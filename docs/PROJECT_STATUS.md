# GridCheck – Project Status

> Zuletzt aktualisiert: **2026-06-14 (HEAD `f3a2d99`)**
>
> **Dieses Dokument ist der massgebliche Projektstand (Single Source of Truth).**
> `SESSION_RESUME.md`, `SESSION_PROMPT.md` und `ROADMAP.md` verweisen hierher.
> `docs/SESSION_STATE.md` ist historisch (2026-05-06) und nicht mehr massgeblich.

## Stack

| Bereich | Technik |
|---------|---------|
| Frontend | Next.js 14.2.35 (App Router), React 18.3.1, Node 20 (`engines`), Vercel (`frontend/`) |
| Backend | FastAPI, Python 3.11+ (CI: 3.12), Railway |
| DB | PostgreSQL 16 + PostGIS (Docker lokal :5433, CI: `postgis/postgis:16-3.4`) |
| Auth | JWT + Refresh-Cookie, `/api/auth/*` + Rewrite-Fallback, 10-min Idle-Auto-Logout |
| Zahlungen | Stripe (optional, Test/Live per ENV, Sichtbarkeit ueber `BILLING_ENABLED`) |
| Observability | Sentry SDK + structlog (JSON-Logs, PII-Masking) |

Toolchain-Matrix: `.cursor/rules/07-toolchain-versions.mdc`. `frontend/package.json`
ruft `verify:toolchain` als `prebuild`. Das Frontend hat 33 Routen (`frontend/app/**/page.tsx`).

## Erledigt (Auszug)

- [x] Engine + N-1-Screening, Stakeholder-PDFs (Report-Tests vorhanden)
- [x] Auth Backend + Frontend (Register/Login, Session)
- [x] Prod-Frontend: **https://gridcheck.vercel.app** (Vercel)
- [x] Lokal: Register/Login OK; Prod: Railway ENV + Redeploy (Migrations) ausstehend
- [x] PLZ→VNB Lookup (`/api/v1/geo/plz/{plz}`)
- [x] Disclaimer UI + PDF
- [x] KI-Feedback-Hash-Chain (`docs/KI_TRAINING.md`)
- [x] Go-Live-Doku: `docs/GO_LIVE_OHNE_DNS.md`, `docs/DEPLOY_AUTH_FIX.md`, `docs/RAILWAY_ENV_SETUP.md`
- [x] Passwort-Reset UI (`/login/forgot-password`, `/reset-password`)
- [x] Szenarienvergleich UI (Projekt + Standalone) inkl. Datenpfad-Fix 2026-06-11
- [x] Bugfix-Runde 2026-06-11 (statisches Audit): Stripe-Addon-Checkout-Mode, Blank-Screen auf
      Rollen-Routen, projectId-Bindung der Projektanalyse, 401-Redirect, Query-Key
- [x] CI (`.github/workflows/ci.yml`): Backend-Job (PostGIS-16-Service, `alembic upgrade head`,
      `pytest -q tests`, Python 3.12) + Frontend-Job (`npm ci`, `verify:toolchain`, `lint`,
      `build`, Node 20). 48 Testdateien unter `backend/tests/`.

## Neu seit 2026-06-11 (Commits bis HEAD)

Die folgenden 15 Commits liegen nach dem letzten Stand der alten Statusdokumente:

| Commit | Inhalt |
|--------|--------|
| `79d4d04` | Projektierer-Profil-Overhaul, 10-min Idle-Auto-Logout, `is_admin`-Flag in `/me` |
| `5a1a878` | VNB- + Invest-Report-Profile (Score-Hero, Risk-Block, Quellen, Szenarien, Sensitivitaeten) |
| `18d0e5d` | Duale Standorteingabe (Adresse + lat/lon) mit Nominatim-Geocoding, fail-soft Warnungen |
| `c95a793` | `.gitignore`: `bak*`-Pattern erweitert |
| `e2f1901` | Sentry-SDK + structlog JSON-Logs, PII-Masking, Login- + Projekt-Events |
| `13eeef8` | Frontend `error`/`not-found`/`loading`-Routen + CSP/HSTS/XFO/Referrer/Permissions-Header |
| `4cca715` | Legal: Impressum/AGB/Datenschutz Erstfassung mit Token-Platzhaltern + TTDSG-Cookie-Opt-in |
| `d1d36c2` | Docs: Railway-Prod-ENV-Setup + 1-Seiten-Launch-Checkliste |
| `e27d006` | Fix: `package-lock.json` resync mit `package.json` (npm-ci-Hotfix) |
| `908587d` | Fix: Rate-Limit-Testisolation gegen Redis-Backend (Test-Mode-Bypass + Bucket-Cleanup) |
| `a6c8bd7` | Billing: ENV-Schalter `BILLING_ENABLED` versteckt Stripe/Preise fuer Nicht-Admins |
| `6c87f54` | DSGVO: Self-Service-Datenexport + Account-Soft-Delete mit anonymisiertem E-Mail-Block |
| `d3a796c` | GIS: MaStR-Import-ETL-Skelett (`mastr_units` + `mastr_imports`-Migration, Read-API, Smoke-CLI) |
| `a888074` | Legal: Anwalts-Briefing-Bundle + Aufsichtsbehoerden-Helper fuer 16 Bundeslaender |
| `f3a2d99` | Settings/Privacy + Datenschutz-Links verdrahtet, Billing-ENV in Railway-Setup (**HEAD**) |

### Neue Migrationen

- `backend/alembic/versions/20260614_01_add_project_address_fields.py`
- `backend/alembic/versions/20260614_02_add_mastr_units.py`
- `backend/alembic/versions/20260614_03_user_deleted_at.py`

### Neue Services / Endpunkte

- `backend/services/mastr_import_service.py` — MaStR-ETL-Skelett; Read-API
  `backend/api/v1_mastr.py` (`/api/v1/mastr`), CLI `backend/scripts/run_mastr_import.py`
- `backend/services/dsgvo_service.py` — Datenexport (Art. 15/20) + Konto-Soft-Delete (Art. 17),
  Endpunkte in `backend/api/users.py` (`POST /me/data-export`), UI `frontend/app/settings/privacy/page.tsx`
- `backend/services/geocoding_service.py` — Adresse ↔ lat/lon, eingebunden in `backend/api/projects.py`

## Offen (priorisiert)

| # | Prio | Thema | Naechster Schritt |
|---|------|-------|-------------------|
| 1 | Kritisch (Nutzer-Aktion) | **Go-Live** | `docs/LAUNCH_CHECKLIST_PRINT.md`, 15 Schritte, unerledigt. Ohne `JWT_SECRET`/`JWT_REFRESH_SECRET` + `alembic upgrade head` auf Railway liefert `/api/auth/register` **503**; ohne `BACKEND_URL` in Vercel ist der Proxy-Pfad tot. |
| 2 | Kritisch (Entscheidung) | **ADR-013** | Kumulations-Check + NB-Georeferenz steht in `DECISIONS.md` auf „Vorgeschlagen". BL-NB-001 darf laut `docs/ROADMAP_BACKLOG.md` erst nach Freigabe **und** Beantwortung der Fragen in `docs/PAINPOINT_NB_DASHBOARD.md` §8 starten. Sperre eingehalten: keine `grid_requests`-Migration vorhanden. |
| 3 | Kritisch (Fachlichkeit) | **GIS-/Netzdaten** | Echte GIS-/Netzdaten fehlen (Risiko R-08, `docs/RISIKO_STATUS.md`). `asset_candidates` existiert als Tabelle/Modell aus Migration `20260510_01_data_source_models.py`, aber es gibt **keinen** `backend/services/osm_etl.py` — BL-GIS-001…005 sind reiner Plan. MaStR ist nur ETL-Skelett. |
| 4 | Hoch (Revisionssicherheit) | **Audit-Bug `v2_reports`** | `backend/api/v2_reports.py` (~Z. 339–363): `persist_completed_analysis_run(..., request_payload=request_payload)` speichert den **unsanitierten** Payload, waehrend die Berechnung auf dem via `enforce_package_rights` gefilterten `payload` laeuft. Das Audit dokumentiert damit nicht, was tatsaechlich gerechnet wurde. Inkonsistenz, kein Crash. **Bewusst noch nicht gefixt** (eigene Aufgabe). |
| 5 | Hoch (Nutzer-Aufgabe) | **Impressum juristisch** | Token-Platzhalter aus `4cca715` durch geprueften Text ersetzen; Anwalts-Briefing-Bundle aus `a888074` nutzen. |
| 6 | Mittel | **ENV Railway** | `NORM_VERSION` + `APP_VERSION` setzen — `docs/RAILWAY_ENV_SETUP.md` |
| 7 | Mittel | **Consent** | Opt-in vor Sentry/Analytics durchziehen (TTDSG-Cookie-Banner ist da, Kopplung pruefen) |
| 8 | Mittel | **Pilotangebot** | Parameter in `docs/sales/PILOTANGEBOT.md` fuellen (N Analysen, Preis, Laufzeit) |
| 9 | Mittel | **Enterprise** | Security-Onepager + AVV-Entwurf (juristisch pruefen) |
| 10 | Mittel | **Perf-Baselines** | BL-PERF-006 steht in `docs/ROADMAP_BACKLOG.md` auf `in_progress` (Setup geliefert, Baseline-Runs ausstehend) |
| 11 | Niedrig | **DNS** | `app`/`api.gridcheck.de` — `docs/DNS_APP_API.md` |
| 12 | Niedrig | **Stripe Checkout** | Test-Price-IDs — `docs/STRIPE_TEST_SETUP.md` |
| 13 | Niedrig | **E2E** | `scripts/smoke_go_live.py --frontend-url` gegen Prod |

## Technische Schulden

- Historische Backup-Verzeichnisse (`_backups/`, `backups/`, `_milestone_backups/`) sind
  weiterhin im Git-Index, obwohl `.gitignore` `bak*`/`_milestone_backups/` inzwischen abdeckt.
  Aufraeumen ist eine eigene Aufgabe, hier bewusst nicht angefasst.
- Der im Audit genannte `backend/engine/stakeholder_reports/renderer.py.bak-L3-engine-hash-pflicht`
  liegt **nicht** mehr im Working Tree; die Datei wurde in Commit `96acd52` untracked.
- Punkt 4 der Offen-Tabelle (`v2_reports`-Audit-Payload) ist Revisionssicherheits-Schuld.

## Skripte

```powershell
# ENV pruefen
cd backend; python scripts/validate_env.py --expect-prod

# Smoke (Backend direkt)
python scripts/smoke_go_live.py --base-url https://<railway-host>

# Smoke inkl. Vercel
python scripts/smoke_go_live.py --base-url https://<railway-host> --frontend-url https://gridcheck.vercel.app

# Datenpipeline
python scripts/run_data_source_pipeline.py

# MaStR-Import (Skelett-Smoke)
python scripts/run_mastr_import.py
```

## Bekannte Prod-Befunde (2026-05-17, seither nicht neu geprueft)

- `app.gridcheck.de` / `api.gridcheck.de`: NXDOMAIN
- `gridcheck.vercel.app`: OK; `/api/auth/register` 404 bis Deploy; Rewrite-Pfad 422/503
- Register **503** → Railway: Migrationen + `DATABASE_URL`

## Weiterfuehrende Dokumente

- `DECISIONS.md` (Repo-Root) — bindende ADRs
- `ROADMAP.md` (Repo-Root) — Sprint-Planung
- `docs/ROADMAP_BACKLOG.md` — sequenzierte Folgestories (BL-NB-*, BL-GIS-*, BL-PERF-*)
- `docs/RISIKO_STATUS.md` — Risikoregister
- `docs/LAUNCH_CHECKLIST_PRINT.md` — Go-Live-Checkliste
- `docs/ARCHITEKTUR.md` — Architekturuebersicht
