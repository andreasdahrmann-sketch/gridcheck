"""Regression: legacy persist must not commit unpaid Project/CheckResult.

Trigger: POST /api/v1/analyze/persist (or /check, /calculate) builds Project +
CheckResult + AuditLog, then calls persist_completed_analysis_run for billing.
If the project row is committed before that call, a later HTTP 402 (e.g. credit
re-check under race) or any persist failure leaves an orphan project whose
GET /api/v1/result/{id} still returns the full analysis without a billed run.

These unit tests pin the flush-only / single-commit ordering without Postgres.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from services import analysis_service


def _engine_result() -> dict:
    return {
        "score": 72.0,
        "spannungsband_ok": True,
        "thermische_auslastung_ok": True,
        "kurzschluss_ok": True,
        "n1_ok": True,
        "netzebene": "MS",
        "empfehlung": "ok",
        "details": {"x": 1},
    }


def _req() -> dict:
    return {
        "projektname": "Orphan Race",
        "plz": "10115",
        "anlagentyp": "pv",
        "leistung_kw": 500.0,
        "spannungsebene": "20",
        "leitungstyp": "NAYY",
        "querschnitt_mm2": "150",
        "leitungslaenge_km": 1.0,
    }


def _patch_common(monkeypatch, *, persist_side_effect=None, persist_return=None):
    access = {
        "billing_category": "free",
        "free_quota_consumed": True,
        "offer_id": "free",
        "package_scope": "basic",
        "usage_bucket": "free",
        "entitlement": None,
        "report_scope": "basic",
        "feature_flags": {},
        "ops_followup_required": False,
    }
    monkeypatch.setattr(analysis_service, "ensure_analysis_allowed", lambda db, user: None)
    monkeypatch.setattr(analysis_service, "package_access_context", lambda *a, **k: access)
    monkeypatch.setattr(analysis_service, "enforce_package_rights", lambda payload, ctx: payload)
    monkeypatch.setattr(analysis_service, "resolve_cable_key", lambda *a, **k: "NAYY 150")
    monkeypatch.setattr(analysis_service, "berechne_netzcheck", lambda **k: _engine_result())

    persist = MagicMock(side_effect=persist_side_effect, return_value=persist_return)
    monkeypatch.setattr(analysis_service, "persist_completed_analysis_run", persist)
    return persist


def test_legacy_persist_does_not_commit_before_billing_succeeds(monkeypatch):
    persist = _patch_common(monkeypatch, persist_return=SimpleNamespace(id=9))
    db = MagicMock()
    project = SimpleNamespace(id=55)
    # Project(...) construction is real; assign id via flush side effect.
    created = {}

    real_project = analysis_service.Project

    def project_ctor(*args, **kwargs):
        obj = real_project(*args, **kwargs)
        created["project"] = obj
        return obj

    monkeypatch.setattr(analysis_service, "Project", project_ctor)

    def flush():
        created["project"].id = 55

    db.flush.side_effect = flush
    user = SimpleNamespace(id=1)

    out = analysis_service.run_analysis_and_persist(db, _req(), user)

    assert out["project_id"] == 55
    db.flush.assert_called()
    db.commit.assert_not_called()
    persist.assert_called_once()
    assert persist.call_args.kwargs["project_id"] == 55
    assert persist.call_args.kwargs["source"] == "legacy_persist"


def test_legacy_persist_billing_402_leaves_no_committed_project(monkeypatch):
    _patch_common(
        monkeypatch,
        persist_side_effect=HTTPException(
            status_code=402,
            detail={"code": "FREE_TIER_LIMIT", "message": "limit"},
        ),
    )
    db = MagicMock()
    created = {}
    real_project = analysis_service.Project

    def project_ctor(*args, **kwargs):
        obj = real_project(*args, **kwargs)
        created["project"] = obj
        return obj

    monkeypatch.setattr(analysis_service, "Project", project_ctor)

    def flush():
        created["project"].id = 77

    db.flush.side_effect = flush
    user = SimpleNamespace(id=2)

    with pytest.raises(HTTPException) as exc:
        analysis_service.run_analysis_and_persist(db, _req(), user)

    assert exc.value.status_code == 402
    db.flush.assert_called()
    # Critical: no commit before/after failed billing — session close rolls back flush.
    db.commit.assert_not_called()
