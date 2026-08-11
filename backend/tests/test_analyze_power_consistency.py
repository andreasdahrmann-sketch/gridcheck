"""Regression: leistung_mw / ac_kw split-brain must be rejected at the API boundary."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.analyze_v2 import AnalyzeRequest


def _base(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "nennspannung": 20.0,
        "leistung_mw": 5.0,
        "leitungstyp": "NA2XS2Y150",
        "entfernung_km": 8.0,
        "anschlussart": "Einspeisung",
        "plant_type": "pv",
        "cos_phi": 0.95,
        "topologie": "ring_offen",
        "redundanz": True,
        "restkapazitaet_ms_mva": 20.0,
    }
    payload.update(overrides)
    return payload


def test_analyze_request_rejects_ac_kw_mismatch():
    with pytest.raises(ValidationError) as exc:
        AnalyzeRequest(**_base(leistung_mw=0.1, ac_kw=5000.0))
    assert "inkonsistent" in str(exc.value).lower()


def test_analyze_request_accepts_matching_ac_kw():
    req = AnalyzeRequest(**_base(leistung_mw=5.0, ac_kw=5000.0))
    assert req.leistung_mw == pytest.approx(5.0)
    assert req.ac_kw == pytest.approx(5000.0)


def test_analyze_request_accepts_missing_ac_kw():
    req = AnalyzeRequest(**_base())
    assert req.ac_kw is None
