"""V1-Endpoint fuer Rolle Projektierer.

DEPRECATED (Phase 2): Use /api/v2/reports/projektierer for new report flow.
This endpoint remains to avoid breaking existing integrations.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from core.errors import AnalysisError
from core.rate_limit import enforce_scoped_rate_limit
from core.schemas import ProjektiererRequest
from roles.projektierer import analyze_for_projektierer

router = APIRouter(prefix="/api/v1/projektierer", tags=["v1-projektierer"])


@router.post("/analyze")
def analyze(request: Request, req: ProjektiererRequest) -> dict:
    """Analyse fuer Rolle Projektierer (Engine + Constraints + Wirtschaftlichkeit)."""
    enforce_scoped_rate_limit(
        "analysis:projektierer-public",
        request=request,
        ip_limit=6,
        window_seconds=300,
        message="Zu viele oeffentliche Projektierer-Analysen",
        hint="Bitte kurz warten, bevor Sie eine weitere Projektierer-Analyse starten.",
    )
    try:
        return analyze_for_projektierer(req)
    except AnalysisError as e:
        raise HTTPException(status_code=e.http_status, detail=e.to_dict())
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": str(e), "hint": None},
        )