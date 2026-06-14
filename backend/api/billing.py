from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_csrf
from core.billing_flags import (
    require_billing_enabled_or_admin,
    require_billing_enabled_public,
)
from db.database import get_db
from db.models import User
from services.billing_service import (
    build_billing_overview,
    create_checkout_session,
    create_portal_session,
    get_checkout_session_status,
    get_public_billing_catalog,
    handle_stripe_webhook,
)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class BillingStatusResponse(BaseModel):
    plan_tier: str
    billing_status: str
    has_active_subscription: bool
    subscription_state: str
    billing_attention: dict | None
    stripe_configured: bool
    customer_portal_available: bool
    has_prepaid_credits: bool
    active_paid_entitlements_count: int
    has_ops_pending: bool
    open_ops_followups_count: int
    billing_state_label: str
    free_checks_limit: int
    free_checks_used: int
    free_checks_remaining: int
    can_run_analysis: bool
    upgrade_required: bool
    current_period_end: str | None
    stripe_customer_id: str | None
    catalog: dict
    recommended_offer_ids: list[str]
    active_entitlements: list[dict]
    entitlement_history: list[dict]
    ops_followups: list[dict]
    recent_billing_events: list[dict]
    stripe_readiness: dict
    analysis_options: list[dict]
    usage_policy: dict


class BillingLinkResponse(BaseModel):
    url: str
    session_id: str | None = None
    offer_id: str | None = None
    offer_name: str | None = None


class BillingCheckoutRequest(BaseModel):
    offer_id: str = "pro_lizenz"


class BillingCheckoutSessionResponse(BaseModel):
    session_id: str | None
    offer_id: str | None = None
    offer_name: str | None = None
    session_status: str | None = None
    payment_status: str | None = None
    synced: bool
    checkout_url: str | None = None
    billing: dict


@router.get("/status", response_model=BillingStatusResponse)
def billing_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _flag: None = Depends(require_billing_enabled_or_admin),
) -> dict:
    return build_billing_overview(db, current_user)


@router.post("/checkout", response_model=BillingLinkResponse)
def billing_checkout(
    req: BillingCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    _flag: None = Depends(require_billing_enabled_or_admin),
) -> dict:
    return create_checkout_session(db, current_user, req.offer_id)


@router.post("/portal", response_model=BillingLinkResponse)
def billing_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    _flag: None = Depends(require_billing_enabled_or_admin),
) -> dict:
    return create_portal_session(db, current_user)


@router.get("/checkout-session", response_model=BillingCheckoutSessionResponse)
def billing_checkout_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _flag: None = Depends(require_billing_enabled_or_admin),
) -> dict:
    return get_checkout_session_status(db, current_user, session_id)


@router.get("/catalog")
def billing_catalog(_flag: None = Depends(require_billing_enabled_public)) -> dict:
    return get_public_billing_catalog()


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    # Webhook bleibt absichtlich erreichbar (kein 503), damit Stripe nicht in einen
    # Retry-Loop faellt, falls der Schalter im laufenden Betrieb umgestellt wird.
    # Der Service entscheidet anhand `settings.billing_enabled`, ob das Event
    # tatsaechlich verarbeitet oder nur audit-loggend ignoriert wird.
    payload = await request.body()
    return handle_stripe_webhook(db, payload, stripe_signature)
