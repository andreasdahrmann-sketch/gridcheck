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
| **Vercel** | `BACKEND_URL` = Railway-HTTPS-Origin (ohne `/api/v1`) |
| **Railway** | Variablen aus `docs/RAILWAY_ENV_SETUP.md` |
| **Migration** | `releaseCommand` in `backend/railway.toml` → `alembic upgrade head` beim Deploy |
| **Health** | `/health` zeigt `database: ok` wenn DB steht |

### Vercel — Pflicht-Variablen (Build + Runtime)

Im Vercel-Projekt (**Root Directory:** `frontend/`, **Node:** 20) unter *Settings → Environment Variables*:

| Variable | Environments | Wert / Regeln |
|----------|--------------|---------------|
| **`BACKEND_URL`** | Production, Preview, Development | Railway-**HTTPS**-Origin **ohne** Pfad-Suffix, z. B. `https://gridcheck-production.up.railway.app` — **nicht** `http://`, **nicht** `/api` oder `/api/v1`, **nicht** die Vercel-Frontend-URL |

Ohne `BACKEND_URL` kann der **Build** mit einem Platzhalter durchlaufen; **Register/Login und `/api/backend/*` funktionieren erst**, wenn `BACKEND_URL` gesetzt ist und ein Redeploy gelaufen ist.

Optional (UI): `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_APP_VERSION` — siehe `frontend/.env.example`.

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
python scripts\smoke_go_live.py --base-url https://<RAILWAY-HOST> --frontend-url https://gridcheck.vercel.app
```

Register-Probe **422** = OK. **503** = Migration/DB (Railway redeploy nach ENV).

---

## Custom Domain (später)

`docs/DNS_APP_API.md` — `app.gridcheck.de` + `api.gridcheck.de`
