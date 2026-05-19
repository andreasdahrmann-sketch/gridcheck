"""Tests fuer GET /api/v1/geo/plz/{plz}.

Deckt drei Pflichtfaelle ab:
- Happy Path mit SNAP-VNB-Treffer
- Happy Path ohne SNAP-VNB
- Validierungsfehler (ungueltige PLZ)

Plus ein paar repraesentative Regionen, damit die kuratierte Daten-
zuordnung nicht stillschweigend kaputtgeht.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from geo.plz_lookup import _load_dataset
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_plz_dataset_cache():
    _load_dataset.cache_clear()
    yield
    _load_dataset.cache_clear()


def test_plz_mitnetz_region_snap_true():
    """Leipzig (04er-Praefix) -> MITNETZ + ENVIA, snap_verfuegbar=True."""
    r = client.get("/api/v1/geo/plz/04109")
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["plz"] == "04109"
    assert data["snap_verfuegbar"] is True
    assert "Sachsen" in data["bundesland_kandidaten"] or \
           "Sachsen-Anhalt" in data["bundesland_kandidaten"]

    kuerzel = {v["kuerzel"] for v in data["vnb_kandidaten"]}
    assert "MITNETZ" in kuerzel
    assert "ENVIA" in kuerzel

    mitnetz = next(v for v in data["vnb_kandidaten"] if v["kuerzel"] == "MITNETZ")
    assert mitnetz["snap_verfuegbar"] is True
    assert mitnetz["snap_url"]
    assert mitnetz["snap_url"].startswith("https://")

    assert data["confidence"] == "B-heuristisch"
    assert data["quelle"]
    assert data["stand"]
    assert data["hinweis"]


def test_plz_enbw_region_snap_true():
    """Stuttgart (70er-Praefix) -> EnBW Netze als Kandidat."""
    r = client.get("/api/v1/geo/plz/70173")
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["plz"] == "70173"
    assert data["snap_verfuegbar"] is True
    kuerzel = {v["kuerzel"] for v in data["vnb_kandidaten"]}
    assert "ENBW_NETZ" in kuerzel
    assert "Baden-Wuerttemberg" in data["bundesland_kandidaten"]
    assert data["hinweis"]


def test_plz_no_snap_region():
    """Heide (25er-Praefix) -> SH Netz ohne verifiziertes SNAP-Portal."""
    r = client.get("/api/v1/geo/plz/25746")
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["plz"] == "25746"
    assert data["snap_verfuegbar"] is False
    kuerzel = {v["kuerzel"] for v in data["vnb_kandidaten"]}
    assert "SH_NETZ" in kuerzel
    assert "Schleswig-Holstein" in data["bundesland_kandidaten"]
    assert data["hinweis"]


def test_plz_berlin_stromnetz():
    """Berlin (10er-Praefix) -> Stromnetz Berlin."""
    r = client.get("/api/v1/geo/plz/10115")
    assert r.status_code == 200, r.text
    data = r.json()
    kuerzel = {v["kuerzel"] for v in data["vnb_kandidaten"]}
    assert "STROMNETZ_BERLIN" in kuerzel
    assert "Berlin" in data["bundesland_kandidaten"]


def test_plz_hessen_syna():
    """Frankfurt (60er-Praefix) -> Syna."""
    r = client.get("/api/v1/geo/plz/60311")
    assert r.status_code == 200, r.text
    data = r.json()
    kuerzel = {v["kuerzel"] for v in data["vnb_kandidaten"]}
    assert "SYNA" in kuerzel
    assert data["snap_verfuegbar"] is True


def test_plz_invalid_format_returns_422():
    """Buchstaben in der PLZ -> 422 mit strukturiertem detail."""
    r = client.get("/api/v1/geo/plz/abcde")
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "PLZ_INVALID"
    assert "5" in (detail.get("hint") or "")


def test_plz_too_short_returns_422():
    """4-stellige PLZ wird abgelehnt."""
    r = client.get("/api/v1/geo/plz/1234")
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "PLZ_INVALID"


def test_plz_westnetz_region():
    """Dortmund (44er-Praefix) -> WESTNETZ-Kandidat."""
    r = client.get("/api/v1/geo/plz/44135")
    assert r.status_code == 200, r.text
    data = r.json()
    kuerzel = {v["kuerzel"] for v in data["vnb_kandidaten"]}
    assert "WESTNETZ" in kuerzel
    assert data["snap_verfuegbar"] is True


def test_plz_bayern_dual_vnb():
    """Augsburg (86er-Praefix) -> BAYERNWERK und LEW als Kandidaten."""
    r = client.get("/api/v1/geo/plz/86150")
    assert r.status_code == 200, r.text
    data = r.json()
    kuerzel = {v["kuerzel"] for v in data["vnb_kandidaten"]}
    assert "BAYERNWERK" in kuerzel
    assert "LEW" in kuerzel
    assert data["snap_verfuegbar"] is True
