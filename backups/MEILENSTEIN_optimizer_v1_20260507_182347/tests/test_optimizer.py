"""Tests fuer engine.optimizer."""
from engine.optimizer import optimiere


def _result_overload():
    return {
        "trafo": {"auslastung_prozent": 210.5},
        "spannung": {"delta_u_prozent": 40.751, "delta_u_hartgrenze_pct": 3.0},
        "thermisch": {"auslastung_prozent": 286.7},
        "kurzschluss": {"sk_sn_ratio": 4.7},
    }


def test_optimizer_findet_bindenden_engpass():
    r = optimiere(_result_overload(), {"leistung_mw": 50.0}, {})
    assert r["status"] == "OK"
    assert r["bindender_engpass"] == "spannung"
    assert 3.5 < r["p_max_mw"] < 3.9


def test_optimizer_liefert_drei_varianten():
    r = optimiere(_result_overload(), {"leistung_mw": 50.0}, {})
    assert len(r["varianten"]) == 3
    assert r["varianten"][1]["leistung_mw"] > r["varianten"][0]["leistung_mw"]


def test_optimizer_kein_engpass():
    res = {
        "trafo": {"auslastung_prozent": 50.0},
        "spannung": {"delta_u_prozent": 1.5, "delta_u_hartgrenze_pct": 3.0},
        "thermisch": {"auslastung_prozent": 60.0},
        "kurzschluss": {"sk_sn_ratio": 25.0},
    }
    r = optimiere(res, {"leistung_mw": 5.0}, {})
    assert r["p_max_mw"] >= 5.0
