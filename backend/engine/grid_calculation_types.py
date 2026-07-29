"""Pydantic types for grid connection screening v2 (revisionssicher, dokumentierte Annahmen)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


PlantTypeLiteral = Literal[
    "pv",
    "wind",
    "bess",
    "hybrid_pv_bess",
    "chp",
    "hydro",
    "consumption",
]
FeedInManagementClass = Literal["none", "remote_control", "direct_marketing"]
ReactivePowerMode = Literal[
    "fixed_cos_phi",
    "cos_phi_p",
    "q_u",
    "q_setpoint",
    "bidirectional",
]


class GridConnectionInput(BaseModel):
    project_type: Literal["generation", "consumption", "storage", "mixed"] = "generation"
    plant_type: PlantTypeLiteral | None = None
    power_kw: float = Field(..., gt=0, le=2_000_000, description="AC-Anschlussleistung am Netz")
    screening_power_kw: float | None = Field(
        default=None,
        gt=0,
        le=2_000_000,
        description="Leistung nach Gleichzeitigkeit für Screening",
    )
    dc_kwp: float | None = Field(default=None, gt=0, le=2_000_000)
    ac_kw: float | None = Field(default=None, gt=0, le=2_000_000)
    simultaneity_factor: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Gleichzeitigkeitsfaktor (Audit, aus PlantTypeConfig)",
    )
    reactive_power_mode: ReactivePowerMode | None = None
    power_factor: float = Field(..., ge=0.8, le=1.0)
    voltage_level: Literal["low", "medium", "high"] = "medium"
    nominal_voltage_kv: float | None = Field(
        default=None,
        gt=0,
        le=380,
        description=(
            "Tatsaechliche Nennspannung in kV (z. B. 10/20/30 MS oder 110/220/380 HS). "
            "Wenn gesetzt, hat diese Vorrang vor den Level-Defaults 0.4/20/110."
        ),
    )
    connection_type: Literal["single_phase", "three_phase"] = "three_phase"
    cos_phi_known: bool | None = None
    existing_connection: bool | None = None
    network_form: Literal["radial", "ring", "meshed", "unknown"] | None = None

    cable_length_km: float = Field(..., gt=0, le=500)
    cable_length_source: Literal["user_input", "geo_calculated", "estimated"] = "estimated"
    cable_cross_section_mm2: float = Field(..., gt=0, le=3000)
    cable_material: Literal["copper", "aluminum"] = "aluminum"
    cable_type: Literal["overhead", "underground"] = "underground"

    transformer_power_kva: float | None = Field(default=None, gt=0)
    transformer_load_percent: float | None = Field(default=None, ge=0, le=150)
    transformer_impedance_percent: float | None = Field(default=None, gt=0, le=20)
    network_short_circuit_mva: float | None = Field(default=None, gt=0)
    grid_topology: Literal["radial", "ring", "meshed", "unknown"] = "unknown"

    coordinates: Coordinates | None = None
    network_operator: str | None = Field(default=None, max_length=200)
    settlement_type: Literal["urban", "suburban", "rural"] = "suburban"


class CalculationAssumption(BaseModel):
    parameter: str
    assumed_value: str
    reason: str
    norm_reference: str | None = None
    confidence: Literal["high", "medium", "low"]


class VoltageDropInputs(BaseModel):
    current_a: float
    length_km: float
    resistance_ohm_per_km: float
    reactance_ohm_per_km: float
    cos_phi: float
    sin_phi: float
    voltage_kv: float


class VoltageDropResult(BaseModel):
    delta_u_percent: float
    delta_u_volt: float
    limit_percent: float
    norm_reference: str
    formula: str
    inputs: VoltageDropInputs
    compliant: bool
    margin_percent: float


class ShortCircuitResult(BaseModel):
    calculation_method: Literal["iec60909_simplified", "iec60909_full", "estimated"]
    ik_max_ka: float | None = None
    ik_min_ka: float | None = None
    limiting_factor: str | None = None
    data_quality: Literal["measured", "calculated", "estimated"]
    disclaimer: str
    cannot_calculate: bool
    missing_data: list[str] = Field(default_factory=list)


class N1Assessment(BaseModel):
    assessment_type: Literal["topological_analysis", "statistical_assessment", "insufficient_data"]
    grid_topology: Literal["radial", "ring", "meshed", "unknown"]
    redundancy_available: bool | None
    critical_elements: list[str] = Field(default_factory=list)
    recommendation: str
    disclaimer: str
    requires_detailed_study: bool


class ThermalResult(BaseModel):
    current_a: float
    thermal_limit_a: float
    utilization_percent: float
    compliant: bool
    cable_type: str


class AppliedThresholds(BaseModel):
    voltage_drop_limit_percent: float
    voltage_drop_norm: str
    power_limit_kw: float
    power_limit_basis: str
    connection_voltage_threshold_kw: float


class NextStep(BaseModel):
    priority: Literal["immediate", "required", "recommended"]
    action: str
    responsible: Literal["applicant", "network_operator", "planner"]
    norm_reference: str | None = None


class FeasibilityResult(BaseModel):
    status: Literal["feasible", "conditionally_feasible", "requires_study", "likely_infeasible"]
    conditions: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    estimated_process_time: str
    next_steps: list[NextStep] = Field(default_factory=list)
    confidence_level: Literal["high", "medium", "low"]
    confidence_reason: str


class TransformerAssessment(BaseModel):
    status: Literal["insufficient_data", "screened"]
    required_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    transformer_power_kva: float | None = None
    existing_load_percent: float | None = None
    project_apparent_kva: float | None = None
    screened_total_utilization_percent: float | None = None
    screening_notes: list[str] = Field(default_factory=list)
    disclaimer: str


class ProtectionChecklistItem(BaseModel):
    topic: str
    norm_reference: str
    status: Literal["requires_verification", "requires_configuration", "requires_documentation"]
    note: str


class ProtectionConceptScreening(BaseModel):
    applicable: bool
    voltage_level_ref: str
    checklist: list[ProtectionChecklistItem] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    disclaimer: str


class NetworkFeedbackTopic(BaseModel):
    standard: str
    subject: str
    screening_level: Literal["qualitative"]
    warning: str


class NetworkFeedbackScreening(BaseModel):
    applicable: bool
    cannot_quantify: bool
    topics: list[NetworkFeedbackTopic] = Field(default_factory=list)
    recommended_studies: list[str] = Field(default_factory=list)
    disclaimer: str


class CoincidenceFactorScreening(BaseModel):
    single_connection_analysis: bool
    cluster_modeling_available: bool
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str


class NormReference(BaseModel):
    code: str
    title: str
    applied_to: str


class EegFeedInScreening(BaseModel):
    applicable: bool
    power_kw: float
    feed_in_management_class: FeedInManagementClass | None = None
    remote_control_threshold_kw: float = 25.0
    direct_marketing_hint_threshold_kw: float = 100.0
    warnings: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    disclaimer: str = ""


class ReactivePowerChecklistItem(BaseModel):
    topic: str
    norm_reference: str
    status: Literal["requires_verification", "requires_study", "requires_configuration"]
    note: str


class ReactivePowerScreening(BaseModel):
    applicable: bool
    power_kw: float
    threshold_kw: float = 135.0
    checklist: list[ReactivePowerChecklistItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    disclaimer: str = ""


class ProcessTimelinePhase(BaseModel):
    phase: str
    duration_weeks: str
    responsible: Literal["applicant", "network_operator", "planner"]
    note: str | None = None


class ProcessTimeline(BaseModel):
    estimated_total: str
    phases: list[ProcessTimelinePhase]
    disclaimer: str


class BkzHint(BaseModel):
    applicable: bool
    qualitative_band: Literal["niedrig", "mittel", "hoch", "unbekannt"]
    norm_reference: str
    hint: str
    disclaimer: str


class NvpRecommendation(BaseModel):
    applicable: bool
    suggested_voltage_level: str
    nearest_node_hint: str
    cable_length_estimate_km: float
    cable_length_note: str
    plant_type: str
    ac_kw: float
    disclaimer: str


class TabDisclaimer(BaseModel):
    applicable: bool
    plz: str | None = None
    vnb_name: str | None = None
    message: str
    disclaimer: str


class ProjektiererPerspective(BaseModel):
    plant_type: str
    plant_type_label: str
    dc_kwp: float | None = None
    ac_kw: float
    overbuild_ratio: float | None = None
    screening_power_kw: float
    cos_phi: float
    cos_phi_source: Literal["nutzer", "plant_default"]
    power_factor: float
    power_factor_source: Literal["nutzer", "plant_default"]
    simultaneity_factor: float
    simultaneity_note: str | None = None
    reactive_power_mode: ReactivePowerMode | None = None
    feed_in_profile_note: str | None = None
    feed_in_management_class: FeedInManagementClass
    process_timeline: ProcessTimeline
    bkz_hint: BkzHint
    nvp_recommendation: NvpRecommendation
    tab_disclaimer: TabDisclaimer
    kumulation_warning: dict[str, Any] | None = None
    scenario_comparison_note: dict[str, Any] | None = None
    reactive_power_threshold_kw: float = 135.0
    disclaimer: str


class GridCalculationResult(BaseModel):
    calculated_at: str
    calculation_version: str
    assumptions: list[CalculationAssumption]
    voltage_drop_analysis: VoltageDropResult
    short_circuit_analysis: ShortCircuitResult
    thermal_analysis: ThermalResult
    n1_assessment: N1Assessment
    thresholds: AppliedThresholds
    feasibility: FeasibilityResult
    transformer_assessment: TransformerAssessment
    protection_concept_screening: ProtectionConceptScreening
    network_feedback_screening: NetworkFeedbackScreening
    coincidence_factor_screening: CoincidenceFactorScreening
    norm_references_applied: list[NormReference] = Field(default_factory=list)
    eeg_feed_in_screening: EegFeedInScreening
    reactive_power_screening: ReactivePowerScreening
    projektierer_perspective: ProjektiererPerspective | None = None

    def model_dump(self, **kwargs):
        return super().model_dump(mode="json", **kwargs)
