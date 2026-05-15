"""Regression: Stateless Engine unter POST /api/v1/analyze (kein projektname)."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

import api.analyze_v2 as analyze_v2_api
from main import app

client = TestClient(app)
URL = "/api/v1/analyze"


@pytest.fixture(autouse=True)
def _passthrough_enforce_package_rights(monkeypatch: pytest.MonkeyPatch) -> None:
    """Free/Basic tier strips multi-component payloads; tests need full engine input."""
    monkeypatch.setattr(
        analyze_v2_api,
        "enforce_package_rights",
        lambda payload, access: payload,
    )


def _auth_headers() -> dict[str, str]:
    email = f"analyze-v2-{uuid.uuid4().hex}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Passwort123!", "role": "projektierer"},
    )
    assert reg.status_code == 200, reg.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Passwort123!"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _post_analyze(json_body: dict):
    return client.post(URL, json=json_body, headers=_auth_headers())


def _v2_payload(**overrides: object) -> dict:
    base: dict[str, object] = {
        "nennspannung": 20.0,
        "leistung_mw": 5.0,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 10.0,
        "anschlussart": "Einspeisung",
    }
    base.update(**{k: v for k, v in overrides.items()})
    return base


def _assert_kein_legacy_projektname_422(detail: object, response_text: str) -> None:
    if isinstance(detail, list):
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc")
                if isinstance(loc, list):
                    joined = ".".join(str(x) for x in loc).lower()
                    assert "projektname" not in joined, response_text
    lowered = str(detail).lower()
    assert "field required" not in lowered or "projektname" not in lowered, response_text


def test_analyze_v2_route_bindet_engine_schema():
    """Gueltiges V2-JSON: Persist-422 (projektname) ist ein Routing-Bug."""
    r = _post_analyze(_v2_payload())
    detail = None
    try:
        detail = r.json().get("detail")
    except Exception:
        detail = None

    if r.status_code == 422:
        _assert_kein_legacy_projektname_422(detail, r.text)
        # Engine darf fachlich 422 liefern, aber nur im FEHLER-Format.
        assert isinstance(detail, dict), r.text
        assert detail.get("status") == "FEHLER", r.text
        return

    assert r.status_code == 200, r.text
    body = r.json()
    assert "status" in body


def test_openapi_listen_post_analyze_einmal_engine():
    """OpenAPI soll genau einen POST unter /api/v1/analyze (Engine) exponieren."""
    schema = client.get("/openapi.json").json()
    post_analyze = [
        path
        for path, ops in schema.get("paths", {}).items()
        if path.rstrip("/") == "/api/v1/analyze" and "post" in ops
    ]
    assert post_analyze == ["/api/v1/analyze"], post_analyze


def test_analyze_v2_route_accepts_extended_project_profile():
    payload = _v2_payload(
        anlagentyp="PV",
        ort="Hannover",
        standort="Gewerbepark Nord",
        projektreife="planung",
        baugenehmigung_vorhanden=True,
        project_components=[
            {"component_type": "pv", "capacity_kw": 4000, "max_export_kw": 3500},
            {"component_type": "battery", "capacity_kw": 2000, "energy_kwh": 8000, "controllable": True},
        ],
        netzanschlusspunkt={"max_export_kw": 3500, "max_import_kw": 1200, "export_limit_mode": "dynamic"},
        project_location={"latitude": 52.379189, "longitude": 9.76199, "address_hint": "Gewerbepark Nord"},
        storage_profile={
            "has_storage": True,
            "operation_mode": "partial_grid_support",
            "power_kw": 2000,
            "energy_kwh": 8000,
            "remote_control_capable": True,
            "reactive_power_capable": True,
        },
        environmental_route={"route_length_km": 4.2, "route_complexity": "mittel", "third_party_land": True},
        stakeholder_context={"customer_type": "projektierer", "priority_focus": "kosten"},
    )
    r = _post_analyze(payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OK"
    assert body["projektprofil"]["is_hybrid"] is True
    assert body["projektprofil"]["component_count"] == 2
    assert len(body["projektprofil"]["component_summary"]) == 2
    assert body["speicher_bewertung"]["relevant"] is True
    assert "Hybridprojekt" in body["projektprofil"]["summary"]
    assert "stakeholder_bewertung" in body
    assert "transparenz" in body


def test_analyze_v2_route_uses_conservative_hybrid_nap_sum_without_explicit_limit():
    payload = _v2_payload(
        anlagentyp="PV",
        project_components=[
            {"component_type": "pv", "capacity_kw": 4000},
            {"component_type": "wind", "capacity_kw": 3000},
            {"component_type": "battery", "capacity_kw": 2000, "energy_kwh": 8000},
        ],
        stakeholder_context={"customer_type": "projektierer", "priority_focus": "balanced"},
    )
    r = _post_analyze(payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["projektprofil"]["max_export_kw"] == 9000


def test_analyze_v2_route_exposes_learning_profile(isolierte_revisionen, isolierte_ki_feedback, isolierte_ki_lerndaten):
    r = _post_analyze(_v2_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    assert "ki" in body
    assert "kalibrierung" in body["ki"]
    assert "feedback_loop" in body["ki"]
    assert "anomalie_check" in body["ki"]
    assert "revision" in body
    assert body["revision"]["hash"]


def test_analyze_v2_rejects_invalid_plz_format():
    r = _post_analyze(_v2_payload(plz="30A59"))
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "PLZ" in str(detail)


def test_analyze_v2_rejects_storage_without_power_or_energy():
    r = _post_analyze(
        _v2_payload(
            storage_profile={
                "has_storage": True,
                "operation_mode": "hybrid",
            }
        ),
    )
    assert r.status_code == 422, r.text
    assert "Speicher" in str(r.json()["detail"])


def test_analyze_v2_rejects_dso_verified_without_network_basis():
    r = _post_analyze(
        _v2_payload(
            n1_datengrundlage="dso_verified",
            stakeholder_context={"customer_type": "netzbetreiber", "priority_focus": "netz"},
        ),
    )
    assert r.status_code == 422, r.text
    assert "VNB-verifiziert" in str(r.json()["detail"])
