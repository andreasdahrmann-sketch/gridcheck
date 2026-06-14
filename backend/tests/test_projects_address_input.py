"""Tests fuer Standort-Eingabe (Adresse vs. Koordinaten) bei POST /api/v1/projects.

Kontrakt:
- Pflicht: mindestens PLZ ODER vollstaendige Koordinaten (lat+lon).
- Adresse + keine Koordinaten -> Backend laeuft geocode_address (gemockt) und persistiert lat/lon.
- Koordinaten + keine Adresse -> akzeptiert; Reverse-Geocoding ist best-effort.
- PLZ allein -> bleibt legacy-vertraeglich (Bestandsverhalten).
- Geocoding-Ausfall -> Warnung in der Response, kein 500.
- Geocoding-Metadaten landen in role_inputs["_geocoding"] fuer Revisionssicherheit.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from db.database import Base, get_db
from main import app
from tests.postgres_test_utils import build_isolated_postgres_session_factory


def _build_client() -> TestClient:
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(Base.metadata, label="projects_addr")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client._gridcheck_cleanup = cleanup  # type: ignore[attr-defined]
    return client


def _close_client(client: TestClient) -> None:
    app.dependency_overrides.clear()
    client.close()
    client._gridcheck_cleanup()  # type: ignore[attr-defined]


def _register_and_login(client: TestClient, email: str, password: str = "Passwort123!") -> dict:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "role": "projektierer"})
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()


def test_create_project_with_address_geocodes_lat_lon(monkeypatch):
    client = _build_client()
    try:
        tokens = _register_and_login(client, "addr-geocode@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        from api import projects as projects_api

        called = {}

        def fake_geocode_address(**kwargs):
            called["kwargs"] = kwargs
            return {
                "latitude": 52.520008,
                "longitude": 13.404954,
                "confidence": 87,
                "source": "OpenStreetMap (Nominatim)",
                "data_class": "B",
                "raw_label": "Unter den Linden 1, 10117 Berlin",
                "has_house_number": True,
            }

        def fail_reverse(**kwargs):
            raise AssertionError("reverse_geocode darf bei Adresseingabe nicht aufgerufen werden")

        monkeypatch.setattr(projects_api.geocoding_service, "geocode_address", fake_geocode_address)
        monkeypatch.setattr(projects_api.geocoding_service, "reverse_geocode", fail_reverse)

        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Adresse Test",
                "street": "Unter den Linden",
                "house_number": "1",
                "plz": "10117",
                "city": "Berlin",
                "typ": "pv",
                "leistung_kw": 500,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["latitude"] == 52.520008
        assert body["longitude"] == 13.404954
        assert body["street"] == "Unter den Linden"
        assert body["house_number"] == "1"
        assert body["plz"] == "10117"
        assert body["warnings"] == []
        assert called["kwargs"]["plz"] == "10117"
        geocoding_meta = body["role_inputs"].get("_geocoding")
        assert geocoding_meta is not None
        assert geocoding_meta["mode"] == "forward"
        assert geocoding_meta["confidence"] == 87
        assert geocoding_meta["data_class"] == "B"
    finally:
        _close_client(client)


def test_create_project_with_latlon_only_works(monkeypatch):
    client = _build_client()
    try:
        tokens = _register_and_login(client, "latlon-only@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        from api import projects as projects_api

        def fail_geocode(**kwargs):
            raise AssertionError("geocode_address darf bei Koordinaten-Eingabe nicht aufgerufen werden")

        monkeypatch.setattr(projects_api.geocoding_service, "geocode_address", fail_geocode)
        monkeypatch.setattr(projects_api.geocoding_service, "reverse_geocode", lambda **kwargs: None)

        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "LatLon Test",
                "latitude": 50.110924,
                "longitude": 8.682127,
                "typ": "pv",
                "leistung_kw": 750,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["latitude"] == 50.110924
        assert body["longitude"] == 8.682127
        assert body["plz"] is None or body["plz"] == ""
    finally:
        _close_client(client)


def test_create_project_with_plz_only_still_works():
    client = _build_client()
    try:
        tokens = _register_and_login(client, "plz-only@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "PLZ Legacy",
                "plz": "30159",
                "typ": "pv",
                "leistung_kw": 1000,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["plz"] == "30159"
        assert body["latitude"] is None
        assert body["longitude"] is None
        assert body["warnings"] == []
    finally:
        _close_client(client)


def test_create_project_rejects_when_no_location():
    client = _build_client()
    try:
        tokens = _register_and_login(client, "no-location@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Keine Standortangabe",
                "typ": "pv",
                "leistung_kw": 100,
            },
        )
        assert response.status_code == 422, response.text
    finally:
        _close_client(client)


def test_geocoding_failure_returns_warning_not_500(monkeypatch):
    client = _build_client()
    try:
        tokens = _register_and_login(client, "geocode-fail@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        from api import projects as projects_api

        monkeypatch.setattr(projects_api.geocoding_service, "geocode_address", lambda **kwargs: None)
        monkeypatch.setattr(projects_api.geocoding_service, "reverse_geocode", lambda **kwargs: None)

        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Adresse ohne Geocoding",
                "street": "Erfundeneweg",
                "house_number": "9999",
                "plz": "99998",
                "city": "Nirgendwo",
                "typ": "pv",
                "leistung_kw": 200,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert "geocoding_failed" in body["warnings"]
        assert body["latitude"] is None
        assert body["longitude"] is None
        assert body["plz"] == "99998"
    finally:
        _close_client(client)
