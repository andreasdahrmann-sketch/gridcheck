from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Project, CheckResult, AuditLog, make_checksum
from engine import berechne_netzcheck
from pydantic import BaseModel
from typing import Optional
import json

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    plz: str
    ort: Optional[str] = None
    typ: str
    leistung_kw: float
    spannung_kv: Optional[float] = None
    einspeiseart: Optional[str] = "Volleinspeisung"
    skv_mva: Optional[float] = None
    bestehende_einspeisung_kw: Optional[float] = 0
    leitungstyp: Optional[str] = "NAYY 150"
    leitungslaenge_km: Optional[float] = 1.0


@router.post("/api/check")
def run_check(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**data.dict())
    db.add(project)
    db.commit()
    db.refresh(project)

    result = berechne_netzcheck(
        typ=data.typ,
        leistung_kw=data.leistung_kw,
        plz=data.plz,
        spannung_kv=data.spannung_kv,
        skv_mva=data.skv_mva,
        bestehende_einspeisung_kw=data.bestehende_einspeisung_kw,
        leitungstyp=data.leitungstyp,
        leitungslaenge_km=data.leitungslaenge_km,
    )

    check = CheckResult(
        project_id=project.id,
        score=result["score"],
        spannungsband_ok=result["spannungsband_ok"],
        thermische_auslastung_ok=result["thermische_auslastung_ok"],
        kurzschluss_ok=result["kurzschluss_ok"],
        n1_ok=result["n1_ok"],
        netzebene=result["netzebene"],
        empfehlung=result["empfehlung"],
        details=json.dumps(result["details"], default=str),
    )
    db.add(check)
    db.commit()

    audit = AuditLog(
        project_id=project.id,
        action="CHECK_CREATED",
        detail=json.dumps(result, default=str),
        checksum=make_checksum(result),
    )
    db.add(audit)
    db.commit()

    return {"project_id": project.id, **result}


@router.get("/api/result/{project_id}")
def get_result(project_id: int, db: Session = Depends(get_db)):
    check = db.query(CheckResult).filter(CheckResult.project_id == project_id).first()
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
    logs = db.query(AuditLog).filter(AuditLog.project_id == project_id).all()
    if not logs:
        raise HTTPException(status_code=404, detail="Keine Audit-Logs gefunden")
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


@router.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "plz": p.plz,
            "ort": p.ort,
            "typ": p.typ,
            "leistung_kw": p.leistung_kw,
            "created_at": str(p.created_at),
        }
        for p in projects
    ]
