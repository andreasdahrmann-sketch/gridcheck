export type ReportAuditEventType =
  | "report_created"
  | "report_previewed"
  | "report_finalized"
  | "report_downloaded"
  | "report_shared"
  | "report_archived"
  | "report_version_created";

export interface ReportAuditEvent {
  eventId: string;
  reportId: string;
  analysisId: string;
  eventType: ReportAuditEventType;
  actorUserId?: string;
  actorRole?: string;
  occurredAt: string;
  metadata: Record<string, string | number | boolean | null>;
  previousResultHash?: string;
  newResultHash?: string;
}
