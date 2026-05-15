import type { GridcheckReportData } from "./types/gridcheck-report-data";

/**
 * Deterministische Serialisierung für Hashing (Reihenfolge der Keys stabil).
 */
export function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((v) => stableStringify(v)).join(",")}]`;
  }
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${stableStringify(obj[k])}`).join(",")}}`;
}

/**
 * Kanonische Payload-Struktur für den Report-Content-Hash (Spezifikation Abschnitt 6.4).
 * `analysisId` entspricht hier der Projekt-ID, bis ein separates Analyse-Artefakt im Backend existiert.
 */
export function canonicalReportHashPayload(data: GridcheckReportData): Record<string, unknown> {
  return {
    analysis_id: data.project.projectId,
    report_id: data.report.reportId,
    stakeholder_type: data.report.stakeholderType,
    report_version: data.report.reportVersion,
    input_data: {
      project: data.project,
      location: data.location,
    },
    assessment_result: data.assessment,
    grid: data.grid,
    risks: data.risks,
    cost: data.cost,
    sources: data.sources,
    model_version: data.report.modelVersion,
    scoring_version: data.report.scoringVersion,
    created_at: data.report.createdAt,
  };
}

export async function sha256HexUtf8(text: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new Error("Web Crypto (crypto.subtle) nicht verfügbar — Hash im Backend erzeugen");
  }
  const digest = await subtle.digest("SHA-256", new TextEncoder().encode(text));
  const bytes = new Uint8Array(digest);
  let hex = "";
  for (let i = 0; i < bytes.length; i += 1) {
    hex += bytes[i].toString(16).padStart(2, "0");
  }
  return hex;
}

export async function computeReportContentHash(data: GridcheckReportData): Promise<string> {
  return sha256HexUtf8(stableStringify(canonicalReportHashPayload(data)));
}
