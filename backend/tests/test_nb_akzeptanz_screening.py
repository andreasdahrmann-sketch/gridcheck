"""Tests fuer Netzbetreiber-Akzeptanz Screening (Gaps 6-12)."""
from __future__ import annotations

import pytest

from engine.grid_calculation_v2 import calculate_grid_connection
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


class TestTransformerAssessment:
    def test_missing_trafo_data_insufficient_data(self):
        inp = _base_input(
            transformer_power_kva=None,
            transformer_load_percent=None,
        )
        result = calculate_grid_connection(inp)
        ta = result.transformer_assessment
        assert ta.status == "insufficient_data"
        assert "transformer_power_kva" in ta.required_fields
        assert "transformer_load_percent" in ta.required_fields
        assert ta.screened_total_utilization_percent is None

    def test_with_trafo_data_screened_not_fake_capacity(self):
        inp = _base_input(
            transformer_power_kva=630.0,
            transformer_load_percent=40.0,
            power_kw=30.0,
        )
        result = calculate_grid_connection(inp)
        ta = result.transformer_assessment
        assert ta.status == "screened"
        assert ta.screened_total_utilization_percent is not None
        assert "keine freie Kapazität" in ta.disclaimer or "keine verbindliche" in ta.disclaimer


class TestEegScreening:
    def test_pv_30kw_eeg_25kw_warning(self):
        inp = _base_input(power_kw=30.0, ac_kw=30.0, project_type="generation")
        result = calculate_grid_connection(inp)
        eeg = result.eeg_feed_in_screening
        assert eeg.applicable is True
        assert eeg.feed_in_management_class == "remote_control"
        assert any("§ 9 EEG" in w or "25" in w for w in eeg.warnings)
        assert any("Fernsteuer" in d for d in eeg.required_documents + eeg.hints + eeg.warnings)


class TestProtectionChecklist:
    def test_generation_has_protection_checklist(self):
        inp = _base_input(project_type="generation")
        result = calculate_grid_connection(inp)
        pc = result.protection_concept_screening
        assert pc.applicable is True
        assert len(pc.checklist) >= 3
        topics = {item.topic for item in pc.checklist}
        assert any("NA-Schutz" in t for t in topics)
        assert any("Einstellwerte" in t for t in topics)
        assert all(item.status != "pass" for item in pc.checklist)  # type: ignore[comparison-overlap]

    def test_consumption_protection_not_applicable(self):
        inp = _base_input(project_type="consumption")
        result = calculate_grid_connection(inp)
        assert result.protection_concept_screening.applicable is False


class TestNormReferences:
    def test_ns_generation_includes_4105(self):
        inp = _base_input(voltage_level="low", project_type="generation")
        result = calculate_grid_connection(inp)
        codes = [r.code for r in result.norm_references_applied]
        assert "VDE-AR-N 4105:2018-11" in codes
        assert "EN 50160:2010" in codes
        assert "EEG 2023" in codes


class TestNetworkFeedback:
    def test_generation_cannot_quantify(self):
        inp = _base_input(project_type="generation")
        result = calculate_grid_connection(inp)
        nf = result.network_feedback_screening
        assert nf.applicable is True
        assert nf.cannot_quantify is True
        assert len(nf.topics) >= 2
