"""Regression: geocoded Project.lat/lon must reach analyze/report project_location.

Trigger: create a project with address or coordinates, then POST /api/v1/analyze
with project_id but without project_location (the workspace path after dual-location
create). Without hydration, reports persist the Germany-center placeholder
51.1657/10.4515 while the project row already has the real site.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from db.database import Base, get_db
from db.models import AnalysisRun
from main import app
from services.project_service import hydrate_analyze_location_from_project, join_address_hint
from tests.postgres_test_utils import build_isolated_postgres_session_factory


_PLACEHOLDER_LAT = 51.1657
_PLACEHOLDER_LON = 10.4515
_SITE_LAT = 52.520008
_SITE_LON = 13.404954


def _build_client() -> TestClient:
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(
        Base.metadata, label="analyze_loc_hydrate"
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client._gridcheck_cleanup = cleanup  # type: ignore[attr-defined]
    client._gridcheck_session_factory = TestingSessionLocal  # type: ignore[attr-defined]
    return client


def _close_client(client: TestClient) -> None:
    app.dependency_overrides.clear()
    client.close()
    client._gridcheck_cleanup()  # type: ignore[attr-defined]


def _register_and_login(client: TestClient, email: str, password: str = "Passwort123!") -> dict:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": "projektierer"},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()


def test_join_address_hint_formats_street_plz_city():
    assert (
        join_address_hint(street="Unter den Linden", house_number="1", plz="10117", city="Berlin")
        == "Unter den Linden 1, 10117, Berlin"
    )
    assert join_address_hint(plz="30159") == "30159"
    assert join_address_hint() is None


def test_hydrate_analyze_location_fills_omitted_coords_from_project():
    project = SimpleNamespace(
        latitude=_SITE_LAT,
        longitude=_SITE_LON,
        street="Unter den Linden",
        house_number="1",
        plz="10117",
        city="Berlin",
        ort=None,
    )
    hydrated = hydrate_analyze_location_from_project(
        {"nennspannung": 20, "leistung_mw": 1.2},
        project,  # type: ignore[arg-type]
    )
    loc = hydrated["project_location"]
    assert loc["latitude"] == _SITE_LAT
    assert loc["longitude"] == _SITE_LON
    assert loc["address_hint"] == "Unter den Linden 1, 10117, Berlin"


def test_hydrate_analyze_location_does_not_overwrite_explicit_coords():
    project = SimpleNamespace(
        latitude=_SITE_LAT,
        longitude=_SITE_LON,
        street="Unter den Linden",
        house_number="1",
        plz="10117",
        city="Berlin",
        ort=None,
    )
    hydrated = hydrate_analyze_location_from_project(
        {
            "project_location": {
                "latitude": 50.110924,
                "longitude": 8.682127,
                "address_hint": "Frankfurt",
            }
        },
        project,  # type: ignore[arg-type]
    )
    loc = hydrated["project_location"]
    assert loc["latitude"] == 50.110924
    assert loc["longitude"] == 8.682127
    assert loc["address_hint"] == "Frankfurt"


def test_analyze_with_project_id_hydrates_geocoded_coordinates(monkeypatch):
    client = _build_client()
    try:
        tokens = _register_and_login(client, "hydrate-analyze@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        from api import projects as projects_api

        monkeypatch.setattr(
            projects_api.geocoding_service,
            "geocode_address",
            lambda **kwargs: {
                "latitude": _SITE_LAT,
                "longitude": _SITE_LON,
                "confidence": 87,
                "source": "OpenStreetMap (Nominatim)",
                "data_class": "B",
                "raw_label": "Unter den Linden 1, 10117 Berlin",
                "has_house_number": True,
            },
        )
        monkeypatch.setattr(
            projects_api.geocoding_service,
            "reverse_geocode",
            lambda **kwargs: None,
        )

        created = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Berlin PV",
                "street": "Unter den Linden",
                "house_number": "1",
                "plz": "10117",
                "city": "Berlin",
                "typ": "pv",
                "leistung_kw": 1200,
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]

        # Workspace save historically overwrote role_inputs without project_location
        # while leaving the geocoded Project row intact.
        patched = client.patch(
            f"/api/v1/projects/{project_id}",
            headers=headers,
            json={"role_inputs": {"anlagentyp": "solar", "anschlussleistung_kw": 1200}},
        )
        assert patched.status_code == 200, patched.text
        assert "project_location" not in patched.json()["role_inputs"]

        analyzed = client.post(
            "/api/v1/analyze",
            headers=headers,
            json={
                "project_id": project_id,
                "nennspannung": 20,
                "leistung_mw": 1.2,
                "leitungstyp": "NA2XS2Y240",
                "entfernung_km": 4.2,
                "anschlussart": "Einspeisung",
                "plz": "10117",
                "anlagentyp": "PV",
            },
        )
        assert analyzed.status_code == 200, analyzed.text
        body = analyzed.json()
        warnings = " ".join(str(item) for item in (body.get("warnungen") or []))
        assert "Platzhalterkoordinate" not in warnings

        db = client._gridcheck_session_factory()  # type: ignore[attr-defined]
        try:
            run = (
                db.query(AnalysisRun)
                .filter(AnalysisRun.project_id == project_id)
                .order_by(AnalysisRun.id.desc())
                .first()
            )
            assert run is not None
            request_payload = json.loads(run.input_json)
            loc = request_payload["project_location"]
            assert loc["latitude"] == _SITE_LAT
            assert loc["longitude"] == _SITE_LON
            result_payload = json.loads(run.result_json)
            result_loc = result_payload["eingabe"]["project_location"]
            assert result_loc["latitude"] == _SITE_LAT
            assert result_loc["longitude"] == _SITE_LON
            assert result_loc["latitude"] != _PLACEHOLDER_LAT
            assert result_loc["longitude"] != _PLACEHOLDER_LON
        finally:
            db.close()
    finally:
        _close_client(client)
