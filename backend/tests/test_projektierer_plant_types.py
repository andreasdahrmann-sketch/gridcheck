"""Tests for plant-type defaults, EEG classes, and reactive-power screening."""
from __future__ import annotations

import pytest

from engine.grid_calculation_v2 import grid_connection_input_from_engine
from engine.grid_calculation_types import GridConnectionInput
from engine.nb_akzeptanz_screening import screen_eeg_feed_in, screen_reactive_power
from engine.plant_types import REACTIVE_POWER_SCREENING_KW, PlantType, resolve_plant_context


def _base_input(**overrides) -> GridConnectionInput:
    data = {
        "project_type": "generation",
        "power_kw": 50.0,
        "ac_kw": 50.0,
        "power_factor": 0.95,
        "voltage_level": "low",
        "connection_type": "three_phase",
        "cable_length_km": 0.5,
        "cable_length_source": "user_input",
        "cable_cross_section_mm2": 150,
        "cable_material": "aluminum",
        "cable_type": "underground",
        "grid_topology": "radial",
    }
    data.update(overrides)
    return GridConnectionInput(**data)


class TestPlantTypePv5Mw:
    def test_cos_phi_and_simultaneity_for_pv_5mw(self, basis_pv_ms):
        eingabe = dict(basis_pv_ms)
        eingabe["leistung_mw"] = 5.0
        eingabe["anlagentyp"] = "PV"

        ctx = resolve_plant_context(eingabe)
        assert ctx.power_factor == pytest.approx(0.9, abs=0.001)
        assert ctx.simultaneity_factor == pytest.approx(0.85, abs=0.001)
        assert ctx.ac_kw == pytest.approx(5000.0, rel=0.01)
        assert ctx.screening_power_kw == pytest.approx(5000.0 * 0.85, rel=0.01)

        inp = grid_connection_input_from_engine(eingabe)
        assert inp.power_factor == pytest.approx(0.9, abs=0.001)
        assert inp.screening_power_kw == pytest.approx(4250.0, rel=0.01)
        assert inp.plant_type == "pv"


class TestPvUsesAcForGridCalculations:
    def test_dc_higher_than_ac_screening_uses_ac(self):
        eingabe = {
            "plant_type": "pv",
            "ac_kw": 100.0,
            "dc_kwp": 130.0,
            "leistung_mw": 0.2,
            "nennspannung": 20,
            "topologie": "stich",
        }
        ctx = resolve_plant_context(eingabe)
        assert ctx.ac_kw == pytest.approx(100.0)
        assert ctx.dc_kwp == pytest.approx(130.0)
        assert ctx.overbuild_ratio == pytest.approx(1.3, rel=0.01)
        assert ctx.screening_power_kw == pytest.approx(85.0, rel=0.01)

        inp = grid_connection_input_from_engine(eingabe)
        assert inp.power_kw == pytest.approx(100.0)
        assert inp.screening_power_kw == pytest.approx(85.0, rel=0.01)


class TestWindSimultaneity:
    def test_wind_simultaneity_035(self):
        eingabe = {"plant_type": "wind", "ac_kw": 3000.0, "nennspannung": 20}
        ctx = resolve_plant_context(eingabe)
        assert ctx.plant_type == PlantType.WIND
        assert ctx.simultaneity_factor == pytest.approx(0.35, abs=0.001)
        assert ctx.screening_power_kw == pytest.approx(1050.0, rel=0.01)


class TestHybridAlias:
    def test_legacy_hybrid_alias(self):
        ctx = resolve_plant_context({"plant_type": "hybrid", "ac_kw": 500.0})
        assert ctx.plant_type == PlantType.HYBRID_PV_BESS


class TestEegFeedInClass:
    def test_pv_30kw_remote_control_class(self):
        inp = _base_input(power_kw=30.0, ac_kw=30.0, plant_type="pv")
        eeg = screen_eeg_feed_in(inp)
        assert eeg.applicable is True
        assert eeg.feed_in_management_class == "remote_control"

    def test_pv_15kw_none_class(self):
        inp = _base_input(power_kw=15.0, ac_kw=15.0, plant_type="pv")
        eeg = screen_eeg_feed_in(inp)
        assert eeg.feed_in_management_class == "none"


class TestReactivePowerScreening:
    def test_150kw_triggers_reactive_screening(self):
        inp = _base_input(
            power_kw=150.0,
            ac_kw=150.0,
            voltage_level="medium",
            plant_type="pv",
            reactive_power_mode="q_u",
        )
        reactive = screen_reactive_power(inp)
        assert reactive.applicable is True
        assert reactive.power_kw == pytest.approx(150.0)
        assert reactive.threshold_kw == REACTIVE_POWER_SCREENING_KW
        assert len(reactive.checklist) >= 3
        assert any("Q(U)" in item.topic for item in reactive.checklist)

    def test_100kw_no_reactive_screening(self):
        inp = _base_input(power_kw=100.0, ac_kw=100.0, plant_type="pv")
        reactive = screen_reactive_power(inp)
        assert reactive.applicable is False
