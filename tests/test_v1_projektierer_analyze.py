"""Smoke-Tests fuer /api/v1/projektierer/analyze."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
URL = "/api/v1/projektierer/analyze"


def _payload(**overrides):
    base = {
        "nennspannung": 20.0,
        "leistung_mw": 5.0,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 2.5,
        "anschlussart": "Einspeisung",
        "anlagentyp": "PV",
        "cos_phi": 0.95,
        "parallele_systeme": 1,
        "budget_eur": 250000,
        "zeitfenster_monate": 12,
        "flex_leistung": True,
    }
    base.update(overrides)
    return base


def test_analyze_ok():
    r = client.post(URL, json=_payload())
    assert r.status_code == 200, r.text
    data = r.json()
    assert "projektierer" in data
    assert data["projektierer"]["optimizer"]["status"] == "PENDING"
    assert data["projektierer"]["constraints"]["budget_eur"] == 250000


def test_analyze_validation_pydantic():
    bad = _payload()
    bad["nennspannung"] = -1
    r = client.post(URL, json=bad)
    assert r.status_code == 422


def test_analyze_constraints_passthrough():
    r = client.post(URL, json=_payload(flex_standort=True, zeitfenster_monate=6))
    assert r.status_code == 200
    c = r.json()["projektierer"]["constraints"]
    assert c["flex_standort"] is True
    assert c["zeitfenster_monate"] == 6