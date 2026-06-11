from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from typing import Any, Literal

from sqlalchemy.orm import Session

from db.models import Project, ProjectMember, User

ProjectAccessLevel = Literal["admin", "owner", "editor", "viewer", "none"]
StakeholderPath = Literal["projektierer", "vnb", "invest"]
FieldSpec = dict[str, "FieldSpec | bool"]


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _copy_json_value(value: Any) -> Any:
    return copy.deepcopy(value)


def derive_stakeholder_path(
    source: Mapping[str, Any] | None,
    *,
    fallback_user_role: str | None = None,
) -> StakeholderPath:
    payload = dict(source or {})
    stakeholder_context = _as_dict(payload.get("stakeholder_context"))
    raw = str(payload.get("kundentyp") or stakeholder_context.get("customer_type") or "").strip().lower()
    if raw == "netzbetreiber" or str(fallback_user_role or "").strip().lower() == "netzbetreiber":
        return "vnb"
    if raw == "investor":
        return "invest"
    return "projektierer"


def get_project_access_level(db: Session, user: User, project: Project) -> ProjectAccessLevel:
    if user.role == "admin":
        return "admin"
    if project.owner_user_id == user.id:
        return "owner"
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
    )
    if membership is None:
        return "none"
    role = str(membership.project_role or "viewer").strip().lower()
    if role in {"owner", "editor", "viewer"}:
        return role  # type: ignore[return-value]
    return "viewer"


def can_view_project_audit(access_level: ProjectAccessLevel) -> bool:
    return access_level in {"admin", "owner", "editor"}


def can_write_project(access_level: ProjectAccessLevel) -> bool:
    return access_level in {"admin", "owner", "editor"}


def parse_project_role_inputs(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        payload = json.loads(raw_value)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_project_stakeholder_path(
    project: Project,
    *,
    fallback_user_role: str | None = None,
) -> StakeholderPath:
    return derive_stakeholder_path(
        parse_project_role_inputs(project.role_inputs),
        fallback_user_role=fallback_user_role,
    )


def sanitize_project_inputs(
    role_inputs: Mapping[str, Any] | None,
    *,
    access_level: ProjectAccessLevel,
) -> dict[str, Any]:
    sanitized = _copy_json_value(dict(role_inputs or {}))
    if access_level in {"admin", "owner", "editor"}:
        return sanitized

    sanitized.pop("antragsteller", None)
    sanitized.pop("project_location", None)
    sanitized.pop("umspannwerk", None)

    netzanschlusspunkt = _as_dict(sanitized.get("netzanschlusspunkt"))
    if netzanschlusspunkt:
        netzanschlusspunkt.pop("preferred_connection_note", None)
        sanitized["netzanschlusspunkt"] = netzanschlusspunkt

    storage_profile = _as_dict(sanitized.get("storage_profile"))
    if storage_profile:
        storage_profile.pop("notes", None)
        sanitized["storage_profile"] = storage_profile

    environmental_route = _as_dict(sanitized.get("environmental_route"))
    if environmental_route:
        environmental_route.pop("notes", None)
        sanitized["environmental_route"] = environmental_route

    return sanitized


def _merge_specs(*specs: FieldSpec) -> FieldSpec:
    merged: FieldSpec = {}
    for spec in specs:
        for key, value in spec.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = _merge_specs(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
    return merged


def _pick_fields(value: Any, spec: FieldSpec) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    picked: dict[str, Any] = {}
    for key, nested in spec.items():
        if key not in value:
            continue
        current = value[key]
        if nested is True:
            picked[key] = _copy_json_value(current)
            continue
        if isinstance(current, dict):
            picked[key] = _pick_fields(current, nested)
            continue
        if isinstance(current, list):
            items: list[Any] = []
            for item in current:
                if isinstance(item, dict):
                    items.append(_pick_fields(item, nested))
                else:
                    items.append(_copy_json_value(item))
            picked[key] = items
            continue
        picked[key] = _copy_json_value(current)
    return picked


_KI_SPEC: FieldSpec = {
    "konfidenz_prozent": True,
    "aehnliche_faelle": True,
    "hinweise": True,
    "kalibrierung": {
        "samples": True,
        "trefferquote": True,
        "durchschnittlicher_fehler": True,
        "bias": True,
        "kalibrierungsfaktor": True,
        "bestaetigungsquote": True,
        "status": True,
    },
    "feedback_loop": {
        "samples_total": True,
        "linked_samples": True,
        "bestaetigt": True,
        "korrigiert": True,
        "bestaetigungsquote": True,
        "coverage_ratio": True,
        "anomaly_feedbacks": True,
        "status": True,
        "last_feedback_at": True,
    },
    "anomalie_check": {
        "is_anomaly": True,
        "severity": True,
        "score": True,
        "summary": True,
        "flags": True,
    },
}

_N1_SUMMARY_SPEC: FieldSpec = {
    "n1_sicher": True,
    "bewertung": True,
    "topologie": True,
    "topologie_text": True,
    "leitung_n1": True,
    "leitung_text": True,
    "n1_auslastung_prozent": True,
    "trafo_n1": True,
    "detail_text": True,
    "n1_klasse": True,
    "n1_konfidenz": True,
    "engpass_komponente": True,
    "stufenbegruendung": True,
    "nachweise_vorhanden": True,
    "nachweise_fehlend": True,
    "dso_daten_vorhanden": True,
    "detail_empfehlungen": True,
}

_COMMON_RESULT_SPEC: FieldSpec = {
    "status": True,
    "score": True,
    "scores": True,
    "machbarkeit_stufe": True,
    "spannungsbewertung": True,
    "n1_hinweis": True,
    "warnungen": True,
    "empfehlungen": True,
    "fazit": True,
    "netzebene": True,
    "daten_confidence": True,
    "datenqualitaet": True,
    "projektprofil": {
        "total_installed_kw": True,
        "component_count": True,
        "is_hybrid": True,
        "component_summary": True,
        "max_export_kw": True,
        "max_import_kw": True,
        "summary": True,
    },
    "speicher_bewertung": {
        "relevant": True,
        "operation_mode": True,
        "flexibility_score": True,
        "grid_support_score": True,
        "benefit_flags": True,
        "warnings": True,
        "summary": True,
        "disclaimer": True,
    },
    "route_environment": {
        "risk_score": True,
        "risk_level": True,
        "drivers": True,
        "mitigation": True,
        "summary": True,
    },
    "stakeholder_bewertung": {
        "netzbetreiber_score": True,
        "projektierer_score": True,
        "umsetzung_score": True,
        "konflikt_level": True,
        "konflikt_summary": True,
        "recommended_focus": True,
    },
    "transparenz": {
        "assumptions": True,
        "disclaimers": True,
        "confidence_notes": True,
        "eingabe_quellen": True,
    },
    "billing_access": True,
    "billing": True,
    "history": True,
    "revision": {"hash": True},
    "ki": _KI_SPEC,
    "n1": _N1_SUMMARY_SPEC,
    "n1_prescreen_ok": True,
    "n1_prescreen_detail": True,
    "technical_details": {
        "spannungsfall": True,
        "kurzschluss": True,
        "leitung": True,
        "trasse": True,
    },
    "power_limit_hints": True,
}

_GRID_V2_RESULT_SPEC: FieldSpec = {
    "grid_calculation_v2": True,
}

_COST_RESULT_SPEC: FieldSpec = {
    "kosten": True,
    "kosten_indikation": True,
    "kosten_indikation_eur": True,
    "kostenklasse": True,
    "kosten_bandbreite": True,
    "cost_band": True,
}

_TECHNICAL_RESULT_SPEC: FieldSpec = {
    "kurzschluss": {
        "ik_min_kA": True,
        "ik_max_kA": True,
        "sk_am_nvp_mva": True,
        "bewertung": True,
    },
    "blindleistung": {
        "q_bedarf_kvar": True,
        "q_reserve_kvar": True,
        "kompensation_empfohlen": True,
        "empfehlung": True,
    },
    "netzrueckwirkung": {
        "leistungsverhaeltnis": True,
        "flickerrisiko": True,
        "oberschwingungsrisiko": True,
        "bewertung": True,
    },
    "n1_analyse": {
        "n1_topologie": True,
        "n1_leitung": True,
        "n1_abgang": True,
        "n1_trafo": True,
        "n1_spannung": True,
        "gesamt": True,
        "annahmen": True,
        "berechnungs_version": True,
        "backend": True,
    },
}

_PROJECT_RESULT_SPEC = _merge_specs(
    _COMMON_RESULT_SPEC, _COST_RESULT_SPEC, _TECHNICAL_RESULT_SPEC, _GRID_V2_RESULT_SPEC
)
_VNB_RESULT_SPEC = _merge_specs(
    _COMMON_RESULT_SPEC, _TECHNICAL_RESULT_SPEC, _GRID_V2_RESULT_SPEC
)
_INVEST_RESULT_SPEC = _merge_specs(_COMMON_RESULT_SPEC, _COST_RESULT_SPEC)


def sanitize_analysis_result(
    result: Mapping[str, Any] | None,
    *,
    stakeholder_path: StakeholderPath,
) -> dict[str, Any]:
    payload = dict(result or {})
    if stakeholder_path == "invest":
        return _pick_fields(payload, _INVEST_RESULT_SPEC)
    if stakeholder_path == "vnb":
        return _pick_fields(payload, _VNB_RESULT_SPEC)
    return _pick_fields(payload, _PROJECT_RESULT_SPEC)


def sanitize_project_result(
    role_results: Mapping[str, Any] | None,
    *,
    stakeholder_path: StakeholderPath,
    access_level: ProjectAccessLevel,
) -> dict[str, Any]:
    sanitized = sanitize_analysis_result(role_results, stakeholder_path=stakeholder_path)
    if access_level != "viewer":
        return sanitized
    sanitized.pop("history", None)
    return sanitized


def sanitize_audit_detail(
    detail: str | None,
    *,
    stakeholder_path: StakeholderPath,
    access_level: ProjectAccessLevel,
) -> str | None:
    if not detail:
        return detail
    try:
        parsed = json.loads(detail)
    except Exception:
        return detail
    if not isinstance(parsed, dict):
        return detail

    payload = _as_dict(parsed.get("payload"))
    if payload:
        if "role_inputs" in payload:
            payload["role_inputs"] = sanitize_project_inputs(payload.get("role_inputs"), access_level=access_level)
        if "role_results" in payload:
            payload["role_results"] = sanitize_project_result(
                payload.get("role_results"),
                stakeholder_path=stakeholder_path,
                access_level=access_level,
            )
        if "request" in payload:
            payload["request"] = sanitize_project_inputs(payload.get("request"), access_level=access_level)
        if "result" in payload:
            payload["result"] = sanitize_analysis_result(
                payload.get("result"),
                stakeholder_path=stakeholder_path,
            )
        if "details" in payload and isinstance(payload["details"], dict):
            payload["details"] = sanitize_analysis_result(
                payload["details"],
                stakeholder_path=stakeholder_path,
            )
        parsed["payload"] = payload
    return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
