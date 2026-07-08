"""DSGVO-Self-Service: Datenexport (Art. 15/20) und Konto-Loeschung (Art. 17).

Diese Tests pruefen den End-to-End-Pfad:
- Auth-Pflicht
- ZIP-Struktur und Inhalt
- Rate-Limit (1x/24h, Admin-Bypass)
- Passwort-Bestaetigung bei Loeschung
- Soft-Delete von User + Projekten + Reset-Tokens
- Re-Login nach Loeschung blockiert
- Audit-Eintrag (RevisionRecord) pro Aktion
"""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient

import api.users as users_api
from db.database import Base, get_db
from db.models import (
    PasswordResetToken,
    Project,
    RevisionRecord,
    User,
)
from main import app
from tests.postgres_test_utils import build_isolated_postgres_session_factory


PASSWORD = "Passwort123!"


def build_client() -> TestClient:
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(
        Base.metadata, label="dsgvo"
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


def _reset_rate_limit_state() -> None:
    from core import rate_limit as rate_limit_mod

    rate_limit_mod._MEM_BUCKETS.clear()
    rate_limit_mod._REDIS_CLIENT = None


def setup_function(function=None):
    _reset_rate_limit_state()


def _register(client: TestClient, email: str, password: str = PASSWORD, role: str = "projektierer") -> None:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert res.status_code == 200, res.text


def _login(client: TestClient, email: str, password: str = PASSWORD) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def _create_project(client: TestClient, owner_email: str) -> int:
    with client._gridcheck_session_factory() as db:  # type: ignore[attr-defined]
        owner = db.query(User).filter(User.email == owner_email).first()
        assert owner is not None
        project = Project(
            name="Test Projekt DSGVO",
            plz="10115",
            ort="Berlin",
            typ="pv",
            leistung_kw=150.0,
            owner_user_id=owner.id,
        )
        db.add(project)
        db.commit()
        return project.id


# ---------------------------------------------------------------------------
# Datenexport
# ---------------------------------------------------------------------------


def test_data_export_requires_auth() -> None:
    client = build_client()
    try:
        res = client.post("/api/v1/users/me/data-export")
        assert res.status_code == 401, res.text
    finally:
        _close_client(client)


def test_data_export_returns_zip_with_expected_files() -> None:
    client = build_client()
    try:
        email = _unique_email("export-zip")
        _register(client, email)
        token = _login(client, email)
        _create_project(client, email)

        res = client.post("/api/v1/users/me/data-export", headers=_auth(token))
        assert res.status_code == 200, res.text
        assert res.headers["content-type"].startswith("application/zip")
        disposition = res.headers.get("content-disposition", "")
        assert "gridcheck_export_" in disposition
        assert disposition.endswith('.zip"')

        zf = zipfile.ZipFile(io.BytesIO(res.content))
        names = set(zf.namelist())
        assert {"README.md", "account.json", "projects.json", "reports.json", "audit_log.json", "billing.json"} <= names

        account = json.loads(zf.read("account.json"))
        assert account["account"]["email"] == email
        assert "password_hash" not in account["account"]

        projects = json.loads(zf.read("projects.json"))
        assert len(projects["projects"]) == 1
        assert projects["projects"][0]["name"] == "Test Projekt DSGVO"
    finally:
        _close_client(client)


def test_data_export_rate_limited_to_1_per_24h() -> None:
    client = build_client()
    try:
        email = _unique_email("export-rate")
        _register(client, email)
        token = _login(client, email)

        first = client.post("/api/v1/users/me/data-export", headers=_auth(token))
        assert first.status_code == 200, first.text

        second = client.post("/api/v1/users/me/data-export", headers=_auth(token))
        assert second.status_code == 429, second.text
        assert second.json()["detail"]["code"] == "RATE_LIMITED"
    finally:
        _close_client(client)


def test_data_export_failed_zip_build_does_not_consume_rate_limit(monkeypatch) -> None:
    client = build_client()
    original_build = users_api.build_user_export_zip
    calls = {"count": 0}

    def flaky_build_user_export_zip(user_id, db):
        calls["count"] += 1
        if calls["count"] == 1:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "EXPORT_TEMPORARY_FAILURE",
                    "message": "Datenexport temporaer nicht verfuegbar.",
                    "hint": "Bitte erneut versuchen.",
                },
            )
        return original_build(user_id, db)

    monkeypatch.setattr(users_api, "build_user_export_zip", flaky_build_user_export_zip)
    try:
        email = _unique_email("export-flaky")
        _register(client, email)
        token = _login(client, email)

        first = client.post("/api/v1/users/me/data-export", headers=_auth(token))
        assert first.status_code == 503, first.text

        retry = client.post("/api/v1/users/me/data-export", headers=_auth(token))
        assert retry.status_code == 200, retry.text
        assert retry.headers["content-type"].startswith("application/zip")
    finally:
        _close_client(client)


def test_data_export_admin_no_rate_limit() -> None:
    client = build_client()
    try:
        email = _unique_email("export-admin")
        _register(client, email)
        with client._gridcheck_session_factory() as db:  # type: ignore[attr-defined]
            user = db.query(User).filter(User.email == email).first()
            assert user is not None
            user.role = "admin"
            db.commit()
        token = _login(client, email)

        for _ in range(3):
            res = client.post("/api/v1/users/me/data-export", headers=_auth(token))
            assert res.status_code == 200, res.text
    finally:
        _close_client(client)


def test_data_export_writes_revision_audit_entry() -> None:
    client = build_client()
    try:
        email = _unique_email("export-audit")
        _register(client, email)
        token = _login(client, email)

        res = client.post("/api/v1/users/me/data-export", headers=_auth(token))
        assert res.status_code == 200, res.text

        with client._gridcheck_session_factory() as db:  # type: ignore[attr-defined]
            user = db.query(User).filter(User.email == email).first()
            assert user is not None
            entries = (
                db.query(RevisionRecord)
                .filter(
                    RevisionRecord.actor_user_id == user.id,
                    RevisionRecord.action_type == "dsgvo_export_requested",
                )
                .all()
            )
            assert len(entries) == 1
    finally:
        _close_client(client)


# ---------------------------------------------------------------------------
# Konto-Loeschung
# ---------------------------------------------------------------------------


def test_delete_account_requires_password() -> None:
    client = build_client()
    try:
        email = _unique_email("delete-pw")
        _register(client, email)
        token = _login(client, email)

        res = client.post(
            "/api/v1/users/me/delete-account",
            headers=_auth(token),
            json={"confirm_password": "FalschesPasswort1!"},
        )
        assert res.status_code == 401, res.text
        assert res.json()["detail"]["code"] == "PASSWORD_INVALID"

        with client._gridcheck_session_factory() as db:  # type: ignore[attr-defined]
            user = db.query(User).filter(User.email == email).first()
            assert user is not None
            assert user.deleted_at is None
    finally:
        _close_client(client)


def test_delete_account_soft_deletes_user_and_projects() -> None:
    client = build_client()
    try:
        email = _unique_email("delete-soft")
        _register(client, email)
        token = _login(client, email)
        project_id = _create_project(client, email)

        res = client.post(
            "/api/v1/users/me/delete-account",
            headers=_auth(token),
            json={"confirm_password": PASSWORD},
        )
        assert res.status_code == 204, res.text

        with client._gridcheck_session_factory() as db:  # type: ignore[attr-defined]
            user = db.query(User).filter(User.id != 0).filter(
                User.deleted_email_hash.isnot(None)
            ).first()
            assert user is not None, "Geloeschter User-Datensatz muss vorhanden bleiben (Soft-Delete)"
            assert user.deleted_at is not None
            assert user.is_active is False
            assert user.password_hash == ""
            assert user.email.startswith("deleted_user_")
            assert user.email.endswith("@anonymized.local")

            project = db.query(Project).filter(Project.id == project_id).first()
            assert project is not None
            assert project.deleted_at is not None
    finally:
        _close_client(client)


def test_delete_account_invalidates_password_reset_tokens() -> None:
    client = build_client()
    try:
        email = _unique_email("delete-sessions")
        _register(client, email)
        token = _login(client, email)

        with client._gridcheck_session_factory() as db:  # type: ignore[attr-defined]
            user = db.query(User).filter(User.email == email).first()
            assert user is not None
            db.add(
                PasswordResetToken(
                    user_id=user.id,
                    token_hash="a" * 64,
                    expires_at=datetime.now(timezone.utc).replace(year=2099),
                )
            )
            db.commit()

        res = client.post(
            "/api/v1/users/me/delete-account",
            headers=_auth(token),
            json={"confirm_password": PASSWORD},
        )
        assert res.status_code == 204, res.text

        with client._gridcheck_session_factory() as db:  # type: ignore[attr-defined]
            open_tokens = (
                db.query(PasswordResetToken)
                .filter(PasswordResetToken.used_at.is_(None))
                .all()
            )
            assert open_tokens == []
    finally:
        _close_client(client)


def test_delete_account_writes_audit_entry() -> None:
    client = build_client()
    try:
        email = _unique_email("delete-audit")
        _register(client, email)
        token = _login(client, email)

        res = client.post(
            "/api/v1/users/me/delete-account",
            headers=_auth(token),
            json={"confirm_password": PASSWORD},
        )
        assert res.status_code == 204, res.text

        with client._gridcheck_session_factory() as db:  # type: ignore[attr-defined]
            entries = (
                db.query(RevisionRecord)
                .filter(RevisionRecord.action_type == "dsgvo_account_deleted")
                .all()
            )
            assert len(entries) == 1
    finally:
        _close_client(client)


def test_deleted_user_cannot_login() -> None:
    client = build_client()
    try:
        email = _unique_email("delete-relogin")
        _register(client, email)
        token = _login(client, email)

        res = client.post(
            "/api/v1/users/me/delete-account",
            headers=_auth(token),
            json={"confirm_password": PASSWORD},
        )
        assert res.status_code == 204, res.text

        relogin = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
        )
        assert relogin.status_code == 401, relogin.text
        assert relogin.json()["detail"]["code"] == "LOGIN_INVALID"

        reregister = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": PASSWORD, "role": "projektierer"},
        )
        assert reregister.status_code == 409, reregister.text
        assert reregister.json()["detail"]["code"] == "EMAIL_DELETED_BLOCKED"
    finally:
        _close_client(client)
