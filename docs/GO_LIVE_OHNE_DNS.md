# GridCheck sofort nutzbar (ohne app.gridcheck.de / api.gridcheck.de)

**Problem:** `app.gridcheck.de` und `api.gridcheck.de` haben oft **keinen DNS-Eintrag** (NXDOMAIN). Der Code auf `main` ist in Ordnung — es fehlt die erreichbare Infrastruktur.

## Bekannte Prod-URLs (Stand Prüfung)

| Rolle | URL | Status |
|-------|-----|--------|
| **Frontend (Vercel)** | https://gridcheck.vercel.app | erreichbar |
| **Backend (Railway)** | über Proxy: `/api/backend/health` → OK | `BACKEND_URL` in Vercel gesetzt |
| **Custom Domains** | app./api.gridcheck.de | DNS fehlt (NXDOMAIN) |

Nach Vercel-Redeploy: Auth nutzt `/api/auth/*`, sonst Fallback auf `/api/backend/api/v1/auth/*`.

**Register 503:** Railway → Postgres + `alembic upgrade head` (siehe unten).

Zwei Wege:

| Weg | Dauer | Ergebnis |
|-----|-------|----------|
| **A – Lokal** | ~10 Min | Register/Login auf `localhost:3000` |
| **B – Vercel + Railway** | ~15 Min | Register/Login auf `*.vercel.app` |

Custom-Domains: [DNS_APP_API.md](./DNS_APP_API.md)

---

## Weg A – Lokal (empfohlen zum Testen)

### 1. Postgres starten

```powershell
cd C:\Users\andre\gridcheck
docker compose up -d postgres
```

### 2. Backend

```powershell
cd C:\Users\andre\gridcheck\backend
copy .env.example .env
# JWT_SECRET und JWT_REFRESH_SECRET in .env mit je 32+ Zufallszeichen ersetzen
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

Health: http://localhost:8000/health → `{"status":"ok",...}`

### 3. Frontend (Node 20)

```powershell
cd C:\Users\andre\gridcheck\frontend
nvm use 20
copy .env.example .env.local
# .env.local: BACKEND_URL=http://localhost:8000
npm install
npm run dev
```

### 4. Registrieren

http://localhost:3000/register — Passwort z. B. `MeinPasswort123!`

Diagnose: http://localhost:3000/api-test

**Hilfsskript:** `.\scripts\start-local.ps1` (startet Postgres, gibt die nächsten Befehle aus)

---

## Weg B – Produktion mit Vercel-URL (ohne Custom Domain)

### 1. Railway – Backend-URL kopieren

Railway → Service **backend** → **Settings → Networking** → öffentliche HTTPS-URL, z. B.:

`https://gridcheck-production-xxxx.up.railway.app`

**Health testen:**

```powershell
Invoke-WebRequest -Uri "https://<RAILWAY-HOST>/health" -UseBasicParsing
```

### 2. Railway – Umgebungsvariablen

```env
APP_ENV=prod
DATABASE_URL=<von Postgres-Service>
JWT_SECRET=<32+ Zeichen>
JWT_REFRESH_SECRET=<32+ Zeichen, anders als JWT_SECRET>
CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$
TRUSTED_HOSTS=*.up.railway.app,*.vercel.app
LOG_LEVEL=INFO
```

Migration (Railway Shell):

```bash
cd backend && alembic upgrade head
```

### 3. Vercel – Frontend

Vercel → Projekt → **Settings → Environment Variables** (Production):

```env
BACKEND_URL=https://<RAILWAY-HOST>
```

- Nur **Origin**, kein `/api/v1`
- **https://**

**Redeploy** auslösen (Deployments → Redeploy).

Vercel-URL notieren, z. B. `https://gridcheck-xxx.vercel.app`

### 4. Smoke-Test

| URL | Erwartung |
|-----|-----------|
| `https://<RAILWAY>/health` | 200 |
| `https://<VERCEL>/api-test` | Health OK, Register-Probe 400/422 |
| `https://<VERCEL>/register` | Erfolg mit starkem Passwort |

**Prüfskript:**

```powershell
.\scripts\go-live-check.ps1 -FrontendUrl "https://<VERCEL>" -BackendUrl "https://<RAILWAY>"
```

---

## Warum app.gridcheck.de nicht geht

DNS muss `app` → Vercel und `api` → Railway zeigen. Bis das gesetzt ist, **Vercel-URL aus dem Dashboard** verwenden, nicht `app.gridcheck.de`.

Siehe [DNS_APP_API.md](./DNS_APP_API.md).

---

## Auth-Details

Siehe [DEPLOY_AUTH_FIX.md](./DEPLOY_AUTH_FIX.md).
