from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from db.database import SessionLocal
from db.models import AnalysisRun, ReportRevisionRecord, User, make_checksum
from engine.revision import speichere_revision
from engine.stakeholder_reports.invest import build_invest_report
from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf
from engine.stakeholder_reports.renderer import (
    persist_report_revision,
    render_from_template,
    render_invest_html,
    render_vnb_html,
)
from engine.stakeholder_reports.vnb import VNB_NB_CHECKLISTE_HINWEIS, build_vnb_report
from main import app

client = TestClient(app)


def _reset_rate_limit_state() -> None:
    from core import rate_limit as rate_limit_mod

    rate_limit_mod._MEM_BUCKETS.clear()
    rate_limit_mod._REDIS_CLIENT = None


def setup_function(function=None):
    _reset_rate_limit_state()


def _register_and_login_user() -> tuple[str, dict[str, str]]:
    email = f"report-{uuid.uuid4().hex}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Passwort123!", "role": "projektierer"},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "Passwort123!"})
    assert login.status_code == 200, login.text
    return email, {"Authorization": f"Bearer {login.json()['access_token']}"}


def _auth_headers() -> dict[str, str]:
    return _register_and_login_user()[1]


def _report_request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "nennspannung": 20.0,
        "leistung_mw": 5.0,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 10.0,
        "anschlussart": "Einspeisung",
        "plz": "30159",
        "anlagentyp": "PV",
    }
    payload.update(overrides)
    return payload


def _mock_report_analysis(
    monkeypatch,
    result: dict,
    *,
    offer_id: str = "professional_anschlussstrategie",
    package_scope: str = "professional",
    report_scope: str = "professional",
) -> None:
    from api import v2_reports as reports_api

    def _run(_payload: dict) -> dict:
        response = copy.deepcopy(result)
        revision = speichere_revision(response, engine_version="test-stakeholder-report")
        response["revision"] = {"hash": revision["hash"]}
        return response

    monkeypatch.setattr(reports_api, "run_v1_analysis", _run)
    monkeypatch.setattr(
        reports_api,
        "package_access_context",
        lambda *args, **kwargs: {
            "offer_id": offer_id,
            "package_scope": package_scope,
            "report_scope": report_scope,
            "usage_bucket": "oneoff",
            "ops_followup_required": package_scope == "professional",
            "feature_flags": {},
            "billing_category": "paid",
            "free_quota_consumed": False,
            "entitlement": None,
        },
    )
    monkeypatch.setattr(reports_api, "enforce_package_rights", lambda payload, access: payload)


def _latest_report_revision(report_type: str) -> ReportRevisionRecord:
    db = SessionLocal()
    try:
        row = (
            db.query(ReportRevisionRecord)
            .filter(ReportRevisionRecord.report_type == report_type)
            .order_by(ReportRevisionRecord.revisionsnummer.desc(), ReportRevisionRecord.id.desc())
            .first()
        )
        assert row is not None
        return row
    finally:
        db.close()


def _engine_result_base() -> dict:
    return {
        "status": "OK",
        "eingabe": {
            "plz": "30159",
            "ort": "Hannover",
            "standort": "Gewerbepark Nord",
            "leistung_mw": 5.0,
            "nennspannung": 20.0,
            "anschlussart": "Einspeisung",
            "antragsteller": "SPV Hannover Nord",
            "projektreife": "planung",
            "n1_datengrundlage": "planner_assumption",
            "project_location": {"address_hint": "Gewerbepark Nord"},
        },
        "warnungen": ["Leitungslast nahe Grenzwert"],
        "empfehlungen": ["NVP-Alternative pruefen"],
        "n1": {"n1_sicher": False, "topologie_text": "Topologie unbekannt"},
        "fazit": {"entscheidung": "C"},
        "revision": {"hash": "vnb-invest-abc"},
        "datenqualitaet": {"klasse": "B", "text": "Solide Projektdaten. Ergebnis plausibel."},
        "thermisch": {"bewertung": "GELB", "text": "Thermische Auslastung nahe Grenzwert."},
        "spannung": {"bewertung": "GELB", "text": "Spannungsaenderung noch plausibel, aber knapp."},
        "kurzschluss": {"bewertung": "GELB", "text": "Kurzschlussleistung ausreichend mit Puffer."},
        "projektprofil": {"summary": "Hybridprofil mit begrenzter NAP-Einspeisung"},
        "speicher_bewertung": {"summary": "Teilweise netzdienlicher Speicherbetrieb"},
        "route_environment": {"summary": "Mittleres Trassenrisiko"},
        "stakeholder_bewertung": {
            "konflikt_summary": "Stakeholder-Zielkonflikt vorhanden",
            "recommended_focus": "Fokus auf Varianten- und Trassenargumentation",
        },
        "transparenz": {
            "confidence_notes": ["Datenqualitaet B"],
            "disclaimers": ["Keine Kapazitaetsgarantie"],
        },
    }


def test_vnb_pdf_bytes_smoke():
    report = build_vnb_report(_engine_result_base())
    pdf_bytes = build_stakeholder_report_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_vnb_build_render_smoke():
    report = build_vnb_report(_engine_result_base())
    html = render_vnb_html(report)
    assert len(report["technical_review_table"]) >= 1
    assert report["signature_section"]["fields"]
    assert report["report_type"] == "vnb"
    assert report["report_scope"] == "professional"
    assert report["report_scope_label"] == "Professional Anschlussstrategie"
    assert report["netzbetreiber_checkliste_hinweis"] == VNB_NB_CHECKLISTE_HINWEIS
    assert report["stakeholder_konflikt"] == "Stakeholder-Zielkonflikt vorhanden"
    assert len(report["request_review"]) == 4
    assert len(report["technical_precheck"]) == 4
    assert "freie interne Netzkapazitaet" in report["visibility_boundary_note"]
    assert len(report["normen_snapshot"]) > 0
    assert "<html" in html.lower()
    assert "Netzbetreiber" in html
    assert "Strukturierte Anfragepruefung" in html
    assert "Status- / Prozesssicht" in html
    assert "Daten-, Pruef- und Auditrolle" in html


def test_vnb_prefers_rich_n1_detail():
    er = _engine_result_base()
    er["n1"] = {
        "n1_sicher": False,
        "topologie_text": "Topologie unbekannt",
        "detail_text": "N-1-Level N1-3. Gesamtbewertung ROT. Engpass trafo.",
    }
    report = build_vnb_report(er)
    assert report["n1_detail"] == "N-1-Level N1-3. Gesamtbewertung ROT. Engpass trafo."


def test_vnb_render_from_template_alias():
    report = build_vnb_report(_engine_result_base())
    assert render_vnb_html(report) == render_from_template("vnb.html.j2", report)


def test_vnb_persist_report_revision_smoke(isolierte_report_revisionen):
    report = build_vnb_report(_engine_result_base())
    html = render_vnb_html(report)
    rev = persist_report_revision(report, html, report.get("engine_revision_hash"), report_type="vnb")
    assert rev["hash"]
    assert rev["engine_revision_hash"] == "vnb-invest-abc"
    latest = _latest_report_revision("vnb")
    stored_report = json.loads(latest.report_json)
    assert latest.hash == rev["hash"]
    assert stored_report["report_type"] == "vnb"
    assert stored_report["audit_hash"] == rev["hash"]
    assert stored_report["report_revision"]["hash"] == rev["hash"]
    assert stored_report["report_revision"]["uuid"] == rev["uuid"]


def test_invest_pdf_bytes_smoke():
    report = build_invest_report(_engine_result_base())
    pdf_bytes = build_stakeholder_report_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_invest_build_render_without_kosten():
    report = build_invest_report(_engine_result_base())
    html = render_invest_html(report)
    assert report["report_type"] == "invest"
    assert report["report_scope"] == "professional"
    assert report.get("kosten_indikation") is None
    assert report.get("cost_band") is None
    assert report["recommended_focus"] == "Fokus auf Varianten- und Trassenargumentation"
    assert "Kosten-Indikation" not in html
    assert "<html" in html.lower()
    assert "Standortbewertung" in html
    assert "Due-Diligence-orientierte Sicht" in html
    assert "Sichtbarkeitsgrenze" in html


def test_invest_kpi_and_timeline():
    er = _engine_result_base()
    er["grid_calculation_v2"] = {
        "projektierer_perspective": {
            "process_timeline": {"estimated_total": "8-16 Wochen", "phases": []},
        }
    }
    report = build_invest_report(er)
    assert len(report["kpi_summary"]) >= 3
    assert report["process_timeline"]


def test_invest_build_render_with_kosten():
    er = _engine_result_base()
    er["kosten"] = {
        "investition_gesamt_eur": 1_250_000,
        "band_niedrig_eur": 1_000_000,
        "band_basis_eur": 1_250_000,
        "band_hoch_eur": 1_650_000,
        "betriebskosten_pa_eur": 12_000,
        "konfidenz_prozent": 60,
        "quelle": "Referenzwerte",
        "band_annahmen": ["Bandbreite statt Punktwert."],
        "hauptrisikotreiber": ["Laengere Trasse."],
    }
    report = build_invest_report(er)
    html = render_invest_html(report)
    assert report["kosten_indikation"] is not None
    assert report["cost_band"] is not None
    assert report["kosten_indikation"]["investition_gesamt_eur"] == 1_250_000
    assert report["cost_band"]["hoch_eur"] == 1_650_000
    assert "Kosten-Indikation" in html
    assert "Kostenbandbreite" in html
    assert "investition_gesamt_eur" in html


def test_vnb_basic_scope_hides_strategy_and_marks_boundary():
    er = _engine_result_base()
    er["billing_access"] = {
        "offer_id": "basic_schnellcheck",
        "package_scope": "basic",
        "report_scope": "basic",
    }
    report = build_vnb_report(er)
    html = render_vnb_html(report)
    assert report["includes_strategy_section"] is False
    assert report["report_scope_label"] == "Basic Kernreport"
    assert "Paketgrenze" in html


def test_invest_basic_scope_hides_cost_section_and_marks_boundary():
    er = _engine_result_base()
    er["kosten"] = {"investition_gesamt_eur": 500000, "band_basis_eur": 500000}
    er["billing_access"] = {
        "offer_id": "basic_schnellcheck",
        "package_scope": "basic",
        "report_scope": "basic",
    }
    report = build_invest_report(er)
    html = render_invest_html(report)
    assert report["includes_cost_section"] is False
    assert report["report_scope_label"] == "Basic Kernreport"
    assert "Paketgrenze" in html


def test_invest_persist_report_revision_smoke(isolierte_report_revisionen):
    er = _engine_result_base()
    er["kosten"] = {"investition_gesamt_eur": 99, "band_basis_eur": 99}
    report = build_invest_report(er)
    html = render_invest_html(report)
    rev = persist_report_revision(report, html, report.get("engine_revision_hash"), report_type="invest")
    assert rev["hash"]
    latest = _latest_report_revision("invest")
    stored_report = json.loads(latest.report_json)
    assert latest.hash == rev["hash"]
    assert stored_report["kosten_indikation"]["investition_gesamt_eur"] == 99
    assert stored_report["report_revision"]["hash"] == rev["hash"]


def test_post_vnb_report_analyze_request(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    _mock_report_analysis(monkeypatch, _engine_result_base())
    r = client.post("/api/v2/reports/vnb", json={"analyze_request": _report_request()}, headers=_auth_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OK"
    assert body["report_type"] == "vnb"
    assert body["report_data"]["report_type"] == "vnb"
    assert body["report_data"]["source_analysis_run_id"] is not None
    assert body["report_data"]["audit_hash"] == body["report_revision"]["hash"]
    assert body["report_data"]["report_revision"]["hash"] == body["report_revision"]["hash"]
    assert body["report_data"]["report_verify_path"] == body["report_revision"]["verify_path"]
    latest = _latest_report_revision("vnb")
    assert latest.hash == body["report_revision"]["hash"]


def test_post_invest_report_analyze_request(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    er = _engine_result_base()
    er["kosten"] = {"investition_gesamt_eur": 500000, "band_basis_eur": 500000}
    _mock_report_analysis(monkeypatch, er)
    r = client.post("/api/v2/reports/invest", json={"analyze_request": _report_request()}, headers=_auth_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OK"
    assert body["report_type"] == "invest"
    assert body["report_data"]["kosten_indikation"]["investition_gesamt_eur"] == 500000
    assert body["report_data"]["report_revision"]["hash"] == body["report_revision"]["hash"]
    latest = _latest_report_revision("invest")
    assert latest.hash == body["report_revision"]["hash"]


def test_report_route_uses_persisted_analysis_run_source(
    isolierte_revisionen,
    isolierte_report_revisionen,
):
    email, headers = _register_and_login_user()
    result = _engine_result_base()
    revision = speichere_revision(result, engine_version="test-analysis-run")
    result["revision"] = {"hash": revision["hash"]}

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        run = AnalysisRun(
            user_id=user.id,
            project_id=None,
            source="interactive",
            status="completed",
            input_json=json.dumps(_report_request(), ensure_ascii=False),
            request_checksum=make_checksum(_report_request()),
            result_json=json.dumps(result, ensure_ascii=False),
            result_checksum=make_checksum(result),
            score=77,
            decision_code="C",
            revision_hash=revision["hash"],
            offer_id="professional_anschlussstrategie",
            package_scope="professional",
            usage_bucket="oneoff",
            billing_category="paid",
            free_quota_consumed=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    r = client.post("/api/v2/reports/vnb", json={"analysis_run_id": run_id}, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OK"
    assert body["report_revision"]["engine_revision_hash"] == revision["hash"]
    assert body["report_data"]["source_analysis_run_id"] == run_id
    assert body["report_data"]["source_revision_hash"] == revision["hash"]
    assert body["report_data"]["source_verify_path"].endswith(revision["hash"])
    assert body["report_data"]["report_revision"]["hash"] == body["report_revision"]["hash"]


def test_post_vnb_report_pdf_query_format(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    _mock_report_analysis(
        monkeypatch,
        _engine_result_base(),
        offer_id="basic_schnellcheck",
        package_scope="basic",
        report_scope="basic",
    )
    r = client.post(
        "/api/v2/reports/vnb?format=pdf",
        json={"analyze_request": _report_request(requested_offer_id="basic_schnellcheck")},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert "attachment" in r.headers.get("content-disposition", "").lower()
    assert "gridcheck-vnb-basic-" in r.headers.get("content-disposition", "").lower()
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 1000
    latest = _latest_report_revision("vnb")
    assert r.headers.get("x-gridcheck-report-revision-hash") == latest.hash
    assert r.headers.get("x-gridcheck-report-revision-uuid") == latest.uuid
    assert r.headers.get("x-gridcheck-report-verify-path", "").endswith(latest.hash)


def test_post_invest_report_pdf_body_output_format(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    er = _engine_result_base()
    er["kosten"] = {"investition_gesamt_eur": 500000, "band_basis_eur": 500000}
    _mock_report_analysis(
        monkeypatch,
        er,
        offer_id="premium_pre_check",
        package_scope="premium",
        report_scope="premium",
    )
    r = client.post(
        "/api/v2/reports/invest",
        json={"analyze_request": _report_request(requested_offer_id="premium_pre_check"), "output_format": "pdf"},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert "gridcheck-invest-premium-" in r.headers.get("content-disposition", "").lower()
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 1000
    latest = _latest_report_revision("invest")
    assert r.headers.get("x-gridcheck-report-revision-hash") == latest.hash
    assert r.headers.get("x-gridcheck-report-revision-uuid") == latest.uuid
    assert r.headers.get("x-gridcheck-report-verify-path", "").endswith(latest.hash)


def test_get_report_revision_verifies_source_binding(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    _mock_report_analysis(monkeypatch, _engine_result_base())
    headers = _auth_headers()
    export_response = client.post(
        "/api/v2/reports/vnb",
        json={"analyze_request": _report_request()},
        headers=headers,
    )
    assert export_response.status_code == 200, export_response.text
    exported = export_response.json()

    verify_response = client.get(
        exported["report_revision"]["verify_path"],
        headers=headers,
    )
    assert verify_response.status_code == 200, verify_response.text
    verify_body = verify_response.json()
    assert verify_body["integrity"]["ok"] is True
    assert verify_body["report_revision"]["hash"] == exported["report_revision"]["hash"]
    assert verify_body["source"]["analysis_run_id"] == exported["report_data"]["source_analysis_run_id"]
    assert verify_body["source"]["revision_hash"] == exported["report_data"]["source_revision_hash"]


def test_get_report_revision_detects_tampered_source_checksums(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    _mock_report_analysis(monkeypatch, _engine_result_base())
    headers = _auth_headers()
    export_response = client.post(
        "/api/v2/reports/vnb",
        json={"analyze_request": _report_request()},
        headers=headers,
    )
    assert export_response.status_code == 200, export_response.text
    exported = export_response.json()
    verify_path = exported["report_revision"]["verify_path"]

    db = SessionLocal()
    try:
        latest = _latest_report_revision("vnb")
        row = db.query(ReportRevisionRecord).filter(ReportRevisionRecord.id == latest.id).first()
        assert row is not None
        stored_report = json.loads(row.report_json)
        stored_report["source_result_checksum"] = "0" * 64
        row.report_json = json.dumps(stored_report, ensure_ascii=False)
        db.commit()
    finally:
        db.close()

    verify_response = client.get(verify_path, headers=headers)
    assert verify_response.status_code == 200, verify_response.text
    verify_body = verify_response.json()
    assert verify_body["integrity"]["ok"] is False
    assert verify_body["integrity"]["source_checks"]["result_checksum_matches"] is False


def test_report_route_rejects_double_source_payload():
    r = client.post(
        "/api/v2/reports/vnb",
        json={"analysis_run_id": 12, "analyze_request": _report_request()},
        headers=_auth_headers(),
    )
    assert r.status_code == 422, r.text
    assert "analyze_request or analysis_run_id" in r.text.lower()


def test_report_route_rejects_client_supplied_engine_result():
    r = client.post(
        "/api/v2/reports/vnb",
        json={"engine_result": _engine_result_base()},
        headers=_auth_headers(),
    )
    assert r.status_code == 422, r.text
    assert "analysis_run_id" in r.text.lower()


def test_vnb_report_route_is_rate_limited(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    _reset_rate_limit_state()
    _mock_report_analysis(monkeypatch, _engine_result_base())
    headers = _auth_headers()

    for _ in range(10):
        r = client.post("/api/v2/reports/vnb", json={"analyze_request": _report_request()}, headers=headers)
        assert r.status_code == 200, r.text

    limited = client.post("/api/v2/reports/vnb", json={"analyze_request": _report_request()}, headers=headers)
    assert limited.status_code == 429, limited.text
    detail = limited.json()["detail"]
    assert detail["code"] == "RATE_LIMITED"
    assert detail["message"] == "Zu viele Report-Exporte"
