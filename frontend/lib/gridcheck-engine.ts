import type { GridCheckInput, GridCheckResult, Spannungsebene } from "@/types";

export function hasNetzplanResult(value: Partial<GridCheckResult> | null): value is GridCheckResult {
  return Boolean(
    value &&
      typeof value.score === "number" &&
      typeof value.machbarkeit_stufe === "string" &&
      value.teil_scores &&
      value.kurzschluss &&
      value.projektprofil &&
      value.transparenz,
  );
}

/** Conservative Ik bands (kA) — vorläufig without DSO Sk''. */
const IK_BAND_KA: Record<Spannungsebene, { min: number; typ: number; max: number }> = {
  NS: { min: 16, typ: 22, max: 25 },
  MS: { min: 20, typ: 25, max: 31.5 },
  HS: { min: 31.5, typ: 40, max: 63 },
};

const POWER_LIMITS: Record<
  Spannungsebene,
  { label: string; typicalMaxKw: number; screeningUpperKw: number; hinweis: string }
> = {
  NS: {
    label: "Niederspannung",
    typicalMaxKw: 135,
    screeningUpperKw: 300,
    hinweis:
      "Über ca. 135 kW Einspeiseleistung ist meist ein MS-Anschluss zu prüfen (TAB/VNB können strenger sein).",
  },
  MS: {
    label: "Mittelspannung",
    typicalMaxKw: 20_000,
    screeningUpperKw: 50_000,
    hinweis:
      "Großanlagen: N-1-/Netzstudie mit VNB-Daten nötig; MVP-Screening maximal N1-2 ohne DSO-Daten.",
  },
  HS: {
    label: "Hochspannung",
    typicalMaxKw: 100_000,
    screeningUpperKw: 200_000,
    hinweis: "HS-Anschlüsse sind projektspezifisch; Kurzschluss- und N-1-Nachweise nur vorläufig ohne VNB-Daten.",
  },
};

const CONNECTION_TYPE_LABELS: Record<string, string> = {
  feed_in: "Einspeisung",
  einspeisung: "Einspeisung",
  consumption: "Entnahme",
  entnahme: "Entnahme",
  bidirectional: "Bidirektional",
  mixed: "Gemischt",
  speicher: "Speicher",
  storage: "Speicher",
  unknown: "Unbekannt",
};

export function formatConnectionType(raw: string | undefined): string {
  const key = String(raw ?? "").trim().toLowerCase();
  return CONNECTION_TYPE_LABELS[key] ?? (key ? key : "Unbekannt");
}

export function getPowerLimitHints(spannungsebene: Spannungsebene, anschlussleistungKw?: number) {
  const spec = POWER_LIMITS[spannungsebene];
  const kw = Number(anschlussleistungKw ?? 0);
  return {
    ...spec,
    eingabeKw: kw,
    ueberTypischemRichtwert: kw > spec.typicalMaxKw,
  };
}

/**
 * UI-side Ik band helper (engine computes authoritative values).
 */
export function getMaxShortCircuitCurrent(
  spannungsebene: Spannungsebene,
  options?: { ikBerechnetKa?: number; skMvaProvided?: boolean },
) {
  const band = IK_BAND_KA[spannungsebene];
  let referenz = band.typ;
  if (options?.ikBerechnetKa && options.ikBerechnetKa > 0) {
    referenz = Math.max(band.min, Math.min(band.max, options.ikBerechnetKa));
  }
  return {
    ikReferenzKa: referenz,
    bandMinKa: band.min,
    bandMaxKa: band.max,
    vorlaeufig: !options?.skMvaProvided,
    hinweis:
      "Vorläufige Ik-Bandbreite nach Spannungsebene; verbindlich ist Sk'' aus der Netzbetreiber-Auskunft.",
  };
}

/**
 * Heuristic cable length for form hints only — backend re-computes for analysis.
 */
export function estimateCableLength(input: Pick<GridCheckInput, "spannungsebene" | "entfernung_km" | "plz">) {
  if (input.entfernung_km !== undefined && input.entfernung_km > 0) {
    return {
      km: input.entfernung_km,
      heuristisch: false,
      annahme: "Trassenentfernung aus Nutzereingabe.",
    };
  }
  const span =
    input.spannungsebene === "NS"
      ? { low: 0.15, high: 2.5 }
      : input.spannungsebene === "HS"
        ? { low: 5, high: 35 }
        : { low: 1, high: 12 };
  const plz = (input.plz ?? "").replace(/\D/g, "").slice(0, 5);
  const offset = plz ? (parseInt(plz, 10) % 97) / 97 : 0.5;
  const km = span.low + (span.high - span.low) * (0.35 * offset + 0.1);
  return {
    km: Math.round(km * 1000) / 1000,
    heuristisch: true,
    annahme: `Heuristische Trassenentfernung ca. ${km.toFixed(1)} km (${span.low}–${span.high} km Korridor) — keine GPS-Messung.`,
  };
}

const PLANT_COS_PHI: Record<string, number> = {
  pv: 0.9,
  wind: 0.9,
  bess: 0.92,
  hybrid_pv_bess: 0.98,
  hybrid: 0.98,
  chp: 0.95,
  hydro: 0.9,
  consumption: 0.95,
};

function inferPlantType(input: Pick<GridCheckInput, "plant_type" | "anlagentyp" | "richtung" | "project_components">): string {
  if (input.plant_type) return input.plant_type;
  if (input.anlagentyp === "solar") return "pv";
  if (input.anlagentyp === "wind") return "wind";
  if (input.anlagentyp === "batterie") return "bess";
  const types = (input.project_components ?? []).map((c) => c.component_type);
  if (types.includes("battery") && (types.includes("pv") || types.includes("wind"))) return "hybrid_pv_bess";
  if (types.includes("battery")) return "bess";
  if (input.richtung === "bezug") return "consumption";
  return "pv";
}

export function resolveCosPhiDefault(
  input: Pick<GridCheckInput, "cos_phi" | "cos_phi_known" | "anlagentyp" | "plant_type" | "richtung" | "project_components">,
) {
  if (input.cos_phi_known && input.cos_phi !== undefined && input.cos_phi >= 0.8 && input.cos_phi <= 1) {
    return { cosPhi: input.cos_phi, quelle: "nutzer" as const };
  }
  if (!input.cos_phi_known && input.cos_phi !== undefined && input.cos_phi >= 0.8 && input.cos_phi <= 1) {
    return { cosPhi: input.cos_phi, quelle: "nutzer" as const };
  }
  const plant = inferPlantType(input);
  const cosPhi = PLANT_COS_PHI[plant] ?? 0.95;
  return { cosPhi, quelle: "rolle_default" as const };
}
