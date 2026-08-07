from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import settings
from db.models import AnalysisRun, BillingEntitlement, BillingEvent, GridcheckResultAudit, Project, User, make_checksum
from engine.berechnung import ENGINE_VERSION
from compliance import APP_VERSION_NORMSTAND, get_normen_fuer_spannungsebene
from services.conversion_tracking_service import track_checkout_completed, track_checkout_started

PAID_ACCESS_STATUSES = {"active", "trialing", "past_due"}
SUBSCRIPTION_ANALYSIS_ACCESS_STATUSES = {"active", "trialing"}
PORTAL_ELIGIBLE_STATES = {"active", "trialing", "past_due", "canceled"}
PAYMENT_OFFER_IDS = {"basic_schnellcheck", "premium_pre_check", "professional_anschlussstrategie"}
SUBSCRIPTION_OFFER_IDS = {"pro_lizenz"}
ADDON_OFFER_IDS = {"express_upgrade"}
OPS_OPEN_STATUSES = {"pending_review", "in_progress"}
OPS_TRANSITIONS = {
    "pending_review": {"in_progress"},
    "in_progress": {"completed"},
    "completed": set(),
    "not_required": set(),
}


def _subscription_state(user: User) -> str:
    status = str(user.billing_status or "free")
    if status == "checkout_completed":
        return "checkout_pending"
    if status == "past_due":
        return "past_due"
    if status == "trialing":
        return "trialing"
    if status == "active":
        return "active"
    if status == "canceled":
        return "canceled"
    return "none"


def _billing_attention(user: User) -> dict[str, Any] | None:
    subscription_state = _subscription_state(user)
    if subscription_state == "past_due":
        return {
            "severity": "warning",
            "title": "Zahlung fuer Pro Lizenz offen",
            "message": (
                "Stripe meldet eine offene oder fehlgeschlagene Subscription-Zahlung. "
                "Neue Pro-Analysen sind gesperrt, separat bezahlte One-off-Pakete bleiben weiter nutzbar."
            ),
            "action": "open_portal",
            "cta_label": "Billing Portal oeffnen",
        }
    if subscription_state == "checkout_pending":
        return {
            "severity": "info",
            "title": "Freischaltung wird noch bestaetigt",
            "message": "Checkout wurde erkannt, aber Stripe hat die Subscription noch nicht final als aktiv bestaetigt.",
            "action": "wait",
            "cta_label": "Status beobachten",
        }
    if subscription_state == "canceled":
        return {
            "severity": "warning",
            "title": "Pro Lizenz beendet",
            "message": "Die Subscription ist beendet. Falls Sie reaktivieren moechten, pruefen Sie das Billing Portal oder starten Sie einen neuen Checkout.",
            "action": "open_portal",
            "cta_label": "Portal zur Reaktivierung",
        }
    return None


def _offer_catalog() -> dict[str, list[dict[str, Any]]]:
    offers = [
        {
            "offer_id": "basic_schnellcheck",
            "name": "Basic Schnellcheck",
            "category": "pay_per_use",
            "billing_mode": "payment",
            "price_label": "249 EUR",
            "amount_cents": 24_900,
            "interval": None,
            "tagline": "Schnelle Einordnung vor Antrag und Detailplanung.",
            "summary": "Fuer die erste Netzanschluss-Klarheit mit kompaktem Ergebnisbild.",
            "cta_label": "Basic buchen",
            "checkout_enabled": bool(settings.stripe_secret_key and settings.stripe_price_basic_id),
            "stripe_price_id": settings.stripe_price_basic_id,
            "recommended_for": "Erste Standort- und Pipeline-Sichtung",
            "featured": False,
            "self_serve_unlock": False,
            "visibility": "public",
            "package_scope": "basic",
            "included_credits": 1,
            "report_scope": "basic",
            "usage_bucket": "oneoff",
            "ops_followup_required": False,
            "feature_flags": {
                "hybrid": False,
                "storage": False,
                "environment": False,
                "stakeholder_compare": False,
                "variants": False,
                "visualization": False,
                "express_eligible": False,
            },
        },
        {
            "offer_id": "premium_pre_check",
            "name": "Premium Pre-Check",
            "category": "pay_per_use",
            "billing_mode": "payment",
            "price_label": "749 EUR",
            "amount_cents": 74_900,
            "interval": None,
            "tagline": "Mehr Substanz fuer kritische Vorhaben vor Kapitalbindung.",
            "summary": "Fuer Projekte, bei denen Bedingungen, Engpaesse und Darstellbarkeit frueh sauber aufbereitet werden sollen.",
            "cta_label": "Premium buchen",
            "checkout_enabled": bool(settings.stripe_secret_key and settings.stripe_price_premium_id),
            "stripe_price_id": settings.stripe_price_premium_id,
            "recommended_for": "Anspruchsvollere Projektentscheidungen und Investorenabstimmung",
            "featured": True,
            "self_serve_unlock": False,
            "visibility": "public",
            "package_scope": "premium",
            "included_credits": 1,
            "report_scope": "premium",
            "usage_bucket": "oneoff",
            "ops_followup_required": False,
            "feature_flags": {
                "hybrid": True,
                "storage": True,
                "environment": True,
                "stakeholder_compare": True,
                "variants": False,
                "visualization": False,
                "express_eligible": True,
            },
        },
        {
            "offer_id": "professional_anschlussstrategie",
            "name": "Professional Anschlussstrategie",
            "category": "pay_per_use",
            "billing_mode": "payment",
            "price_label": "1.490 EUR",
            "amount_cents": 149_000,
            "interval": None,
            "tagline": "Strategische Anschlussdarstellung statt nur Ampelbewertung.",
            "summary": "Fuer Vorhaben, bei denen Anschlussstrategie, Bedingungen und naechste Schritte belastbar verdichtet werden muessen.",
            "cta_label": "Professional buchen",
            "checkout_enabled": bool(settings.stripe_secret_key and settings.stripe_price_professional_id),
            "stripe_price_id": settings.stripe_price_professional_id,
            "recommended_for": "Komplexe Projekte vor Antrag, EPC-Start oder IC-Freigabe",
            "featured": False,
            "self_serve_unlock": False,
            "visibility": "public",
            "package_scope": "professional",
            "included_credits": 1,
            "report_scope": "professional",
            "usage_bucket": "oneoff",
            "ops_followup_required": True,
            "feature_flags": {
                "hybrid": True,
                "storage": True,
                "environment": True,
                "stakeholder_compare": True,
                "variants": True,
                "visualization": True,
                "express_eligible": True,
            },
        },
        {
            "offer_id": "pro_lizenz",
            "name": "Pro Lizenz",
            "category": "saas",
            "billing_mode": "subscription",
            "price_label": "ab 1.290 EUR / Monat",
            "amount_cents": 129_000,
            "interval": "month",
            "tagline": "Fuer laufende Projektpipeline und wiederkehrende Checks.",
            "summary": "Oeffentlich sichtbare SaaS-Option fuer Teams, die Netzanschluss-Klarheit fortlaufend in ihrer Pipeline brauchen.",
            "cta_label": "Pro starten",
            "checkout_enabled": bool(settings.stripe_secret_key and settings.stripe_price_pro_license_id),
            "stripe_price_id": settings.stripe_price_pro_license_id,
            "recommended_for": "Wiederkehrende Vorqualifizierung und teamweites Arbeiten",
            "featured": True,
            "self_serve_unlock": True,
            "visibility": "public",
            "package_scope": "premium",
            "included_credits": 20,
            "report_scope": "premium",
            "usage_bucket": "subscription",
            "ops_followup_required": False,
            "feature_flags": {
                "hybrid": True,
                "storage": True,
                "environment": True,
                "stakeholder_compare": True,
                "variants": False,
                "variants_light": True,
                "visualization": True,
                "express_eligible": False,
            },
        },
        {
            "offer_id": "vnb_pilot",
            "name": "VNB Pilot",
            "category": "pilot",
            "billing_mode": "contact",
            "price_label": "auf Anfrage",
            "amount_cents": None,
            "interval": None,
            "tagline": "Pilot fuer Netzbetreiber mit Prozess- und Datenbezug.",
            "summary": "Fuer VNB-nahe Arbeitsweisen, Pilotierung und abgestimmte Rollout-Szenarien.",
            "cta_label": "Pilot anfragen",
            "checkout_enabled": False,
            "stripe_price_id": None,
            "recommended_for": "Netzbetreiber und gemeinsame Pilotphasen",
            "featured": False,
            "self_serve_unlock": False,
            "visibility": "public",
            "package_scope": "pilot",
            "included_credits": None,
            "report_scope": "professional",
            "usage_bucket": "manual",
            "ops_followup_required": True,
            "feature_flags": {
                "hybrid": True,
                "storage": True,
                "environment": True,
                "stakeholder_compare": True,
                "variants": True,
                "visualization": True,
                "express_eligible": False,
            },
        },
    ]
    addons = [
        {
            "offer_id": "express_upgrade",
            "name": "Express",
            "category": "addon",
            "billing_mode": "addon",
            "price_label": "optional",
            "amount_cents": None,
            "interval": None,
            "tagline": "Zeitkritische Bearbeitung als sichtbares Upgrade vorbereitet.",
            "summary": "Im MVP bereits als Zusatzleistung und spaeterer Checkout-Pfad modelliert.",
            "cta_label": "Verfuegbarkeit anfragen",
            "checkout_enabled": bool(settings.stripe_secret_key and settings.stripe_price_express_id),
            "stripe_price_id": settings.stripe_price_express_id,
            "recommended_for": "Zeitkritische Vorhaben und Board-/IC-Termine",
            "featured": False,
            "self_serve_unlock": False,
            "visibility": "public",
            "package_scope": "addon",
            "included_credits": None,
            "report_scope": "none",
            "usage_bucket": "addon",
            "ops_followup_required": True,
            "feature_flags": {"express": True},
        }
    ]
    return {"offers": offers, "addons": addons}


def get_public_billing_catalog() -> dict[str, Any]:
    catalog = _offer_catalog()
    return {
        "headline": "Netzanschluss-Klarheit vor Antrag, Detailplanung und Kapitalbindung.",
        "subheadline": "Vom Schnellcheck bis zur laufenden Projektpipeline: oeffentlich sichtbare MVP-Angebote fuer fruehe Anschlussklarheit.",
        **catalog,
    }


def _offer_lookup(offer_id: str) -> dict[str, Any]:
    catalog = _offer_catalog()
    for collection in (catalog["offers"], catalog["addons"]):
        for offer in collection:
            if offer["offer_id"] == offer_id:
                return offer
    raise HTTPException(
        status_code=404,
        detail={
            "code": "BILLING_OFFER_NOT_FOUND",
            "message": "Angebot nicht gefunden.",
            "hint": "Bitte ein gueltiges Angebot aus dem Pricing-Katalog waehlen.",
        },
    )


def _feature_flags(offer: dict[str, Any]) -> dict[str, bool]:
    value = offer.get("feature_flags")
    return value if isinstance(value, dict) else {}


def _serialize_entitlement(entitlement: BillingEntitlement) -> dict[str, Any]:
    remaining = None
    if entitlement.total_credits is not None:
        remaining = max(0, int(entitlement.total_credits) - int(entitlement.used_credits or 0))
    metadata = {}
    try:
        metadata = json.loads(entitlement.metadata_json or "{}")
    except Exception:
        metadata = {}
    return {
        "id": entitlement.id,
        "offer_id": entitlement.offer_id,
        "offer_category": entitlement.offer_category,
        "package_scope": entitlement.package_scope,
        "status": entitlement.status,
        "source": entitlement.source,
        "total_credits": entitlement.total_credits,
        "used_credits": entitlement.used_credits,
        "remaining_credits": remaining,
        "valid_from": _iso(entitlement.valid_from),
        "valid_until": _iso(entitlement.valid_until),
        "checkout_session_id": entitlement.checkout_session_id,
        "stripe_subscription_id": entitlement.stripe_subscription_id,
        "express_requested": entitlement.express_requested,
        "ops_followup_required": entitlement.ops_followup_required,
        "ops_status": entitlement.ops_status,
        "ops_assignee_user_id": entitlement.ops_assignee_user_id,
        "ops_assignee_email": entitlement.ops_assignee.email if entitlement.ops_assignee else None,
        "ops_assignee_name": entitlement.ops_assignee.full_name if entitlement.ops_assignee else None,
        "ops_assigned_at": _iso(entitlement.ops_assigned_at),
        "ops_started_at": _iso(entitlement.ops_started_at),
        "ops_completed_at": _iso(entitlement.ops_completed_at),
        "ops_last_comment": entitlement.ops_last_comment,
        "metadata": metadata,
    }


def _active_entitlements(db: Session, user: User) -> list[BillingEntitlement]:
    return (
        db.query(BillingEntitlement)
        .filter(
            BillingEntitlement.user_id == user.id,
            BillingEntitlement.status.in_(["active", "ops_pending"]),
        )
        .order_by(BillingEntitlement.created_at.asc(), BillingEntitlement.id.asc())
        .all()
    )


def _remaining_credits(entitlement: BillingEntitlement) -> int | None:
    if entitlement.total_credits is None:
        return None
    return max(0, int(entitlement.total_credits) - int(entitlement.used_credits or 0))


def _entitlement_usable(entitlement: BillingEntitlement) -> bool:
    now = _utcnow()
    if entitlement.status not in {"active", "ops_pending"}:
        return False
    if entitlement.valid_until and entitlement.valid_until < now:
        return False
    remaining = _remaining_credits(entitlement)
    return remaining is None or remaining > 0


def _get_subscription_entitlement(
    db: Session,
    user: User,
    *,
    statuses: set[str] | None = None,
) -> BillingEntitlement | None:
    entitlement_statuses = statuses or {"active"}
    return (
        db.query(BillingEntitlement)
        .filter(
            BillingEntitlement.user_id == user.id,
            BillingEntitlement.offer_id == "pro_lizenz",
            BillingEntitlement.status.in_(sorted(entitlement_statuses)),
        )
        .order_by(BillingEntitlement.updated_at.desc(), BillingEntitlement.id.desc())
        .first()
    )


def _sync_subscription_quota(user: User, entitlement: BillingEntitlement, offer: dict[str, Any]) -> None:
    included = offer.get("included_credits")
    if included is not None and entitlement.total_credits != included:
        entitlement.total_credits = int(included)
    if entitlement.valid_until and user.billing_current_period_end:
        if entitlement.valid_until != user.billing_current_period_end:
            entitlement.valid_until = user.billing_current_period_end
    elif user.billing_current_period_end:
        entitlement.valid_until = user.billing_current_period_end
    entitlement.updated_at = _utcnow()


def _ensure_subscription_entitlement(db: Session, user: User) -> BillingEntitlement | None:
    if user.plan_tier != "pro" or user.billing_status not in PAID_ACCESS_STATUSES:
        return None
    offer = _offer_lookup("pro_lizenz")
    entitlement = _get_subscription_entitlement(db, user)
    if entitlement is None:
        entitlement = BillingEntitlement(
            user_id=user.id,
            offer_id="pro_lizenz",
            offer_category=str(offer["category"]),
            package_scope=str(offer["package_scope"]),
            source="subscription",
            status="active",
            total_credits=int(offer["included_credits"]),
            used_credits=0,
            valid_from=_utcnow(),
            valid_until=user.billing_current_period_end,
            stripe_price_id=user.stripe_price_id,
            stripe_subscription_id=user.stripe_subscription_id,
            metadata_json=_json_text(
                {
                    "report_scope": offer["report_scope"],
                    "feature_flags": _feature_flags(offer),
                    "usage_bucket": offer["usage_bucket"],
                }
            ),
        )
        db.add(entitlement)
        db.flush()
    else:
        _sync_subscription_quota(user, entitlement, offer)
    return entitlement


def _apply_payment_purchase_user_state(
    user: User,
    *,
    offer_id: str,
    stripe_price_id: str | None,
) -> None:
    """Sync user billing fields after a successful one-off Stripe Checkout."""
    if stripe_price_id:
        user.stripe_price_id = stripe_price_id
    if offer_id not in PAYMENT_OFFER_IDS:
        return
    if user.billing_status in PAID_ACCESS_STATUSES:
        return
    offer = _offer_lookup(offer_id)
    scope = str(offer.get("package_scope") or "").strip().lower()
    if scope in {"basic", "premium", "professional"}:
        user.plan_tier = scope
    user.billing_status = "purchased"
    user.updated_at = _utcnow()


def _issue_payment_entitlement(
    db: Session,
    user: User,
    *,
    offer_id: str,
    checkout_session_id: str | None,
    payment_intent_id: str | None,
    stripe_price_id: str | None,
    status: str,
) -> BillingEntitlement:
    offer = _offer_lookup(offer_id)
    express_requested = bool(offer_id == "express_upgrade")
    entitlement = BillingEntitlement(
        user_id=user.id,
        offer_id=offer_id,
        offer_category=str(offer["category"]),
        package_scope=str(offer["package_scope"]),
        source="checkout",
        status=status,
        total_credits=offer.get("included_credits"),
        used_credits=0,
        valid_from=_utcnow(),
        valid_until=user.billing_current_period_end if offer_id == "pro_lizenz" else None,
        checkout_session_id=checkout_session_id,
        stripe_price_id=stripe_price_id,
        stripe_payment_intent_id=payment_intent_id,
        stripe_subscription_id=user.stripe_subscription_id if offer_id == "pro_lizenz" else None,
        express_requested=express_requested,
        ops_followup_required=bool(offer.get("ops_followup_required")),
        ops_status="pending_review" if express_requested or offer.get("ops_followup_required") else "not_required",
        metadata_json=_json_text(
            {
                "report_scope": offer["report_scope"],
                "feature_flags": _feature_flags(offer),
                "usage_bucket": offer["usage_bucket"],
                "cta_label": offer["cta_label"],
            }
        ),
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def _entitlement_for_offer(db: Session, user: User, offer_id: str) -> BillingEntitlement | None:
    rows = (
        db.query(BillingEntitlement)
        .filter(
            BillingEntitlement.user_id == user.id,
            BillingEntitlement.offer_id == offer_id,
        )
        .order_by(BillingEntitlement.created_at.asc(), BillingEntitlement.id.asc())
        .all()
    )
    for entitlement in rows:
        if _entitlement_usable(entitlement):
            return entitlement
    return None


def list_active_entitlements(db: Session, user: User) -> list[dict[str, Any]]:
    _ensure_subscription_entitlement(db, user)
    entitlements = _active_entitlements(db, user)
    if not has_paid_access(user):
        entitlements = [item for item in entitlements if item.offer_id != "pro_lizenz"]
    return [_serialize_entitlement(entitlement) for entitlement in entitlements]


def list_entitlement_history(db: Session, user: User, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        db.query(BillingEntitlement)
        .filter(BillingEntitlement.user_id == user.id)
        .order_by(BillingEntitlement.updated_at.desc(), BillingEntitlement.id.desc())
        .limit(limit)
        .all()
    )
    entitlement_ids = [row.id for row in rows]
    latest_runs: dict[int, tuple[AnalysisRun, str | None]] = {}
    if entitlement_ids:
        run_rows = (
            db.query(AnalysisRun, Project.name)
            .outerjoin(Project, Project.id == AnalysisRun.project_id)
            .filter(AnalysisRun.user_id == user.id, AnalysisRun.entitlement_id.in_(entitlement_ids))
            .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
            .all()
        )
        for run, project_name in run_rows:
            if run.entitlement_id and run.entitlement_id not in latest_runs:
                latest_runs[int(run.entitlement_id)] = (run, project_name)

    history: list[dict[str, Any]] = []
    for row in rows:
        payload = _serialize_entitlement(row)
        latest = latest_runs.get(row.id)
        history.append(
            {
                **payload,
                "last_analysis_run_id": latest[0].id if latest else None,
                "last_analysis_created_at": _iso(latest[0].created_at) if latest else None,
                "last_analysis_project_name": latest[1] if latest else None,
                "last_analysis_score": latest[0].score if latest else None,
                "last_analysis_decision_code": latest[0].decision_code if latest else None,
            }
        )
    return history


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _from_unix_timestamp(value: Any) -> datetime | None:
    try:
        if value in (None, ""):
            return None
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except Exception:
        return None


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        converted = value.to_dict()
        return converted if isinstance(converted, dict) else dict(converted)
    if hasattr(value, "__dict__"):
        return {k: v for k, v in vars(value).items() if not k.startswith("_")}
    return dict(value)


def _paywall_detail(db: Session, user: User) -> dict[str, Any]:
    overview = build_billing_overview(db, user)
    if _subscription_state(user) == "past_due":
        return {
            "code": "SUBSCRIPTION_PAYMENT_REQUIRED",
            "message": "Die Pro Lizenz ist wegen offener Zahlung fuer neue Subscription-Analysen gesperrt.",
            "hint": "Bitte Billing Portal oeffnen oder stattdessen ein separates One-off-Paket waehlen.",
            "billing": overview,
        }
    limit = overview.get("free_checks_limit", settings.free_checks_limit)
    return {
        "code": "FREE_TIER_LIMIT",
        "message": (
            f"Das Free-Kontingent ({limit} abgeschlossene Checks) ist aufgebraucht. "
            "Bitte ein Angebot buchen oder auf Pro wechseln."
        ),
        "hint": "Upgrade ueber Einstellungen > Tarif & Analyse-History starten.",
        "billing": overview,
    }


def _stripe_not_configured_detail() -> dict[str, Any]:
    return {
        "code": "STRIPE_NOT_CONFIGURED",
        "message": "Stripe ist in dieser Umgebung noch nicht konfiguriert.",
        "hint": "Bitte die passenden STRIPE_PRICE_* und STRIPE_SECRET_KEY setzen oder spaeter erneut versuchen.",
    }


def _load_stripe_module():
    try:
        import stripe  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without dependency installed
        raise HTTPException(status_code=503, detail=_stripe_not_configured_detail()) from exc
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail=_stripe_not_configured_detail())
    stripe.api_key = settings.stripe_secret_key
    return stripe


def _build_stripe_readiness() -> dict[str, Any]:
    catalog = _offer_catalog()
    issues: list[str] = []
    warnings: list[str] = []
    offers: list[dict[str, Any]] = []

    if not settings.stripe_secret_key:
        issues.append("STRIPE_SECRET_KEY fehlt.")
    if not settings.stripe_webhook_secret:
        warnings.append("STRIPE_WEBHOOK_SECRET fehlt. Automatische Subscription-Syncs bleiben dann lueckenhaft.")
    if not settings.stripe_checkout_success_url or not settings.stripe_checkout_cancel_url:
        warnings.append("Checkout-Return-URLs sind nicht explizit gesetzt. Es wird auf /settings zurueckgefallen.")
    if not settings.stripe_portal_return_url:
        warnings.append("STRIPE_PORTAL_RETURN_URL ist nicht explizit gesetzt. Das Portal faellt auf /settings zurueck.")

    for offer in [*catalog["offers"], *catalog["addons"]]:
        if offer["billing_mode"] == "contact":
            continue
        offer_issues: list[str] = []
        if not settings.stripe_secret_key:
            offer_issues.append("Secret Key fehlt.")
        if not offer.get("stripe_price_id"):
            offer_issues.append("Price ID fehlt.")
        offers.append(
            {
                "offer_id": offer["offer_id"],
                "billing_mode": offer["billing_mode"],
                "ready": len(offer_issues) == 0,
                "issues": offer_issues,
            }
        )

    if issues:
        status = "disabled"
    elif warnings:
        status = "warning"
    else:
        status = "ready"

    return {
        "status": status,
        "checkout_ready": any(item["ready"] for item in offers if item["billing_mode"] in {"payment", "subscription"}),
        "webhook_ready": bool(settings.stripe_webhook_secret),
        "portal_ready": bool(settings.stripe_secret_key),
        "issues": issues,
        "warnings": warnings,
        "offers": offers,
    }


def has_paid_access(user: User) -> bool:
    # Billing-Hide-Schalter: ohne aktivierten Schalter (Default) wird jeder
    # Nicht-Admin-User wie plan_tier=free behandelt, unabhaengig vom DB-Stand.
    # Admin-Bypass bleibt; Admin-Flows werden ohnehin in
    # _apply_admin_overview_overrides / package_access_context auf Admin-Pfad
    # umgeleitet. Hier nur die Konsumenten-Sicht synchron halten.
    if not settings.billing_enabled and not _is_unlimited_admin(user):
        return False
    return user.plan_tier != "free" and user.billing_status in SUBSCRIPTION_ANALYSIS_ACCESS_STATUSES


# --- Admin bypass --------------------------------------------------------------
#
# Interne Admin-Konten (User.role == "admin") sind ein operativer Zugang fuer
# Betreiber, QA und Support. Sie umgehen die "3 Free Checks"-Schranke und sehen
# alle Premium-Features mit dem hoechsten Paket-Scope ("professional").
#
# Verbindlich:
#   - Die Rollenpruefung erfolgt ausschliesslich serverseitig anhand der DB-Spalte
#     users.role (kommt ueber das JWT 'sub' -> get_current_user -> DB-Lookup).
#     Es wird KEIN Wert aus dem Request, Header oder Frontend vertraut.
#   - Es werden KEINE Credits/Counter (free_quota_consumed, entitlement.used_credits)
#     fuer Admin-Runs hochgezaehlt. Admin-Runs landen mit billing_category="admin"
#     und usage_bucket="admin" in der Analyse-History, bleiben dort vollstaendig
#     auditierbar und sind klar von echten Free/Pro/Pay-per-Use-Runs unterscheidbar.
#   - Normale Basic-User sind nicht betroffen. Das 3-Frei-Checks-Limit bleibt
#     fuer alle Nicht-Admin-Rollen unveraendert (test_freemium_paywall_and_billing_catalog).


def _is_unlimited_admin(user: User) -> bool:
    """Server-side truth: only DB role 'admin' grants the unlimited-access bypass."""
    return str(getattr(user, "role", "") or "").strip().lower() == "admin"


_ADMIN_OFFER_SCOPE = "professional"
_ADMIN_OFFER_REPORT_SCOPE = "professional"
_ADMIN_OFFER_USAGE_BUCKET = "admin"
_ADMIN_OFFER_ID = "admin"


def _admin_feature_flags() -> dict[str, bool]:
    """Mirrors the professional package feature set so admins see every premium UI path."""
    return {
        "hybrid": True,
        "storage": True,
        "environment": True,
        "stakeholder_compare": True,
        "variants": True,
        "visualization": True,
        "express_eligible": True,
    }


def _admin_access_context(requested_offer_id: str | None = None) -> dict[str, Any]:
    """Synthetic access context for admin users; no entitlement, no quota consumed."""
    return {
        "billing_category": "admin",
        "free_quota_consumed": False,
        "offer_id": _ADMIN_OFFER_ID,
        "package_scope": _ADMIN_OFFER_SCOPE,
        "usage_bucket": _ADMIN_OFFER_USAGE_BUCKET,
        "entitlement": None,
        "report_scope": _ADMIN_OFFER_REPORT_SCOPE,
        "feature_flags": _admin_feature_flags(),
        "ops_followup_required": False,
    }


def _apply_admin_overview_overrides(overview: dict[str, Any], user: User) -> dict[str, Any]:
    """Rewrite a billing overview so admins see unlimited access and the premium option set."""
    overview["plan_tier"] = "admin"
    overview["billing_state_label"] = "admin"
    overview["can_run_analysis"] = True
    overview["upgrade_required"] = False
    overview["billing_attention"] = None
    overview["has_active_subscription"] = False
    overview["subscription_state"] = overview.get("subscription_state") or "none"

    admin_option = {
        "offer_id": _ADMIN_OFFER_ID,
        "label": "Admin (unlimited)",
        "package_scope": _ADMIN_OFFER_SCOPE,
        "remaining_credits": None,
        "usage_bucket": _ADMIN_OFFER_USAGE_BUCKET,
        "report_scope": _ADMIN_OFFER_REPORT_SCOPE,
        "feature_flags": _admin_feature_flags(),
        "default": True,
        "ops_followup_required": False,
    }
    options = list(overview.get("analysis_options") or [])
    for option in options:
        option["default"] = False
    overview["analysis_options"] = [admin_option, *options]
    return overview


def count_consumed_free_checks(db: Session, user: User) -> int:
    count = (
        db.query(func.count(AnalysisRun.id))
        .filter(
            AnalysisRun.user_id == user.id,
            AnalysisRun.status == "completed",
            AnalysisRun.free_quota_consumed.is_(True),
        )
        .scalar()
    )
    return int(count or 0)


def _ops_next_action(entitlement: dict[str, Any]) -> str:
    offer_id = str(entitlement.get("offer_id") or "")
    ops_status = str(entitlement.get("ops_status") or "")
    if offer_id == "express_upgrade":
        return "Express-Pfad operativ bestaetigen und SLA/Termin manuell koordinieren."
    if ops_status == "in_progress":
        return "Operative Bearbeitung fortsetzen und Abschlussstatus dokumentieren."
    if ops_status == "completed":
        return "Follow-up ist abgeschlossen."
    return "Operative Anschlussstrategie, Visualisierung und naechste Schritte pruefen."


def _build_followup_payloads(
    db: Session,
    rows: list[BillingEntitlement],
) -> list[dict[str, Any]]:
    entitlement_ids = [row.id for row in rows]
    latest_runs: dict[int, tuple[AnalysisRun, str | None]] = {}
    if entitlement_ids:
        run_rows = (
            db.query(AnalysisRun, Project.name)
            .outerjoin(Project, Project.id == AnalysisRun.project_id)
            .filter(AnalysisRun.entitlement_id.in_(entitlement_ids))
            .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
            .all()
        )
        for run, project_name in run_rows:
            if run.entitlement_id and run.entitlement_id not in latest_runs:
                latest_runs[int(run.entitlement_id)] = (run, project_name)

    followups: list[dict[str, Any]] = []
    for row in rows:
        entitlement = _serialize_entitlement(row)
        latest = latest_runs.get(row.id)
        followups.append(
            {
                "entitlement_id": row.id,
                "offer_id": entitlement["offer_id"],
                "package_scope": entitlement["package_scope"],
                "status": entitlement["status"],
                "ops_status": entitlement["ops_status"],
                "express_requested": entitlement["express_requested"],
                "checkout_session_id": entitlement["checkout_session_id"],
                "remaining_credits": entitlement["remaining_credits"],
                "customer_user_id": row.user_id,
                "customer_email": row.user.email if row.user else None,
                "customer_name": row.user.full_name if row.user else None,
                "project_name": latest[1] if latest else None,
                "analysis_run_id": latest[0].id if latest else None,
                "analysis_created_at": latest[0].created_at if latest else None,
                "ops_assignee_user_id": entitlement["ops_assignee_user_id"],
                "ops_assignee_email": entitlement["ops_assignee_email"],
                "ops_assignee_name": entitlement["ops_assignee_name"],
                "ops_assigned_at": entitlement["ops_assigned_at"],
                "ops_started_at": entitlement["ops_started_at"],
                "ops_completed_at": entitlement["ops_completed_at"],
                "ops_last_comment": entitlement["ops_last_comment"],
                "updated_at": row.updated_at,
                "next_action": _ops_next_action(entitlement),
            }
        )
    return followups


def list_ops_followups(db: Session, user: User, *, limit: int = 10) -> list[dict[str, Any]]:
    rows = (
        db.query(BillingEntitlement)
        .filter(
            BillingEntitlement.user_id == user.id,
            BillingEntitlement.ops_followup_required.is_(True),
            BillingEntitlement.ops_status.notin_(["not_required", "completed"]),
        )
        .order_by(BillingEntitlement.updated_at.desc(), BillingEntitlement.id.desc())
        .limit(limit)
        .all()
    )
    return _build_followup_payloads(db, rows)


def list_ops_followups_admin(
    db: Session,
    *,
    include_completed: bool = False,
    assigned_to_me_user_id: int | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = db.query(BillingEntitlement).filter(BillingEntitlement.ops_followup_required.is_(True))
    if include_completed:
        query = query.filter(BillingEntitlement.ops_status != "not_required")
    else:
        query = query.filter(BillingEntitlement.ops_status.in_(sorted(OPS_OPEN_STATUSES)))
    if assigned_to_me_user_id is not None:
        query = query.filter(BillingEntitlement.ops_assignee_user_id == assigned_to_me_user_id)
    rows = (
        query.order_by(
            BillingEntitlement.ops_assigned_at.desc().nullslast(),
            BillingEntitlement.updated_at.desc(),
            BillingEntitlement.id.desc(),
        )
        .limit(limit)
        .all()
    )
    return _build_followup_payloads(db, rows)


def _get_ops_entitlement_or_404(db: Session, entitlement_id: int) -> BillingEntitlement:
    entitlement = (
        db.query(BillingEntitlement)
        .filter(BillingEntitlement.id == entitlement_id, BillingEntitlement.ops_followup_required.is_(True))
        .first()
    )
    if entitlement is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "OPS_FOLLOWUP_NOT_FOUND",
                "message": "OPS-Follow-up wurde nicht gefunden.",
                "hint": "Bitte Queue aktualisieren und erneut versuchen.",
            },
        )
    return entitlement


def _assert_ops_transition(current_status: str, new_status: str) -> None:
    allowed = OPS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "OPS_STATUS_TRANSITION_INVALID",
                "message": f"Ungueltiger OPS-Statuswechsel von {current_status} nach {new_status}.",
                "hint": "Zulaessig ist nur pending_review -> in_progress -> completed.",
            },
        )


def _record_ops_followup_event(
    db: Session,
    *,
    entitlement: BillingEntitlement,
    admin_user: User,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    _record_billing_event(
        db,
        user_id=entitlement.user_id,
        event_type=event_type,
        status=entitlement.ops_status,
        payload={
            "entitlement_id": entitlement.id,
            "admin_user_id": admin_user.id,
            "admin_email": admin_user.email,
            **payload,
        },
        checkout_session_id=entitlement.checkout_session_id,
        provider_customer_id=entitlement.user.stripe_customer_id if entitlement.user else None,
        provider_subscription_id=entitlement.stripe_subscription_id,
    )


def claim_ops_followup(
    db: Session,
    admin_user: User,
    *,
    entitlement_id: int,
    comment: str | None = None,
) -> dict[str, Any]:
    entitlement = _get_ops_entitlement_or_404(db, entitlement_id)
    if entitlement.ops_status == "completed":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "OPS_FOLLOWUP_ALREADY_COMPLETED",
                "message": "Dieser OPS-Follow-up ist bereits abgeschlossen.",
                "hint": "Bitte einen offenen Follow-up waehlen.",
            },
        )
    if entitlement.ops_assignee_user_id and entitlement.ops_assignee_user_id != admin_user.id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "OPS_FOLLOWUP_ALREADY_ASSIGNED",
                "message": "Dieser OPS-Follow-up ist bereits einem anderen Admin zugewiesen.",
                "hint": "Bitte zuerst die bestehende Zuweisung pruefen.",
            },
        )
    previous_status = entitlement.ops_status
    if previous_status == "pending_review":
        _assert_ops_transition(previous_status, "in_progress")
        entitlement.ops_status = "in_progress"
    entitlement.ops_assignee_user_id = admin_user.id
    entitlement.ops_assignee = admin_user
    if entitlement.ops_assigned_at is None:
        entitlement.ops_assigned_at = _utcnow()
    if entitlement.ops_started_at is None:
        entitlement.ops_started_at = _utcnow()
    if comment:
        entitlement.ops_last_comment = comment.strip()[:2000]
    entitlement.updated_at = _utcnow()
    _record_ops_followup_event(
        db,
        entitlement=entitlement,
        admin_user=admin_user,
        event_type="ops.followup.claimed",
        payload={
            "previous_status": previous_status,
            "new_status": entitlement.ops_status,
            "comment": entitlement.ops_last_comment,
        },
    )
    db.commit()
    return next(item for item in _build_followup_payloads(db, [entitlement]) if item["entitlement_id"] == entitlement.id)


def update_ops_followup_status(
    db: Session,
    admin_user: User,
    *,
    entitlement_id: int,
    new_status: str,
    comment: str | None = None,
) -> dict[str, Any]:
    entitlement = _get_ops_entitlement_or_404(db, entitlement_id)
    next_status = str(new_status or "").strip()
    if next_status not in OPS_TRANSITIONS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "OPS_STATUS_INVALID",
                "message": "OPS-Status ist ungueltig.",
                "hint": "Bitte pending_review, in_progress oder completed verwenden.",
            },
        )
    if entitlement.ops_assignee_user_id and entitlement.ops_assignee_user_id != admin_user.id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "OPS_FOLLOWUP_ASSIGNEE_MISMATCH",
                "message": "Dieser OPS-Follow-up ist einem anderen Admin zugewiesen.",
                "hint": "Bitte nur eigene oder unzugewiesene Follow-ups bearbeiten.",
            },
        )
    previous_status = entitlement.ops_status
    _assert_ops_transition(previous_status, next_status)
    entitlement.ops_assignee_user_id = admin_user.id
    entitlement.ops_assignee = admin_user
    if entitlement.ops_assigned_at is None:
        entitlement.ops_assigned_at = _utcnow()
    if next_status == "in_progress" and entitlement.ops_started_at is None:
        entitlement.ops_started_at = _utcnow()
    if next_status == "completed":
        entitlement.ops_completed_at = _utcnow()
        if entitlement.status == "ops_pending":
            entitlement.status = "active"
    if comment:
        entitlement.ops_last_comment = comment.strip()[:2000]
    entitlement.ops_status = next_status
    entitlement.updated_at = _utcnow()
    _record_ops_followup_event(
        db,
        entitlement=entitlement,
        admin_user=admin_user,
        event_type="ops.followup.status_changed",
        payload={
            "previous_status": previous_status,
            "new_status": next_status,
            "comment": entitlement.ops_last_comment,
        },
    )
    db.commit()
    return next(item for item in _build_followup_payloads(db, [entitlement]) if item["entitlement_id"] == entitlement.id)


def build_billing_overview(db: Session, user: User) -> dict[str, Any]:
    _ensure_subscription_entitlement(db, user)
    free_checks_limit = settings.free_checks_limit
    free_checks_used = count_consumed_free_checks(db, user)
    paid_access = has_paid_access(user)
    free_checks_remaining = max(0, free_checks_limit - free_checks_used)
    catalog = get_public_billing_catalog()
    checkout_enabled = any(offer["checkout_enabled"] for offer in catalog["offers"])
    entitlements = list_active_entitlements(db, user)
    entitlement_history = list_entitlement_history(db, user, limit=20)
    ops_followups = list_ops_followups(db, user, limit=10)
    stripe_readiness = _build_stripe_readiness()
    subscription_state = _subscription_state(user)
    billing_attention = _billing_attention(user)
    analysis_options: list[dict[str, Any]] = []
    prepaid_credit_entitlements = [
        entitlement
        for entitlement in entitlements
        if entitlement["offer_id"] != "pro_lizenz"
        and entitlement["remaining_credits"] is not None
        and int(entitlement["remaining_credits"]) > 0
    ]
    ops_pending_entitlements = [
        entitlement
        for entitlement in entitlements
        if entitlement.get("ops_status") not in {None, "", "not_required", "completed"}
    ]

    if free_checks_remaining > 0:
        free_offer = _offer_lookup("basic_schnellcheck")
        analysis_options.append(
            {
                "offer_id": "free",
                "label": "Free Check",
                "package_scope": "basic",
                "remaining_credits": free_checks_remaining,
                "usage_bucket": "free",
                "report_scope": free_offer["report_scope"],
                "feature_flags": _feature_flags(free_offer),
                "default": not paid_access and len(entitlements) == 0,
            }
        )

    for entitlement in entitlements:
        offer = _offer_lookup(entitlement["offer_id"])
        if offer["offer_id"] == "pro_lizenz" and not paid_access:
            continue
        if offer["billing_mode"] == "addon":
            continue
        if entitlement["status"] not in {"active", "ops_pending"}:
            continue
        if entitlement["remaining_credits"] is not None and int(entitlement["remaining_credits"]) <= 0:
            continue
        analysis_options.append(
            {
                "offer_id": entitlement["offer_id"],
                "label": offer["name"],
                "package_scope": entitlement["package_scope"],
                "remaining_credits": entitlement["remaining_credits"],
                "usage_bucket": offer["usage_bucket"],
                "report_scope": offer["report_scope"],
                "feature_flags": _feature_flags(offer),
                "default": offer["offer_id"] == "pro_lizenz" and paid_access,
                "ops_followup_required": entitlement["ops_followup_required"],
            }
        )
    if analysis_options and not any(bool(option.get("default")) for option in analysis_options):
        for option in analysis_options:
            if option["offer_id"] != "free":
                option["default"] = True
                break
    can_run_analysis = any(
        option["remaining_credits"] is None or int(option["remaining_credits"]) > 0 for option in analysis_options
    )
    if paid_access:
        billing_state_label = "pro"
    elif prepaid_credit_entitlements:
        billing_state_label = "credits"
    elif can_run_analysis:
        billing_state_label = "free"
    elif subscription_state == "past_due":
        billing_state_label = "past_due"
    else:
        billing_state_label = "paywall"

    overview = {
        "plan_tier": user.plan_tier,
        "billing_status": user.billing_status,
        "has_active_subscription": paid_access,
        "subscription_state": subscription_state,
        "billing_attention": billing_attention,
        "stripe_configured": bool(settings.stripe_secret_key and checkout_enabled),
        "customer_portal_available": bool(
            settings.stripe_secret_key and user.stripe_customer_id and subscription_state in PORTAL_ELIGIBLE_STATES
        ),
        "has_prepaid_credits": bool(prepaid_credit_entitlements),
        "active_paid_entitlements_count": len(prepaid_credit_entitlements),
        "has_ops_pending": bool(ops_pending_entitlements) or bool(ops_followups),
        "open_ops_followups_count": len(ops_followups),
        "billing_state_label": billing_state_label,
        "free_checks_limit": free_checks_limit,
        "free_checks_used": free_checks_used,
        "free_checks_remaining": free_checks_remaining,
        "can_run_analysis": can_run_analysis,
        "upgrade_required": not can_run_analysis,
        "current_period_end": _iso(user.billing_current_period_end),
        "stripe_customer_id": user.stripe_customer_id,
        "catalog": catalog,
        "recommended_offer_ids": (
            ["premium_pre_check", "professional_anschlussstrategie", "basic_schnellcheck"]
            if subscription_state == "past_due"
            else ["premium_pre_check", "professional_anschlussstrategie", "pro_lizenz"]
        ),
        "active_entitlements": entitlements,
        "entitlement_history": entitlement_history,
        "ops_followups": [
            {
                **followup,
                "analysis_created_at": _iso(followup["analysis_created_at"]),
                "updated_at": _iso(followup["updated_at"]),
            }
            for followup in ops_followups
        ],
        "recent_billing_events": [
            {
                **event,
                "created_at": _iso(event["created_at"]),
            }
            for event in list_recent_billing_events(db, user, limit=10)
        ],
        "stripe_readiness": stripe_readiness,
        "analysis_options": analysis_options,
        "usage_policy": {
            "free_checks": {
                "limit": free_checks_limit,
                "consumption_rule": "Nur erfolgreich abgeschlossene Analysen verbrauchen Free Checks.",
            },
            "pay_per_use": {
                "consumption_rule": "Basic, Premium und Professional verbrauchen je erfolgreichem Run genau 1 Credit.",
            },
            "subscription": {
                "offer_id": "pro_lizenz",
                "included_credits_per_period": _offer_lookup("pro_lizenz")["included_credits"],
                "consumption_rule": "Die Pro Lizenz verbraucht pro erfolgreichem Run 1 Inklusiv-Analyse innerhalb der aktiven Billing-Periode.",
                "past_due_rule": "Bei past_due bleiben Billing Portal, Projekte, History und bestehende Reports offen, neue Pro-Analysen sind jedoch gesperrt.",
            },
            "ops_boundary": {
                "professional": "Professional schaltet Professional-Reportscope frei und markiert den Run fuer operativen Follow-up.",
                "express": "Express ist ein operativer Zusatzpfad und aendert keine technische Analyse ohne separate OPS-Freigabe.",
            },
        },
    }

    # Admin-Bypass: ueberschreibt nur die paket-/limit-relevanten Felder am Ende.
    # plan_tier=="admin" schaltet Frontend-Banner (isPaidBillingStatus) automatisch aus,
    # can_run_analysis=True und upgrade_required=False loesen Paywall-UI in GridCheckForm/BillingUpgradePrompt.
    if _is_unlimited_admin(user):
        return _apply_admin_overview_overrides(overview, user)
    return overview


def ensure_analysis_allowed(db: Session, user: User) -> dict[str, Any]:
    overview = build_billing_overview(db, user)
    if overview["can_run_analysis"]:
        return overview
    raise HTTPException(status_code=402, detail=_paywall_detail(db, user))


def package_access_context(
    db: Session,
    user: User,
    *,
    requested_offer_id: str | None = None,
) -> dict[str, Any]:
    # Admin-Bypass: keine Paywall, kein Quota-Verbrauch, voller Professional-Scope.
    # Greift VOR jeder Entitlement-/Free-Tier-Pruefung, damit Admin nie an einer
    # 402-Paywall haengenbleibt. Counter werden nicht hochgezaehlt, weil
    # entitlement=None und free_quota_consumed=False (siehe persist_completed_analysis_run).
    if _is_unlimited_admin(user):
        return _admin_access_context(requested_offer_id)

    _ensure_subscription_entitlement(db, user)

    if requested_offer_id and requested_offer_id not in PAYMENT_OFFER_IDS | SUBSCRIPTION_OFFER_IDS | {"free"}:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_OFFER_INVALID",
                "message": "Die gewaehlte Paketoption ist fuer Analysen nicht gueltig.",
                "hint": "Bitte Free, Basic, Premium, Professional oder Pro Lizenz verwenden.",
            },
        )

    if requested_offer_id == "free" or requested_offer_id is None:
        subscription_entitlement = _get_subscription_entitlement(db, user)
        if requested_offer_id is None and has_paid_access(user) and subscription_entitlement and _entitlement_usable(subscription_entitlement):
            offer = _offer_lookup("pro_lizenz")
            return {
                "billing_category": "paid",
                "free_quota_consumed": False,
                "offer_id": "pro_lizenz",
                "package_scope": offer["package_scope"],
                "usage_bucket": offer["usage_bucket"],
                "entitlement": subscription_entitlement,
                "report_scope": offer["report_scope"],
                "feature_flags": _feature_flags(offer),
                "ops_followup_required": False,
            }

        if requested_offer_id == "free":
            if count_consumed_free_checks(db, user) < settings.free_checks_limit:
                free_offer = _offer_lookup("basic_schnellcheck")
                return {
                    "billing_category": "free",
                    "free_quota_consumed": True,
                    "offer_id": "free",
                    "package_scope": "basic",
                    "usage_bucket": "free",
                    "entitlement": None,
                    "report_scope": free_offer["report_scope"],
                    "feature_flags": _feature_flags(free_offer),
                    "ops_followup_required": False,
                }
            raise HTTPException(status_code=402, detail=_paywall_detail(db, user))

    if requested_offer_id is None:
        for offer_id in ("professional_anschlussstrategie", "premium_pre_check", "basic_schnellcheck"):
            entitlement = _entitlement_for_offer(db, user, offer_id)
            if entitlement:
                offer = _offer_lookup(offer_id)
                return {
                    "billing_category": "paid",
                    "free_quota_consumed": False,
                    "offer_id": offer_id,
                    "package_scope": offer["package_scope"],
                    "usage_bucket": offer["usage_bucket"],
                    "entitlement": entitlement,
                    "report_scope": offer["report_scope"],
                    "feature_flags": _feature_flags(offer),
                    "ops_followup_required": bool(offer.get("ops_followup_required")),
                }
        if count_consumed_free_checks(db, user) < settings.free_checks_limit:
            free_offer = _offer_lookup("basic_schnellcheck")
            return {
                "billing_category": "free",
                "free_quota_consumed": True,
                "offer_id": "free",
                "package_scope": "basic",
                "usage_bucket": "free",
                "entitlement": None,
                "report_scope": free_offer["report_scope"],
                "feature_flags": _feature_flags(free_offer),
                "ops_followup_required": False,
            }
        raise HTTPException(status_code=402, detail=_paywall_detail(db, user))

    if requested_offer_id in SUBSCRIPTION_OFFER_IDS:
        entitlement = _get_subscription_entitlement(db, user)
        if has_paid_access(user) and entitlement and _entitlement_usable(entitlement):
            offer = _offer_lookup(requested_offer_id)
            return {
                "billing_category": "paid",
                "free_quota_consumed": False,
                "offer_id": requested_offer_id,
                "package_scope": offer["package_scope"],
                "usage_bucket": offer["usage_bucket"],
                "entitlement": entitlement,
                "report_scope": offer["report_scope"],
                "feature_flags": _feature_flags(offer),
                "ops_followup_required": False,
            }
        if _subscription_state(user) == "past_due":
            raise HTTPException(status_code=402, detail=_paywall_detail(db, user))
        raise HTTPException(status_code=402, detail=_paywall_detail(db, user))

    entitlement = _entitlement_for_offer(db, user, requested_offer_id)
    if entitlement:
        offer = _offer_lookup(requested_offer_id)
        return {
            "billing_category": "paid",
            "free_quota_consumed": False,
            "offer_id": requested_offer_id,
            "package_scope": offer["package_scope"],
            "usage_bucket": offer["usage_bucket"],
            "entitlement": entitlement,
            "report_scope": offer["report_scope"],
            "feature_flags": _feature_flags(offer),
            "ops_followup_required": bool(offer.get("ops_followup_required")),
        }
    raise HTTPException(status_code=402, detail=_paywall_detail(db, user))


def enforce_package_rights(payload: dict[str, Any], access: dict[str, Any]) -> dict[str, Any]:
    package_scope = str(access["package_scope"])
    feature_flags = access.get("feature_flags") if isinstance(access.get("feature_flags"), dict) else {}
    sanitized = dict(payload)
    warnings: list[str] = []

    if package_scope == "basic":
        project_components = sanitized.get("project_components")
        if isinstance(project_components, list) and len(project_components) > 1:
            sanitized["project_components"] = project_components[:1]
            warnings.append("Hybrid-/Mehrkomponentenlogik ist erst ab Premium freigeschaltet.")
        if sanitized.get("storage_profile"):
            sanitized["storage_profile"] = None
            warnings.append("Speicher- und Netzdienlichkeitsbewertung ist erst ab Premium freigeschaltet.")
        if sanitized.get("environmental_route"):
            sanitized["environmental_route"] = None
            warnings.append("Umwelt-/Trassenbewertung ist erst ab Premium freigeschaltet.")

    sanitized["requested_offer_id"] = access["offer_id"]
    sanitized["package_scope"] = package_scope
    sanitized["report_scope"] = access["report_scope"]
    sanitized["feature_flags"] = feature_flags
    if warnings:
        sanitized["package_warnings"] = warnings
    return sanitized


def _extract_score(result_payload: dict[str, Any]) -> float | None:
    try:
        scores = result_payload.get("scores")
        if isinstance(scores, dict) and scores.get("gesamt") is not None:
            return float(scores["gesamt"])
        if result_payload.get("score") is not None:
            return float(result_payload["score"])
    except Exception:
        return None
    return None


def _extract_decision_code(result_payload: dict[str, Any]) -> str | None:
    fazit = result_payload.get("fazit")
    if isinstance(fazit, dict) and fazit.get("entscheidung") is not None:
        return str(fazit["entscheidung"])
    return None


def _extract_revision_hash(result_payload: dict[str, Any]) -> str | None:
    revision = result_payload.get("revision")
    if isinstance(revision, dict) and revision.get("hash"):
        return str(revision["hash"])
    return None


def _resolve_norm_version(
    request_payload: dict[str, Any],
    result_payload: dict[str, Any],
) -> str:
    if result_payload.get("norm_version"):
        return str(result_payload["norm_version"])
    try:
        u_kv = float(
            request_payload.get("nennspannung")
            or request_payload.get("spannung_kv")
            or 20.0
        )
    except (TypeError, ValueError):
        u_kv = 20.0
    norms = get_normen_fuer_spannungsebene(u_kv, nur_kategorien=["Anwendungsregel", "Norm"])
    details = "; ".join(f"{n.norm_id} ({n.stand})" for n in norms[:8])
    if details:
        return f"Registry {APP_VERSION_NORMSTAND} | {details}"
    return f"Registry {APP_VERSION_NORMSTAND}"


def _persist_gridcheck_result_audit(
    db: Session,
    *,
    user: User,
    project_id: int | None,
    request_payload: dict[str, Any],
    result_payload: dict[str, Any],
) -> None:
    transparenz = result_payload.get("transparenz") if isinstance(result_payload.get("transparenz"), dict) else {}
    scores = result_payload.get("scores") if isinstance(result_payload.get("scores"), dict) else {}
    sources: list[Any] = []
    if isinstance(result_payload.get("datenqualitaet"), dict):
        dq_sources = result_payload["datenqualitaet"].get("quellen")
        if isinstance(dq_sources, list):
            sources = dq_sources
    audit = GridcheckResultAudit(
        project_id=project_id,
        model_version=str(result_payload.get("engine_version") or ENGINE_VERSION),
        scoring_version=str(result_payload.get("engine_version") or ENGINE_VERSION),
        norm_version=_resolve_norm_version(request_payload, result_payload),
        app_version=settings.app_version,
        inputs_json=_json_text({**request_payload, "user_id": user.id}),
        assumptions_json=_json_text(transparenz.get("assumptions", [])),
        warnings_json=_json_text(result_payload.get("warnungen", [])),
        score_components_json=_json_text(scores),
        sources_json=_json_text(sources),
        result_json=_json_text(result_payload),
        result_hash=make_checksum(result_payload),
    )
    db.add(audit)


def _lock_entitlement_for_consume(db: Session, entitlement_id: int) -> BillingEntitlement | None:
    """SELECT … FOR UPDATE + populate_existing so concurrent sessions see fresh used_credits."""
    return (
        db.query(BillingEntitlement)
        .filter(BillingEntitlement.id == entitlement_id)
        .with_for_update()
        .execution_options(populate_existing=True)
        .one_or_none()
    )


def _consume_access_quota(
    db: Session,
    user: User,
    access: dict[str, Any],
) -> BillingEntitlement | None:
    """
    Atomically consume prepaid/subscription credits or free-tier quota at persist time.

    package_access_context runs before the (potentially long) engine calculation and only
    snapshots entitlement/free-quota state. Two parallel analyze requests can both pass that
    check against a 1-credit pack (or the last free check). Without a re-check under row
    locks here, both would persist completed runs while used_credits stays at 1 (last-writer
    wins) or free_quota_consumed exceeds FREE_CHECKS_LIMIT.
    """
    entitlement = access.get("entitlement")
    if isinstance(entitlement, BillingEntitlement):
        locked = _lock_entitlement_for_consume(db, int(entitlement.id))
        if locked is None or not _entitlement_usable(locked):
            raise HTTPException(status_code=402, detail=_paywall_detail(db, user))
        locked.used_credits = int(locked.used_credits or 0) + 1
        remaining = _remaining_credits(locked)
        if remaining is not None and remaining <= 0:
            locked.status = "consumed"
        locked.updated_at = _utcnow()
        access["entitlement"] = locked
        return locked

    if bool(access.get("free_quota_consumed")):
        (
            db.query(User)
            .filter(User.id == user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
            .one()
        )
        if count_consumed_free_checks(db, user) >= settings.free_checks_limit:
            raise HTTPException(status_code=402, detail=_paywall_detail(db, user))
    return None


def persist_completed_analysis_run(
    db: Session,
    user: User,
    *,
    request_payload: dict[str, Any],
    result_payload: dict[str, Any],
    source: str,
    project_id: int | None = None,
    access_context: dict[str, Any] | None = None,
) -> AnalysisRun:
    access = access_context or package_access_context(
        db,
        user,
        requested_offer_id=str(request_payload.get("requested_offer_id")) if request_payload.get("requested_offer_id") else None,
    )
    entitlement = _consume_access_quota(db, user, access)
    run = AnalysisRun(
        user_id=user.id,
        project_id=project_id,
        source=source,
        status="completed",
        input_json=_json_text(request_payload),
        request_checksum=make_checksum(request_payload),
        result_json=_json_text(result_payload),
        result_checksum=make_checksum(result_payload),
        score=_extract_score(result_payload),
        decision_code=_extract_decision_code(result_payload),
        revision_hash=_extract_revision_hash(result_payload),
        offer_id=access["offer_id"],
        package_scope=access["package_scope"],
        usage_bucket=access["usage_bucket"],
        entitlement_id=entitlement.id if isinstance(entitlement, BillingEntitlement) else None,
        billing_category=access["billing_category"],
        free_quota_consumed=bool(access["free_quota_consumed"]),
    )
    db.add(run)
    _persist_gridcheck_result_audit(
        db,
        user=user,
        project_id=project_id,
        request_payload=request_payload,
        result_payload=result_payload,
    )
    db.commit()
    db.refresh(run)
    return run


def persist_failed_analysis_run(
    db: Session,
    user: User,
    *,
    request_payload: dict[str, Any],
    error_payload: dict[str, Any],
    source: str,
    status: str,
    project_id: int | None = None,
) -> AnalysisRun:
    run = AnalysisRun(
        user_id=user.id,
        project_id=project_id,
        source=source,
        status=status,
        input_json=_json_text(request_payload),
        request_checksum=make_checksum(request_payload),
        result_json=_json_text(error_payload),
        result_checksum=make_checksum(error_payload),
        score=None,
        decision_code=None,
        revision_hash=None,
        offer_id=str(request_payload.get("requested_offer_id") or "") or None,
        package_scope=str(request_payload.get("package_scope") or "basic"),
        usage_bucket="none",
        entitlement_id=None,
        billing_category="none",
        free_quota_consumed=False,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_analysis_history(db: Session, user: User, *, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        db.query(AnalysisRun, Project.name)
        .outerjoin(Project, Project.id == AnalysisRun.project_id)
        .filter(AnalysisRun.user_id == user.id)
        .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
        .limit(limit)
        .all()
    )
    history: list[dict[str, Any]] = []
    for run, project_name in rows:
        history.append(
            {
                "id": run.id,
                "project_id": run.project_id,
                "project_name": project_name,
                "source": run.source,
                "status": run.status,
                "score": run.score,
                "decision_code": run.decision_code,
                "revision_hash": run.revision_hash,
                "offer_id": run.offer_id,
                "package_scope": run.package_scope,
                "usage_bucket": run.usage_bucket,
                "entitlement_id": run.entitlement_id,
                "billing_category": run.billing_category,
                "free_quota_consumed": run.free_quota_consumed,
                "created_at": run.created_at,
            }
        )
    return history


def list_recent_billing_events(db: Session, user: User, *, limit: int = 10) -> list[dict[str, Any]]:
    rows = (
        db.query(BillingEvent)
        .filter(BillingEvent.user_id == user.id)
        .order_by(BillingEvent.created_at.desc(), BillingEvent.id.desc())
        .limit(limit)
        .all()
    )
    events: list[dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "id": row.id,
                "event_type": row.event_type,
                "status": row.status,
                "provider_event_id": row.provider_event_id,
                "checkout_session_id": row.checkout_session_id,
                "provider_customer_id": row.provider_customer_id,
                "provider_subscription_id": row.provider_subscription_id,
                "amount_cents": row.amount_cents,
                "currency": row.currency,
                "created_at": row.created_at,
            }
        )
    return events


def _record_billing_event(
    db: Session,
    *,
    user_id: int | None,
    event_type: str,
    status: str,
    payload: dict[str, Any],
    provider_event_id: str | None = None,
    checkout_session_id: str | None = None,
    provider_customer_id: str | None = None,
    provider_subscription_id: str | None = None,
    amount_cents: int | None = None,
    currency: str | None = None,
) -> BillingEvent:
    record = BillingEvent(
        user_id=user_id,
        provider="stripe",
        event_type=event_type,
        provider_event_id=provider_event_id,
        checkout_session_id=checkout_session_id,
        provider_customer_id=provider_customer_id,
        provider_subscription_id=provider_subscription_id,
        status=status,
        amount_cents=amount_cents,
        currency=currency,
        payload_json=_json_text(payload),
    )
    db.add(record)
    return record


def _ensure_query_param(url: str, key: str, value: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _ensure_checkout_urls() -> tuple[str, str]:
    if settings.stripe_checkout_success_url and settings.stripe_checkout_cancel_url:
        return (
            _ensure_query_param(settings.stripe_checkout_success_url, "billing", "success"),
            _ensure_query_param(settings.stripe_checkout_cancel_url, "billing", "cancel"),
        )
    base_url = (settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000").rstrip("/")
    return (
        _ensure_query_param(settings.stripe_checkout_success_url or f"{base_url}/settings", "billing", "success"),
        _ensure_query_param(settings.stripe_checkout_cancel_url or f"{base_url}/settings", "billing", "cancel"),
    )


def _portal_return_url() -> str:
    if settings.stripe_portal_return_url:
        return settings.stripe_portal_return_url
    base_url = (settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000").rstrip("/")
    return f"{base_url}/settings"


def _ensure_customer(db: Session, user: User, stripe_mod) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id
    try:
        customer = stripe_mod.Customer.create(
            email=user.email,
            name=user.full_name or None,
            metadata={"user_id": str(user.id), "app_env": settings.app_env},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "STRIPE_CUSTOMER_CREATE_FAILED",
                "message": "Stripe-Kundenkonto konnte nicht angelegt werden.",
                "hint": "Bitte Stripe-Konfiguration und Netzwerkzugriff pruefen.",
            },
        ) from exc
    customer_dict = _as_dict(customer)
    user.stripe_customer_id = str(customer_dict["id"])
    user.updated_at = _utcnow()
    db.commit()
    db.refresh(user)
    return user.stripe_customer_id


def create_checkout_session(db: Session, user: User, offer_id: str = "pro_lizenz") -> dict[str, str]:
    offer = _offer_lookup(offer_id)
    if not offer.get("checkout_enabled") or not offer.get("stripe_price_id"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BILLING_OFFER_NOT_CHECKOUT_READY",
                "message": "Dieses Angebot ist in dieser Umgebung nicht direkt buchbar.",
                "hint": "Bitte anderes Angebot waehlen oder Kontakt aufnehmen.",
            },
        )
    subscription_state = _subscription_state(user)
    if offer_id in SUBSCRIPTION_OFFER_IDS and subscription_state in {"active", "trialing", "past_due", "checkout_pending"}:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BILLING_SUBSCRIPTION_ALREADY_IN_PROGRESS",
                "message": (
                    "Fuer dieses Konto laeuft bereits eine Pro-Subscription."
                    if subscription_state != "checkout_pending"
                    else "Der letzte Pro-Checkout wird noch von Stripe bestaetigt."
                ),
                "hint": (
                    "Bitte Billing Portal fuer Zahlungsdaten oder Vertragsverwaltung verwenden."
                    if subscription_state in {"active", "trialing", "past_due"}
                    else "Bitte auf die finale Stripe-Bestaetigung warten, bevor ein neuer Checkout gestartet wird."
                ),
            },
        )
    stripe_mod = _load_stripe_module()
    customer_id = _ensure_customer(db, user, stripe_mod)
    success_url, cancel_url = _ensure_checkout_urls()
    if "CHECKOUT_SESSION_ID" not in success_url:
        separator = "&" if "?" in success_url else "?"
        success_url = f"{success_url}{separator}session_id={{CHECKOUT_SESSION_ID}}"
    metadata = {
        "user_id": str(user.id),
        "offer_id": str(offer["offer_id"]),
        "offer_name": str(offer["name"]),
        "offer_category": str(offer["category"]),
        "package_scope": str(offer["package_scope"]),
        "report_scope": str(offer["report_scope"]),
        "source": "gridcheck",
    }
    # Stripe Checkout kennt nur "payment" | "subscription" | "setup".
    # Interne Addon-Angebote (z. B. express_upgrade) sind Einmalzahlungen.
    stripe_checkout_mode = "payment" if offer["billing_mode"] == "addon" else offer["billing_mode"]
    create_kwargs: dict[str, Any] = {
        "mode": stripe_checkout_mode,
        "customer": customer_id,
        "client_reference_id": str(user.id),
        "allow_promotion_codes": True,
        "billing_address_collection": "auto",
        "line_items": [{"price": offer["stripe_price_id"], "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata,
    }
    if offer["billing_mode"] == "subscription":
        create_kwargs["subscription_data"] = {"metadata": metadata}
    try:
        session = stripe_mod.checkout.Session.create(**create_kwargs)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "STRIPE_CHECKOUT_FAILED",
                "message": "Stripe Checkout konnte nicht erzeugt werden.",
                "hint": "Bitte Price IDs, Return-URLs und Stripe-Zugang pruefen.",
            },
        ) from exc
    session_dict = _as_dict(session)
    checkout_url = session_dict.get("url")
    if not checkout_url:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "STRIPE_CHECKOUT_FAILED",
                "message": "Stripe Checkout konnte nicht erzeugt werden.",
                "hint": "Bitte spaeter erneut versuchen.",
            },
        )
    _record_billing_event(
        db,
        user_id=user.id,
        event_type="checkout.session.created",
        status="created",
        payload=session_dict,
        checkout_session_id=session_dict.get("id"),
        provider_customer_id=customer_id,
        provider_subscription_id=session_dict.get("subscription"),
    )
    track_checkout_started(
        db,
        user,
        offer_id=str(offer["offer_id"]),
        checkout_session_id=str(session_dict.get("id") or "") or None,
    )
    db.commit()
    return {
        "url": str(checkout_url),
        "session_id": str(session_dict.get("id") or ""),
        "offer_id": str(offer["offer_id"]),
        "offer_name": str(offer["name"]),
    }


def create_portal_session(db: Session, user: User) -> dict[str, str]:
    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "BILLING_PORTAL_UNAVAILABLE",
                "message": "Noch kein Stripe-Kundenkonto vorhanden.",
                "hint": "Bitte zuerst ein Upgrade starten.",
            },
        )
    stripe_mod = _load_stripe_module()
    try:
        session = stripe_mod.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=_portal_return_url(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "BILLING_PORTAL_FAILED",
                "message": "Stripe Billing Portal konnte nicht erzeugt werden.",
                "hint": "Bitte Return-URL und Stripe-Konfiguration pruefen.",
            },
        ) from exc
    session_dict = _as_dict(session)
    portal_url = session_dict.get("url")
    if not portal_url:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "BILLING_PORTAL_FAILED",
                "message": "Stripe Billing Portal konnte nicht erzeugt werden.",
                "hint": "Bitte spaeter erneut versuchen.",
            },
        )
    _record_billing_event(
        db,
        user_id=user.id,
        event_type="billing_portal.session.created",
        status="created",
        payload=session_dict,
        provider_customer_id=user.stripe_customer_id,
    )
    db.commit()
    return {"url": str(portal_url)}


def _resolve_user_for_event(db: Session, event_type: str, data_object: dict[str, Any]) -> User | None:
    metadata = data_object.get("metadata")
    if isinstance(metadata, dict) and metadata.get("user_id"):
        try:
            user_id = int(metadata["user_id"])
        except Exception:
            user_id = None
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user

    client_reference_id = data_object.get("client_reference_id")
    if client_reference_id:
        try:
            user_id = int(client_reference_id)
        except Exception:
            user_id = None
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user

    customer_id = data_object.get("customer")
    if customer_id:
        user = db.query(User).filter(User.stripe_customer_id == str(customer_id)).first()
        if user:
            return user

    subscription_id = data_object.get("id") if event_type.startswith("customer.subscription.") else data_object.get("subscription")
    if subscription_id:
        return db.query(User).filter(User.stripe_subscription_id == str(subscription_id)).first()
    return None


def _apply_subscription_state(user: User, data_object: dict[str, Any]) -> None:
    subscription_status = str(data_object.get("status") or user.billing_status or "free")
    items = data_object.get("items")
    price_id = None
    if isinstance(items, dict):
        data_items = items.get("data")
        if isinstance(data_items, list) and data_items:
            first = data_items[0]
            if isinstance(first, dict):
                price = first.get("price")
                if isinstance(price, dict) and price.get("id"):
                    price_id = str(price["id"])
    user.stripe_customer_id = str(data_object.get("customer") or user.stripe_customer_id or "") or None
    user.stripe_subscription_id = str(data_object.get("id") or user.stripe_subscription_id or "") or None
    user.stripe_price_id = price_id or user.stripe_price_id
    user.billing_status = subscription_status
    user.plan_tier = "pro" if subscription_status in PAID_ACCESS_STATUSES else "free"
    user.billing_current_period_end = _from_unix_timestamp(data_object.get("current_period_end"))
    user.updated_at = _utcnow()


def _upsert_subscription_entitlement_from_offer(
    db: Session,
    user: User,
    *,
    offer_id: str,
    checkout_session_id: str | None = None,
    stripe_subscription_id: str | None = None,
    status: str = "active",
) -> BillingEntitlement:
    offer = _offer_lookup(offer_id)
    entitlement = _get_subscription_entitlement(db, user, statuses={"active", "pending", "ops_pending"})
    if entitlement is None:
        entitlement = BillingEntitlement(
            user_id=user.id,
            offer_id=offer_id,
            offer_category=str(offer["category"]),
            package_scope=str(offer["package_scope"]),
            source="subscription",
            status=status,
            total_credits=int(offer["included_credits"]),
            used_credits=0,
            valid_from=_utcnow(),
            valid_until=user.billing_current_period_end,
            checkout_session_id=checkout_session_id,
            stripe_price_id=user.stripe_price_id,
            stripe_subscription_id=stripe_subscription_id or user.stripe_subscription_id,
            ops_followup_required=False,
            ops_status="not_required",
            metadata_json=_json_text(
                {
                    "report_scope": offer["report_scope"],
                    "feature_flags": _feature_flags(offer),
                    "usage_bucket": offer["usage_bucket"],
                }
            ),
        )
        db.add(entitlement)
        db.flush()
    else:
        entitlement.status = status
        entitlement.checkout_session_id = checkout_session_id or entitlement.checkout_session_id
        entitlement.stripe_subscription_id = stripe_subscription_id or user.stripe_subscription_id
        entitlement.stripe_price_id = user.stripe_price_id
        _sync_subscription_quota(user, entitlement, offer)
    return entitlement


def _mark_subscription_entitlements_inactive(db: Session, user: User) -> None:
    rows = (
        db.query(BillingEntitlement)
        .filter(
            BillingEntitlement.user_id == user.id,
            BillingEntitlement.offer_id == "pro_lizenz",
            BillingEntitlement.status.in_(["active", "pending", "ops_pending"]),
        )
        .all()
    )
    for entitlement in rows:
        entitlement.status = "canceled"
        entitlement.updated_at = _utcnow()


def _payment_entitlement_exists(db: Session, checkout_session_id: str | None, offer_id: str) -> bool:
    if not checkout_session_id:
        return False
    return (
        db.query(BillingEntitlement)
        .filter(
            BillingEntitlement.checkout_session_id == checkout_session_id,
            BillingEntitlement.offer_id == offer_id,
        )
        .first()
        is not None
    )


def _session_offer_metadata(data_object: dict[str, Any]) -> tuple[str, str | None]:
    metadata = data_object.get("metadata") if isinstance(data_object.get("metadata"), dict) else {}
    offer_id = str(metadata.get("offer_id") or "")
    offer_name = str(metadata.get("offer_name") or "") or None
    return offer_id, offer_name


def _extract_session_price_id(data_object: dict[str, Any]) -> str | None:
    line_items = data_object.get("line_items")
    if isinstance(line_items, dict):
        items = line_items.get("data")
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                price = first.get("price")
                if isinstance(price, dict) and price.get("id"):
                    return str(price["id"])

    display_items = data_object.get("display_items")
    if isinstance(display_items, list) and display_items:
        first = display_items[0]
        if isinstance(first, dict) and first.get("price"):
            return str(first["price"])
    return None


def _sync_checkout_session_completion(
    db: Session,
    user: User,
    data_object: dict[str, Any],
) -> dict[str, Any]:
    customer_id = data_object.get("customer")
    subscription_id = data_object.get("subscription")
    checkout_session_id = str(data_object.get("id") or "") or None
    payment_intent_id = str(data_object.get("payment_intent") or "") or None
    payment_status = str(data_object.get("payment_status") or "")
    session_status = str(data_object.get("status") or "")
    offer_id, offer_name = _session_offer_metadata(data_object)
    price_id = _extract_session_price_id(data_object) or user.stripe_price_id
    synced = False

    if customer_id:
        user.stripe_customer_id = str(customer_id)

    if subscription_id and offer_id in SUBSCRIPTION_OFFER_IDS:
        user.stripe_subscription_id = str(subscription_id)
        if user.billing_status in PAID_ACCESS_STATUSES:
            next_status = user.billing_status
            next_entitlement_status = "active"
        else:
            next_status = "checkout_completed"
            next_entitlement_status = "pending"
        user.plan_tier = "pro" if next_status in PAID_ACCESS_STATUSES else "free"
        user.billing_status = next_status
        user.updated_at = _utcnow()
        _upsert_subscription_entitlement_from_offer(
            db,
            user,
            offer_id=offer_id,
            checkout_session_id=checkout_session_id,
            stripe_subscription_id=str(subscription_id),
            status=next_entitlement_status,
        )
        synced = True
    elif offer_id in PAYMENT_OFFER_IDS and payment_status == "paid":
        if not _payment_entitlement_exists(db, checkout_session_id, offer_id):
            _issue_payment_entitlement(
                db,
                user,
                offer_id=offer_id,
                checkout_session_id=checkout_session_id,
                payment_intent_id=payment_intent_id,
                stripe_price_id=price_id,
                status="active",
            )
        _apply_payment_purchase_user_state(user, offer_id=offer_id, stripe_price_id=price_id)
        synced = True
    elif offer_id in ADDON_OFFER_IDS and payment_status == "paid":
        if not _payment_entitlement_exists(db, checkout_session_id, offer_id):
            _issue_payment_entitlement(
                db,
                user,
                offer_id=offer_id,
                checkout_session_id=checkout_session_id,
                payment_intent_id=payment_intent_id,
                stripe_price_id=price_id,
                status="ops_pending",
            )
        synced = True

    if synced:
        track_checkout_completed(
            db,
            user,
            offer_id=offer_id or None,
            checkout_session_id=checkout_session_id,
            payment_status=payment_status or None,
        )

    return {
        "session_id": checkout_session_id,
        "offer_id": offer_id or None,
        "offer_name": offer_name,
        "session_status": session_status or None,
        "payment_status": payment_status or None,
        "synced": synced,
    }


def get_checkout_session_status(db: Session, user: User, session_id: str) -> dict[str, Any]:
    if not session_id or not session_id.strip():
        raise HTTPException(
            status_code=422,
            detail={
                "code": "BILLING_SESSION_ID_REQUIRED",
                "message": "Checkout-Session-ID fehlt.",
                "hint": "Bitte den Rueckweg aus Stripe mit gueltiger session_id aufrufen.",
            },
        )

    stripe_mod = _load_stripe_module()
    try:
        session = stripe_mod.checkout.Session.retrieve(session_id, expand=["line_items", "subscription"])
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BILLING_CHECKOUT_SESSION_NOT_FOUND",
                "message": "Stripe-Checkout-Session konnte nicht geladen werden.",
                "hint": "Bitte session_id pruefen oder Checkout erneut starten.",
            },
        ) from exc

    session_dict = _as_dict(session)
    resolved_user = _resolve_user_for_event(db, "checkout.session.completed", session_dict)
    if resolved_user is None or resolved_user.id != user.id:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BILLING_CHECKOUT_SESSION_NOT_FOUND",
                "message": "Diese Checkout-Session gehoert nicht zum eingeloggten Benutzer.",
                "hint": "Bitte mit dem richtigen Konto anmelden.",
            },
        )

    sync_result = {"session_id": session_id, "synced": False}
    if str(session_dict.get("status") or "") == "complete":
        sync_result = _sync_checkout_session_completion(db, user, session_dict)
        _record_billing_event(
            db,
            user_id=user.id,
            event_type="checkout.session.status",
            status="synced" if sync_result.get("synced") else "observed",
            payload=session_dict,
            checkout_session_id=session_dict.get("id"),
            provider_customer_id=session_dict.get("customer"),
            provider_subscription_id=session_dict.get("subscription"),
            amount_cents=session_dict.get("amount_total") if isinstance(session_dict.get("amount_total"), int) else None,
            currency=str(session_dict.get("currency")) if session_dict.get("currency") else None,
        )
        db.commit()
        db.refresh(user)

    return {
        **sync_result,
        "checkout_url": session_dict.get("url"),
        "billing": build_billing_overview(db, user),
    }


def handle_stripe_webhook(db: Session, payload: bytes, stripe_signature: str | None) -> dict[str, str]:
    # Billing-Hide-Schalter: wenn Billing in dieser Umgebung deaktiviert ist,
    # nehmen wir das Event entgegen, audit-loggen es und antworten mit 200,
    # damit Stripe nicht in einen Retry-Loop faellt. Es findet KEINE
    # User-/Subscription-Mutation statt.
    if not settings.billing_enabled:
        try:
            _record_billing_event(
                db,
                user_id=None,
                event_type="webhook_received_while_disabled",
                status="ignored",
                payload={
                    "raw_size": len(payload or b""),
                    "has_signature": bool(stripe_signature),
                },
            )
            db.commit()
        except Exception:
            db.rollback()
        return {"status": "ignored_billing_disabled"}
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "STRIPE_WEBHOOK_NOT_CONFIGURED",
                "message": "Stripe Webhook Secret fehlt.",
                "hint": "Bitte STRIPE_WEBHOOK_SECRET setzen.",
            },
        )
    stripe_mod = _load_stripe_module()
    try:
        event = stripe_mod.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "STRIPE_WEBHOOK_INVALID",
                "message": "Stripe-Webhook konnte nicht verifiziert werden.",
                "hint": "Signatur und Secret pruefen.",
            },
        ) from exc

    event_dict = _as_dict(event)
    provider_event_id = str(event_dict.get("id") or "")
    if provider_event_id:
        duplicate = (
            db.query(BillingEvent)
            .filter(BillingEvent.provider == "stripe", BillingEvent.provider_event_id == provider_event_id)
            .first()
        )
        if duplicate:
            return {"status": "duplicate"}

    event_type = str(event_dict.get("type") or "stripe.unknown")
    data = event_dict.get("data") or {}
    data_object = data.get("object") if isinstance(data, dict) else {}
    if not isinstance(data_object, dict):
        data_object = {}

    user = _resolve_user_for_event(db, event_type, data_object)
    if user:
        if event_type == "checkout.session.completed":
            _sync_checkout_session_completion(db, user, data_object)
        elif event_type in {"customer.subscription.created", "customer.subscription.updated"}:
            _apply_subscription_state(user, data_object)
            if user.billing_status in PAID_ACCESS_STATUSES:
                _upsert_subscription_entitlement_from_offer(
                    db,
                    user,
                    offer_id="pro_lizenz",
                    stripe_subscription_id=user.stripe_subscription_id,
                )
        elif event_type == "customer.subscription.deleted":
            _apply_subscription_state(user, data_object)
            user.plan_tier = "free"
            user.billing_status = "canceled"
            _mark_subscription_entitlements_inactive(db, user)
        elif event_type == "invoice.paid":
            if data_object.get("subscription"):
                user.billing_status = "active"
                user.plan_tier = "pro"
                user.updated_at = _utcnow()
                _upsert_subscription_entitlement_from_offer(
                    db,
                    user,
                    offer_id="pro_lizenz",
                    stripe_subscription_id=str(data_object.get("subscription")),
                    status="active",
                )
        elif event_type == "invoice.payment_failed":
            user.billing_status = "past_due"
            user.updated_at = _utcnow()

    _record_billing_event(
        db,
        user_id=user.id if user else None,
        event_type=event_type,
        status="processed",
        payload=event_dict,
        provider_event_id=provider_event_id or None,
        checkout_session_id=data_object.get("id") if event_type.startswith("checkout.session.") else data_object.get("checkout_session_id"),
        provider_customer_id=data_object.get("customer"),
        provider_subscription_id=data_object.get("id") if event_type.startswith("customer.subscription.") else data_object.get("subscription"),
        amount_cents=data_object.get("amount_total") if isinstance(data_object.get("amount_total"), int) else None,
        currency=str(data_object.get("currency")) if data_object.get("currency") else None,
    )
    db.commit()
    return {"status": "processed"}
