from __future__ import annotations

import pytest

from economics.erloes import berechne_erloes


def test_wind_alias_nutzt_wind_onshore_volllaststunden(monkeypatch):
    monkeypatch.setattr(
        "economics.erloes.get_strompreis_eur_mwh",
        lambda: {"price_eur_mwh": 80.0, "source": "test", "timestamp": 0.0},
    )
    out = berechne_erloes("wind", 1.0)
    assert out["anlagentyp"] == "WIND_ONSHORE"
    assert out["volllaststunden_h_a"] == 2000
    assert out["energie_mwh_a"] == 2000.0


def test_negative_leistung_wird_abgewiesen():
    with pytest.raises(ValueError):
        berechne_erloes("PV", -1.0)

