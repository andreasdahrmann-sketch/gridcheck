from __future__ import annotations

import hashlib
import json

from engine.stakeholder_reports.projektierer import build_projektierer_report
from engine.stakeholder_reports.renderer import persist_report_revision, render_projektierer_html


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
    }


def test_build_and_render_smoke():
    report = build_projektierer_report(_engine_result())
    html = render_projektierer_html(report)
    assert report["report_type"] == "projektierer"
    assert "normen_snapshot" in report and len(report["normen_snapshot"]) > 0
    assert "<html" in html.lower()
    assert "ProjektiererReport" in html


def test_hash_determinism_for_same_input():
    report = build_projektierer_report(_engine_result())
    h1 = hashlib.sha256(json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    h2 = hashlib.sha256(json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    assert h1 == h2


def test_normen_snapshot_contains_ms_rules():
    report = build_projektierer_report(_engine_result())
    ids = {n["norm_id"] for n in report["normen_snapshot"]}
    assert "VDE-AR-N 4110" in ids


def test_persist_report_revision_smoke(tmp_path, monkeypatch):
    from engine.stakeholder_reports import renderer

    monkeypatch.setattr(renderer, "REPORT_REV_PATH", str(tmp_path / "report_revisionen.jsonl"))
    report = build_projektierer_report(_engine_result())
    html = render_projektierer_html(report)
    rev = persist_report_revision(report, html, report.get("engine_revision_hash"))
    assert rev["hash"]
    assert rev["engine_revision_hash"] == "abc123"

