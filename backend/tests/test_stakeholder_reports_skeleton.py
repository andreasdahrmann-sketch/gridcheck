"""Smoke-Test MS PDF-1a: Modul laedt + Skelett laeuft ohne Crash."""
from __future__ import annotations

from datetime import datetime

from engine.stakeholder_reports import StakeholderReport, ReportKontext
from compliance import NORMEN, get_norm, get_normen_fuer_spannungsebene


def test_normen_registry_geladen():
    assert len(NORMEN) >= 20
    assert "VDE-AR-N 4110" in NORMEN
    assert "DIN EN 60909" in NORMEN
    assert "EnWG" in NORMEN


def test_get_norm_liefert_stand():
    n = get_norm("VDE-AR-N 4110")
    assert n is not None
    assert n.stand == "2023-09"


def test_normen_fuer_ms_spannung():
    normen = get_normen_fuer_spannungsebene(20.0, nur_kategorien=["Anwendungsregel"])
    ids = {n.norm_id for n in normen}
    assert "VDE-AR-N 4110" in ids
    assert "VDE-AR-N 4105" not in ids


class _DummyReport(StakeholderReport):
    UNTERTITEL = "Skelett-Test"

    def _build_role_sections(self, doc):
        return


def test_basisklasse_rendert_pdf():
    kontext = ReportKontext(
        rolle="projektierer",
        request_data={"plz": "28195", "leistung_kw": 5000},
        result_data={"score": 85.0},
        project_id=1,
        app_version="1.0.0-skeleton",
    )
    rep = _DummyReport(kontext)
    pdf_bytes = rep.render()
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_kontext_timestamp_ist_utc_iso():
    k = ReportKontext(
        rolle="endkunde",
        request_data={},
        result_data={},
        project_id=1,
    )
    assert k.timestamp_utc.endswith("Z")
    datetime.fromisoformat(k.timestamp_utc.replace("Z", "+00:00"))
