from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from db.database import SessionLocal
from db.models import ConversionEvent, User
from main import app
from services.conversion_tracking_service import record_conversion_event

client = TestClient(app)


def _register_and_login(email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPasswort123!", "role": "projektierer"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPasswort123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_headers() -> tuple[dict[str, str], str]:
    email = f"conversion-admin-{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPasswort123!", "role": "projektierer"},
    )
    assert reg.status_code == 200, reg.text
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.role = "admin"
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPasswort123!"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, email


def test_post_conversion_event_persists() -> None:
    email = f"conversion-tracker-{uuid.uuid4().hex[:8]}@example.com"
    headers = _register_and_login(email)
    response = client.post(
        "/api/v1/analytics/events",
        headers=headers,
        json={
            "event_name": "page_view_product",
            "session_id": "sess-smoke-1",
            "properties": {"surface": "product_guide", "card_id": "premium"},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["event_name"] == "page_view_product"
    assert body["session_id"] == "sess-smoke-1"
    assert isinstance(body["id"], int)

    db = SessionLocal()
    try:
        stored = db.query(ConversionEvent).filter(ConversionEvent.id == body["id"]).one()
        assert stored.event_name == "page_view_product"
        assert stored.session_id == "sess-smoke-1"
        assert '"card_id": "premium"' in stored.properties_json
    finally:
        db.close()


def test_post_conversion_event_rejects_unknown_name() -> None:
    email = f"conversion-invalid-{uuid.uuid4().hex[:8]}@example.com"
    headers = _register_and_login(email)
    response = client.post(
        "/api/v1/analytics/events",
        headers=headers,
        json={"event_name": "not_a_real_event", "properties": {}},
    )
    assert response.status_code == 422


def test_conversion_summary_requires_admin() -> None:
    admin_headers, admin_email = _admin_headers()
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == admin_email).first()
        assert admin is not None
        record_conversion_event(
            db,
            user_id=admin.id,
            event_name="checkout_started",
            properties={"offer_id": "premium_pre_check"},
        )
        record_conversion_event(
            db,
            user_id=admin.id,
            event_name="analysis_completed",
            properties={"analysis_run_id": 1},
        )
        db.commit()
    finally:
        db.close()

    user_headers = _register_and_login(f"conversion-user-{uuid.uuid4().hex[:8]}@example.com")
    forbidden = client.get("/api/v1/analytics/summary", headers=user_headers)
    assert forbidden.status_code == 403

    summary = client.get("/api/v1/analytics/summary?days=7", headers=admin_headers)
    assert summary.status_code == 200, summary.text
    counts = summary.json()["counts"]
    assert counts["checkout_started"] >= 1
    assert counts["analysis_completed"] >= 1
