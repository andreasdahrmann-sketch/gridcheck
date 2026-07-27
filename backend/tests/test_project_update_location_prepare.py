"""Unit tests for PATCH location merge/re-geocode helper (no DB required)."""

from __future__ import annotations

from types import SimpleNamespace

from api.projects import _prepare_project_update_payload


def _existing(**overrides):
    base = {
        "street": "Unter den Linden",
        "house_number": "1",
        "plz": "10117",
        "city": "Berlin",
        "ort": None,
        "latitude": 52.520008,
        "longitude": 13.404954,
        "role_inputs": '{"plz": "10117"}',
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_prepare_update_regeocodes_when_address_changes(monkeypatch):
    from api import projects as projects_api

    calls: list[dict] = []

    def fake_geocode_address(**kwargs):
        calls.append(kwargs)
        return {
            "latitude": 48.137154,
            "longitude": 11.576124,
            "confidence": 88,
            "source": "OpenStreetMap (Nominatim)",
            "data_class": "B",
            "raw_label": "Marienplatz 1, 80331 Muenchen",
            "has_house_number": True,
        }

    monkeypatch.setattr(projects_api.geocoding_service, "geocode_address", fake_geocode_address)
    monkeypatch.setattr(projects_api.geocoding_service, "reverse_geocode", lambda **kwargs: None)

    patch, warnings = _prepare_project_update_payload(
        _existing(),
        {
            "street": "Marienplatz",
            "house_number": "1",
            "plz": "80331",
            "city": "Muenchen",
        },
    )

    assert warnings == []
    assert len(calls) == 1
    assert calls[0]["plz"] == "80331"
    assert patch["latitude"] == 48.137154
    assert patch["longitude"] == 11.576124
    assert patch["role_inputs"]["_geocoding"]["mode"] == "forward"


def test_prepare_update_keeps_coords_when_only_name_changes(monkeypatch):
    from api import projects as projects_api

    monkeypatch.setattr(
        projects_api.geocoding_service,
        "geocode_address",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("geocode should not run")),
    )

    patch, warnings = _prepare_project_update_payload(_existing(), {"name": "Neu"})
    assert warnings == []
    assert patch == {"name": "Neu"}


def test_prepare_update_keeps_coords_for_plz_patch_without_full_address(monkeypatch):
    from api import projects as projects_api

    monkeypatch.setattr(
        projects_api.geocoding_service,
        "geocode_address",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("geocode should not run")),
    )
    monkeypatch.setattr(
        projects_api.geocoding_service,
        "reverse_geocode",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("reverse geocode should not run")),
    )

    existing = _existing(street=None, house_number=None, plz=None, city=None)
    patch, warnings = _prepare_project_update_payload(existing, {"plz": "60311"})
    assert warnings == []
    assert patch == {"plz": "60311"}


def test_prepare_update_clears_coords_when_regeocode_fails(monkeypatch):
    from api import projects as projects_api

    monkeypatch.setattr(projects_api.geocoding_service, "geocode_address", lambda **kwargs: None)
    monkeypatch.setattr(projects_api.geocoding_service, "reverse_geocode", lambda **kwargs: None)

    patch, warnings = _prepare_project_update_payload(
        _existing(),
        {"street": "Erfundeneweg", "house_number": "1", "plz": "99998", "city": "Nirgendwo"},
    )
    assert "geocoding_failed" in warnings
    assert patch["latitude"] is None
    assert patch["longitude"] is None
