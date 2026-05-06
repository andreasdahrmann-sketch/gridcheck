# backend/api/analyze_v2.py
"""
GridCheck v2 - Diagnose-Endpoint
- Strikte Eingabevalidierung via Pydantic
- Ruft direkt die neue Engine berechne_netzanschluss()
- Ergaenzt KI-Bewertung + Revisions-Persistenz
- Liefert das vollstaendige Engine-Output-Dict (kein Informationsverlust)
"""

from typing import Any, Dict, Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from engine import berechne_netzanschluss, ki_bewertung

router_v2 = APIRouter(prefix="/api/v2", tags=["v2-Analyse"])


class AnalyzeRequest(BaseModel):
    # Pflichtfelder
    nennspannung: float = Field(..., gt=0, le=380, description="kV")
    leistung_mw: float = Field(..., gt=0, le=2000, description="MW")
    leitungstyp: str = Field(..., description="z.B. NA2XS2Y240, NAYY150")
    entfernung_km: float = Field(..., gt=0, le=500)
    anschlussart: Literal["Einspeisung", "Entnahme", "Speicher"]

    # Optional
    anlagentyp: Optional[str] = Field(default="PV")
    plz: Optional[str] = Field(default=None)
    cos_phi: Optional[float] = Field(default=0.95, ge=0.8, le=1.0)
    parallele_systeme: Optional[int] = Field(default=1, ge=1, le=4)
    redundanz: Optional[bool] = Field(default=False)
    p_kw: Optional[float] = Field(default=None, gt=0)
    bestehende_einspeisung_mw: Optional[float] = Field(default=0, ge=0)
    sk_mva: Optional[float] = Field(default=None, gt=0)
    trafo_s_mva: Optional[float] = Field(default=None, gt=0)
    uk_prozent: Optional[float] = Field(default=None, gt=0, le=20)
    bestand_auslastung_prozent: Optional[float] = Field(default=0, ge=0, le=100)
    temperatur_c: Optional[float] = Field(default=20, ge=-30, le=80)


@router_v2.post("/analyze", response_model=None)
def analyze_v2(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    Vollwertige Netzanschluss-Diagnose.
    Liefert das komplette Engine-Output-Dict.
    HTTP 422 bei fachlichen Eingabefehlern.
    """
    eingabe = req.model_dump(exclude_none=False)

    # 1) Berechnung
    try:
        result = berechne_netzanschluss(eingabe)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine-Fehler: {e}")

    # 2) Fachliche Validierungsfehler -> 422
    if result.get("status") == "FEHLER":
        raise HTTPException(
            status_code=422,
            detail={
                "status": "FEHLER",
                "fehler": result.get("fehler", []),
                "warnungen": result.get("warnungen", []),
            },
        )

    # 3) KI-Bewertung (nicht kritisch)
    try:
        result = ki_bewertung(result)
    except Exception:
        result.setdefault("ki", {"konfidenz_prozent": 0,
                                 "hinweise": ["KI-Modul nicht verfuegbar"]})

    return result
