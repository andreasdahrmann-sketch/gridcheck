# C:\Users\andre\gridcheck\backend\api\routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import json

from db.database import get_db
from db.models import Project, CheckResult, AuditLog, make_checksum
from engine import berechne_netzcheck

router = APIRouter()

# ============================================================
#  SCHEMAS — Single Source of Truth
# ============================================================

class AnalyzeRequest(BaseModel):
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
    skv_mva: Optional[float] = None
    parallelsysteme: int = 1
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
#  HELPERS
# ============================================================

def resolve_cable_key(leitungstyp: str, querschnitt: str) -> str:
    try:
        from constants import CABLE_DATABASE
    except ImportError:
        return f"{leitungstyp} {querschnitt}"
    for candidate in (f"{leitungstyp} {querschnitt}",
                      f"{leitungstyp} {querschnitt}SE",
                      f"NA2XS2Y {querschnitt}"):
        if candidate in CABLE_DATABASE:
            return candidate
    for k in CABLE_DATABASE:
        if leitungstyp.upper() in k.upper():
            return k
    return "NAYY 150"


# ============================================================
#  ENDPOINTS
# ============================================================

@router.post("/api/analyze")
def analyze(req: AnalyzeRequest, db: Session = Depends(get_db)):
    """Hauptendpoint — führt Netzanschluss-Analyse aus."""
    cable_key = resolve_cable_key(req.leitungstyp, req.querschnitt_mm2)
    spannung_kv = float(req.spannungsebene)
    bestehende_kw = (req.vorbelastung_mw or 0) * 1000.0

    result = berechne_netzcheck(
        typ=req.anlagentyp,
        leistung_kw=req.leistung_kw,
        plz=req.plz,
        spannung_kv=spannung_kv,
        skv_mva=req.skv_mva,
        bestehende_einspeisung_kw=bestehende_kw,
        leitungstyp=cable_key,
        leitungslaenge_km=req.leitungslaenge_km,
    )

    project = Project(
        name=req.projektname,
        plz=req.plz,
        typ=req.anlagentyp,
        leistung_kw=req.leistung_kw,
        spannung_kv=spannung_kv,
        einspeiseart=req.einspeiseart,
        skv_mva=req.skv_mva,
        bestehende_einspeisung_kw=bestehende_kw,
        leitungstyp=cable_key,
        leitungslaenge_km=req.leitungslaenge_km,
    )
    db.add(project)
    db.flush()

    check = CheckResult(
        project_id=project.id,
        score=result["score"],
        spannungsband_ok=result["spannungsband_ok"],
        thermische_auslastung_ok=result["thermische_auslastung_ok"],
        kurzschluss_ok=result["kurzschluss_ok"],
        n1_ok=result["n1_ok"],
        netzebene=result["netzebene"],
        empfehlung=result["empfehlung"],
        details=json.dumps(result.get("details", {}), default=str),
    )
    db.add(check)

    audit_payload = {"request": req.dict(), "result": result, "cable_resolved": cable_key}
    audit = AuditLog(
        project_id=project.id,
        action="ANALYSIS_COMPLETED",
        detail=json.dumps(audit_payload, default=str),
        checksum=make_checksum(audit_payload),
    )
    db.add(audit)
    db.commit()

    return {"project_id": project.id, **result}


# Aliase für Rückwärtskompatibilität
@router.post("/api/check")
def check_alias(req: AnalyzeRequest, db: Session = Depends(get_db)):
    return analyze(req, db)

@router.post("/api/calculate")
def calculate_alias(req: AnalyzeRequest, db: Session = Depends(get_db)):
    return analyze(req, db)


@router.get("/api/history")
@router.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).limit(50).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "plz": p.plz,
            "typ": p.typ,
            "leistung_kw": p.leistung_kw,
            "created_at": str(p.created_at),
        }
        for p in projects
    ]


@router.get("/api/result/{project_id}")
def get_result(project_id: int, db: Session = Depends(get_db)):
    check = (
        db.query(CheckResult)
        .filter(CheckResult.project_id == project_id)
        .order_by(CheckResult.id.desc())
        .first()
    )
    if not check:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return {
        "project_id": check.project_id,
        "score": check.score,
        "spannungsband_ok": check.spannungsband_ok,
        "thermische_auslastung_ok": check.thermische_auslastung_ok,
        "kurzschluss_ok": check.kurzschluss_ok,
        "n1_ok": check.n1_ok,
        "netzebene": check.netzebene,
        "empfehlung": check.empfehlung,
        "details": json.loads(check.details) if check.details else {},
    }


@router.get("/api/audit/{project_id}")
def get_audit(project_id: int, db: Session = Depends(get_db)):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.project_id == project_id)
        .order_by(AuditLog.timestamp)
        .all()
    )
    if not logs:
        raise HTTPException(status_code=404, detail="Keine Audit-Logs")
    return [
        {
            "id": l.id,
            "timestamp": str(l.timestamp),
            "action": l.action,
            "detail": l.detail,
            "checksum": l.checksum,
        }
        for l in logs
    ]
