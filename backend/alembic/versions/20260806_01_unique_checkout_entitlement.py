"""unique (checkout_session_id, offer_id) for billing_entitlements

Revision ID: 20260806_01
Revises: 20260614_03
Create Date: 2026-08-06

Begruendung:
- Stripe webhook (`checkout.session.completed`) und Success-Page
  (`GET /billing/checkout-session`) koennen nach Zahlung parallel
  `_sync_checkout_session_completion` ausfuehren.
- Die bisherige Check-then-Act-Logik (`_payment_entitlement_exists` dann
  Insert) ist nicht race-sicher; `checkout_session_id` war nur indexiert,
  nicht unique → doppelte aktive Prepaid-Packs fuer eine Zahlung.
- Partial Unique Index (NULL session ids bleiben fuer Admin-/Manual-Grants
  erlaubt) erzwingt Idempotenz auf DB-Ebene; App fängt IntegrityError ab.

Reversibel: down() entfernt den Unique-Index.
"""

from __future__ import annotations

from alembic import op


revision = "20260806_01"
down_revision = "20260614_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the earliest entitlement per (session, offer); drop race duplicates.
    op.execute(
        """
        DELETE FROM billing_entitlements AS duplicate
        USING billing_entitlements AS keeper
        WHERE duplicate.checkout_session_id IS NOT NULL
          AND duplicate.checkout_session_id = keeper.checkout_session_id
          AND duplicate.offer_id = keeper.offer_id
          AND duplicate.id > keeper.id
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_billing_entitlements_checkout_session_offer
        ON billing_entitlements (checkout_session_id, offer_id)
        WHERE checkout_session_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_billing_entitlements_checkout_session_offer")
