"""Perf-Benchmarks für `engine.grid_calculation_v2.calculate_grid_connection`.

Drei deterministische Input-Größen (klein/mittel/groß):
  - 100 kW PV / NS / Stich (radial)
  - 1 MW PV / MS / Ring
  - 10 MW PV / MS / Ring

Inputs sind bewusst nicht aus der DB geseedet — die Funktion ist rein
deterministisch (siehe Rules `01-backend.mdc` → calculations/), kein
Side-Effect, kein I/O. Genau das, was wir hier messen wollen.
"""
from __future__ import annotations

import pytest

from engine.grid_calculation_types import GridConnectionInput
from engine.grid_calculation_v2 import calculate_grid_connection


def _input_small() -> GridConnectionInput:
    return GridConnectionInput(
        project_type="generation",
        plant_type="pv",
        power_kw=100.0,
        power_factor=0.95,
        voltage_level="low",
        connection_type="three_phase",
        cable_length_km=0.3,
        cable_length_source="user_input",
        cable_cross_section_mm2=150,
        cable_material="aluminum",
        cable_type="underground",
        grid_topology="radial",
    )


def _input_medium() -> GridConnectionInput:
    return GridConnectionInput(
        project_type="generation",
        plant_type="pv",
        power_kw=1000.0,
        power_factor=0.95,
        voltage_level="medium",
        connection_type="three_phase",
        cable_length_km=2.0,
        cable_length_source="user_input",
        cable_cross_section_mm2=240,
        cable_material="aluminum",
        cable_type="underground",
        grid_topology="ring",
        transformer_power_kva=2500.0,
        transformer_impedance_percent=6.0,
        transformer_load_percent=40.0,
        network_short_circuit_mva=250.0,
    )


def _input_large() -> GridConnectionInput:
    return GridConnectionInput(
        project_type="generation",
        plant_type="pv",
        power_kw=10_000.0,
        power_factor=0.95,
        voltage_level="medium",
        connection_type="three_phase",
        cable_length_km=5.0,
        cable_length_source="user_input",
        cable_cross_section_mm2=300,
        cable_material="aluminum",
        cable_type="underground",
        grid_topology="ring",
        transformer_power_kva=25_000.0,
        transformer_impedance_percent=10.0,
        transformer_load_percent=55.0,
        network_short_circuit_mva=500.0,
    )


@pytest.mark.benchmark(group="grid_calc")
def test_calculate_grid_connection_small(benchmark) -> None:
    inp = _input_small()
    result = benchmark(calculate_grid_connection, inp, anlagentyp="PV")
    assert result.calculation_version
    assert result.voltage_drop_analysis is not None


@pytest.mark.benchmark(group="grid_calc")
def test_calculate_grid_connection_medium(benchmark) -> None:
    inp = _input_medium()
    result = benchmark(calculate_grid_connection, inp, anlagentyp="PV")
    assert result.calculation_version
    assert result.short_circuit_analysis is not None


@pytest.mark.benchmark(group="grid_calc")
def test_calculate_grid_connection_large(benchmark) -> None:
    inp = _input_large()
    result = benchmark(calculate_grid_connection, inp, anlagentyp="PV")
    assert result.calculation_version
    assert result.thermal_analysis is not None
