# Railway-Backend-URL dauerhaft festhalten

Die **echte** Railway-HTTPS-URL steht **nicht** im Git-Repo (absichtlich). Sie lebt in **Railway** (Networking) und **Vercel** (`BACKEND_URL`). Wenn sie „verschwindet“, ist fast immer die **Vercel-Variable leer** oder ein **neuer Railway-Default-Host** nach Service-Neuanlage — nicht ein Repo-Bug.

---

## 1. URL in Railway finden (kanonische Quelle)

1. [railway.app](https://railway.app) → dein Projekt  
2. Service **backend** (Root Directory: `backend/`)  
3. **Settings** → **Networking**  
4. Unter **Public Networking** / **Domains**: die HTTPS-URL kopieren  
   - Format: `https://<service>.up.railway.app`  
   - **Aktuell (Production, Stand 2026-05-17):** `https://gridcheck-production.up.railway.app`  
   - **Nicht** `:8080` an die öffentliche URL hängen (8080 ist nur der interne Railway-Port).

**Health direkt am Backend prüfen:**

```powershell
Invoke-WebRequest -Uri "https://gridcheck-production.up.railway.app/health" -UseBasicParsing
```

Erwartung: HTTP 200, JSON mit `"status":"ok"`. Mit `APP_ENV=prod` und gültiger `DATABASE_URL` zusätzlich `"database":"ok"`.

---

## 2. URL in Vercel setzen (Production + Preview)

1. [vercel.com](https://vercel.com) → Projekt **gridcheck**  
2. **Settings** → **Environment Variables**  
3. Variable **`BACKEND_URL`** (nicht `NEXT_PUBLIC_API_URL` / `VITE_API_URL`):

| Feld | Wert |
|------|------|
| **Name** | `BACKEND_URL` |
| **Value** | `https://gridcheck-production.up.railway.app` — **nur Origin**, kein `/api`, kein `/api/v1`, kein trailing `/`, **kein** `:8080` |
| **Environments** | **Production** und **Preview** (empfohlen: auch Development, falls Vercel-CLI-Builds) |

4. **Save** → danach **Redeploy** (Deployments → … → Redeploy), sonst nutzt die Live-App noch den letzten Build.

**Build-Regel:** Ohne `BACKEND_URL` bricht der Vercel-Build ab (`next.config.mjs`). Ein leerer Wert in der UI zählt als „fehlt“ — genau das wirkt wie „URL ist weg“.

**Veraltete Variablen entfernen oder ignorieren:**

- `NEXT_PUBLIC_API_URL` — wird im Code **nicht** für Auth/Rewrites genutzt  
- `NEXT_PUBLIC_BACKEND_URL`, `VITE_API_URL` — ebenfalls nicht kanonisch  

Kanonisch: `BACKEND_URL` + Browser-Pfad `/api/backend/*` (Rewrite).

---

## 3. Proxy testen (ohne Railway-URL zu kennen)

```powershell
.\scripts\where-is-my-backend.ps1
```

Oder manuell:

```powershell
Invoke-WebRequest -Uri "https://gridcheck.vercel.app/api/backend/health" -UseBasicParsing
```

- **HTTP 200** + Response-Header `X-Railway-*` → Vercel leitet auf ein **laufendes** Railway-Backend (oft noch alter Build mit gesetzter `BACKEND_URL`).  
- **502 / Build-Fehler** → `BACKEND_URL` in Vercel leer oder falsch → Schritt 1 + 2.

Die Railway-**Hostname** steht **nicht** in den Response-Headern — nur Hinweise (`X-Railway-Edge`, `X-Railway-Request-Id`).

---

## 4. Warum die URL „verschwindet“

| Ursache | Was passiert | Gegenmaßnahme |
|---------|----------------|---------------|
| **Vercel `BACKEND_URL` geleert** | Neuer Deploy schlägt fehl oder Proxy bricht; alte Deployment-URL kann noch kurz funktionieren | Wert in Vercel + Passwortmanager notieren; `vercel env ls` |
| **Nur in `.env.example` / Docs eingetragen** | Beim nächsten Deploy nicht gesetzt | Nie Prod-URL nur in Beispiel-Dateien |
| **Railway-Service neu erstellt** | Neuer `*.up.railway.app`-Host | Custom Domain oder Service-Name stabil halten |
| **`railway-variables.generated.txt` gelöscht** | Datei ist **gitignored**, enthält **keine** URL — nur ENV-Vorlage | URL separat speichern (Passwortmanager) |
| **Preview ≠ Production** | Preview ohne `BACKEND_URL` | Beide Environments in Vercel setzen |
| **`api.gridcheck.de` geplant, DNS fehlt** | NXDOMAIN — kein Ersatz für Railway-Default-URL | Erst DNS, dann `BACKEND_URL=https://api.gridcheck.de` |

---

## 5. Dauerhaft stabil (empfohlen)

### Option A — Custom Domain (beste Dauerlösung)

1. Railway → backend → **Networking** → **Custom Domain** → `api.gridcheck.de`  
2. DNS (CNAME) wie in [DNS_APP_API.md](./DNS_APP_API.md)  
3. Vercel: `BACKEND_URL=https://api.gridcheck.de`  
4. Railway: `TRUSTED_HOSTS=api.gridcheck.de,app.gridcheck.de,*.up.railway.app`

Die URL ändert sich nicht mehr, wenn Railway den internen Default-Host rotiert.

### Option B — Railway-Default-URL + Disziplin

- URL nach jedem Railway-Networking-Check in **Vercel** und **Passwortmanager**  
- **Nicht** in Git committen (rotierende Hosts, keine Secrets im Repo)  
- Nach jeder Änderung: `.\scripts\go-live-check.ps1 -FrontendUrl "https://gridcheck.vercel.app" -BackendUrl "https://gridcheck-production.up.railway.app"`

---

## 6. Checkliste nach „URL weg“

1. Railway → Networking → HTTPS-URL kopieren (aktuell: `https://gridcheck-production.up.railway.app`)  
2. `GET https://gridcheck-production.up.railway.app/health` → 200  
3. Vercel → `BACKEND_URL=https://gridcheck-production.up.railway.app` (Production + Preview)  
4. Redeploy Vercel **gridcheck**  
5. `.\scripts\where-is-my-backend.ps1` → Proxy OK  
6. https://gridcheck.vercel.app/register testen  

Weitere Details: [GO_LIVE_OHNE_DNS.md](./GO_LIVE_OHNE_DNS.md), [LAUNCH.md](./LAUNCH.md).
