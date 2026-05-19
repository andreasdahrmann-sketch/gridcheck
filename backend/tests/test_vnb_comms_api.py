from __future__ import annotations

from fastapi.testclient import TestClient

from db.database import Base, get_db
from db.models import User
from main import app
from tests.postgres_test_utils import build_isolated_postgres_session_factory
from tests.test_auth_projects_api import _close_client, _reset_rate_limit_state


def build_client():
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(Base.metadata, label="vnb_comms")
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


def _approve_user(client: TestClient, email: str) -> None:
    db = client._gridcheck_session_factory()  # type: ignore[attr-defined]
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.vnb_verification_status = "approved"
        db.commit()
    finally:
        db.close()


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("gridcheck_csrf")
    assert token
    return {"X-CSRF-Token": token}


def _register_nb(client: TestClient, email: str, password: str = "Passwort123!") -> None:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": "netzbetreiber"},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text


def test_vnb_comms_requires_verified_netzbetreiber():
    _reset_rate_limit_state()
    client = build_client()
    try:
        _register_nb(client, "vnb-pending@example.com")
        denied = client.get("/api/v1/vnb/comms/threads")
        assert denied.status_code == 403
        assert denied.json()["detail"]["code"] == "VNB_VERIFICATION_PENDING"

        _approve_user(client, "vnb-pending@example.com")
        allowed = client.get("/api/v1/vnb/comms/threads")
        assert allowed.status_code == 200
        assert allowed.json() == []
    finally:
        _close_client(client)


def test_vnb_comms_thread_lifecycle():
    _reset_rate_limit_state()
    client = build_client()
    try:
        _register_nb(client, "vnb-a@example.com")
        _approve_user(client, "vnb-a@example.com")

        create = client.post(
            "/api/v1/vnb/comms/threads",
            headers=_csrf_headers(client),
            json={
                "title": "Hinweis MS-Engpass Region Nord",
                "category": "kapazitaetshinweis",
                "body": "Fachlicher Hinweis ohne Kapazitaetszusage: Engpass-Screening in der Region.",
                "target_vnb_region": "nord",
            },
        )
        assert create.status_code == 200, create.text
        thread_id = create.json()["id"]
        assert create.json()["message_count"] == 1

        _register_nb(client, "vnb-b@example.com")
        _approve_user(client, "vnb-b@example.com")

        listing = client.get("/api/v1/vnb/comms/threads")
        assert listing.status_code == 200
        assert any(item["id"] == thread_id for item in listing.json())

        reply = client.post(
            f"/api/v1/vnb/comms/threads/{thread_id}/messages",
            headers=_csrf_headers(client),
            json={"body": "Danke fuer den Hinweis. Wir pruefen intern die Trassenvariante."},
        )
        assert reply.status_code == 200, reply.text
        assert reply.json()["message_count"] == 2

        pii = client.post(
            f"/api/v1/vnb/comms/threads/{thread_id}/messages",
            headers=_csrf_headers(client),
            json={"body": "Kontakt: kunde@example.com fuer Rueckfragen."},
        )
        assert pii.status_code == 422
        assert pii.json()["detail"]["code"] == "VNB_MESSAGE_PII"
    finally:
        _close_client(client)
