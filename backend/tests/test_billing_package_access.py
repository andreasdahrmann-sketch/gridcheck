from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from db.database import Base, get_db
from db.models import AnalysisRun, BillingEntitlement, BillingEvent, User
from main import app
from tests.postgres_test_utils import build_isolated_postgres_session_factory


def build_client():
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(Base.metadata, label="billing_package")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client._gridcheck_cleanup = cleanup  # type: ignore[attr-defined]
    client._gridcheck_session_factory = TestingSessionLocal  # type: ignore[attr-defined]
    return client


def _close_client(client: TestClient) -> None:
    app.dependency_overrides.clear()
    client.close()
    client._gridcheck_cleanup()  # type: ignore[attr-defined]


def _register_and_login(
    client: TestClient, email: str, password: str = "Passwort123!", *, role: str = "projektierer"
) -> dict:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "role": role})
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _db_session(client: TestClient):
    return client._gridcheck_session_factory()  # type: ignore[attr-defined]


def _promote_user_to_admin(client: TestClient, email: str) -> int:
    with _db_session(client) as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.role = "admin"
        db.commit()
        return int(user.id)


def _base_payload() -> dict:
    return {
        "nennspannung": 20,
        "leistung_mw": 4.5,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 4,
        "anschlussart": "Speicher",
        "plz": "10115",
        "anlagentyp": "PV",
        "project_components": [
            {"component_type": "pv", "capacity_kw": 2500},
            {"component_type": "battery", "capacity_kw": 2000, "energy_kwh": 4000},
        ],
        "storage_profile": {
            "has_storage": True,
            "operation_mode": "grid_support",
            "power_kw": 2000,
            "energy_kwh": 4000,
            "grid_support_services": ["peak_shaving"],
        },
        "environmental_route": {
            "route_length_km": 3.5,
            "crossings_count": 2,
            "protected_area_touch": True,
            "route_complexity": "hoch",
        },
    }


def test_basic_package_strips_premium_only_inputs(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "basic-rights@example.com")
        seen_payload: dict = {}

        from api import analyze_v2 as analyze_v2_api

        def fake_run(payload: dict, **kwargs) -> dict:
            seen_payload.clear()
            seen_payload.update(payload)
            return {
                "status": "OK",
                "scores": {"gesamt": 71},
                "fazit": {"entscheidung": "B"},
                "warnungen": [],
                "empfehlungen": ["Basisreport erstellt"],
                "revision": {"hash": "b" * 64},
            }

        monkeypatch.setattr(analyze_v2_api, "run_v1_analysis", fake_run)

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "basic-rights@example.com").first()
            assert user is not None
            db.add(
                BillingEntitlement(
                    user_id=user.id,
                    offer_id="basic_schnellcheck",
                    offer_category="pay_per_use",
                    package_scope="basic",
                    source="checkout",
                    status="active",
                    total_credits=1,
                    used_credits=0,
                    valid_from=datetime.now(timezone.utc),
                    metadata_json='{"report_scope":"basic"}',
                )
            )
            db.commit()

        payload = _base_payload()
        payload["requested_offer_id"] = "basic_schnellcheck"
        response = client.post("/api/v1/analyze", headers=_headers(tokens), json=payload)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["billing_access"]["package_scope"] == "basic"
        assert seen_payload["storage_profile"] is None
        assert seen_payload["environmental_route"] is None
        assert len(seen_payload["project_components"]) == 1

        with _db_session(client) as db:
            run = db.query(AnalysisRun).order_by(AnalysisRun.id.desc()).first()
            entitlement = db.query(BillingEntitlement).filter(BillingEntitlement.offer_id == "basic_schnellcheck").first()
            assert run is not None
            assert run.offer_id == "basic_schnellcheck"
            assert run.package_scope == "basic"
            assert run.usage_bucket == "oneoff"
            assert entitlement is not None
            assert entitlement.used_credits == 1
            assert entitlement.status == "consumed"

        billing = client.get("/api/v1/billing/status", headers=_headers(tokens))
        assert billing.status_code == 200, billing.text
        billing_body = billing.json()
        consumed_item = next(
            item for item in billing_body["entitlement_history"] if item["offer_id"] == "basic_schnellcheck"
        )
        assert consumed_item["status"] == "consumed"
        assert consumed_item["last_analysis_run_id"] is not None
        assert not any(item["offer_id"] == "basic_schnellcheck" for item in billing_body["active_entitlements"])
    finally:
        _close_client(client)


def test_stripe_webhooks_create_payment_and_subscription_entitlements(monkeypatch):
    client = build_client()
    try:
        _register_and_login(client, "stripe-hooks@example.com")
        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "stripe-hooks@example.com").first()
            assert user is not None
            user.stripe_customer_id = "cus_test_123"
            db.commit()
            user_id = user.id

        from services import billing_service

        fake_settings = replace(billing_service.settings, stripe_webhook_secret="whsec_test")
        monkeypatch.setattr(billing_service, "settings", fake_settings)

        class FakeWebhook:
            next_event: dict = {}

            @staticmethod
            def construct_event(payload, signature, secret):
                return FakeWebhook.next_event

        class FakeStripeModule:
            Webhook = FakeWebhook

        monkeypatch.setattr(billing_service, "_load_stripe_module", lambda: FakeStripeModule)

        FakeWebhook.next_event = {
            "id": "evt_checkout_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_basic",
                    "customer": "cus_test_123",
                    "payment_intent": "pi_test_basic",
                    "payment_status": "paid",
                    "status": "complete",
                    "metadata": {
                        "user_id": str(user_id),
                        "offer_id": "professional_anschlussstrategie",
                    },
                    "line_items": {"data": [{"price": {"id": "price_professional_test"}}]},
                }
            },
        }
        first = client.post("/api/v1/billing/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert first.status_code == 200, first.text

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "stripe-hooks@example.com").first()
            assert user is not None
            assert user.plan_tier == "professional"
            assert user.billing_status == "purchased"
            assert user.stripe_price_id == "price_professional_test"
            professional_entitlement = (
                db.query(BillingEntitlement)
                .filter(
                    BillingEntitlement.user_id == user.id,
                    BillingEntitlement.offer_id == "professional_anschlussstrategie",
                )
                .first()
            )
            assert professional_entitlement is not None
            assert professional_entitlement.status == "active"

        future_period_end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
        FakeWebhook.next_event = {
            "id": "evt_sub_1",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_123",
                    "customer": "cus_test_123",
                    "status": "active",
                    "current_period_end": future_period_end,
                    "items": {"data": [{"price": {"id": "price_pro_123"}}]},
                }
            },
        }
        second = client.post("/api/v1/billing/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert second.status_code == 200, second.text

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "stripe-hooks@example.com").first()
            assert user is not None
            assert user.plan_tier == "pro"
            assert user.billing_status == "active"
            entitlements = (
                db.query(BillingEntitlement)
                .filter(BillingEntitlement.user_id == user.id)
                .order_by(BillingEntitlement.id.asc())
                .all()
            )
            assert len(entitlements) == 2
            assert user.plan_tier == "pro"
            assert user.billing_status == "active"
            assert entitlements[0].offer_id == "professional_anschlussstrategie"
            assert entitlements[0].status == "active"
            assert entitlements[1].offer_id == "pro_lizenz"
            assert entitlements[1].status == "active"
            assert entitlements[1].total_credits == 20
            assert entitlements[1].stripe_subscription_id == "sub_test_123"
    finally:
        _close_client(client)


def test_billing_status_exposes_subscription_attention_states(monkeypatch):
    client = build_client()
    try:
        from services import billing_service

        fake_settings = replace(billing_service.settings, stripe_secret_key="sk_test")
        monkeypatch.setattr(billing_service, "settings", fake_settings)

        past_due_tokens = _register_and_login(client, "past-due@example.com")
        checkout_tokens = _register_and_login(client, "checkout-pending@example.com")
        canceled_tokens = _register_and_login(client, "canceled@example.com")

        with _db_session(client) as db:
            past_due_user = db.query(User).filter(User.email == "past-due@example.com").first()
            checkout_user = db.query(User).filter(User.email == "checkout-pending@example.com").first()
            canceled_user = db.query(User).filter(User.email == "canceled@example.com").first()
            assert past_due_user is not None
            assert checkout_user is not None
            assert canceled_user is not None

            future_period_end = datetime.now(timezone.utc) + timedelta(days=15)

            past_due_user.plan_tier = "pro"
            past_due_user.billing_status = "past_due"
            past_due_user.stripe_customer_id = "cus_past_due"
            past_due_user.stripe_subscription_id = "sub_past_due"
            past_due_user.billing_current_period_end = future_period_end

            checkout_user.plan_tier = "pro"
            checkout_user.billing_status = "checkout_completed"
            checkout_user.stripe_customer_id = "cus_checkout_pending"
            checkout_user.stripe_subscription_id = "sub_checkout_pending"
            checkout_user.billing_current_period_end = future_period_end

            canceled_user.plan_tier = "free"
            canceled_user.billing_status = "canceled"
            canceled_user.stripe_customer_id = "cus_canceled"
            canceled_user.stripe_subscription_id = "sub_canceled"
            canceled_user.billing_current_period_end = future_period_end
            db.commit()

        past_due = client.get("/api/v1/billing/status", headers=_headers(past_due_tokens))
        assert past_due.status_code == 200, past_due.text
        past_due_body = past_due.json()
        assert past_due_body["subscription_state"] == "past_due"
        assert past_due_body["billing_attention"]["action"] == "open_portal"
        assert past_due_body["has_active_subscription"] is False
        assert past_due_body["customer_portal_available"] is True
        assert "pro_lizenz" not in past_due_body["recommended_offer_ids"]
        assert not any(item["offer_id"] == "pro_lizenz" for item in past_due_body["active_entitlements"])

        checkout_pending = client.get("/api/v1/billing/status", headers=_headers(checkout_tokens))
        assert checkout_pending.status_code == 200, checkout_pending.text
        checkout_body = checkout_pending.json()
        assert checkout_body["subscription_state"] == "checkout_pending"
        assert checkout_body["billing_attention"]["action"] == "wait"
        assert checkout_body["has_active_subscription"] is False
        assert checkout_body["customer_portal_available"] is False

        canceled = client.get("/api/v1/billing/status", headers=_headers(canceled_tokens))
        assert canceled.status_code == 200, canceled.text
        canceled_body = canceled.json()
        assert canceled_body["subscription_state"] == "canceled"
        assert canceled_body["billing_attention"]["action"] == "open_portal"
        assert canceled_body["customer_portal_available"] is True
    finally:
        _close_client(client)


def test_subscription_checkout_stays_pending_until_stripe_activation(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "subscription-pending@example.com")
        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "subscription-pending@example.com").first()
            assert user is not None
            user.stripe_customer_id = "cus_subscription_pending"
            db.commit()
            user_id = user.id

        from services import billing_service

        fake_settings = replace(billing_service.settings, stripe_secret_key="sk_test", free_checks_limit=0)
        monkeypatch.setattr(billing_service, "settings", fake_settings)

        class FakeCheckoutSession:
            @staticmethod
            def retrieve(session_id, expand=None):
                assert session_id == "cs_sub_pending"
                return {
                    "id": "cs_sub_pending",
                    "status": "complete",
                    "payment_status": "unpaid",
                    "customer": "cus_subscription_pending",
                    "subscription": "sub_pending_123",
                    "client_reference_id": str(user_id),
                    "metadata": {
                        "user_id": str(user_id),
                        "offer_id": "pro_lizenz",
                        "offer_name": "Pro Lizenz",
                    },
                    "line_items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_pro_pending",
                                }
                            }
                        ]
                    },
                }

        class FakeStripeModule:
            class checkout:
                Session = FakeCheckoutSession

        monkeypatch.setattr(billing_service, "_load_stripe_module", lambda: FakeStripeModule)

        response = client.get(
            "/api/v1/billing/checkout-session?session_id=cs_sub_pending",
            headers=_headers(tokens),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["synced"] is True
        assert body["billing"]["subscription_state"] == "checkout_pending"
        assert body["billing"]["has_active_subscription"] is False
        assert body["billing"]["can_run_analysis"] is False
        assert not any(item["offer_id"] == "pro_lizenz" for item in body["billing"]["active_entitlements"])
        pending_item = next(item for item in body["billing"]["entitlement_history"] if item["offer_id"] == "pro_lizenz")
        assert pending_item["status"] == "pending"

        with _db_session(client) as db:
            user = db.query(User).filter(User.id == user_id).first()
            assert user is not None
            assert user.billing_status == "checkout_completed"
            assert user.plan_tier == "free"
    finally:
        _close_client(client)


def test_past_due_without_other_access_blocks_subscription_analysis(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "past-due-blocked@example.com")

        from services import billing_service

        fake_settings = replace(billing_service.settings, stripe_secret_key="sk_test", free_checks_limit=0)
        monkeypatch.setattr(billing_service, "settings", fake_settings)

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "past-due-blocked@example.com").first()
            assert user is not None
            user.plan_tier = "pro"
            user.billing_status = "past_due"
            user.stripe_customer_id = "cus_past_due_blocked"
            user.stripe_subscription_id = "sub_past_due_blocked"
            user.billing_current_period_end = datetime.now(timezone.utc) + timedelta(days=10)
            db.commit()

        billing = client.get("/api/v1/billing/status", headers=_headers(tokens))
        assert billing.status_code == 200, billing.text
        billing_body = billing.json()
        assert billing_body["subscription_state"] == "past_due"
        assert billing_body["has_active_subscription"] is False
        assert billing_body["can_run_analysis"] is False
        assert billing_body["upgrade_required"] is True
        assert billing_body["billing_state_label"] == "past_due"
        assert billing_body["customer_portal_available"] is True
        assert billing_body["analysis_options"] == []
        assert "pro_lizenz" not in billing_body["recommended_offer_ids"]
        assert not any(item["offer_id"] == "pro_lizenz" for item in billing_body["active_entitlements"])

        blocked = client.post(
            "/api/v1/analyze",
            headers=_headers(tokens),
            json={**_base_payload(), "requested_offer_id": "pro_lizenz"},
        )
        assert blocked.status_code == 402, blocked.text
        blocked_body = blocked.json()["detail"]
        assert blocked_body["code"] == "SUBSCRIPTION_PAYMENT_REQUIRED"
        assert blocked_body["billing"]["subscription_state"] == "past_due"
        assert blocked_body["billing"]["customer_portal_available"] is True
    finally:
        _close_client(client)


def test_past_due_keeps_oneoff_credits_usable(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "past-due-oneoff@example.com")
        seen_payload: dict = {}

        from api import analyze_v2 as analyze_v2_api
        from services import billing_service

        fake_settings = replace(billing_service.settings, stripe_secret_key="sk_test", free_checks_limit=0)
        monkeypatch.setattr(billing_service, "settings", fake_settings)

        def fake_run(payload: dict, **kwargs) -> dict:
            seen_payload.clear()
            seen_payload.update(payload)
            return {
                "status": "OK",
                "scores": {"gesamt": 74},
                "fazit": {"entscheidung": "B"},
                "warnungen": [],
                "empfehlungen": ["One-off fallback genutzt"],
                "revision": {"hash": "p" * 64},
            }

        monkeypatch.setattr(analyze_v2_api, "run_v1_analysis", fake_run)

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "past-due-oneoff@example.com").first()
            assert user is not None
            user.plan_tier = "pro"
            user.billing_status = "past_due"
            user.stripe_customer_id = "cus_past_due_oneoff"
            user.stripe_subscription_id = "sub_past_due_oneoff"
            user.billing_current_period_end = datetime.now(timezone.utc) + timedelta(days=10)
            db.add(
                BillingEntitlement(
                    user_id=user.id,
                    offer_id="premium_pre_check",
                    offer_category="pay_per_use",
                    package_scope="premium",
                    source="checkout",
                    status="active",
                    total_credits=1,
                    used_credits=0,
                    valid_from=datetime.now(timezone.utc),
                    metadata_json='{"report_scope":"premium"}',
                )
            )
            db.commit()

        response = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["billing_access"]["offer_id"] == "premium_pre_check"
        assert body["billing_access"]["package_scope"] == "premium"
        assert seen_payload["requested_offer_id"] == "premium_pre_check"

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "past-due-oneoff@example.com").first()
            assert user is not None
            assert user.billing_status == "past_due"
            premium = (
                db.query(BillingEntitlement)
                .filter(BillingEntitlement.user_id == user.id, BillingEntitlement.offer_id == "premium_pre_check")
                .one()
            )
            assert premium.used_credits == 1
            assert premium.status == "consumed"
            runs = db.query(AnalysisRun).filter(AnalysisRun.user_id == user.id).all()
            assert len(runs) == 1
            assert runs[0].offer_id == "premium_pre_check"
    finally:
        _close_client(client)


def test_checkout_session_status_syncs_paid_entitlement_idempotently(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "checkout-status@example.com")
        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "checkout-status@example.com").first()
            assert user is not None
            user.stripe_customer_id = "cus_checkout_status"
            db.commit()
            user_id = user.id

        from services import billing_service

        class FakeCheckoutSession:
            @staticmethod
            def retrieve(session_id, expand=None):
                assert session_id == "cs_paid_123"
                return {
                    "id": "cs_paid_123",
                    "status": "complete",
                    "payment_status": "paid",
                    "customer": "cus_checkout_status",
                    "payment_intent": "pi_paid_123",
                    "client_reference_id": str(user_id),
                    "metadata": {
                        "user_id": str(user_id),
                        "offer_id": "premium_pre_check",
                        "offer_name": "Premium Pre-Check",
                    },
                    "line_items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_premium_123",
                                }
                            }
                        ]
                    },
                }

        class FakeStripeModule:
            class checkout:
                Session = FakeCheckoutSession

        monkeypatch.setattr(billing_service, "_load_stripe_module", lambda: FakeStripeModule)

        first = client.get(
            "/api/v1/billing/checkout-session?session_id=cs_paid_123",
            headers=_headers(tokens),
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["synced"] is True
        assert first_body["offer_id"] == "premium_pre_check"
        assert first_body["billing"]["has_prepaid_credits"] is True
        assert first_body["billing"]["billing_state_label"] == "credits"
        assert any(item["offer_id"] == "premium_pre_check" for item in first_body["billing"]["active_entitlements"])
        assert any(
            event["event_type"] == "checkout.session.status" for event in first_body["billing"]["recent_billing_events"]
        )

        second = client.get(
            "/api/v1/billing/checkout-session?session_id=cs_paid_123",
            headers=_headers(tokens),
        )
        assert second.status_code == 200, second.text
        second_body = second.json()
        assert second_body["synced"] is True

        with _db_session(client) as db:
            entitlements = (
                db.query(BillingEntitlement)
                .filter(BillingEntitlement.user_id == user_id, BillingEntitlement.offer_id == "premium_pre_check")
                .all()
            )
            assert len(entitlements) == 1
            assert entitlements[0].status == "active"
    finally:
        _close_client(client)


def test_billing_status_exposes_ops_followups(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "ops-followup@example.com")
        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "ops-followup@example.com").first()
            assert user is not None

            professional = BillingEntitlement(
                user_id=user.id,
                offer_id="professional_anschlussstrategie",
                offer_category="pay_per_use",
                package_scope="professional",
                source="checkout",
                status="active",
                total_credits=1,
                used_credits=0,
                valid_from=datetime.now(timezone.utc),
                checkout_session_id="cs_prof_ops",
                ops_followup_required=True,
                ops_status="pending_review",
                metadata_json='{"report_scope":"professional"}',
            )
            express = BillingEntitlement(
                user_id=user.id,
                offer_id="express_upgrade",
                offer_category="addon",
                package_scope="addon",
                source="checkout",
                status="ops_pending",
                total_credits=None,
                used_credits=0,
                valid_from=datetime.now(timezone.utc),
                checkout_session_id="cs_express_ops",
                express_requested=True,
                ops_followup_required=True,
                ops_status="pending_review",
                metadata_json='{"report_scope":"none"}',
            )
            db.add(professional)
            db.add(express)
            db.flush()
            db.add(
                AnalysisRun(
                    user_id=user.id,
                    project_id=None,
                    source="interactive",
                    status="completed",
                    input_json="{}",
                    request_checksum="req_ops",
                    result_json="{}",
                    result_checksum="res_ops",
                    score=84,
                    decision_code="B",
                    revision_hash="o" * 64,
                    offer_id="professional_anschlussstrategie",
                    package_scope="professional",
                    usage_bucket="oneoff",
                    entitlement_id=professional.id,
                    billing_category="paid",
                    free_quota_consumed=False,
                )
            )
            db.commit()

        response = client.get("/api/v1/billing/status", headers=_headers(tokens))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["has_ops_pending"] is True
        assert body["open_ops_followups_count"] == 2
        assert len(body["ops_followups"]) == 2
        assert any(item["offer_id"] == "professional_anschlussstrategie" for item in body["ops_followups"])
        assert any("Express-Pfad" in item["next_action"] for item in body["ops_followups"])
        assert "status" in body["stripe_readiness"]
        assert "offers" in body["stripe_readiness"]
    finally:
        _close_client(client)


def test_checkout_session_create_failure_returns_controlled_error(monkeypatch):
    client = build_client()
    try:
        _register_and_login(client, "checkout-failure@example.com")
        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "checkout-failure@example.com").first()
            assert user is not None

            from services import billing_service

            fake_settings = replace(
                billing_service.settings,
                stripe_secret_key="sk_test",
                stripe_price_pro_license_id="price_pro_test",
                stripe_checkout_success_url="https://example.com/settings",
                stripe_checkout_cancel_url="https://example.com/settings",
            )
            monkeypatch.setattr(billing_service, "settings", fake_settings)

            class FakeCustomer:
                @staticmethod
                def create(**kwargs):
                    return {"id": "cus_checkout_failure", **kwargs}

            class FakeCheckoutSession:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("invalid price")

            class FakeStripeModule:
                Customer = FakeCustomer

                class checkout:
                    Session = FakeCheckoutSession

            monkeypatch.setattr(billing_service, "_load_stripe_module", lambda: FakeStripeModule)

            with pytest.raises(HTTPException) as exc:
                billing_service.create_checkout_session(db, user, "pro_lizenz")
            assert exc.value.status_code == 502
            assert exc.value.detail["code"] == "STRIPE_CHECKOUT_FAILED"
    finally:
        _close_client(client)


def test_subscription_checkout_is_blocked_while_pending_or_active(monkeypatch):
    client = build_client()
    try:
        _register_and_login(client, "checkout-guard@example.com")
        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "checkout-guard@example.com").first()
            assert user is not None

            from services import billing_service

            fake_settings = replace(
                billing_service.settings,
                stripe_secret_key="sk_test",
                stripe_price_pro_license_id="price_pro_test",
            )
            monkeypatch.setattr(billing_service, "settings", fake_settings)

            user.billing_status = "checkout_completed"
            user.plan_tier = "free"
            with pytest.raises(HTTPException) as pending_exc:
                billing_service.create_checkout_session(db, user, "pro_lizenz")
            assert pending_exc.value.status_code == 409
            assert pending_exc.value.detail["code"] == "BILLING_SUBSCRIPTION_ALREADY_IN_PROGRESS"

            user.billing_status = "active"
            user.plan_tier = "pro"
            user.stripe_customer_id = "cus_existing_subscription"
            with pytest.raises(HTTPException) as active_exc:
                billing_service.create_checkout_session(db, user, "pro_lizenz")
            assert active_exc.value.status_code == 409
            assert active_exc.value.detail["code"] == "BILLING_SUBSCRIPTION_ALREADY_IN_PROGRESS"
    finally:
        _close_client(client)


def test_admin_ops_followup_queue_claim_and_complete_flow():
    client = build_client()
    try:
        admin_tokens = _register_and_login(client, "ops-admin@example.com")
        user_tokens = _register_and_login(client, "ops-customer@example.com")
        admin_id = _promote_user_to_admin(client, "ops-admin@example.com")

        with _db_session(client) as db:
            admin = db.query(User).filter(User.email == "ops-admin@example.com").first()
            customer = db.query(User).filter(User.email == "ops-customer@example.com").first()
            assert admin is not None
            assert customer is not None

            entitlement = BillingEntitlement(
                user_id=customer.id,
                offer_id="professional_anschlussstrategie",
                offer_category="pay_per_use",
                package_scope="professional",
                source="checkout",
                status="active",
                total_credits=1,
                used_credits=0,
                valid_from=datetime.now(timezone.utc),
                checkout_session_id="cs_ops_claim",
                ops_followup_required=True,
                ops_status="pending_review",
                metadata_json='{"report_scope":"professional"}',
            )
            db.add(entitlement)
            db.flush()
            db.add(
                AnalysisRun(
                    user_id=customer.id,
                    project_id=None,
                    source="interactive",
                    status="completed",
                    input_json="{}",
                    request_checksum="req_ops_admin",
                    result_json="{}",
                    result_checksum="res_ops_admin",
                    score=82,
                    decision_code="B",
                    revision_hash="q" * 64,
                    offer_id="professional_anschlussstrategie",
                    package_scope="professional",
                    usage_bucket="oneoff",
                    entitlement_id=entitlement.id,
                    billing_category="paid",
                    free_quota_consumed=False,
                )
            )
            db.commit()
            entitlement_id = entitlement.id

        forbidden = client.get("/api/v1/ops-followups", headers=_headers(user_tokens))
        assert forbidden.status_code == 403, forbidden.text

        listing = client.get("/api/v1/ops-followups", headers=_headers(admin_tokens))
        assert listing.status_code == 200, listing.text
        listing_body = listing.json()
        assert len(listing_body) == 1
        assert listing_body[0]["customer_email"] == "ops-customer@example.com"
        assert listing_body[0]["ops_status"] == "pending_review"

        claimed = client.post(
            f"/api/v1/ops-followups/{entitlement_id}/claim",
            headers=_headers(admin_tokens),
            json={"comment": "Fall uebernommen"},
        )
        assert claimed.status_code == 200, claimed.text
        claim_body = claimed.json()
        assert claim_body["ops_status"] == "in_progress"
        assert claim_body["ops_assignee_user_id"] == admin_id
        assert claim_body["ops_last_comment"] == "Fall uebernommen"

        completed = client.patch(
            f"/api/v1/ops-followups/{entitlement_id}",
            headers=_headers(admin_tokens),
            json={"status": "completed", "comment": "Abschluss dokumentiert"},
        )
        assert completed.status_code == 200, completed.text
        completed_body = completed.json()
        assert completed_body["ops_status"] == "completed"
        assert completed_body["ops_last_comment"] == "Abschluss dokumentiert"

        with _db_session(client) as db:
            entitlement = db.query(BillingEntitlement).filter(BillingEntitlement.id == entitlement_id).first()
            assert entitlement is not None
            assert entitlement.ops_assignee_user_id == admin_id
            assert entitlement.ops_status == "completed"
            assert entitlement.ops_started_at is not None
            assert entitlement.ops_completed_at is not None
            events = (
                db.query(BillingEvent)
                .filter(BillingEvent.checkout_session_id == "cs_ops_claim")
                .order_by(BillingEvent.id.asc())
                .all()
            )
            event_types = [item.event_type for item in events]
            assert "ops.followup.claimed" in event_types
            assert "ops.followup.status_changed" in event_types
    finally:
        _close_client(client)


def test_ops_followup_status_transition_is_enforced():
    client = build_client()
    try:
        admin_tokens = _register_and_login(client, "ops-transition-admin@example.com")
        _register_and_login(client, "ops-transition-user@example.com")
        _promote_user_to_admin(client, "ops-transition-admin@example.com")

        with _db_session(client) as db:
            customer = db.query(User).filter(User.email == "ops-transition-user@example.com").first()
            assert customer is not None
            entitlement = BillingEntitlement(
                user_id=customer.id,
                offer_id="express_upgrade",
                offer_category="addon",
                package_scope="addon",
                source="checkout",
                status="ops_pending",
                total_credits=None,
                used_credits=0,
                valid_from=datetime.now(timezone.utc),
                checkout_session_id="cs_ops_transition",
                express_requested=True,
                ops_followup_required=True,
                ops_status="pending_review",
                metadata_json='{"report_scope":"none"}',
            )
            db.add(entitlement)
            db.commit()
            entitlement_id = entitlement.id

        invalid = client.patch(
            f"/api/v1/ops-followups/{entitlement_id}",
            headers=_headers(admin_tokens),
            json={"status": "completed", "comment": "Zu frueh"},
        )
        assert invalid.status_code == 409, invalid.text
        assert invalid.json()["detail"]["code"] == "OPS_STATUS_TRANSITION_INVALID"
    finally:
        _close_client(client)


def test_report_scope_differs_between_basic_and_premium(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "report-scope@example.com")

        from api import v2_reports as reports_api
        from engine.revision import speichere_revision

        def fake_run(payload: dict, **kwargs) -> dict:
            result = {
                "status": "OK",
                "eingabe": payload,
                "warnungen": ["Leitungslast nahe Grenzwert"],
                "empfehlungen": ["NVP-Alternative pruefen"],
                "n1": {"n1_sicher": False, "topologie_text": "Topologie unbekannt"},
                "fazit": {"entscheidung": "C"},
                "projektprofil": {"summary": "Hybridprofil"},
                "speicher_bewertung": {"summary": "Netzdienlicher Speicher"},
                "route_environment": {"summary": "Mittleres Trassenrisiko"},
                "stakeholder_bewertung": {
                    "konflikt_summary": "Stakeholder-Zielkonflikt vorhanden",
                    "recommended_focus": "Fokus auf Varianten- und Trassenargumentation",
                },
                "transparenz": {
                    "confidence_notes": ["Datenqualitaet B"],
                    "disclaimers": ["Keine Kapazitaetsgarantie"],
                },
                "kosten": {"investition_gesamt_eur": 500000},
            }
            with _db_session(client) as db:
                user = db.query(User).filter(User.email == "report-scope@example.com").first()
                assert user is not None
                rev_meta = speichere_revision(
                    result,
                    engine_version="test-report-scope",
                    actor_user_id=user.id,
                    db=db,
                )
                db.commit()
            result["revision"] = {"hash": rev_meta["hash"]}
            return result

        monkeypatch.setattr(reports_api, "run_v1_analysis", fake_run)

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "report-scope@example.com").first()
            assert user is not None
            db.add(
                BillingEntitlement(
                    user_id=user.id,
                    offer_id="premium_pre_check",
                    offer_category="pay_per_use",
                    package_scope="premium",
                    source="checkout",
                    status="active",
                    total_credits=1,
                    used_credits=0,
                    valid_from=datetime.now(timezone.utc),
                    metadata_json='{"report_scope":"premium"}',
                )
            )
            db.commit()

        basic = client.post(
            "/api/v2/reports/invest",
            headers=_headers(tokens),
            json={"analyze_request": {**_base_payload(), "requested_offer_id": "free"}},
        )
        assert basic.status_code == 200, basic.text
        basic_html = basic.json()["html"]
        assert "Paketgrenze" in basic_html
        assert "Kosten-Indikation" not in basic_html

        premium = client.post(
            "/api/v2/reports/invest",
            headers=_headers(tokens),
            json={"analyze_request": {**_base_payload(), "requested_offer_id": "premium_pre_check"}},
        )
        assert premium.status_code == 200, premium.text
        premium_html = premium.json()["html"]
        assert "Kosten-Indikation" in premium_html
        assert "Paketgrenze" not in premium_html
    finally:
        _close_client(client)


def _install_fake_stripe_webhook(monkeypatch, billing_service, **setting_overrides):
    fake_settings = replace(
        billing_service.settings,
        stripe_webhook_secret="whsec_test",
        **setting_overrides,
    )
    monkeypatch.setattr(billing_service, "settings", fake_settings)

    class FakeWebhook:
        next_event: dict = {}

        @staticmethod
        def construct_event(payload, signature, secret):
            return FakeWebhook.next_event

    class FakeStripeModule:
        Webhook = FakeWebhook

    monkeypatch.setattr(billing_service, "_load_stripe_module", lambda: FakeStripeModule)
    return FakeWebhook


def test_delayed_subscription_updated_does_not_reactivate_canceled_pro(monkeypatch):
    """Retried customer.subscription.updated after deleted must not restore Pro."""
    client = build_client()
    try:
        tokens = _register_and_login(client, "canceled-sub-updated@example.com")
        from services import billing_service

        FakeWebhook = _install_fake_stripe_webhook(
            monkeypatch, billing_service, stripe_secret_key="sk_test", free_checks_limit=0
        )

        future_period_end = int((datetime.now(timezone.utc) + timedelta(days=20)).timestamp())
        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "canceled-sub-updated@example.com").first()
            assert user is not None
            user.plan_tier = "free"
            user.billing_status = "canceled"
            user.stripe_customer_id = "cus_canceled_sub_updated"
            user.stripe_subscription_id = "sub_canceled_sub_updated"
            user.billing_current_period_end = datetime.now(timezone.utc) - timedelta(days=1)
            db.add(
                BillingEntitlement(
                    user_id=user.id,
                    offer_id="pro_lizenz",
                    offer_category="subscription",
                    package_scope="professional",
                    source="subscription",
                    status="canceled",
                    total_credits=20,
                    used_credits=20,
                    valid_from=datetime.now(timezone.utc) - timedelta(days=40),
                    stripe_subscription_id="sub_canceled_sub_updated",
                    metadata_json='{"report_scope":"professional"}',
                )
            )
            db.commit()
            user_id = user.id

        FakeWebhook.next_event = {
            "id": "evt_sub_updated_after_cancel",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_canceled_sub_updated",
                    "customer": "cus_canceled_sub_updated",
                    "status": "active",
                    "current_period_end": future_period_end,
                    "items": {"data": [{"price": {"id": "price_pro_stale"}}]},
                }
            },
        }
        response = client.post("/api/v1/billing/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "processed"

        with _db_session(client) as db:
            user = db.query(User).filter(User.id == user_id).first()
            assert user is not None
            assert user.plan_tier == "free"
            assert user.billing_status == "canceled"
            entitlements = (
                db.query(BillingEntitlement)
                .filter(BillingEntitlement.user_id == user.id, BillingEntitlement.offer_id == "pro_lizenz")
                .all()
            )
            assert entitlements
            assert all(row.status == "canceled" for row in entitlements)
            assert not any(row.status == "active" for row in entitlements)

        blocked = client.post(
            "/api/v1/analyze",
            headers=_headers(tokens),
            json={**_base_payload(), "requested_offer_id": "pro_lizenz"},
        )
        assert blocked.status_code == 402, blocked.text
        assert blocked.json()["detail"]["code"] == "FREE_TIER_LIMIT"
    finally:
        _close_client(client)


def test_delayed_subscription_deleted_does_not_cancel_newer_pro(monkeypatch):
    """Delayed deleted for an old subscription must not wipe a newer live Pro."""
    client = build_client()
    try:
        _register_and_login(client, "newer-sub-kept@example.com")
        from services import billing_service

        FakeWebhook = _install_fake_stripe_webhook(monkeypatch, billing_service)

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "newer-sub-kept@example.com").first()
            assert user is not None
            user.plan_tier = "pro"
            user.billing_status = "active"
            user.stripe_customer_id = "cus_newer_sub_kept"
            user.stripe_subscription_id = "sub_new_live"
            user.billing_current_period_end = datetime.now(timezone.utc) + timedelta(days=25)
            db.add(
                BillingEntitlement(
                    user_id=user.id,
                    offer_id="pro_lizenz",
                    offer_category="subscription",
                    package_scope="professional",
                    source="subscription",
                    status="active",
                    total_credits=20,
                    used_credits=0,
                    valid_from=datetime.now(timezone.utc),
                    stripe_subscription_id="sub_new_live",
                    metadata_json='{"report_scope":"professional"}',
                )
            )
            db.commit()
            user_id = user.id

        FakeWebhook.next_event = {
            "id": "evt_old_sub_deleted",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_old_canceled",
                    "customer": "cus_newer_sub_kept",
                    "status": "canceled",
                }
            },
        }
        response = client.post("/api/v1/billing/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert response.status_code == 200, response.text

        with _db_session(client) as db:
            user = db.query(User).filter(User.id == user_id).first()
            assert user is not None
            assert user.plan_tier == "pro"
            assert user.billing_status == "active"
            assert user.stripe_subscription_id == "sub_new_live"
            entitlement = (
                db.query(BillingEntitlement)
                .filter(BillingEntitlement.user_id == user.id, BillingEntitlement.offer_id == "pro_lizenz")
                .one()
            )
            assert entitlement.status == "active"
            assert entitlement.stripe_subscription_id == "sub_new_live"
    finally:
        _close_client(client)


def test_subscription_updated_activates_new_sub_after_cancel(monkeypatch):
    """A new Stripe subscription id after cancel must still activate Pro."""
    client = build_client()
    try:
        _register_and_login(client, "resub-after-cancel@example.com")
        from services import billing_service

        FakeWebhook = _install_fake_stripe_webhook(monkeypatch, billing_service)
        future_period_end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "resub-after-cancel@example.com").first()
            assert user is not None
            user.plan_tier = "free"
            user.billing_status = "canceled"
            user.stripe_customer_id = "cus_resub_after_cancel"
            user.stripe_subscription_id = "sub_old_canceled"
            db.add(
                BillingEntitlement(
                    user_id=user.id,
                    offer_id="pro_lizenz",
                    offer_category="subscription",
                    package_scope="professional",
                    source="subscription",
                    status="canceled",
                    total_credits=20,
                    used_credits=20,
                    valid_from=datetime.now(timezone.utc) - timedelta(days=40),
                    stripe_subscription_id="sub_old_canceled",
                    metadata_json='{"report_scope":"professional"}',
                )
            )
            db.commit()
            user_id = user.id

        FakeWebhook.next_event = {
            "id": "evt_new_sub_created",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_new_resubscribe",
                    "customer": "cus_resub_after_cancel",
                    "status": "active",
                    "current_period_end": future_period_end,
                    "items": {"data": [{"price": {"id": "price_pro_resub"}}]},
                }
            },
        }
        response = client.post("/api/v1/billing/webhook", content=b"{}", headers={"Stripe-Signature": "sig"})
        assert response.status_code == 200, response.text

        with _db_session(client) as db:
            user = db.query(User).filter(User.id == user_id).first()
            assert user is not None
            assert user.plan_tier == "pro"
            assert user.billing_status == "active"
            assert user.stripe_subscription_id == "sub_new_resubscribe"
            active = (
                db.query(BillingEntitlement)
                .filter(
                    BillingEntitlement.user_id == user.id,
                    BillingEntitlement.offer_id == "pro_lizenz",
                    BillingEntitlement.status == "active",
                )
                .one()
            )
            assert active.stripe_subscription_id == "sub_new_resubscribe"
    finally:
        _close_client(client)
