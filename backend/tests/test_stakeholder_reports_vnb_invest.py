from __future__ import annotations

import json

from fastapi.testclient import TestClient

from engine.stakeholder_reports.invest import build_invest_report
from engine.stakeholder_reports.renderer import (
    persist_report_revision,
    render_from_template,
    render_invest_html,
    render_vnb_html,
)
from engine.stakeholder_reports.vnb import VNB_NB_CHECKLISTE_HINWEIS, build_vnb_report
from main import app

client = TestClient(app)


def _engine_result_base() -> dict:
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
        "revision": {"hash": "vnb-invest-abc"},
    }


def test_vnb_build_render_smoke():
    report = build_vnb_report(_engine_result_base())
    html = render_vnb_html(report)
    assert report["report_type"] == "vnb"
    assert report["netzbetreiber_checkliste_hinweis"] == VNB_NB_CHECKLISTE_HINWEIS
    assert len(report["normen_snapshot"]) > 0
    assert "<html" in html.lower()
    assert "Netzbetreiber" in html


def test_vnb_render_from_template_alias():
    report = build_vnb_report(_engine_result_base())
    assert render_vnb_html(report) == render_from_template("vnb.html.j2", report)


def test_vnb_persist_report_revision_smoke(tmp_path, monkeypatch):
    from engine.stakeholder_reports import renderer

    rev_path = str(tmp_path / "report_revisionen.jsonl")
    monkeypatch.setattr(renderer, "REPORT_REV_PATH", rev_path)
    report = build_vnb_report(_engine_result_base())
    html = render_vnb_html(report)
    rev = persist_report_revision(
        report, html, report.get("engine_revision_hash"), report_type="vnb"
    )
    assert rev["hash"]
    assert rev["engine_revision_hash"] == "vnb-invest-abc"
    line = (tmp_path / "report_revisionen.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1]
    stored = json.loads(line)
    assert stored["report_type"] == "vnb"
    assert stored["daten"]["report"]["report_type"] == "vnb"


def test_invest_build_render_without_kosten():
    report = build_invest_report(_engine_result_base())
    html = render_invest_html(report)
    assert report["report_type"] == "invest"
    assert report.get("kosten_indikation") is None
    assert "Kosten-Indikation" not in html
    assert "<html" in html.lower()


def test_invest_build_render_with_kosten():
    er = _engine_result_base()
    er["kosten"] = {
        "investition_gesamt_eur": 1_250_000,
        "betriebskosten_pa_eur": 12_000,
        "konfidenz_prozent": 60,
        "quelle": "Referenzwerte",
    }
    report = build_invest_report(er)
    html = render_invest_html(report)
    assert report["kosten_indikation"] is not None
    assert report["kosten_indikation"]["investition_gesamt_eur"] == 1_250_000
    assert "Kosten-Indikation" in html
    assert "investition_gesamt_eur" in html


def test_invest_persist_report_revision_smoke(tmp_path, monkeypatch):
    from engine.stakeholder_reports import renderer

    rev_path = str(tmp_path / "report_revisionen.jsonl")
    monkeypatch.setattr(renderer, "REPORT_REV_PATH", rev_path)
    er = _engine_result_base()
    er["kosten"] = {"investition_gesamt_eur": 99}
    report = build_invest_report(er)
    html = render_invest_html(report)
    rev = persist_report_revision(
        report, html, report.get("engine_revision_hash"), report_type="invest"
    )
    assert rev["hash"]
    line = (tmp_path / "report_revisionen.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1]
    stored = json.loads(line)
    assert stored["report_type"] == "invest"
    assert stored["daten"]["report"]["kosten_indikation"]["investition_gesamt_eur"] == 99


def test_post_vnb_report_engine_result(tmp_path, monkeypatch):
    from engine.stakeholder_reports import renderer

    rev_file = tmp_path / "report_revisionen.jsonl"
    monkeypatch.setattr(renderer, "REPORT_REV_PATH", str(rev_file))

    r = client.post("/api/v2/reports/vnb", json={"engine_result": _engine_result_base()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OK"
    assert body["report_type"] == "vnb"
    assert "checkliste" in body["html"].lower() or "Checkliste" in body["html"]
    assert body["report_data"]["report_type"] == "vnb"
    assert body["report_revision"]["hash"]
    last = json.loads(rev_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["report_type"] == "vnb"


def test_post_invest_report_engine_result(tmp_path, monkeypatch):
    from engine.stakeholder_reports import renderer

    rev_file = tmp_path / "report_revisionen.jsonl"
    monkeypatch.setattr(renderer, "REPORT_REV_PATH", str(rev_file))

    er = _engine_result_base()
    er["kosten"] = {"investition_gesamt_eur": 500000}
    r = client.post("/api/v2/reports/invest", json={"engine_result": er})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OK"
    assert body["report_type"] == "invest"
    assert body["report_data"]["kosten_indikation"]["investition_gesamt_eur"] == 500000
    assert body["report_revision"]["hash"]
    last = json.loads(rev_file.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert last["report_type"] == "invest"
