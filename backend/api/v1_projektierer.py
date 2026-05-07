"""V1-Endpoint fuer Rolle Projektierer."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.errors import AnalysisError
from core.schemas import ProjektiererRequest
from roles.projektierer import analyze_for_projektierer

router = APIRouter(prefix="/api/v1/projektierer", tags=["v1-projektierer"])


@router.post("/analyze")
def analyze(req: ProjektiererRequest) -> dict:
    """Analyse fuer Rolle Projektierer (Engine + Constraints + Wirtschaftlichkeit)."""
    try:
        return analyze_for_projektierer(req)
    except AnalysisError as e:
        raise HTTPException(status_code=e.http_status, detail=e.to_dict())
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": str(e), "hint": None},
        )