"""Perf-Benchmarks für `build_stakeholder_report_pdf` (projektierer/vnb/invest).

Deterministischer Engine-Result-Fixture inline (Vorlage:
`backend/tests/test_projektierer_report.py::_engine_result`). Wir messen
nur den PDF-Build pro Stakeholder — vorgelagerte Engine-Berechnung ist
in test_perf_grid_calc.py separat abgedeckt.

Ziele:
  - Baseline für TIER-2-Diskussionen (ReportLab Style-Reuse, BL-PERF-002).
  - Drei Stakeholder werden getrennt gemessen, weil sich die Layouts und
    Style-Allokationen unterscheiden (vnb hat Signaturblock, invest hat
    KPI-Strip, projektierer hat technische Tabellen).
"""
from __future__ import annotations

from typing import Any

import pytest

from engine.stakeholder_reports.invest import build_invest_report
from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf
from engine.stakeholder_reports.projektierer import build_projektierer_report
from engine.stakeholder_reports.vnb import build_vnb_report


def _engine_result() -> dict[str, Any]:
    """Stabiler Beispiel-Engine-Result für Bench (kein DB-Zugriff)."""
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
        "revision": {"hash": "perfbench0000000000000000000000000000000000000000000000000000abcd"},
        "projektprofil": {"summary": "Hybridprojekt mit begrenzter NAP-Einspeisung"},
        "speicher_bewertung": {"summary": "Speicher mit netzdienlichen Elementen"},
        "route_environment": {"summary": "Trassenthemen sollten vertieft werden"},
        "stakeholder_bewertung": {
            "konflikt_summary": "Netzsicht und Projektsicht weichen deutlich ab",
            "recommended_focus": "Varianten frueh abstimmen",
        },
        "transparenz": {
            "confidence_notes": ["Datenqualitaet B"],
            "disclaimers": ["Vorlaeufige Analyse"],
        },
        "technical_details": {
            "spannungsfall": {"delta_u_prozent": 2.1, "bewertung": "GRUEN"},
            "kurzschluss": {"ik_referenz_ka": 12.0, "vorlaeufig": True},
            "leitung": {"querschnitt_mm2": 240, "typ": "NA2XS2Y"},
            "trasse": {"entfernung_km": 1.2, "heuristisch": True},
        },
        "grid_calculation_v2": {
            "calculation_version": "v2-perf-bench",
            "projektierer_perspective": {
                "plant_type_label": "Photovoltaik",
                "ac_kw": 5000,
                "feed_in_management_class": "direct_marketing",
                "process_timeline": {
                    "estimated_total": "8-16 Wochen",
                    "phases": [
                        {"phase": "VNB-Prüfung MS", "duration_weeks": "4-8"},
                    ],
                },
                "bkz_hint": {"hint": "BKZ qualitativ: mittleres Band"},
            },
            "eeg_feed_in_screening": {
                "applicable": True,
                "feed_in_management_class": "direct_marketing",
                "hints": ["Direktvermarktung erforderlich"],
            },
        },
    }


_ENGINE_RESULT = _engine_result()


@pytest.mark.benchmark(group="pdf_render")
def test_pdf_render_projektierer(benchmark) -> None:
    report = build_projektierer_report(_ENGINE_RESULT)

    def _build() -> int:
        return len(build_stakeholder_report_pdf(report))

    size = benchmark(_build)
    assert size > 1000


@pytest.mark.benchmark(group="pdf_render")
def test_pdf_render_vnb(benchmark) -> None:
    report = build_vnb_report(_ENGINE_RESULT)

    def _build() -> int:
        return len(build_stakeholder_report_pdf(report))

    size = benchmark(_build)
    assert size > 1000


@pytest.mark.benchmark(group="pdf_render")
def test_pdf_render_invest(benchmark) -> None:
    report = build_invest_report(_ENGINE_RESULT)

    def _build() -> int:
        return len(build_stakeholder_report_pdf(report))

    size = benchmark(_build)
    assert size > 1000
