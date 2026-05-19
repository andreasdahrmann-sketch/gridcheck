import type { ConfidenceLevel, GridCheckResult } from "@/types";

export type ConfidenceTone = "strong" | "moderate" | "weak" | "unknown";

export interface ConfidenceLevelMeta {
  label: string;
  tone: ConfidenceTone;
  summary: string;
}

const LEVEL_META: Record<ConfidenceLevel, ConfidenceLevelMeta> = {
  A: {
    label: "A – verifiziert / hohe Datenqualität",
    tone: "strong",
    summary: "Mehrere Eingaben stützen sich auf belastbare Quellen oder konservative Normannahmen mit geringer Unsicherheit.",
  },
  B: {
    label: "B – solide Heuristik",
    tone: "moderate",
    summary: "Plausible Projekt- und Netzannahmen; verbleibende Lücken sind benannt und beeinflussen die Aussagekraft.",
  },
  C: {
    label: "C – modelliert / abgeleitet",
    tone: "weak",
    summary: "Wesentliche Teile basieren auf Modell- oder Standardannahmen. Ergebnis ist indikativ, nicht verbindlich.",
  },
  D: {
    label: "D – unsicher / unvollständig",
    tone: "unknown",
    summary: "Kritische Netz- oder Betriebsdaten fehlen. Aussagen sind vorläufig und brauchen VNB-Klärung.",
  },
};

export function getConfidenceLevelMeta(level: ConfidenceLevel): ConfidenceLevelMeta {
  return LEVEL_META[level] ?? LEVEL_META.D;
}

export function buildConfidenceHighlights(result: GridCheckResult, limit = 3): string[] {
  const notes = result.transparenz.confidence_notes ?? [];
  const assumptions = result.transparenz.assumptions ?? [];
  const merged = [...notes, ...assumptions].filter((item) => item.trim().length > 0);
  return merged.slice(0, limit);
}
