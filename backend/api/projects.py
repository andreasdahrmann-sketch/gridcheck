from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_csrf
from db.database import get_db
from db.models import User
from services import project_service

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

UPLOAD_DIR = os.getenv("PROJECT_UPLOAD_DIR", "./uploads")


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    plz: str = Field(..., min_length=4, max_length=5)
    typ: str = Field(..., min_length=1, max_length=50)
    leistung_kw: float = Field(..., gt=0)
    description: str | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    plz: str | None = Field(default=None, min_length=4, max_length=5)
    typ: str | None = None
    leistung_kw: float | None = Field(default=None, gt=0)
    description: str | None = None


class ShareRequest(BaseModel):
    target_user_id: int = Field(..., gt=0)
    project_role: str = Field(default="viewer", pattern="^(viewer|editor|owner)$")


class ProjectResponse(BaseModel):
    id: int
    name: str
    plz: str
    typ: str
    leistung_kw: float
    description: str | None
    owner_user_id: int | None
    created_at: datetime
    updated_at: datetime | None


def _to_response(project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        plz=project.plz,
        typ=project.typ,
        leistung_kw=project.leistung_kw,
        description=project.description,
        owner_user_id=project.owner_user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post("", response_model=ProjectResponse)
def create_project(
    req: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ProjectResponse:
    project = project_service.create_project(db, current_user, **req.model_dump())
    return _to_response(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    return [_to_response(p) for p in project_service.list_projects(db, current_user)]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    return _to_response(project_service.get_project(db, current_user, project_id))


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    req: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ProjectResponse:
    project = project_service.update_project(db, current_user, project_id, req.model_dump(exclude_none=True))
    return _to_response(project)


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
