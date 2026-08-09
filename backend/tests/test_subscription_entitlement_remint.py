"""Regression: Pro Lizenz must not remint inclusive credits inside one period.

Trigger: active pro subscriber exhausts included_credits (20). persist marks the
entitlement status=consumed. The next package_access_context call ran
_ensure_subscription_entitlement with an active-only lookup, found nothing, and
inserted a fresh pro_lizenz row with used_credits=0 — unbounded paid analyses
for the same Stripe period.

These unit tests lock the ensure/sync behaviour without live Postgres.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from db.models import BillingEntitlement
from services import billing_service
from services.billing_service import (
    _ensure_subscription_entitlement,
    _sync_subscription_quota,
)


class _QueryChain:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


def _entitlement_mock(**kwargs) -> MagicMock:
    ent = MagicMock(spec=BillingEntitlement)
    for key, value in kwargs.items():
        setattr(ent, key, value)
    return ent


def test_ensure_reuses_consumed_subscription_entitlement_same_period(monkeypatch):
    period_end = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    consumed = _entitlement_mock(
        id=9,
        status="consumed",
        total_credits=20,
        used_credits=20,
        valid_until=period_end,
        valid_from=period_end - timedelta(days=30),
    )
    user = SimpleNamespace(
        id=3,
        plan_tier="pro",
        billing_status="active",
        billing_current_period_end=period_end,
        stripe_price_id="price_pro",
        stripe_subscription_id="sub_123",
    )
    db = MagicMock()
    db.query.return_value = _QueryChain(consumed)
    monkeypatch.setattr(billing_service, "_utcnow", lambda: datetime(2026, 8, 9, 11, 0, tzinfo=timezone.utc))

    result = _ensure_subscription_entitlement(db, user)

    assert result is consumed
    db.add.assert_not_called()
    assert consumed.status == "consumed"
    assert consumed.used_credits == 20
    assert consumed.valid_until == period_end


def test_ensure_resets_credits_only_on_period_rollover(monkeypatch):
    old_period_end = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
    new_period_end = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    consumed = _entitlement_mock(
        id=9,
        status="consumed",
        total_credits=20,
        used_credits=20,
        valid_until=old_period_end,
        valid_from=old_period_end - timedelta(days=30),
    )
    user = SimpleNamespace(
        id=3,
        plan_tier="pro",
        billing_status="active",
        billing_current_period_end=new_period_end,
        stripe_price_id="price_pro",
        stripe_subscription_id="sub_123",
    )
    db = MagicMock()
    db.query.return_value = _QueryChain(consumed)
    now = datetime(2026, 8, 1, 0, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(billing_service, "_utcnow", lambda: now)

    result = _ensure_subscription_entitlement(db, user)

    assert result is consumed
    db.add.assert_not_called()
    assert consumed.status == "active"
    assert consumed.used_credits == 0
    assert consumed.valid_until == new_period_end
    assert consumed.valid_from == now


def test_sync_subscription_quota_does_not_reset_within_same_period():
    period_end = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    entitlement = _entitlement_mock(
        status="consumed",
        total_credits=20,
        used_credits=20,
        valid_until=period_end,
    )
    user = SimpleNamespace(billing_current_period_end=period_end)
    offer = {"included_credits": 20}

    _sync_subscription_quota(user, entitlement, offer)

    assert entitlement.status == "consumed"
    assert entitlement.used_credits == 20
    assert entitlement.valid_until == period_end
