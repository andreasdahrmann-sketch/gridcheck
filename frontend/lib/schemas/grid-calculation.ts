import { z } from "zod";

/** Read-only Zod schemas for API block `grid_calculation_v2` (authoritative engine: Python). */

export const calculationAssumptionSchema = z.object({
  parameter: z.string(),
  assumed_value: z.string(),
  reason: z.string(),
  norm_reference: z.string().optional().nullable(),
  confidence: z.enum(["high", "medium", "low"]),
});

export const voltageDropResultSchema = z.object({
  delta_u_percent: z.number(),
  delta_u_volt: z.number(),
  limit_percent: z.number(),
  norm_reference: z.string(),
  formula: z.string(),
  inputs: z.object({
    current_a: z.number(),
    length_km: z.number(),
    resistance_ohm_per_km: z.number(),
    reactance_ohm_per_km: z.number(),
    cos_phi: z.number(),
    sin_phi: z.number(),
    voltage_kv: z.number(),
  }),
  compliant: z.boolean(),
  margin_percent: z.number(),
});

export const shortCircuitResultSchema = z.object({
  calculation_method: z.enum(["iec60909_simplified", "iec60909_full", "estimated"]),
  ik_max_ka: z.number().optional().nullable(),
  ik_min_ka: z.number().optional().nullable(),
  limiting_factor: z.string().optional().nullable(),
  data_quality: z.enum(["measured", "calculated", "estimated"]),
  disclaimer: z.string(),
  cannot_calculate: z.boolean(),
  missing_data: z.array(z.string()).default([]),
});

export const n1AssessmentSchema = z.object({
  assessment_type: z.enum(["topological_analysis", "statistical_assessment", "insufficient_data"]),
  grid_topology: z.enum(["radial", "ring", "meshed", "unknown"]),
  redundancy_available: z.boolean().nullable(),
  critical_elements: z.array(z.string()),
  recommendation: z.string(),
  disclaimer: z.string(),
  requires_detailed_study: z.boolean(),
});

export const thermalResultSchema = z.object({
  current_a: z.number(),
  thermal_limit_a: z.number(),
  utilization_percent: z.number(),
  compliant: z.boolean(),
  cable_type: z.string(),
});

export const feasibilityResultSchema = z.object({
  status: z.enum(["feasible", "conditionally_feasible", "requires_study", "likely_infeasible"]),
  conditions: z.array(z.string()),
  required_documents: z.array(z.string()),
  estimated_process_time: z.string(),
  next_steps: z.array(
    z.object({
      priority: z.enum(["immediate", "required", "recommended"]),
      action: z.string(),
      responsible: z.enum(["applicant", "network_operator", "planner"]),
      norm_reference: z.string().optional().nullable(),
    }),
  ),
  confidence_level: z.enum(["high", "medium", "low"]),
  confidence_reason: z.string(),
});

export const transformerAssessmentSchema = z.object({
  status: z.enum(["insufficient_data", "screened"]),
  required_fields: z.array(z.string()),
  missing_fields: z.array(z.string()),
  transformer_power_kva: z.number().optional().nullable(),
  existing_load_percent: z.number().optional().nullable(),
  project_apparent_kva: z.number().optional().nullable(),
  screened_total_utilization_percent: z.number().optional().nullable(),
  screening_notes: z.array(z.string()).default([]),
  disclaimer: z.string(),
});

export const protectionConceptScreeningSchema = z.object({
  applicable: z.boolean(),
  voltage_level_ref: z.string(),
  checklist: z.array(
    z.object({
      topic: z.string(),
      norm_reference: z.string(),
      status: z.enum(["requires_verification", "requires_configuration", "requires_documentation"]),
      note: z.string(),
    }),
  ),
  required_documents: z.array(z.string()),
  disclaimer: z.string(),
});

export const networkFeedbackScreeningSchema = z.object({
  applicable: z.boolean(),
  cannot_quantify: z.boolean(),
  topics: z.array(
    z.object({
      standard: z.string(),
      subject: z.string(),
      screening_level: z.literal("qualitative"),
      warning: z.string(),
    }),
  ),
  recommended_studies: z.array(z.string()),
  disclaimer: z.string(),
});

export const coincidenceFactorScreeningSchema = z.object({
  single_connection_analysis: z.boolean(),
  cluster_modeling_available: z.boolean(),
  warnings: z.array(z.string()),
  disclaimer: z.string(),
});

export const normReferenceSchema = z.object({
  code: z.string(),
  title: z.string(),
  applied_to: z.string(),
});

export const eegFeedInScreeningSchema = z.object({
  applicable: z.boolean(),
  power_kw: z.number(),
  remote_control_threshold_kw: z.number().optional(),
  direct_marketing_hint_threshold_kw: z.number().optional(),
  warnings: z.array(z.string()),
  required_documents: z.array(z.string()),
  hints: z.array(z.string()),
  disclaimer: z.string(),
});

export const gridCalculationV2Schema = z.object({
  calculated_at: z.string(),
  calculation_version: z.string(),
  assumptions: z.array(calculationAssumptionSchema),
  voltage_drop_analysis: voltageDropResultSchema,
  short_circuit_analysis: shortCircuitResultSchema,
  thermal_analysis: thermalResultSchema,
  n1_assessment: n1AssessmentSchema,
  thresholds: z.object({
    voltage_drop_limit_percent: z.number(),
    voltage_drop_norm: z.string(),
    power_limit_kw: z.number(),
    power_limit_basis: z.string(),
    connection_voltage_threshold_kw: z.number(),
  }),
  feasibility: feasibilityResultSchema,
  transformer_assessment: transformerAssessmentSchema,
  protection_concept_screening: protectionConceptScreeningSchema,
  network_feedback_screening: networkFeedbackScreeningSchema,
  coincidence_factor_screening: coincidenceFactorScreeningSchema,
  norm_references_applied: z.array(normReferenceSchema),
  eeg_feed_in_screening: eegFeedInScreeningSchema,
});

export type GridCalculationV2 = z.infer<typeof gridCalculationV2Schema>;

const FEASIBILITY_LABELS: Record<GridCalculationV2["feasibility"]["status"], string> = {
  feasible: "Grundsaetzlich plausibel",
  conditionally_feasible: "Bedingt plausibel",
  requires_study: "Vertiefte Studie erforderlich",
  likely_infeasible: "Voraussichtlich nicht plausibel",
};

export function parseGridCalculationV2(raw: unknown): GridCalculationV2 | null {
  const parsed = gridCalculationV2Schema.safeParse(raw);
  return parsed.success ? parsed.data : null;
}

export function feasibilityStatusLabel(status: GridCalculationV2["feasibility"]["status"]): string {
  return FEASIBILITY_LABELS[status] ?? status;
}
