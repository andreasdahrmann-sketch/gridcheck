"""Regression: checkout entitlement must not double-issue under race.

Trigger: Stripe webhook `checkout.session.completed` and success-page
`GET /api/v1/billing/checkout-session` both call `_sync_checkout_session_completion`
for the same paid session. Without serialization + unique (session, offer),
both observe "missing" and insert two active prepaid packs (e.g. 2 credits
for one Premium payment).

These unit tests lock the IntegrityError / re-fetch path and the under-lock
exists short-circuit without requiring live Postgres concurrency.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from db.models import BillingEntitlement, User
from services.billing_service import (
    _ensure_payment_entitlement,
    _get_payment_entitlement,
)


class _QueryChain:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def with_for_update(self):
        return self

    def one(self):
        return self._result

    def first(self):
        return self._result


def test_ensure_payment_entitlement_returns_existing_under_user_lock(monkeypatch):
    existing = SimpleNamespace(id=11, checkout_session_id="cs_race", offer_id="premium_pre_check")
    user = SimpleNamespace(id=42)
    db = MagicMock()

    def query(model):
        if model is User:
            return _QueryChain(user)
        assert model is BillingEntitlement
        return _QueryChain(existing)

    db.query.side_effect = query
    issued = {"called": False}

    def _fake_issue(*args, **kwargs):
        issued["called"] = True
        raise AssertionError("must not issue when entitlement already exists")

    monkeypatch.setattr(
        "services.billing_service._issue_payment_entitlement",
        _fake_issue,
    )

    result = _ensure_payment_entitlement(
        db,
        user,
        offer_id="premium_pre_check",
        checkout_session_id="cs_race",
        payment_intent_id="pi_1",
        stripe_price_id="price_1",
        status="active",
    )
    assert result is existing
    assert issued["called"] is False


def test_ensure_payment_entitlement_integrity_error_returns_winner(monkeypatch):
    """Loser of a unique-index race must re-read the winner row, not raise."""
    winner = SimpleNamespace(id=99, checkout_session_id="cs_race", offer_id="basic_schnellcheck")
    user = SimpleNamespace(id=7)
    db = MagicMock()
    lookup_results = [None, winner]

    def query(model):
        if model is User:
            return _QueryChain(user)
        assert model is BillingEntitlement
        value = lookup_results.pop(0) if lookup_results else winner
        return _QueryChain(value)

    db.query.side_effect = query

    @contextmanager
    def _nested():
        yield
        raise IntegrityError("INSERT", {}, Exception("uq_billing_entitlements_checkout_session_offer"))

    db.begin_nested.side_effect = lambda: _nested()

    monkeypatch.setattr(
        "services.billing_service._issue_payment_entitlement",
        lambda *a, **k: SimpleNamespace(id=1),
    )

    result = _ensure_payment_entitlement(
        db,
        user,
        offer_id="basic_schnellcheck",
        checkout_session_id="cs_race",
        payment_intent_id="pi_1",
        stripe_price_id="price_basic",
        status="active",
    )
    assert result is winner


def test_get_payment_entitlement_requires_session_id():
    db = MagicMock()
    assert _get_payment_entitlement(db, None, "premium_pre_check") is None
    db.query.assert_not_called()


def test_ensure_raises_if_integrity_error_without_winner(monkeypatch):
    user = SimpleNamespace(id=3)
    db = MagicMock()

    def query(model):
        if model is User:
            return _QueryChain(user)
        return _QueryChain(None)

    db.query.side_effect = query

    @contextmanager
    def _nested():
        yield
        raise IntegrityError("INSERT", {}, Exception("uq"))

    db.begin_nested.side_effect = lambda: _nested()
    monkeypatch.setattr(
        "services.billing_service._issue_payment_entitlement",
        lambda *a, **k: SimpleNamespace(id=1),
    )

    with pytest.raises(IntegrityError):
        _ensure_payment_entitlement(
            db,
            user,
            offer_id="premium_pre_check",
            checkout_session_id="cs_orphan",
            payment_intent_id="pi_x",
            stripe_price_id="price_x",
            status="active",
        )
