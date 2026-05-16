from __future__ import annotations

import copy
import hashlib
import json
import uuid

from fastapi.testclient import TestClient

from db.database import SessionLocal
from db.models import ReportRevisionRecord
from engine.revision import speichere_revision
from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf
from engine.stakeholder_reports.projektierer import build_projektierer_report
from engine.stakeholder_reports.renderer import (
    persist_report_revision,
    render_projektierer_html,
)
from main import app

client = TestClient(app)


def _auth_headers() -> dict[str, str]:
    email = f"projektierer-report-{uuid.uuid4().hex}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Passwort123!", "role": "projektierer"},
    )
    assert reg.status_code == 200, reg.text
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "Passwort123!"}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _report_request() -> dict:
    return {
        "nennspannung": 20.0,
        "leistung_mw": 5.0,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 10.0,
        "anschlussart": "Einspeisung",
        "plz": "30159",
        "anlagentyp": "PV",
    }


def _mock_report_analysis(monkeypatch, result: dict) -> None:
    from api import v2_reports as reports_api

    def _run(_payload: dict) -> dict:
        response = copy.deepcopy(result)
        revision = speichere_revision(
            response, engine_version="test-projektierer-report"
        )
        response["revision"] = {"hash": revision["hash"]}
        return response

    monkeypatch.setattr(reports_api, "run_v1_analysis", _run)
    monkeypatch.setattr(
        reports_api,
        "package_access_context",
        lambda *args, **kwargs: {
            "offer_id": "professional_anschlussstrategie",
            "package_scope": "professional",
            "report_scope": "professional",
            "usage_bucket": "oneoff",
            "ops_followup_required": True,
            "feature_flags": {},
            "billing_category": "paid",
            "free_quota_consumed": False,
            "entitlement": None,
        },
    )
    monkeypatch.setattr(
        reports_api, "enforce_package_rights", lambda payload, access: payload
    )


def _latest_report_revision() -> ReportRevisionRecord:
    db = SessionLocal()
    try:
        row = (
            db.query(ReportRevisionRecord)
            .filter(ReportRevisionRecord.report_type == "projektierer")
            .order_by(
                ReportRevisionRecord.revisionsnummer.desc(),
                ReportRevisionRecord.id.desc(),
            )
            .first()
        )
        assert row is not None
        return row
    finally:
        db.close()


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


def test_projektierer_pdf_bytes_smoke():
    report = build_projektierer_report(_engine_result())
    pdf_bytes = build_stakeholder_report_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_build_and_render_smoke():
    report = build_projektierer_report(_engine_result())
    html = render_projektierer_html(report)
    assert report["report_type"] == "projektierer"
    assert report["report_scope"] == "professional"
    assert report["report_scope_label"] == "Professional Anschlussstrategie"
    assert "normen_snapshot" in report and len(report["normen_snapshot"]) > 0
    assert (
        report["projektprofil_summary"]
        == "Hybridprojekt mit begrenzter NAP-Einspeisung"
    )
    assert report["recommended_focus"] == "Varianten frueh abstimmen"
    assert "<html" in html.lower()
    assert "ProjektiererReport" in html
    assert "Anschlussstrategie" in html


def test_basic_scope_hides_strategy_and_shows_boundary():
    engine_result = _engine_result()
    engine_result["billing_access"] = {
        "offer_id": "basic_schnellcheck",
        "package_scope": "basic",
        "report_scope": "basic",
    }
    report = build_projektierer_report(engine_result)
    html = render_projektierer_html(report)
    assert report["package_scope"] == "basic"
    assert report["report_scope"] == "basic"
    assert report["report_scope_label"] == "Basic Kernreport"
    assert report["includes_strategy_section"] is False
    assert "Paketgrenze" in html
    assert "Basic Kernreport" in html


def test_hash_determinism_for_same_input():
    report = build_projektierer_report(_engine_result())
    h1 = hashlib.sha256(
        json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    h2 = hashlib.sha256(
        json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert h1 == h2


def test_normen_snapshot_contains_ms_rules():
    report = build_projektierer_report(_engine_result())
    ids = {n["norm_id"] for n in report["normen_snapshot"]}
    assert "VDE-AR-N 4110" in ids


def test_persist_report_revision_smoke(isolierte_report_revisionen):
    report = build_projektierer_report(_engine_result())
    html = render_projektierer_html(report)
    rev = persist_report_revision(report, html, report.get("engine_revision_hash"))
    assert rev["hash"]
    assert rev["engine_revision_hash"] == "abc123"
    assert rev["verify_path"].endswith(rev["hash"])
    latest = _latest_report_revision()
    stored_report = json.loads(latest.report_json)
    assert latest.hash == rev["hash"]
    assert latest.engine_revision_hash == "abc123"
    assert stored_report["report_type"] == "projektierer"
    assert stored_report["audit_hash"] == rev["hash"]
    assert stored_report["report_revision"]["hash"] == rev["hash"]
    assert stored_report["report_revision"]["uuid"] == rev["uuid"]
    assert stored_report["report_revision"]["verify_path"] == rev["verify_path"]


def test_post_projektierer_report_html_includes_persisted_gridcheck(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    _mock_report_analysis(monkeypatch, _engine_result())
    r = client.post(
        "/api/v2/reports/projektierer",
        json={"analyze_request": _report_request()},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("output_format") == "html"
    rd = body.get("report_data") or {}
    gc = rd.get("gridcheck_report_data")
    assert isinstance(gc, dict)
    assert gc.get("report", {}).get("reportId") == body.get("report_revision", {}).get(
        "uuid"
    )
    latest = _latest_report_revision()
    stored = json.loads(latest.report_json)
    assert isinstance(stored.get("gridcheck_report_data"), dict)
    assert stored["gridcheck_report_data"]["report"]["reportId"] == latest.uuid


def test_post_projektierer_report_pdf(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    _mock_report_analysis(monkeypatch, _engine_result())
    r = client.post(
        "/api/v2/reports/projektierer?format=pdf",
        json={"analyze_request": _report_request()},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 1000
    latest = _latest_report_revision()
    assert latest.report_type == "projektierer"
    assert r.headers.get("x-gridcheck-report-revision-hash") == latest.hash
    assert r.headers.get("x-gridcheck-report-revision-uuid") == latest.uuid
    assert r.headers.get("x-gridcheck-report-verify-path", "").endswith(latest.hash)


def test_report_route_rejects_client_supplied_engine_result():
    r = client.post(
        "/api/v2/reports/projektierer",
        json={"engine_result": _engine_result()},
        headers=_auth_headers(),
    )
    assert r.status_code == 422, r.text
    assert "analysis_run_id" in r.text
