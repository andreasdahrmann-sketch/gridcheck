"""V1-Endpoint fuer Rolle Projektierer."""
from fastapi import APIRouter, HTTPException
from core.errors import AnalysisError
from core.schemas import ProjektiererRequest
from roles.projektierer import analyze_for_projektierer

router = APIRouter(prefix="/api/v1/projektierer", tags=["v1-projektierer"])


@router.post("/analyze")
def analyze(req: ProjektiererRequest):
    try:
        return analyze_for_projektierer(req)
    except AnalysisError as e:
        raise HTTPException(status_code=e.http_status, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": str(e),
                    "hint": None, "details": []},
        )