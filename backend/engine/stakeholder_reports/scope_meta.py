from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_VALID_SCOPES = {"basic", "premium", "professional"}

_SCOPE_LABELS = {
    "basic": "Basic Kernreport",
    "premium": "Premium Vertiefung",
    "professional": "Professional Anschlussstrategie",
}

_SCOPE_SUMMARIES = {
    "basic": "Kompakter Kernreport mit Screening, N-1-Hinweis, Auflagen und Empfehlungen.",
    "premium": "Vertiefter Stakeholder-Report mit Strategie-, Transparenz- und themenspezifischen Zusatzabschnitten.",
    "professional": "Voller Professional-Report mit operativem Follow-up-Pfad und sichtbar erweitertem Deliverable-Scope.",
}

_BOUNDARY_NOTES = {
    "basic": "Vertiefte Strategie-, Transparenz- und stakeholder-spezifische Zusatzabschnitte werden erst ab Premium freigeschaltet.",
    "premium": "Premium enthaelt die fachliche Vertiefung, aber noch keinen operativen Professional-Follow-up-Pfad.",
    "professional": "Professional markiert den Run fuer operative Anschlussstrategie, erweiterten Scope und abgestimmten Nachlauf.",
}


@dataclass(frozen=True)
class ReportScopeMeta:
    offer_id: str | None
    package_scope: str
    package_scope_label: str
    report_scope: str
    report_scope_label: str
    scope_summary: str
    scope_boundary_note: str
    includes_strategy_section: bool
    includes_transparency_section: bool
    includes_visualization_note: bool
    includes_cost_section: bool
    ops_followup_required: bool


def _normalize_scope(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in _VALID_SCOPES:
        return candidate
    return fallback


def resolve_report_scope_meta(engine_result: dict[str, Any]) -> ReportScopeMeta:
    billing_access = engine_result.get("billing_access", {})
    engine_package_scope = engine_result.get("package_scope")
    engine_report_scope = engine_result.get("report_scope")

    package_scope = _normalize_scope(
        billing_access.get("package_scope") or engine_package_scope or engine_report_scope,
        "professional",
    )
    report_scope = _normalize_scope(
        billing_access.get("report_scope") or engine_report_scope or package_scope,
        package_scope,
    )
    offer_id = str(billing_access.get("offer_id") or engine_result.get("requested_offer_id") or "").strip() or None

    return ReportScopeMeta(
        offer_id=offer_id,
        package_scope=package_scope,
        package_scope_label=_SCOPE_LABELS[package_scope],
        report_scope=report_scope,
        report_scope_label=_SCOPE_LABELS[report_scope],
        scope_summary=_SCOPE_SUMMARIES[report_scope],
        scope_boundary_note=_BOUNDARY_NOTES[report_scope],
        includes_strategy_section=report_scope in {"premium", "professional"},
        includes_transparency_section=report_scope in {"premium", "professional"},
        includes_visualization_note=report_scope == "professional",
        includes_cost_section=report_scope in {"premium", "professional"},
        ops_followup_required=bool(billing_access.get("ops_followup_required")) or report_scope == "professional",
    )
