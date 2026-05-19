# Admin-Nutzer (intern vorprovisionieren)

## Hintergrund

- Oeffentliche Registrierung mit `role=admin` ist **gesperrt** (`403 ADMIN_SELF_REGISTRATION_FORBIDDEN`).
- Login liefert bei fehlendem Nutzer oder falschem Passwort **`401 LOGIN_INVALID`** (`"Login fehlgeschlagen"`).
- In Production existiert `admin@gridcheck.de` **nicht automatisch** — einmalig anlegen.

## Passwortpolicy

| Flow | Mindestlaenge |
|------|----------------|
| Login (`POST /api/v1/auth/login`) | 8 Zeichen (Pydantic) |
| Register / Passwort-Aenderung | **12 Zeichen** + Gross/Klein/Zahl/Sonderzeichen |
| Admin-Skript (`create_admin_user.py`) | **8 Zeichen** + Komplexitaet (interner Ops-Weg) |

`Admin2026!` (11 Zeichen) ist fuer Login und Admin-Provisionierung gueltig.

## Einmalig auf Railway (Production)

```powershell
cd C:\Users\andre\gridcheck
railway link -p proud-spirit -s gridcheck -e production

# Passwort nur lokal/als temporaere Variable — nicht committen
$env:ADMIN_EMAIL = "admin@gridcheck.de"
$env:ADMIN_PASSWORD = "Admin2026!"

railway run python scripts/create_admin_user.py --email $env:ADMIN_EMAIL --password-env ADMIN_PASSWORD
```

Bestehenden Nutzer Passwort zuruecksetzen:

```powershell
railway run python scripts/create_admin_user.py --email admin@gridcheck.de --password-env ADMIN_PASSWORD --update-password
```

## Lokal (Docker-Postgres)

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg2://gridcheck:gridcheck_dev_2026@localhost:5433/gridcheck"
$env:ADMIN_PASSWORD = "Admin2026!!"
python scripts/create_admin_user.py
```

## Login pruefen

```powershell
python -c "import urllib.request,json; r=urllib.request.Request('https://gridcheck-production.up.railway.app/api/v1/auth/login', data=json.dumps({'email':'admin@gridcheck.de','password':'Admin2026!'}).encode(), headers={'Content-Type':'application/json'}, method='POST');
import urllib.error
try:
 u=urllib.request.urlopen(r); print('STATUS', u.status)
except urllib.error.HTTPError as e:
 print('STATUS', e.code); print(e.read().decode())"
```

Erwartung nach erfolgreicher Provisionierung: **HTTP 200** mit `access_token` und `refresh_token`.

## Frontend

Vercel-Proxy: `POST /api/backend/api/v1/auth/login` (siehe `frontend/lib/api/auth.ts`).  
Fehlercode `LOGIN_INVALID` → Meldung „E-Mail oder Passwort ist falsch.“ (kein Infrastruktur-Bug).
