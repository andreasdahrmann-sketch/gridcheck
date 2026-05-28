# GridCheck — Backlog (Nice-to-have)

Dokumentierte Folgeaufgaben ohne aktuelle Implementierungspflicht.

| Thema | Beschreibung | Prioritaet |
|-------|--------------|------------|
| Engine-Tests | Erweiterung Rechenkern-Coverage (N-1-Grenzfaelle, Spannungsfall-Matrix) | Mittel |
| Sentry | `SENTRY_DSN` Backend + Frontend, Release-Tracking mit `APP_VERSION` | Mittel |
| Onboarding | Gefuehrter Erst-Check (Tour), Beispielprojekt | Niedrig |
| Passwort-Reset UI | Login-Seite: Formular fuer `/api/v1/auth/forgot-password` + Token-Eingabe (Backend fertig) | Hoch |
| Impressum | Rechtlich gepruefte Firmendaten (Nutzer pflegt separat) | Hoch (Recht) |

**Hinweis:** Keine Scheinsicherheit bei Netzkapazitaet; DSO-Daten bleiben separater Integrationspfad.

---

## NB-Painpoint — Kumulations-Check und Georeferenz-Sicht

Bezug: `docs/PAINPOINT_NB_DASHBOARD.md`, `docs/decisions/ADR-013-kumulations-check-und-nb-georeferenz.md`, `DECISIONS.md` ADR-013.

> **Vor Story-Start:** ADR-013 muss **freigegeben** sein und die offenen Fragen in `PAINPOINT_NB_DASHBOARD.md` §8 müssen beantwortet sein. Reihenfolge ist **bindend** (Rule 06: eine Aufgabe zur Zeit).

### BL-NB-001 — Schema `grid_requests` + Alembic-Migration

**Ziel:** Persistente Cross-Project-Schicht für vom Projektierer ausgelöste Vor-Netzanfragen.

**Scope:**
- Neue Alembic-Revision `2026MMDD_xx_grid_requests` mit Tabelle `grid_requests` (Felder siehe `docs/PAINPOINT_NB_DASHBOARD.md` §2.1).
- PostGIS-Index `GIST(location_geom)`, B-Tree-Indizes auf `postal_code`, `(status, submitted_at)`, `owner_user_id`, `(vnb_id, status)`.
- Begleitende Audit-Tabelle `grid_request_audit` (append-only, analog `gridcheck_result_audit`).
- SQLAlchemy-Modelle in `backend/app/models/` ohne API-Anbindung in dieser Story.

**Akzeptanzkriterien:**
- `alembic upgrade head` und `alembic downgrade -1` laufen ohne Drift auf leerer DB.
- Tabellen vorhanden, Indizes vorhanden (`\d grid_requests` + `\di`).
- Down-Migration entfernt beide Tabellen sauber (Rule 01: reversibel).
- Keine API-Endpoints, kein Frontend.
- Doc-Update: `DECISIONS.md` ADR-013 von „Vorgeschlagen" auf „Angenommen" durch Nutzer.

**Tests:**
- `pytest backend/tests/test_grid_requests_schema.py` (neu): Insert + Audit-Trigger, kein Update außer `status`/`updated_at`.
- Migrations-Smoke gegen leere und gegen vorhandene Test-DB (Rule 01).

**Abhängigkeiten:** ADR-013 freigegeben; Mandantenmodell-Entscheidung (`organizations` vs. nur `users.id`) geklärt.

**Aufwand:** M (2–4 PW inkl. Migration, Modelle, Tests, Review).

---

### BL-NB-002 — Backend `POST /api/v1/grid-requests`

**Ziel:** Projektierer kann Vor-Netzanfrage erzeugen — manuell oder automatisch beim Abschluss eines Analyse-Runs.

**Scope:**
- Pydantic-Schemas `GridRequestCreate`, `GridRequestRead` (Rule 01, kein Roh-Dict).
- Endpoint `POST /api/v1/grid-requests` mit JWT-Auth, Owner-Bind an aktuellen User.
- Service `services/grid_request_service.py`:
  - validiert Eingaben (Plausibilität AC kW > 0, Geo-Bounds DE, etc.),
  - schreibt Zeile + Audit-Eintrag,
  - berechnet `revision_hash` aus zugehörigem `analysis_runs`-Snapshot (ADR-005).
- Auto-Trigger im bestehenden Analyse-Run-Abschluss (`engine/projektierer_output.py` Aufrufer): bei `status='completed'` legt der Service einen `grid_request` mit `status='draft'` an, sofern nicht bereits vorhanden.
- Status-Transitionen `draft → submitted → confirmed|rejected|withdrawn` über separaten Endpoint `PATCH /api/v1/grid-requests/{id}/status` mit Whitelist.

**Akzeptanzkriterien:**
- Pydantic-Validierung lehnt fehlende oder ungültige Felder ab (Rule 01).
- Owner-Filter: `GET /api/v1/grid-requests` listet ausschließlich eigene Einträge.
- BOLA-Test: User A kann mit ID von User B nicht zugreifen (HTTP 404).
- Audit-Eintrag pro Status-Wechsel (Append-only, ADR-005).
- Keine Klarname-Felder von anderen Mandanten in irgendeiner Response.

**Tests:**
- `pytest backend/tests/test_grid_requests_api.py` mit positiven/negativen Fällen, JWT-Owner-Filter, Status-Maschine.
- Engine-Auto-Insert-Test (mocked Run-Abschluss).

**Abhängigkeiten:** BL-NB-001.

**Aufwand:** M.

---

### BL-NB-003 — Aggregierter Kumulations-Endpoint

**Ziel:** Projektierer sehen anonymisierte Indikatoren über andere offene Anfragen in einem Bereich — ohne PII, ohne Re-Identifikation.

**Scope:**
- Endpoint `GET /api/v1/grid-requests/aggregate`:
  - Eingabe **xor**: entweder `postal_code` (5-stellig) **oder** `radius_km` + `lat` + `lon` (serverseitige Rundung auf 3 NK-Stellen ≈ 110 m).
  - Antwortform siehe `docs/PAINPOINT_NB_DASHBOARD.md` §3.2.
- k-Anonymität: bei `open_request_count < 3` → `{ "insufficient_data": true }` + Disclaimer. **Kein** Count, **kein** Summen-Wert.
- Rate-Limit ≥ 30 req/min/user via `slowapi` (Rule 01).
- Logging strukturiert (`structlog`) inkl. Hash der Anfrage-Parameter, **ohne** Roh-Geo (Privacy-by-Design).
- Frontend-Konsument: `GridCheckForm`-Side-Card („In Ihrer Region sind X Anfragen mit zusammen Y MW gemeldet — keine Aussage über Netzkapazität.").
- Pflicht-Disclaimer im UI + JSON-Feld `disclaimer`.

**Akzeptanzkriterien:**
- Property-basierter Test gegen Differenzangriffe: Aggregat zweier knapp überlappender Centroiden darf keine Einzelanfrage rekonstruieren (Test fuzzt 1000 zufällige Konfigurationen).
- Bei k < 3 keine numerischen Felder in Response.
- Rate-Limit löst bei Überschreitung HTTP 429 aus.
- `postal_code` **und** `radius_km` gleichzeitig → HTTP 422.
- Keine Owner-IDs, keine `grid_request.id`-Listen in Response.

**Tests:**
- `pytest backend/tests/test_grid_requests_aggregate.py` (Pflicht inkl. Differenzangriff-Fuzz, k-Schwelle, Rate-Limit-Smoke).
- `vitest` Test des Side-Cards-Renderings mit Mock-Response.

**Abhängigkeiten:** BL-NB-001, BL-NB-002, Entscheidung k-Schwelle (`PAINPOINT_NB_DASHBOARD.md` §8.2).

**Aufwand:** M (privacy-tests treiben Aufwand, nicht das Schema).

---

### BL-NB-004 — NB-Map-View `/vnb/map` (admin + verified NB only)

**Ziel:** Verifizierter Netzbetreiber sieht alle offenen `grid_requests` seines Gebiets georeferenziert; Admin sieht alles.

**Scope:**
- Frontend `frontend/app/vnb/map/page.tsx`:
  - Route mit Wrapper `<ProtectedVnbRoute requireVerified={true} />` (existiert in `frontend/components/auth/ProtectedVnbRoute.tsx`; ggf. um `requireVerified`-Prop erweitern).
  - Leaflet (oder MapLibre) mit Marker-Cluster, Filter: `status`, `voltage_level`, `plant_type`, Zeitraum.
  - Click-Marker → Detail-Panel **ohne** Klarname (siehe ADR-013).
- Backend `GET /api/v1/vnb/grid-requests/map`:
  - Auth-Gate: Rolle `netzbetreiber` **und** `vnb_verification_status='approved'` **und** Bounding-Box im NB-Gebiet (`vnb_id` oder `region_code`-Mapping).
  - Admin überschreibt Gebietsfilter.
  - Antwort: Geo-JSON mit Punkten, Felder ohne `owner_user_id`-Klarname.
- Audit-Tabelle `grid_request_view_audit` (wer / wann / welche IDs gesehen) — Pflicht für DSGVO Art. 32 (siehe `PAINPOINT_NB_DASHBOARD.md` §3.3).
- UI-Hinweis: „Kein Echtzeit-Netzkapazitätsbild. Vor-Anfragen, kein verbindlicher Stand." (Rule 06.)
- Klarname-Freigabe-Workflow via existierende `/vnb/kommunikation` referenzieren — kein neuer Endpoint in dieser Story.

**Akzeptanzkriterien:**
- Nicht-verifizierter NB erhält HTTP 403 + Hinweis auf Verifikationspfad.
- BOLA-Test: NB-Region A sieht keine Punkte aus Region B.
- View-Audit-Eintrag pro Aufruf (Smoke-Test mit ≥ 1 Eintrag).
- Keine Klarname-Felder im Frontend-Source-Map abrufbar.
- Map-Performance: ≤ 2 s Erstrendering mit 5.000 Markern (Cluster).
- Lighthouse-Accessibility ≥ 90 (Rule 02).

**Tests:**
- `pytest backend/tests/test_vnb_map_endpoint.py` (Auth-Matrix, Region-Filter, Audit).
- Playwright-E2E (optional, Happy-Path): Login als verifizierter NB → Map-Render → Marker-Klick → Detail ohne Klarname.

**Abhängigkeiten:** BL-NB-001 … 003, `vnb_verification_status='approved'`-Pfad (`20260519_02_vnb_verification_status`).

**Aufwand:** L (Frontend + Backend + Audit-Tabelle + Performance-Tests).

---

### BL-NB-005 — Digitale Vor-Einspeisezusage (PDF-Template)

**Ziel:** Nach VNB-Vorprüfung kann der NB ein strukturiertes Dokument „Vor-Einspeisezusage mit Auflagen" als PDF erzeugen. **GridCheck ist Trägermedium, VNB ist Aussteller.**

**Scope:**
- Neues Jinja2-Template `backend/engine/stakeholder_reports/templates/vnb_vor_einspeisezusage.html.j2` (analog `projektierer.html.j2`, eigener Branding-Block für VNB).
- Generator `backend/engine/stakeholder_reports/vnb_vor_einspeisezusage.py` mit Pflichtfeldern:
  - Projektierer (pseudonymisiert bis Freigabe)
  - Standort (Adresse + Geo)
  - AC kW, Anlagentyp, Spannungsebene
  - Auflagen-Liste (strukturiert, aus NB-Eingabe)
  - Vorbehalte (z. B. Sk''-Daten ausstehend)
  - Norm-Bezug (`norm_references_applied` aus Engine — Rule 03)
  - Audit-Hash + `analysis_runs.id`
  - **Disclaimer:** „Keine rechtsverbindliche Netzanschlusszusage; nur Vor-Einschätzung des VNB im Rahmen einer Vor-Anfrage." (Rule 06.)
- Endpoint `POST /api/v1/vnb/grid-requests/{id}/vor-einspeisezusage` (verifizierter NB only, gleicher Gebietsfilter wie BL-NB-004).
- Status-Wechsel `grid_requests.status → confirmed` mit Audit-Eintrag.
- Frontend-Aktion im Detail-Panel der NB-Map.

**Akzeptanzkriterien:**
- PDF enthält alle Pflichtfelder + Hash + Audit-ID + Disclaimer.
- Test: Audit-Trail zeigt `confirmed`-Übergang inkl. NB-User + Zeitstempel.
- Klarname-Freigabe erforderlich, bevor PDF Klarname enthält (sonst: pseudonymisiert).
- Rechtlich gepflegter Disclaimer ist Pflichtfeld (Template-Test schlägt fehl, wenn entfernt).
- VNB darf **nur eigene Region** Zusagen erstellen.

**Tests:**
- `pytest backend/tests/test_vnb_vor_einspeisezusage.py` (Pflichtfelder, Disclaimer, Audit, Region-Gate).
- PDF-Smoke (Größe, MIME).

**Abhängigkeiten:**
- BL-NB-004 muss live sein.
- **Rechtliche Klärung** vor Start (siehe `docs/PAINPOINT_NB_DASHBOARD.md` §5.3 / §8.5): Aussteller-Rolle. Ohne Klärung **nicht** beginnen.

**Aufwand:** L (Template + Generator + Audit-Workflow + PDF-Tests + rechtliche Abstimmung).

---

### Reihenfolge & Abhängigkeitsgraph

```
ADR-013 angenommen
   └─ BL-NB-001  (Schema)
        └─ BL-NB-002  (POST + Auto-Insert)
             └─ BL-NB-003  (Aggregat, Privacy-first)
                  └─ BL-NB-004  (NB-Map)
                       └─ BL-NB-005  (Vor-Einspeisezusage, nach rechtlicher Klärung)
```

**Out-of-scope dieser Iteration:** BL-NB-006 (MaStR-Bestandsdaten als zusätzliche Cluster-Schicht — eigene ADR und eigene Story).
