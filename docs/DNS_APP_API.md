# DNS: app.gridcheck.de + api.gridcheck.de

Ohne diese Einträge ist **kein** Login unter den Marketing-Domains möglich (Browser: NXDOMAIN).

## Ziel

| Host | Zeigt auf |
|------|-----------|
| `app.gridcheck.de` | Vercel (Frontend) |
| `api.gridcheck.de` | Railway (Backend) |

## Vercel (Frontend)

1. Vercel → Projekt → **Settings → Domains**
2. **Add** → `app.gridcheck.de`
3. Vercel zeigt DNS-Einträge (meist **CNAME** `app` → `cname.vercel-dns.com` o. ä.)
4. Bei Domain-Registrar (z. B. GoDaddy / domaincontrol) diesen CNAME eintragen
5. Warten (5 Min – 48 h), bis DNS propagiert

## Railway (Backend)

1. Railway → Backend-Service → **Settings → Networking** → **Custom Domain**
2. `api.gridcheck.de` hinzufügen
3. CNAME `api` → von Railway angezeigter Ziel-Host
4. Im Registrar eintragen

## Nach DNS-Aktivierung

### Vercel

```env
BACKEND_URL=https://api.gridcheck.de
```

Redeploy.

### Railway

```env
CORS_ORIGINS=https://app.gridcheck.de
TRUSTED_HOSTS=api.gridcheck.de,app.gridcheck.de,*.up.railway.app
```

Optional `CORS_ORIGIN_REGEX` für Vercel-Previews behalten.

### Prüfen

```powershell
Resolve-DnsName app.gridcheck.de
Resolve-DnsName api.gridcheck.de
.\scripts\go-live-check.ps1 -FrontendUrl "https://app.gridcheck.de" -BackendUrl "https://api.gridcheck.de"
```
