import type { GridCheckResult, StakeholderContextInput } from "@/types";

export type StakeholderCustomerType = NonNullable<StakeholderContextInput["customer_type"]>;
export type StakeholderProductPath = "projektierer" | "vnb" | "invest";

type StakeholderSource = {
  kundentyp?: string;
  stakeholder_context?: StakeholderContextInput;
};

export function resolveStakeholderCustomerType(source?: StakeholderSource | null): StakeholderCustomerType {
  const raw = source?.kundentyp ?? source?.stakeholder_context?.customer_type;
  if (raw === "netzbetreiber") return "netzbetreiber";
  if (raw === "investor") return "investor";
  if (raw === "speicherbetreiber") return "speicherbetreiber";
  return "projektierer";
}

export function resolveStakeholderProductPath(source?: StakeholderSource | null): StakeholderProductPath {
  const customerType = resolveStakeholderCustomerType(source);
  if (customerType === "netzbetreiber") return "vnb";
  if (customerType === "investor") return "invest";
  return "projektierer";
}

export function canViewDeepTechnicalDetails(path: StakeholderProductPath): boolean {
  return path !== "invest";
}

export function getStakeholderProductCopy(path: StakeholderProductPath) {
  if (path === "vnb") {
    return {
      label: "VNB",
      resultTitle: "VNB-Vorpruefung",
      heroTitle: "Strukturierte Anfragepruefung fuer technische VNB-Vorpruefung.",
      heroDescription:
        "Der VNB-Pfad fokussiert strukturierte Anfragepruefung, technische Vorpruefung, Prozesssicht, technische Auflagen und revisionssichere Auditierbarkeit.",
      formIntro:
        "Erfassen Sie nur belastbare Projekt- und Netzgrundlagen. Ohne konkrete Netz- oder Umspannwerksdaten bleibt der Nachweis bewusst konservativ.",
      exportLabel: "VNB-Pruefprotokoll PDF",
      visibilityNote:
        "Dieser Pfad zeigt keine freie interne Netzkapazitaet und erzeugt keine stillschweigende Freigabe interner Netzdaten.",
      summaryLead: "Strukturierte Anfragepruefung, technische Vorpruefung und Auditrolle fuer den Netzbetreiberkontext.",
    };
  }
  if (path === "invest") {
    return {
      label: "Invest",
      resultTitle: "Investoren- / Due-Diligence-Sicht",
      heroTitle: "Standort-, Risiko- und Kostenbandbreite fuer Invest-Entscheidungen.",
      heroDescription:
        "Der Invest-Pfad verdichtet Standortbewertung, Risikoanalyse, Kostenbandbreite, Portfolioeinordnung und due-diligence-orientierte Reports ohne interne Netzdaten offenzulegen.",
      formIntro:
        "Erfassen Sie Standort, Projektreife und Trassenkontext so konkret wie moeglich. Die Investsicht zeigt bewusst aggregierte Risiko- und Kostensignale statt interner Netztiefe.",
      exportLabel: "Invest-Report PDF",
      visibilityNote:
        "Die Investsicht blendet rohe Feeder-, Impedanz- und interne Netzkapazitaetsdetails bewusst aus und zeigt nur aggregierte Risiko- und Kostensignale.",
      summaryLead: "Standortbewertung, Risikoanalyse und Due-Diligence-orientierte Verdichtung fuer Investoren.",
    };
  }
  return {
    label: "Projektierer",
    resultTitle: "Projektierer-Pre-Check",
    heroTitle: "Schnelles technisches Entscheidungs- und Vorbereitungstool fuer Projektierer.",
    heroDescription:
      "Der Projektierer-Pfad unterstuetzt Standortentwicklung, technische Vorpruefung, Variantenvergleich, Kosten- und Trassenklaerung, VNB-Vorbereitung sowie investorentaugliche Vorabkommunikation.",
    formIntro:
      "Erfassen Sie das Projekt so, wie es fuer Standortentscheidung, Variantenvergleich, VNB-Vorbereitung und spaetere Due-Diligence sinnvoll ist. Jede Aussage bleibt konservativ und vorlaeufig.",
    exportLabel: "Projektreport PDF",
    visibilityNote:
      "Der Pre-Check ersetzt keine verbindliche Netzanschlusszusage und behauptet keine freie Kapazitaet ohne belastbare Datenbasis.",
    summaryLead: "Technischer Standardpfad fuer Vorqualifizierung, Variantenvergleich, Trassen- und Kostenvorbereitung.",
  };
}

export function buildIndicativeCostBand(result?: Partial<GridCheckResult> | null) {
  const base =
    typeof result?.kosten_bandbreite?.basis_eur === "number"
      ? result.kosten_bandbreite.basis_eur
      : typeof result?.kosten_indikation_eur === "number"
        ? result.kosten_indikation_eur
        : null;
  if (base === null) return null;
  return {
    niedrig:
      typeof result?.kosten_bandbreite?.niedrig_eur === "number"
        ? result.kosten_bandbreite.niedrig_eur
        : Math.round(base * 0.85),
    basis: base,
    hoch:
      typeof result?.kosten_bandbreite?.hoch_eur === "number"
        ? result.kosten_bandbreite.hoch_eur
        : Math.round(base * 1.25),
    confidence: result?.kosten_bandbreite?.confidence_pct,
    source: result?.kosten_bandbreite?.source,
    assumptions: result?.kosten_bandbreite?.assumptions ?? [],
    drivers: result?.kosten_bandbreite?.drivers ?? [],
  };
}

export function buildProjektiererGuidance(result?: Partial<GridCheckResult> | null) {
  const recommendations = result?.empfehlungen ?? [];
  const routeRisk = result?.route_environment?.risk_level ?? "mittel";
  const hasHybrid = Boolean(result?.projektprofil?.is_hybrid);
  const costBand = buildIndicativeCostBand(result);
  return {
    roles: [
      "Standortentwickler und technischer Vorpruefer",
      "Variantenvergleicher fuer Anschluss-, Speicher- und Trassenoptionen",
      "Datenvorbereiter fuer Netzbetreiber und Projektmanager im Pre-Check",
      "Verkaeufer- und Due-Diligence-Vorbereiter gegenueber Investoren",
    ],
    compareAxes: [
      hasHybrid ? "Hybrid- und Begrenzungsvariante gegen Standardanschluss vergleichen" : "Leistungs- und Spannungsebenenvariante vergleichen",
      routeRisk === "hoch" ? "Trassen- und Genehmigungsvariante vor Kostenoptimierung pruefen" : "Trassen- und Distanzannahmen gegen Kostenband pruefen",
      "VNB-Vorbereitung: Nachweise und offene Datenluecken vor Antrag strukturieren",
      "Investorenfaehige Verdichtung: Kostenband, Risiken und naechste Schritte exportieren",
    ],
    preparationChecklist: [
      result?.n1?.n1_klasse ? `N-1-Nachweistiefe dokumentieren: ${result.n1.n1_klasse}` : "N-1-Nachweistiefe dokumentieren",
      recommendations[0] ?? "Erste technische Massnahme oder Auflage festhalten",
      costBand ? `Kostenbandbreite vorbereiten: ${costBand.basis.toLocaleString("de-DE")} EUR Basiswert` : "Kostenbandbreite fuer Anschluss und Trasse vorbereiten",
      routeRisk === "hoch" ? "Genehmigungs- und Trassenthemen frueh mitfuehren" : "Trassen- und Standortannahmen fuer VNB / Invest sauber dokumentieren",
    ],
  };
}
