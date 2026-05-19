"""V1-Endpoints fuer geo-bezogene Lookups (PLZ -> VNB-Kandidaten, OSM-Nahbauten)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, Request

from core.errors import AnalysisError
from core.rate_limit import enforce_rate_limit, get_client_ip
from geo.osm_nearby import lookup_osm_nearby
from geo.plz_lookup import lookup_plz
from geo.schemas import OsmNearbyResponse, PlzLookupResponse

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
    request: Request,
    plz: str = Path(..., description="Deutsche PLZ, genau 5 Ziffern."),
) -> PlzLookupResponse:
    enforce_rate_limit(
        f"geo:plz:ip:{get_client_ip(request)}",
        limit=40,
        window_seconds=60,
        message="Zu viele PLZ-Lookups",
        hint="Bitte kurz warten und die Anfrage erneut senden.",
    )
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


@router.get(
    "/osm-nearby",
    response_model=OsmNearbyResponse,
    summary="OSM-Infrastrukturhinweise im Umkreis (Nahbauten)",
    description=(
        "Liefert normalisierte OpenStreetMap-Hinweise auf Netzassets im Umkreis "
        "eines Standorts. Datenklasse B, keine Kapazitaetsaussage. "
        "Entweder lat+lon oder plz (Geocoding via Nominatim) erforderlich."
    ),
)
def get_osm_nearby(
    request: Request,
    lat: float | None = Query(default=None, ge=-90, le=90, description="Breitengrad WGS84."),
    lon: float | None = Query(default=None, ge=-180, le=180, description="Laengengrad WGS84."),
    plz: str | None = Query(default=None, description="Deutsche PLZ (5 Ziffern), falls keine Koordinaten."),
    radius_m: int = Query(default=2_500, ge=100, le=15_000, description="Suchradius in Metern."),
) -> OsmNearbyResponse:
    if lat is not None and lon is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "COORDINATES_INCOMPLETE",
                "message": "lon fehlt.",
                "hint": "lat und lon gemeinsam angeben.",
            },
        )
    if lon is not None and lat is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "COORDINATES_INCOMPLETE",
                "message": "lat fehlt.",
                "hint": "lat und lon gemeinsam angeben.",
            },
        )
    enforce_rate_limit(
        f"geo:osm-nearby:ip:{get_client_ip(request)}",
        limit=20,
        window_seconds=60,
        message="Zu viele OSM-Nahbauten-Anfragen",
        hint="Bitte kurz warten — die Anfragerate ist begrenzt.",
    )
    try:
        return lookup_osm_nearby(lat=lat, lon=lon, plz=plz, radius_m=radius_m)
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
