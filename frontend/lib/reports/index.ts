export type {
  AuditActor,
  ConnectionCandidate,
  CostItem,
  DataSourceUsage,
  GridcheckReportData,
  GridPressureIndicator,
  N1ScreeningResult,
  OperationMode,
  ProjectTechnology,
  RecommendationLevel,
  ReportStatus,
  RiskLevel,
  StakeholderType,
  VoltageLevel,
} from "./types/gridcheck-report-data";
export type { ReportProfile, ReportSectionDefinition, DetailLevel, ReportTone, TableDensity } from "./types/report-profile";
export type { ReportAuditEvent, ReportAuditEventType } from "./types/report-audit";

export {
  projectDeveloperReportProfile,
  gridOperatorReportProfile,
  investorReportProfile,
  getReportProfile,
} from "./profiles";
export {
  STAKEHOLDER_TO_LEGACY_REPORT_TYPE,
  LEGACY_REPORT_TYPE_TO_STAKEHOLDER,
  isReportStakeholderType,
} from "./stakeholder-legacy-map";
export type { LegacyStakeholderReportType } from "./stakeholder-legacy-map";

export {
  sharedDisclaimerDe,
  projectDeveloperConclusionTemplate,
  gridOperatorReviewNoteTemplate,
  investorExecutiveSummaryTemplate,
  fillReportTemplate,
} from "./templates/shared-blocks";

export { validateReportForFinalization } from "./validate-report-data";
export { runPrePdfQualityChecks, prePdfQualityChecklistDe } from "./pre-pdf-checks";
export {
  stableStringify,
  canonicalReportHashPayload,
  sha256HexUtf8,
  computeReportContentHash,
} from "./report-hash";
