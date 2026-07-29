"""Tests fuer engine.grid_calculation_v2."""
from __future__ import annotations

import math

import pytest

from engine.grid_calculation_v2 import (
    CALCULATION_VERSION,
    calculate_grid_connection,
    calculate_voltage_drop,
    grid_connection_input_from_engine,
)
from engine.grid_calculation_types import GridConnectionInput


def _base_input(**overrides) -> GridConnectionInput:
    data = {
        "project_type": "generation",
        "power_kw": 50.0,
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


class TestVoltageDropFormula:
    def test_known_case_three_phase_aluminum_150mm2(self):
        inp = _base_input(power_kw=50.0, cable_length_km=0.5, cable_cross_section_mm2=150)
        assumptions = []
        result = calculate_voltage_drop(inp, assumptions)

        u_n_v = 400.0
        cos_phi = 0.95
        sin_phi = math.sqrt(1 - cos_phi**2)
        current_a = (50_000) / (math.sqrt(3) * u_n_v * cos_phi)

        r_per_km = 0.206 * (1 + 0.00403 * (70 - 20))
        x_per_km = 0.063
        r_total = r_per_km * 0.5
        x_total = x_per_km * 0.5
        expected_du_v = math.sqrt(3) * current_a * (r_total * cos_phi + x_total * sin_phi)
        expected_du_pct = (expected_du_v / u_n_v) * 100.0

        assert result.formula.startswith("ΔU = √3")
        assert result.inputs.current_a == pytest.approx(round(current_a, 1), rel=0.01)
        assert result.delta_u_percent == pytest.approx(round(expected_du_pct, 2), abs=0.05)
        assert result.limit_percent == 3.0


class TestShortCircuitMissingData:
    def test_cannot_calculate_without_network_and_transformer_data(self):
        inp = _base_input(
            transformer_power_kva=None,
            transformer_impedance_percent=None,
            network_short_circuit_mva=None,
        )
        result = calculate_grid_connection(inp)
        sc = result.short_circuit_analysis
        assert sc.cannot_calculate is True
        assert len(sc.missing_data) >= 2
        assert "IEC 60909" in sc.disclaimer


class TestAssumptionsWhenEstimated:
    def test_assumptions_non_empty_for_estimated_cable_length(self):
        inp = _base_input(cable_length_source="estimated")
        result = calculate_grid_connection(inp)
        assert len(result.assumptions) >= 1
        assert any(a.parameter == "Kabellaenge" for a in result.assumptions)

    def test_calculation_version(self):
        inp = _base_input()
        result = calculate_grid_connection(inp)
        assert result.calculation_version == CALCULATION_VERSION


class TestEngineAdapter:
    def test_from_engine_eingabe_produces_v2_block(self, basis_pv_ms):
        from engine.berechnung import berechne_netzanschluss

        r = berechne_netzanschluss(basis_pv_ms, dry_run=True)
        assert "grid_calculation_v2" in r
        v2 = r["grid_calculation_v2"]
        assert v2.get("calculation_version") == CALCULATION_VERSION
        assert "n1_assessment" in v2
        assert "disclaimer" in v2["n1_assessment"]

    def test_adapter_maps_ms_voltage(self, basis_pv_ms):
        inp = grid_connection_input_from_engine(basis_pv_ms)
        assert inp.voltage_level == "medium"
        assert inp.nominal_voltage_kv == pytest.approx(float(basis_pv_ms["nennspannung"]))
        assert inp.power_kw == pytest.approx(basis_pv_ms["leistung_mw"] * 1000)


class TestNominalVoltagePreserved:
    """Regression: MV must not collapse every nennspannung to 20 kV."""

    def test_10kv_vs_20kv_changes_current_and_delta_u(self):
        common = {
            "project_type": "generation",
            "power_kw": 5000.0,
            "power_factor": 0.9,
            "voltage_level": "medium",
            "connection_type": "three_phase",
            "cable_length_km": 5.0,
            "cable_length_source": "user_input",
            "cable_cross_section_mm2": 150,
            "cable_material": "aluminum",
            "cable_type": "underground",
            "grid_topology": "ring",
        }
        result_20 = calculate_voltage_drop(
            GridConnectionInput(**common, nominal_voltage_kv=20.0),
            [],
        )
        result_10 = calculate_voltage_drop(
            GridConnectionInput(**common, nominal_voltage_kv=10.0),
            [],
        )

        assert result_20.inputs.voltage_kv == 20.0
        assert result_10.inputs.voltage_kv == 10.0
        # I ~ 1/U and ΔU% ~ 1/U² → 10 kV must be materially stricter than 20 kV.
        assert result_10.inputs.current_a == pytest.approx(result_20.inputs.current_a * 2.0, rel=0.02)
        assert result_10.delta_u_percent == pytest.approx(result_20.delta_u_percent * 4.0, rel=0.05)
        assert result_20.compliant is True
        assert result_10.compliant is False

    def test_adapter_preserves_explicit_10kv(self):
        eingabe = {
            "nennspannung": 10,
            "leistung_mw": 5.0,
            "leitungstyp": "NA2XS2Y150",
            "entfernung_km": 5.0,
            "anschlussart": "Einspeisung",
            "cos_phi": 0.9,
            "plant_type": "pv",
            "topologie": "ring",
        }
        inp = grid_connection_input_from_engine(eingabe)
        assert inp.voltage_level == "medium"
        assert inp.nominal_voltage_kv == 10.0
        result = calculate_voltage_drop(inp, [])
        assert result.inputs.voltage_kv == 10.0
        assert result.compliant is False
