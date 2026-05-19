"""Tests fuer GET /api/v1/geo/osm-nearby (mocked Overpass)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from geo.osm_nearby import (
    SAMPLE_OVERPASS_RESPONSE,
    clear_osm_nearby_cache_for_tests,
    lookup_osm_nearby,
    parse_overpass_elements,
)
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_osm_nearby_state():
    clear_osm_nearby_cache_for_tests()
    yield
    clear_osm_nearby_cache_for_tests()


def _mock_overpass(_lat: float, _lon: float, _radius_m: int) -> list[dict]:
    return list(SAMPLE_OVERPASS_RESPONSE["elements"])


def test_parse_overpass_elements_filters_and_sorts():
    assets = parse_overpass_elements(
        SAMPLE_OVERPASS_RESPONSE["elements"],
        center_lat=51.34,
        center_lon=12.37,
        radius_m=5_000,
    )
    assert len(assets) == 2
    assert assets[0].distance_m <= assets[1].distance_m
    assert assets[0].type == "substation"
    assert assets[0].name == "Demo Umspannwerk"
    assert "freie" not in (assets[0].tags_summary or "").lower()


def test_lookup_osm_nearby_service_mock():
    result = lookup_osm_nearby(
        lat=51.34,
        lon=12.37,
        radius_m=2_000,
        overpass_fetch=_mock_overpass,
    )
    assert result.validierungsstatus == "OK"
    assert len(result.assets) == 2
    assert result.data_class == "B"
    assert result.source == "OSM"
    assert "kapazitaet" in result.disclaimer.lower()


def test_osm_nearby_endpoint_happy_path():
    def _fetch(lat: float, lon: float, radius_m: int) -> list[dict]:
        return _mock_overpass(lat, lon, radius_m)

    from geo import osm_nearby as module

    original = module.fetch_overpass
    module.fetch_overpass = _fetch
    try:
        r = client.get(
            "/api/v1/geo/osm-nearby",
            params={"lat": 51.34, "lon": 12.37, "radius_m": 2500},
        )
    finally:
        module.fetch_overpass = original

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["source"] == "OSM"
    assert data["data_class"] == "B"
    assert data["confidence"] == "B"
    assert len(data["assets"]) >= 1
    asset = data["assets"][0]
    assert "lat" in asset and "lon" in asset and "distance_m" in asset
    assert data["disclaimer"]
    assert data["hinweis"]
    assert "kapazitaet" in data["disclaimer"].lower()


def test_osm_nearby_requires_location():
    r = client.get("/api/v1/geo/osm-nearby", params={"radius_m": 1000})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "LOCATION_REQUIRED"


def test_osm_nearby_incomplete_coordinates():
    r = client.get("/api/v1/geo/osm-nearby", params={"lat": 51.34, "radius_m": 1000})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "COORDINATES_INCOMPLETE"


def test_osm_nearby_cache_hit():
    from geo import osm_nearby as module

    calls = {"count": 0}
    original = module.fetch_overpass

    def _fetch(lat: float, lon: float, radius_m: int) -> list[dict]:
        calls["count"] += 1
        return _mock_overpass(lat, lon, radius_m)

    module.fetch_overpass = _fetch
    try:
        first = client.get(
            "/api/v1/geo/osm-nearby",
            params={"lat": 51.34, "lon": 12.37, "radius_m": 2000},
        )
        second = client.get(
            "/api/v1/geo/osm-nearby",
            params={"lat": 51.34, "lon": 12.37, "radius_m": 2000},
        )
    finally:
        module.fetch_overpass = original

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["cache_hit"] is True
    assert calls["count"] == 1
