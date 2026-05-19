"""Auth: Passwort-Reset-Flow und E-Mail-Stubs."""

from __future__ import annotations

import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient

from core import rate_limit as rate_limit_mod
from main import app
from services.auth_service import _hash_reset_token


def _reset_rate_limit_state() -> None:
    rate_limit_mod._MEM_BUCKETS.clear()
    rate_limit_mod._REDIS_CLIENT = None


@pytest.fixture
def client():
    _reset_rate_limit_state()
    return TestClient(app)


def _register(client: TestClient, email: str, password: str = "SecurePass!99") -> None:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": "endkunde"},
    )
    assert res.status_code == 200, res.text


def test_forgot_password_always_ok_no_enumeration(client: TestClient):
    res = client.post("/api/v1/auth/forgot-password", json={"email": "unknown@example.com"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_forgot_password_rate_limited(client: TestClient):
    _reset_rate_limit_state()
    email = f"forgot-limit-{uuid.uuid4().hex}@example.com"
    for _ in range(5):
        res = client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert res.status_code == 200
    res = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert res.status_code == 429
    assert res.json()["detail"]["code"] == "RATE_LIMITED"


def test_password_reset_roundtrip(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    sent: list[str] = []

    def _capture(**kwargs):
        sent.append(kwargs.get("reset_url", ""))
        return True

    monkeypatch.setattr("services.email_service.send_password_reset_email", _capture)

    email = f"reset-flow-{uuid.uuid4().hex}@example.com"
    _register(client, email)

    res = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    assert sent, "Reset-E-Mail sollte versendet (oder geloggt) werden"

    raw_token = sent[0].split("reset_token=")[-1]
    new_password = "NewSecurePass!01"
    res = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "password": new_password},
    )
    assert res.status_code == 200, res.text

    login_ok = client.post("/api/v1/auth/login", json={"email": email, "password": new_password})
    assert login_ok.status_code == 200

    login_old = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePass!99"})
    assert login_old.status_code == 401


def test_reset_token_single_use(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    sent: list[str] = []

    monkeypatch.setattr(
        "services.email_service.send_password_reset_email",
        lambda **kwargs: sent.append(kwargs.get("reset_url", "")) or True,
    )

    email = f"reset-once-{uuid.uuid4().hex}@example.com"
    _register(client, email)
    client.post("/api/v1/auth/forgot-password", json={"email": email})
    raw_token = sent[0].split("reset_token=")[-1]

    first = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "password": "AnotherSecure!02"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "password": "AnotherSecure!03"},
    )
    assert second.status_code == 400
    assert second.json()["detail"]["code"] == "PASSWORD_RESET_INVALID"


def test_token_hash_matches_db():
    raw = "test-token-value"
    assert _hash_reset_token(raw) == hashlib.sha256(raw.encode("utf-8")).hexdigest()
