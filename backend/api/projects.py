from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_csrf
from db.database import get_db
from db.models import User
from services import geocoding_service, project_service
from services.visibility_service import (
    derive_stakeholder_path,
    get_project_access_level,
    parse_project_role_inputs,
    sanitize_project_inputs,
    sanitize_project_result,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

UPLOAD_DIR = os.getenv("PROJECT_UPLOAD_DIR", "./uploads")


def _has_address(values: dict[str, Any]) -> bool:
    street = (values.get("street") or "").strip()
    house_number = (values.get("house_number") or "").strip()
    plz = (values.get("plz") or "").strip()
    return bool(street and house_number and plz)


def _has_coordinates(values: dict[str, Any]) -> bool:
    return values.get("latitude") is not None and values.get("longitude") is not None


def _has_plz_only(values: dict[str, Any]) -> bool:
    return bool((values.get("plz") or "").strip())


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    plz: str | None = Field(default=None, min_length=4, max_length=5)
    ort: str | None = Field(default=None, max_length=120)
    street: str | None = Field(default=None, max_length=120)
    house_number: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    typ: str = Field(..., min_length=1, max_length=50)
    leistung_kw: float = Field(..., gt=0)
    description: str | None = None
    role_inputs: dict[str, Any] | None = None
    role_results: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _at_least_one_location(self) -> "ProjectCreateRequest":
        data = self.model_dump()
        if _has_address(data) or _has_coordinates(data) or _has_plz_only(data):
            return self
        raise ValueError(
            "Mindestens PLZ oder vollstaendige Koordinaten (latitude+longitude) erforderlich.",
        )


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    plz: str | None = Field(default=None, min_length=4, max_length=5)
    ort: str | None = Field(default=None, max_length=120)
    street: str | None = Field(default=None, max_length=120)
    house_number: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    typ: str | None = None
    leistung_kw: float | None = Field(default=None, gt=0)
    description: str | None = None
    role_inputs: dict[str, Any] | None = None
    role_results: dict[str, Any] | None = None


class ShareRequest(BaseModel):
    target_user_id: int = Field(..., gt=0)
    project_role: str = Field(default="viewer", pattern="^(viewer|editor|owner)$")


class ProjectResponse(BaseModel):
    id: int
    name: str
    plz: str | None
    ort: str | None = None
    street: str | None = None
    house_number: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    typ: str
    leistung_kw: float
    description: str | None
    role_inputs: dict[str, Any]
    role_results: dict[str, Any]
    owner_user_id: int | None
    created_at: datetime
    updated_at: datetime | None
    warnings: list[str] = Field(default_factory=list)

def _to_response(
    project,
    db: Session,
    current_user: User,
    *,
    warnings: list[str] | None = None,
) -> ProjectResponse:
    role_inputs = parse_project_role_inputs(project.role_inputs)
    access_level = get_project_access_level(db, current_user, project)
    stakeholder_path = derive_stakeholder_path(role_inputs, fallback_user_role=current_user.role)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        plz=project.plz,
        ort=project.ort,
        street=getattr(project, "street", None),
        house_number=getattr(project, "house_number", None),
        city=getattr(project, "city", None),
        latitude=getattr(project, "latitude", None),
        longitude=getattr(project, "longitude", None),
        typ=project.typ,
        leistung_kw=project.leistung_kw,
        description=project.description,
        role_inputs=sanitize_project_inputs(role_inputs, access_level=access_level),
        role_results=sanitize_project_result(
            parse_project_role_inputs(project.role_results),
            stakeholder_path=stakeholder_path,
            access_level=access_level,
        ),
        owner_user_id=project.owner_user_id if access_level in {"admin", "owner", "editor"} else None,
        created_at=project.created_at,
        updated_at=project.updated_at,
        warnings=list(warnings or []),
    )


def _enrich_location_with_geocoding(payload: dict[str, Any]) -> list[str]:
    """Erzeugt lat/lon aus Adresse oder Adresse aus lat/lon. Fail-soft, mutiert payload.

    Liefert eine Liste mit Warnungen (z. B. "geocoding_failed"), die der Client anzeigen kann.
    Geocoding-Metadaten landen in payload["role_inputs"]["_geocoding"], damit das Projekt sie
    revisionssicher mitschreibt (Datenquelle, Confidence) — ohne dass das Project-Modell neue
    Felder fuer Confidence/Source braucht.
    """
    warnings: list[str] = []
    role_inputs = payload.get("role_inputs")
    if not isinstance(role_inputs, dict):
        role_inputs = {}
    geocoding_meta = role_inputs.get("_geocoding") if isinstance(role_inputs.get("_geocoding"), dict) else {}

    has_address = bool(
        (payload.get("street") or "").strip()
        and (payload.get("house_number") or "").strip()
        and (payload.get("plz") or "").strip(),
    )
    has_coordinates = payload.get("latitude") is not None and payload.get("longitude") is not None

    if has_address and not has_coordinates:
        result = geocoding_service.geocode_address(
            street=payload.get("street"),
            house_number=payload.get("house_number"),
            plz=payload.get("plz"),
            city=payload.get("city"),
        )
        if result:
            payload["latitude"] = result["latitude"]
            payload["longitude"] = result["longitude"]
            geocoding_meta = {
                "mode": "forward",
                "source": result["source"],
                "data_class": result["data_class"],
                "confidence": result["confidence"],
                "raw_label": result.get("raw_label"),
                "has_house_number": result.get("has_house_number", False),
            }
        else:
            warnings.append("geocoding_failed")

    elif has_coordinates and not has_address:
        result = geocoding_service.reverse_geocode(
            lat=payload.get("latitude"),
            lon=payload.get("longitude"),
        )
        if result:
            if not (payload.get("street") or "").strip() and result.get("street"):
                payload["street"] = result["street"]
            if not (payload.get("house_number") or "").strip() and result.get("house_number"):
                payload["house_number"] = result["house_number"]
            if not (payload.get("plz") or "").strip() and result.get("plz"):
                payload["plz"] = result["plz"]
            if not (payload.get("city") or "").strip() and result.get("city"):
                payload["city"] = result["city"]
            geocoding_meta = {
                "mode": "reverse",
                "source": result["source"],
                "data_class": result["data_class"],
                "confidence": result["confidence"],
                "raw_label": result.get("raw_label"),
            }
        else:
            warnings.append("reverse_geocoding_failed")

    if geocoding_meta:
        role_inputs["_geocoding"] = geocoding_meta
        payload["role_inputs"] = role_inputs

    return warnings


@router.post("", response_model=ProjectResponse)
def create_project(
    req: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ProjectResponse:
    payload = req.model_dump()
    warnings = _enrich_location_with_geocoding(payload)
    project = project_service.create_project(db, current_user, **payload)
    return _to_response(project, db, current_user, warnings=warnings)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    return [_to_response(p, db, current_user) for p in project_service.list_projects(db, current_user)]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    return _to_response(project_service.get_project(db, current_user, project_id), db, current_user)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    req: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ProjectResponse:
    project = project_service.update_project(db, current_user, project_id, req.model_dump(exclude_none=True))
    return _to_response(project, db, current_user)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, str]:
    project_service.delete_project(db, current_user, project_id)
    return {"status": "deleted"}


@router.post("/{project_id}/share")
def share_project(
    project_id: int,
    req: ShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, str]:
    project_service.share_project(db, current_user, project_id, req.target_user_id, req.project_role)
    return {"status": "shared"}


@router.delete("/{project_id}/share/{target_user_id}")
def unshare_project(
    project_id: int,
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, str]:
    project_service.unshare_project(db, current_user, project_id, target_user_id)
    return {"status": "unshared"}


@router.post("/{project_id}/files")
def upload_file(
    project_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, str | int]:
    record = project_service.upload_project_file(db, current_user, project_id, file, upload_dir=UPLOAD_DIR)
    return {"id": record.id, "file_name": record.file_name, "size_bytes": record.size_bytes}
