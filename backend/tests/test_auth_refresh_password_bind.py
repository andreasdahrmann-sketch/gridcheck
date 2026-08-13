"""Refresh JWTs must die when the password hash changes (no token_version column)."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://gridcheck:gridcheck@localhost:5432/gridcheck_test")
os.environ.setdefault("JWT_SECRET", "pytest-gridcheck-access-secret-32-chars")
os.environ.setdefault("JWT_REFRESH_SECRET", "pytest-gridcheck-refresh-secret-32")

from core.auth import create_token, hash_password
from services.auth_service import (
    ACCESS_TTL_MIN,
    REFRESH_TTL_MIN,
    _password_binding,
    issue_token_pair,
    refresh_access_token,
)


class _Query:
    def __init__(self, user):
        self._user = user

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._user


class _FakeDb:
    def __init__(self, user):
        self.user = user

    def query(self, _model):
        return _Query(self.user)


def _user(*, password: str = "Passwort123!", user_id: int = 7) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email="victim@example.com",
        role="projektierer",
        password_hash=hash_password(password),
        is_active=True,
        deleted_at=None,
    )


def test_refresh_succeeds_while_password_unchanged():
    user = _user()
    tokens = issue_token_pair(user)
    refreshed = refresh_access_token(_FakeDb(user), tokens["refresh_token"])
    assert refreshed["access_token"]
    assert refreshed["token_type"] == "bearer"


def test_refresh_rejected_after_password_hash_changes():
    user = _user(password="AltPasswort123!")
    tokens = issue_token_pair(user)
    user.password_hash = hash_password("NeuPasswort123!")

    with pytest.raises(HTTPException) as exc_info:
        refresh_access_token(_FakeDb(user), tokens["refresh_token"])

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "AUTH_REFRESH_REVOKED"


def test_legacy_refresh_without_pwd_ver_is_rejected():
    user = _user()
    legacy = create_token(
        {"sub": str(user.id), "email": user.email, "role": user.role},
        REFRESH_TTL_MIN,
        refresh=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        refresh_access_token(_FakeDb(user), legacy)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "AUTH_REFRESH_REVOKED"


def test_refresh_rejected_when_user_is_missing():
    user = _user()
    tokens = issue_token_pair(user)

    with pytest.raises(HTTPException) as exc_info:
        refresh_access_token(_FakeDb(None), tokens["refresh_token"])

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "AUTH_USER_INVALID"


def test_password_binding_changes_with_hash():
    user = _user(password="EinsPasswort!1")
    first = _password_binding(user)
    user.password_hash = hash_password("ZweiPasswort!2")
    second = _password_binding(user)
    assert first != second
    assert len(first) == 16


def test_access_token_does_not_need_db_roundtrip_for_binding():
    """Access tokens stay short-lived; binding is enforced on refresh only."""
    user = _user()
    tokens = issue_token_pair(user)
    assert tokens["access_token"]
    assert ACCESS_TTL_MIN < REFRESH_TTL_MIN
