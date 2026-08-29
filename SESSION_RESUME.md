# SESSION RESUME — GridCheck (Stand: 2026-06-14, HEAD `f3a2d99`)

> **Massgeblicher Stand: `docs/PROJECT_STATUS.md`.**
> Diese Datei ist nur der Session-Einstieg. Alles Inhaltliche (Commits, Migrationen,
> offene Punkte, Prioritaeten) steht in `docs/PROJECT_STATUS.md` und wird hier nicht dupliziert.

## Erster Befehl an die KI:
Lies zuerst .cursorrules, .cursor/rules/06-arbeitsweise-gridcheck.mdc,
.cursor/rules/05-workflow.mdc, .cursor/rules/08-decisions-binding.mdc,
PROJECT_RULES.md, docs/WORKFLOW.md und DECISIONS.md.
Danach docs/PROJECT_STATUS.md fuer den aktuellen Stand.
Arbeite strikt danach. Eine Aufgabe pro Antwort. Backup vor jeder Dateiänderung.
Stack: FastAPI + PostgreSQL 16 + PostGIS + Alembic + Next.js 14. Kein Supabase, kein Drizzle.

## Kurzueberblick (Details in docs/PROJECT_STATUS.md)
- Auth, Engine + N-1-Screening, Stakeholder-PDFs, Szenarienvergleich und Rollen-Routen
  (`/projektierer`, `/vnb`, `/invest`) sind vorhanden.
- Seit 2026-06-11 zusaetzlich: Report-Profil-Overhaul, duale Standorteingabe mit Geocoding,
  Sentry + structlog, Security-Header, Legal-Seiten, DSGVO-Self-Service, MaStR-ETL-Skelett,
  Billing-ENV-Schalter.
- CI laeuft ueber `.github/workflows/ci.yml` (Backend: PostGIS + `alembic upgrade head` +
  `pytest -q tests`; Frontend: `npm ci` + `verify:toolchain` + `lint` + `build`).

## Historischer Verlauf (gekuerzt, 2026-06-11)
- L3.1 Billing-FK-Fix im Code erledigt (`db/models.py`: `foreign_keys=`).
- 6 Bugfixes aus statischem Audit (Stripe-Checkout-Mode, Blank-Screen auf Rollen-Routen,
  `projectId`-Bindung, 401-Redirect, Snapshot-Persistenz Szenarienvergleich, Query-Key `["me"]`).
- Eingabe-Quellen-Markierung: `baue_eingabe_quellen(...)` in `backend/engine/berechnung.py`,
  Ergebnis unter `transparenz['eingabe_quellen']` (additiv, KEIN Einfluss auf Revisionshash).
  Whitelist in `backend/services/visibility_service.py`, Frontend-Mapping in `lib/api/analyze.ts`.
  Quelle-Enum: `nutzer` | `standardwert` | `modell`. PDF-Pfad bewusst nicht angefasst
  (byte-identity-Test `test_perf_002`).

## GIS-Pipeline: Plan statt Blind-Code
- Interaktive OSM-Suche ist live (`geo/osm_nearby.py`). Persistente ETL offen —
  es gibt keinen `backend/services/osm_etl.py`.
- MaStR: nur ETL-Skelett (`backend/services/mastr_import_service.py`).
- Sequenzierter Plan: `docs/ROADMAP_BACKLOG.md` → „GIS-/Netzdatenpipeline" (BL-GIS-001…005).
- Start erst mit lauffaehiger PostgreSQL+PostGIS und gruener Testsuite (Rule 06 / Tests-gruen).

## NAECHSTE AUFGABEN (priorisiert, Details in docs/PROJECT_STATUS.md)
1. **Go-Live-Checkliste** `docs/LAUNCH_CHECKLIST_PRINT.md` abarbeiten (Nutzer-Aktion).
   Ohne `JWT_*` + `alembic upgrade head` auf Railway bleibt Register **503**;
   ohne `BACKEND_URL` in Vercel ist der Proxy-Pfad tot.
2. **ADR-013 entscheiden** („Vorgeschlagen" → „Angenommen"/abgelehnt) inkl. Fragen in
   `docs/PAINPOINT_NB_DASHBOARD.md` §8. Erst danach BL-NB-001.
3. **Audit-Fix `backend/api/v2_reports.py`**: unsanitierter `request_payload` wird persistiert,
   gerechnet wird auf dem gefilterten `payload` (Revisionssicherheits-Inkonsistenz).

## Weitere offene Punkte (Nutzer-Aktionen)
- DNS: app./api.gridcheck.de (docs/DNS_APP_API.md)
- Stripe: Test-Price-IDs anlegen + ENV (docs/STRIPE_TEST_SETUP.md)
- Prod-Smoke: `python scripts/smoke_go_live.py --base-url <railway> --frontend-url https://gridcheck.vercel.app`
- Impressum juristisch pruefen (Token-Platzhalter ersetzen)
- `NORM_VERSION` / `APP_VERSION` in Railway setzen
- Pilotangebot: Platzhalter in docs/sales/PILOTANGEBOT.md fuellen (N Analysen, Preis, Laufzeit)

## Wichtige Regeln (aus .cursorrules)
- Revisionssicherheit: append-only, Hash-Chain
- Keine freie Netzkapazitaet ohne Beleg behaupten
- Keine Geschaeftslogik im Frontend
- Bei Regelverletzung: STOPP + sicherer Vorschlag
