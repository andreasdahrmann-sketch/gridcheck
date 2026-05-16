"""
Pre-PDF quality checks for canonical GridcheckReportData (mirrors frontend/lib/reports).
"""

from __future__ import annotations

import re
from typing import Any

_STAKEHOLDER_TYPES = frozenset({"project_developer", "grid_operator", "investor"})
_GENERATING_TECH = frozenset({"pv", "wind", "battery", "hybrid"})

_BINDING_LANGUAGE: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bkapazitätsgarant", re.IGNORECASE),
    re.compile(r"\bnetzanschluss\s*zusage\b", re.IGNORECASE),
    re.compile(r"\bgarantiert\s+anschlussfähig", re.IGNORECASE),
)


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return bool(value == value)  # NaN check
    return False


def _has_feed_or_consumption(project: dict[str, Any]) -> bool:
    feed = project.get("feedInCapacityMw")
    cons = project.get("consumptionCapacityMw")
    return _finite_number(feed) or _finite_number(cons)


def validate_report_for_finalization(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Hard mandatory fields before report finalization (Spec section 4)."""
    errors: list[str] = []
    report = data.get("report") if isinstance(data.get("report"), dict) else {}
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    location = data.get("location") if isinstance(data.get("location"), dict) else {}
    grid = data.get("grid") if isinstance(data.get("grid"), dict) else {}
    risks = data.get("risks") if isinstance(data.get("risks"), dict) else {}
    cost = data.get("cost") if isinstance(data.get("cost"), dict) else {}
    assessment = data.get("assessment") if isinstance(data.get("assessment"), dict) else {}
    sources = data.get("sources") if isinstance(data.get("sources"), list) else []
    audit = data.get("audit") if isinstance(data.get("audit"), dict) else {}

    if not _non_empty_str(report.get("reportId")):
        errors.append("report.reportId fehlt")
    if not _non_empty_str(report.get("auditId")):
        errors.append("report.auditId fehlt")
    if not _non_empty_str(report.get("reportVersion")):
        errors.append("report.reportVersion fehlt")
    if not _non_empty_str(report.get("modelVersion")):
        errors.append("report.modelVersion fehlt")
    if not _non_empty_str(report.get("scoringVersion")):
        errors.append("report.scoringVersion fehlt")
    if not _non_empty_str(report.get("createdAt")):
        errors.append("report.createdAt fehlt")
    stakeholder = report.get("stakeholderType")
    if stakeholder not in _STAKEHOLDER_TYPES:
        errors.append("report.stakeholderType ungültig")

    if not _non_empty_str(project.get("projectId")):
        errors.append("project.projectId fehlt")
    if not _non_empty_str(project.get("projectName")):
        errors.append("project.projectName fehlt")
    if not project.get("technology"):
        errors.append("project.technology fehlt")
    if not project.get("operationMode"):
        errors.append("project.operationMode fehlt")

    if not _finite_number(location.get("latitude")):
        errors.append("location.latitude ungültig")
    if not _finite_number(location.get("longitude")):
        errors.append("location.longitude ungültig")

    if not grid.get("recommendedVoltageLevel"):
        errors.append("grid.recommendedVoltageLevel fehlt")
    candidates = grid.get("candidateConnectionPoints")
    if not isinstance(candidates, list):
        errors.append("grid.candidateConnectionPoints fehlt")
    if not grid.get("n1Screening"):
        errors.append("grid.n1Screening fehlt")

    for key in (
        "overallRisk",
        "gridConnectionRisk",
        "costRisk",
        "timelineRisk",
        "dataQualityRisk",
    ):
        if not risks.get(key):
            errors.append(f"risks.{key} fehlt")

    if not assessment.get("recommendation"):
        errors.append("assessment.recommendation fehlt")
    if not _non_empty_str(assessment.get("summary")):
        errors.append("assessment.summary fehlt")
    if not isinstance(assessment.get("assumptions"), list):
        errors.append("assessment.assumptions fehlt")
    if not isinstance(assessment.get("warnings"), list):
        errors.append("assessment.warnings fehlt")
    if not isinstance(assessment.get("nextSteps"), list):
        errors.append("assessment.nextSteps fehlt")

    if not sources:
        errors.append("sources: mindestens eine Quelle erforderlich")
    if not _non_empty_str(audit.get("inputHash")):
        errors.append("audit.inputHash fehlt")
    if not _non_empty_str(audit.get("resultHash")):
        errors.append("audit.resultHash fehlt")
    if not isinstance(audit.get("immutable"), bool):
        errors.append("audit.immutable muss boolean sein")

    n1 = grid.get("n1Screening") if isinstance(grid.get("n1Screening"), dict) else {}

    if stakeholder == "project_developer":
        if not _has_feed_or_consumption(project):
            errors.append(
                "project_developer: project.feedInCapacityMw oder "
                "project.consumptionCapacityMw erforderlich"
            )
        if not all(
            _finite_number(cost.get(k)) for k in ("lowEstimate", "baseEstimate", "highEstimate")
        ):
            errors.append(
                "project_developer: cost.lowEstimate/baseEstimate/highEstimate erforderlich"
            )
        drivers = cost.get("mainCostDrivers")
        if not isinstance(drivers, list) or not drivers:
            errors.append("project_developer: cost.mainCostDrivers mindestens ein Eintrag")
        if isinstance(candidates, list) and len(candidates) < 1:
            errors.append("project_developer: mindestens ein Anschlusskandidat")
        next_steps = assessment.get("nextSteps")
        if not isinstance(next_steps, list) or len(next_steps) < 3:
            errors.append("project_developer: assessment.nextSteps mindestens drei Einträge")

    if stakeholder == "grid_operator":
        if not _has_feed_or_consumption(project):
            errors.append(
                "grid_operator: project.feedInCapacityMw oder "
                "project.consumptionCapacityMw erforderlich"
            )
        limitations = n1.get("limitations")
        if not isinstance(limitations, list) or not limitations:
            errors.append("grid_operator: grid.n1Screening.limitations mindestens ein Eintrag")
        follow = n1.get("requiredFollowUp")
        if not isinstance(follow, list) or not follow:
            errors.append(
                "grid_operator: grid.n1Screening.requiredFollowUp mindestens ein Eintrag"
            )
        if not audit.get("generatedBy"):
            errors.append("grid_operator: audit.generatedBy erforderlich")
        for src in sources:
            if not isinstance(src, dict):
                errors.append("grid_operator: jede Quelle braucht retrievedAt (Datenstand)")
                break
            if not _non_empty_str(src.get("retrievedAt")):
                errors.append("grid_operator: jede Quelle braucht retrievedAt (Datenstand)")
                break

    if stakeholder == "investor":
        if not all(
            _finite_number(cost.get(k)) for k in ("lowEstimate", "baseEstimate", "highEstimate")
        ):
            errors.append("investor: cost.lowEstimate/baseEstimate/highEstimate erforderlich")
        items = cost.get("costItems")
        if not isinstance(items, list) or not items:
            errors.append("investor: cost.costItems mindestens eine Position")
        key_findings = assessment.get("keyFindings")
        if not isinstance(key_findings, list) or not any(
            _non_empty_str(x) for x in key_findings
        ):
            errors.append("investor: assessment.keyFindings mindestens ein nicht-leerer Eintrag")
        tech = project.get("technology")
        if tech in _GENERATING_TECH and risks.get("curtailmentRisk") is None:
            errors.append("investor: risks.curtailmentRisk bei Erzeugungsanlage erforderlich")

    return len(errors) == 0, errors


def run_pre_pdf_quality_checks(
    data: dict[str, Any],
    *,
    report_wrapper: dict[str, Any] | None = None,
) -> list[str]:
    """Mandatory + editorial checks before PDF generation."""
    _ok, mandatory_errors = validate_report_for_finalization(data)
    issues: list[str] = list(mandatory_errors)

    assessment = data.get("assessment") if isinstance(data.get("assessment"), dict) else {}
    warnings = assessment.get("warnings") if isinstance(assessment.get("warnings"), list) else []
    assumptions = (
        assessment.get("assumptions") if isinstance(assessment.get("assumptions"), list) else []
    )
    has_warn_or_assumption = any(_non_empty_str(x) for x in warnings) or any(
        _non_empty_str(x) for x in assumptions
    )
    if not has_warn_or_assumption:
        issues.append(
            "Qualität: mindestens eine Warnung oder eine dokumentierte "
            "Annahme/Unsicherheit vorsehen"
        )

    summary = str(assessment.get("summary") or "")
    for pattern in _BINDING_LANGUAGE:
        if pattern.search(summary):
            issues.append(
                "Qualität: Managementtext könnte verbindlich wirken — auf vorläufige "
                "Einordnung und fehlende Zusage prüfen"
            )
            break

    if report_wrapper is not None:
        disclaimers = report_wrapper.get("disclaimers")
        has_disclaimer = isinstance(disclaimers, list) and any(
            _non_empty_str(x) for x in disclaimers
        )
        if not has_disclaimer:
            issues.append("Profil: Report-disclaimers fehlen auf dem Stakeholder-Report")
        audit_ref = report_wrapper.get("audit_hash") or report_wrapper.get(
            "engine_revision_hash"
        )
        if not _non_empty_str(audit_ref):
            issues.append("Profil: Audit-Hash/Engine-Revision fehlt auf dem Report")

    report = data.get("report") if isinstance(data.get("report"), dict) else {}
    if report.get("status") == "final" and not _non_empty_str(report.get("contentHash")):
        issues.append(
            "Finaler Report: report.contentHash (SHA-256) muss vor dem PDF-Download gesetzt sein"
        )

    return issues
