from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from db.models import SiteMarker, User
from engine.revision import speichere_revision

_ALLOWED_UPLOAD_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def _marker_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "SITE_MARKER_NOT_FOUND",
            "message": "Vor-Ort-Marker nicht gefunden",
            "hint": "Bitte Marker-ID pruefen oder Liste neu laden.",
        },
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "code": "SITE_MARKER_FORBIDDEN",
            "message": "Kein Zugriff auf Vor-Ort-Marker",
            "hint": "Bitte mit dem erfassenden Konto anmelden.",
        },
    )


def _can_access(user: User, marker: SiteMarker) -> bool:
    return user.role == "admin" or marker.created_by_user_id == user.id


def get_site_marker(db: Session, user: User, marker_id: int) -> SiteMarker:
    marker = db.query(SiteMarker).filter(SiteMarker.id == marker_id).first()
    if not marker:
        raise _marker_not_found()
    if not _can_access(user, marker):
        raise _forbidden()
    return marker


def list_site_markers(db: Session, user: User) -> list[SiteMarker]:
    query = db.query(SiteMarker)
    if user.role != "admin":
        query = query.filter(SiteMarker.created_by_user_id == user.id)
    return query.order_by(SiteMarker.created_at.desc(), SiteMarker.id.desc()).all()


def create_site_marker(
    db: Session,
    user: User,
    *,
    asset_type: str,
    location_source: str,
    latitude: float,
    longitude: float,
    photo: UploadFile,
    upload_dir: str,
    max_size_bytes: int = 10 * 1024 * 1024,
) -> SiteMarker:
    content_type = (photo.content_type or "").lower()
    if content_type not in _ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "SITE_MARKER_PHOTO_TYPE_NOT_ALLOWED",
                "message": "Fototyp nicht erlaubt",
                "hint": "Erlaubt sind JPG, PNG und WEBP.",
            },
        )
    if not photo.filename:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "SITE_MARKER_PHOTO_FILENAME_MISSING",
                "message": "Dateiname fehlt",
                "hint": "Bitte Foto erneut auswaehlen.",
            },
        )

    os.makedirs(upload_dir, exist_ok=True)
    file_name = Path(photo.filename).name
    storage_name = f"{user.id}_{uuid4().hex}_{file_name}"
    storage_path = Path(upload_dir) / storage_name
    size_bytes = 0
    digest = hashlib.sha256()

    try:
        with storage_path.open("wb") as handle:
            while True:
                chunk = photo.file.read(1024 * 256)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > max_size_bytes:
                    handle.close()
                    storage_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "code": "SITE_MARKER_PHOTO_TOO_LARGE",
                            "message": "Foto ist zu gross",
                            "hint": "Bitte ein Bild bis maximal 10 MB hochladen.",
                        },
                    )
                digest.update(chunk)
                handle.write(chunk)
    finally:
        photo.file.close()

    if size_bytes == 0:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail={
                "code": "SITE_MARKER_PHOTO_EMPTY",
                "message": "Foto ist leer",
                "hint": "Bitte ein gueltiges Foto hochladen.",
            },
        )

    marker = SiteMarker(
        created_by_user_id=user.id,
        asset_type=asset_type,
        location_source=location_source,
        latitude=latitude,
        longitude=longitude,
        verification_status="unverified",
        photo_file_name=file_name,
        photo_mime_type=content_type,
        photo_size_bytes=size_bytes,
        photo_storage_path=str(storage_path),
        photo_checksum=digest.hexdigest(),
    )
    db.add(marker)
    db.flush()

    revision = speichere_revision(
        {
            "eingabe": {
                "site_marker_id": marker.id,
                "asset_type": asset_type,
                "location_source": location_source,
                "latitude": latitude,
                "longitude": longitude,
            },
            "fazit": {
                "status": "SITE_MARKER_CREATED",
                "verification_status": marker.verification_status,
            },
            "warnungen": [
                "Vor-Ort-Marker ist initial unverified und darf nicht als verifizierte Netzaussage interpretiert werden."
            ],
            "empfehlungen": [
                "Marker bei Bedarf spaeter fachlich pruefen und mit weiteren Quellen abgleichen."
            ],
        },
        actor_user_id=user.id,
        action_type="SITE_MARKER_CREATED",
        db=db,
    )
    marker.revision_hash = revision["hash"]
    db.commit()
    db.refresh(marker)
    return marker
