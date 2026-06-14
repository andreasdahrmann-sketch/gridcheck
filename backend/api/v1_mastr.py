"""V1 Read-API fuer MaStR-Bestandsdaten (BL-GIS-003 Skeleton).

KEINE Aussage zur freien Netzkapazitaet (Rule 06).
PostGIS ST_DWithin kommt im naechsten Inkrement; heute via PLZ + grobe BBox.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.rate_limit import enforce_scoped_rate_limit
from db.database import get_db
from db.models import MastrUnit, User
from schemas.mastr import MastrUnitResponse, MastrUnitsPage


router = APIRouter(prefix="/api/v1/mastr", tags=["v1-mastr"])

_PAGE_LIMIT_MAX = 100

# Sehr grobe Naeherung fuer Skeleton-Endpoint (kein PostGIS):
# 1 Breitengrad ~ 111.32 km. Laengengrad bei 51 deg N ~ 70 km.
_KM_PER_DEG_LAT = Decimal("111.32")
_KM_PER_DEG_LON = Decimal("70.0")


def _bbox_filter(query, *, lat: Decimal, lon: Decimal, radius_km: Decimal):
    delta_lat = radius_km / _KM_PER_DEG_LAT
    delta_lon = radius_km / _KM_PER_DEG_LON
    return query.filter(
        MastrUnit.latitude.isnot(None),
        MastrUnit.longitude.isnot(None),
        MastrUnit.latitude >= (lat - delta_lat),
        MastrUnit.latitude <= (lat + delta_lat),
        MastrUnit.longitude >= (lon - delta_lon),
        MastrUnit.longitude <= (lon + delta_lon),
    )


@router.get(
    "/units",
    response_model=MastrUnitsPage,
    summary="MaStR-Units im Umkreis (Skeleton, ohne PostGIS)",
    description=(
        "Liefert MaStR-Bestandsanlagen gefiltert nach PLZ und/oder Bounding-Box "
        "um lat/lon. Datenklasse A laut Rule 06. KEINE Kapazitaetsaussage."
    ),
)
def get_units(
    request: Request,
    plz: Optional[str] = Query(default=None, max_length=10),
    lat: Optional[Decimal] = Query(default=None, ge=-90, le=90),
    lon: Optional[Decimal] = Query(default=None, ge=-180, le=180),
    radius_km: Decimal = Query(default=Decimal("5"), gt=0, le=Decimal("50")),
    unit_type: Optional[str] = Query(default=None, max_length=20),
    limit: int = Query(default=50, gt=0, le=_PAGE_LIMIT_MAX),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MastrUnitsPage:
    enforce_scoped_rate_limit(
        "mastr:read",
        request=request,
        ip_limit=60,
        window_seconds=60,
        message="Zu viele MaStR-Anfragen.",
        hint="Kurz warten und erneut versuchen.",
    )

    if plz is None and (lat is None or lon is None):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "MASTR_FILTER_REQUIRED",
                "message": "Mindestens plz oder lat+lon erforderlich.",
                "hint": "plz angeben oder lat und lon zusammen.",
            },
        )
    if (lat is None) != (lon is None):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "MASTR_COORDS_INCOMPLETE",
                "message": "lat und lon muessen zusammen angegeben werden.",
                "hint": "Beide Koordinaten oder keine.",
            },
        )

    base_query = db.query(MastrUnit)
    if plz:
        if not plz.isdigit():
            raise HTTPException(
                status_code=422,
                detail={"code": "MASTR_PLZ_INVALID", "message": "plz darf nur Ziffern enthalten.", "hint": None},
            )
        base_query = base_query.filter(MastrUnit.plz == plz)
    if lat is not None and lon is not None:
        base_query = _bbox_filter(base_query, lat=lat, lon=lon, radius_km=radius_km)
    if unit_type:
        base_query = base_query.filter(MastrUnit.unit_type == unit_type.lower())

    total = base_query.count()
    rows = (
        base_query.order_by(MastrUnit.mastr_id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [MastrUnitResponse.model_validate(row) for row in rows]
    return MastrUnitsPage(items=items, total=total, limit=limit, offset=offset)
