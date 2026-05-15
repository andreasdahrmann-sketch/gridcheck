# backend/api/analyze_v2.py
"""
GridCheck v2 - Diagnose-Endpoint
- Strikte Eingabevalidierung via Pydantic
- Ruft direkt die neue Engine berechne_netzanschluss()
- Ergaenzt hybride Projekt-, Speicher-, Umwelt- und Stakeholder-Inputs
- Liefert das vollstaendige Engine-Output-Dict (kein Informationsverlust)
"""

from datetime import datetime
from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_csrf
from core.rate_limit import enforce_scoped_rate_limit
from db.database import get_db
from db.models import User
from services import project_service
from services.billing_service import (
    build_billing_overview,
    ensure_analysis_allowed,
    enforce_package_rights,
    list_analysis_history,
    package_access_context,
    persist_completed_analysis_run,
    persist_failed_analysis_run,
)
from services.visibility_service import derive_stakeholder_path, sanitize_analysis_result
from services.v1_analysis_service import run_v1_analysis

router_v2 = APIRouter(tags=["analyse"])


class ProjectComponentPayload(BaseModel):
    component_type: Literal[
        "pv",
        "wind",
        "battery",
        "load",
        "charging",
        "heat_pump",
        "electrolyzer",
        "substation",
        "other",
    ]
    capacity_kw: float = Field(..., gt=0, le=2_000_000)
    label: str | None = Field(default=None, max_length=120)
    energy_kwh: float | None = Field(default=None, gt=0, le=20_000_000)
    max_export_kw: float | None = Field(default=None, ge=0, le=2_000_000)
    max_import_kw: float | None = Field(default=None, ge=0, le=2_000_000)
    controllable: bool = False


class NetzanschlusspunktPayload(BaseModel):
    max_export_kw: float | None = Field(default=None, ge=0, le=2_000_000)
    max_import_kw: float | None = Field(default=None, ge=0, le=2_000_000)
    export_limit_mode: Literal["none", "fixed", "dynamic", "schedule"] = "none"
    own_transformer: bool = False
    own_substation: bool = False
    own_switchgear: bool = False
    remote_metering_ready: bool = False
    preferred_connection_note: str | None = Field(default=None, max_length=500)


class StorageProfilePayload(BaseModel):
    has_storage: bool = False
    operation_mode: Literal["market", "hybrid", "partial_grid_support", "grid_support", "unknown"] = "unknown"
    power_kw: float | None = Field(default=None, gt=0, le=2_000_000)
    energy_kwh: float | None = Field(default=None, gt=0, le=20_000_000)
    grid_support_services: list[str] = Field(default_factory=list)
    reactive_power_capable: bool = False
    remote_control_capable: bool = False
    schedule_based_dispatch: bool = False
    dynamic_export_limit: bool = False
    peak_shaving: bool = False
    curtailment_ready: bool = False
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_consistency(self) -> "StorageProfilePayload":
        if self.has_storage and self.power_kw is None and self.energy_kwh is None:
            raise ValueError(
                "Wenn Speicher aktiviert ist, muss mindestens Leistung oder Energie angegeben werden."
            )
        return self


class EnvironmentalRoutePayload(BaseModel):
    route_length_km: float | None = Field(default=None, ge=0, le=500)
    crossings_count: int | None = Field(default=None, ge=0, le=500)
    protected_area_touch: bool = False
    water_protection_area: bool = False
    forest_crossing: bool = False
    third_party_land: bool = False
    noise_sensitive_area: bool = False
    route_complexity: Literal["niedrig", "mittel", "hoch", "unbekannt"] = "unbekannt"
    mitigation_measures: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)


class StakeholderContextPayload(BaseModel):
    customer_type: Literal["projektierer", "speicherbetreiber", "netzbetreiber", "investor"] | None = None
    priority_focus: Literal["kosten", "zeit", "netz", "genehmigung", "balanced"] = "balanced"
    investor_relevant: bool = False
    netzbetreiber_dialog_needed: bool = False


class ProjectLocationPayload(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    address_hint: str | None = Field(default=None, max_length=300)
    area_radius_m: float | None = Field(default=None, ge=0, le=50_000)

    @model_validator(mode="after")
    def validate_coordinates(self) -> "ProjectLocationPayload":
        if (self.latitude is None) ^ (self.longitude is None):
            raise ValueError(
                "Standortkoordinaten duerfen nur gemeinsam mit Breiten- und Laengengrad gesetzt werden."
            )
        return self


class N1TransformerPayload(BaseModel):
    label: str | None = Field(default=None, max_length=80)
    sn_mva: float = Field(..., gt=0, le=1_000)
    belastung_aktuell_mw: float = Field(default=0, ge=0, le=1_000)


class N1FeederPayload(BaseModel):
    label: str | None = Field(default=None, max_length=80)
    i_max_a: float | None = Field(default=None, gt=0, le=20_000)
    belastung_aktuell_a: float | None = Field(default=None, ge=0, le=20_000)
    reserve_n1_a: float | None = Field(default=None, ge=0, le=20_000)
    reserve_i_a: float | None = Field(default=None, ge=0, le=20_000)
    primary: bool = False
    verfuegbar_im_n1: bool = True
    koppelbar: bool = True
    datenquelle: Literal["unknown", "planner_assumption", "user_estimate", "dso_verified"] = "unknown"


class UmspannwerkPayload(BaseModel):
    datenquelle: Literal["unknown", "planner_assumption", "user_estimate", "dso_verified"] = "unknown"
    trafos: list[N1TransformerPayload] = Field(default_factory=list)
    abgaenge: list[N1FeederPayload] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    requested_offer_id: str | None = Field(default=None, max_length=80)

    # Pflichtfelder
    nennspannung: float = Field(..., gt=0, le=380, description="kV")
    leistung_mw: float = Field(..., gt=0, le=2000, description="MW")
    leitungstyp: str = Field(..., description="z.B. NA2XS2Y240, NAYY150")
    entfernung_km: float = Field(..., gt=0, le=500)
    anschlussart: Literal["Einspeisung", "Entnahme", "Speicher"]

    # Optionaler Basiskontext
    anlagentyp: str | None = Field(default="PV")
    plz: str | None = Field(default=None)
    ort: str | None = Field(default=None)
    standort: str | None = Field(default=None, max_length=300)
    antragsteller: str | None = Field(default=None)
    projektreife: Literal["idee", "planung", "genehmigt", "baubereit"] | None = None
    foerderfrist: str | None = None
    baugenehmigung_vorhanden: bool = False
    cos_phi: float | None = Field(default=0.95, ge=0.8, le=1.0)
    parallele_systeme: int | None = Field(default=1, ge=1, le=4)
    redundanz: bool | None = Field(default=False)
    p_kw: float | None = Field(default=None, gt=0)
    bestehende_einspeisung_mw: float | None = Field(default=0, ge=0)
    sk_mva: float | None = Field(default=None, gt=0)
    trafo_s_mva: float | None = Field(default=None, gt=0)
    uk_prozent: float | None = Field(default=None, gt=0, le=20)
    trafo_uk_prozent: float | None = Field(default=None, gt=0, le=20)
    bestand_auslastung_prozent: float | None = Field(default=0, ge=0, le=100)
    temperatur_c: float | None = Field(default=20, ge=-30, le=80)
    topologie: Literal[
        "stich",
        "stich_mit_notverbindung",
        "ring",
        "ring_offen",
        "ring_geschlossen",
        "doppelstich",
        "vermascht",
        "unbekannt",
    ] = "unbekannt"
    restkapazitaet_ms_mva: float | None = Field(default=None, gt=0, le=10_000)
    umschaltzeit_min: float | None = Field(default=None, ge=0, le=1_440)
    n1_datengrundlage: Literal["unknown", "planner_assumption", "user_estimate", "dso_verified"] = "unknown"
    umspannwerk: UmspannwerkPayload | None = None

    # Additive Erweiterungen fuer Hybrid-/Stakeholder-Logik
    project_components: list[ProjectComponentPayload] = Field(default_factory=list)
    netzanschlusspunkt: NetzanschlusspunktPayload | None = None
    storage_profile: StorageProfilePayload | None = None
    environmental_route: EnvironmentalRoutePayload | None = None
    stakeholder_context: StakeholderContextPayload | None = None
    project_location: ProjectLocationPayload | None = None

    @field_validator(
        "requested_offer_id",
        "anlagentyp",
        "plz",
        "ort",
        "standort",
        "antragsteller",
        "foerderfrist",
        "leitungstyp",
        mode="before",
    )
    @classmethod
    def strip_string_fields(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_consistency(self) -> "AnalyzeRequest":
        if self.plz is not None and not self.plz.isdigit():
            raise ValueError("PLZ muss nur Ziffern enthalten.")
        if self.plz is not None and len(self.plz) != 5:
            raise ValueError("PLZ muss genau 5 Ziffern haben.")
        if not self.leitungstyp:
            raise ValueError("Leitungstyp darf nicht leer sein.")
        if self.stakeholder_context and self.stakeholder_context.customer_type == "investor":
            self.stakeholder_context.investor_relevant = True
        if self.n1_datengrundlage == "dso_verified":
            has_verified_basis = any(
                value is not None
                for value in (
                    self.sk_mva,
                    self.trafo_s_mva,
                    self.restkapazitaet_ms_mva,
                )
            ) or (
                self.umspannwerk is not None
                and (len(self.umspannwerk.trafos) > 0 or len(self.umspannwerk.abgaenge) > 0)
            )
            if not has_verified_basis:
                raise ValueError(
                    "VNB-verifiziert darf nur genutzt werden, wenn konkrete Netz- oder Umspannwerksdaten vorliegen."
                )
        return self


class AnalysisHistoryItemResponse(BaseModel):
    id: int
    project_id: int | None
    project_name: str | None
    source: str
    status: str
    score: float | None
    decision_code: str | None
    revision_hash: str | None
    offer_id: str | None
    package_scope: str
    usage_bucket: str
    entitlement_id: int | None
    billing_category: str
    free_quota_consumed: bool
    created_at: datetime


@router_v2.post("/analyze", response_model=None)
def analyze_v2(
    request: Request,
    req: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> Dict[str, Any]:
    """
    Vollwertige Netzanschluss-Diagnose.
    Liefert das komplette Engine-Output-Dict.
    HTTP 422 bei fachlichen Eingabefehlern.
    """
    enforce_scoped_rate_limit(
        "analysis:interactive",
        request=request,
        current_user=current_user,
        user_limit=12,
        ip_limit=40,
        window_seconds=300,
        message="Zu viele Analyse-Anfragen",
        hint="Bitte kurz warten und die Analyse danach erneut starten.",
    )
    ensure_analysis_allowed(db, current_user)
    request_payload = req.model_dump(exclude_none=False)
    project_id = request_payload.get("project_id")
    access_context = package_access_context(
        db,
        current_user,
        requested_offer_id=request_payload.get("requested_offer_id"),
    )
    stakeholder_path = derive_stakeholder_path(request_payload, fallback_user_role=current_user.role)
    if project_id is not None:
        _, _, stakeholder_path = project_service.get_project_access_context(
            db,
            current_user,
            int(project_id),
            require_write=True,
        )
    eingabe = req.model_dump(exclude_none=False, exclude={"project_id"})
    eingabe = enforce_package_rights(eingabe, access_context)
    source = "project" if project_id is not None else "interactive"

    # 1) Berechnung
    try:
        result = run_v1_analysis(eingabe)
    except Exception as e:
        persist_failed_analysis_run(
            db,
            current_user,
            request_payload=request_payload,
            error_payload={"code": "ENGINE_ERROR", "message": str(e)},
            source=source,
            status="engine_failed",
            project_id=project_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ENGINE_ERROR",
                "message": f"Engine-Fehler: {e}",
                "hint": "Bitte Eingaben pruefen oder Backend-Logs einsehen.",
            },
        )

    # 2) Fachliche Validierungsfehler -> 422
    if result.get("status") == "FEHLER":
        persist_failed_analysis_run(
            db,
            current_user,
            request_payload=request_payload,
            error_payload=result,
            source=source,
            status="validation_failed",
            project_id=project_id,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "status": "FEHLER",
                "fehler": result.get("fehler", []),
                "warnungen": result.get("warnungen", []),
            },
        )

    run = persist_completed_analysis_run(
        db,
        current_user,
        request_payload=request_payload,
        result_payload=result,
        source=source,
        project_id=project_id,
        access_context=access_context,
    )
    response_payload = {
        **result,
        "history": {"analysis_run_id": run.id},
        "billing_access": {
            "offer_id": access_context["offer_id"],
            "package_scope": access_context["package_scope"],
            "usage_bucket": access_context["usage_bucket"],
            "report_scope": access_context["report_scope"],
            "ops_followup_required": access_context["ops_followup_required"],
        },
        "billing": build_billing_overview(db, current_user),
    }
    return sanitize_analysis_result(response_payload, stakeholder_path=stakeholder_path)


@router_v2.get("/analysis/history", response_model=list[AnalysisHistoryItemResponse])
def analysis_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return list_analysis_history(db, current_user, limit=limit)
