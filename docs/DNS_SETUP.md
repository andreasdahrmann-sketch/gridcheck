# DNS-Setup: app.gridcheck.de + api.gridcheck.de

**Ziel:** Marketing-Domains für Frontend (Vercel) und API (Railway) — inkl. CORS, Trusted Hosts und Verifikation.

**Verwandte Dokumente:**

- Kurzreferenz: [DNS_APP_API.md](./DNS_APP_API.md)
- Betrieb ohne Custom-Domain: [GO_LIVE_OHNE_DNS.md](./GO_LIVE_OHNE_DNS.md)
- Auth/Proxy: [DEPLOY_AUTH_FIX.md](./DEPLOY_AUTH_FIX.md)
- Railway-ENV: [RAILWAY_ENV_SETUP.md](./RAILWAY_ENV_SETUP.md)

**Aktueller Stand (laut Projektstatus):** `app.gridcheck.de` / `api.gridcheck.de` oft **NXDOMAIN** — bis DNS propagiert ist, `https://gridcheck.vercel.app` + Railway-URL nutzen.

---

## Übersicht

| Host | Dienst | Plattform |
|------|--------|-----------|
| `app.gridcheck.de` | Frontend (Next.js) | Vercel |
| `api.gridcheck.de` | Backend (FastAPI) | Railway |

```text
Browser → app.gridcheck.de (Vercel)
              ↓ BACKEND_URL / Rewrites
         api.gridcheck.de (Railway) → PostgreSQL
```

---

## Voraussetzungen

- [ ] Domain `gridcheck.de` beim Registrar verwaltbar (DNS-Zone)
- [ ] Vercel-Projekt mit Root Directory **`frontend`**
- [ ] Railway: Backend-Service + PostgreSQL, `alembic upgrade head` ausgeführt
- [ ] JWT-Secrets gesetzt (`JWT_SECRET`, `JWT_REFRESH_SECRET`, je ≥ 32 Zeichen, unterschiedlich)

---

## Schritt 1 — DNS beim Registrar

### 1a) Frontend: `app.gridcheck.de` → Vercel

1. **Vercel** → Projekt → **Settings → Domains**
2. **Add** → `app.gridcheck.de`
3. Vercel zeigt den benötigten Eintrag (typisch):

   | Typ | Name/Host | Ziel |
   |-----|-----------|------|
   | **CNAME** | `app` | `cname.vercel-dns.com` (exakter Wert aus Vercel-Dashboard) |

4. Beim **Domain-Registrar** (z. B. IONOS, GoDaddy, Cloudflare) CNAME eintragen
5. Optional: **APEX** `gridcheck.de` → Vercel (separater A/ALIAS-Eintrag, nur wenn gewünscht)

### 1b) Backend: `api.gridcheck.de` → Railway

1. **Railway** → Backend-Service → **Settings → Networking** → **Custom Domain**
2. `api.gridcheck.de` hinzufügen
3. Railway zeigt CNAME-Ziel (z. B. `*.up.railway.app`-Hostname)
4. Beim Registrar:

   | Typ | Name/Host | Ziel |
   |-----|-----------|------|
   | **CNAME** | `api` | von Railway angezeigter Host |

### 1c) Propagation abwarten

- Typisch **5 Min – 48 h**
- Kein Login unter Custom-Domain, solange **NXDOMAIN** oder falscher CNAME

**Prüfen (PowerShell):**

```powershell
Resolve-DnsName app.gridcheck.de -Type CNAME -ErrorAction SilentlyContinue
Resolve-DnsName api.gridcheck.de -Type CNAME -ErrorAction SilentlyContinue
```

Erwartung: beide liefern einen CNAME (kein „DNS name does not exist“).

---

## Schritt 2 — Vercel (Frontend)

### Environment Variables (Production)

```env
BACKEND_URL=https://api.gridcheck.de
```

**Regeln:**

- Nur **Origin** — kein `/api/v1`-Suffix
- Nur **`https://`**
- Für **Preview** Deployments optional weiterhin Railway-URL oder Preview-Backend

### Domain bestätigen

- Vercel → Domains → Status **Valid** für `app.gridcheck.de`
- **Redeploy** auslösen (Deployments → Redeploy), damit `BACKEND_URL` im Build aktiv ist

---

## Schritt 3 — Railway (Backend)

### Environment Variables (Production)

```env
APP_ENV=prod
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET=<32+ Zeichen>
JWT_REFRESH_SECRET=<32+ Zeichen, ≠ JWT_SECRET>
LOG_LEVEL=INFO

# Custom-Domain aktiv:
CORS_ORIGINS=https://app.gridcheck.de
TRUSTED_HOSTS=api.gridcheck.de,app.gridcheck.de,*.up.railway.app

# Optional: Vercel-Preview-Deployments weiter erlauben
CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$
```

**Hinweise:**

- `CORS_ORIGINS` und `CORS_ORIGIN_REGEX` können parallel gesetzt sein (Backend merged Origins)
- `TRUSTED_HOSTS` schützt vor Host-Header-Angriffen (`TrustedHostMiddleware`)
- Migrationen: `cd backend && alembic upgrade head` (Railway Shell oder Release-Phase)

### Custom Domain bestätigen

- Railway → Networking → `api.gridcheck.de` Status **Active** / Zertifikat bereit

---

## Schritt 4 — Smoke-Tests

### Einzelchecks

```powershell
# Backend direkt
Invoke-WebRequest -Uri "https://api.gridcheck.de/health" -UseBasicParsing

# Frontend-Proxy (Next.js Rewrite)
Invoke-WebRequest -Uri "https://app.gridcheck.de/api/backend/health" -UseBasicParsing
```

Erwartung: HTTP **200**, Body enthält `"status":"ok"`.

### Gesamt-Check (Skript)

```powershell
cd C:\Users\andre\gridcheck
.\scripts\go-live-check.ps1 `
  -FrontendUrl "https://app.gridcheck.de" `
  -BackendUrl "https://api.gridcheck.de"
```

### Python-Smoke (optional)

```powershell
cd backend
python scripts/smoke_go_live.py `
  --base-url https://api.gridcheck.de `
  --frontend-url https://app.gridcheck.de
```

### Manuell im Browser

| URL | Erwartung |
|-----|-----------|
| https://app.gridcheck.de/register | Registrierung mit starkem Passwort (≥ 12 Zeichen, Komplexität) |
| https://app.gridcheck.de/api-test | Health OK |
| https://api.gridcheck.de/health | `{"status":"ok",...}` |

**Register 503:** `DATABASE_URL` oder Migrationen prüfen — siehe [GO_LIVE_OHNE_DNS.md](./GO_LIVE_OHNE_DNS.md).

---

## Schritt 5 — Rollback / Fallback

Wenn DNS noch nicht propagiert:

| Rolle | Fallback-URL |
|-------|----------------|
| Frontend | `https://gridcheck.vercel.app` |
| Backend | `https://gridcheck-production.up.railway.app` |

Vercel `BACKEND_URL` temporär auf Railway-URL setzen, **Redeploy**.

---

## Checkliste (Abnahme)

- [ ] `Resolve-DnsName` für `app` und `api` erfolgreich
- [ ] Vercel Domain **Valid**, SSL aktiv
- [ ] Railway Custom Domain **Active**
- [ ] `BACKEND_URL=https://api.gridcheck.de` + Redeploy
- [ ] Railway: `CORS_ORIGINS`, `TRUSTED_HOSTS` gesetzt
- [ ] `go-live-check.ps1` grün
- [ ] Register/Login unter `app.gridcheck.de` getestet

---

## Troubleshooting

| Symptom | Ursache | Maßnahme |
|---------|---------|----------|
| NXDOMAIN | Kein DNS-Eintrag | CNAME bei Registrar prüfen |
| SSL-Fehler Vercel | Domain nicht verifiziert | Vercel Domains → DNS erneut prüfen |
| 400 Bad Request (Host) | `TRUSTED_HOSTS` fehlt `api.gridcheck.de` | Railway ENV anpassen, redeploy |
| CORS-Fehler im Browser | `CORS_ORIGINS` ohne `https://app.gridcheck.de` | Railway ENV + redeploy |
| 503 Register | DB/Migration | `alembic upgrade head`, `DATABASE_URL` |
| `/api/auth/*` 404 | Alter Deploy | Vercel Redeploy, [DEPLOY_AUTH_FIX.md](./DEPLOY_AUTH_FIX.md) |

---

*Zuletzt aktualisiert: Mai 2026 (PRIO 3 — Sales-Ready)*
