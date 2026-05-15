import type { StakeholderType } from "./types/gridcheck-report-data";

/** Backend-Engine / Jinja-Templates nutzen weiterhin kurze Rollen-IDs. */
export type LegacyStakeholderReportType = "projektierer" | "vnb" | "invest";

export const STAKEHOLDER_TO_LEGACY_REPORT_TYPE: Record<StakeholderType, LegacyStakeholderReportType> = {
  project_developer: "projektierer",
  grid_operator: "vnb",
  investor: "invest",
};

export const LEGACY_REPORT_TYPE_TO_STAKEHOLDER: Record<LegacyStakeholderReportType, StakeholderType> = {
  projektierer: "project_developer",
  vnb: "grid_operator",
  invest: "investor",
};

export function isReportStakeholderType(value: unknown): value is StakeholderType {
  return value === "project_developer" || value === "grid_operator" || value === "investor";
}
