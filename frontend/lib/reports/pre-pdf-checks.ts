import type { GridcheckReportData } from "./types/gridcheck-report-data";
import { getReportProfile } from "./profiles";
import { validateReportForFinalization } from "./validate-report-data";

function nonEmpty(s: string): boolean {
  return s.trim().length > 0;
}

/** Heuristik: keine werblich-verbindlichen Formulierungen im Summary. */
const BINDING_LANGUAGE: RegExp[] = [
  /\bkapazitätsgarant/i,
  /\bnetzanschluss\s*zusage\b/i,
  /\bgarantiert\s+anschlussfähig/i,
];

/**
 * Qualitätsprüfung vor PDF-Erzeugung (Spezifikation Abschnitt 8 + redaktionelle Guardrails).
 * Liefert konsolidierte Hinweise inkl. Pflichtfeldfehler aus validateReportForFinalization.
 */
export function runPrePdfQualityChecks(data: GridcheckReportData): string[] {
  const issues: string[] = [];
  const mandatory = validateReportForFinalization(data);
  issues.push(...mandatory.errors);

  const warnOrAssumption =
    data.assessment.warnings.some(nonEmpty) || data.assessment.assumptions.some(nonEmpty);
  if (!warnOrAssumption) {
    issues.push("Qualität: mindestens eine Warnung oder eine dokumentierte Annahme/Unsicherheit vorsehen");
  }

  const summary = data.assessment.summary;
  for (const rx of BINDING_LANGUAGE) {
    if (rx.test(summary)) {
      issues.push(
        "Qualität: Managementtext könnte verbindlich wirken — auf vorläufige Einordnung und fehlende Zusage prüfen",
      );
      break;
    }
  }

  const profile = getReportProfile(data.report.stakeholderType);
  if (!profile.includeDisclaimer || !profile.includeAuditBlock) {
    issues.push("Profil: Disclaimer und Revisionsblock müssen für alle Stakeholder aktiv sein");
  }

  if (data.report.status === "final" && !nonEmpty(data.report.contentHash ?? "")) {
    issues.push("Finaler Report: report.contentHash (SHA-256) muss vor dem PDF-Download gesetzt sein");
  }

  return issues;
}

export const prePdfQualityChecklistDe: readonly string[] = [
  "Sind alle Pflichtfelder vorhanden?",
  "Passt der Stakeholder-Typ zum Report-Profil?",
  "Sind Datenquellen inkl. Datenstand (retrievedAt) erfasst?",
  "Sind Modellversion und Scoringversion gesetzt?",
  "Gibt es mindestens eine Warnung oder Unsicherheitsangabe?",
  "Wird keine verbindliche Netzanschlusszusage formuliert?",
  "Ist der Disclaimer im Profil vorgesehen?",
  "Wurde ein Audit- bzw. Content-Hash erzeugt?",
  "Ist der finale Report unveränderbar markiert (audit.immutable)?",
] as const;
