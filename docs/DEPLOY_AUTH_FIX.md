# Auth Deploy-Checkliste (Register / Login)

Stand: 2026-05-16. Ziel: Register und Login end-to-end (Vercel Frontend → Railway Backend → PostgreSQL).

> **Sofort nutzbar:** Wenn `app.gridcheck.de` / `api.gridcheck.de` nicht aufloesen (NXDOMAIN), zuerst [GO_LIVE_OHNE_DNS.md](./GO_LIVE_OHNE_DNS.md) (lokal oder `*.vercel.app` + Railway). Custom-DNS: [DNS_APP_API.md](./DNS_APP_API.md).

## 1. Railway (Backend + PostgreSQL)

Pflichtvariablen (Service **backend**):

```env
APP_ENV=prod
APP_VERSION=v0.1.0
DATABASE_URL=<von Railway Postgres injiziert>
JWT_SECRET=<min. 32 Zeichen, zufaellig>
JWT_REFRESH_SECRET=<eigener Wert, ungleich JWT_SECRET>
JWT_ACCESS_TTL_MIN=15
JWT_REFRESH_TTL_DAYS=14
LOG_LEVEL=INFO
NORM_VERSION=VDE-AR-N-4105:2018-11

# CORS: Produktiv-Domain ODER Vercel-Regex fuer Previews
CORS_ORIGINS=https://app.gridcheck.de
# CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$

# Host-Header beim Proxy: Railway-Hostname aus BACKEND_URL + Frontend-Domains
TRUSTED_HOSTS=*.up.railway.app,app.gridcheck.de,api.gridcheck.de
```

Migration **vor** oder unmittelbar mit Deploy (Railway Shell / CI):

```bash
cd backend
alembic upgrade head
```

Health:

```bash
curl -sS https://<BACKEND-ORIGIN>/health
# Erwartung: {"status":"ok","version":"..."}
```

## 2. Vercel (Frontend, Root Directory `frontend`)

```env
BACKEND_URL=https://<BACKEND-ORIGIN>
```

Regeln:

- Nur **Origin** (kein `/api`, kein `/api/v1`).
- **https://** (ausser lokales `http://localhost:8000`).
- Nach Aenderung: **Redeploy** (Build bricht ohne `BACKEND_URL` ab).

Optional (Default passt):

```env
NEXT_PUBLIC_API_BASE=/api/backend
```

Auth-Requests nutzen `/api/auth/*` (Next.js Route Handler, serverseitiger Proxy). Alle anderen APIs weiter `/api/backend/*` (Rewrite).

## 3. Smoke-Tests

| URL | Erwartung |
|-----|-----------|
| `https://<BACKEND-ORIGIN>/health` | HTTP 200, `status: ok` |
| `https://<FRONTEND>/api/backend/health` | HTTP 200 (Rewrite) |
| `https://<FRONTEND>/api-test` | Health OK + Register-Probe 400/422 |
| `https://<FRONTEND>/register` | Registrierung mit starkem Passwort → Erfolg |

Register-Probe (schwaches Passwort, nur Erreichbarkeit):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "https://<FRONTEND>/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"probe@example.com","password":"short","role":"projektierer"}'
# Erwartung: 400 oder 422 (nicht 502/404)
```

## 4. Wenn weiterhin „API request failed“ / Fehler

1. Browser **DevTools → Network** → Request `register` oder `login` oeffnen.
2. **HTTP-Status** notieren:

| Status | Typische Ursache |
|--------|------------------|
| **502 / 503 / 504** | `BACKEND_URL` falsch, Backend down, DB nicht erreichbar |
| **404** | `BACKEND_URL` mit `/api/v1` Suffix oder falscher Pfad |
| **400** | `TRUSTED_HOSTS` enthaelt Host aus `BACKEND_URL` nicht |
| **500** | Backend-Log (Railway); oft fehlende Migration |
| **409** | E-Mail bereits registriert |
| **422 / 400** | Passwort-Policy (min. 12 Zeichen, Gross/Klein/Zahl/Sonderzeichen) |

3. Railway Logs: `auth_register_*`, `DATABASE_UNAVAILABLE`, `Invalid host header`.
4. Vercel: Environment `BACKEND_URL` in **Production** pruefen (nicht nur Preview).

## 5. Lokal

```bash
# Terminal 1 – Postgres (Port 5433) + Backend
cd backend
alembic upgrade head
uvicorn main:app --reload --port 8000

# Terminal 2 – Frontend
cd frontend
# .env.local: BACKEND_URL=http://localhost:8000
npm run dev
```

Tests:

```bash
cd backend
pytest tests/test_auth_projects_api.py -q --tb=short
```
