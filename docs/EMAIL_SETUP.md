# E-Mail-Setup (GridCheck)

Transaktionale E-Mails: **Willkommen nach Registrierung** (optional) und **Passwort-Reset**.

## Verhalten nach Umgebung

| Umgebung | Ohne Provider | Mit Provider |
|----------|---------------|--------------|
| `dev` / `test` | Log-Zeile (`email_stub`) | Resend oder SMTP |
| `staging` / `prod` | Warnung, kein Versand | Resend oder SMTP (Pflicht für Reset-Mails) |

## Provider (eine Variante reicht)

### Resend (empfohlen für Railway)

```env
RESEND_API_KEY=re_...
EMAIL_FROM=GridCheck <noreply@gridcheck.de>
```

### SMTP (z. B. Hetzner, Mailgun, Brevo)

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=mailer@example.com
SMTP_PASSWORD=<secret>
EMAIL_FROM=noreply@gridcheck.de
```

Legacy-Alias (Kontaktformular): `CONTACT_SMTP_*` wird weiterhin unterstützt, wenn `SMTP_HOST` leer ist.

## Passwort-Reset

```env
PASSWORD_RESET_BASE_URL=https://app.gridcheck.de
PASSWORD_RESET_TTL_MIN=60
```

Fallback: Ableitung aus `STRIPE_CHECKOUT_SUCCESS_URL` (ohne Query/`/settings`), sonst `http://localhost:3000`.

API:

- `POST /api/v1/auth/forgot-password` — Rate-Limit 5 / 5 Min pro E-Mail
- `POST /api/v1/auth/reset-password` — Token aus E-Mail-Link

## Willkommens-Mail

```env
EMAIL_SEND_WELCOME=true
```

`false` / `0` / `off` deaktiviert die Willkommens-Mail nach Registrierung.

## Lokaler Test

1. Backend ohne SMTP/Resend starten → Logs zeigen `email_stub`.
2. Optional SMTP-Credentials in `backend/.env` setzen.
3. `POST /api/v1/auth/forgot-password` mit bekannter E-Mail; Link in Log oder Postfach.

## Sicherheit

- Keine Secrets im Code oder Git.
- Reset-Tokens nur gehasht in DB (`password_reset_tokens`).
- Antwort auf `forgot-password` verrät nicht, ob die E-Mail existiert.
