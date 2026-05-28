---
adr: 013
titel: Kumulations-Check und NB-Georeferenz-Sicht
status: Vorgeschlagen
datum: 2026-05-24
autor: GridCheck Core
bezug:
  - DECISIONS.md (ADR-004, ADR-005, ADR-007-DETAIL, ADR-008, ADR-010, ADR-011)
  - docs/PAINPOINT_NB_DASHBOARD.md
  - docs/PROJEKTIERER_ARCHITECTURE.md
  - docs/ROADMAP_BACKLOG.md (BL-NB-001 … BL-NB-005)
---

> **Hinweis Doppelablage:** Rule 08 (`.cursor/rules/08-decisions-binding.mdc`) deklariert `DECISIONS.md` als kanonische Quelle und schließt `docs/decisions/` aus. Dieses Detail-ADR existiert auf expliziten Nutzer-Wunsch zusätzlich; die maßgebliche Tabellenzeile mit Status wird **parallel** in `DECISIONS.md` geführt. Bei künftigen Status-Änderungen ist `DECISIONS.md` führend; dieses File ist Detailbegründung.

# ADR-013 — Kumulations-Check und georeferenzierte NB-Sicht

## Kontext

Der vom Nutzer formulierte Painpoint (siehe `docs/PAINPOINT_NB_DASHBOARD.md`, §1):

1. Projektierer gibt Anlage ein (Standort, Leistung, Typ)
2. App prüft: „Gibt es bereits eine Netzanfrage in diesem Bereich?" (Kumulations-Check)
3. NB sieht in seinem Dashboard alle offenen Anfragen georeferenziert
4. Vorprüfung mit echten Netzdaten → Antwort in Stunden statt Wochen
5. Digitale Einspeisezusage mit Auflagen

GridCheck hat heute (Mai 2026) Schritt 1 abgedeckt, Schritt 2 nur qualitativ via `screen_coincidence_factor`, Schritt 3 gar nicht, Schritt 4 nur heuristisch, Schritt 5 nur als Bericht-Empfehlung. Eine systematische Lösung erfordert eine neue Datenebene (`grid_requests`) und eine Strategie für die Sichtbarkeit dieser Daten zwischen verschiedenen Mandanten.

Die Schwierigkeit liegt nicht im Schema, sondern im **Spagat zwischen Datenschutz/Geschäftsgeheimnis (Projektierer) und operativem Nutzen (NB)**: Wer darf was sehen?

## Entscheidung (Vorschlag)

**Zweischicht-Sichtbarkeit der `grid_requests`:**

- **Aggregat-Schicht** (Variante A) für alle authentifizierten Projektierer.
- **Detail-Schicht** (Variante C) ausschließlich für Netzbetreiber mit `vnb_verification_status = 'approved'` und nur für deren räumlich zuordenbares Gebiet.

Die **Variante B** (Heatmap mit Geo-Cluster) wird **nicht** als Standard-Sicht für fremde Projektierer eingeführt, sondern bleibt explizit dem verifizierten NB vorbehalten.

## Optionen (geprüft)

### Variante A — PLZ-/Radius-aggregierte Anzeige (privacy-first)

- Fremde Projektierer sehen **nur** anonymisierte Indikatoren (k-Anonymität, k ≥ 3).
- Felder: PLZ-Centroid (oder Radius-Centroid serverseitig gerundet), Anzahl offener Anfragen, Summe AC kW, Anlagentyp-Histogramm, Datenfrische.
- **Keine** Liste fremder `grid_request.id`, **keine** Punktgeometrien.

**Pro:** DSGVO + GeschGehG vollständig erfüllt; minimaler Engineering-Aufwand; keine BOLA-Fallen.
**Kontra:** Nutzwert für Projektierer begrenzt — eher Warnsignal als Planungswerkzeug.

### Variante B — Geo-Cluster mit Heatmap

- Fremde Projektierer sehen Heatmap-Tiles (z. B. H3 / Geohash) mit gerundeter Dichte.
- Pro Tile: nur Counts + Summen, kein Detail.

**Pro:** Visuell überzeugend; bessere Standortwahl.
**Kontra:** Re-Identifikations-Risiko bei seltenen Anlagentypen; Differenzangriffe (zwei Tiles vs. ein gemeinsames) erfordern aufwendige Privacy-Budgets; UX suggeriert Genauigkeit, die wir nicht haben. **Nicht** für fremde Projektierer freigeben, sondern intern für verifizierte NBs als Zusatz-Layer optional.

### Variante C — Volle NB-Detail-Sicht

- Verifizierte NBs sehen Punkt-Geometrie, AC kW, Anlagentyp, Status, Audit-Bezug, **ohne** Klarname Projektierer.
- Klarname-Freigabe nur nach expliziter Zustimmung über `/vnb/kommunikation` (existiert).
- Audit-Log jeder NB-Sicht (`grid_request_view_audit`).

**Pro:** Liefert echten operativen Mehrwert; entspricht dem Soll-Flow Schritt 3.
**Kontra:** Erfordert robustes Verifikations-Gate (existiert: `vnb_verification_status`); rechtliche Klärung Datenklasse D; höchste Audit-Anforderungen.

## Empfehlung

| Zielgruppe | Variante | Begründung |
|------------|----------|------------|
| Projektierer (eigene Daten) | Detail | Eigene Daten, immer voll sichtbar |
| Projektierer (fremde Daten) | **A** | Privacy-first, k ≥ 3, kein Re-Id-Risiko |
| Netzbetreiber `vnb_verification_status = 'approved'` | **C** im eigenen Gebiet | Operative Vorprüfung; Verifikation existiert |
| Netzbetreiber `pending` | Kein Zugriff | Existierendes Gate bleibt aktiv |
| Admin | Detail | Bestehende Admin-Rechte |

**Variante B** kein eigenständiges Frontend-Feature im MVP — höchstens optionaler Layer der NB-Map.

## Konsequenzen

### Positiv

- Klarer Pfad für Schritt 2 und 3 des Painpoints (siehe `PAINPOINT_NB_DASHBOARD.md`, §1).
- Bestehendes Verifikations-Gate (`vnb_verification_status`) wird aktiv genutzt — kein neues Auth-Konzept.
- PostGIS (ADR-008) wird endlich für die Aufgabe verwendet, für die es vorgehalten wird.
- Audit-Trail (ADR-005) wird auf neue Sichten erweitert, keine konzeptionelle Lücke.

### Negativ / Risiken

- Schema-Erweiterung (`grid_requests` + Audit-Tabelle) bindet Engine-Output an persistente Cross-Project-Schicht — Migrationen müssen rückwärts kompatibel mit bestehenden `analysis_runs` bleiben.
- Aggregat-Endpoint braucht Rate-Limit + k-Schwelle, sonst Differenzangriffe möglich.
- NB-Map kann zu Erwartung „Echtzeit-Kapazitätssicht" führen — Disclaimer-Disziplin im UI Pflicht (Rule 06).
- Mehraufwand für Privacy-Tests (BL-NB-003-Akzeptanzkriterien zwingen k ≥ 3).
- Klarname-Maskierung verlangt strikte Trennung: NB darf Audit-Verlauf, aber nicht Klarname sehen, bis Kontaktfreigabe vorliegt. Verstoß = DSGVO-Vorfall.

### Neutral

- Engine-Logik (`backend/engine/*`) bleibt unverändert — die Tabelle `grid_requests` ist eine Ableitung, kein neuer Rechenpfad.

## Migrations- und Rollout-Plan

1. **Phase 0 — ADR-013 freigeben.** Nutzer-Entscheidung zu offenen Fragen in `PAINPOINT_NB_DASHBOARD.md` §8 (Mandantenmodell, k-Schwelle, PLZ vs. Radius, VNB-Pilot, Aussteller Einspeisezusage).
2. **Phase 1 — BL-NB-001.** Alembic-Migration `grid_requests` + `grid_request_audit` (Append-only), GIST-Index, B-Tree-Indizes. Datenmodell ohne API freischalten.
3. **Phase 2 — BL-NB-002.** Backend `POST /api/v1/grid-requests` + automatischer Insert beim Abschluss eines Analyse-Runs. Status-Maschine `draft → submitted → confirmed/rejected/withdrawn`.
4. **Phase 3 — BL-NB-003.** Aggregat-Endpoint `GET /api/v1/grid-requests/aggregate` mit `postal_code` **xor** `radius_km+lat+lon`. k ≥ 3-Gate, Rate-Limit, Tests gegen Differenzangriff.
5. **Phase 4 — BL-NB-004.** Frontend `/vnb/map` (Leaflet o. ä.) + Backend `GET /api/v1/vnb/grid-requests/map`. Verifikations-Gate + Audit-View-Log.
6. **Phase 5 — BL-NB-005.** PDF-Template „Vor-Einspeisezusage" und NB-Workflow. Vor Start: rechtliche Klarstellung Aussteller (`PAINPOINT_NB_DASHBOARD.md` §5.3 / §8).
7. **Phase 6 (out-of-scope dieser ADR) — BL-NB-006.** MaStR-Bestandsdaten als zusätzliche Cluster-Schicht, eigene ADR.

### Rollback

- Alembic-Down-Migrationen für `grid_requests` und Audit-Tabelle ohne Datenverlust (Tabellen anfangs leer / append-only).
- Frontend-Routen sind Feature-gated über `vnb_verification_status` und ENV-Flag — abschaltbar ohne Migration.

## Beschluss

- **Status:** Vorgeschlagen (wartet auf Nutzerfreigabe).
- **Aktive Aufgabe nach Freigabe:** BL-NB-001.
- **Annahmen, die noch geklärt werden müssen:** siehe `docs/PAINPOINT_NB_DASHBOARD.md` §8.

## Referenzen

- ADR-004 (Stack)
- ADR-005 (Hash-Chain Revisionssicherheit)
- ADR-007-DETAIL (Kein Supabase)
- ADR-008 (PostgreSQL 16 + PostGIS)
- ADR-010 (Alembic-only)
- ADR-011 (PostgreSQL-only für Tests)
- `.cursor/rules/06-arbeitsweise-gridcheck.mdc` (Datenquellen-Regeln, N-1-Level, Frontend-Grenzen)
- `.cursor/rules/08-decisions-binding.mdc` (Vorrang `DECISIONS.md`)
