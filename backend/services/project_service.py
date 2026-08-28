from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from db.models import AuditLog, Project, ProjectFile, ProjectMember, User, make_checksum
from services.visibility_service import (
    StakeholderPath,
    can_write_project,
    get_project_access_level,
    resolve_project_stakeholder_path,
)

_ALLOWED_UPLOAD_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

from engine.revision import speichere_revision


def _json_text(value: dict | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def join_address_hint(
    *,
    street: str | None = None,
    house_number: str | None = None,
    plz: str | None = None,
    city: str | None = None,
    ort: str | None = None,
) -> str | None:
    street_line = " ".join(
        part for part in ((street or "").strip(), (house_number or "").strip()) if part
    )
    locality = (city or "").strip() or (ort or "").strip()
    hint = ", ".join(part for part in (street_line, (plz or "").strip(), locality) if part)
    return hint or None


def format_project_address_hint(project: Project) -> str | None:
    return join_address_hint(
        street=getattr(project, "street", None),
        house_number=getattr(project, "house_number", None),
        plz=getattr(project, "plz", None),
        city=getattr(project, "city", None),
        ort=getattr(project, "ort", None),
    )


def hydrate_analyze_location_from_project(
    payload: dict[str, Any],
    project: Project,
) -> dict[str, Any]:
    """Fill omitted analyze/report coordinates from the persisted Project row.

    Dual-location create stores WGS84 on `projects.latitude/longitude`, but the
    workspace analyze payload historically sent only `role_inputs.project_location`.
    That field stays empty unless the profile form was filled, so reports persisted
    the Germany-center placeholder (51.1657, 10.4515) for an otherwise geocoded site.
    Explicit request coordinates are never overwritten.
    """
    hydrated = dict(payload)
    loc_raw = hydrated.get("project_location")
    loc: dict[str, Any] = dict(loc_raw) if isinstance(loc_raw, dict) else {}

    has_coords = loc.get("latitude") is not None and loc.get("longitude") is not None
    project_lat = getattr(project, "latitude", None)
    project_lon = getattr(project, "longitude", None)
    if not has_coords and project_lat is not None and project_lon is not None:
        loc["latitude"] = float(project_lat)
        loc["longitude"] = float(project_lon)

    if not str(loc.get("address_hint") or "").strip():
        hint = format_project_address_hint(project)
        if hint:
            loc["address_hint"] = hint

    if loc.get("latitude") is not None or loc.get("longitude") is not None or loc.get("address_hint"):
        hydrated["project_location"] = loc
    return hydrated


def _can_read(user: User, project: Project, db: Session) -> bool:
    if user.role == "admin" or project.owner_user_id == user.id:
        return True
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
    )
    return member is not None


def _can_write(user: User, project: Project, db: Session) -> bool:
    return can_write_project(get_project_access_level(db, user, project))


def _project_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "PROJECT_NOT_FOUND", "message": "Projekt nicht gefunden", "hint": "Bitte ID pruefen."},
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "PROJECT_FORBIDDEN", "message": "Kein Zugriff auf Projekt", "hint": "Bitte Berechtigung pruefen."},
    )


def _write_forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "code": "PROJECT_WRITE_FORBIDDEN",
            "message": "Projektgebundene Aenderungen sind nur fuer Owner, Editor oder Admin erlaubt.",
            "hint": "Bitte mit Owner-, Editor- oder Admin-Rechten erneut versuchen.",
        },
    )


def _append_audit_and_revision(db: Session, project: Project, user: User, action: str, payload: dict) -> None:
    audit_payload = {"action": action, "actor_user_id": user.id, "payload": payload}
    db.add(
        AuditLog(
            project_id=project.id,
            action=action,
            detail=json.dumps(audit_payload, default=str),
            checksum=make_checksum(audit_payload),
        )
    )
    speichere_revision(
        {"eingabe": payload, "fazit": {"status": action}},
        actor_user_id=user.id,
        action_type=action,
        project_id=project.id,
        db=db,
    )


def create_project(
    db: Session,
    user: User,
    *,
    name: str,
    plz: str | None = None,
    typ: str,
    leistung_kw: float,
    description: str | None = None,
    role_inputs: dict | None = None,
    role_results: dict | None = None,
    street: str | None = None,
    house_number: str | None = None,
    city: str | None = None,
    ort: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Project:
    project = Project(
        name=name,
        plz=plz,
        ort=ort,
        street=street,
        house_number=house_number,
        city=city,
        latitude=latitude,
        longitude=longitude,
        typ=typ,
        leistung_kw=leistung_kw,
        description=description or "",
        role_inputs=_json_text(role_inputs),
        role_results=_json_text(role_results),
        owner_user_id=user.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, project_role="owner"))
    _append_audit_and_revision(
        db,
        project,
        user,
        "PROJECT_CREATED",
        {
            "name": name,
            "typ": typ,
            "leistung_kw": leistung_kw,
            "plz": plz,
            "ort": ort,
            "street": street,
            "house_number": house_number,
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
            "role_inputs": role_inputs or {},
            "role_results": role_results or {},
        },
    )
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session, user: User) -> list[Project]:
    query = (
        db.query(Project)
        .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(
            Project.deleted_at.is_(None),
            (Project.owner_user_id == user.id) | (ProjectMember.user_id == user.id),
        )
        .distinct(Project.id)
        .order_by(Project.id, Project.updated_at.desc())
    )
    return query.all()


def get_project(db: Session, user: User, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise _project_not_found()
    if not _can_read(user, project, db):
        raise _forbidden()
    return project


def get_project_access_context(
    db: Session,
    user: User,
    project_id: int,
    *,
    require_write: bool = False,
) -> tuple[Project, str, StakeholderPath]:
    project = get_project(db, user, project_id)
    access_level = get_project_access_level(db, user, project)
    if require_write and not can_write_project(access_level):
        raise _write_forbidden()
    stakeholder_path = resolve_project_stakeholder_path(project, fallback_user_role=user.role)
    return project, access_level, stakeholder_path


def update_project(db: Session, user: User, project_id: int, payload: dict) -> Project:
    project = get_project(db, user, project_id)
    if not _can_write(user, project, db):
        raise _forbidden()
    for key in (
        "name",
        "plz",
        "typ",
        "leistung_kw",
        "description",
        "street",
        "house_number",
        "city",
        "ort",
        "latitude",
        "longitude",
    ):
        if key in payload and payload[key] is not None:
            setattr(project, key, payload[key])
    if "role_inputs" in payload and payload["role_inputs"] is not None:
        project.role_inputs = _json_text(payload["role_inputs"])
    if "role_results" in payload and payload["role_results"] is not None:
        project.role_results = _json_text(payload["role_results"])
    project.updated_at = datetime.now(timezone.utc)
    _append_audit_and_revision(db, project, user, "PROJECT_UPDATED", payload)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, user: User, project_id: int) -> None:
    project = get_project(db, user, project_id)
    if not _can_write(user, project, db):
        raise _forbidden()
    project.deleted_at = datetime.now(timezone.utc)
    project.updated_at = datetime.now(timezone.utc)
    _append_audit_and_revision(db, project, user, "PROJECT_DELETED", {"project_id": project.id})
    db.commit()


def share_project(db: Session, user: User, project_id: int, target_user_id: int, project_role: str) -> None:
    project = get_project(db, user, project_id)
    if project.owner_user_id != user.id and user.role != "admin":
        raise _forbidden()
    target_user = db.query(User).filter(User.id == target_user_id, User.is_active.is_(True)).first()
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "Ziel-Benutzer nicht gefunden", "hint": "Bitte user_id pruefen."},
        )
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == target_user_id)
        .first()
    )
    if membership:
        membership.project_role = project_role
    else:
        db.add(ProjectMember(project_id=project.id, user_id=target_user_id, project_role=project_role))
    _append_audit_and_revision(
        db,
        project,
        user,
        "PROJECT_SHARED",
        {"target_user_id": target_user_id, "project_role": project_role},
    )
    db.commit()


def unshare_project(db: Session, user: User, project_id: int, target_user_id: int) -> None:
    project = get_project(db, user, project_id)
    if project.owner_user_id != user.id and user.role != "admin":
        raise _forbidden()
    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == target_user_id)
        .first()
    )
    if membership:
        db.delete(membership)
    _append_audit_and_revision(db, project, user, "PROJECT_UNSHARED", {"target_user_id": target_user_id})
    db.commit()


def upload_project_file(
    db: Session,
    user: User,
    project_id: int,
    upload: UploadFile,
    upload_dir: str,
    max_size_bytes: int = 8 * 1024 * 1024,
) -> ProjectFile:
    project = get_project(db, user, project_id)
    if not _can_write(user, project, db):
        raise _forbidden()
    content_type = (upload.content_type or "").lower()
    if content_type not in _ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "UPLOAD_TYPE_NOT_ALLOWED",
                "message": "Dateityp nicht erlaubt",
                "hint": "Erlaubt sind PDF, PNG, JPG, TXT und XLSX.",
            },
        )
    if not upload.filename:
        raise HTTPException(
            status_code=400,
            detail={"code": "UPLOAD_FILENAME_MISSING", "message": "Dateiname fehlt", "hint": "Bitte Datei erneut waehlen."},
        )
    os.makedirs(upload_dir, exist_ok=True)
    original_name = upload.filename or "upload.bin"
    file_name = Path(original_name).name
    safe_name = f"{project.id}_{int(datetime.now(timezone.utc).timestamp())}_{file_name}"
    storage_path = os.path.join(upload_dir, safe_name)
    size_bytes = 0
    digest = hashlib.sha256()
    with open(storage_path, "wb") as fp:
        while True:
            chunk = upload.file.read(1024 * 256)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > max_size_bytes:
                fp.close()
                os.remove(storage_path)
                raise HTTPException(
                    status_code=413,
                    detail={"code": "UPLOAD_TOO_LARGE", "message": "Datei zu gross", "hint": "Bitte kleinere Datei hochladen."},
                )
            digest.update(chunk)
            fp.write(chunk)
    if size_bytes == 0:
        os.remove(storage_path)
        raise HTTPException(
            status_code=400,
            detail={"code": "UPLOAD_EMPTY", "message": "Datei ist leer", "hint": "Bitte gueltige Datei hochladen."},
        )
    digest_hex = digest.hexdigest()
    record = ProjectFile(
        project_id=project.id,
        uploaded_by=user.id,
        file_name=file_name,
        mime_type=content_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
        checksum=digest_hex,
    )
    db.add(record)
    _append_audit_and_revision(
        db,
        project,
        user,
        "PROJECT_FILE_UPLOADED",
        {"file_name": record.file_name, "size_bytes": record.size_bytes, "checksum": digest_hex},
    )
    db.commit()
    db.refresh(record)
    return record
