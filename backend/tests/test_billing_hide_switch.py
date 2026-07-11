"""Billing-Hide-Schalter (BILLING_ENABLED) Regression.

Pflicht-Verhalten:
- Default (`billing_enabled=False`) → Routen unter /api/v1/billing/* antworten 503
  mit Code BILLING_DISABLED, EXCEPT der Stripe-Webhook (der nimmt das Event auf
  und beantwortet es ohne DB-Persistenz mit 200, damit Stripe nicht in einen
  Retry-Loop faellt).
- Admin (User.role == "admin") umgeht den 503 weiterhin.
- has_paid_access ignoriert den DB-Stand bei deaktiviertem Billing fuer
  Nicht-Admins (Frontend muss ohne Stripe-Pfad strikt Free-Erlebnis sehen).
"""
from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from db.database import Base, get_db
from db.models import BillingEvent, User
from main import app
from tests.postgres_test_utils import build_isolated_postgres_session_factory


def _build_client():
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(
        Base.metadata, label="billing_hide_switch"
    )

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


def _db_session(client: TestClient):
    return client._gridcheck_session_factory()  # type: ignore[attr-defined]


def _register_and_login(
    client: TestClient,
    email: str,
    password: str = "Passwort123!",
    *,
    role: str = "projektierer",
) -> dict:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _set_user_role(client: TestClient, email: str, role: str) -> int:
    with _db_session(client) as db:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None, f"user {email} not found"
        user.role = role
        db.commit()
        return int(user.id)


def _set_billing_enabled(monkeypatch: pytest.MonkeyPatch, *, enabled: bool) -> None:
    """Patch settings in allen Modulen, die das Flag lesen."""
    from core import billing_flags
    from core import config as core_config
    from services import billing_service

    fake = replace(core_config.settings, billing_enabled=enabled)
    monkeypatch.setattr(core_config, "settings", fake)
    monkeypatch.setattr(billing_flags, "settings", fake)
    monkeypatch.setattr(billing_service, "settings", fake)


def test_billing_routes_return_503_when_disabled(monkeypatch):
    """Nicht-Admin sieht 503 mit BILLING_DISABLED, sobald der Schalter aus ist."""
    client = _build_client()
    try:
        _set_billing_enabled(monkeypatch, enabled=False)
        tokens = _register_and_login(client, "billing-disabled-user@example.com")

        status = client.get("/api/v1/billing/status", headers=_headers(tokens))
        assert status.status_code == 503, status.text
        body = status.json()
        assert body["detail"]["code"] == "BILLING_DISABLED"

        catalog = client.get("/api/v1/billing/catalog")
        assert catalog.status_code == 503, catalog.text
        assert catalog.json()["detail"]["code"] == "BILLING_DISABLED"

        checkout = client.post(
            "/api/v1/billing/checkout",
            headers=_headers(tokens),
            json={"offer_id": "pro_lizenz"},
        )
        # 503 bevor CSRF/Stripe gerufen wird
        assert checkout.status_code == 503, checkout.text
    finally:
        _close_client(client)


def test_admin_bypasses_503_when_disabled(monkeypatch):
    """Admin (User.role == 'admin') umgeht den 503-Schalter weiterhin."""
    client = _build_client()
    try:
        _set_billing_enabled(monkeypatch, enabled=False)
        tokens = _register_and_login(client, "billing-disabled-admin@example.com")
        _set_user_role(client, "billing-disabled-admin@example.com", "admin")

        status = client.get("/api/v1/billing/status", headers=_headers(tokens))
        assert status.status_code == 200, status.text
        body = status.json()
        assert body["plan_tier"] == "admin"
        assert body["can_run_analysis"] is True
    finally:
        _close_client(client)


def test_billing_routes_work_when_enabled(monkeypatch):
    """Mit BILLING_ENABLED=true antwortet /status normal."""
    client = _build_client()
    try:
        _set_billing_enabled(monkeypatch, enabled=True)
        tokens = _register_and_login(client, "billing-enabled-user@example.com")

        status = client.get("/api/v1/billing/status", headers=_headers(tokens))
        assert status.status_code == 200, status.text
        body = status.json()
        assert body["plan_tier"] == "free"
        assert body["can_run_analysis"] is True
        assert body["upgrade_required"] is False

        catalog = client.get("/api/v1/billing/catalog")
        assert catalog.status_code == 200, catalog.text
    finally:
        _close_client(client)


def test_webhook_noops_without_persisting_when_disabled(monkeypatch):
    """Webhook bleibt erreichbar; bei deaktiviertem Billing keine DB-Schreiblast."""
    client = _build_client()
    try:
        _set_billing_enabled(monkeypatch, enabled=False)

        res = client.post(
            "/api/v1/billing/webhook",
            content=b'{"id":"evt_disabled","type":"checkout.session.completed"}',
            headers={"Stripe-Signature": "t=0,v1=deadbeef"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "ignored_billing_disabled"

        with _db_session(client) as db:
            events = (
                db.query(BillingEvent)
                .filter(BillingEvent.event_type == "webhook_received_while_disabled")
                .all()
            )
            assert events == []
    finally:
        _close_client(client)


def test_user_plan_tier_is_free_when_disabled(monkeypatch):
    """has_paid_access behandelt jeden Nicht-Admin als free, solange Billing aus ist."""
    client = _build_client()
    try:
        _set_billing_enabled(monkeypatch, enabled=False)
        _register_and_login(client, "plan-tier-locked@example.com")

        from services.billing_service import has_paid_access

        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "plan-tier-locked@example.com").first()
            assert user is not None
            user.plan_tier = "pro"
            user.billing_status = "active"
            db.commit()
            assert has_paid_access(user) is False

            user.role = "admin"
            db.commit()
            # Admin behaelt seinen eigenen Pfad (admin-context); has_paid_access prueft
            # weiter den DB-Stand. Der Schutz gegenueber dem Schalter ist Admin-spezifisch
            # via _is_unlimited_admin und greift NICHT, wenn der Admin selbst kein "pro"
            # haette. Hier soll mindestens demonstriert werden: der Schalter blockt Admin
            # NICHT.
            assert has_paid_access(user) is True

        # Mit aktivem Schalter: Nicht-Admin mit pro-Status hat wieder Zugriff.
        _set_billing_enabled(monkeypatch, enabled=True)
        with _db_session(client) as db:
            user = db.query(User).filter(User.email == "plan-tier-locked@example.com").first()
            assert user is not None
            user.role = "projektierer"
            db.commit()
            assert has_paid_access(user) is True
    finally:
        _close_client(client)
