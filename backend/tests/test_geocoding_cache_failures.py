"""Geocoding cache must not treat transport failures as permanent misses.

Regression: Nominatim timeouts / HTTP errors were cached as None, so the same
address kept failing until LRU eviction even after the provider recovered.
Genuine empty provider responses may still be negative-cached.
"""

from __future__ import annotations

import httpx
import pytest

from services import geocoding_service


@pytest.fixture(autouse=True)
def _clear_geocoding_cache():
    geocoding_service.clear_geocoding_cache_for_tests()
    yield
    geocoding_service.clear_geocoding_cache_for_tests()


def test_geocode_address_retries_after_transport_error() -> None:
    calls = {"n": 0}

    def flaky_then_ok(url, *, params, timeout_seconds, user_agent):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("nominatim timeout")
        return [
            {
                "lat": "52.520008",
                "lon": "13.404954",
                "importance": 0.7,
                "display_name": "Unter den Linden 1, 10117 Berlin",
                "address": {"house_number": "1", "road": "Unter den Linden"},
            }
        ]

    first = geocoding_service.geocode_address(
        street="Unter den Linden",
        house_number="1",
        plz="10117",
        city="Berlin",
        http_get_json=flaky_then_ok,
    )
    assert first is None

    second = geocoding_service.geocode_address(
        street="Unter den Linden",
        house_number="1",
        plz="10117",
        city="Berlin",
        http_get_json=flaky_then_ok,
    )
    assert second is not None
    assert second["latitude"] == 52.520008
    assert second["longitude"] == 13.404954
    assert calls["n"] == 2


def test_geocode_address_still_negative_caches_empty_results() -> None:
    calls = {"n": 0}

    def empty_payload(url, *, params, timeout_seconds, user_agent):
        calls["n"] += 1
        return []

    first = geocoding_service.geocode_address(
        street="Nowhere Street",
        house_number="999",
        plz="00000",
        city="Nirgends",
        http_get_json=empty_payload,
    )
    assert first is None

    second = geocoding_service.geocode_address(
        street="Nowhere Street",
        house_number="999",
        plz="00000",
        city="Nirgends",
        http_get_json=empty_payload,
    )
    assert second is None
    assert calls["n"] == 1


def test_reverse_geocode_retries_after_http_error() -> None:
    calls = {"n": 0}

    def flaky_then_ok(url, *, params, timeout_seconds, user_agent):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.HTTPStatusError(
                "503",
                request=httpx.Request("GET", url),
                response=httpx.Response(503),
            )
        return {
            "importance": 0.6,
            "display_name": "Unter den Linden 1, 10117 Berlin",
            "address": {
                "road": "Unter den Linden",
                "house_number": "1",
                "postcode": "10117",
                "city": "Berlin",
            },
        }

    first = geocoding_service.reverse_geocode(lat=52.52, lon=13.405, http_get_json=flaky_then_ok)
    assert first is None

    second = geocoding_service.reverse_geocode(lat=52.52, lon=13.405, http_get_json=flaky_then_ok)
    assert second is not None
    assert second["street"] == "Unter den Linden"
    assert second["plz"] == "10117"
    assert calls["n"] == 2
