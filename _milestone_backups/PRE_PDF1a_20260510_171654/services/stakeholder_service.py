from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from db.models import AuditLog, CheckResult, Project, make_checksum
from engine import berechne_netzcheck
from services.analysis_service import resolve_cable_key


def run_endkunde_check(db: Session, req_data: dict[str, Any]) -> dict[str, Any]:
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

    project = Project(
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

    return {"project_id": project.id, "result": result}


def run_projektierer_check(db: Session, req_data: dict[str, Any]) -> dict[str, Any]:
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
        einspeiseart=req_data["einspeiseart"],
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

    return {"project_id": project.id, "result": result, "cable_key": cable_key}


def persist_stakeholder_audit(
    db: Session,
    *,
    project_id: int,
    action: str,
    payload: dict[str, Any],
) -> int:
    audit = AuditLog(
        project_id=project_id,
        action=action,
        detail=json.dumps(payload, default=str),
        checksum=make_checksum(payload),
    )
    db.add(audit)
    db.flush()
    return int(audit.id)


def commit_endkunde_transaction(
    db: Session,
    *,
    project_id: int,
    req_data: dict[str, Any],
    tendenz: str,
    score: float,
) -> None:
    persist_stakeholder_audit(
        db,
        project_id=project_id,
        action="STAKEHOLDER_ENDKUNDE",
        payload={"request": req_data, "tendenz": tendenz, "score": score},
    )
    db.commit()


def commit_projektierer_transaction(
    db: Session,
    *,
    project_id: int,
    req_data: dict[str, Any],
    result: dict[str, Any],
) -> None:
    persist_stakeholder_audit(
        db,
        project_id=project_id,
        action="STAKEHOLDER_PROJEKTIERER",
        payload={"request": req_data, "result": result},
    )
    db.commit()


def run_netzbetreiber_check(db: Session, req_data: dict[str, Any]) -> dict[str, Any]:
    # Historisches Verhalten: Projektname im Datensatz mit Aktenzeichen-NB-Prefix (Audit nutzt weiter req_data unveraendert).
    nb_req = {
        **req_data,
        "projektname": f"[NB:{req_data['aktenzeichen']}] {req_data['projektname']}",
    }
    base = run_projektierer_check(db, nb_req)
    result = base["result"]
    project_id = base["project_id"]

    audit_payload = {
        "request": req_data,
        "result": result,
        "pruefer_id": req_data["pruefer_id"],
        "aktenzeichen": req_data["aktenzeichen"],
    }
    audit_id = persist_stakeholder_audit(
        db,
        project_id=project_id,
        action="STAKEHOLDER_NETZBETREIBER",
        payload=audit_payload,
    )
    checksum = make_checksum(audit_payload)
    db.commit()

    return {
        "project_id": project_id,
        "result": result,
        "audit_id": audit_id,
        "checksum": checksum,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
