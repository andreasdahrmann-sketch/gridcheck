from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from db.models import AuditLog, CheckResult, Project, make_checksum
from engine import berechne_netzcheck


def resolve_cable_key(leitungstyp: str, querschnitt: str) -> str:
    try:
        from constants import CABLE_DATABASE
    except ImportError:
        return f"{leitungstyp} {querschnitt}"
    for candidate in (
        f"{leitungstyp} {querschnitt}",
        f"{leitungstyp} {querschnitt}SE",
        f"NA2XS2Y {querschnitt}",
    ):
        if candidate in CABLE_DATABASE:
            return candidate
    for key in CABLE_DATABASE:
        if leitungstyp.upper() in key.upper():
            return key
    return "NAYY 150"


def run_analysis_and_persist(db: Session, req_data: dict[str, Any]) -> dict[str, Any]:
    cable_key = resolve_cable_key(req_data["leitungstyp"], req_data["querschnitt_mm2"])
    spannung_kv = float(req_data["spannungsebene"])
    bestehende_kw = (req_data.get("vorbelastung_mw") or 0) * 1000.0

    result = berechne_netzcheck(
        typ=req_data["anlagentyp"],
        leistung_kw=req_data["leistung_kw"],
        plz=req_data["plz"],
        spannung_kv=spannung_kv,
        skv_mva=req_data.get("skv_mva"),
        bestehende_einspeisung_kw=bestehende_kw,
        leitungstyp=cable_key,
        leitungslaenge_km=req_data["leitungslaenge_km"],
    )

    project = Project(
        name=req_data["projektname"],
        plz=req_data["plz"],
        typ=req_data["anlagentyp"],
        leistung_kw=req_data["leistung_kw"],
        spannung_kv=spannung_kv,
        einspeiseart=req_data.get("einspeiseart", "volleinspeisung"),
        skv_mva=req_data.get("skv_mva"),
        bestehende_einspeisung_kw=bestehende_kw,
        leitungstyp=cable_key,
        leitungslaenge_km=req_data["leitungslaenge_km"],
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

    audit_payload = {"request": req_data, "result": result, "cable_resolved": cable_key}
    audit = AuditLog(
        project_id=project.id,
        action="ANALYSIS_COMPLETED",
        detail=json.dumps(audit_payload, default=str),
        checksum=make_checksum(audit_payload),
    )
    db.add(audit)
    db.commit()

    return {"project_id": project.id, **result}


def list_projects_summary(db: Session) -> list[dict[str, Any]]:
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


def get_latest_result(db: Session, project_id: int) -> Optional[dict[str, Any]]:
    check = (
        db.query(CheckResult)
        .filter(CheckResult.project_id == project_id)
        .order_by(CheckResult.id.desc())
        .first()
    )
    if not check:
        return None
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


def get_audit_logs(db: Session, project_id: int) -> list[dict[str, Any]]:
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.project_id == project_id)
        .order_by(AuditLog.timestamp)
        .all()
    )
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
