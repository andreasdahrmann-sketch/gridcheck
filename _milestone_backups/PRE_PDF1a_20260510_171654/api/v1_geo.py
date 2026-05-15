"""V1-Endpoints fuer geo-bezogene Lookups (PLZ -> VNB-Kandidaten)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path

from core.errors import AnalysisError
from geo.plz_lookup import lookup_plz
from geo.schemas import PlzLookupResponse

router = APIRouter(prefix="/api/v1/geo", tags=["v1-geo"])


@router.get(
    "/plz/{plz}",
    response_model=PlzLookupResponse,
    summary="Heuristisches PLZ -> VNB-Kandidaten-Lookup",
    description=(
        "Liefert moegliche zustaendige Verteilnetzbetreiber fuer eine deutsche "
        "PLZ und markiert, ob mindestens ein Kandidat ein oeffentliches "
        "SNAP-Online-Vorpruefungsportal anbietet. Confidence ist B-heuristisch "
        "(PLZ-Praefix-basiert), keine parzellengenaue Aussage. Keine Aussage "
        "zur freien Netzkapazitaet."
    ),
)
def get_plz(
    plz: str = Path(..., description="Deutsche PLZ, genau 5 Ziffern."),
) -> PlzLookupResponse:
    try:
        return lookup_plz(plz)
    except AnalysisError as e:
        raise HTTPException(status_code=e.http_status, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "hint": None,
            },
        )
