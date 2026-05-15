"""Smoke-Tests fuer /api/v1/projektierer/analyze."""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
URL = "/api/v1/projektierer/analyze"


def _payload(**overrides):
    base = {
        "anlagentyp": "PV",
        "p_kw": 5000,
        "leistung_mw": 5.0,
        "plz": "00000",
        "nennspannung": 20,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 10,
        "anschlussart": "Einspeisung",
    }
    base.update(overrides)
    return base


def _reset_rate_limit_state():
    from core import rate_limit as rate_limit_mod

    rate_limit_mod._MEM_BUCKETS.clear()
    rate_limit_mod._REDIS_CLIENT = None


def setup_function(function=None):
    _reset_rate_limit_state()


def test_happy_path_minimal():
    """Minimaler gueltiger Request -> 200 + Engine-Block + Projektierer-Block."""
    r = client.post(URL, json=_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    # Engine-Felder
    assert "status" in body
    assert "fazit" in body
    # Rollen-Block
    assert "projektierer" in body
    proj = body["projektierer"]
    assert "constraints" in proj
    assert "wirtschaftlichkeit" in proj
    assert "optimizer" in proj


def test_constraints_passthrough():
    """Constraints aus Request muessen 1:1 im projektierer.constraints landen."""
    r = client.post(URL, json=_payload(
        budget_eur=500000,
        zeitfenster_monate=12,
        flex_leistung=True,
        flex_standort=True,
    ))
    assert r.status_code == 200, r.text
    c = r.json()["projektierer"]["constraints"]
    assert c["budget_eur"] == 500000
    assert c["zeitfenster_monate"] == 12
    assert c["flex_leistung"] is True
    assert c["flex_standort"] is True
    assert c["flex_zeitfenster"] is False  # default


def test_wirtschaftlichkeit_pv_5mw():
    """PV 5 MW -> Erloes + Amortisation berechnet."""
    r = client.post(URL, json=_payload())
    assert r.status_code == 200
    w = r.json()["projektierer"]["wirtschaftlichkeit"]
    assert w["erloes"] is not None
    assert w["erloes"]["leistung_mw"] == 5.0
    assert w["erloes"]["erloes_jahr_eur"] > 0
    assert w["investkosten_eur"] is not None and w["investkosten_eur"] > 0
    assert w["amortisation_jahre"] is not None and w["amortisation_jahre"] > 0
    assert w["fehler"] is None


def test_optimizer_status_ok_or_pending():
    """Optimizer liefert deterministische Engpass-Skizze (OK) oder UNKLAR ohne Kennzahlen."""
    r = client.post(URL, json=_payload())
    assert r.status_code == 200
    opt = r.json()["projektierer"]["optimizer"]
    assert opt["status"] in ("OK", "UNKLAR")


def test_validation_missing_required_fields():
    """Fehlende Pflichtfelder -> 422 (Pydantic)."""
    r = client.post(URL, json={"anlagentyp": "PV", "p_kw": 5000})
    assert r.status_code == 422
    assert "detail" in r.json()


def test_validation_negative_budget():
    """Negatives Budget -> 422 (ge=0 constraint)."""
    r = client.post(URL, json=_payload(budget_eur=-1))
    assert r.status_code == 422


def test_route_is_rate_limited():
    _reset_rate_limit_state()
    for _ in range(6):
        r = client.post(URL, json=_payload())
        assert r.status_code == 200, r.text

    limited = client.post(URL, json=_payload())
    assert limited.status_code == 429
    detail = limited.json()["detail"]
    assert detail["code"] == "RATE_LIMITED"
    assert detail["message"] == "Zu viele oeffentliche Projektierer-Analysen"
