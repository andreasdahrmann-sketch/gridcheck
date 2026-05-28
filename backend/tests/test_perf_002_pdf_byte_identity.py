"""Regression test for BL-PERF-002: ParagraphStyle caching in pdf_layout.py.

Background
----------
BL-PERF-002 introduced ``@lru_cache`` on the eight ``*_style(palette)`` factories
in ``backend/engine/stakeholder_reports/pdf_layout.py``. The intent is purely a
performance optimisation -- the rendered PDFs for the three stakeholder layouts
(projektierer / vnb / invest) must remain byte-identical to the pre-cache
output.

This test renders each stakeholder PDF twice (and once more after clearing the
style caches) and asserts SHA-256 byte-identity across all three runs. Because
ReportLab embeds ``/CreationDate``, ``/ModDate`` and a random File-ID by default,
``reportlab.rl_config.invariant`` is forced to ``1`` for the test scope so the
PDF binary is deterministic and only differs when the actual style/layout output
diverges.

If this test ever turns red the cache is leaking state (e.g. someone mutates a
cached style instance after retrieval) and the cache should be removed for that
specific factory -- not the test relaxed.
"""
from __future__ import annotations

import hashlib

import pytest
from reportlab import rl_config

from engine.stakeholder_reports import pdf_layout
from engine.stakeholder_reports.invest import build_invest_report
from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf
from engine.stakeholder_reports.projektierer import build_projektierer_report
from engine.stakeholder_reports.vnb import build_vnb_report


def _engine_result() -> dict:
    """Stable engine-result fixture.

    Vorlage: ``backend/tests/test_projektierer_report.py::_engine_result`` --
    bewusst inline gehalten, damit dieser Regressionstest unabhaengig von
    Fixtures aus den DB-Tests laeuft.
    """
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
        "revision": {
            "hash": "perf002bytes00000000000000000000000000000000000000000000000abcd"
        },
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
    }


# Style-Funktionen, die per @lru_cache in BL-PERF-002 gecached werden.
# Wir leiten die Liste bewusst per ``hasattr(..., "cache_clear")`` ab, damit der
# Test ohne Anpassung weiter funktioniert, falls in Zukunft eine Funktion aus
# dem Cache rausfaellt (Mutations-Audit-Ausnahme).
_STYLE_FACTORIES = (
    pdf_layout.title_style,
    pdf_layout.subtitle_style,
    pdf_layout.section_style,
    pdf_layout.body_style,
    pdf_layout.body_bold_style,
    pdf_layout.muted_style,
    pdf_layout.hero_value_style,
    pdf_layout.hero_label_style,
)


def _clear_style_caches() -> None:
    for fn in _STYLE_FACTORIES:
        clear = getattr(fn, "cache_clear", None)
        if clear is not None:
            clear()


@pytest.fixture(autouse=True)
def _force_invariant_reportlab(monkeypatch):
    """Make ReportLab output deterministic (no real timestamps / random File-ID)."""
    monkeypatch.setattr(rl_config, "invariant", 1, raising=False)
    # Caches sauber starten, damit der erste Render in diesem Test reproduzierbar
    # die Style-Konstruktion durchlaeuft.
    _clear_style_caches()
    yield
    _clear_style_caches()


@pytest.mark.parametrize(
    ("report_type", "builder"),
    [
        ("projektierer", build_projektierer_report),
        ("vnb", build_vnb_report),
        ("invest", build_invest_report),
    ],
)
def test_pdf_bytes_identical_across_renders(report_type, builder) -> None:
    """Zweimaliger Render desselben Reports muss byte-identisch sein.

    Schuetzt gegen Cache-Leaks aus BL-PERF-002 (Mutation einer gecachten
    ParagraphStyle-Instanz wuerde hier sofort sichtbar werden).
    """
    report = builder(_engine_result())

    pdf_first = build_stakeholder_report_pdf(report)
    pdf_second = build_stakeholder_report_pdf(report)

    digest_first = hashlib.sha256(pdf_first).hexdigest()
    digest_second = hashlib.sha256(pdf_second).hexdigest()

    assert digest_first == digest_second, (
        f"PDF bytes differ between two consecutive renders for {report_type}: "
        f"{digest_first} vs {digest_second}"
    )
    assert pdf_first.startswith(b"%PDF")
    assert len(pdf_first) > 1000


@pytest.mark.parametrize(
    ("report_type", "builder"),
    [
        ("projektierer", build_projektierer_report),
        ("vnb", build_vnb_report),
        ("invest", build_invest_report),
    ],
)
def test_pdf_bytes_identical_after_style_cache_clear(report_type, builder) -> None:
    """Render vor und nach ``cache_clear()`` muss byte-identisch sein.

    Verifiziert, dass ein "kalt" rekonstruiertes Style-Objekt exakt dasselbe
    PDF erzeugt wie eines aus dem Cache -- das ist die eigentliche
    Verhaltens-Garantie der BL-PERF-002-Optimierung.
    """
    report = builder(_engine_result())

    pdf_cached = build_stakeholder_report_pdf(report)
    _clear_style_caches()
    pdf_after_clear = build_stakeholder_report_pdf(report)

    digest_cached = hashlib.sha256(pdf_cached).hexdigest()
    digest_after_clear = hashlib.sha256(pdf_after_clear).hexdigest()

    assert digest_cached == digest_after_clear, (
        f"PDF bytes differ for {report_type} between cached and fresh-cache "
        f"render: {digest_cached} vs {digest_after_clear}"
    )
