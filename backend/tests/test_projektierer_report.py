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


def _hannover_hybrid_ms_report_request() -> dict:
    """Realistisches DE-Beispiel: Hannover (30159), PV+BESS, 5 MW, MS (20 kV)."""
    return {
        "plz": "30159",
        "ort": "Hannover",
        "standort": "Gewerbepark Nord",
        "nennspannung": 20.0,
        "leistung_mw": 5.0,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 4.2,
        "anschlussart": "Einspeisung",
        "anlagentyp": "PV",
        "projektreife": "planung",
        "project_components": [
            {"component_type": "pv", "capacity_kw": 4000, "max_export_kw": 3500},
            {
                "component_type": "battery",
                "capacity_kw": 2000,
                "energy_kwh": 8000,
                "controllable": True,
            },
        ],
        "netzanschlusspunkt": {
            "max_export_kw": 3500,
            "max_import_kw": 1200,
            "export_limit_mode": "dynamic",
        },
        "storage_profile": {
            "has_storage": True,
            "operation_mode": "partial_grid_support",
            "power_kw": 2000,
            "energy_kwh": 8000,
            "remote_control_capable": True,
            "reactive_power_capable": True,
        },
        "stakeholder_context": {
            "customer_type": "projektierer",
            "priority_focus": "balanced",
        },
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


def test_projektierer_analyze_then_pdf_hannover_hybrid_ms(
    isolierte_revisionen,
    isolierte_report_revisionen,
    monkeypatch,
):
    """E2E: reale Engine-Analyse (Hannover, PV+BESS, 5 MW, MS) + Projektierer-PDF-Export."""
    import api.analyze_v2 as analyze_v2_api

    monkeypatch.setattr(
        analyze_v2_api,
        "enforce_package_rights",
        lambda payload, access: payload,
    )

    headers = _auth_headers()
    analyze_payload = _hannover_hybrid_ms_report_request()

    analyze_res = client.post(
        "/api/v1/analyze",
        json=analyze_payload,
        headers=headers,
    )
    assert analyze_res.status_code == 200, analyze_res.text
    analyze_body = analyze_res.json()
    assert analyze_body.get("status") == "OK", analyze_body
    projektprofil = analyze_body.get("projektprofil") or {}
    assert projektprofil.get("is_hybrid") is True
    assert float(analyze_payload["leistung_mw"]) == 5.0
    assert float(analyze_payload["nennspannung"]) == 20.0
    assert analyze_payload["plz"] == "30159"

    engine_result = _engine_result()
    engine_result["eingabe"] = {
        "plz": "30159",
        "ort": "Hannover",
        "leistung_mw": 5.0,
        "nennspannung": 20.0,
        "anschlussart": "Einspeisung",
    }
    engine_result["projektprofil"] = {
        "summary": str(projektprofil.get("summary") or "Hybridprojekt mit begrenzter NAP-Einspeisung"),
        "is_hybrid": True,
    }
    engine_result["speicher_bewertung"] = analyze_body.get("speicher_bewertung") or {
        "summary": "Speicher mit netzdienlichen Elementen"
    }
    _mock_report_analysis(monkeypatch, engine_result)

    pdf_res = client.post(
        "/api/v2/reports/projektierer?format=pdf",
        json={"analyze_request": _report_request()},
        headers=headers,
    )
    assert pdf_res.status_code == 200, pdf_res.text
    assert pdf_res.headers.get("content-type", "").startswith("application/pdf")
    assert pdf_res.content.startswith(b"%PDF")
    assert len(pdf_res.content) > 0

    report = build_projektierer_report(engine_result)
    assert report["spannungsebene"] == "MS"
    assert report["leistung_mw"] == 5.0
    assert len(report.get("normen_snapshot") or []) > 0


def test_report_route_rejects_client_supplied_engine_result():
    r = client.post(
        "/api/v2/reports/projektierer",
        json={"engine_result": _engine_result()},
        headers=_auth_headers(),
    )
    assert r.status_code == 422, r.text
    assert "analysis_run_id" in r.text
