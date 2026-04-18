from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import SessionLocal
from app.models.project import Project, NetzbetreiberPrio, Duplikatcheck
from datetime import datetime
import hashlib, json

router = APIRouter(prefix="/api/projects", tags=["projects"])

EINSATZZWECKE = [
    "Eigenverbrauch", "Netzstabilisierung", "Direktvermarktung",
    "Regelenergie", "Inselbetrieb", "E-Mobilitaet-Laden",
    "Waermeversorgung", "Industrieprozess", "Quartiersversorgung"
]
ANLAGENTYPEN = [
    "PV-Freiflaeche", "PV-Dach", "Wind", "BESS",
    "Biogas", "Wasserstoff", "Waermepumpe", "Ladesaeule", "KWK"
]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === SCHEMAS ===

class ProjectCreate(BaseModel):
    name: str
    plz: str
    leistung_kw: float
    spannung_kv: float
    typ: str
    einsatzzweck: Optional[str] = "Eigenverbrauch"
    anlagentyp: Optional[str] = "PV-Freiflaeche"
    co2_relevanz: Optional[str] = "mittel"
    netzdienlichkeit_selbst: Optional[str] = "mittel"
    zeitdruck: Optional[str] = "normal"
    bereits_beantragt_bei: Optional[List[str]] = []
    erstellt_von: Optional[str] = "system"

class ProjectOut(BaseModel):
    id: int
    name: str
    plz: str
    leistung_kw: float
    spannung_kv: float
    typ: str
    einsatzzweck: Optional[str]
    anlagentyp: Optional[str]
    co2_relevanz: Optional[str]
    netzdienlichkeit_selbst: Optional[str]
    zeitdruck: Optional[str]
    bereits_beantragt_bei: Optional[str]
    anzahl_bisherige_antraege: Optional[int]
    ampel: Optional[str]
    ergebnis: Optional[str]
    empfehlungen: Optional[str]
    n1_bestanden: Optional[bool]
    prioritaets_score: Optional[float]
    zeitstempel: str
    hash: str
    class Config:
        from_attributes = True

class PrioCreate(BaseModel):
    netzbetreiber_name: str
    prio_netzdienlichkeit: int = 5
    prio_co2: int = 5
    prio_versorgungssicherheit: int = 5
    prio_regionaler_bedarf: int = 5
    prio_zeitdruck: int = 3
    bevorzugte_anlagentypen: Optional[List[str]] = []
    bevorzugte_einsatzzwecke: Optional[List[str]] = []

class PrioOut(BaseModel):
    id: int
    netzbetreiber_name: str
    prio_netzdienlichkeit: int
    prio_co2: int
    prio_versorgungssicherheit: int
    prio_regionaler_bedarf: int
    prio_zeitdruck: int
    bevorzugte_anlagentypen: Optional[str]
    bevorzugte_einsatzzwecke: Optional[str]
    class Config:
        from_attributes = True

# === HELPER ===

def berechne_hash(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()

def duplikat_fingerprint(plz: str, leistung_kw: float, anlagentyp: str) -> str:
    raw = f"{plz}|{round(leistung_kw, -1)}|{anlagentyp}"
    return hashlib.sha256(raw.encode()).hexdigest()

def berechne_prioritaets_score(p: ProjectCreate, prio: NetzbetreiberPrio) -> float:
    """Score 0-100 basierend auf NB-Gewichtung und Projekt-Eigenschaften"""
    score = 0.0
    max_score = 0.0

    # Netzdienlichkeit
    nd_map = {"hoch": 10, "mittel": 5, "gering": 2}
    nd_wert = nd_map.get(p.netzdienlichkeit_selbst, 5)
    score += nd_wert * prio.prio_netzdienlichkeit
    max_score += 10 * prio.prio_netzdienlichkeit

    # CO2
    co2_map = {"hoch": 10, "mittel": 5, "gering": 2}
    co2_wert = co2_map.get(p.co2_relevanz, 5)
    score += co2_wert * prio.prio_co2
    max_score += 10 * prio.prio_co2

    # Zeitdruck
    zd_map = {"kritisch": 10, "eilig": 7, "normal": 3}
    zd_wert = zd_map.get(p.zeitdruck, 3)
    score += zd_wert * prio.prio_zeitdruck
    max_score += 10 * prio.prio_zeitdruck

    # Bevorzugter Anlagentyp
    bev_typen = json.loads(prio.bevorzugte_anlagentypen or "[]")
    if p.anlagentyp in bev_typen:
        score += 10 * prio.prio_regionaler_bedarf
    max_score += 10 * prio.prio_regionaler_bedarf

    # Bevorzugter Einsatzzweck
    bev_zwecke = json.loads(prio.bevorzugte_einsatzzwecke or "[]")
    if p.einsatzzweck in bev_zwecke:
        score += 10 * prio.prio_versorgungssicherheit
    max_score += 10 * prio.prio_versorgungssicherheit

    return round((score / max_score) * 100, 1) if max_score > 0 else 50.0

def netzanalyse(p: ProjectCreate) -> dict:
    issues = []
    empfehlungen = []
    n1_ok = True

    if p.spannung_kv == 0.4:
        if p.leistung_kw > 100:
            issues.append("Leistung zu hoch fuer NS-Netz (max ~100kW)")
            empfehlungen.append("Wechsel auf MS-Ebene (10/20kV) empfohlen")
            n1_ok = False
        elif p.leistung_kw > 70:
            issues.append("Grenzbereich NS-Netz, Trafopruefung noetig")
            empfehlungen.append("Trafoauslastung und Leitungsquerschnitt pruefen")
    elif p.spannung_kv in [10, 20]:
        if p.leistung_kw > 20000:
            issues.append("Leistung zu hoch fuer MS-Netz")
            empfehlungen.append("HS-Anschluss (110kV) erforderlich")
            n1_ok = False
        elif p.leistung_kw > 10000:
            issues.append("N-1: Redundanz im MS-Netz pruefen")
            empfehlungen.append("Zweite Einspeisung oder Ringschluss empfohlen")
    elif p.spannung_kv == 110:
        if p.leistung_kw > 200000:
            issues.append("Leistung kritisch fuer 110kV-Ebene")
            empfehlungen.append("HoeS-Anschluss oder Netzteilung pruefen")
            n1_ok = False
        elif p.leistung_kw > 100000:
            issues.append("N-1: Transformator-Redundanz erforderlich")
            empfehlungen.append("Doppelsammelschiene und Reservetrafo vorsehen")

    skv_min = {"0.4": 5, "10": 100, "20": 200, "110": 2000}
    sk = skv_min.get(str(p.spannung_kv), 100)
    verhaeltnis = (sk * 1000) / p.leistung_kw if p.leistung_kw > 0 else 999
    if verhaeltnis < 20:
        issues.append(f"Sk/P-Verhaeltnis={verhaeltnis:.1f} zu gering (min 20)")
        empfehlungen.append("Netzverstaerkung oder Blindleistungskompensation")
        n1_ok = False
    elif verhaeltnis < 50:
        empfehlungen.append(f"Sk/P={verhaeltnis:.1f} - Oberschwingungsanalyse empfohlen")

    if not issues:
        ampel = "gruen"
        ergebnis = "Netzanschluss technisch machbar"
    elif n1_ok:
        ampel = "gelb"
        ergebnis = "Machbar mit Auflagen"
    else:
        ampel = "rot"
        ergebnis = "Netzanschluss kritisch - Massnahmen erforderlich"

    return {
        "ampel": ampel, "ergebnis": ergebnis,
        "n1_bestanden": n1_ok,
        "empfehlungen": "; ".join(empfehlungen) if empfehlungen else "Keine"
    }

# === ROUTES ===

@router.get("/optionen")
def get_optionen():
    return {"einsatzzwecke": EINSATZZWECKE, "anlagentypen": ANLAGENTYPEN}

@router.post("/", response_model=ProjectOut)
def create_project(p: ProjectCreate, db: Session = Depends(get_db)):
    analyse = netzanalyse(p)

    # Duplikatcheck
    fp = duplikat_fingerprint(p.plz, p.leistung_kw, p.anlagentyp or "")
    dup = db.query(Duplikatcheck).filter(Duplikatcheck.fingerprint == fp).first()
    anzahl_vorher = 0
    if dup:
        dup.anzahl += 1
        anzahl_vorher = dup.anzahl
    else:
        dup = Duplikatcheck(
            plz=p.plz, leistung_kw=p.leistung_kw,
            anlagentyp=p.anlagentyp or "", fingerprint=fp,
            project_ids="[]", anzahl=1
        )
        db.add(dup)
        anzahl_vorher = 1

    # Prioritaets-Score (erster NB oder Default)
    nb_prio = db.query(NetzbetreiberPrio).first()
    prio_score = berechne_prioritaets_score(p, nb_prio) if nb_prio else 50.0

    hash_data = {
        "name": p.name, "plz": p.plz, "leistung_kw": p.leistung_kw,
        "spannung_kv": p.spannung_kv, "typ": p.typ,
        "einsatzzweck": p.einsatzzweck, "anlagentyp": p.anlagentyp,
        "ergebnis": analyse["ergebnis"]
    }

    projekt = Project(
        name=p.name, plz=p.plz, leistung_kw=p.leistung_kw,
        spannung_kv=p.spannung_kv, typ=p.typ,
        einsatzzweck=p.einsatzzweck, anlagentyp=p.anlagentyp,
        co2_relevanz=p.co2_relevanz,
        netzdienlichkeit_selbst=p.netzdienlichkeit_selbst,
        zeitdruck=p.zeitdruck,
        bereits_beantragt_bei=json.dumps(p.bereits_beantragt_bei or []),
        anzahl_bisherige_antraege=anzahl_vorher,
        ampel=analyse["ampel"], ergebnis=analyse["ergebnis"],
        n1_bestanden=analyse["n1_bestanden"],
        empfehlungen=analyse["empfehlungen"],
        prioritaets_score=prio_score,
        zeitstempel=datetime.utcnow().isoformat(),
        hash=berechne_hash(hash_data),
        erstellt_von=p.erstellt_von
    )
    db.add(projekt)
    db.commit()
    db.refresh(projekt)

    # Duplikat project_ids aktualisieren
    ids = json.loads(dup.project_ids or "[]")
    ids.append(projekt.id)
    dup.project_ids = json.dumps(ids)
    db.commit()

    return projekt

@router.get("/", response_model=List[ProjectOut])
def list_projects(sortby: str = "score", db: Session = Depends(get_db)):
    q = db.query(Project).filter(Project.is_archived == False)
    if sortby == "score":
        q = q.order_by(Project.prioritaets_score.desc())
    elif sortby == "zeit":
        q = q.order_by(Project.id.desc())
    elif sortby == "duplikate":
        q = q.order_by(Project.anzahl_bisherige_antraege.desc())
    else:
        q = q.order_by(Project.id.desc())
    return q.all()

@router.get("/duplikate")
def list_duplikate(db: Session = Depends(get_db)):
    return db.query(Duplikatcheck).filter(Duplikatcheck.anzahl > 1).all()

@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return p

# === NETZBETREIBER PRIO ===

nb_router = APIRouter(prefix="/api/netzbetreiber", tags=["netzbetreiber"])

@nb_router.post("/prio", response_model=PrioOut)
def set_prio(p: PrioCreate, db: Session = Depends(get_db)):
    existing = db.query(NetzbetreiberPrio).filter(
        NetzbetreiberPrio.netzbetreiber_name == p.netzbetreiber_name
    ).first()
    data = {
        "prio_netzdienlichkeit": p.prio_netzdienlichkeit,
        "prio_co2": p.prio_co2,
        "prio_versorgungssicherheit": p.prio_versorgungssicherheit,
        "prio_regionaler_bedarf": p.prio_regionaler_bedarf,
        "prio_zeitdruck": p.prio_zeitdruck,
        "bevorzugte_anlagentypen": json.dumps(p.bevorzugte_anlagentypen or []),
        "bevorzugte_einsatzzwecke": json.dumps(p.bevorzugte_einsatzzwecke or []),
    }
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        nb = NetzbetreiberPrio(netzbetreiber_name=p.netzbetreiber_name, **data)
        db.add(nb)
        db.commit()
        db.refresh(nb)
        return nb

@nb_router.get("/prio", response_model=List[PrioOut])
def get_prios(db: Session = Depends(get_db)):
    return db.query(NetzbetreiberPrio).all()
