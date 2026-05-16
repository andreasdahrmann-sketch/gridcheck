from __future__ import annotations

import copy

from engine.gridcheck_report_mapper import build_gridcheck_report_data_from_engine_result
from engine.stakeholder_reports.projektierer import build_projektierer_report
from engine.stakeholder_reports.report_quality import (
    run_pre_pdf_quality_checks,
    validate_report_for_finalization,
)


def _engine_result() -> dict:
    return {
        "status": "OK",
        "eingabe": {
            "plz": "30159",
            "ort": "Hannover",
            "leistung_mw": 5.0,
            "nennspannung": 20.0,
            "anschlussart": "Einspeisung",
        },
        "warnungen": ["Leitungslast nahe Grenzwert"],
        "empfehlungen": ["NVP-Alternative pruefen"],
        "n1": {"n1_sicher": False, "topologie_text": "Topologie unbekannt"},
        "fazit": {"entscheidung": "C"},
        "revision": {"hash": "abc123"},
        "transparenz": {
            "disclaimers": ["Vorlaeufige Analyse ohne Kapazitaetsgarantie"],
        },
    }


def _valid_project_developer_payload() -> dict:
    return build_gridcheck_report_data_from_engine_result(
        _engine_result(),
        stakeholder_type="project_developer",
        project_id="proj-1",
        project_name="Testprojekt",
        report_id="rep-1",
        audit_id="audit-1",
        generated_by="user",
    )


def _valid_wrapper() -> dict:
    return build_projektierer_report(_engine_result())


def test_valid_project_developer_passes():
    data = _valid_project_developer_payload()
    ok, errors = validate_report_for_finalization(data)
    assert ok, errors
    issues = run_pre_pdf_quality_checks(data, report_wrapper=_valid_wrapper())
    assert issues == []


def test_missing_report_id_fails():
    data = _valid_project_developer_payload()
    data["report"]["reportId"] = ""
    ok, errors = validate_report_for_finalization(data)
    assert not ok
    assert any("report.reportId" in e for e in errors)


def test_binding_language_in_summary_fails_soft_check():
    data = _valid_project_developer_payload()
    data["assessment"]["summary"] = "Netzanschluss Zusage ist gesichert."
    ok, errors = validate_report_for_finalization(data)
    assert ok, errors
    issues = run_pre_pdf_quality_checks(data, report_wrapper=_valid_wrapper())
    assert any("verbindlich wirken" in i for i in issues)


def test_missing_disclaimers_on_wrapper_fails():
    data = _valid_project_developer_payload()
    wrapper = _valid_wrapper()
    wrapper["disclaimers"] = []
    issues = run_pre_pdf_quality_checks(data, report_wrapper=wrapper)
    assert any("disclaimers" in i.lower() for i in issues)


def test_mapper_output_passes_for_all_stakeholders():
    result = _engine_result()
    for legacy, stakeholder in (
        ("projektierer", "project_developer"),
        ("vnb", "grid_operator"),
        ("invest", "investor"),
    ):
        data = build_gridcheck_report_data_from_engine_result(
            result,
            stakeholder_type=stakeholder,  # type: ignore[arg-type]
            project_id="p1",
            project_name="Hannover",
            generated_by="user",
        )
        ok, errors = validate_report_for_finalization(data)
        assert ok, f"{stakeholder}: {errors}"


def test_grid_operator_requires_generated_by():
    data = _valid_project_developer_payload()
    data = copy.deepcopy(data)
    data["report"]["stakeholderType"] = "grid_operator"
    data["audit"]["generatedBy"] = None
    ok, errors = validate_report_for_finalization(data)
    assert not ok
    assert any("generatedBy" in e for e in errors)
