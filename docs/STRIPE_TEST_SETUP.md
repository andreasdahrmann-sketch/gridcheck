# Stripe Checkout — Testmodus einrichten

Ohne gesetzte `STRIPE_*`-Variablen ist **kein Checkout** moeglich (`STRIPE_NOT_CONFIGURED`). Das ist beabsichtigt — kein halb konfigurierter Zahlungsflow.

## Testmodus (Staging / lokale Tests)

1. [Stripe Dashboard](https://dashboard.stripe.com/test/products) → Produkte/Preise anlegen (z. B. Basic, Premium, Professional).
2. Price-IDs kopieren (`price_...`).
3. Developers → API keys → **Test** keys (`sk_test_...`, optional `pk_test_...`).
4. Developers → Webhooks → Endpoint `https://<BACKEND>/api/v1/billing/webhook` → Signing secret `whsec_...`.

### Railway / `.env`

```env
APP_ENV=staging
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_BASIC_ID=price_...
STRIPE_PRICE_PREMIUM_ID=price_...
STRIPE_PRICE_PROFESSIONAL_ID=price_...
STRIPE_PRICE_PRO_LICENSE_ID=price_...
STRIPE_PRICE_EXPRESS_ID=price_...
STRIPE_CHECKOUT_SUCCESS_URL=https://gridcheck.vercel.app/settings?billing=success
STRIPE_CHECKOUT_CANCEL_URL=https://gridcheck.vercel.app/settings?billing=cancel
STRIPE_PORTAL_RETURN_URL=https://gridcheck.vercel.app/settings
```

**Regel:** Entweder **alle** Pflicht-Stripe-Variablen setzen oder **alle** leer lassen (partielle Konfiguration bricht `load_settings()` in prod ab).

## Pruefen

```bash
cd backend
python scripts/validate_env.py
python scripts/smoke_go_live.py --base-url http://localhost:8000 --email test@example.com --password 'MeinPasswort123!'
```

`GET /api/v1/billing/status` → `stripe_configured: true`, Offers mit `checkout_enabled: true`.

## Live (spaeter)

Nur mit `sk_live_` / `pk_live_` und `APP_ENV=prod`. Siehe `backend/.env.prod.example`.
