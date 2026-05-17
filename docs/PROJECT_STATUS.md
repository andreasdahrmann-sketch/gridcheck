# GridCheck – Project Status

> Zuletzt aktualisiert: **2026-05-17**

## Stack

| Bereich | Technik |
|---------|---------|
| Frontend | Next.js 14.2.x, React 18, Vercel (`frontend/`) |
| Backend | FastAPI, Python 3.11+, Railway |
| DB | PostgreSQL 16 + PostGIS (Docker lokal :5433) |
| Auth | JWT + Refresh-Cookie, `/api/auth/*` + Rewrite-Fallback |
| Zahlungen | Stripe (optional, Test/Live per ENV) |

## Erledigt (Auszug)

- [x] Engine + N-1-Screening, Stakeholder-PDFs (38+ Report-Tests)
- [x] Auth Backend + Frontend (Register/Login, Session)
- [x] Prod-Frontend: **https://gridcheck.vercel.app** (Vercel)
- [x] Lokal: Register/Login OK; Prod: Railway ENV + Redeploy (Migrations) ausstehend
- [x] PLZ→VNB Lookup (`/api/v1/geo/plz/{plz}`)
- [x] Disclaimer UI + PDF
- [x] KI-Feedback-Hash-Chain (`docs/KI_TRAINING.md`)
- [x] Go-Live-Doku: `GO_LIVE_OHNE_DNS.md`, `DEPLOY_AUTH_FIX.md`, `RAILWAY_ENV_SETUP.md`

## Offen (priorisiert)

| # | Thema | Naechster Schritt |
|---|--------|-------------------|
| 1 | **Railway ENV** | `JWT_*`, `alembic upgrade head` — `docs/RAILWAY_ENV_SETUP.md` |
| 2 | **DNS** | `app`/`api.gridcheck.de` — `docs/DNS_APP_API.md` |
| 3 | **Stripe Checkout** | Test-Price-IDs — `docs/STRIPE_TEST_SETUP.md` |
| 4 | **GIS/OSM** | Eigener Meilenstein — `docs/DATA_SOURCE_PIPELINE.md` |
| 5 | **Enterprise** | Security-Onepager + AVV-Entwurf (juristisch pruefen) |
| 6 | **E2E** | `scripts/smoke_go_live.py --frontend-url` gegen Prod |

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
```

## Bekannte Prod-Befunde (2026-05-17)

- `app.gridcheck.de` / `api.gridcheck.de`: NXDOMAIN
- `gridcheck.vercel.app`: OK; `/api/auth/register` 404 bis Deploy; Rewrite-Pfad 422/503
- Register **503** → Railway: Migrationen + `DATABASE_URL`
