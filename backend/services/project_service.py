from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from db.models import AuditLog, Project, ProjectFile, ProjectMember, User, make_checksum
_ALLOWED_UPLOAD_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

from engine.revision import speichere_revision


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
    if user.role == "admin" or project.owner_user_id == user.id:
        return True
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
    )
    return member is not None and member.project_role in {"editor", "owner"}


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
    )


def create_project(db: Session, user: User, *, name: str, plz: str, typ: str, leistung_kw: float, description: str | None) -> Project:
    project = Project(
        name=name,
        plz=plz,
        typ=typ,
        leistung_kw=leistung_kw,
        description=description or "",
        owner_user_id=user.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, project_role="owner"))
    _append_audit_and_revision(db, project, user, "PROJECT_CREATED", {"name": name, "typ": typ, "leistung_kw": leistung_kw, "plz": plz})
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
        .order_by(Project.updated_at.desc())
    )
    return query.all()


def get_project(db: Session, user: User, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise _project_not_found()
    if not _can_read(user, project, db):
        raise _forbidden()
    return project


def update_project(db: Session, user: User, project_id: int, payload: dict) -> Project:
    project = get_project(db, user, project_id)
    if not _can_write(user, project, db):
        raise _forbidden()
    for key in ("name", "plz", "typ", "leistung_kw", "description"):
        if key in payload and payload[key] is not None:
            setattr(project, key, payload[key])
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
