from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base
import hashlib, json


def make_checksum(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


class Project(Base):
    __tablename__ = "projects"
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

    checks = relationship("CheckResult", back_populates="project")
    audits = relationship("AuditLog", back_populates="project")


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
