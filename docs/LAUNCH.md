# GridCheck starten — eine Seite

## Lokal (funktioniert sofort)

```powershell
cd C:\Users\andre\gridcheck
.\scripts\bootstrap-local.ps1
```

Dann zwei Terminals (Backend :8000, Frontend :3000 mit `nvm use 20`).

→ http://localhost:3000/register — Passwort z. B. `MeinPasswort123!`

---

## Produktion (Vercel + Railway)

| Was | URL / Aktion |
|-----|----------------|
| **App** | https://gridcheck.vercel.app |
| **Backend (Railway)** | `https://gridcheck-production.up.railway.app` — **ohne** `:8080` (Port nur intern) |
| **Vercel** | `BACKEND_URL=https://gridcheck-production.up.railway.app` (nur Origin, kein `/api/v1`) → **Redeploy** |
| **Railway** | Variablen aus `railway-variables.generated.txt` / `docs/RAILWAY_ENV_SETUP.md` |
| **Migration** | `releaseCommand` in `backend/railway.toml` → `alembic upgrade head` beim Deploy |
| **Health** | `GET /health` → 200; mit `APP_ENV=prod` zusätzlich `"database":"ok"` |

### Du musst in Vercel (Production)

**Settings → Environment Variables:**

```
BACKEND_URL=https://gridcheck-production.up.railway.app
```

Danach **Deployments → Redeploy** (sonst nutzt die Live-App noch den alten Build).

### Du musst in Railway (Backend-Service)

Aus Vorlage `railway-variables.generated.txt` (Werte **nicht** committen):

```
JWT_SECRET=<48 Zeichen Zufall>
JWT_REFRESH_SECRET=<anderer 48 Zeichen Zufall>
DATABASE_URL=<von Postgres-Service verlinken>
APP_ENV=prod
CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$
CORS_ORIGINS=https://gridcheck.vercel.app
TRUSTED_HOSTS=*.up.railway.app,*.vercel.app
```

Ohne `APP_ENV=prod` antwortet `/health` ohne `database`-Feld (nur `status` + `version`).

### Railway-Variablen (Minimum)

```
JWT_SECRET=<48 Zeichen Zufall>
JWT_REFRESH_SECRET=<anderer 48 Zeichen Zufall>
DATABASE_URL=<von Postgres>
APP_ENV=prod
CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$
CORS_ORIGINS=https://gridcheck.vercel.app
TRUSTED_HOSTS=*.up.railway.app,*.vercel.app
```

JWT erzeugen: `.\scripts\bootstrap-local.ps1` schreibt Beispiel-`.env` — Werte kopieren, nicht committen.

### Prüfen

```powershell
cd backend
python scripts\smoke_go_live.py --base-url https://gridcheck-production.up.railway.app --frontend-url https://gridcheck.vercel.app
```

Direkt:

```powershell
Invoke-WebRequest -Uri "https://gridcheck-production.up.railway.app/health" -UseBasicParsing
Invoke-WebRequest -Uri "https://gridcheck.vercel.app/api/backend/health" -UseBasicParsing
```

Register-Probe **422** = OK. **503** = Migration/DB (Railway redeploy nach ENV).

---

## Custom Domain (später)

`docs/DNS_APP_API.md` — `app.gridcheck.de` + `api.gridcheck.de`
