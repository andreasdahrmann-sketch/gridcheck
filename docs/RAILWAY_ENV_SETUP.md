# Railway Production ENV Setup — Go-Live Anleitung

Diese Anleitung fuehrt den Backend-Service auf Railway in einen produktionsreifen Zustand. Zielgruppe: ein Mensch mit Railway-/Vercel-UI-Zugriff. Keine Code-Aenderungen noetig — nur ENV setzen, Migration laufen lassen, Smoke pruefen.

Kanonische Quellen (gelten bei Konflikt):

- `.cursor/rules/04-deployment.mdc` — Pflicht-ENV-Liste
- `backend/core/config.py` — was die App wirklich liest (fail-fast)
- `backend/railway.toml` — Start- und Release-Command auf Railway
- `DECISIONS.md` (ADR-007ff.) — Stack, Stripe Testmode, Alembic-only

---

## 1. Pflicht-Variablen (Backend / Railway)

Pruefe diese Liste vor jedem Prod-Deploy. „Pflicht" = `backend/core/config.py` bricht beim Boot ab, wenn fehlt.

| Variable | Pflicht (prod) | Beispielwert | Geheim? | Hinweis |
|---|---|---|---|---|
| `APP_ENV` | ja | `prod` | nein | Schaltet fail-fast + `database`-Feld in `/health` an. |
| `APP_VERSION` | empfohlen | `v0.1.0` | nein | Aus Git-Tag setzen, landet im Audit-Log und in `/health`. |
| `DATABASE_URL` | ja | `postgresql://user:pass@host:5432/db` | **ja** | Von Railway-Postgres-Service via „Reference" verlinken; `postgres://` wird automatisch zu `postgresql://`. |
| `JWT_SECRET` | ja | 64 Hex-Zeichen | **ja** | Min. 32 Zeichen. Generierung siehe §2. |
| `JWT_REFRESH_SECRET` | ja | 64 Hex-Zeichen | **ja** | **Anderer** Zufallswert als `JWT_SECRET`. |
| `CORS_ORIGINS` | ja* | `https://gridcheck.vercel.app` | nein | * Mindestens eines von `CORS_ORIGINS` oder `CORS_ORIGIN_REGEX`. |
| `CORS_ORIGIN_REGEX` | optional | `^https://[a-z0-9-]+\.vercel\.app$` | nein | Praktisch fuer Vercel-Preview-Deploys. Muss gueltiger Regex sein. |
| `TRUSTED_HOSTS` | empfohlen | `*.up.railway.app,*.vercel.app` | nein | CSV, ohne Spaces. Ohne Wert: nur `localhost,127.0.0.1`. |
| `LOG_LEVEL` | nein | `INFO` | nein | `INFO` in Prod, `DEBUG` nur fuer kurzes Troubleshooting. |
| `REDIS_URL` | nein | `redis://...` | bei Auth ja | Wenn nicht gesetzt: kein Redis-Backed Rate-Limit. |
| `ENABLE_LEGACY_ROUTES` | nein | leer | nein | Default in `prod`: aus. Nicht setzen, ausser bewusster Rollback-Schritt. |
| `AUTH_ACCESS_COOKIE` | nein | `gridcheck_access` | nein | Default ok. |
| `AUTH_REFRESH_COOKIE` | nein | `gridcheck_refresh` | nein | Default ok. |
| `AUTH_CSRF_COOKIE` | nein | `gridcheck_csrf` | nein | Default ok. |
| `FREE_CHECKS_LIMIT` | nein | `3` | nein | Integer >= 0. |
| `AUTO_CREATE_SCHEMA` | **muss leer/false** | — | nein | `true` ist verboten (ADR-010). Schema nur via Alembic. |
| `SENTRY_DSN` | empfohlen | `https://...@sentry.io/...` | **ja** | Aktiviert Error-Tracking (`backend/core/monitoring.py`). Ohne DSN = aus. |
| `PROJECT_UPLOAD_DIR` | bei Projekt-Uploads | `/data/uploads` | nein | Persistent Volume noetig — Container-FS ist ephemer. |
| `SITE_MARKER_UPLOAD_DIR` | bei Site-Markern | `/data/uploads/site_markers` | nein | Wie oben. |
| `PASSWORD_RESET_BASE_URL` | bei Passwort-Reset | `https://gridcheck.vercel.app` | nein | Origin, kein Pfad. |
| `PASSWORD_RESET_TTL_MIN` | nein | `60` | nein | Minuten. |
| `RESEND_API_KEY` / `EMAIL_FROM` | bei Versand | `re_...` / `noreply@gridcheck.de` | **ja** | Ohne Key: keine Mails (kein Crash). |
| `CONTACT_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` / `CONTACT_TO_EMAIL` | bei Kontaktformular | echte SMTP-Werte | **ja** | Platzhalter `smtp.example.com` = deaktiviert. |

### Billing-Schalter (Hide-Switch)

`BILLING_ENABLED` schaltet den gesamten Billing-Pfad an/aus. Default = `false`, damit die App auch ohne Stripe live gehen kann. Der Admin-Bypass (`User.role == "admin"`) ist davon nicht betroffen.

| Variable | Beispielwert | Wirkung |
|---|---|---|
| `BILLING_ENABLED` | `false` (Default) | `/api/v1/billing/*` antwortet 503 `BILLING_DISABLED` fuer Nicht-Admins. Stripe-Webhook bleibt erreichbar (200) und ignoriert Events mit Audit-Log `webhook_received_while_disabled`. Frontend versteckt Pricing-/Settings-Billing-UI. |
| `BILLING_ENABLED` | `true` | Stripe-Pfad aktiv (vorausgesetzt die `STRIPE_*`-Pflichtgruppe ist vollstaendig). |

Frontend-Spiegel (Vercel): `NEXT_PUBLIC_BILLING_ENABLED=false|true` als Build-Variable in **Production** und **Preview** setzen. Der Wert wird zur Build-Zeit eingebettet — nach Aenderung **Redeploy** ausloesen.

> Fuer ein „echtes Live" mit Stripe muessen **beide** Schalter (`BILLING_ENABLED` Backend + `NEXT_PUBLIC_BILLING_ENABLED` Frontend) auf `true` stehen UND die Stripe-Pflichtgruppe (siehe unten) komplett gesetzt sein.

### Stripe (optional, aber „alles oder nichts")

Sobald **eine** Stripe-Variable gesetzt ist, validiert `config.py` die komplette Gruppe — fehlende Werte fuehren zum Boot-Abbruch.

| Variable | Beispielwert (Prod) | Hinweis |
|---|---|---|
| `STRIPE_SECRET_KEY` | `sk_live_...` | In `staging`: `sk_test_...`. |
| `STRIPE_PUBLISHABLE_KEY` | `pk_live_...` | Analog. |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | |
| `STRIPE_PRICE_BASIC_ID` | `price_...` | |
| `STRIPE_PRICE_PREMIUM_ID` | `price_...` | |
| `STRIPE_PRICE_PROFESSIONAL_ID` | `price_...` | |
| `STRIPE_PRICE_PRO_LICENSE_ID` | `price_...` | |
| `STRIPE_PRICE_EXPRESS_ID` | `price_...` | optional, aber wenn gesetzt: Prefix `price_`. |
| `STRIPE_CHECKOUT_SUCCESS_URL` | `https://gridcheck.vercel.app/settings?billing=success` | absolute https-URL. |
| `STRIPE_CHECKOUT_CANCEL_URL` | `https://gridcheck.vercel.app/settings?billing=cancel` | analog. |
| `STRIPE_PORTAL_RETURN_URL` | `https://gridcheck.vercel.app/settings` | analog. |

> Hinweis: `JWT_ACCESS_TTL_MIN`, `JWT_REFRESH_TTL_DAYS`, `NORM_VERSION` sind in `.cursor/rules/04-deployment.mdc` gelistet, werden aber **derzeit nicht** von `backend/core/config.py` gelesen. Setzen schadet nicht; weglassen aktuell ohne Effekt. Konflikt-Klaerung gehoert in `DECISIONS.md` (siehe §8).

---

## 2. JWT-Secrets erzeugen (PowerShell, kryptographisch sicher)

Niemals committen. Niemals in Code/Logs einfuegen. **Direkt** in der Railway-UI eintragen.

```powershell
# Zwei voneinander unabhaengige 64-Hex-Werte (= 32 Bytes Entropie) erzeugen.
function New-HexSecret {
    param([int]$Bytes = 32)
    $buf = New-Object 'byte[]' $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buf)
    ($buf | ForEach-Object { '{0:x2}' -f $_ }) -join ''
}

"JWT_SECRET=          $(New-HexSecret)"
"JWT_REFRESH_SECRET=  $(New-HexSecret)"
```

Pruefe vor dem Eintippen, dass beide Werte **verschieden** sind und jeweils **64 Hex-Zeichen** lang.

- Eintragen: Railway → Service `backend` → **Variables** → `+ New Variable` → Name + Value einfuegen → **Save**.
- Auf gar keinen Fall in `.env`, Repo-Files, Chat, Tickets oder Screenshots verewigen.

---

## 3. Reihenfolge fuer das Go-Live-Deploy

Schritt fuer Schritt — `>2 min` Hang? STOP, Railway-Logs lesen, dann erst weiter.

### (a) ENV in Railway setzen

1. Railway → Projekt `gridcheck` → Service `backend` → **Variables**.
2. Werte aus Tabelle §1 eintragen (Pflicht zuerst).
3. **Deploys → Redeploy** (oder Railway triggert automatisch beim Speichern der Vars).

### (b) Postgres-Migration

`backend/railway.toml` hat sowohl `releaseCommand = "python -m alembic upgrade head"` als auch einen Start-Fallback `python scripts/ensure_migrations.py`. In der Praxis fuehrt Railway den `releaseCommand` nicht immer vor `startCommand` aus — daher der Fallback.

**Erwartet**: Deploy laeuft durch, `/health` antwortet `200` mit `database: "ok"`.

**Wenn Schema fehlt** (Symptom: Register → `HTTP 503`):

1. Railway → Service `backend` → **Shell** (oben rechts „Connect → Shell").
2. Manuell triggern:

```bash
python -m alembic current
python -m alembic upgrade head
python -m alembic current   # muss head zeigen
```

Sobald `current` auf head zeigt, **Restart** des Services.

### (c) Healthcheck validieren

```powershell
Invoke-WebRequest -Uri "https://gridcheck-production.up.railway.app/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

Erwartet (gekuerzt): `{"status":"ok","version":"...","env":"prod","database":"ok"}`.

Mit `curl`:

```bash
curl -fsS https://gridcheck-production.up.railway.app/health
```

Fehlt das Feld `database`: `APP_ENV` ist nicht `prod`. Setzen und redeploy.

### (d) Smoke-Test gegen Frontend + API

```powershell
cd C:\Users\andre\gridcheck\backend
python scripts\smoke_go_live.py `
  --base-url https://gridcheck-production.up.railway.app `
  --frontend-url https://gridcheck.vercel.app
```

Erwartetes Endergebnis: `Alle Smoke-Checks bestanden.` (Exit-Code 0).

Mit Login-Probe (deckt Billing/Analyze/History/PDF):

```powershell
python scripts\smoke_go_live.py `
  --base-url https://gridcheck-production.up.railway.app `
  --frontend-url https://gridcheck.vercel.app `
  --email smoke-user@gridcheck.de `
  --password "<Passwort>"
```

> Hinweis: Das Skript heisst `backend/scripts/smoke_go_live.py` (nicht `scripts/smoke_go_live.py`). CLI-Flag ist `--base-url`, nicht `--api-url`.

---

## 4. Vercel-Settings (Frontend, Production + Preview)

Vercel → Project `gridcheck` → **Settings → Environment Variables**. Beide Scopes (**Production** und **Preview**) muessen `BACKEND_URL` haben, sonst schlagen Login/Register im Browser fehl.

| Name | Value | Scope |
|---|---|---|
| `BACKEND_URL` | `https://gridcheck-production.up.railway.app` (nur Origin, **ohne** `/api/v1`) | Production |
| `BACKEND_URL` | `https://gridcheck-production.up.railway.app` (gleicher Wert oder Staging-URL falls vorhanden) | Preview |

Nach dem Setzen: **Deployments → Latest → Redeploy** (Production), bzw. neuer Preview-Build.

Kontrolle:

```powershell
Invoke-WebRequest -Uri "https://gridcheck.vercel.app/api/backend/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

Erwartet: identischer JSON-Body wie direkter `/health`-Aufruf.

---

## 5. Notfall-Rollback

Drei Pfade, je nach Fehlerklasse.

### A. Letztes Deploy in Railway zuruecksetzen

1. Railway → Service `backend` → **Deployments**.
2. Letzten gruenen Deploy auswaehlen → `...` → **Redeploy**.
3. Variablen-Aenderung der letzten halben Stunde rueckgaengig machen (wenn ENV-Ursache).

### B. Letzten Code-Commit rueckabwickeln

Falls eine Code-Aenderung die Ursache ist (z. B. Migrations-Fehler):

```powershell
git revert <commit-sha>
git push origin main
```

Railway triggert automatisch neuen Deploy mit dem revert.

### C. Manueller Alembic-Downgrade (nur Notfall)

Schema-Rueckabwicklung pro Revision (siehe `DECISIONS.md` 2026-05-13 / ADR-010):

```bash
python -m alembic downgrade -1
```

Vorher Postgres-Snapshot ziehen (Railway → Postgres → **Backups → Manual Snapshot**). Keine Massen-Downgrades ohne Backup.

---

## 6. Lokale ENV-Validierung vor Deploy

Optional, aber empfohlen:

```powershell
cd C:\Users\andre\gridcheck\backend
copy .env.staging.example .env.prod.example
# Werte (DATABASE_URL, JWT_*, CORS) in .env.prod.example eintragen.
python scripts\validate_env.py --env-file .env.prod.example --expect-prod
```

`.env.prod.example` ist via `.gitignore` ausgeschlossen — bleibt lokal.

---

## 7. Stripe / Sentry / SMTP — Reihenfolge

1. **Sentry zuerst** (`SENTRY_DSN`): Fehler im Go-Live sichtbar machen.
2. **Stripe Testmode** in `staging` (siehe `docs/STRIPE_TEST_SETUP.md` falls vorhanden) — niemals direkt Live-Keys ohne Testmode-Lauf.
3. **Stripe Live** erst, wenn Checkout + Webhook in Testmode gruen.
4. **SMTP / Resend** zuletzt — Versand-Fehler crashen die App nicht, blockieren aber Onboarding-Mails.

---

## 8. Konflikte mit `.cursor/rules/04-deployment.mdc`

Stand heute liest `backend/core/config.py` folgende in Rule 04 gelistete Variablen **nicht**:

- `JWT_ACCESS_TTL_MIN`
- `JWT_REFRESH_TTL_DAYS`
- `NORM_VERSION`

Bevor diese in Prod gesetzt werden, sollte eine Entscheidung in `DECISIONS.md` festgehalten werden (entweder Rule 04 anpassen oder die Werte tatsaechlich in `config.py` einlesen). Bis dahin: weglassen.

---

## 9. Verifikations-Checkliste (Kurzfassung)

- [ ] `APP_ENV=prod` in Railway gesetzt
- [ ] `DATABASE_URL` per Reference von Postgres-Service
- [ ] `JWT_SECRET` + `JWT_REFRESH_SECRET` (≠) je 64 Hex
- [ ] `CORS_ORIGINS` und/oder `CORS_ORIGIN_REGEX`
- [ ] `TRUSTED_HOSTS` mit `*.up.railway.app,*.vercel.app`
- [ ] `alembic current` zeigt head
- [ ] `/health` liefert `database: "ok"`
- [ ] `smoke_go_live.py` exit-code 0
- [ ] Vercel `BACKEND_URL` in Production + Preview
- [ ] Sentry DSN gesetzt (oder bewusst leer)
- [ ] Stripe nur, wenn vollstaendig konfigurierbar
