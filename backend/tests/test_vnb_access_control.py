"""Access control: VNB dashboard and stakeholder routes require verified netzbetreiber."""
from __future__ import annotations

from fastapi.testclient import TestClient

from core.vnb_access import _USERS_COLUMNS_CACHE, user_is_verified_netzbetreiber
from db.database import Base, get_db
from db.models import User
from main import app
from services.auth_service import approve_netzbetreiber
from tests.postgres_test_utils import build_isolated_postgres_session_factory


def build_client():
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(Base.metadata, label="vnb_access")
    session = TestingSessionLocal()

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
    client._seed_session = session  # type: ignore[attr-defined]
    return client


def _close_client(client: TestClient) -> None:
    app.dependency_overrides.clear()
    client._seed_session.close()  # type: ignore[attr-defined]
    client.close()
    client._gridcheck_cleanup()  # type: ignore[attr-defined]


def _register(client: TestClient, email: str, role: str, password: str = "Passwort123!") -> dict:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert reg.status_code == 200, reg.text
    return reg.json()


def _login(client: TestClient, email: str, password: str = "Passwort123!") -> str:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _minimal_netzbetreiber_payload() -> dict:
    return {
        "projektname": "VNB Test",
        "plz": "10115",
        "anlagentyp": "pv",
        "leistung_kw": 500.0,
        "spannungsebene": "20",
        "cos_phi": 0.95,
        "einspeiseart": "volleinspeisung",
        "speicher": False,
        "trafo_mva": 0.63,
        "leitungslaenge_km": 1.0,
        "leitungstyp": "NAYY",
        "querschnitt_mm2": "150",
        "parallelsysteme": 1,
        "eigentumsgrenze": "HAK",
        "netz_typ": "kabel",
        "pruefer_id": "pr-1",
        "aktenzeichen": "AZ-VNB-1",
    }


def _promote_to_admin(client: TestClient, email: str) -> None:
    db = client._gridcheck_session_factory()  # type: ignore[attr-defined]
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.role = "admin"
        db.commit()
    finally:
        db.close()


def test_admin_allowed_on_netzbetreiber_stakeholder_route():
    client = build_client()
    try:
        _register(client, "admin-vnb@example.com", "projektierer")
        _promote_to_admin(client, "admin-vnb@example.com")
        token = _login(client, "admin-vnb@example.com")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text
        assert me.json()["vnb_dashboard_access"] is True
        assert me.json()["netzbetreiber_verified"] is False
        res = client.post(
            "/api/v1/stakeholder/netzbetreiber",
            json=_minimal_netzbetreiber_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200, res.text
    finally:
        _close_client(client)


def test_admin_allowed_on_vnb_comms_threads():
    client = build_client()
    try:
        _register(client, "admin-comms@example.com", "endkunde")
        _promote_to_admin(client, "admin-comms@example.com")
        token = _login(client, "admin-comms@example.com")
        res = client.get(
            "/api/v1/vnb/comms/threads",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200, res.text
        assert res.json() == []
    finally:
        _close_client(client)


def test_endkunde_denied_on_netzbetreiber_stakeholder_route():
    client = build_client()
    try:
        _register(client, "endkunde-vnb@example.com", "endkunde")
        token = _login(client, "endkunde-vnb@example.com")
        res = client.post(
            "/api/v1/stakeholder/netzbetreiber",
            json=_minimal_netzbetreiber_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        assert res.json()["detail"]["code"] in {"STAKEHOLDER_FORBIDDEN", "VNB_ACCESS_DENIED"}
    finally:
        _close_client(client)


def test_pending_netzbetreiber_denied():
    client = build_client()
    try:
        user = _register(client, "pending-nb@example.com", "netzbetreiber")
        assert user["vnb_verification_status"] == "pending"
        assert user["netzbetreiber_verified"] is False
        token = _login(client, "pending-nb@example.com")
        res = client.post(
            "/api/v1/stakeholder/netzbetreiber",
            json=_minimal_netzbetreiber_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403
        assert res.json()["detail"]["code"] == "VNB_ACCESS_DENIED"
    finally:
        _close_client(client)


def test_verified_netzbetreiber_allowed():
    client = build_client()
    try:
        user = _register(client, "verified-nb@example.com", "netzbetreiber")
        db = client._gridcheck_session_factory()  # type: ignore[attr-defined]
        approve_netzbetreiber(db, user_id=user["id"])
        db.close()

        token = _login(client, "verified-nb@example.com")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        body = me.json()
        assert body["netzbetreiber_verified"] is True
        assert body["vnb_verification_status"] == "approved"

    finally:
        _close_client(client)


def test_approve_netzbetreiber_sets_verified_flags():
    client = build_client()
    try:
        pending = _register(client, "approve-me@example.com", "netzbetreiber")
        db = client._seed_session  # type: ignore[attr-defined]
        approved = approve_netzbetreiber(db, user_id=pending["id"])
        assert approved.vnb_verification_status == "approved"

        token = _login(client, "approve-me@example.com")
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        body = me_res.json()
        assert body["netzbetreiber_verified"] is True
        assert body["vnb_verification_status"] == "approved"
    finally:
        _close_client(client)


def test_stale_users_column_cache_does_not_deny_approved_netzbetreiber():
    class DummySession:
        def __init__(self) -> None:
            self.bind = object()

        def get_bind(self) -> object:
            return self.bind

    session = DummySession()
    user = User(
        email="stale-cache-vnb@example.com",
        password_hash="unused",
        role="netzbetreiber",
        vnb_verification_status="approved",
    )

    _USERS_COLUMNS_CACHE.clear()
    _USERS_COLUMNS_CACHE[id(session.bind)] = frozenset()
    try:
        assert user_is_verified_netzbetreiber(user, db=session) is True  # type: ignore[arg-type]
    finally:
        _USERS_COLUMNS_CACHE.clear()
