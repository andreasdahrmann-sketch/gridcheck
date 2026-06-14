"""Admin-Bypass Regression: lock down that internal admin users (User.role == "admin")
can run all flows without paywall, without consuming free/paid quota and without
polluting revenue metrics.

Wichtige Eigenschaften (gemaess DECISIONS.md / 06-arbeitsweise-gridcheck.mdc):
- Admin-Runs werden audit-distinct gespeichert: billing_category="admin",
  usage_bucket="admin", offer_id="admin", entitlement_id IS NULL,
  free_quota_consumed=False.
- Frontend bekommt nur ein Read-only-Flag ueber Backend-Felder; Enforcement bleibt
  strikt serverseitig anhand User.role aus der DB (kein Vertrauen auf Header/Frontend).
- Bezahl-Pfade fuer Nicht-Admins bleiben unveraendert (Regression test).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from db.database import Base, get_db
from db.models import AnalysisRun, BillingEntitlement, BillingEvent, User
from main import app
from tests.postgres_test_utils import build_isolated_postgres_session_factory


def _build_client():
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(
        Base.metadata, label="admin_bypass"
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


def _stub_analysis_engine(monkeypatch, captured: list[dict] | None = None) -> None:
    from api import analyze_v2 as analyze_v2_api

    def fake_run(payload: dict, **kwargs) -> dict:
        if captured is not None:
            captured.append(dict(payload))
        return {
            "status": "OK",
            "scores": {"gesamt": 82},
            "fazit": {"entscheidung": "B"},
            "warnungen": [],
            "empfehlungen": ["Admin-Test (nicht abgerechnet)"],
            "revision": {"hash": "a" * 64},
        }

    monkeypatch.setattr(analyze_v2_api, "run_v1_analysis", fake_run)


def test_admin_can_run_analyze_without_entitlement(monkeypatch):
    """Admin runs successfully without any BillingEntitlement and beyond the free-tier window."""
    client = _build_client()
    try:
        tokens = _register_and_login(client, "admin-runs@example.com")
        _set_user_role(client, "admin-runs@example.com", "admin")
        _stub_analysis_engine(monkeypatch)

        for _ in range(5):
            response = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["billing_access"]["offer_id"] == "admin"
            assert body["billing_access"]["package_scope"] == "professional"
            assert body["billing_access"]["usage_bucket"] == "admin"
            assert body["billing"]["plan_tier"] == "admin"
            assert body["billing"]["can_run_analysis"] is True
            assert body["billing"]["upgrade_required"] is False
    finally:
        _close_client(client)


def test_admin_run_persists_as_admin_bypass_not_paid(monkeypatch):
    """Audit: AnalysisRun row identifies admin runs uniquely (billing_category=admin, no entitlement, no quota)."""
    client = _build_client()
    try:
        tokens = _register_and_login(client, "admin-audit@example.com")
        user_id = _set_user_role(client, "admin-audit@example.com", "admin")
        _stub_analysis_engine(monkeypatch)

        response = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
        assert response.status_code == 200, response.text

        with _db_session(client) as db:
            run = (
                db.query(AnalysisRun)
                .filter(AnalysisRun.user_id == user_id)
                .order_by(AnalysisRun.id.desc())
                .first()
            )
            assert run is not None
            assert run.billing_category == "admin"
            assert run.usage_bucket == "admin"
            assert run.offer_id == "admin"
            assert run.package_scope == "professional"
            assert run.entitlement_id is None
            assert run.free_quota_consumed is False
            assert run.status == "completed"
    finally:
        _close_client(client)


def test_admin_premium_inputs_are_not_stripped(monkeypatch):
    """Admin gets professional scope; storage_profile/environmental_route/multi-component preserved."""
    client = _build_client()
    try:
        tokens = _register_and_login(client, "admin-features@example.com")
        _set_user_role(client, "admin-features@example.com", "admin")
        captured: list[dict] = []
        _stub_analysis_engine(monkeypatch, captured)

        response = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
        assert response.status_code == 200, response.text
        assert captured, "engine stub was not called"
        sent = captured[0]
        assert sent.get("storage_profile") is not None
        assert sent.get("environmental_route") is not None
        assert isinstance(sent.get("project_components"), list)
        assert len(sent["project_components"]) == 2
        assert sent.get("package_scope") == "professional"
    finally:
        _close_client(client)


def test_non_admin_still_hits_paywall(monkeypatch):
    """Regression: free-tier paywall remains intact for non-admin users."""
    client = _build_client()
    try:
        tokens = _register_and_login(client, "billing-regression@example.com")
        _stub_analysis_engine(monkeypatch)

        for _ in range(3):
            ok = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
            assert ok.status_code == 200, ok.text

        paywalled = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
        assert paywalled.status_code == 402, paywalled.text
        assert paywalled.json()["detail"]["code"] == "FREE_TIER_LIMIT"
    finally:
        _close_client(client)


def test_admin_does_not_consume_free_quota(monkeypatch):
    """Admin runs do not increment free_quota counter; after demote, full free quota remains."""
    client = _build_client()
    try:
        tokens = _register_and_login(client, "admin-no-quota@example.com")
        user_id = _set_user_role(client, "admin-no-quota@example.com", "admin")
        _stub_analysis_engine(monkeypatch)

        for _ in range(5):
            ok = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
            assert ok.status_code == 200, ok.text

        from services.billing_service import count_consumed_free_checks

        with _db_session(client) as db:
            user = db.query(User).filter(User.id == user_id).first()
            assert user is not None
            assert count_consumed_free_checks(db, user) == 0

        _set_user_role(client, "admin-no-quota@example.com", "projektierer")

        for _ in range(3):
            ok = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
            assert ok.status_code == 200, ok.text

        paywalled = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
        assert paywalled.status_code == 402, paywalled.text
        assert paywalled.json()["detail"]["code"] == "FREE_TIER_LIMIT"
    finally:
        _close_client(client)


def test_admin_billing_overview_shows_unlimited_state():
    """GET /billing/status reports admin overrides: plan_tier=admin, no upgrade required, no paywall."""
    client = _build_client()
    try:
        tokens = _register_and_login(client, "admin-overview@example.com")
        _set_user_role(client, "admin-overview@example.com", "admin")

        res = client.get("/api/v1/billing/status", headers=_headers(tokens))
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["plan_tier"] == "admin"
        assert body["billing_state_label"] == "admin"
        assert body["can_run_analysis"] is True
        assert body["upgrade_required"] is False
        assert body["billing_attention"] in (None, {})
        assert body["analysis_options"], "admin must see at least the synthetic admin option"
        admin_option = next((opt for opt in body["analysis_options"] if opt["offer_id"] == "admin"), None)
        assert admin_option is not None
        assert admin_option["package_scope"] == "professional"
        assert admin_option["default"] is True
    finally:
        _close_client(client)


def test_admin_can_access_vnb_dashboard_routes():
    """ADR-013/VNB-Access: admin sees VNB-dashboard surface (read-only) without verified-NB status."""
    client = _build_client()
    try:
        tokens = _register_and_login(client, "admin-vnb-routes@example.com")
        _set_user_role(client, "admin-vnb-routes@example.com", "admin")

        me = client.get("/api/v1/auth/me", headers=_headers(tokens))
        assert me.status_code == 200, me.text
        me_body = me.json()
        assert me_body["role"] == "admin"
        assert me_body["is_admin"] is True
        assert me_body["vnb_dashboard_access"] is True
        assert me_body["netzbetreiber_verified"] is False

        comms = client.get("/api/v1/vnb/comms/threads", headers=_headers(tokens))
        assert comms.status_code == 200, comms.text
    finally:
        _close_client(client)


def test_admin_does_not_appear_in_revenue_metrics(monkeypatch):
    """Admin runs do not produce BillingEvents, do not consume entitlements and stay marked as admin."""
    client = _build_client()
    try:
        tokens = _register_and_login(client, "admin-no-revenue@example.com")
        user_id = _set_user_role(client, "admin-no-revenue@example.com", "admin")
        _stub_analysis_engine(monkeypatch)

        with _db_session(client) as db:
            db.add(
                BillingEntitlement(
                    user_id=user_id,
                    offer_id="premium_pre_check",
                    offer_category="pay_per_use",
                    package_scope="premium",
                    source="checkout",
                    status="active",
                    total_credits=3,
                    used_credits=0,
                    valid_from=datetime.now(timezone.utc),
                    metadata_json='{"report_scope":"premium"}',
                )
            )
            db.commit()

        for _ in range(3):
            ok = client.post("/api/v1/analyze", headers=_headers(tokens), json=_base_payload())
            assert ok.status_code == 200, ok.text

        from services.billing_service import count_consumed_free_checks

        with _db_session(client) as db:
            runs = db.query(AnalysisRun).filter(AnalysisRun.user_id == user_id).all()
            assert len(runs) == 3
            assert all(run.billing_category == "admin" for run in runs)
            assert all(run.entitlement_id is None for run in runs)
            assert all(run.free_quota_consumed is False for run in runs)

            entitlement = (
                db.query(BillingEntitlement)
                .filter(
                    BillingEntitlement.user_id == user_id,
                    BillingEntitlement.offer_id == "premium_pre_check",
                )
                .one()
            )
            assert entitlement.used_credits == 0
            assert entitlement.status == "active"

            billing_events = db.query(BillingEvent).filter(BillingEvent.user_id == user_id).all()
            assert billing_events == []

            user = db.query(User).filter(User.id == user_id).first()
            assert user is not None
            assert count_consumed_free_checks(db, user) == 0
    finally:
        _close_client(client)
