/**
 * Canonical report payload for stakeholder-specific PDFs.
 * Same analysis core, different presentation (profiles + templates).
 */

export type StakeholderType = "project_developer" | "grid_operator" | "investor";

export type RiskLevel = "low" | "medium" | "high" | "critical" | "unknown";

export type ConfidenceLevel = "low" | "medium" | "high";

export type RecommendationLevel = "go" | "conditional_go" | "review_required" | "no_go";

export type ProjectTechnology = "pv" | "wind" | "battery" | "hybrid" | "load" | "other";

export type OperationMode = "feed_in" | "consumption" | "bidirectional" | "mixed";

export type VoltageLevel = "lv" | "mv" | "hv" | "ehv" | "unknown";

export type ReportStatus = "draft" | "final" | "archived";

export type AuditActor = "system" | "user" | "admin";

export interface ConnectionCandidate {
  candidateId: string;
  label: string;
  assetType: "line" | "substation" | "switchgear" | "transformer" | "unknown";
  voltageLevel: VoltageLevel;
  distanceKm: number;
  confidence: ConfidenceLevel;
  technicalFitScore: number;
  costRisk: RiskLevel;
  routeRisk: RiskLevel;
  comment: string;
}

export interface N1ScreeningResult {
  status:
    | "not_applicable"
    | "screening_only"
    | "limited"
    | "critical"
    | "requires_grid_operator_data";
  score?: number;
  summary: string;
  limitations: string[];
  requiredFollowUp: string[];
}

export interface GridPressureIndicator {
  indicatorId: string;
  label: string;
  level: RiskLevel;
  detail: string;
}

export interface CostItem {
  label: string;
  low: number;
  base: number;
  high: number;
  confidence: ConfidenceLevel;
  comment?: string;
}

export interface DataSourceUsage {
  sourceId: string;
  sourceName: string;
  sourceType: "user_input" | "public_dataset" | "grid_operator_data" | "model_assumption";
  retrievedAt: string;
  version?: string;
  license?: string;
  confidence: ConfidenceLevel;
  usedFor: string[];
}

export interface GridcheckReportData {
  report: {
    reportId: string;
    auditId: string;
    reportVersion: string;
    modelVersion: string;
    scoringVersion: string;
    createdAt: string;
    stakeholderType: StakeholderType;
    status: ReportStatus;
    /** SHA-256 (hex) über canonicalReportHashPayload — nach Finalisierung setzen. */
    contentHash?: string;
  };
  project: {
    projectId: string;
    projectName: string;
    technology: ProjectTechnology;
    installedCapacityMw?: number;
    feedInCapacityMw?: number;
    consumptionCapacityMw?: number;
    storagePowerMw?: number;
    storageCapacityMwh?: number;
    operationMode: OperationMode;
    targetCod?: string;
  };
  location: {
    addressLabel?: string;
    municipality?: string;
    federalState?: string;
    latitude: number;
    longitude: number;
    parcelInfo?: string;
    /** Netzbetreibergebiet; optional wenn nicht bekannt (siehe Validierung). */
    gridOperatorArea?: string;
  };
  grid: {
    recommendedVoltageLevel: VoltageLevel;
    recommendedConnectionType: string;
    candidateConnectionPoints: ConnectionCandidate[];
    n1Screening: N1ScreeningResult;
    gridPressureIndicators: GridPressureIndicator[];
  };
  risks: {
    overallRisk: RiskLevel;
    gridConnectionRisk: RiskLevel;
    routeRisk: RiskLevel;
    costRisk: RiskLevel;
    timelineRisk: RiskLevel;
    permittingRisk?: RiskLevel;
    curtailmentRisk?: RiskLevel;
    dataQualityRisk: RiskLevel;
  };
  cost: {
    currency: "EUR";
    lowEstimate: number;
    baseEstimate: number;
    highEstimate: number;
    costItems: CostItem[];
    mainCostDrivers: string[];
    confidence: ConfidenceLevel;
  };
  assessment: {
    recommendation: RecommendationLevel;
    summary: string;
    keyFindings: string[];
    assumptions: string[];
    warnings: string[];
    nextSteps: string[];
  };
  sources: DataSourceUsage[];
  audit: {
    inputHash: string;
    resultHash: string;
    generatedBy: AuditActor;
    generatedByUserId?: string;
    immutable: boolean;
  };
}
