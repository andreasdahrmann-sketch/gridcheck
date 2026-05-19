/**
 * Mirror of backend/engine/plant_types.py — display & Zod only, not authoritative.
 */
import { z } from "zod";

export const plantTypeIdSchema = z.enum([
  "pv",
  "wind",
  "bess",
  "hybrid_pv_bess",
  "chp",
  "hydro",
  "consumption",
]);

export const feedInManagementClassSchema = z.enum([
  "none",
  "remote_control",
  "direct_marketing",
]);

export const reactivePowerModeSchema = z.enum([
  "fixed_cos_phi",
  "cos_phi_p",
  "q_u",
  "q_setpoint",
  "bidirectional",
]);

export const voltageLevelKeySchema = z.enum(["low", "medium", "high"]);

export const powerFactorRangeSchema = z.object({
  min: z.number(),
  max: z.number(),
});

export const plantTypeConfigSchema = z.object({
  id: plantTypeIdSchema.optional(),
  label: z.string(),
  label_en: z.string(),
  default_power_factor: z.number(),
  power_factor_range: powerFactorRangeSchema,
  default_simultaneity_factor: z.number(),
  simultaneity_note: z.string(),
  reactive_power_capable: z.boolean(),
  default_reactive_power_mode: reactivePowerModeSchema,
  has_dc_side: z.boolean(),
  default_norm_reference: z.object({
    low: z.string(),
    medium: z.string(),
    high: z.string(),
  }),
  feed_in_profile_note: z.string(),
  project_type: z.enum(["generation", "consumption", "storage", "mixed"]),
});

export type PlantTypeId = z.infer<typeof plantTypeIdSchema>;
export type FeedInManagementClass = z.infer<typeof feedInManagementClassSchema>;
export type ReactivePowerMode = z.infer<typeof reactivePowerModeSchema>;
export type PlantTypeConfigMirror = z.infer<typeof plantTypeConfigSchema>;

/** UI options — aligned with Python PLANT_TYPE_CONFIG */
export const PLANT_TYPE_OPTIONS: Array<{
  value: PlantTypeId;
  label: string;
  hint: string;
  defaultPowerFactor: number;
  defaultSimultaneity: number;
  hasDcSide: boolean;
}> = [
  {
    value: "pv",
    label: "Photovoltaik",
    hint: "DC/AC optional; Netzanschluss auf AC-Leistung.",
    defaultPowerFactor: 0.9,
    defaultSimultaneity: 0.85,
    hasDcSide: true,
  },
  {
    value: "wind",
    label: "Windenergie",
    hint: "Gleichzeitigkeit typ. 0,35 — volatile Einspeise.",
    defaultPowerFactor: 0.9,
    defaultSimultaneity: 0.35,
    hasDcSide: false,
  },
  {
    value: "bess",
    label: "Batteriespeicher",
    hint: "Bidirektional; Blindleistungsmodus mit VNB klären.",
    defaultPowerFactor: 0.92,
    defaultSimultaneity: 0.9,
    hasDcSide: false,
  },
  {
    value: "hybrid_pv_bess",
    label: "Hybrid (PV + Speicher)",
    hint: "Kombinierte Einspeise- und Speicherlogik.",
    defaultPowerFactor: 0.98,
    defaultSimultaneity: 0.88,
    hasDcSide: true,
  },
  {
    value: "chp",
    label: "Kraft-Wärme-Kopplung (BHKW)",
    hint: "Einspeisung/Bezug je nach Betriebsweise.",
    defaultPowerFactor: 0.95,
    defaultSimultaneity: 0.9,
    hasDcSide: false,
  },
  {
    value: "hydro",
    label: "Wasserkraft",
    hint: "Regelbar — Wasserrecht und VNB-Vorgaben beachten.",
    defaultPowerFactor: 0.9,
    defaultSimultaneity: 0.8,
    hasDcSide: false,
  },
  {
    value: "consumption",
    label: "Verbrauch / Last",
    hint: "VDE-AR-N 4100 — kein EEG-Einspeisemanagement.",
    defaultPowerFactor: 0.95,
    defaultSimultaneity: 1.0,
    hasDcSide: false,
  },
];

export const FEED_IN_CLASS_LABELS: Record<FeedInManagementClass, string> = {
  none: "Kein §9-Einspeisemanagement (<25 kW AC)",
  remote_control: "Fernsteuerung / Einspeisemanagement (25–100 kW AC)",
  direct_marketing: "Direktvermarktung (≥100 kW AC)",
};

export const REACTIVE_POWER_MODE_LABELS: Record<ReactivePowerMode, string> = {
  fixed_cos_phi: "Festes cos φ",
  cos_phi_p: "cos φ(P)",
  q_u: "Q(U)-Kennlinie",
  q_setpoint: "Q-Sollwert",
  bidirectional: "Bidirektional (4-Quadranten)",
};

export function plantTypeLabel(id: PlantTypeId | string | undefined): string {
  const normalized =
    id === "hybrid" ? "hybrid_pv_bess" : id;
  return PLANT_TYPE_OPTIONS.find((o) => o.value === normalized)?.label ?? String(id ?? "—");
}

export function plantTypeDefaults(id: PlantTypeId | undefined) {
  const opt = PLANT_TYPE_OPTIONS.find((o) => o.value === id);
  return opt ?? PLANT_TYPE_OPTIONS[0];
}
