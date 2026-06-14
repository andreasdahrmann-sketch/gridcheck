/**
 * Billing-Hide-Schalter (Frontend-Spiegel zum Backend `BILLING_ENABLED`).
 *
 * Verhalten:
 *   - Default (Variable nicht gesetzt oder anderer Wert): false
 *     → Pricing/Checkout/Settings-Billing werden im Frontend ausgeblendet.
 *     Admins (Backend-Truth: User.role == "admin") bekommen ueber die
 *     vorhandenen Admin-Pfade Zugriff; das Backend ist und bleibt die
 *     Sicherheitsgrenze.
 *   - "true": Billing-UI sichtbar, Backend muss ebenfalls `BILLING_ENABLED=true`
 *     haben, sonst antwortet die API mit 503 BILLING_DISABLED.
 *
 * Wichtig:
 *   - Diese Funktion ist eine UX-Schicht (Hide), keine Sicherheitsgrenze.
 *     Enforcement passiert serverseitig in `core/billing_flags.py` und in
 *     `services/billing_service.py`.
 *   - `process.env.NEXT_PUBLIC_*` wird zur Build-Zeit eingebettet; der Wert
 *     muss in Vercel/Railway als Build-Variable gesetzt sein.
 */
export function isBillingEnabled(): boolean {
  return process.env.NEXT_PUBLIC_BILLING_ENABLED === "true";
}
