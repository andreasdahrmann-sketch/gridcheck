from __future__ import annotations

from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf


def _base_report(report_type: str, unsafe_text: str) -> dict:
    return {
        "report_type": report_type,
        "standort": unsafe_text,
        "project_name": unsafe_text,
        "report_generated_at": "2026-06-07T11:05:00Z",
        "report_version": "1.0",
        "app_normstand": "VDE test",
        "report_scope_label": "Standard & Pilot <Scope",
        "entscheidung": "B",
        "leistung_mw": 5.0,
        "spannungsebene": "MS",
        "anschlussart": "Einspeisung",
        "plz": "30159",
        "anlagentyp": "PV",
    }


def test_projektierer_pdf_escapes_bkz_text_with_xml_metacharacters():
    unsafe_text = "Müller & Solarpark <Nord"
    report = _base_report("projektierer", unsafe_text)
    report.update(
        {
            "bkz_hint": unsafe_text,
            "process_timeline": [unsafe_text],
            "technical_details_table": [
                {"kenngroesse": "Spannung", "wert": unsafe_text, "hinweis": "GELB"}
            ],
        }
    )

    pdf_bytes = build_stakeholder_report_pdf(report)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_invest_pdf_escapes_hero_and_risk_text_with_xml_metacharacters():
    unsafe_text = "Müller & Solarpark <Nord"
    report = _base_report("invest", unsafe_text)
    report.update(
        {
            "recommended_focus": f"Fokus {unsafe_text}",
            "scores": {"gesamt": 77},
            "risk_overview": [
                {"label": unsafe_text, "detail": unsafe_text, "status": "mittel"}
            ],
            "empfohlene_massnahmen": [unsafe_text],
            "kpi_summary": ["Score 77"],
        }
    )

    pdf_bytes = build_stakeholder_report_pdf(report)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
