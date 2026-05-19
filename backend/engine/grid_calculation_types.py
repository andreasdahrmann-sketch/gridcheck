"""Pydantic types for grid connection screening v2 (revisionssicher, dokumentierte Annahmen)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class GridConnectionInput(BaseModel):
    project_type: Literal["generation", "consumption", "storage", "mixed"] = "generation"
    power_kw: float = Field(..., gt=0, le=2_000_000)
    power_factor: float = Field(..., ge=0.8, le=1.0)
    voltage_level: Literal["low", "medium", "high"] = "medium"
    connection_type: Literal["single_phase", "three_phase"] = "three_phase"

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
    remote_control_threshold_kw: float = 25.0
    direct_marketing_hint_threshold_kw: float = 100.0
    warnings: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    disclaimer: str = ""


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

    def model_dump(self, **kwargs):
        return super().model_dump(mode="json", **kwargs)
