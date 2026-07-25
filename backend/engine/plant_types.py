"""
Plant-type configuration for Projektierer screening (authoritative, Pydantic v2).

Frontend mirrors: frontend/lib/schemas/plant-types.ts
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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
VoltageLevelKey = Literal["low", "medium", "high"]
ProjectTypeLiteral = Literal["generation", "consumption", "storage", "mixed"]
PowerFactorSource = Literal["nutzer", "plant_default"]

REACTIVE_POWER_SCREENING_KW = 135.0
EEG_REMOTE_CONTROL_KW = 25.0
EEG_DIRECT_MARKETING_KW = 100.0

PLANT_TYPE_LEGACY_ALIASES: dict[str, PlantTypeLiteral] = {
    "hybrid": "hybrid_pv_bess",
    "hybrid_pv_bess": "hybrid_pv_bess",
    "solar": "pv",
    "battery": "bess",
    "batterie": "bess",
    "speicher": "bess",
    "bhkw": "chp",
    "load": "consumption",
    "verbrauch": "consumption",
    "entnahme": "consumption",
}


class PlantType(str, Enum):
    PV = "pv"
    WIND = "wind"
    BESS = "bess"
    HYBRID_PV_BESS = "hybrid_pv_bess"
    CHP = "chp"
    HYDRO = "hydro"
    CONSUMPTION = "consumption"


class PowerFactorRange(BaseModel):
    model_config = ConfigDict(frozen=True)

    min: float = Field(ge=0.5, le=1.0)
    max: float = Field(ge=0.5, le=1.0)


class PlantTypeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    label_en: str
    default_power_factor: float = Field(ge=0.5, le=1.0)
    power_factor_range: PowerFactorRange
    default_simultaneity_factor: float = Field(ge=0.0, le=1.0)
    simultaneity_note: str
    reactive_power_capable: bool
    default_reactive_power_mode: ReactivePowerMode
    has_dc_side: bool
    default_norm_reference: dict[VoltageLevelKey, str]
    feed_in_profile_note: str
    project_type: ProjectTypeLiteral

    # Backward-compatible accessors used by older engine code
    @property
    def label_de(self) -> str:
        return self.label

    @property
    def default_cos_phi(self) -> float:
        return self.default_power_factor

    @property
    def simultaneity_factor(self) -> float:
        return self.default_simultaneity_factor

    @property
    def has_dc_ac(self) -> bool:
        return self.has_dc_side

    def norm_ref(self, voltage_level: VoltageLevelKey = "medium") -> str:
        return self.default_norm_reference.get(
            voltage_level, self.default_norm_reference["medium"]
        )


def _norm_refs(
    low: str,
    medium: str,
    high: str,
) -> dict[VoltageLevelKey, str]:
    return {"low": low, "medium": medium, "high": high}


PLANT_TYPE_CONFIG: dict[PlantType, PlantTypeConfig] = {
    PlantType.PV: PlantTypeConfig(
        label="Photovoltaik",
        label_en="Photovoltaics",
        default_power_factor=0.9,
        power_factor_range=PowerFactorRange(min=0.85, max=1.0),
        default_simultaneity_factor=0.85,
        simultaneity_note=(
            "PV-Einspeiseprofil tagsÃ¼ber â€” volle AC-Nennleistung nicht dauerhaft gleichzeitig am NVP."
        ),
        reactive_power_capable=True,
        default_reactive_power_mode="fixed_cos_phi",
        has_dc_side=True,
        default_norm_reference=_norm_refs(
            "VDE-AR-N 4105:2018-11",
            "VDE-AR-N 4110:2018-11",
            "VDE-AR-N 4120:2018-11",
        ),
        feed_in_profile_note="Tagesgang / Sonneneinstrahlung â€” Einspeise nicht 24/7 auf Nennleistung.",
        project_type="generation",
    ),
    PlantType.WIND: PlantTypeConfig(
        label="Windenergie",
        label_en="Wind power",
        default_power_factor=0.9,
        power_factor_range=PowerFactorRange(min=0.85, max=1.0),
        default_simultaneity_factor=0.35,
        simultaneity_note=(
            "Wind volatil â€” Gleichzeitigkeitsfaktor 0,35 fÃ¼r konservatives Lastfluss-Screening "
            "(kein Erzeugungsgarantie-Nachweis)."
        ),
        reactive_power_capable=True,
        default_reactive_power_mode="cos_phi_p",
        has_dc_side=False,
        default_norm_reference=_norm_refs(
            "VDE-AR-N 4105:2018-11",
            "VDE-AR-N 4110:2018-11",
            "VDE-AR-N 4120:2018-11",
        ),
        feed_in_profile_note="Volatile Einspeise â€” volle Nennleistung selten gleichzeitig.",
        project_type="generation",
    ),
    PlantType.BESS: PlantTypeConfig(
        label="Batteriespeicher",
        label_en="Battery storage",
        default_power_factor=0.92,
        power_factor_range=PowerFactorRange(min=0.9, max=1.0),
        default_simultaneity_factor=0.9,
        simultaneity_note=(
            "Speicher betrieblich begrenzt â€” Gleichzeitigkeit hoch, aber nicht 1,0 ohne Fahrplan."
        ),
        reactive_power_capable=True,
        default_reactive_power_mode="bidirectional",
        has_dc_side=False,
        default_norm_reference=_norm_refs(
            "VDE-AR-N 4105:2018-11",
            "VDE-AR-N 4110:2018-11",
            "VDE-AR-N 4120:2018-11",
        ),
        feed_in_profile_note="Steuerbar / netzdienlich mÃ¶glich â€” Q-FÃ¤higkeit projektspezifisch.",
        project_type="storage",
    ),
    PlantType.HYBRID_PV_BESS: PlantTypeConfig(
        label="Hybrid (PV + Speicher)",
        label_en="Hybrid PV + BESS",
        default_power_factor=0.98,
        power_factor_range=PowerFactorRange(min=0.9, max=1.0),
        default_simultaneity_factor=0.88,
        simultaneity_note="Kombination Erzeugung und Speicher â€” konservativer Mittelwert fÃ¼r Screening.",
        reactive_power_capable=True,
        default_reactive_power_mode="bidirectional",
        has_dc_side=True,
        default_norm_reference=_norm_refs(
            "VDE-AR-N 4105:2018-11",
            "VDE-AR-N 4110:2018-11",
            "VDE-AR-N 4120:2018-11",
        ),
        feed_in_profile_note="PV-Tagesgang plus steuerbarer Speicher â€” VNB-Abstimmung zentral.",
        project_type="mixed",
    ),
    PlantType.CHP: PlantTypeConfig(
        label="Kraft-WÃ¤rme-Kopplung",
        label_en="Combined heat and power",
        default_power_factor=0.95,
        power_factor_range=PowerFactorRange(min=0.9, max=1.0),
        default_simultaneity_factor=0.9,
        simultaneity_note="BHKW oft grundlastnah â€” Gleichzeitigkeit hoch, WÃ¤rmegefÃ¼hrter Betrieb beachten.",
        reactive_power_capable=True,
        default_reactive_power_mode="fixed_cos_phi",
        has_dc_side=False,
        default_norm_reference=_norm_refs(
            "VDE-AR-N 4105:2018-11",
            "VDE-AR-N 4110:2018-11",
            "VDE-AR-N 4120:2018-11",
        ),
        feed_in_profile_note="Grundlast-/Regelbetrieb â€” Einspeiseplan mit WÃ¤rmenutzung abstimmen.",
        project_type="generation",
    ),
    PlantType.HYDRO: PlantTypeConfig(
        label="Wasserkraft",
        label_en="Hydropower",
        default_power_factor=0.9,
        power_factor_range=PowerFactorRange(min=0.85, max=1.0),
        default_simultaneity_factor=0.8,
        simultaneity_note=(
            "Laufwasser/reguliert unterschiedlich â€” Faktor 0,8 als konservatives Screening ohne Pegeldaten."
        ),
        reactive_power_capable=True,
        default_reactive_power_mode="q_setpoint",
        has_dc_side=False,
        default_norm_reference=_norm_refs(
            "VDE-AR-N 4105:2018-11",
            "VDE-AR-N 4110:2018-11",
            "VDE-AR-N 4120:2018-11",
        ),
        feed_in_profile_note="Regelbar je nach Anlagentyp â€” Wasserrecht und VNB-Vorgaben maÃŸgeblich.",
        project_type="generation",
    ),
    PlantType.CONSUMPTION: PlantTypeConfig(
        label="Verbrauch / Last",
        label_en="Consumption / load",
        default_power_factor=0.95,
        power_factor_range=PowerFactorRange(min=0.85, max=1.0),
        default_simultaneity_factor=1.0,
        simultaneity_note="Verbraucheranschluss â€” Gleichzeitigkeit 1,0 fÃ¼r Einzelanschluss-Screening.",
        reactive_power_capable=False,
        default_reactive_power_mode="fixed_cos_phi",
        has_dc_side=False,
        default_norm_reference=_norm_refs(
            "VDE-AR-N 4100:2019-11",
            "VDE-AR-N 4110:2018-11",
            "VDE-AR-N 4120:2018-11",
        ),
        feed_in_profile_note="Bezugslast â€” kein EEG-Einspeisemanagement.",
        project_type="consumption",
    ),
}


class PlantContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    plant_type: PlantType
    config: PlantTypeConfig
    ac_kw: float
    dc_kwp: float | None = None
    overbuild_ratio: float | None = None
    screening_power_kw: float
    power_factor: float
    power_factor_source: PowerFactorSource
    simultaneity_factor: float
    reactive_power_mode: ReactivePowerMode
    feed_in_management_class: FeedInManagementClass
    norm_reference: str

    @property
    def cos_phi(self) -> float:
        return self.power_factor

    @property
    def cos_phi_source(self) -> PowerFactorSource:
        return self.power_factor_source


def _f(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_plant_type(raw: str | None) -> PlantType | None:
    key = str(raw or "").strip().lower()
    if not key:
        return None
    if key in PLANT_TYPE_LEGACY_ALIASES:
        key = PLANT_TYPE_LEGACY_ALIASES[key]
    try:
        return PlantType(key)
    except ValueError:
        return None


def map_legacy_anlagentyp(raw: str | None) -> PlantType:
    key = str(raw or "").strip().lower()
    mapped = normalize_plant_type(key)
    if mapped:
        return mapped
    legacy = {
        "pv": PlantType.PV,
        "waermepumpe": PlantType.CONSUMPTION,
        "ladepark": PlantType.CONSUMPTION,
    }
    return legacy.get(key, PlantType.PV)


def infer_plant_type_from_eingabe(eingabe: dict[str, Any]) -> PlantType:
    explicit = normalize_plant_type(str(eingabe.get("plant_type") or ""))
    if explicit:
        return explicit

    mapped = map_legacy_anlagentyp(str(eingabe.get("anlagentyp") or ""))
    components = eingabe.get("project_components") or []
    if isinstance(components, list) and components:
        types = {
            str(item.get("component_type") or "").strip().lower()
            for item in components
            if isinstance(item, dict)
        }
        has_battery = "battery" in types or "bess" in types
        has_gen = bool(types & {"pv", "wind", "solar"})
        if has_battery and has_gen:
            return PlantType.HYBRID_PV_BESS
        if has_battery:
            return PlantType.BESS
        if "wind" in types:
            return PlantType.WIND
        if "pv" in types or "solar" in types:
            return PlantType.PV

    anschluss = str(eingabe.get("anschlussart") or "").strip()
    if anschluss == "Entnahme":
        return PlantType.CONSUMPTION
    if anschluss == "Speicher":
        return PlantType.BESS
    return mapped


def classify_feed_in_management(power_kw: float) -> FeedInManagementClass:
    if power_kw < EEG_REMOTE_CONTROL_KW:
        return "none"
    if power_kw < EEG_DIRECT_MARKETING_KW:
        return "remote_control"
    return "direct_marketing"


def resolve_reactive_power_mode(
    eingabe: dict[str, Any],
    config: PlantTypeConfig,
    ac_kw: float,
) -> ReactivePowerMode:
    explicit = str(eingabe.get("reactive_power_mode") or "").strip().lower()
    if explicit in (
        "fixed_cos_phi",
        "cos_phi_p",
        "q_u",
        "q_setpoint",
        "bidirectional",
    ):
        return explicit  # type: ignore[return-value]
    if ac_kw > REACTIVE_POWER_SCREENING_KW and config.reactive_power_capable:
        if config.default_reactive_power_mode == "fixed_cos_phi":
            return "q_u"
        return config.default_reactive_power_mode
    return config.default_reactive_power_mode


def resolve_plant_context(
    eingabe: dict[str, Any],
    *,
    voltage_level: VoltageLevelKey = "medium",
) -> PlantContext:
    plant_type = infer_plant_type_from_eingabe(eingabe)
    config = PLANT_TYPE_CONFIG[plant_type]

    ac_kw = _f(eingabe.get("ac_kw")) or _f(eingabe.get("ac_power_kw"))
    p_mw = _f(eingabe.get("leistung_mw"))
    p_kw_legacy = _f(eingabe.get("p_kw"))
    if ac_kw is None and p_mw is not None:
        ac_kw = p_mw * 1000.0
    if ac_kw is None and p_kw_legacy is not None:
        ac_kw = p_kw_legacy
    if ac_kw is None:
        ac_kw = 1.0

    dc_kwp = _f(eingabe.get("dc_kwp")) or _f(eingabe.get("dc_power_kwp"))
    if dc_kwp is None and config.has_dc_side:
        dc_kwp = _f(eingabe.get("dc_kwp_peak"))

    overbuild: float | None = None
    if dc_kwp is not None and ac_kw > 0:
        overbuild = round(dc_kwp / ac_kw, 3)

    explicit_pf = _f(eingabe.get("cos_phi"))
    if explicit_pf is None:
        explicit_pf = _f(eingabe.get("power_factor"))

    # Absolute MVP bounds (frontend validates 0.8–1.0). An explicit value in this
    # band must never be silently replaced by a plant default: for PV+Einspeisung the
    # default jumps to 1.0, which understates Scheinleistung (anti-conservative) and
    # contradicts the value shown/edited in the form. Plant-type range remains
    # advisory metadata; cos_phi_known is documentation-only and must not discard
    # a numeric cos φ that was actually sent.
    _ABS_PF_MIN = 0.8
    _ABS_PF_MAX = 1.0
    if explicit_pf is not None and _ABS_PF_MIN <= explicit_pf <= _ABS_PF_MAX:
        power_factor = explicit_pf
        pf_source: PowerFactorSource = "nutzer"
    else:
        power_factor = config.default_power_factor
        if plant_type == PlantType.PV and str(eingabe.get("anschlussart") or "").strip().lower() == "einspeisung":
            power_factor = 1.0
        pf_source = "plant_default"

    simultaneity = config.default_simultaneity_factor
    if plant_type == PlantType.CONSUMPTION:
        screening_kw = ac_kw
    else:
        screening_kw = ac_kw * simultaneity

    feed_class = classify_feed_in_management(ac_kw)
    reactive_mode = resolve_reactive_power_mode(eingabe, config, ac_kw)

    vl: VoltageLevelKey = voltage_level
    if plant_type == PlantType.CONSUMPTION and vl == "low":
        norm_ref = config.default_norm_reference["low"]
    else:
        norm_ref = config.norm_ref(vl)

    return PlantContext(
        plant_type=plant_type,
        config=config,
        ac_kw=ac_kw,
        dc_kwp=dc_kwp,
        overbuild_ratio=overbuild,
        screening_power_kw=round(screening_kw, 3),
        power_factor=round(power_factor, 4),
        power_factor_source=pf_source,
        simultaneity_factor=simultaneity,
        reactive_power_mode=reactive_mode,
        feed_in_management_class=feed_class,
        norm_reference=norm_ref,
    )


def plant_type_config_for_export() -> list[dict[str, Any]]:
    """JSON-serializable catalog for frontend mirror / docs."""
    out: list[dict[str, Any]] = []
    for pt, cfg in PLANT_TYPE_CONFIG.items():
        out.append(
            {
                "id": pt.value,
                **cfg.model_dump(),
            }
        )
    return out
