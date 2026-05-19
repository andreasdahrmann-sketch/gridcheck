from __future__ import annotations

import pytest

from engine.gridcheck_report_mapper import (
    build_gridcheck_report_data_from_engine_result,
    stakeholder_type_for_legacy_report_type,
)


def _minimal_engine_ok() -> dict:
    return {
        "status": "OK",
        "engine_version": "test-engine",
        "eingabe": {
            "nennspannung": 20.0,
            "leistung_mw": 15.0,
            "entfernung_km": 3.4,
            "anschlussart": "Einspeisung",
            "anlagentyp": "PV",
            "plz": "12345",
            "ort": "Beispielhausen",
            "project_location": {"latitude": 52.5, "longitude": 9.9},
            "project_id": 42,
        },
        "fazit": {
            "entscheidung": "B",
            "text": "BEDINGT PLAUSIBEL",
            "detail": "Score 55/100",
            "farbe": "GELB",
        },
        "scores": {"gesamt": 55, "harte_verstoesse": []},
        "n1": {
            "n1_sicher": False,
            "n1_klasse": "N1-2",
            "bewertung": "GELB",
            "detail_text": "Screening ohne vollstaendige Netzdaten.",
            "detail_empfehlungen": ["VNB-Daten nachfordern"],
            "detail_annahmen": ["Reserve heuristisch"],
            "nachweise_fehlend": ["Betriebsmittelliste"],
            "topologie_text": "Ring/Stich nicht abschliessend bewertbar.",
        },
        "kosten": {
            "band_niedrig_eur": 1_000_000,
            "band_basis_eur": 1_200_000,
            "band_hoch_eur": 1_500_000,
            "investition_gesamt_eur": 1_200_000,
            "kosten_trasse_eur": 400_000,
            "kosten_station_eur": 500_000,
            "kosten_planung_eur": 200_000,
            "kosten_genehmigung_eur": 100_000,
            "konfidenz_prozent": 50,
            "hauptrisikotreiber": ["Trasse"],
        },
        "datenqualitaet": {"klasse": "C", "text": "Demo"},
        "warnungen": ["Demo-Warnung"],
        "empfehlungen": [
            "Variante pruefen",
            "VNB ansprechen",
            "Leistungsszenarien vergleichen",
        ],
        "transparenz": {
            "assumptions": ["Modellannahme A"],
            "disclaimers": ["Keine Zusage"],
        },
        "projektprofil": {
            "total_installed_kw": 18_000.0,
            "max_export_kw": 15_000.0,
            "summary": "PV Hybrid-Stub",
        },
        "route_environment": {"risk_level": "mittel", "summary": "Trasse mittel"},
        "stakeholder_bewertung": {"konflikt_summary": "Konflikt moderat"},
        "revision": {"hash": "a" * 64, "previous_hash": "b" * 64},
        "_provenance": {
            "request_checksum": "c" * 64,
            "result_checksum": "d" * 64,
            "analysis_run_id": 99,
        },
    }


def test_build_gridcheck_report_data_core_keys():
    raw = _minimal_engine_ok()
    data = build_gridcheck_report_data_from_engine_result(
        raw,
        stakeholder_type="project_developer",
        project_id="42",
        project_name="Demo",
        report_id="r1",
        audit_id="a1",
        generated_by="system",
    )
    assert data["report"]["stakeholderType"] == "project_developer"
    assert data["project"]["feedInCapacityMw"] == 15.0
    assert data["location"]["latitude"] == 52.5
    assert data["grid"]["n1Screening"]["status"] in {
        "limited",
        "screening_only",
        "critical",
        "requires_grid_operator_data",
    }
    assert len(data["assessment"]["nextSteps"]) >= 3
    assert data["cost"]["currency"] == "EUR"
    assert data["audit"]["inputHash"] == "c" * 64


def test_mapper_merges_grid_calculation_v2_perspective():
    raw = _minimal_engine_ok()
    raw["grid_calculation_v2"] = {
        "feasibility": {"status": "conditional", "summary": "V2-Screening: bedingt"},
        "projektierer_perspective": {
            "plant_type_label": "Photovoltaik",
            "ac_kw": 800,
            "process_timeline": {"estimated_total": "4-8 Wochen"},
            "bkz_hint": {"hint": "BKZ Band mittel"},
        },
        "eeg_feed_in_screening": {
            "applicable": True,
            "hints": ["Fernsteuerbarkeit abstimmen"],
        },
    }
    data = build_gridcheck_report_data_from_engine_result(
        raw,
        stakeholder_type="project_developer",
        project_id="42",
        project_name="Demo",
    )
    findings = data["assessment"]["keyFindings"]
    assert any("Photovoltaik" in f for f in findings)
    assert any("V2-Screening" in f for f in findings)
    assert any("Zeitplan" in s for s in data["assessment"]["nextSteps"])
    assert any("EEG" in w for w in data["assessment"]["warnings"])


def test_stakeholder_type_for_legacy():
    assert (
        stakeholder_type_for_legacy_report_type("projektierer") == "project_developer"
    )
    assert stakeholder_type_for_legacy_report_type("vnb") == "grid_operator"
    assert stakeholder_type_for_legacy_report_type("invest") == "investor"


def test_rejects_non_ok_status():
    with pytest.raises(ValueError, match="OK"):
        build_gridcheck_report_data_from_engine_result(
            {"status": "FEHLER"},
            stakeholder_type="investor",
            project_id="1",
            project_name="X",
        )
