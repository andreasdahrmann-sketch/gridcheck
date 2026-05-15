import type { StakeholderType } from "./gridcheck-report-data";

export type ReportTone = "practical" | "formal_technical" | "executive";

export type DetailLevel = "compact" | "standard" | "expert";

export type TableDensity = "low" | "medium" | "high";

export interface ReportSectionDefinition {
  id: string;
  title: string;
  required: boolean;
}

export interface ReportProfile {
  stakeholderType: StakeholderType;
  title: string;
  subtitle: string;
  tone: ReportTone;
  detailLevel: DetailLevel;
  tableDensity: TableDensity;
  includeExecutiveSummary: boolean;
  includeTechnicalAppendix: boolean;
  includeCostDetails: boolean;
  includeAuditBlock: boolean;
  includeDisclaimer: boolean;
  sections: ReportSectionDefinition[];
}
