from __future__ import annotations

import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_csrf
from db.database import get_db
from db.models import SiteMarker, User
from services import site_marker_service

router = APIRouter(prefix="/api/v1/site-markers", tags=["site-markers"])

UPLOAD_DIR = os.getenv("SITE_MARKER_UPLOAD_DIR", "./uploads/site_markers")

AssetType = Literal["ortsnetztrafo", "umspannwerk", "schaltstation"]
LocationSource = Literal["gps", "manual"]
VerificationStatus = Literal["unverified"]


class SiteMarkerResponse(BaseModel):
    id: int
    asset_type: AssetType
    location_source: LocationSource
    verification_status: VerificationStatus
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    photo_file_name: str
    photo_mime_type: str
    photo_size_bytes: int
    photo_api_path: str
    revision_hash: str | None
    created_at: datetime


def _to_response(marker: SiteMarker) -> SiteMarkerResponse:
    return SiteMarkerResponse(
        id=marker.id,
        asset_type=marker.asset_type,
        location_source=marker.location_source,
        verification_status=marker.verification_status,
        latitude=marker.latitude,
        longitude=marker.longitude,
        photo_file_name=marker.photo_file_name,
        photo_mime_type=marker.photo_mime_type,
        photo_size_bytes=marker.photo_size_bytes,
        photo_api_path=f"/api/v1/site-markers/{marker.id}/photo",
        revision_hash=marker.revision_hash,
        created_at=marker.created_at,
    )


@router.get("", response_model=list[SiteMarkerResponse])
def list_site_markers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SiteMarkerResponse]:
    return [_to_response(marker) for marker in site_marker_service.list_site_markers(db, current_user)]


@router.post("", response_model=SiteMarkerResponse, status_code=status.HTTP_201_CREATED)
def create_site_marker(
    asset_type: AssetType = Form(...),
    location_source: LocationSource = Form(...),
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> SiteMarkerResponse:
    marker = site_marker_service.create_site_marker(
        db,
        current_user,
        asset_type=asset_type,
        location_source=location_source,
        latitude=latitude,
        longitude=longitude,
        photo=photo,
        upload_dir=UPLOAD_DIR,
    )
    return _to_response(marker)


@router.get("/{marker_id}/photo")
def get_site_marker_photo(
    marker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    marker = site_marker_service.get_site_marker(db, current_user, marker_id)
    if not os.path.exists(marker.photo_storage_path):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SITE_MARKER_PHOTO_MISSING",
                "message": "Foto nicht gefunden",
                "hint": "Bitte Marker neu erfassen oder Support kontaktieren.",
            },
        )
    return FileResponse(
        marker.photo_storage_path,
        media_type=marker.photo_mime_type,
        filename=marker.photo_file_name,
    )
