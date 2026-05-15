from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from db.models import AuditLog, CheckResult, Project, ProjectMember, User, make_checksum
from engine.revision import speichere_revision
from engine import berechne_netzcheck
from services.analysis_service import resolve_cable_key


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _build_role_inputs(req_data: dict[str, Any], *, stakeholder_customer_type: str) -> dict[str, Any]:
    return {
        **req_data,
        "kundentyp": stakeholder_customer_type,
        "stakeholder_context": {
            "customer_type": stakeholder_customer_type,
        },
    }


def _persist_project(
    db: Session,
    *,
    actor: User,
    name: str,
    plz: str,
    typ: str,
    leistung_kw: float,
    spannung_kv: float,
    einspeiseart: str,
    skv_mva: float | None,
    bestehende_einspeisung_kw: float,
    leitungstyp: str,
    leitungslaenge_km: float,
    stakeholder_role: str,
    role_inputs: dict[str, Any],
    role_results: dict[str, Any],
) -> Project:
    project = Project(
        name=name,
        plz=plz,
        typ=typ,
        leistung_kw=leistung_kw,
        spannung_kv=spannung_kv,
        einspeiseart=einspeiseart,
        skv_mva=skv_mva,
        bestehende_einspeisung_kw=bestehende_einspeisung_kw,
        leitungstyp=leitungstyp,
        leitungslaenge_km=leitungslaenge_km,
        owner_user_id=actor.id,
        role=stakeholder_role,
        role_inputs=_json_text(role_inputs),
        role_results=_json_text(role_results),
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=actor.id, project_role="owner"))
    return project


def run_endkunde_check(db: Session, req_data: dict[str, Any], actor: User) -> dict[str, Any]:
    spannung_kv = float(req_data["spannungsebene"])
    result = berechne_netzcheck(
        typ=req_data["anlagentyp"],
        leistung_kw=req_data["leistung_kw"],
        plz=req_data["plz"],
        spannung_kv=spannung_kv,
        skv_mva=None,
        bestehende_einspeisung_kw=0.0,
        leitungstyp="NAYY 150",
        leitungslaenge_km=0.5,
    )

    role_inputs = _build_role_inputs(req_data, stakeholder_customer_type="investor")
    project = _persist_project(
        db,
        actor=actor,
        name=f"Endkunde-Anfrage {req_data['plz']}",
        plz=req_data["plz"],
        typ=req_data["anlagentyp"],
        leistung_kw=req_data["leistung_kw"],
        spannung_kv=spannung_kv,
        einspeiseart="volleinspeisung",
        skv_mva=None,
        bestehende_einspeisung_kw=0.0,
        leitungstyp="NAYY 150",
        leitungslaenge_km=0.5,
        stakeholder_role="invest",
        role_inputs=role_inputs,
        role_results=result,
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
        details=json.dumps(result.get("details", {}), default=str),
    )
    db.add(check)

    return {"project_id": project.id, "result": result}


def run_projektierer_check(
    db: Session,
    req_data: dict[str, Any],
    actor: User,
    *,
    stakeholder_customer_type: str = "projektierer",
    stakeholder_role: str = "projektierer",
) -> dict[str, Any]:
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

    role_inputs = _build_role_inputs(req_data, stakeholder_customer_type=stakeholder_customer_type)
    project = _persist_project(
        db,
        actor=actor,
        name=req_data["projektname"],
        plz=req_data["plz"],
        typ=req_data["anlagentyp"],
        leistung_kw=req_data["leistung_kw"],
        spannung_kv=spannung_kv,
        einspeiseart=req_data["einspeiseart"],
        skv_mva=req_data.get("skv_mva"),
        bestehende_einspeisung_kw=bestehende_kw,
        leitungstyp=cable_key,
        leitungslaenge_km=req_data["leitungslaenge_km"],
        stakeholder_role=stakeholder_role,
        role_inputs=role_inputs,
        role_results=result,
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
        details=json.dumps(result.get("details", {}), default=str),
    )
    db.add(check)

    return {"project_id": project.id, "result": result, "cable_key": cable_key}


def persist_stakeholder_audit(
    db: Session,
    *,
    actor: User,
    project_id: int,
    action: str,
    payload: dict[str, Any],
) -> int:
    audit_payload = {
        "action": action,
        "actor_user_id": actor.id,
        "payload": payload,
    }
    audit = AuditLog(
        project_id=project_id,
        action=action,
        detail=json.dumps(audit_payload, default=str),
        checksum=make_checksum(audit_payload),
    )
    db.add(audit)
    db.flush()
    return int(audit.id)


def commit_endkunde_transaction(
    db: Session,
    *,
    actor: User,
    project_id: int,
    req_data: dict[str, Any],
    tendenz: str,
    score: float,
) -> None:
    role_inputs = _build_role_inputs(req_data, stakeholder_customer_type="investor")
    payload = {"request": role_inputs, "tendenz": tendenz, "score": score}
    persist_stakeholder_audit(
        db,
        actor=actor,
        project_id=project_id,
        action="STAKEHOLDER_ENDKUNDE",
        payload=payload,
    )
    speichere_revision(
        {
            "eingabe": role_inputs,
            "fazit": {"entscheidung": tendenz, "status": "STAKEHOLDER_ENDKUNDE"},
            "scores": {"gesamt": score},
            "warnungen": payload.get("warnungen", []),
        },
        actor_user_id=actor.id,
        action_type="STAKEHOLDER_ENDKUNDE",
        project_id=project_id,
        db=db,
    )
    db.commit()


def commit_projektierer_transaction(
    db: Session,
    *,
    actor: User,
    project_id: int,
    req_data: dict[str, Any],
    result: dict[str, Any],
) -> None:
    role_inputs = _build_role_inputs(req_data, stakeholder_customer_type="projektierer")
    payload = {"request": role_inputs, "result": result}
    persist_stakeholder_audit(
        db,
        actor=actor,
        project_id=project_id,
        action="STAKEHOLDER_PROJEKTIERER",
        payload=payload,
    )
    speichere_revision(
        {
            "eingabe": role_inputs,
            "fazit": {"entscheidung": result.get("empfehlung"), "status": "STAKEHOLDER_PROJEKTIERER"},
            "scores": {"gesamt": result.get("score")},
            "warnungen": result.get("warnungen", []),
            "empfehlungen": [result.get("empfehlung")] if result.get("empfehlung") else [],
            "n1": {"n1_sicher": result.get("n1_ok")},
        },
        actor_user_id=actor.id,
        action_type="STAKEHOLDER_PROJEKTIERER",
        project_id=project_id,
        db=db,
    )
    db.commit()


def run_netzbetreiber_check(db: Session, req_data: dict[str, Any], actor: User) -> dict[str, Any]:
    # Historisches Verhalten: Projektname im Datensatz mit Aktenzeichen-NB-Prefix (Audit nutzt weiter req_data unveraendert).
    nb_req = {
        **req_data,
        "projektname": f"[NB:{req_data['aktenzeichen']}] {req_data['projektname']}",
    }
    base = run_projektierer_check(
        db,
        nb_req,
        actor,
        stakeholder_customer_type="netzbetreiber",
        stakeholder_role="netzbetreiber",
    )
    result = base["result"]
    project_id = base["project_id"]

    role_inputs = _build_role_inputs(req_data, stakeholder_customer_type="netzbetreiber")
    audit_payload = {
        "request": role_inputs,
        "result": result,
        "pruefer_id": req_data["pruefer_id"],
        "aktenzeichen": req_data["aktenzeichen"],
    }
    audit_id = persist_stakeholder_audit(
        db,
        actor=actor,
        project_id=project_id,
        action="STAKEHOLDER_NETZBETREIBER",
        payload=audit_payload,
    )
    checksum = make_checksum(audit_payload)
    speichere_revision(
        {
            "eingabe": role_inputs,
            "fazit": {"entscheidung": result.get("empfehlung"), "status": "STAKEHOLDER_NETZBETREIBER"},
            "scores": {"gesamt": result.get("score")},
            "warnungen": result.get("warnungen", []),
            "empfehlungen": [result.get("empfehlung")] if result.get("empfehlung") else [],
            "n1": {"n1_sicher": result.get("n1_ok")},
            "nb_check": {
                "pruefer_id": req_data["pruefer_id"],
                "aktenzeichen": req_data["aktenzeichen"],
            },
        },
        actor_user_id=actor.id,
        action_type="STAKEHOLDER_NETZBETREIBER",
        project_id=project_id,
        db=db,
    )
    db.commit()

    return {
        "project_id": project_id,
        "result": result,
        "audit_id": audit_id,
        "checksum": checksum,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
