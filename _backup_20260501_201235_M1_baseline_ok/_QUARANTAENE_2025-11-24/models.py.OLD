from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal, Dict
from enum import Enum
from datetime import datetime
import uuid
import math


class VoltageLevel(str, Enum):
    NS = "NS"
    MS_10 = "MS_10"
    MS_20 = "MS_20"
    MS_30 = "MS_30"
    HS = "HS"
    HoeS = "HoeS"

class ProjectType(str, Enum):
    PV = "pv"
    WIND = "wind"
    SPEICHER = "speicher"
    WAERMEPUMPE = "waermepumpe"
    LADEINFRA = "ladeinfra"
    INDUSTRIE = "industrie"
    HYBRID = "hybrid"

class GridTopology(str, Enum):
    RADIAL = "radial"
    RING = "ring"
    VERMASCHT = "vermascht"
    STICHLEITUNG = "stichleitung"
    UNBEKANNT = "unbekannt"

class ConnectionType(str, Enum):
    EINPHASIG = "einphasig"
    DREIPHASIG = "dreiphasig"

class FeedInChar(str, Enum):
    KONSTANT = "konstant"
    VOLATIL = "volatil"

class QRegulation(str, Enum):
    COS_PHI_CONST = "cos_phi_const"
    Q_U = "Q(U)"
    Q_P = "Q(P)"
    KEINE = "keine"

class UserProfile(str, Enum):
    PROJEKTIERER = "projektierer"
    PARKBETREIBER = "parkbetreiber"
    NETZBETREIBER = "netzbetreiber"
    INVESTOR = "investor"

class ConfidenceLevel(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ProjectData(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=200)
    company: str = Field(..., min_length=1, max_length=200)
    plz: str = Field(..., pattern=r"^\d{5}$")
    ort: Optional[str] = None
    strasse: Optional[str] = None
    flurstueck: Optional[str] = None
    bundesland: Optional[str] = None
    user_profile: UserProfile = UserProfile.PROJEKTIERER

class PlantData(BaseModel):
    project_type: ProjectType
    p_max_kw: float = Field(..., gt=0)
    cos_phi: float = Field(default=0.95, ge=0.8, le=1.0)
    q_regulation: QRegulation = QRegulation.COS_PHI_CONST
    connection_type: ConnectionType = ConnectionType.DREIPHASIG
    feed_in_char: FeedInChar = FeedInChar.VOLATIL
    p_feed_in_kw: Optional[float] = Field(default=None, ge=0)
    p_consumption_kw: Optional[float] = Field(default=None, ge=0)
    storage_kwh: Optional[float] = Field(default=None, ge=0)
    gleichzeitigkeitsfaktor: float = Field(default=0.9, ge=0.0, le=1.0)
    has_frt: Optional[bool] = None
    has_remote_control: Optional[bool] = None

    @validator("p_feed_in_kw", always=True)
    def default_feed_in(cls, v, values):
        if v is None and "p_max_kw" in values:
            return values["p_max_kw"] * 0.95
        return v

    @validator("p_consumption_kw", always=True)
    def default_consumption(cls, v, values):
        if v is None and "p_max_kw" in values:
            return values["p_max_kw"] * 0.05
        return v

class GridData(BaseModel):
    voltage_level: VoltageLevel
    grid_topology: GridTopology = GridTopology.UNBEKANNT
    sk_mva: Optional[float] = Field(default=None, gt=0)
    sk_mva_min: Optional[float] = Field(default=None, gt=0)
    rx_ratio: Optional[float] = Field(default=None, gt=0)
    cable_type: Optional[str] = None
    cable_length_km: Optional[float] = Field(default=None, gt=0)
    cable_temp_c: float = Field(default=20.0, ge=-20, le=90)
    trafo_s_mva: Optional[float] = Field(default=None, gt=0)
    trafo_uk_percent: Optional[float] = Field(default=None, gt=0, le=25)
    trafo_count: int = Field(default=1, ge=1, le=10)
    existing_load_kw: float = Field(default=0, ge=0)
    existing_feed_in_kw: float = Field(default=0, ge=0)
    existing_cos_phi: float = Field(default=0.95, ge=0.8, le=1.0)

class CostDataCustom(BaseModel):
    tiefbau_eur_m: Optional[float] = None
    kabel_eur_m: Optional[float] = None
    trafostation_eur: Optional[float] = None
    schaltanlage_eur: Optional[float] = None
    planung_eur: Optional[float] = None
    bkz_eur: Optional[float] = None

class VNBConfig(BaseModel):
    max_auslastung: float = Field(default=0.70, ge=0.1, le=1.5)
    max_delta_u: float = Field(default=0.03, ge=0.01, le=0.10)
    min_sk_sn: float = Field(default=20.0, ge=1.0, le=100.0)
    max_leistung_nvp_kw: Optional[float] = None
    speicher_prio: bool = True
    netzdienlichkeit_bonus: bool = True

class GridCheckInput(BaseModel):
    project: ProjectData
    plant: PlantData
    grid: GridData
    costs: Optional[CostDataCustom] = None
    vnb_config: Optional[VNBConfig] = None


class MetricResult(BaseModel):
    name: str
    value: float
    unit: str
    limit: Optional[float] = None
    status: Literal["ok", "warnung", "kritisch"]
    detail: str

class N1Result(BaseModel):
    passed: bool
    reasons: List[str]
    topology_note: str

class CostEstimate(BaseModel):
    trasse_eur: float
    station_eur: float
    planung_eur: float
    total_eur: float
    is_custom: bool
    confidence: ConfidenceLevel

class Recommendation(BaseModel):
    category: Literal["ok", "warnung", "kritisch", "info"]
    text: str

class ScenarioResult(BaseModel):
    name: str
    delta_u_percent: float
    auslastung_percent: float
    status: Literal["ok", "warnung", "kritisch"]

class PlausibilityWarning(BaseModel):
    field: str
    message: str
    severity: Literal["hinweis", "warnung", "fehler"]

class SubScores(BaseModel):
    capacity: int = Field(ge=0, le=100)
    voltage: int = Field(ge=0, le=100)
    short_circuit: int = Field(ge=0, le=100)
    security: int = Field(ge=0, le=100)
    data_quality: int = Field(ge=0, le=100)

class ShortCircuitResult(BaseModel):
    ik_max_a: float
    ik_min_a: float
    sk_sn_ratio: float
    ik_ib_ratio: float
    status: Literal["ok", "warnung", "kritisch"]
    detail: str

class ProfileSpecificOutput(BaseModel):
    profile: str
    sections: Dict[str, object]

class GridCheckOutput(BaseModel):
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    engine_version: str = "2.1.0"
    confidence: ConfidenceLevel
    score: int = Field(ge=0, le=100)
    sub_scores: SubScores
    status: Literal["ok", "bedingt", "kritisch"]
    status_text: str
    hard_override: bool = False
    hard_override_reason: Optional[str] = None
    plausibility_warnings: List[PlausibilityWarning]
    data_quality_note: str
    metrics: List[MetricResult]
    short_circuit: ShortCircuitResult
    scenarios: List[ScenarioResult]
    n1: N1Result
    costs: CostEstimate
    recommendations: List[Recommendation]
    netzrueckwirkung_anteil: float
    netzrueckwirkung_status: Literal["ok", "hinweis", "pruefung", "kritisch"]
    q_max_kvar: float
    s_max_kva: float
    applicable_tar: str
    vnb_decision: Optional[str] = None
    vnb_prio_score: Optional[int] = None
    profile_output: Optional[ProfileSpecificOutput] = None
    input_snapshot: dict
