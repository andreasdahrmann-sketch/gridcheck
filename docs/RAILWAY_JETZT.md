# Railway — Registrierung/Login JETZT (Checkliste)

## Backend-Service `gridcheck` — diese Variables MÜSSEN gesetzt sein

| Variable | Wert |
|----------|------|
| `DATABASE_URL` | **Reference** → Postgres → `DATABASE_URL` (nicht `Postgres` umbenennen!) |
| `JWT_SECRET` | min. 32 Zeichen Zufall |
| `JWT_REFRESH_SECRET` | anderer Wert, min. 32 Zeichen |
| `APP_ENV` | `prod` |
| `CORS_ORIGINS` | `https://gridcheck.vercel.app` |
| `CORS_ORIGIN_REGEX` | `^https://[a-z0-9-]+\.vercel\.app$` |
| `TRUSTED_HOSTS` | `*` (Railway-Healthchecks nutzen interne Hosts; restriktive Listen führen zu Deploy-FAIL mit HTTP 400 auf `/health`) |

Ohne `JWT_SECRET` / `JWT_REFRESH_SECRET` liefert **Login** HTTP **503** mit `AUTH_JWT_NOT_CONFIGURED` (kein 500 mehr seit Commit `fix: return 503 when JWT secrets missing on login`).

Secrets per CLI setzen (Beispiel):

```powershell
cd C:\Users\andre\gridcheck
railway link -p proud-spirit -s gridcheck -e production
$jwt1 = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
$jwt2 = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
railway variables set "JWT_SECRET=$jwt1" "JWT_REFRESH_SECRET=$jwt2" "APP_ENV=prod" "CORS_ORIGINS=https://gridcheck.vercel.app" "CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$" "TRUSTED_HOSTS=*"
```

Danach Deploy abwarten (`railway deployment list`) und Login testen.

## Admin-Login (`admin@gridcheck.de`)

Oeffentliche Registrierung als Admin ist gesperrt. Fehlt der Nutzer in der DB → Login **401** `LOGIN_INVALID`.

Einmalig vorprovisionieren (z. B. `Admin2026!` — min. 8 Zeichen + Komplexitaet):

```powershell
$env:ADMIN_PASSWORD = "Admin2026!"
railway run python scripts/create_admin_user.py --email admin@gridcheck.de --password-env ADMIN_PASSWORD
```

Details: `docs/ADMIN_USER.md`

## Falls Registrierung `DATABASE_SCHEMA_MISSING` meldet

Ursache oft: `alembic stamp head` auf alter DB (Alembic sagt „head“, Spalte heißt noch `hashed_password`).

**Einmalig reparieren** (löscht alle Daten in `public` — nur für leere Test-DB):

```powershell
cd backend
$env:DATABASE_URL="postgresql+psycopg2://USER:PASS@HOST:PORT/railway"  # DATABASE_PUBLIC_URL vom Postgres-Service
$env:ALLOW_DB_RESET="1"
python scripts/repair_prod_schema.py
```

Danach Register-Test wie unten.

## Nach Git-Push (startCommand mit Migrationen)

Railway deployt neu. Im **Deploy-Log** muss stehen:

```
alembic upgrade head: OK
```

oder `stamping head`.

## Test (PowerShell)

```powershell
'{"email":"neu@example.com","password":"TestPasswort2026!","role":"projektierer"}' | Out-File -Encoding ascii body.json
curl.exe -X POST "https://gridcheck-production.up.railway.app/api/v1/auth/register" -H "Content-Type: application/json" --data-binary "@body.json"
```

Erwartung: JSON mit `id`, `email`, `role` — **kein** `DATABASE_UNAVAILABLE`.

## Vercel

```
BACKEND_URL=https://gridcheck-production.up.railway.app
```

Dann **Redeploy** → https://gridcheck.vercel.app/register

Passwort: min. **12** Zeichen, z. B. `TestPasswort2026!`
