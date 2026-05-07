from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, get_db
from main import app


def build_client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _register_and_login(client: TestClient, email: str, password: str = "Passwort123!") -> dict:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "role": "projektierer"})
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()


def test_auth_register_login_and_me():
    client = build_client()
    tokens = _register_and_login(client, "alice@example.com")
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_project_crud_sharing_and_upload(monkeypatch):
    client = build_client()
    owner_tokens = _register_and_login(client, "owner@example.com")
    user = client.post(
        "/api/v1/auth/register",
        json={"email": "viewer@example.com", "password": "Passwort123!", "role": "endkunde"},
    )
    assert user.status_code == 200
    viewer_id = user.json()["id"]
    headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

    created = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "P1", "plz": "10115", "typ": "pv", "leistung_kw": 1200},
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]

    shared = client.post(
        f"/api/v1/projects/{project_id}/share",
        headers=headers,
        json={"target_user_id": viewer_id, "project_role": "viewer"},
    )
    assert shared.status_code == 200, shared.text
    viewer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "Passwort123!"},
    )
    viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}
    viewer_list = client.get("/api/v1/projects", headers=viewer_headers)
    assert viewer_list.status_code == 200
    assert any(item["id"] == project_id for item in viewer_list.json())

    updated = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=headers,
        json={"description": "Aktualisiert"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Aktualisiert"

    upload = client.post(
        f"/api/v1/projects/{project_id}/files",
        headers=headers,
        files={"file": ("plan.txt", io.BytesIO(b"netzplan"), "text/plain")},
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["file_name"] == "plan.txt"

    deleted = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert deleted.status_code == 200
    forbidden_after_delete = client.get(f"/api/v1/projects/{project_id}", headers=viewer_headers)
    assert forbidden_after_delete.status_code == 404


def test_user_settings_and_contact(monkeypatch):
    client = build_client()
    tokens = _register_and_login(client, "settings@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    update_me = client.patch("/api/v1/users/me", headers=headers, json={"full_name": "Max Mustermann"})
    assert update_me.status_code == 200
    assert update_me.json()["full_name"] == "Max Mustermann"

    change_pw = client.patch(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "Passwort123!", "new_password": "NeuPasswort123!"},
    )
    assert change_pw.status_code == 200

    from api import contact as contact_api

    monkeypatch.setattr(contact_api, "send_contact_mail", lambda **kwargs: None)
    payload = {
        "name": "Tester",
        "email": "tester@example.com",
        "subject": "Frage",
        "message": "Bitte um Rueckmeldung zur Netzkapazitaet.",
    }
    contact = client.post("/api/v1/contact", json=payload)
    assert contact.status_code == 200
    for _ in range(5):
        client.post("/api/v1/contact", json=payload)
    limited = client.post("/api/v1/contact", json=payload)
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "RATE_LIMITED"


def test_cookie_auth_requires_csrf_for_mutations():
    client = build_client()
    _register_and_login(client, "csrf@example.com")

    no_csrf = client.patch("/api/v1/users/me", json={"full_name": "CSRF Test"})
    assert no_csrf.status_code == 403
    assert no_csrf.json()["detail"]["code"] == "CSRF_INVALID"

    csrf_token = client.cookies.get("gridcheck_csrf")
    assert csrf_token
    with_csrf = client.patch(
        "/api/v1/users/me",
        headers={"X-CSRF-Token": csrf_token},
        json={"full_name": "CSRF Test"},
    )
    assert with_csrf.status_code == 200
    assert with_csrf.json()["full_name"] == "CSRF Test"

    no_csrf_project = client.post(
        "/api/v1/projects",
        json={"name": "No CSRF", "plz": "10115", "typ": "pv", "leistung_kw": 1000},
    )
    assert no_csrf_project.status_code == 403
    assert no_csrf_project.json()["detail"]["code"] == "CSRF_INVALID"
