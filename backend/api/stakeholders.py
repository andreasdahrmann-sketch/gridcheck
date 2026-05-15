# C:\Users\andre\gridcheck\backend\api\stakeholders.py
# Stakeholder-spezifische Endpoints (Endkunde / Projektierer / Netzbetreiber)
# Nutzt intern berechne_netzcheck wie /api/analyze, liefert aber zielgruppen-
# gerechte Inputs und Outputs.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from core.auth import get_current_user, require_csrf
from db.database import get_db
from db.models import User
from services.stakeholder_service import (
    commit_endkunde_transaction,
    commit_projektierer_transaction,
    run_endkunde_check,
    run_netzbetreiber_check,
    run_projektierer_check,
)

router = APIRouter(prefix="/stakeholder", tags=["Stakeholder"])


def _require_stakeholder_access(current_user: User, *, allowed_roles: set[str], route_name: str) -> User:
    normalized_role = str(current_user.role or "").strip().lower()
    if normalized_role == "admin" or normalized_role in allowed_roles:
        return current_user
    raise HTTPException(
        status_code=403,
        detail={
            "code": "STAKEHOLDER_FORBIDDEN",
            "message": f"Der Stakeholder-Pfad {route_name} ist fuer diese Rolle nicht freigeschaltet.",
            "hint": "Bitte ein Konto mit passender Stakeholder-Rolle verwenden.",
        },
    )


# ============================================================
#  1) ENDKUNDE / INVESTOR  — minimal Input, simple Output
# ============================================================

class EndkundeRequest(BaseModel):
    plz: str = Field(..., min_length=4, max_length=5)
    anlagentyp: str = Field("pv", description="pv | wind | bhkw | speicher | last")
    leistung_kw: float = Field(..., gt=0)
    spannungsebene: str = Field("0.4", description="0.4 | 20 | 110")


class EndkundeResponse(BaseModel):
    project_id: int
    tendenz: str                # "machbar" | "bedingt_machbar" | "schwierig"
    ampel: str                  # "gruen" | "gelb" | "rot"
    klartext: str               # 1-2 Saetze fuer Laien
    grobkosten_eur_min: int
    grobkosten_eur_max: int
    naechste_schritte: List[str]


def _tendenz_from_score(score: float) -> tuple:
    if score >= 80:
        return "machbar", "gruen"
    if score >= 50:
        return "bedingt_machbar", "gelb"
    return "schwierig", "rot"


def _grobkosten(leistung_kw: float, spannung_kv: float, score: float) -> tuple:
    # grobe Hausnummer: NS 150-300 EUR/kW, MS 200-500, HS 400-900
    # bei niedrigem Score Aufschlag (Netzausbau noetig)
    if spannung_kv <= 0.4:
        base_min, base_max = 150, 300
    elif spannung_kv <= 20:
        base_min, base_max = 200, 500
    else:
        base_min, base_max = 400, 900
    aufschlag = 1.0 if score >= 80 else (1.5 if score >= 50 else 2.5)
    lo = int(leistung_kw * base_min * aufschlag)
    hi = int(leistung_kw * base_max * aufschlag)
    return lo, hi


@router.post("/endkunde", response_model=EndkundeResponse)
def check_endkunde(
    req: EndkundeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    actor = _require_stakeholder_access(
        current_user,
        allowed_roles={"endkunde", "projektierer", "netzbetreiber"},
        route_name="endkunde",
    )
    service_data = run_endkunde_check(db, req.model_dump(), actor)
    project_id = service_data["project_id"]
    result = service_data["result"]
    spannung_kv = float(req.spannungsebene)

    tendenz, ampel = _tendenz_from_score(result["score"])
    lo, hi = _grobkosten(req.leistung_kw, spannung_kv, result["score"])

    if ampel == "gruen":
        klartext = (f"Ihr Vorhaben mit {req.leistung_kw:.0f} kW in {req.plz} ist "
                    f"nach erster Pruefung sehr wahrscheinlich realisierbar.")
        schritte = ["Fachplaner beauftragen", "Netzanschlussbegehren stellen",
                    "Anlagenzertifikat einholen"]
    elif ampel == "gelb":
        klartext = (f"Ihr Vorhaben ist moeglich, erfordert aber technische Zusatz"
                    f"massnahmen (z.B. Blindleistungsregelung oder Leistungs"
                    f"begrenzung).")
        schritte = ["Detailpruefung durch Projektierer", "Variantenrechnung",
                    "Vorgespraech mit Netzbetreiber"]
    else:
        klartext = (f"In der aktuellen Konfiguration ist der Anschluss schwierig. "
                    f"Netzausbau oder reduzierte Leistung wahrscheinlich noetig.")
        schritte = ["Leistung reduzieren pruefen", "Hoehere Spannungsebene pruefen",
                    "Netzbetreiber kontaktieren"]

    commit_endkunde_transaction(
        db,
        actor=actor,
        project_id=project_id,
        req_data=req.model_dump(),
        tendenz=tendenz,
        score=result["score"],
    )

    return EndkundeResponse(
        project_id=project_id, tendenz=tendenz, ampel=ampel,
        klartext=klartext, grobkosten_eur_min=lo, grobkosten_eur_max=hi,
        naechste_schritte=schritte,
    )


# ============================================================
#  2) PROJEKTIERER  — voller Input, technische Detail-Antwort
# ============================================================

class ProjektiererRequest(BaseModel):
    projektname: str = Field(..., min_length=1)
    plz: str = Field(..., min_length=4, max_length=5)
    anlagentyp: str = "pv"
    leistung_kw: float = Field(..., gt=0)
    spannungsebene: str = "20"
    cos_phi: float = 0.95
    einspeiseart: str = "volleinspeisung"
    speicher: bool = False
    speicher_kwh: Optional[float] = None
    trafo_mva: float = 0.63
    leitungslaenge_km: float = 1.0
    leitungstyp: str = "NAYY"
    querschnitt_mm2: str = "150"
    netzverknuepfungspunkt: Optional[str] = ""
    skv_mva: Optional[float] = None
    parallelsysteme: int = 1
    eigentumsgrenze: str = "HAK"
    vorbelastung_mw: Optional[float] = 0
    netz_typ: str = "kabel"
    gewuenschte_massnahmen: List[str] = Field(
        default_factory=list,
        description="z.B. ['Q(U)', 'Curtailment_70', 'Trafo_Upgrade']"
    )


class EngpassInfo(BaseModel):
    kriterium: str
    wert: Optional[float] = None
    grenzwert: Optional[float] = None
    bewertung: str


class ProjektiererResponse(BaseModel):
    project_id: int
    score: float
    spannungsband_ok: bool
    thermische_auslastung_ok: bool
    kurzschluss_ok: bool
    n1_ok: bool
    netzebene: str
    empfehlung: str
    engpaesse: List[EngpassInfo]
    massnahmen_empfehlungen: List[str]
    details: dict


def _engpaesse(result: dict) -> List[EngpassInfo]:
    out = []
    d = result.get("details", {})
    if not result["spannungsband_ok"]:
        out.append(EngpassInfo(
            kriterium="Spannungsband",
            wert=d.get("delta_u_prozent"), grenzwert=3.0,
            bewertung="Spannungsanhebung ueberschritten (>3% NS / >2% MS)"
        ))
    if not result["thermische_auslastung_ok"]:
        out.append(EngpassInfo(
            kriterium="Thermische Auslastung",
            wert=d.get("auslastung_prozent"), grenzwert=100.0,
            bewertung="Betriebsmittel (Kabel/Trafo) ueberlastet"
        ))
    if not result["kurzschluss_ok"]:
        out.append(EngpassInfo(
            kriterium="Kurzschlussleistung",
            wert=d.get("skv_mva"), grenzwert=None,
            bewertung="SkV unzureichend"
        ))
    if not result["n1_ok"]:
        out.append(EngpassInfo(
            kriterium="N-1 Sicherheit", bewertung="Ausfall eines Betriebsmittels nicht beherrschbar"
        ))
    return out


def _massnahmen(result: dict, req: ProjektiererRequest) -> List[str]:
    m = []
    if not result["spannungsband_ok"]:
        m.append("Blindleistungsregelung Q(U) gemaess VDE-AR-N 4105/4110 aktivieren")
        m.append("Querschnittserhoehung der Anschlussleitung pruefen")
    if not result["thermische_auslastung_ok"]:
        m.append("Wirkleistungsbegrenzung (z.B. 70%-Regelung) pruefen")
        m.append("Trafo-Upgrade oder paralleler Trafo erwaegen")
    if not result["kurzschluss_ok"]:
        m.append("Anschluss an hoehere Spannungsebene pruefen")
    if not result["n1_ok"]:
        m.append("Redundante Einspeisung / Ringnetz-Anbindung pruefen")
    if not m:
        m.append("Keine Zusatzmassnahmen erforderlich — Anschluss konform")
    return m


@router.post("/projektierer", response_model=ProjektiererResponse)
def check_projektierer(
    req: ProjektiererRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    actor = _require_stakeholder_access(
        current_user,
        allowed_roles={"projektierer", "netzbetreiber"},
        route_name="projektierer",
    )
    service_data = run_projektierer_check(db, req.model_dump(), actor)
    project_id = service_data["project_id"]
    result = service_data["result"]

    commit_projektierer_transaction(
        db,
        actor=actor,
        project_id=project_id,
        req_data=req.model_dump(),
        result=result,
    )

    return ProjektiererResponse(
        project_id=project_id, score=result["score"],
        spannungsband_ok=result["spannungsband_ok"],
        thermische_auslastung_ok=result["thermische_auslastung_ok"],
        kurzschluss_ok=result["kurzschluss_ok"], n1_ok=result["n1_ok"],
        netzebene=result["netzebene"], empfehlung=result["empfehlung"],
        engpaesse=_engpaesse(result),
        massnahmen_empfehlungen=_massnahmen(result, req),
        details=result.get("details", {}),
    )


# ============================================================
#  3) NETZBETREIBER  — voller Input + Pruefer-ID, Audit-Antwort
# ============================================================

class NetzbetreiberRequest(ProjektiererRequest):
    pruefer_id: str = Field(..., min_length=1)
    aktenzeichen: str = Field(..., min_length=1)
    pruefvermerk: Optional[str] = ""


class KonformitaetFlags(BaseModel):
    vde_ar_n_4105: bool   # NS
    vde_ar_n_4110: bool   # MS
    vde_ar_n_4120: bool   # HS
    tar_hochspannung: bool


class RevisionsBlock(BaseModel):
    timestamp_utc: str
    pruefer_id: str
    aktenzeichen: str
    audit_id: int
    checksum_sha256: str


class NetzbetreiberResponse(ProjektiererResponse):
    konformitaet: KonformitaetFlags
    revision: RevisionsBlock
    pruefvermerk: str


@router.post("/netzbetreiber", response_model=NetzbetreiberResponse)
def check_netzbetreiber(
    req: NetzbetreiberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    actor = _require_stakeholder_access(
        current_user,
        allowed_roles={"netzbetreiber"},
        route_name="netzbetreiber",
    )
    service_data = run_netzbetreiber_check(db, req.model_dump(), actor)
    project_id = service_data["project_id"]
    result = service_data["result"]
    audit_id = service_data["audit_id"]
    checksum = service_data["checksum"]
    spannung_kv = float(req.spannungsebene)

    # Konformitaet = technische Kriterien (nicht Score!)
    # Basis: Spannungsband + thermisch + Kurzschluss erfuellt.
    # Fuer MS/HS/HoeS zusaetzlich N-1 Pre-Screen plausibel.
    technisch_basis_ok = (
        result["spannungsband_ok"]
        and result["thermische_auslastung_ok"]
        and result["kurzschluss_ok"]
    )
    technisch_ms_hs_ok = technisch_basis_ok and result["n1_ok"]

    konform = KonformitaetFlags(
        # VDE-AR-N 4105: Niederspannung (<= 1 kV; praktisch 0,4 kV)
        vde_ar_n_4105=(spannung_kv <= 1.0 and technisch_basis_ok),
        # VDE-AR-N 4110: Mittelspannung (> 1 kV bis 35 kV)
        vde_ar_n_4110=(1.0 < spannung_kv <= 35.0 and technisch_ms_hs_ok),
        # VDE-AR-N 4120: Hochspannung (> 35 kV bis 110 kV)
        vde_ar_n_4120=(35.0 < spannung_kv <= 110.0 and technisch_ms_hs_ok),
        # TAR Hoechstspannung (> 110 kV)
        tar_hochspannung=(spannung_kv > 110.0 and technisch_ms_hs_ok),
    )

    revision = RevisionsBlock(
        timestamp_utc=service_data["timestamp_utc"],
        pruefer_id=req.pruefer_id, aktenzeichen=req.aktenzeichen,
        audit_id=audit_id, checksum_sha256=checksum,
    )

    return NetzbetreiberResponse(
        project_id=project_id, score=result["score"],
        spannungsband_ok=result["spannungsband_ok"],
        thermische_auslastung_ok=result["thermische_auslastung_ok"],
        kurzschluss_ok=result["kurzschluss_ok"], n1_ok=result["n1_ok"],
        netzebene=result["netzebene"], empfehlung=result["empfehlung"],
        engpaesse=_engpaesse(result),
        massnahmen_empfehlungen=_massnahmen(result, req),
        details=result.get("details", {}),
        konformitaet=konform, revision=revision,
        pruefvermerk=req.pruefvermerk or "",
    )
