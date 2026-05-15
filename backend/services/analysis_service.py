from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import AuditLog, CheckResult, Project, ProjectMember, User, make_checksum
from engine import berechne_netzcheck
from services.billing_service import (
    enforce_package_rights,
    ensure_analysis_allowed,
    package_access_context,
    persist_completed_analysis_run,
)
from services.visibility_service import (
    can_view_project_audit,
    derive_stakeholder_path,
    get_project_access_level,
    sanitize_analysis_result,
    sanitize_audit_detail,
)


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


def run_analysis_and_persist(db: Session, req_data: dict[str, Any], user: User) -> dict[str, Any]:
    ensure_analysis_allowed(db, user)
    access_context = package_access_context(
        db,
        user,
        requested_offer_id=str(req_data.get("requested_offer_id")) if req_data.get("requested_offer_id") else None,
    )
    req_data = enforce_package_rights(req_data, access_context)
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
        owner_user_id=user.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, project_role="owner"))

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
    persist_completed_analysis_run(
        db,
        user,
        request_payload=req_data,
        result_payload=result,
        source="legacy_persist",
        project_id=project.id,
        access_context=access_context,
    )

    return {"project_id": project.id, **result}


def list_projects_summary(db: Session, user: User) -> list[dict[str, Any]]:
    projects = (
        db.query(Project)
        .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(
            Project.deleted_at.is_(None),
            (Project.owner_user_id == user.id) | (ProjectMember.user_id == user.id),
        )
        .distinct(Project.id)
        .order_by(Project.id, Project.created_at.desc())
        .limit(50)
        .all()
    )
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


def _get_accessible_project(db: Session, user: User, project_id: int) -> Project | None:
    from services import project_service

    try:
        return project_service.get_project(db, user, project_id)
    except Exception:
        return None


def _parse_project_role_inputs(project: Project) -> dict[str, Any]:
    if not project.role_inputs:
        return {}
    try:
        payload = json.loads(project.role_inputs)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_check_details(check: CheckResult) -> dict[str, Any]:
    if not check.details:
        return {}
    try:
        payload = json.loads(check.details)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def get_latest_result(db: Session, user: User, project_id: int) -> Optional[dict[str, Any]]:
    project = _get_accessible_project(db, user, project_id)
    if not project:
        return None
    check = (
        db.query(CheckResult)
        .filter(CheckResult.project_id == project_id)
        .order_by(CheckResult.id.desc())
        .first()
    )
    if not check:
        return None
    access_level = get_project_access_level(db, user, project)
    stakeholder_path = derive_stakeholder_path(
        _parse_project_role_inputs(project),
        fallback_user_role=user.role,
    )
    return {
        "project_id": check.project_id,
        "score": check.score,
        "spannungsband_ok": check.spannungsband_ok,
        "thermische_auslastung_ok": check.thermische_auslastung_ok,
        "kurzschluss_ok": check.kurzschluss_ok,
        "n1_ok": check.n1_ok,
        "netzebene": check.netzebene,
        "empfehlung": check.empfehlung,
        "details": sanitize_analysis_result(
            _parse_check_details(check),
            stakeholder_path=stakeholder_path,
        ),
        "visibility_scope": stakeholder_path,
        "viewer_access_level": access_level,
    }


def get_audit_logs(db: Session, user: User, project_id: int) -> list[dict[str, Any]]:
    project = _get_accessible_project(db, user, project_id)
    if not project:
        return []
    access_level = get_project_access_level(db, user, project)
    if not can_view_project_audit(access_level):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AUDIT_FORBIDDEN",
                "message": "Audit-Trail ist nur fuer interne Bearbeiter oder Projektverantwortliche sichtbar.",
                "hint": "Bitte mit Owner-, Editor- oder Admin-Rechten erneut versuchen.",
            },
        )
    stakeholder_path = derive_stakeholder_path(
        _parse_project_role_inputs(project),
        fallback_user_role=user.role,
    )
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
            "detail": sanitize_audit_detail(
                l.detail,
                stakeholder_path=stakeholder_path,
                access_level=access_level,
            ),
            "checksum": l.checksum,
        }
        for l in logs
    ]
