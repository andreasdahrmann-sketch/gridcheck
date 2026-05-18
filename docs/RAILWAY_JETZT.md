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
| `TRUSTED_HOSTS` | `*.up.railway.app,gridcheck-production.up.railway.app,*.vercel.app` |

Ohne `JWT_SECRET` / `JWT_REFRESH_SECRET` startet die App in Prod nicht zuverlässig.

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
