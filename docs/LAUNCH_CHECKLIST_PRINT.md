# GridCheck — Go-Live Checkliste (Druckversion)

Stand: 2026-06-14. Eine Seite. Reihenfolge strikt einhalten. Details: `docs/RAILWAY_ENV_SETUP.md`.

| # | Schritt | Befehl / UI-Pfad | Erwartetes Resultat |
|---|---|---|---|
| 1 | JWT-Secrets erzeugen (lokal, PowerShell) | `function New-HexSecret { $b=New-Object byte[] 32; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); ($b\|%{'{0:x2}' -f $_}) -join '' }; New-HexSecret; New-HexSecret` | Zwei verschiedene 64-Hex-Strings. Nicht committen. |
| 2 | Backend-ENV in Railway setzen | Railway → Service `backend` → **Variables**: `APP_ENV=prod`, `DATABASE_URL` (Reference auf Postgres), `JWT_SECRET`, `JWT_REFRESH_SECRET`, `CORS_ORIGINS=https://gridcheck.vercel.app`, `CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$`, `TRUSTED_HOSTS=*.up.railway.app,*.vercel.app`, `LOG_LEVEL=INFO` | Alle Variablen sichtbar; Deploy startet automatisch. |
| 3 | Backend-Deploy abwarten | Railway → Service `backend` → **Deployments → Latest** | Status: **Active**. Logs: kein `RuntimeError: Missing required env var`. |
| 4 | Alembic-Migration sicherstellen | Railway → Service `backend` → **Shell**: `python -m alembic current` (falls nicht head: `python -m alembic upgrade head`) | Output endet auf `head`. |
| 5 | Healthcheck Backend | `curl -fsS https://gridcheck-production.up.railway.app/health` | `{"status":"ok","version":"…","env":"prod","database":"ok"}`. |
| 6 | Vercel `BACKEND_URL` setzen | Vercel → Project `gridcheck` → **Settings → Environment Variables** → `BACKEND_URL=https://gridcheck-production.up.railway.app` fuer **Production** UND **Preview**. | Beide Scopes zeigen den Wert. |
| 7 | Vercel-Redeploy | Vercel → **Deployments → Latest → Redeploy** (Production) | Build gruen, Domain aktualisiert. |
| 8 | Healthcheck via Frontend-Proxy | `curl -fsS https://gridcheck.vercel.app/api/backend/health` | identischer JSON wie Schritt 5. |
| 9 | Smoke-Test (ohne Login) | `cd C:\Users\andre\gridcheck\backend; python scripts\smoke_go_live.py --base-url https://gridcheck-production.up.railway.app --frontend-url https://gridcheck.vercel.app` | Zeile `Alle Smoke-Checks bestanden.`, Exit-Code 0. |
| 10 | Smoke-Test (mit Login, deckt Analyze + PDF) | Wie Schritt 9 + `--email smoke-user@gridcheck.de --password '<pw>'` | Alle Checks `[OK]`, `POST /api/v1/analyze` und `POST /api/v2/reports/projektierer?format=pdf` gruen. |
| 11 | Stripe-Entscheidung | Entweder **gar nicht** setzen (Billing deaktiviert) **oder** komplett: alle `STRIPE_*` aus `RAILWAY_ENV_SETUP.md` §1. Niemals teilweise. | Boot-Log frei von `Stripe ist nur teilweise konfiguriert`. |
| 12 | Sentry live schalten | Railway → Variable `SENTRY_DSN=<DSN>` setzen → Redeploy. | Boot-Log: kein Sentry-Init-Error. Testfehler im Sentry-Dashboard sichtbar. |
| 13 | Optional: Custom Domain (DNS) | Vercel → **Domains** → `app.gridcheck.de` hinzufuegen; Railway → **Settings → Domains** → `api.gridcheck.de`. DNS-Eintraege gemaess `docs/DNS_APP_API.md`. | Beide Domains zeigen gruenen Status. |
| 14 | Finaler Login-Test (Browser) | `https://gridcheck.vercel.app/register` → Account anlegen → Login → Dashboard | Login funktioniert, kein „Backend nicht erreichbar". |
| 15 | Rollback-Plan dokumentieren | Letzten Deploy-Hash + DB-Snapshot-ID notieren. Rollback-Pfad: Railway **Deployments → letzter gruener Deploy → Redeploy** ODER `git revert <sha> && git push`. | Notiz in Tickets/Runbook. |

**Stopp-Kriterien**: Schritt 5/8/9/14 rot → Schritte 11–15 nicht starten. Erst Root-Cause, dann weiter.

**Register-Probe HTTP-Codes** (aus Smoke-Skript): `422`/`400` = OK, `409` = Mail existiert (OK), `503` = DB/Migration fehlt → zurueck zu Schritt 4.
