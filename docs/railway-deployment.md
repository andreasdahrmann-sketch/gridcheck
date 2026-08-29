# GridCheck - Split Deployment fuer den MVP

## Zielbild

Sauberer MVP-Pfad mit getrennten Deployments:

- `frontend/` auf Vercel
- `backend/` auf einem separaten Host mit PostgreSQL (z. B. Railway, Coolify, Hetzner, Render)
- oeffentliche HTTPS-Frontend-URL als PWA- und Web-Einstiegspunkt
- backendseitig stateless vorbereitet, Upload-Pfade explizit konfigurierbar

Die bestehende Next.js-App bleibt der Auslieferungspfad. Fuer Android ist keine native Store-Verpackung noetig, solange die Vercel-URL per HTTPS erreichbar ist und Chrome die PWA installieren kann.

## Repo-Stand

- `frontend/next.config.mjs` rewritet `/api/backend/*` serverseitig auf `BACKEND_URL`
- Vercel braucht dafuer **kein** zusaetzliches `vercel.json`; Next.js wird nativ erkannt und die Rewrites kommen bereits aus `next.config.mjs`
- `/health` ist als Backend-Healthcheck vorhanden
- `backend/Procfile` und `backend/railway.toml` bleiben als optionale Startvorlagen fuer Railway nutzbar
- `PROJECT_UPLOAD_DIR` und `SITE_MARKER_UPLOAD_DIR` sind dokumentiert, damit Uploads spaeter nicht an eine ephemere Container-FS gekoppelt bleiben

## 1. Frontend auf Vercel vorbereiten

In Vercel fuer das Projekt:

1. Repository importieren
2. **Root Directory** auf `frontend` setzen
3. Framework `Next.js` automatisch erkennen lassen
4. Diese ENV setzen:

```env
BACKEND_URL=https://api.gridcheck.de
NEXT_PUBLIC_API_BASE=/api/backend
NEXT_PUBLIC_APP_NAME=GridCheck
NEXT_PUBLIC_APP_VERSION=0.1.0
NEXT_PUBLIC_MAPBOX_TOKEN=
NEXT_PUBLIC_MAPBOX_STYLE_ID=mapbox/dark-v11
```

Hinweise:

- `BACKEND_URL` muss eine absolute `https://...`-URL sein
- in Vercel bricht der Build **nicht** ab, wenn `BACKEND_URL` fehlt: `frontend/next.config.mjs` (Z. 12-19) warnt nur per `console.warn` und faellt still auf einen hart verdrahteten Prod-Host zurueck. Nur ein gesetzter, aber falsch formatierter Wert bricht den Build ab (Guards in Z. 21, 30, 36). Offener Entscheidungspunkt: Punkt 6 in `docs/PROJECT_STATUS.md`
- `NEXT_PUBLIC_API_BASE` bleibt fuer den MVP auf `/api/backend`, damit der Browser immer nur gegen denselben Origin spricht

## 2. Backend separat deployen

Das Backend kann auf Railway oder jedem anderen Host mit oeffentlicher HTTPS-URL laufen. Wichtig ist nur:

- Root Directory bzw. Startpfad auf `backend`
- Start-Command: `uvicorn main:app --host 0.0.0.0 --port ${PORT}`
- Healthcheck: `GET /health`
- PostgreSQL per `DATABASE_URL`
- keine Auto-Migrationen beim App-Start

### Backend-ENV fuer Staging / Preview

```env
APP_ENV=staging
APP_VERSION=v0.1.0-rc
DATABASE_URL=<postgres-url>
CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$
JWT_SECRET=<32+ zufaellige Zeichen>
JWT_REFRESH_SECRET=<32+ andere zufaellige Zeichen>
TRUSTED_HOSTS=*.up.railway.app,*.vercel.app,localhost,127.0.0.1
AUTO_CREATE_SCHEMA=false
ENABLE_LEGACY_ROUTES=false
LOG_LEVEL=INFO
PROJECT_UPLOAD_DIR=/var/lib/gridcheck/uploads
SITE_MARKER_UPLOAD_DIR=/var/lib/gridcheck/uploads/site_markers
```

### Backend-ENV fuer Produktion

```env
APP_ENV=prod
APP_VERSION=v1.0.0
DATABASE_URL=<postgres-url>
CORS_ORIGINS=https://app.gridcheck.de
JWT_SECRET=<32+ zufaellige Zeichen>
JWT_REFRESH_SECRET=<32+ andere zufaellige Zeichen>
TRUSTED_HOSTS=app.gridcheck.de,api.gridcheck.de
AUTO_CREATE_SCHEMA=false
LOG_LEVEL=INFO
PROJECT_UPLOAD_DIR=/var/lib/gridcheck/uploads
SITE_MARKER_UPLOAD_DIR=/var/lib/gridcheck/uploads/site_markers
```

Wichtig:

- `CORS_ORIGINS` **oder** `CORS_ORIGIN_REGEX` setzen
- bei Vercel Preview-Deploys ist der Regex-Weg am einfachsten
- `TRUSTED_HOSTS` bezieht sich auf die oeffentlichen Hosts, unter denen Requests am Backend ankommen
- Upload-Verzeichnisse duerfen in staging/prod nicht auf eine ephemere Container-FS zeigen; fuer mehr als eine Instanz braucht ihr ein Shared Volume oder einen Objekt-Storage-Pfad hinter einem Mount/Gateway
- Stripe-Variablen entweder komplett leer lassen oder als vollstaendiges Buendel setzen

## 3. Migrationen separat ausfuehren

Nach dem ersten erfolgreichen Backend-Deploy einmalig:

```powershell
cd C:\Users\andre\gridcheck\backend
python -m alembic upgrade head
```

Wenn dein Host dafuer einen One-off-Job, Release Command oder eine Konsole anbietet, denselben Befehl dort ausfuehren. Wichtig bleibt: keine Migrationen still im normalen Web-Start.

## 4. Verifikation nach Deploy

Nach dem Cutover pruefen:

1. `https://<backend-host>/health`
2. `https://<frontend-host>`
3. `https://<frontend-host>/api-test`
4. Login, ein einfacher API-Request und mindestens ein Upload-Flow gegen die produktive Konfiguration

## 5. Android / PWA

1. Auf dem Android-Geraet `https://<frontend-host>` in Chrome oeffnen
2. Kurz warten, bis Manifest und Service Worker geladen sind
3. Im Chrome-Menue `App installieren` oder `Zum Startbildschirm hinzufuegen` waehlen
4. GridCheck startet danach im Standalone-Modus wie eine App
