from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from api.analyze_v2 import AnalyzeRequest
from engine.stakeholder_reports.invest import build_invest_report
from engine.stakeholder_reports.projektierer import build_projektierer_report
from engine.stakeholder_reports.renderer import (
    persist_report_revision,
    render_invest_html,
    render_projektierer_html,
    render_vnb_html,
)
from engine.stakeholder_reports.vnb import build_vnb_report
from services.v1_analysis_service import run_v1_analysis

router_reports = APIRouter(prefix="/v2/reports", tags=["reports-v2"])


class StakeholderHtmlReportRequest(BaseModel):
    analyze_request: AnalyzeRequest | None = None
    engine_result: dict[str, Any] | None = None
    output_format: str = Field(default="html", pattern="^(html)$")

    @model_validator(mode="after")
    def validate_source(self) -> "StakeholderHtmlReportRequest":
        if self.analyze_request is None and self.engine_result is None:
            raise ValueError("Either analyze_request or engine_result is required.")
        return self


class ProjektiererReportRequest(StakeholderHtmlReportRequest):
    pass


class VnbReportRequest(StakeholderHtmlReportRequest):
    pass


class InvestReportRequest(StakeholderHtmlReportRequest):
    pass


def _resolve_engine_result(req: StakeholderHtmlReportRequest) -> dict[str, Any]:
    if req.engine_result is not None:
        return req.engine_result
    assert req.analyze_request is not None
    result = run_v1_analysis(req.analyze_request.model_dump(exclude_none=False))
    if result.get("status") == "FEHLER":
        raise HTTPException(status_code=422, detail=result)
    return result


@router_reports.post("/projektierer")
def create_projektierer_report(req: ProjektiererReportRequest) -> dict[str, Any]:
    result = _resolve_engine_result(req)
    report = build_projektierer_report(result)
    html = render_projektierer_html(report)
    rev = persist_report_revision(
        report, html, report.get("engine_revision_hash"), report_type="projektierer"
    )
    return {
        "status": "OK",
        "report_type": "projektierer",
        "output_format": "html",
        "html": html,
        "report_data": report,
        "report_revision": rev,
    }


@router_reports.post("/vnb")
def create_vnb_report(req: VnbReportRequest) -> dict[str, Any]:
    result = _resolve_engine_result(req)
    report = build_vnb_report(result)
    html = render_vnb_html(report)
    rev = persist_report_revision(report, html, report.get("engine_revision_hash"), report_type="vnb")
    return {
        "status": "OK",
        "report_type": "vnb",
        "output_format": "html",
        "html": html,
        "report_data": report,
        "report_revision": rev,
    }


@router_reports.post("/invest")
def create_invest_report(req: InvestReportRequest) -> dict[str, Any]:
    result = _resolve_engine_result(req)
    report = build_invest_report(result)
    html = render_invest_html(report)
    rev = persist_report_revision(report, html, report.get("engine_revision_hash"), report_type="invest")
    return {
        "status": "OK",
        "report_type": "invest",
        "output_format": "html",
        "html": html,
        "report_data": report,
        "report_revision": rev,
    }
