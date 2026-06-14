"""Billing-Hide-Schalter: ENV-gesteuerter Guard fuer /api/v1/billing/*.

Ziel:
- Wenn `BILLING_ENABLED=false` (Default): die App geht ohne Stripe live.
  Nicht-Admin-User bekommen 503 auf den Billing-Routen.
- Admin-Bypass bleibt bestehen: User mit `User.role == "admin"` (DB-Truth)
  sehen weiter alle Billing-Endpunkte und Funktionen.
- Stripe-Webhook bleibt erreichbar (kein 503), damit Stripe nicht in einen
  Retry-Loop faellt; der eigentliche Webhook-Handler entscheidet selbst,
  ob Events verarbeitet oder nur audit-loggend ignoriert werden.

Single source of truth fuer den Schalter ist `settings.billing_enabled`
aus `core.config`.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException

from core.auth import get_current_user
from core.config import settings
from db.models import User


def _billing_disabled_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "BILLING_DISABLED",
            "message": "Billing is not yet enabled in this environment.",
            "hint": "Contact support if you need premium access.",
        },
    )


def is_admin_user(user: User | None) -> bool:
    """Server-side truth: only DB role 'admin' grants the unlimited-access bypass."""
    if user is None:
        return False
    return str(getattr(user, "role", "") or "").strip().lower() == "admin"


def require_billing_enabled_or_admin(
    current_user: User = Depends(get_current_user),
) -> None:
    """Guard fuer authentifizierte Billing-Routen.

    Laesst durch wenn `BILLING_ENABLED=true` ODER User Admin ist.
    Sonst HTTP 503 mit Code `BILLING_DISABLED`.
    """
    if settings.billing_enabled:
        return
    if is_admin_user(current_user):
        return
    raise _billing_disabled_error()


def require_billing_enabled_public() -> None:
    """Guard fuer oeffentliche (unauthenticated) Billing-Routen wie /catalog.

    Strikt: bei `BILLING_ENABLED=false` immer HTTP 503, kein Bypass moeglich,
    weil ohne Auth keine Admin-Pruefung stattfinden kann.
    """
    if settings.billing_enabled:
        return
    raise _billing_disabled_error()
