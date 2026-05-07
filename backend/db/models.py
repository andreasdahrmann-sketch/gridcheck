from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base
import hashlib, json


def make_checksum(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_deleted_at", "deleted_at"),
        Index("ix_projects_owner_deleted_updated", "owner_user_id", "deleted_at", "updated_at"),
    )
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plz = Column(String(5), nullable=False)
    ort = Column(String, nullable=True)
    typ = Column(String, nullable=False)
    leistung_kw = Column(Float, nullable=False)
    spannung_kv = Column(Float, nullable=True)
    einspeiseart = Column(String, default="Volleinspeisung")
    skv_mva = Column(Float, nullable=True)
    bestehende_einspeisung_kw = Column(Float, default=0)
    leitungstyp = Column(String, default="NAYY 150")
    leitungslaenge_km = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # --- NEU: Rollen-Erweiterung (additiv, keine Breaking Changes) ---
    role = Column(String, default="projektierer")           # projektierer | netzbetreiber | admin
    role_inputs = Column(Text, default="{}")                # JSON: rollenspez. Eingaben
    role_results = Column(Text, default="{}")               # JSON: rollenspez. Ergebnisse
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    description = Column(Text, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True)

    checks = relationship("CheckResult", back_populates="project")
    audits = relationship("AuditLog", back_populates="project")
    owner = relationship("User", back_populates="owned_projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")


class CheckResult(Base):
    __tablename__ = "check_results"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    score = Column(Integer, nullable=False)
    spannungsband_ok = Column(Boolean)
    thermische_auslastung_ok = Column(Boolean)
    kurzschluss_ok = Column(Boolean)
    n1_ok = Column(Boolean)
    netzebene = Column(String)
    empfehlung = Column(Text)
    details = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="checks")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    action = Column(String, nullable=False)
    detail = Column(Text)
    checksum = Column(String)

    project = relationship("Project", back_populates="audits")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="endkunde")
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owned_projects = relationship("Project", back_populates="owner")
    memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    uploaded_files = relationship("ProjectFile", back_populates="uploader")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_role = Column(String, nullable=False, default="viewer")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="memberships")


class ProjectFile(Base):
    __tablename__ = "project_files"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(Text, nullable=False)
    checksum = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="files")
    uploader = relationship("User", back_populates="uploaded_files")

