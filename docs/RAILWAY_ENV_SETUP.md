# Railway / Backend ENV — Auth, Billing, Kontakt

Pflicht fuer **Register/Login** in Prod: `DATABASE_URL`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, CORS, `TRUSTED_HOSTS`, Migrationen.

Billing und Kontaktformular sind **optional** (leere Stripe/SMTP = Feature deaktiviert, kein Crash).

## 1. JWT-Secrets erzeugen (PowerShell)

```powershell
# Zwei verschiedene Zufallswerte (je 32+ Zeichen)
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
```

In Railway → Backend-Service → **Variables** eintragen:

| Variable | Wert |
|----------|------|
| `JWT_SECRET` | erster Zufallswert |
| `JWT_REFRESH_SECRET` | zweiter Zufallswert (≠ erster) |
| `DATABASE_URL` | von Postgres-Service verlinken |
| `APP_ENV` | `prod` |
| `CORS_ORIGIN_REGEX` | `^https://[a-z0-9-]+\.vercel\.app$` |
| `CORS_ORIGINS` | `https://gridcheck.vercel.app` (oder `https://app.gridcheck.de`) |
| `TRUSTED_HOSTS` | `*.up.railway.app,*.vercel.app` |

## 2. Migrationen (einmalig)

Railway Shell:

```bash
cd backend
alembic upgrade head
```

Ohne Migration: Register → **HTTP 503** (Datenbank/Schema).

## 3. Validierung lokal

```powershell
cd backend
copy .env.prod.example .env
# JWT_* in .env setzen
python scripts/validate_env.py --expect-prod
```

## 4. Stripe (optional)

Siehe [STRIPE_TEST_SETUP.md](./STRIPE_TEST_SETUP.md). Ohne Stripe: `checkout_enabled=false`, Rest der App laeuft.

## 5. SMTP (optional)

Kontaktformular nur mit echten `CONTACT_SMTP_*`. Platzhalter `smtp.example.com` = deaktiviert.
