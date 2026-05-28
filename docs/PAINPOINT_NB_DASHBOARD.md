---
titel: Painpoint NB-Dashboard — Kumulations-Check und georeferenzierte VNB-Sicht
status: Konzept / Vor-ADR (siehe ADR-013)
stand: 2026-05-24
verantwortlich: GridCheck Core
bezug:
  - docs/SKILLS_REFERENCE.md (§9 Painpoint Netzbetreiber)
  - docs/PROJEKTIERER_ARCHITECTURE.md
  - docs/NB_AKZEPTANZ_SCREENING.md
  - DECISIONS.md (ADR-004, ADR-005, ADR-007-DETAIL, ADR-008, ADR-010, ADR-011)
  - docs/ROADMAP_BACKLOG.md (BL-NB-001 … BL-NB-005)
---

# Painpoint NB-Dashboard — Kumulations-Check und georeferenzierte Anfragen

> **Zweck dieses Dokuments:** Lücken-Analyse zwischen dem vom Nutzer beschriebenen Soll-Flow (Netzbetreiber sieht alle offenen Netzanfragen georeferenziert; Projektierer sieht Kumulationsindikatoren) und dem aktuellen Stand der GridCheck-Codebasis. Es ist **kein Implementierungsticket**, sondern Grundlage für ADR-013 und die BL-NB-* Stories.

> **Kein Stack-Wechsel.** Der Stack bleibt FastAPI + PostgreSQL 16/PostGIS + Alembic + Next.js 14 + Railway/Vercel. Begründung siehe Abschnitt 7.

---

## 1. Soll-Flow vs. Ist-Stand

| # | Soll (Nutzer-Vorgabe) | Ist (GridCheck Mai 2026) | Lücke | Risiko bei Nichtumsetzung |
|---|----------------------|--------------------------|-------|---------------------------|
| 1 | Projektierer gibt Anlage ein (Standort, Leistung, Typ) | Wizard inkl. `plant_type`, `ac_kw`, `dc_kwp`, Standort vorhanden (`ProjectProfileFields`) | — | — |
| 2 | App prüft: „Gibt es bereits eine Netzanfrage in diesem Bereich?" (Kumulations-Check) | `screen_coincidence_factor` warnt nur qualitativ (Single-Connection); keine persistente Cluster-Abfrage pro NB-Region / ONT / Radius | **Tabelle `grid_requests`** und Aggregat-Endpoint fehlen | Projektierer sieht parallele Anfragen nicht → Doppelanträge, falsche Erwartungen |
| 3 | NB sieht in Dashboard alle offenen Anfragen georeferenziert | `NetzbetreiberDashboard` zeigt eigene Pakete/Akzeptanz; **keine** Cross-Project-Geo-Map | `/vnb/map` (Marker-Map mit Filter) fehlt; Zugriff nur für `vnb_verification_status='approved'` | NB hat keinen aggregierten Überblick → kein operativer Mehrwert |
| 4 | Vorprüfung mit echten Netzdaten → Antwort in Stunden | Engine v2 liefert Vorprüfung **ohne echte Netzdaten** (heuristisch); MaStR/OSM-Stubs vorhanden, DSO-Datenpfad offen | DSO-Schnittstelle / verifizierte Topologie fehlt; verbleibt N1-1 / N1-2 (siehe `.cursor/rules/06-arbeitsweise-gridcheck.mdc`) | Antwortqualität bleibt heuristisch; **kein** Risiko für die App (durch Disclaimer abgedeckt) |
| 5 | Digitale Einspeisezusage mit Auflagen | Projektierer-PDF (`projektierer.html.j2`) enthält Empfehlungen + Auflagen, aber **kein** Dokument-Typ „Vor-Einspeisezusage" | PDF-Template + Signaturfeld fehlen | Workflow endet beim Bericht, nicht beim NB-Konsens |

**Legende Lücke-Spalte:** Fettgedruckt = Schema/DB-Änderung nötig. Kursiv = nur Backend/Frontend-Logik.

---

## 2. Datenmodell-Anforderungen (Kumulations-Check)

### 2.1 Tabelle `grid_requests` (Vorschlag, **nicht** implementiert)

Eine Zeile = eine vom Projektierer ausgelöste Vor-Netzanfrage, ausgelöst automatisch beim Speichern einer Analyse (`analysis_runs.status IN ('completed','submitted')`).

| Spalte | Typ | NOT NULL | Zweck |
|--------|-----|----------|-------|
| `id` | `bigint` PK | ✅ | Surrogatschlüssel |
| `analysis_run_id` | `bigint` FK → `analysis_runs.id` | ✅ | Bindeglied zum Snapshot (Revisionssicherheit) |
| `owner_user_id` | `int` FK → `users.id` | ✅ | Projektierer (für Mandantenfilter) |
| `owner_org_id` | `int` FK → `organizations.id` (sofern vorhanden) | optional | Mehrnutzer-Mandant |
| `plant_type` | `varchar(32)` | ✅ | PV/Wind/BESS/… (Enum aus `engine.plant_types`) |
| `ac_kw` | `numeric(10,2)` | ✅ | AC-Anschlussleistung |
| `dc_kwp` | `numeric(10,2)` | optional | nur PV/Hybrid (assumption only) |
| `voltage_level` | `varchar(8)` | ✅ | `low` / `medium` / `high` |
| `location_lat` | `numeric(9,6)` | ✅ | WGS84 |
| `location_lon` | `numeric(9,6)` | ✅ | WGS84 |
| `location_geom` | `geometry(Point,4326)` (PostGIS) | ✅ | Index `GIST` für Radiussuche (ADR-008) |
| `postal_code` | `varchar(5)` | ✅ | PLZ-Aggregat (anonymisiert) |
| `region_code` | `varchar(16)` | optional | NB-Region/AGS-Schlüssel (Destatis) |
| `vnb_id` | `int` FK → `users.id` (Rolle `netzbetreiber`) | optional | Zustellungsmappe, falls eindeutig zuordenbar |
| `status` | `varchar(24)` | ✅ | `draft` / `submitted` / `withdrawn` / `confirmed` / `rejected` |
| `submitted_at` | `timestamp` | optional | gesetzt bei status `submitted` |
| `revision_hash` | `varchar(64)` | optional | SHA-256-Kette aus `analysis_runs` (ADR-005) |
| `created_at` | `timestamp` | ✅ | DEFAULT now() |
| `updated_at` | `timestamp` | ✅ | trigger / app-side |

**Indizes (Pflicht):**

- `GIST(location_geom)` — Radius-Queries für Kumulation
- `B-TREE(postal_code, status)` — PLZ-Aggregat
- `B-TREE(owner_user_id)` — Mandantenfilter
- `B-TREE(status, submitted_at)` — Kanban / offene Anfragen
- `B-TREE(vnb_id, status)` — NB-Dashboard

**Append-only-Regel (ADR-005, ADR-010):**
Status-Übergänge nicht als UPDATE, sondern als zusätzliche Zeile in `grid_request_audit` (separates Audit-Modell) — Schema analog zu `gridcheck_result_audit`. Im MVP genügt `updated_at`, der Audit-Trail wird in BL-NB-001b nachgereicht.

### 2.2 Beziehungs-Modell

```
analysis_runs ─── 1:1 ───► grid_requests ─── n:1 ───► users (owner)
                              │
                              └─ optional n:1 ──► users (vnb_id, verified)
```

`analysis_runs` bleibt der Snapshot-Anker; `grid_requests` ist die für andere Projektierer/NBs **sichtbare Schicht** mit reduzierter PII.

### 2.3 Was **nicht** in die Tabelle gehört

- Adresse, Flurstück, Firmenname, Ansprechpartner, Projektname → bleiben in `analysis_runs` / `projects` (mandantengeschützt)
- Wirtschaftliche Eckdaten (CAPEX, Renditen) → bleiben in `projektierer_output`
- Netzbetreiber-Antwortdaten → eigenes Modell `grid_request_responses` (BL-NB-005)

---

## 3. Privacy & Mandantenfähigkeit

### 3.1 Zwei Sichten — striktes Need-to-know

| Rolle | Sicht | Felder | Geo-Genauigkeit |
|-------|-------|--------|-----------------|
| Eigener Projektierer | **Detail** | alle eigenen `grid_requests` + verknüpfter Run | Punkt (lat/lon exakt) |
| Fremder Projektierer | **Aggregat** | nur Indikatoren über Radius/PLZ | gerundet auf 3 Nachkommastellen (~110 m) oder nur PLZ-Centroid |
| Netzbetreiber `vnb_verification_status='approved'` | **Detail im eigenen Gebiet** | alle Felder außer Projektierer-Klarname (pseudonymisiert) | Punkt |
| Netzbetreiber `pending` | **kein Zugriff** | — | — |
| Admin | Detail | alle | Punkt |

### 3.2 Aggregat-Indikator (Beispiel-Response für fremde Projektierer)

```json
{
  "radius_km": 5,
  "center_postal_code": "12345",
  "open_request_count": 3,
  "sum_ac_kw_requested": 4800,
  "voltage_levels": ["low", "medium"],
  "plant_type_breakdown": {
    "pv": 2,
    "bess": 1
  },
  "data_freshness_days": 4,
  "disclaimer": "Aggregierte, nicht-verbindliche Indikatoren aus laufenden Vor-Anfragen. Keine Aussage über verfügbare Netzkapazität."
}
```

**Pflichtregeln (BOLA-Schutz, `.cursor/rules/06-arbeitsweise-gridcheck.mdc`):**

- **k-Anonymität:** Mindestens **k ≥ 3** Anfragen pro Aggregat. Bei k < 3 → Response `"insufficient_data": true`, keine Counts.
- Keine Differenzbildung möglich: Aggregat-Endpoint nimmt **nur PLZ oder Radius-Centroid** entgegen, nicht beides simultan, und der Centroid wird serverseitig gerundet.
- Kein Endpoint liefert eine Liste fremder `grid_request.id`-Werte.
- Rate-Limit auf Aggregat-Endpoint (mind. 30 req/min/user) gegen Scrape-Differenzangriffe.

### 3.3 NB-Detail-Sicht

- Nur Felder freigeben, die für die operative Vorprüfung nötig sind. **Klarname Projektierer bleibt verborgen** bis zur freigegebenen Kontaktaufnahme über `/vnb/kommunikation` (existiert).
- Audit-Log jeder NB-Sicht (`grid_request_view_audit`): wer, wann, welche `grid_request.id` — Pflicht für KRITIS/DSGVO Art. 32.

---

## 4. DSO-/Netzdaten-Schnittstelle

### 4.1 Was kostenfrei nutzbar ist (Datenklasse A/B nach `.cursor/rules/06-arbeitsweise-gridcheck.mdc`)

| Quelle | Inhalt | Nutzbar für | Grenze |
|--------|--------|-------------|--------|
| MaStR (Marktstammdatenregister, BNetzA) | Bestand EE-Anlagen, MaStR-Nr., Standort, Leistung, Status | Hintergrundlast, Cluster-Indikator, Plausibilitätsprüfung | Kein Bezug zu *geplanten* Anfragen anderer Projektierer |
| SMARD (BNetzA) | Erzeugung/Last je Regelzone, viertelstündlich | Engpassindikator regional | Keine Aussage auf ONT/Strang-Ebene |
| BNetzA-Veröffentlichungen | Netzentgelte, regional verbreitete Engpässe | Kontext, Reporting | Aggregiert |
| BKG Verwaltungsgrenzen | PLZ ↔ AGS ↔ NB-Gebiet | Mapping Region | — |
| OSM/Overpass | Trassen, Umspannwerke, Hinweise | Geometrie, Lagebeziehung | **Niemals** als Quelle freier Kapazität |
| DWD CDC | Klima/Solar/Wind | Ertragsschätzung | — |

### 4.2 Was VNB-Daten erfordert (Datenklasse D, geschlossen)

- ONT-Auslastung, Mittelspannungs-Strangbelastung, Kurzschlussleistung Sk'' am PCC
- Topologie inkl. Schutzkonzept, N-1-Pfade
- Bereits **erteilte** Einspeisezusagen anderer Projektierer
- Geplante Netzausbauschritte (NEP regional)

→ Vor Vorhandensein von D-Daten bleibt das Screening bei **N1-1 / N1-2** (siehe `.cursor/rules/06-arbeitsweise-gridcheck.mdc`, Abschnitt N-1-Regeln). Die App **darf** das nicht überstellen.

### 4.3 Realistische Anbindungsstufen

1. **Stufe 1 (MVP):** Nur GridCheck-interne `grid_requests` als Kumulationsquelle (App-Cross-Projekt).
2. **Stufe 2 (+1 Jahr):** MaStR-Bestand als zusätzliche Hintergrundlast (Datenklasse A).
3. **Stufe 3 (+2 Jahre):** Pilot-VNB liefert SK''/ONT-Auslastung via signiertem JSON/CSV-Drop oder REST-API.
4. **Stufe 4 (offen):** CIM/CGMES-Pfad (pandapower-Konverter existiert in `backend/.venv` als Vendor-Lib — nicht aktiv eingebunden, kein Eigenbau ohne ADR).

---

## 5. Rechtliche Aspekte

### 5.1 DSGVO

- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b (Vertrag) für eigenen Projektierer, Art. 6 Abs. 1 lit. f (berechtigtes Interesse) für aggregierte Indikatoren an andere Projektierer.
- **Datenminimierung (Art. 5 Abs. 1 lit. c):** Aggregat-Endpoint liefert keine direkten Personenbezüge. Klarname-Freigabe nur nach expliziter Zustimmung.
- **Verzeichnis von Verarbeitungstätigkeiten (Art. 30):** `grid_requests` als eigene Verarbeitung dokumentieren — `docs/AVV_ENTWURF.md` ergänzen (Folge-Ticket).
- **Speicherbegrenzung (Art. 5 Abs. 1 lit. e):** Inaktive `grid_requests` (status `withdrawn`, älter 24 Monate) per Soft-Delete-Job; Audit-Log bleibt 10 Jahre.

### 5.2 Geschäftsgeheimnisse (GeschGehG)

- AC kW + Standort + Anlagentyp kann in Kombination ein Projektgeheimnis sein. **Anonymisierung im Aggregat ist Pflicht**, nicht optional.
- VNB sieht zwar Detaildaten, ist aber qua Rolle (§ 12, § 14 EnWG) Empfänger; Klarname Projektierer bleibt bis zur freigegebenen Kontaktaufnahme verborgen.

### 5.3 BNetzA / EnWG

- GridCheck ist **kein** Netzbetreiber und gibt **keine** Einspeisezusage (siehe Rule 06: „ersetzt niemals eine rechtsverbindliche Netzanschlussprüfung").
- Eine „digitale Vor-Einspeisezusage" (BL-NB-005) darf nur als **Empfehlungsdokument des VNB** umgesetzt werden — VNB ist Ersteller und Unterzeichner, GridCheck nur Trägermedium.
- Disclaimer-Pflicht in jedem Aggregat-Output und PDF (existiert bereits in `projektierer.html.j2`, muss für NB-Output gespiegelt werden).

### 5.4 KRITIS / IT-Sicherheit

- Detaillierte Standortdaten von EE-Anlagen sind kritische Infrastrukturinformationen. Zugriff streng rollengebunden + Audit-Log.
- Keine sensiblen Roh-Standortlisten via öffentliche Endpoints, kein Sitemap-Crawling der NB-Map.
- Konsistenz mit ADR-007-DETAIL: keine Datenresidenz außerhalb EU.

---

## 6. Aufwandsschätzung pro Teilfeature

Schätzung: **S** = ≤ 1 Personenwoche, **M** = 2–4 PW, **L** = ≥ 5 PW (inkl. Tests, Review, Migration, Dokumentation). Ohne KI, ohne externe DSO-Anbindung.

| Story | Inhalt | Aufwand | Abhängig von |
|-------|--------|---------|--------------|
| BL-NB-001 | Schema `grid_requests` + Alembic-Migration + Audit-Tabelle | **M** | ADR-013 freigegeben |
| BL-NB-002 | Backend `POST /api/v1/grid-requests` + automatischer Insert beim Analyse-Run | **M** | BL-NB-001 |
| BL-NB-003 | Aggregierter Kumulations-Endpoint (PLZ/Radius, k≥3, Rate-Limit) | **M** | BL-NB-001, BL-NB-002 |
| BL-NB-004 | `/vnb/map` Frontend (Leaflet o. ä.), Backend `/api/v1/vnb/grid-requests/map`, Mandanten-/Verifikations-Gate | **L** | BL-NB-001 … 003, `vnb_verification_status='approved'` |
| BL-NB-005 | PDF-Template „Vor-Einspeisezusage" + Workflow im NB-Dashboard | **L** | BL-NB-004, Klärung rechtlicher Rahmen (5.3) |
| BL-NB-006 (Folge) | MaStR-Import als Hintergrundlast (Datenklasse A) | **L** | unabhängig, ADR nötig |

**Realistischer MVP-Korridor:** BL-NB-001 bis BL-NB-003 ≈ **6–8 Personenwochen** inkl. Review, Tests, Migration, Privacy-Audit. BL-NB-004/005 separater Iteration. **Kein** „in einer Woche fertig".

---

## 7. Stack-Hinweis — warum keine Supabase-Architektur

Die vom Nutzer skizzierte Architektur (Next.js 15 / React 19 / Supabase Auth + DB + Storage + Realtime) wird **nicht** übernommen. Begründung:

1. **ADR-007-DETAIL (Kein Supabase, final 2026-05-10):** GridCheck verarbeitet KRITIS-nahe Daten. Supabase erfüllt die Anforderungen an Datenresidenz und Auditierbarkeit nicht, das ist explizit dokumentiert.
2. **ADR-010 (Alembic-only):** Schemamanagement ausschließlich versioniert via Alembic. Supabase-Migration-Tooling wäre paralleler Pfad — verboten.
3. **ADR-005 / ADR-008 (PostgreSQL + PostGIS + Hash-Chain):** PostGIS und Append-only Audit-Tabellen sind eigene Komponenten der Revisionssicherheit. Mit Supabase würden Hash-Chain-Trigger und Audit-Strategie verlagert / neu konzipiert — großes Risiko, kein Mehrwert.
4. **Engine in Python:** Die fachliche Logik (`backend/engine/grid_calculation_v2.py`, `nb_akzeptanz_screening.py`, `projektierer_output.py`) ist Python. Sie ist die Source of Truth — eine Bibliotheks-/Edge-Function-Verlagerung nach JS ist explizit ausgeschlossen (siehe `docs/PROJEKTIERER_ARCHITECTURE.md`).
5. **Toolchain-Matrix (`.cursor/rules/07-toolchain-versions.mdc`):** Next.js 15 / React 19 ist außerhalb der erlaubten Matrix. Ein Stacksprung wäre eigenes Migrationsprojekt mit ADR, nicht Teil dieses Painpoints.
6. **Realtime:** Die in der Skizze betonte Supabase-Realtime ist für das Kumulations-Feature **nicht** notwendig. Aktualität via TanStack Query Invalidations + SSE/WS in FastAPI ist ausreichend (siehe ADR-007-DETAIL).

→ Der Painpoint „NB-Dashboard mit Kumulations-Check" wird mit dem bestehenden Stack adressiert: FastAPI-Endpoints (Versionierung `/api/v1`), Alembic-Migration für `grid_requests`, PostGIS-Index für Radius, Next.js-14-Seite `/vnb/map` mit Leaflet, JWT-Auth + Rollen-Gate, Audit-Log analog `gridcheck_result_audit`.

---

## 8. Offene Fragen für den Nutzer

1. **Mandantenmodell:** Eigene `organizations`-Tabelle einführen, oder bleibt `users.id` der einzige Mandantenschlüssel?
2. **k-Anonymität:** Reicht `k ≥ 3` für Aggregat? Strengere Werte (k ≥ 5) erhöhen Privatsphäre, machen MVP aber schnell datenleer.
3. **VNB-Pilot:** Gibt es einen konkreten Pilot-VNB, mit dem die Detail-Sicht (Variante C in ADR-013) im echten Betrieb validiert werden kann?
4. **PLZ vs. PostGIS-Radius im MVP:** PLZ-Aggregat ist DSGVO-freundlicher, Radius (mit Centroid-Rundung) ist UX-freundlicher. Welche Variante zuerst?
5. **„Vor-Einspeisezusage" (BL-NB-005):** Wer ist rechtlich Aussteller — VNB direkt, oder soll GridCheck einen mehrstufigen Workflow „Empfehlungsentwurf → VNB-Signatur" abbilden?

**Bis zur Klärung: kein Code-Schritt jenseits von BL-NB-001 anstoßen.** (Regel 06: nur eine Aufgabe zur Zeit.)

---

## 9. Referenzen

- `DECISIONS.md` (alle relevanten ADRs)
- `docs/SKILLS_REFERENCE.md` §8 + §9
- `docs/PROJEKTIERER_ARCHITECTURE.md` (Source of Truth Engine)
- `docs/NB_AKZEPTANZ_SCREENING.md` (bestehende Screening-Module)
- `backend/engine/nb_akzeptanz_screening.py` (`screen_coincidence_factor`)
- `backend/alembic/versions/20260512_02_site_markers_mvp.py` (Vorbild Geo-Tabelle)
- `backend/alembic/versions/20260519_02_vnb_verification_status.py` (Verifikations-Gate)
- `.cursor/rules/06-arbeitsweise-gridcheck.mdc` (Datenquellen, N-1-Level, Frontend-Beschränkungen)
- `.cursor/rules/03-elektrotechnik.mdc` (Norm-Bezüge VDE-AR-N 4100/4105/4110)
