"""Regression: prepaid/free analysis credits must not double-consume under race.

Trigger: two parallel analyze requests both pass package_access_context against a
1-credit pack (or the last free check), run the engine, then both call
persist_completed_analysis_run. Without FOR UPDATE + re-check at consume time,
both persist completed runs while used_credits stays at 1 (last-writer wins) or
free_quota_consumed exceeds FREE_CHECKS_LIMIT.

These unit tests lock the re-check / 402 path without requiring live Postgres
concurrency.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from db.models import BillingEntitlement, User
from services import billing_service
from services.billing_service import _consume_access_quota


class _QueryChain:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def with_for_update(self):
        return self

    def execution_options(self, **kwargs):
        return self

    def one(self):
        return self._result

    def one_or_none(self):
        return self._result


def _entitlement_mock(**kwargs) -> MagicMock:
    """MagicMock(spec=BillingEntitlement) so isinstance(..., BillingEntitlement) is True."""
    ent = MagicMock(spec=BillingEntitlement)
    for key, value in kwargs.items():
        setattr(ent, key, value)
    return ent


def test_consume_prepaid_credit_locks_and_marks_consumed(monkeypatch):
    entitlement = _entitlement_mock(
        id=11,
        status="active",
        total_credits=1,
        used_credits=0,
        valid_until=None,
    )
    user = SimpleNamespace(id=42)
    access = {"entitlement": entitlement, "free_quota_consumed": False}
    db = MagicMock()

    def query(model):
        assert model is BillingEntitlement
        return _QueryChain(entitlement)

    db.query.side_effect = query
    monkeypatch.setattr(billing_service, "_utcnow", lambda: "now")

    result = _consume_access_quota(db, user, access)

    assert result is entitlement
    assert entitlement.used_credits == 1
    assert entitlement.status == "consumed"
    assert entitlement.updated_at == "now"
    assert access["entitlement"] is entitlement


def test_consume_prepaid_credit_raises_when_already_spent(monkeypatch):
    stale = _entitlement_mock(id=11, status="active", total_credits=1, used_credits=0, valid_until=None)
    locked = _entitlement_mock(id=11, status="consumed", total_credits=1, used_credits=1, valid_until=None)
    user = SimpleNamespace(id=7)
    access = {"entitlement": stale, "free_quota_consumed": False}
    db = MagicMock()

    def query(model):
        assert model is BillingEntitlement
        return _QueryChain(locked)

    db.query.side_effect = query
    monkeypatch.setattr(
        billing_service,
        "_paywall_detail",
        lambda db, user: {"code": "FREE_TIER_LIMIT"},
    )

    with pytest.raises(HTTPException) as exc:
        _consume_access_quota(db, user, access)

    assert exc.value.status_code == 402
    assert locked.used_credits == 1


def test_consume_free_quota_raises_when_limit_reached(monkeypatch):
    user = SimpleNamespace(id=3)
    access = {"entitlement": None, "free_quota_consumed": True}
    db = MagicMock()

    def query(model):
        assert model is User
        return _QueryChain(user)

    db.query.side_effect = query
    monkeypatch.setattr(billing_service, "count_consumed_free_checks", lambda db, user: 3)
    monkeypatch.setattr(billing_service.settings, "free_checks_limit", 3)
    monkeypatch.setattr(
        billing_service,
        "_paywall_detail",
        lambda db, user: {"code": "FREE_TIER_LIMIT"},
    )

    with pytest.raises(HTTPException) as exc:
        _consume_access_quota(db, user, access)

    assert exc.value.status_code == 402


def test_consume_free_quota_allows_when_under_limit(monkeypatch):
    user = SimpleNamespace(id=3)
    access = {"entitlement": None, "free_quota_consumed": True}
    db = MagicMock()

    def query(model):
        assert model is User
        return _QueryChain(user)

    db.query.side_effect = query
    monkeypatch.setattr(billing_service, "count_consumed_free_checks", lambda db, user: 2)
    monkeypatch.setattr(billing_service.settings, "free_checks_limit", 3)

    assert _consume_access_quota(db, user, access) is None


def test_admin_bypass_skips_quota_lock():
    user = SimpleNamespace(id=1)
    access = {"entitlement": None, "free_quota_consumed": False}
    db = MagicMock()

    assert _consume_access_quota(db, user, access) is None
    db.query.assert_not_called()
