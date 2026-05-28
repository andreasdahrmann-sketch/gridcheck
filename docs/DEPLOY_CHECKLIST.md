# GridCheck — Deploy-Checkliste (Railway + Vercel)

**Stand:** 2026-05-19  
**Ziel:** Produktions-Deploy ohne Schema-Drift, mit revisionssicheren ENV und Alembic.

---

## 1. Vor dem Deploy (lokal / CI)

```powershell
cd frontend
npm run verify:toolchain
npm run build

cd ..\backend
python -m pytest tests/test_projektierer_plant_types.py tests/test_nb_akzeptanz_screening.py tests/test_vnb_access_control.py tests/test_projektierer_report.py -q --tb=no
```

- Alle Checks gruen
- Keine uncommitteten `.venv`-Artefakte

---

## 2. PostgreSQL (Railway)

| Schritt | Befehl / Aktion |
|--------|------------------|
| Backup | Railway Snapshot oder `pg_dump` vor Migration |
| Migration | `alembic upgrade head` (CI oder Railway pre-deploy) — **nicht** beim App-Start in Prod |
| Verifikation | `alembic current` = `head` |

**Regel:** Kein `Base.metadata.create_all()` in Prod. Jede Schemaaenderung = Alembic-Revision (ADR-010).

---

## 3. Backend ENV (Railway) — Pflicht

| Variable | Zweck | Hinweis |
|----------|-------|---------|
| `APP_ENV` | `prod` \| `staging` \| `dev` | Fail-fast wenn fehlt |
| `APP_VERSION` | Audit / PDF | Git-Tag z. B. `v1.2.3` |
| `DATABASE_URL` | Postgres | Von Railway injiziert |
| `JWT_SECRET` | Access-Token | min. 32 Zeichen, zufaellig |
| `JWT_REFRESH_SECRET` | Refresh-Token | ≠ `JWT_SECRET` |
| `JWT_ACCESS_TTL_MIN` | z. B. `15` | |
| `JWT_REFRESH_TTL_DAYS` | z. B. `14` | |
| `CORS_ORIGINS` | Komma-Liste | z. B. `https://app.gridcheck.de` |
| `LOG_LEVEL` | `INFO` (prod) | |
| `NORM_VERSION` | Normensammlung-Label | z. B. `VDE-AR-N-4105:2018-11 + ...` |

### Optional (empfohlen / bei Nutzung setzen)

| Variable | Zweck |
|----------|-------|
| `SENTRY_DSN` | Error-Tracking |
| `STRIPE_*` | Billing (Self-Serve) |
| `RESEND_API_KEY` / SMTP | Passwort-Reset / Transaktionsmail |
| `MAPBOX_TOKEN` | Karten |

**Secrets nie im Repo.** Template: `backend/.env.example`.

---

## 4. Frontend (Vercel)

| Einstellung | Wert |
|-------------|------|
| Root Directory | `frontend` |
| Node | **20.x** (`.nvmrc`, `engines`) |
| Install | `npm ci` |
| Build | `npm run build` (fuehrt `verify:toolchain` aus) |

### ENV

| Variable | Zweck |
|----------|-------|
| `BACKEND_URL` | Railway-API (Proxy `/api/backend`) |
| `NEXT_PUBLIC_*` | nur wenn bewusst oeffentlich |
| `VITE_APP_ENV` / `VITE_SENTRY_DSN` | optional |

---

## 5. Routen-Smoke (nach Deploy)

- `/projektierer`, `/login`, `/login/forgot-password`, `/reset-password`
- `/map`, `/reports`, `/onboarding`
- `/vnb`, `/vnb/kommunikation` (nur freigeschalteter VNB)
- `/admin/users` (nur Admin)
- `GET /health` → `{"status":"ok",...}`

---

## 6. VNB-Freischaltung

1. UI: `/admin/users` (Admin-Rolle)
2. CLI: `python scripts/approve_netzbetreiber.py --email …`

Siehe `docs/VNB_ACCESS.md`.

---

## 7. Bewusst ausserhalb Deploy (Nutzer / Drittanbieter)

- Impressum (rechtlicher Inhalt)
- Stripe / Resend / SMTP Live-Keys
- Echte VNB-TAB-, Trafo- und Kumulationsdaten
- Verbindliche NVP-Auskunft des DSO

---

## 8. Rollback

1. Railway: vorheriges Deployment reaktivieren
2. DB: `alembic downgrade -1` nur mit Backup und Drift-Check
3. Frontend: Vercel Instant Rollback
