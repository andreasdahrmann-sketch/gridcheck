from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from api.analyze_v2 import AnalyzeRequest
from core.auth import get_current_user, require_csrf
from core.rate_limit import enforce_scoped_rate_limit
from db.database import get_db
from db.models import (
    AnalysisRun,
    ReportRevisionRecord,
    RevisionRecord,
    User,
    make_checksum,
)
from engine.revision import build_revision_data
from engine.gridcheck_report_mapper import (
    build_gridcheck_report_data_from_engine_result,
    stakeholder_type_for_legacy_report_type,
)
from engine.stakeholder_reports.invest import build_invest_report
from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf
from engine.stakeholder_reports.projektierer import build_projektierer_report
from engine.stakeholder_reports.renderer import (
    build_source_verify_path,
    persist_report_revision,
    render_invest_html,
    render_projektierer_html,
    render_vnb_html,
    verify_report_revision_record,
)
from engine.stakeholder_reports.report_quality import run_pre_pdf_quality_checks
from engine.stakeholder_reports.vnb import build_vnb_report
from services import project_service
from services.conversion_tracking_service import track_report_exported
from services.billing_service import (
    ensure_analysis_allowed,
    enforce_package_rights,
    package_access_context,
    persist_completed_analysis_run,
)
from services.v1_analysis_service import run_v1_analysis

router_reports = APIRouter(prefix="/v2/reports", tags=["reports-v2"])


class StakeholderHtmlReportRequest(BaseModel):
    analyze_request: AnalyzeRequest | None = None
    analysis_run_id: int | None = Field(default=None, gt=0)
    output_format: str = Field(default="html", pattern="^(html|pdf)$")

    @model_validator(mode="after")
    def validate_source(self) -> "StakeholderHtmlReportRequest":
        sources = [self.analyze_request is not None, self.analysis_run_id is not None]
        if sum(1 for source in sources if source) != 1:
            raise ValueError(
                "Provide exactly one of analyze_request or analysis_run_id."
            )
        return self


class ProjektiererReportRequest(StakeholderHtmlReportRequest):
    pass


class VnbReportRequest(StakeholderHtmlReportRequest):
    pass


class InvestReportRequest(StakeholderHtmlReportRequest):
    pass


def _report_source_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "REPORT_SOURCE_NOT_FOUND",
            "message": "Analyse-Lauf fuer den Report wurde nicht gefunden.",
            "hint": "Bitte Analyse erneut ausfuehren oder die Reportquelle aktualisieren.",
        },
    )


def _report_stakeholder_forbidden(
    report_type: str, stakeholder_path: str
) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "code": "REPORT_STAKEHOLDER_FORBIDDEN",
            "message": "Projektgebundene Reports duerfen nur ueber den freigegebenen Stakeholder-Pfad exportiert werden.",
            "hint": f"Bitte den {stakeholder_path}-Pfad statt {report_type} verwenden.",
        },
    )


def _assert_project_report_path(report_type: str, stakeholder_path: str | None) -> None:
    if stakeholder_path is None or stakeholder_path == report_type:
        return
    raise _report_stakeholder_forbidden(report_type, stakeholder_path)


def _derive_report_scope(offer_id: str | None, package_scope: str | None) -> str:
    scope = str(package_scope or "").strip().lower()
    if scope in {"basic", "premium", "professional"}:
        return scope
    if str(offer_id or "").strip().lower() == "pro_lizenz":
        return "premium"
    return "professional"


def _validate_sha256_hex(hash_value: str) -> str:
    token = str(hash_value or "").strip().lower()
    if len(token) != 64 or not all(ch in "0123456789abcdef" for ch in token):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "REPORT_REVISION_HASH_INVALID",
                "message": "Ungueltiger Report-Revisions-Hash.",
                "hint": "Bitte den vollen 64-stelligen SHA-256-Hash verwenden.",
            },
        )
    return token


def _report_revision_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "REPORT_REVISION_NOT_FOUND",
            "message": "Die angeforderte Report-Revision wurde nicht gefunden.",
            "hint": "Bitte Hash pruefen oder den Report erneut exportieren.",
        },
    )


def _load_analysis_run_or_404(db: Session, analysis_run_id: int) -> AnalysisRun:
    run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_run_id).first()
    if run is None:
        raise _report_source_not_found()
    return run


def _authorize_analysis_run_access(
    db: Session,
    current_user: User,
    run: AnalysisRun,
    *,
    require_write: bool,
) -> str | None:
    stakeholder_path: str | None = None
    if run.project_id is not None:
        _, _, stakeholder_path = project_service.get_project_access_context(
            db,
            current_user,
            int(run.project_id),
            require_write=require_write,
        )
    elif current_user.role != "admin" and run.user_id != current_user.id:
        raise _report_source_not_found()
    return stakeholder_path


def _load_analysis_run_result(
    db: Session,
    current_user: User,
    analysis_run_id: int,
) -> tuple[dict[str, Any], str | None]:
    run = _load_analysis_run_or_404(db, analysis_run_id)
    stakeholder_path = _authorize_analysis_run_access(
        db,
        current_user,
        run,
        require_write=True,
    )

    if run.status != "completed" or not run.result_json:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_INCOMPLETE",
                "message": "Der ausgewaehlte Analyse-Lauf ist nicht reportfaehig abgeschlossen.",
                "hint": "Bitte zuerst eine erfolgreiche Analyse mit gespeichertem Ergebnis erzeugen.",
            },
        )
    try:
        result = json.loads(run.result_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_INVALID",
                "message": "Der gespeicherte Analyse-Lauf ist nicht lesbar.",
                "hint": "Bitte Analyse erneut ausfuehren und Report danach neu erzeugen.",
            },
        ) from exc
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_INVALID",
                "message": "Der gespeicherte Analyse-Lauf hat ein ungueltiges Format.",
                "hint": "Bitte Analyse erneut ausfuehren und Report danach neu erzeugen.",
            },
        )
    if run.result_checksum and make_checksum(result) != run.result_checksum:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_TAMPERED",
                "message": "Die gespeicherte Analysequelle stimmt nicht mehr mit ihrer revisionssicheren Pruefsumme ueberein.",
                "hint": "Bitte Analyse erneut ausfuehren, bevor ein Report erzeugt wird.",
            },
        )

    revision = result.get("revision")
    if not isinstance(revision, dict):
        revision = {"hash": run.revision_hash}
        result["revision"] = revision
    if run.revision_hash and revision.get("hash") not in {None, run.revision_hash}:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_TAMPERED",
                "message": "Analyse-Lauf und eingebetteter Revisions-Hash widersprechen sich.",
                "hint": "Bitte Analyse erneut ausfuehren, bevor ein Report erzeugt wird.",
            },
        )
    if run.revision_hash and not revision.get("hash"):
        revision["hash"] = run.revision_hash
    if not run.revision_hash:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_UNVERIFIED",
                "message": "Der Analyse-Lauf besitzt keinen belastbaren Revisions-Hash.",
                "hint": "Bitte Analyse erneut ausfuehren und den Report aus dem gespeicherten Lauf erzeugen.",
            },
        )

    revision_record = (
        db.query(RevisionRecord)
        .filter(RevisionRecord.hash == run.revision_hash)
        .first()
    )
    if revision_record is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_UNVERIFIED",
                "message": "Die revisionssichere Analysequelle fuer diesen Report fehlt in PostgreSQL.",
                "hint": "Bitte Analyse erneut ausfuehren und Report danach neu erzeugen.",
            },
        )
    try:
        revision_data = json.loads(revision_record.data_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_INVALID",
                "message": "Die revisionssichere Analysequelle ist nicht lesbar.",
                "hint": "Bitte Analyse erneut ausfuehren und Report danach neu erzeugen.",
            },
        ) from exc
    expected_revision_data = build_revision_data(
        result,
        actor_user_id=revision_record.actor_user_id,
        action_type=revision_record.action_type,
        project_id=revision_record.project_id,
    )
    if revision_data != expected_revision_data:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_TAMPERED",
                "message": "Analyse-Lauf und revisionssichere Detaildaten stimmen nicht mehr ueberein.",
                "hint": "Bitte Analyse erneut ausfuehren, bevor ein Report erzeugt wird.",
            },
        )
    if (
        run.project_id is not None
        and revision_record.project_id is not None
        and revision_record.project_id != run.project_id
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_SOURCE_TAMPERED",
                "message": "Analyse-Lauf und revisionssichere Projektbindung widersprechen sich.",
                "hint": "Bitte Analyse erneut ausfuehren, bevor ein Report erzeugt wird.",
            },
        )

    result["billing_access"] = {
        "offer_id": run.offer_id or "manual",
        "package_scope": run.package_scope or "professional",
        "report_scope": _derive_report_scope(run.offer_id, run.package_scope),
        "usage_bucket": run.usage_bucket or "manual",
        "ops_followup_required": str(run.package_scope or "").strip().lower()
        == "professional",
    }
    result["history"] = {"analysis_run_id": run.id}
    result["_provenance"] = {
        "analysis_run_id": run.id,
        "request_checksum": run.request_checksum,
        "result_checksum": run.result_checksum,
        "revision_hash": run.revision_hash,
        "revision_record_number": revision_record.revisionsnummer,
    }
    return result, stakeholder_path


def _resolve_engine_result(
    req: StakeholderHtmlReportRequest,
    db: Session,
    current_user: User,
    *,
    report_type: str,
) -> tuple[dict[str, Any], str | None]:
    if req.analysis_run_id is not None:
        result, stakeholder_path = _load_analysis_run_result(
            db, current_user, req.analysis_run_id
        )
        _assert_project_report_path(report_type, stakeholder_path)
        return result, stakeholder_path

    assert req.analyze_request is not None
    ensure_analysis_allowed(db, current_user)
    request_payload = req.analyze_request.model_dump(exclude_none=False)
    project_id = request_payload.get("project_id")
    if project_id is not None:
        _, _, stakeholder_path = project_service.get_project_access_context(
            db,
            current_user,
            int(project_id),
            require_write=True,
        )
        _assert_project_report_path(report_type, stakeholder_path)
    access = package_access_context(
        db,
        current_user,
        requested_offer_id=request_payload.get("requested_offer_id"),
    )
    payload = enforce_package_rights(dict(request_payload), access)
    result = run_v1_analysis(payload)
    if result.get("status") == "FEHLER":
        raise HTTPException(status_code=422, detail=result)
    run = persist_completed_analysis_run(
        db,
        current_user,
        request_payload=request_payload,
        result_payload=result,
        source="report_export",
        project_id=int(project_id) if project_id is not None else None,
        access_context=access,
    )
    return _load_analysis_run_result(db, current_user, run.id)


def _gridcheck_project_display_name(engine_result: dict[str, Any]) -> str:
    eingabe = (
        engine_result.get("eingabe")
        if isinstance(engine_result.get("eingabe"), dict)
        else {}
    )
    for key in ("standort", "ort", "plz", "antragsteller"):
        label = str(eingabe.get(key) or "").strip()
        if label:
            return label[:200]
    return "GridCheck-Projekt"


def _gridcheck_project_id_str(
    engine_result: dict[str, Any], provenance: dict[str, Any]
) -> str:
    eingabe = (
        engine_result.get("eingabe")
        if isinstance(engine_result.get("eingabe"), dict)
        else {}
    )
    raw = eingabe.get("project_id")
    if raw is not None and str(raw).strip():
        return str(raw).strip()
    run_id = provenance.get("analysis_run_id")
    if run_id is not None:
        return f"analysis_run:{run_id}"
    return "unknown"


def _resolve_export_format(
    req: StakeholderHtmlReportRequest, format_query: str | None
) -> str:
    if format_query is not None and format_query.strip() != "":
        return format_query.strip().lower()
    return str(req.output_format).strip().lower()


def _report_pdf_quality_failed(issues: list[str]) -> HTTPException:
    preview = "; ".join(issues[:5])
    extra = len(issues) - 5
    hint = preview if extra <= 0 else f"{preview} (+{extra} weitere)"
    return HTTPException(
        status_code=422,
        detail={
            "code": "REPORT_PDF_QUALITY_FAILED",
            "message": (
                "PDF-Export blockiert: Reportdaten erfuellen die Qualitaetspruefung nicht."
            ),
            "hint": hint,
            "issues": issues[:20],
        },
    )


def _pdf_attachment_response(
    pdf_bytes: bytes,
    report_type: str,
    report_revision: dict[str, Any],
    report_data: dict[str, Any],
    report_scope: str | None = None,
) -> Response:
    safe = report_type.replace("/", "-")
    scope_token = (report_scope or "report").replace("/", "-")
    fname = f"gridcheck-{safe}-{scope_token}-{report_revision['uuid']}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{fname}"',
        "X-GridCheck-Report-Revision-Hash": str(report_revision["hash"]),
        "X-GridCheck-Report-Revision-UUID": str(report_revision["uuid"]),
        "X-GridCheck-Report-Verify-Path": str(report_revision.get("verify_path") or ""),
    }
    source_revision_hash = report_data.get("source_revision_hash")
    if source_revision_hash:
        headers["X-GridCheck-Source-Revision-Hash"] = str(source_revision_hash)
    source_verify_path = report_data.get("source_verify_path")
    if source_verify_path:
        headers["X-GridCheck-Source-Verify-Path"] = str(source_verify_path)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )


def _export_stakeholder_report(
    request: Request,
    req: StakeholderHtmlReportRequest,
    format_query: str | None,
    *,
    report_type: str,
    build_report: Callable[[dict[str, Any]], dict[str, Any]],
    render_html: Callable[[dict[str, Any]], str],
    db: Session,
    current_user: User,
) -> dict[str, Any] | Response:
    out_fmt = _resolve_export_format(req, format_query)
    if out_fmt not in ("html", "pdf"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_format",
                "message": "format / output_format must be html or pdf",
            },
        )
    enforce_scoped_rate_limit(
        "reports:export",
        request=request,
        current_user=current_user,
        user_limit=10,
        ip_limit=30,
        window_seconds=300,
        message="Zu viele Report-Exporte",
        hint="Bitte kurz warten und den Report danach erneut erzeugen.",
    )
    result, _ = _resolve_engine_result(req, db, current_user, report_type=report_type)
    report = build_report(result)
    provenance = (
        result.get("_provenance") if isinstance(result.get("_provenance"), dict) else {}
    )
    report["source_analysis_run_id"] = provenance.get("analysis_run_id")
    report["source_request_checksum"] = provenance.get("request_checksum")
    report["source_result_checksum"] = provenance.get("result_checksum")
    report["source_revision_record_number"] = provenance.get("revision_record_number")
    report["source_revision_hash"] = provenance.get("revision_hash") or report.get(
        "engine_revision_hash"
    )
    report["source_verify_path"] = build_source_verify_path(
        report.get("source_revision_hash")
    )

    revision_uuid = str(uuid.uuid4())
    engine_rev = (
        str(report.get("engine_revision_hash") or "").strip()
        or str((result.get("revision") or {}).get("hash") or "").strip()
    )
    gridcheck_report_data = build_gridcheck_report_data_from_engine_result(
        result,
        stakeholder_type=stakeholder_type_for_legacy_report_type(report_type),
        project_id=_gridcheck_project_id_str(result, provenance),
        project_name=_gridcheck_project_display_name(result),
        report_id=revision_uuid,
        audit_id=engine_rev or revision_uuid,
        generated_by="user",
        generated_by_user_id=str(current_user.id),
    )
    report["gridcheck_report_data"] = gridcheck_report_data

    if out_fmt == "pdf":
        gc_data = (
            report.get("gridcheck_report_data")
            if isinstance(report, dict)
            else None
        )
        if not isinstance(gc_data, dict):
            raise _report_pdf_quality_failed(
                ["gridcheck_report_data fehlt oder ist ungueltig"]
            )
        quality_issues = run_pre_pdf_quality_checks(gc_data, report_wrapper=report)
        if quality_issues:
            raise _report_pdf_quality_failed(quality_issues)

    rev = persist_report_revision(
        report,
        render_html,
        report.get("engine_revision_hash"),
        report_type=report_type,
        db=db,
        revision_uuid=revision_uuid,
    )
    final_report = (
        rev.get("report_data") if isinstance(rev.get("report_data"), dict) else report
    )
    final_html = str(rev.get("html") or "")
    gridcheck_embedded = (
        final_report.get("gridcheck_report_data")
        if isinstance(final_report, dict)
        else None
    )
    if out_fmt == "pdf":
        pdf_bytes = build_stakeholder_report_pdf(final_report)
        track_report_exported(
            db,
            current_user,
            report_type=report_type,
            output_format=out_fmt,
            report_revision_uuid=str(rev.get("uuid") or revision_uuid),
            analysis_run_id=report.get("source_analysis_run_id"),
        )
        db.commit()
        return _pdf_attachment_response(
            pdf_bytes,
            report_type,
            rev,
            final_report,
            str(final_report.get("report_scope") or ""),
        )
    track_report_exported(
        db,
        current_user,
        report_type=report_type,
        output_format=out_fmt,
        report_revision_uuid=str(rev.get("uuid") or revision_uuid),
        analysis_run_id=report.get("source_analysis_run_id"),
    )
    db.commit()
    return {
        "status": "OK",
        "report_type": report_type,
        "output_format": "html",
        "html": final_html,
        "report_data": final_report,
        "report_revision": rev,
        "gridcheck_report_data": gridcheck_embedded,
    }


@router_reports.get("/revisions/{hash_value}")
def get_report_revision(
    hash_value: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    normalized_hash = _validate_sha256_hex(hash_value)
    record = (
        db.query(ReportRevisionRecord)
        .filter(ReportRevisionRecord.hash == normalized_hash)
        .first()
    )
    if record is None:
        raise _report_revision_not_found()

    integrity = verify_report_revision_record(record)
    report_data = integrity.get("report_data")
    if not isinstance(report_data, dict):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_REVISION_INVALID",
                "message": "Die gespeicherte Report-Revision ist nicht lesbar.",
                "hint": "Bitte Report erneut erzeugen.",
            },
        )

    source_analysis_run_id = report_data.get("source_analysis_run_id")
    if not isinstance(source_analysis_run_id, int) or source_analysis_run_id <= 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REPORT_REVISION_SOURCE_MISSING",
                "message": "Die Report-Revision enthaelt keinen belastbaren Analyse-Quellbezug.",
                "hint": "Bitte Report aus einem gespeicherten Analyse-Lauf neu erzeugen.",
            },
        )

    source_run = _load_analysis_run_or_404(db, source_analysis_run_id)
    _authorize_analysis_run_access(db, current_user, source_run, require_write=False)

    source_revision_hash = (
        str(
            report_data.get("source_revision_hash") or record.engine_revision_hash or ""
        ).strip()
        or None
    )
    source_revision_record = None
    if source_revision_hash is not None:
        source_revision_record = (
            db.query(RevisionRecord)
            .filter(RevisionRecord.hash == source_revision_hash)
            .first()
        )

    source_checks = {
        "analysis_run_id_matches": source_run.id == source_analysis_run_id,
        "request_checksum_matches": report_data.get("source_request_checksum")
        in {None, source_run.request_checksum},
        "result_checksum_matches": report_data.get("source_result_checksum")
        in {None, source_run.result_checksum},
        "source_revision_hash_matches": source_revision_hash
        in {None, source_run.revision_hash},
        "source_revision_record_exists": source_revision_hash is None
        or source_revision_record is not None,
    }
    source_ok = all(source_checks.values())

    return {
        "status": "OK",
        "report_revision": {
            "revisionsnummer": record.revisionsnummer,
            "uuid": record.uuid,
            "hash": record.hash,
            "timestamp": record.timestamp.isoformat(),
            "report_type": record.report_type,
            "engine_revision_hash": record.engine_revision_hash,
            "verify_path": f"/api/v2/reports/revisions/{record.hash}",
        },
        "integrity": {
            "ok": bool(integrity.get("ok")) and source_ok,
            "report_hash_matches": bool(integrity.get("report_hash_matches")),
            "report_checksum_matches": bool(integrity.get("report_checksum_matches")),
            "html_checksum_matches": bool(integrity.get("html_checksum_matches")),
            "source_checks": source_checks,
        },
        "source": {
            "analysis_run_id": source_run.id,
            "revision_hash": source_revision_hash,
            "verify_path": report_data.get("source_verify_path")
            or build_source_verify_path(source_revision_hash),
            "request_checksum": report_data.get("source_request_checksum"),
            "result_checksum": report_data.get("source_result_checksum"),
            "revision_record_number": report_data.get("source_revision_record_number"),
        },
        "report_data": report_data,
    }


@router_reports.post("/projektierer", response_model=None)
def create_projektierer_report(
    request: Request,
    req: ProjektiererReportRequest,
    fmt: str | None = Query(
        default=None,
        alias="format",
        description="Override body output_format: html | pdf",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, Any] | Response:
    return _export_stakeholder_report(
        request,
        req,
        fmt,
        report_type="projektierer",
        build_report=build_projektierer_report,
        render_html=render_projektierer_html,
        db=db,
        current_user=current_user,
    )


@router_reports.post("/vnb", response_model=None)
def create_vnb_report(
    request: Request,
    req: VnbReportRequest,
    fmt: str | None = Query(
        default=None,
        alias="format",
        description="Override body output_format: html | pdf",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, Any] | Response:
    return _export_stakeholder_report(
        request,
        req,
        fmt,
        report_type="vnb",
        build_report=build_vnb_report,
        render_html=render_vnb_html,
        db=db,
        current_user=current_user,
    )


@router_reports.post("/invest", response_model=None)
def create_invest_report(
    request: Request,
    req: InvestReportRequest,
    fmt: str | None = Query(
        default=None,
        alias="format",
        description="Override body output_format: html | pdf",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, Any] | Response:
    return _export_stakeholder_report(
        request,
        req,
        fmt,
        report_type="invest",
        build_report=build_invest_report,
        render_html=render_invest_html,
        db=db,
        current_user=current_user,
    )
