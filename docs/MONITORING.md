# Monitoring & Error Tracking

## Health

- `GET /health` — App-Version und DB-Erreichbarkeit (`APP_ENV=prod` prüft DB).

## Sentry (optional)

Wenn `SENTRY_DSN` gesetzt ist, initialisiert das Backend beim Start Sentry (sofern `sentry-sdk` installiert ist).

```env
SENTRY_DSN=https://...@sentry.io/...
APP_ENV=production
APP_VERSION=v1.2.3
```

Installation (Backend):

```powershell
cd backend
.\.venv\Scripts\pip.exe install sentry-sdk
```

Ohne Paket: Start läuft normal, Sentry wird übersprungen (Log-Hinweis).

Frontend (Vercel): `NEXT_PUBLIC_SENTRY_DSN` — separates SDK-Setup bei Bedarf (noch nicht im Repo verdrahtet).

## Logs

- `LOG_LEVEL=INFO` (prod) / `DEBUG` (dev)
- Strukturierte Security-Events: `log_security_event` (Auth, Rate-Limits)

## Betrieb

| Signal | Aktion |
|--------|--------|
| 5xx-Spike | Railway-Logs, Sentry-Issues |
| 429-Spike | Rate-Limits / Missbrauch prüfen |
| DB 503 | `alembic upgrade head`, `DATABASE_URL` |

## Roadmap

- Alerting (Pager/Slack) an Sentry/Railway-Metriken
- REDIS_URL für verteiltes Rate-Limiting in Multi-Instance-Deploys
