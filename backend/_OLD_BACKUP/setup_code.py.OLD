import os

def w(path, content):
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'OK {path}')

for p in ['db/__init__.py', 'api/__init__.py', 'services/__init__.py', 'audit/__init__.py']:
    w(p, '')

w('db/database.py', """from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./gridcheck.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""")

w('db/models.py', """from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text
from datetime import datetime, timezone
from .database import Base
import hashlib, json

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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class CheckResult(Base):
    __tablename__ = "check_results"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)
    spannungsband_ok = Column(Boolean)
    thermische_auslastung_ok = Column(Boolean)
    kurzschluss_ok = Column(Boolean)
    n1_ok = Column(Boolean)
    netzebene = Column(String)
    empfehlung = Column(Text)
    details = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    detail = Column(Text)
    checksum = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def make_checksum(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()
""")

w('services/netzcheck.py', """def berechne_netzcheck(typ, leistung_kw, plz, spannung_kv=None):
    score = 100
    empfehlungen = []

    if leistung_kw <= 30:
        netzebene = "NS (0.4 kV)"
        max_kap = 30
    elif leistung_kw <= 500:
        netzebene = "MS (10/20 kV)"
        max_kap = 500
    elif leistung_kw <= 50000:
        netzebene = "HS (110 kV)"
        max_kap = 50000
    else:
        netzebene = "HoeS (220/380 kV)"
        max_kap = 999999

    auslastung = leistung_kw / max_kap
    spannungsband_ok = auslastung < 0.9
    if not spannungsband_ok:
        score -= 25
        empfehlungen.append("Spannungsband kritisch - Trafoausbau pruefen")

    thermisch_ok = auslastung < 0.8
    if not thermisch_ok:
        score -= 25
        empfehlungen.append("Thermische Auslastung hoch - Leitungsausbau noetig")

    kurzschluss_ok = leistung_kw < max_kap * 0.7
    if not kurzschluss_ok:
        score -= 20
        empfehlungen.append("Kurzschlussleistung nicht ausreichend")

    n1_ok = auslastung < 0.5
    if not n1_ok:
        score -= 15
        empfehlungen.append("N-1 Kriterium kritisch - Redundanz pruefen")

    if not empfehlungen:
        empfehlungen.append("Netzanschluss voraussichtlich realisierbar")

    details = {"auslastung_prozent": round(auslastung * 100, 1), "max_kapazitaet_kw": max_kap, "netzebene": netzebene}

    return {"score": max(0, score), "spannungsband_ok": spannungsband_ok, "thermische_auslastung_ok": thermisch_ok, "kurzschluss_ok": kurzschluss_ok, "n1_ok": n1_ok, "netzebene": netzebene, "empfehlung": "; ".join(empfehlungen), "details": details}
""")

w('api/routes.py', """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Project, CheckResult, AuditLog, make_checksum
from services.netzcheck import berechne_netzcheck
from pydantic import BaseModel
from typing import Optional
import json

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    plz: str
    ort: Optional[str] = None
    typ: str
    leistung_kw: float
    spannung_kv: Optional[float] = None
    einspeiseart: Optional[str] = "Volleinspeisung"

@router.post("/api/check")
def run_check(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**data.dict())
    db.add(project)
    db.commit()
    db.refresh(project)
    result = berechne_netzcheck(data.typ, data.leistung_kw, data.plz, data.spannung_kv)
    check = CheckResult(project_id=project.id, score=result["score"], spannungsband_ok=result["spannungsband_ok"], thermische_auslastung_ok=result["thermische_auslastung_ok"], kurzschluss_ok=result["kurzschluss_ok"], n1_ok=result["n1_ok"], netzebene=result["netzebene"], empfehlung=result["empfehlung"], details=json.dumps(result["details"]))
    db.add(check)
    db.commit()
    audit = AuditLog(project_id=project.id, action="CHECK_CREATED", detail=json.dumps(result), checksum=make_checksum(result))
    db.add(audit)
    db.commit()
    return {"project_id": project.id, **result}

@router.get("/api/result/{project_id}")
def get_result(project_id: int, db: Session = Depends(get_db)):
    check = db.query(CheckResult).filter(CheckResult.project_id == project_id).first()
    if not check:
        return {"error": "Not found"}
    return {"project_id": check.project_id, "score": check.score, "spannungsband_ok": check.spannungsband_ok, "thermische_auslastung_ok": check.thermische_auslastung_ok, "kurzschluss_ok": check.kurzschluss_ok, "n1_ok": check.n1_ok, "netzebene": check.netzebene, "empfehlung": check.empfehlung, "details": json.loads(check.details) if check.details else {}}

@router.get("/api/audit/{project_id}")
def get_audit(project_id: int, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(AuditLog.project_id == project_id).all()
    return [{"id": l.id, "timestamp": str(l.timestamp), "action": l.action, "detail": l.detail, "checksum": l.checksum} for l in logs]
""")

w('main.py', """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import engine, Base
from api.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="GridCheck API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/")
def root():
    return {"status": "GridCheck API running", "version": "1.0.0"}
""")

print("FERTIG - Alle Dateien erstellt")
