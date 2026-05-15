# C:\Users\andre\gridcheck\backend\api\routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

from core.auth import get_current_user, require_csrf
from core.config import settings
from core.rate_limit import enforce_scoped_rate_limit
from db.database import get_db
from db.models import User
from services.analysis_service import (
    get_audit_logs,
    get_latest_result,
    list_projects_summary,
    run_analysis_and_persist,
)

router = APIRouter()

# ============================================================
#  SCHEMAS — Single Source of Truth
# ============================================================

class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    # --- Step 1: Projektdaten ---
    projektname: str = Field(..., min_length=1)
    plz: str = Field(..., min_length=4, max_length=5)
    anlagentyp: str = "pv"            # pv | wind | bhkw | speicher | last
    leistung_kw: float = Field(..., gt=0)
    spannungsebene: str = "20"        # 0.4 | 20 | 110
    cos_phi: float = 0.95
    einspeiseart: str = "volleinspeisung"
    speicher: bool = False
    speicher_kwh: Optional[float] = None

    # --- Step 2: Netzparameter ---
    trafo_mva: float = 0.63
    leitungslaenge_km: float = 1.0
    leitungstyp: str = "NAYY"
    querschnitt_mm2: str = "150"
    netzverknuepfungspunkt: Optional[str] = ""
    skv_mva: Optional[float] = Field(default=None, alias="sk_mva")
    parallelsysteme: int = Field(default=1, alias="parallele_systeme")
    eigentumsgrenze: str = "HAK"
    vorbelastung_mw: Optional[float] = 0
    netz_typ: str = "kabel"


class AnalyzeResponse(BaseModel):
    project_id: int
    score: float
    spannungsband_ok: bool
    thermische_auslastung_ok: bool
    kurzschluss_ok: bool
    n1_ok: bool
    netzebene: str
    empfehlung: str
    details: dict


# ============================================================
#  ENDPOINTS
# ============================================================


def _run_persist_analysis(req: AnalyzeRequest, db: Session, current_user: User):
    return run_analysis_and_persist(db, req.model_dump(by_alias=False), current_user)

@router.post("/api/v1/analyze/persist")
def analyze(
    request: Request,
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    """Persistente Analyse (legt Projekt/Check-Ergebnis in DB an).

    Stateless Voll-Analyse liegt unter POST /api/v1/analyze (analyze_v2).
    Dieser Pfad bleibt fuer das Legacy-/Projektliste-Frontend mit projektname.
    """
    enforce_scoped_rate_limit(
        "analysis:persist",
        request=request,
        current_user=current_user,
        user_limit=8,
        ip_limit=30,
        window_seconds=300,
        message="Zu viele persistente Analysen",
        hint="Bitte kurz warten, bevor Sie eine weitere Projekt-Analyse speichern.",
    )
    return _run_persist_analysis(req, db, current_user)


# Aliase für Rückwärtskompatibilität
@router.post("/api/v1/check")
def check_alias(
    request: Request,
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    return analyze(request, req, db, current_user)

@router.post("/api/v1/calculate")
def calculate_alias(
    request: Request,
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    return analyze(request, req, db, current_user)


@router.get("/api/v1/history")
def list_projects_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_projects_summary(db, current_user)


@router.get("/api/v1/result/{project_id}")
def get_result(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = get_latest_result(db, current_user, project_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": "Projekt nicht gefunden",
                "hint": "Pruefen Sie die project_id oder listen Sie Projekte ueber /api/v1/projects.",
            },
        )
    return result


@router.get("/api/v1/audit/{project_id}")
def get_audit(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = get_audit_logs(db, current_user, project_id)
    if not logs:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "AUDIT_LOGS_NOT_FOUND",
                "message": "Keine Audit-Logs",
                "hint": "Fuer diese project_id wurden noch keine Audit-Eintraege gespeichert.",
            },
        )
    return logs


if settings.enable_legacy_routes:
    # Legacy aliases (deprecated): keep only when ENABLE_LEGACY_ROUTES=true.
    router.add_api_route("/api/analyze", analyze, methods=["POST"])
    router.add_api_route("/api/check", check_alias, methods=["POST"])
    router.add_api_route("/api/calculate", calculate_alias, methods=["POST"])
    router.add_api_route("/api/history", list_projects_history, methods=["GET"])
    router.add_api_route("/api/projects", list_projects_history, methods=["GET"])
    router.add_api_route("/api/result/{project_id}", get_result, methods=["GET"])
    router.add_api_route("/api/audit/{project_id}", get_audit, methods=["GET"])
