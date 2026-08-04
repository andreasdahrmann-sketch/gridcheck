"""Regression: public registration must not reserve DSGVO anonymization emails.

Trigger without this fix:
1. Attacker registers deleted_user_{victim_id}@anonymized.local
2. Victim calls POST /api/v1/users/me/delete-account
3. Unique users.email constraint fails → Art. 17 deletion blocked (503)

These tests stay DB-free (--noconftest) so the cloud runner can validate them.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.anonymized_email import (
    ANONYMIZED_EMAIL_DOMAIN,
    build_anonymized_email,
    is_reserved_anonymized_email,
    looks_like_anonymized_account_email,
)


class _EmptyQuery:
    def filter(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def first(self):
        return None


class _FakeDb:
    def query(self, model):  # noqa: ANN001
        return _EmptyQuery()

    def add(self, obj):  # noqa: ANN001
        self.added = obj

    def commit(self):
        return None

    def refresh(self, obj):  # noqa: ANN001
        if getattr(obj, "id", None) is None:
            obj.id = 42


def test_reserved_domain_detection() -> None:
    assert is_reserved_anonymized_email("deleted_user_123@anonymized.local")
    assert is_reserved_anonymized_email("  DELETED_USER_1@Anonymized.Local ")
    assert is_reserved_anonymized_email(f"anything@{ANONYMIZED_EMAIL_DOMAIN}")
    assert not is_reserved_anonymized_email("user@example.com")
    assert not is_reserved_anonymized_email("anonymized.local@example.com")


def test_build_anonymized_email_is_collision_resistant() -> None:
    a = build_anonymized_email(7)
    b = build_anonymized_email(7)
    assert a != b
    assert a.startswith("deleted_user_7_")
    assert a.endswith(f"@{ANONYMIZED_EMAIL_DOMAIN}")
    assert looks_like_anonymized_account_email(a)
    assert looks_like_anonymized_account_email(b)
    # Legacy deterministic form remains recognized for diagnostics.
    assert looks_like_anonymized_account_email("deleted_user_7@anonymized.local")


def test_register_user_rejects_reserved_anonymized_email(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import auth_service

    monkeypatch.setattr(auth_service, "validate_password_strength", lambda password: None)
    monkeypatch.setattr(auth_service, "log_security_event", lambda *a, **k: None)

    with pytest.raises(HTTPException) as exc:
        auth_service.register_user(
            _FakeDb(),
            email="deleted_user_123@anonymized.local",
            password="Passwort123!",
            role="projektierer",
            full_name=None,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "EMAIL_RESERVED"


def test_delete_account_email_avoids_pre_reserved_deterministic_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even if deleted_user_{id}@anonymized.local exists, deletion email must differ."""
    from services import dsgvo_service

    reserved = "deleted_user_99@anonymized.local"
    user = SimpleNamespace(
        id=99,
        email="victim@example.com",
        password_hash="hash",
        deleted_at=None,
        deleted_email_hash=None,
        is_active=True,
        full_name="Victim",
        stripe_customer_id=None,
        stripe_subscription_id=None,
        stripe_price_id=None,
        updated_at=None,
    )

    class _Query:
        def filter(self, *args, **kwargs):  # noqa: ANN002, ANN003
            return self

        def first(self):
            return user

        def update(self, values, synchronize_session=False):  # noqa: ANN001
            return 0

    class _DeleteDb:
        def query(self, model):  # noqa: ANN001
            return _Query()

        def commit(self):
            # Simulate uniqueness: commit fails only for the legacy deterministic form.
            if user.email == reserved:
                raise RuntimeError("UNIQUE constraint failed: users.email")

        def rollback(self):
            return None

    monkeypatch.setattr(dsgvo_service, "verify_password", lambda password, password_hash: True)
    monkeypatch.setattr(dsgvo_service, "log_security_event", lambda *a, **k: None)
    monkeypatch.setattr(dsgvo_service, "speichere_revision", lambda *a, **k: None)

    dsgvo_service.delete_user_account(
        user_id=99,
        password_plain="Passwort123!",
        db=_DeleteDb(),
        request_ip="127.0.0.1",
    )

    assert user.email != reserved
    assert user.email.startswith("deleted_user_99_")
    assert user.email.endswith(f"@{ANONYMIZED_EMAIL_DOMAIN}")
    assert user.deleted_at is not None
    assert user.is_active is False
    assert user.password_hash == ""
