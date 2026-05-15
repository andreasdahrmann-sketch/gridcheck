import type { GridcheckReportData } from "./types/gridcheck-report-data";
import { isReportStakeholderType } from "./stakeholder-legacy-map";

function isNonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function isGeneratingTechnology(technology: GridcheckReportData["project"]["technology"]): boolean {
  return technology === "pv" || technology === "wind" || technology === "battery" || technology === "hybrid";
}

function hasFeedOrConsumptionCapacity(p: GridcheckReportData["project"]): boolean {
  return (
    (p.feedInCapacityMw !== undefined && Number.isFinite(p.feedInCapacityMw)) ||
    (p.consumptionCapacityMw !== undefined && Number.isFinite(p.consumptionCapacityMw))
  );
}

/**
 * Harte Pflichtfelder vor Report-Finalisierung (Spezifikation Abschnitt 4).
 */
export function validateReportForFinalization(data: GridcheckReportData): { ok: boolean; errors: string[] } {
  const errors: string[] = [];
  const { report, project, location, grid, risks, cost, assessment, sources, audit } = data;

  if (!isNonEmptyString(report.reportId)) errors.push("report.reportId fehlt");
  if (!isNonEmptyString(report.auditId)) errors.push("report.auditId fehlt");
  if (!isNonEmptyString(report.reportVersion)) errors.push("report.reportVersion fehlt");
  if (!isNonEmptyString(report.modelVersion)) errors.push("report.modelVersion fehlt");
  if (!isNonEmptyString(report.scoringVersion)) errors.push("report.scoringVersion fehlt");
  if (!isNonEmptyString(report.createdAt)) errors.push("report.createdAt fehlt");
  if (!isReportStakeholderType(report.stakeholderType)) errors.push("report.stakeholderType ungültig");

  if (!isNonEmptyString(project.projectId)) errors.push("project.projectId fehlt");
  if (!isNonEmptyString(project.projectName)) errors.push("project.projectName fehlt");
  if (!project.technology) errors.push("project.technology fehlt");
  if (!project.operationMode) errors.push("project.operationMode fehlt");

  if (!isFiniteNumber(location.latitude)) errors.push("location.latitude ungültig");
  if (!isFiniteNumber(location.longitude)) errors.push("location.longitude ungültig");

  if (!grid.recommendedVoltageLevel) errors.push("grid.recommendedVoltageLevel fehlt");
  if (!Array.isArray(grid.candidateConnectionPoints)) errors.push("grid.candidateConnectionPoints fehlt");
  if (!grid.n1Screening) errors.push("grid.n1Screening fehlt");

  const rk: (keyof typeof risks)[] = [
    "overallRisk",
    "gridConnectionRisk",
    "costRisk",
    "timelineRisk",
    "dataQualityRisk",
  ];
  for (const k of rk) {
    if (!risks[k]) errors.push(`risks.${String(k)} fehlt`);
  }

  if (!assessment.recommendation) errors.push("assessment.recommendation fehlt");
  if (!isNonEmptyString(assessment.summary)) errors.push("assessment.summary fehlt");
  if (!Array.isArray(assessment.assumptions)) errors.push("assessment.assumptions fehlt");
  if (!Array.isArray(assessment.warnings)) errors.push("assessment.warnings fehlt");
  if (!Array.isArray(assessment.nextSteps)) errors.push("assessment.nextSteps fehlt");

  if (!Array.isArray(sources) || sources.length === 0) errors.push("sources: mindestens eine Quelle erforderlich");
  if (!isNonEmptyString(audit.inputHash)) errors.push("audit.inputHash fehlt");
  if (!isNonEmptyString(audit.resultHash)) errors.push("audit.resultHash fehlt");
  if (typeof audit.immutable !== "boolean") errors.push("audit.immutable muss boolean sein");

  const stakeholder = report.stakeholderType;

  if (stakeholder === "project_developer") {
    if (!hasFeedOrConsumptionCapacity(project)) {
      errors.push("project_developer: project.feedInCapacityMw oder project.consumptionCapacityMw erforderlich");
    }
    if (!isFiniteNumber(cost.lowEstimate) || !isFiniteNumber(cost.baseEstimate) || !isFiniteNumber(cost.highEstimate)) {
      errors.push("project_developer: cost.lowEstimate/baseEstimate/highEstimate erforderlich");
    }
    if (!Array.isArray(cost.mainCostDrivers) || cost.mainCostDrivers.length === 0) {
      errors.push("project_developer: cost.mainCostDrivers mindestens ein Eintrag");
    }
    if (grid.candidateConnectionPoints.length < 1) {
      errors.push("project_developer: mindestens ein Anschlusskandidat");
    }
    if (assessment.nextSteps.length < 3) {
      errors.push("project_developer: assessment.nextSteps mindestens drei Einträge");
    }
  }

  if (stakeholder === "grid_operator") {
    if (!hasFeedOrConsumptionCapacity(project)) {
      errors.push("grid_operator: project.feedInCapacityMw oder project.consumptionCapacityMw erforderlich");
    }
    if (!grid.n1Screening.limitations?.length) {
      errors.push("grid_operator: grid.n1Screening.limitations mindestens ein Eintrag");
    }
    if (!grid.n1Screening.requiredFollowUp?.length) {
      errors.push("grid_operator: grid.n1Screening.requiredFollowUp mindestens ein Eintrag");
    }
    if (!audit.generatedBy) {
      errors.push("grid_operator: audit.generatedBy erforderlich");
    }
    const missingRetrievedAt = sources.some((s) => !isNonEmptyString(s.retrievedAt));
    if (missingRetrievedAt) {
      errors.push("grid_operator: jede Quelle braucht retrievedAt (Datenstand)");
    }
  }

  if (stakeholder === "investor") {
    if (!isFiniteNumber(cost.lowEstimate) || !isFiniteNumber(cost.baseEstimate) || !isFiniteNumber(cost.highEstimate)) {
      errors.push("investor: cost.lowEstimate/baseEstimate/highEstimate erforderlich");
    }
    if (!Array.isArray(cost.costItems) || cost.costItems.length === 0) {
      errors.push("investor: cost.costItems mindestens eine Position");
    }
    if (!Array.isArray(assessment.keyFindings) || assessment.keyFindings.filter(isNonEmptyString).length === 0) {
      errors.push("investor: assessment.keyFindings mindestens ein nicht-leerer Eintrag");
    }
    if (isGeneratingTechnology(project.technology)) {
      if (risks.curtailmentRisk === undefined || risks.curtailmentRisk === null) {
        errors.push("investor: risks.curtailmentRisk bei Erzeugungsanlage erforderlich");
      }
    }
  }

  return { ok: errors.length === 0, errors };
}
