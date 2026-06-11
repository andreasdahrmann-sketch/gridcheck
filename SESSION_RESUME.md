# SESSION RESUME — GridCheck (Stand: 2026-06-11, statisches Audit + Bugfixes)

## Erster Befehl an die KI:
Lies zuerst .cursorrules, .cursor/rules/06-arbeitsweise-gridcheck.mdc, PROJECT_RULES.md, docs/WORKFLOW.md und DECISIONS.md.
Arbeite strikt danach. Eine Aufgabe pro Antwort. Backup vor jeder Dateiänderung.
Stack: FastAPI + PostgreSQL 16 + PostGIS + Alembic + Next.js 14. Kein Supabase, kein Drizzle.

## Wo wir stehen (2026-06-11)
- ✅ L3.1 Billing-FK-Fix ist im Code erledigt (`db/models.py`: `foreign_keys=` an `billing_entitlements`, `ops_assignee`)
- ✅ Passwort-Reset-UI vorhanden (`/login/forgot-password`, `/reset-password`)
- ✅ Szenarienvergleich UI vorhanden (Projekt + Standalone)
- ✅ 6 Bugfixes per statischem Audit (Shell war nicht verfuegbar, daher OHNE Testlauf):
  1. `backend/services/billing_service.py`: Stripe-Checkout-Mode "addon" -> "payment" gemappt (Express-Upgrade war 502)
  2. `frontend/components/GridCheckForm.tsx`: "Zurueck"-Button auf Rollen-Routen ausgeblendet (Blank-Screen-Fix)
  3. `frontend/components/projects/ProjectDetailWorkspace.tsx`: `projectId` an `analyzeGridcheck` uebergeben
  4. `frontend/lib/api/projects.ts` + Workspace: `ProjectsApiError` mit Status; Login-Redirect nur bei 401
  5. `GridCheckForm.tsx`: Snapshot-Persistenz fuer `/projektierer/szenarien-vergleich` ergaenzt
  6. Workspace: Query-Key `["auth-me"]` -> `["me"]`

## NEU 2026-06-11 (nach den 6 Bugfixes): Eingabe-Quellen-Markierung
- Engine: `baue_eingabe_quellen(...)` in `backend/engine/berechnung.py`; Ergebnis unter `transparenz['eingabe_quellen']` (additiv, KEIN Einfluss auf Berechnung/Revisionshash — `build_revision_data` enthaelt transparenz nicht).
- Whitelist: `transparenz.eingabe_quellen` in `backend/services/visibility_service.py` (_COMMON_RESULT_SPEC) ergaenzt.
- Frontend: Typ `EingabeQuelle`/`TransparenzResult` (types/index.ts), Mapping in `lib/api/analyze.ts`, Quellen-Tabelle in `GridCheckForm.tsx` (Step-2 Transparenz-Sektion).
- Quelle-Enum: `nutzer` | `standardwert` | `modell`. Markierte Felder: nennspannung, leistung_mw, leitungstyp, anschlussart, entfernung_km, cos_phi, sk_mva, rx_ratio, trafo_s_mva, trafo_uk_prozent.
- PDF-Pfad bewusst NICHT angefasst (byte-identity-Test `test_perf_002` schuetzen).

## GIS-Pipeline: Plan statt Blind-Code
- Interaktive OSM-Suche ist live (`geo/osm_nearby.py`). Persistente ETL offen.
- Sequenzierter Plan: `docs/ROADMAP_BACKLOG.md` → „GIS-/Netzdatenpipeline" (BL-GIS-001…005).
- Start erst mit lauffaehiger PostgreSQL+PostGIS und gruener Testsuite (Rule 06 / Tests-gruen).

## NAECHSTE AUFGABE: Verifikation
Sobald Terminal verfuegbar:
1. cd backend; .\venv\Scripts\Activate.ps1; python -m pytest tests\ -q   (Fokus: test_berechnung, test_analyze_v2_route, test_demo_scenarios, test_perf_002_pdf_byte_identity)
2. cd frontend; npm run build   (Typcheck eingabe_quellen)
3. Bei Gruen: Commit Bugfixes + Eingabe-Quellen-Feature + Doku-Updates

## Danach (priorisierte Offene Punkte — Nutzer-Aktionen noetig)
- Railway: `JWT_*`-ENV setzen + `alembic upgrade head` (docs/RAILWAY_ENV_SETUP.md) — Register 503 bis dahin
- DNS: app./api.gridcheck.de (docs/DNS_APP_API.md)
- Stripe: Test-Price-IDs anlegen + ENV (docs/STRIPE_TEST_SETUP.md)
- Prod-Smoke: `python scripts/smoke_go_live.py --base-url <railway> --frontend-url https://gridcheck.vercel.app`
- ADR-013: Nutzer-Entscheidung "Vorgeschlagen" -> "Angenommen" (+ Fragen in docs/PAINPOINT_NB_DASHBOARD.md §8), erst dann BL-NB-001
- Pilotangebot: Platzhalter in docs/sales/PILOTANGEBOT.md fuellen (N Analysen, Preis, Laufzeit)

## Groessere offene Meilensteine (Code)
- GIS-/Netzdatenpipeline (docs/DATA_SOURCE_PIPELINE.md) — eigener Meilenstein
- "Jede Eingabe mit Quelle markiert (User/Default/Modell)" — Engine-Feature, teilweise vorhanden
- Notiert (nicht angefasst): `v2_reports._resolve_engine_result()` speichert unsanitierten `request_payload` im Audit (Inkonsistenz, kein Crash)

## Wichtige Regeln (aus .cursorrules)
- Revisionssicherheit: append-only, Hash-Chain
- Keine freie Netzkapazitaet ohne Beleg behaupten
- Keine Geschaeftslogik im Frontend
- Bei Regelverletzung: STOPP + sicherer Vorschlag
