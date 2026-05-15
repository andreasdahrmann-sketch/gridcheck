from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from app.db.database import get_db
from app.models.project import (
    Project, Calculation, Snapshot, Report, Comment, User, Netzbetreiber,
    KITrainingData, PlantType, VoltageLevel, TrafficLight, UserRole, ProjectStatus
)
import json, math, hashlib, os

router = APIRouter(prefix='/api/v1', tags=['gridcheck'])

# ============================================================
# SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    company: str = ''
    role: UserRole = UserRole.PROJEKTIERER

class LoginRequest(BaseModel):
    email: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    plz: str = Field(pattern=r'^\d{5}$')
    power_kw: float = Field(gt=0, le=50000)
    plant_type: PlantType
    voltage_kv: VoltageLevel = VoltageLevel.MS_20
    cos_phi: float = Field(default=0.95, ge=0.8, le=1.0)
    einspeiseprofil: str = 'volleinspeisung'
    gleichzeitigkeitsfaktor: float = Field(default=1.0, ge=0.1, le=1.0)
    address: str = ''
    notes: str = ''

class QuestionnaireSubmit(BaseModel):
    project_id: int
    answers: dict  # Rollenspezifische Antworten

class CalcRequest(BaseModel):
    project_id: int
    sk_mv: float = Field(default=250.0, ge=50, le=2000)
    cable_type: str = Field(default='NA2XS2Y_1x240')
    cable_length_km: float = Field(default=5.0, ge=0.1, le=50)
    transformer_sn_kva: float = Field(default=40000, ge=100, le=300000)
    uk_percent: float = Field(default=12.0, ge=4, le=20)
    existing_load_kw: float = Field(default=0)
    run_n1: bool = True
    run_sensitivity: bool = True

class StatusUpdate(BaseModel):
    status: ProjectStatus
    comment: str = ''

class CommentCreate(BaseModel):
    text: str
    is_internal: bool = False

# ============================================================
# FRAGEBOGEN-DEFINITIONEN (pro Rolle & Anlagentyp)
# ============================================================

QUESTIONNAIRES = {
    'projektierer': {
        'pv': [
            {'id':'pv_modules','label':'Anzahl Module','type':'number','required':True},
            {'id':'pv_inverter_kva','label':'Wechselrichter-Leistung (kVA)','type':'number','required':True},
            {'id':'pv_orientation','label':'Ausrichtung','type':'select','options':['Süd','Ost-West','Nachführung'],'required':True},
            {'id':'pv_tilt','label':'Neigungswinkel (°)','type':'number','required':False},
            {'id':'pv_area_m2','label':'Fläche (m²)','type':'number','required':True},
            {'id':'feed_in_type','label':'Einspeiseart','type':'select','options':['Volleinspeisung','Überschusseinspeisung','Eigenverbrauch'],'required':True},
            {'id':'storage_kwh','label':'Speicher vorhanden? (kWh, 0=nein)','type':'number','required':False},
        ],
        'wind': [
            {'id':'wea_count','label':'Anzahl WEA','type':'number','required':True},
            {'id':'wea_type','label':'WEA-Typ/Hersteller','type':'text','required':True},
            {'id':'wea_rated_kw','label':'Nennleistung pro WEA (kW)','type':'number','required':True},
            {'id':'hub_height_m','label':'Nabenhöhe (m)','type':'number','required':True},
            {'id':'rotor_diameter_m','label':'Rotordurchmesser (m)','type':'number','required':True},
            {'id':'wind_zone','label':'Windzone (DIBt)','type':'select','options':['WZ1','WZ2','WZ3','WZ4'],'required':True},
        ],
        'battery': [
            {'id':'bat_capacity_kwh','label':'Speicherkapazität (kWh)','type':'number','required':True},
            {'id':'bat_power_kw','label':'Lade-/Entladeleistung (kW)','type':'number','required':True},
            {'id':'bat_cycles','label':'Lade-/Entladezyklen pro Tag','type':'number','required':True},
            {'id':'bat_technology','label':'Technologie','type':'select','options':['Lithium-Ion','Redox-Flow','NaS','Andere'],'required':True},
            {'id':'bat_purpose','label':'Zweck','type':'select','options':['Arbitrage','Regelenergie','PV-Speicher','Netzstützung'],'required':True},
        ],
        'charging': [
            {'id':'cp_count','label':'Anzahl Ladepunkte','type':'number','required':True},
            {'id':'cp_power_kw','label':'Leistung pro Ladepunkt (kW)','type':'number','required':True},
            {'id':'cp_type','label':'Typ','type':'select','options':['AC 11kW','AC 22kW','DC 50kW','DC 150kW','DC 300kW','HPC 400kW'],'required':True},
            {'id':'cp_gleichzeitig','label':'Gleichzeitigkeitsfaktor','type':'number','required':True},
            {'id':'cp_storage','label':'Pufferspeicher (kWh, 0=nein)','type':'number','required':False},
        ],
        'industry': [
            {'id':'ind_process','label':'Hauptprozess','type':'text','required':True},
            {'id':'ind_peak_kw','label':'Spitzenlast (kW)','type':'number','required':True},
            {'id':'ind_base_kw','label':'Grundlast (kW)','type':'number','required':True},
            {'id':'ind_shifts','label':'Schichtbetrieb','type':'select','options':['1-Schicht','2-Schicht','3-Schicht/24h'],'required':True},
            {'id':'ind_motors_kw','label':'Größter Einzelmotor (kW)','type':'number','required':False},
            {'id':'ind_harmonics','label':'Oberschwingungen erwartet?','type':'select','options':['Nein','Gering','Erheblich'],'required':True},
        ],
        'heat_pump': [
            {'id':'hp_count','label':'Anzahl Wärmepumpen','type':'number','required':True},
            {'id':'hp_power_kw','label':'Elektrische Leistung gesamt (kW)','type':'number','required':True},
            {'id':'hp_type','label':'Typ','type':'select','options':['Luft-Wasser','Sole-Wasser','Wasser-Wasser','Großwärmepumpe'],'required':True},
            {'id':'hp_bivalent','label':'Bivalenter Betrieb?','type':'select','options':['Ja','Nein'],'required':True},
        ],
    },
    'netzbetreiber': {
        '_common': [
            {'id':'nb_netzgebiet','label':'Netzgebiet/Umspannwerk','type':'text','required':True},
            {'id':'nb_abgang','label':'Abgang/Leitung','type':'text','required':True},
            {'id':'nb_sk_gemessen','label':'Gemessene Sk am VAP (MVA)','type':'number','required':False},
            {'id':'nb_existing_capacity_kw','label':'Bereits vergeben (kW)','type':'number','required':True},
            {'id':'nb_planned_kw','label':'Weitere Anfragen (kW)','type':'number','required':False},
            {'id':'nb_netzausbau','label':'Netzausbau geplant?','type':'select','options':['Nein','Ja, kurzfristig','Ja, mittelfristig'],'required':True},
            {'id':'nb_constraints','label':'Besondere Restriktionen','type':'text','required':False},
        ]
    }
}

# ============================================================
# KABELTYPEN-DATENBANK
# ============================================================
CABLE_DATA = {
    'NA2XS2Y_1x240': {'r':0.125,'x':0.11,'iz':420,'label':'NA2XS2Y 1x240mm²'},
    'NA2XS2Y_1x185': {'r':0.164,'x':0.11,'iz':355,'label':'NA2XS2Y 1x185mm²'},
    'NA2XS2Y_1x150': {'r':0.206,'x':0.12,'iz':315,'label':'NA2XS2Y 1x150mm²'},
    'NAYY_1x240':    {'r':0.125,'x':0.08,'iz':400,'label':'NAYY 1x240mm²'},
    'NA2XS2Y_1x400': {'r':0.078,'x':0.10,'iz':530,'label':'NA2XS2Y 1x400mm²'},
    'N2XS2Y_1x240':  {'r':0.077,'x':0.11,'iz':530,'label':'N2XS2Y 1x240mm² (Cu)'},
}

# ============================================================
# KERN-BERECHNUNG
# ============================================================
def calc_ms_grid(p: CalcRequest, proj: Project) -> dict:
    u_kv = float(proj.voltage_kv.replace('kV',''))
    cos_phi = proj.cos_phi or 0.95
    sin_phi = math.sqrt(1 - cos_phi**2)
    p_kw = proj.power_kw
    g_faktor = proj.gleichzeitigkeitsfaktor or 1.0
    p_eff = p_kw * g_faktor
    s_kva = p_eff / cos_phi
    s_mva = s_kva / 1000
    p_mw = p_eff / 1000

    # Kurzschluss
    sk_vap = p.sk_mv
    ik_vap_ka = sk_vap / (math.sqrt(3) * u_kv)

    # Kabel
    cd = CABLE_DATA.get(p.cable_type, CABLE_DATA['NA2XS2Y_1x240'])
    r_cable = cd['r'] * p.cable_length_km
    x_cable = cd['x'] * p.cable_length_km
    z_cable = math.sqrt(r_cable**2 + x_cable**2)
    i_max_cable = cd['iz']

    # Trafo
    z_trafo = (p.uk_percent / 100) * (u_kv**2) / (p.transformer_sn_kva / 1000)
    s_trafo_mva = p.transformer_sn_kva / 1000

    # Impedanzen
    z_netz = u_kv**2 / sk_vap
    z_ges = z_netz + z_cable + z_trafo

    # Sk am Anschlusspunkt
    sk_ap = u_kv**2 / z_ges

    # Leistungsverhältnis
    sk_ratio_limit = 0.02  # 1/50
    sk_ratio = s_mva / sk_ap

    # Spannungsänderung
    delta_u = (p_eff * (r_cable * cos_phi + x_cable * sin_phi)) / (u_kv**2 * 1000) * 100
    delta_u_limit = 2.0

    # Betriebsstrom
    i_betrieb = s_kva / (math.sqrt(3) * u_kv)
    i_existing = (p.existing_load_kw / cos_phi) / (math.sqrt(3) * u_kv) if p.existing_load_kw > 0 else 0
    i_total = i_betrieb + i_existing
    thermal_pct = (i_total / i_max_cable) * 100

    # Trafo-Auslastung
    s_existing = p.existing_load_kw / cos_phi / 1000 if p.existing_load_kw > 0 else 0
    trafo_load = ((s_mva + s_existing) / s_trafo_mva) * 100

    # Checks
    checks = {
        'sk_ratio': sk_ratio < sk_ratio_limit,
        'delta_u': abs(delta_u) < delta_u_limit,
        'thermal': thermal_pct < 80,
        'trafo': trafo_load < 80,
    }

    fail_count = sum(1 for v in checks.values() if not v)
    if fail_count == 0:
        ampel = TrafficLight.GREEN
    elif fail_count <= 2 and checks.get('sk_ratio', False):
        ampel = TrafficLight.YELLOW
    else:
        ampel = TrafficLight.RED

    result = {
        'power_kw': round(p_eff, 1),
        'power_mva': round(s_mva, 4),
        'voltage_kv': u_kv,
        'cos_phi': cos_phi,
        'gleichzeitigkeitsfaktor': g_faktor,
        'sk_vap_mva': round(sk_vap, 2),
        'sk_ap_mva': round(sk_ap, 2),
        'ik_vap_ka': round(ik_vap_ka, 2),
        'sk_ratio': round(sk_ratio, 6),
        'sk_ratio_limit': sk_ratio_limit,
        'sk_ratio_ok': checks['sk_ratio'],
        'delta_u_percent': round(delta_u, 4),
        'delta_u_limit': delta_u_limit,
        'delta_u_ok': checks['delta_u'],
        'i_betrieb_a': round(i_betrieb, 2),
        'i_existing_a': round(i_existing, 2),
        'i_total_a': round(i_total, 2),
        'i_max_cable_a': i_max_cable,
        'thermal_total_percent': round(thermal_pct, 2),
        'thermal_ok': checks['thermal'],
        'trafo_sn_mva': s_trafo_mva,
        'trafo_load_percent': round(trafo_load, 2),
        'trafo_ok': checks['trafo'],
        'z_netz_ohm': round(z_netz, 4),
        'z_cable_ohm': round(z_cable, 4),
        'z_trafo_ohm': round(z_trafo, 4),
        'z_gesamt_ohm': round(z_ges, 4),
        'cable_r_total': round(r_cable, 4),
        'cable_x_total': round(x_cable, 4),
        'cable_type': p.cable_type,
        'cable_length_km': p.cable_length_km,
        'ampel': ampel.value,
        'checks': checks,
    }

    return result

# ============================================================
# N-1 ANALYSE
# ============================================================
def run_n1_analysis(base_result: dict, p: CalcRequest, proj: Project) -> dict:
    """Simuliert Ausfall einzelner Betriebsmittel"""
    scenarios = {}
    
    # N-1: Parallelkabel fällt aus (doppelte Impedanz)
    p_mod = CalcRequest(**p.model_dump())
    # Simuliere: nur 1 Kabel statt 2 → verdoppelte Kabellänge als Proxy
    original_length = p.cable_length_km
    
    # Szenario 1: Kabelausfall → alternative Route +50% Länge
    p_mod.cable_length_km = original_length * 1.5
    s1 = calc_ms_grid(p_mod, proj)
    scenarios['kabel_n1'] = {
        'name': 'Kabelausfall (Umschaltung +50%)',
        'delta_u': s1['delta_u_percent'],
        'thermal': s1['thermal_total_percent'],
        'ampel': s1['ampel'],
        'ok': s1['checks']['delta_u'] and s1['checks']['thermal']
    }
    
    # Szenario 2: Trafo-Ausfall → nächstkleinerer Trafo (50%)
    p_mod2 = CalcRequest(**p.model_dump())
    p_mod2.transformer_sn_kva = p.transformer_sn_kva * 0.5
    s2 = calc_ms_grid(p_mod2, proj)
    scenarios['trafo_n1'] = {
        'name': 'Trafo-Ausfall (50% Kapazität)',
        'delta_u': s2['delta_u_percent'],
        'thermal': s2['thermal_total_percent'],
        'trafo_load': s2['trafo_load_percent'],
        'ampel': s2['ampel'],
        'ok': s2['trafo_load_percent'] < 120  # Kurzzeitig 120% erlaubt
    }
    
    # Szenario 3: Max Einspeisung + Max Last gleichzeitig
    p_mod3 = CalcRequest(**p.model_dump())
    p_mod3.existing_load_kw = p.existing_load_kw + proj.power_kw * 0.3
    s3 = calc_ms_grid(p_mod3, proj)
    scenarios['worst_case'] = {
        'name': 'Worst Case (max. Gleichzeitigkeit)',
        'delta_u': s3['delta_u_percent'],
        'thermal': s3['thermal_total_percent'],
        'ampel': s3['ampel'],
        'ok': s3['ampel'] != 'red'
    }
    
    n1_ok = all(s.get('ok', False) for s in scenarios.values())
    
    return {
        'n1_ok': n1_ok,
        'scenarios': scenarios
    }

# ============================================================
# SENSITIVITAETSANALYSE
# ============================================================
def run_sensitivity(p: CalcRequest, proj: Project) -> dict:
    """Variiert Parameter um ±20% und zeigt Einfluss"""
    base = calc_ms_grid(p, proj)
    params = {
        'sk_mv': ('Sk (MVA)', p.sk_mv),
        'cable_length_km': ('Kabellänge (km)', p.cable_length_km),
        'transformer_sn_kva': ('Trafo (kVA)', p.transformer_sn_kva),
        'existing_load_kw': ('Bestandslast (kW)', max(p.existing_load_kw, 100)),
    }
    
    sensitivity = {}
    for key, (label, base_val) in params.items():
        results = []
        for factor in [0.8, 0.9, 1.0, 1.1, 1.2]:
            p_mod = CalcRequest(**p.model_dump())
            setattr(p_mod, key, base_val * factor)
            # Clamp
            if key == 'sk_mv': p_mod.sk_mv = max(50, min(2000, p_mod.sk_mv))
            if key == 'cable_length_km': p_mod.cable_length_km = max(0.1, p_mod.cable_length_km)
            r = calc_ms_grid(p_mod, proj)
            results.append({
                'factor': factor,
                'value': round(base_val * factor, 2),
                'delta_u': r['delta_u_percent'],
                'thermal': r['thermal_total_percent'],
                'sk_ratio': r['sk_ratio'],
                'ampel': r['ampel']
            })
        sensitivity[key] = {'label': label, 'results': results}
    
    return sensitivity

# ============================================================
# KI-EMPFEHLUNGEN
# ============================================================
def generate_recommendations(result: dict, n1: dict, proj: Project) -> list:
    """Generiert konkrete Handlungsempfehlungen"""
    recs = []
    
    if not result['checks']['sk_ratio']:
        recs.append({
            'severity': 'high',
            'category': 'Netzkapazität',
            'text': f"Sk-Verhältnis {result['sk_ratio']*100:.2f}% überschreitet 2%. Höhere Spannungsebene oder näheren Anschlusspunkt prüfen.",
            'action': 'Anschluss an stärkeren Netzknoten oder 110kV prüfen'
        })
    
    if not result['checks']['delta_u']:
        recs.append({
            'severity': 'high',
            'category': 'Spannungshaltung',
            'text': f"Δu = {result['delta_u_percent']:.2f}% > {result['delta_u_limit']}%. Kürzere Leitung oder größerer Querschnitt empfohlen.",
            'action': f"Kabelquerschnitt erhöhen oder Leitungslänge auf < {result['cable_length_km']*0.7:.1f} km reduzieren"
        })
    
    if not result['checks']['thermal']:
        recs.append({
            'severity': 'high',
            'category': 'Thermische Belastung',
            'text': f"Kabel zu {result['thermal_total_percent']:.1f}% ausgelastet. Größerer Querschnitt oder Parallelkabel nötig.",
            'action': 'NA2XS2Y 1x400mm² oder Doppelkabel verwenden'
        })
    
    if not result['checks']['trafo']:
        recs.append({
            'severity': 'medium',
            'category': 'Trafo-Kapazität',
            'text': f"Trafo zu {result['trafo_load_percent']:.1f}% ausgelastet. Größeren Trafo oder zusätzlichen Trafo vorsehen.",
            'action': f"Trafo >= {result['power_mva']*1000/0.7:.0f} kVA empfohlen"
        })
    
    if n1 and not n1.get('n1_ok', True):
        failed = [s['name'] for k,s in n1.get('scenarios',{}).items() if not s.get('ok',True)]
        recs.append({
            'severity': 'medium',
            'category': 'N-1 Sicherheit',
            'text': f"N-1 Analyse nicht bestanden: {', '.join(failed)}",
            'action': 'Redundante Leitungsführung oder Lastmanagement implementieren'
        })
    
    if result['checks']['sk_ratio'] and result['sk_ratio'] > 0.015:
        recs.append({
            'severity': 'low',
            'category': 'Hinweis',
            'text': f"Sk-Verhältnis bei {result['sk_ratio']*100:.2f}% – nahe am Grenzwert. Flicker-Nachweis nach VDE-AR-N 4110 erforderlich.",
            'action': 'Flicker-Berechnung durchführen'
        })
    
    if not recs:
        recs.append({
            'severity': 'info',
            'category': 'Bewertung',
            'text': 'Alle Kriterien erfüllt. Netzanschluss voraussichtlich ohne Maßnahmen möglich.',
            'action': 'Netzanschlussantrag beim Netzbetreiber einreichen'
        })
    
    return recs

# ============================================================
# ENDPOINTS
# ============================================================

# --- Auth (vereinfacht) ---
@router.post('/auth/register')
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, 'Email existiert bereits')
    pw_hash = hashlib.sha256(data.password.encode()).hexdigest()
    user = User(email=data.email, password_hash=pw_hash, name=data.name, company=data.company, role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {'id': user.id, 'email': user.email, 'role': user.role.value, 'name': user.name}

@router.post('/auth/login')
def login(data: LoginRequest, db: Session = Depends(get_db)):
    pw_hash = hashlib.sha256(data.password.encode()).hexdigest()
    user = db.query(User).filter(User.email == data.email, User.password_hash == pw_hash).first()
    if not user: raise HTTPException(401, 'Ungültige Anmeldedaten')
    return {'id': user.id, 'email': user.email, 'role': user.role.value, 'name': user.name, 'company': user.company}

# --- Fragebögen ---
@router.get('/questionnaires/{role}/{plant_type}')
def get_questionnaire(role: str, plant_type: str):
    role_q = QUESTIONNAIRES.get(role, {})
    questions = role_q.get(plant_type, role_q.get('_common', []))
    return {'role': role, 'plant_type': plant_type, 'questions': questions}

@router.post('/questionnaires/submit')
def submit_questionnaire(data: QuestionnaireSubmit, db: Session = Depends(get_db)):
    proj = db.query(Project).get(data.project_id)
    if not proj: raise HTTPException(404)
    proj.questionnaire = data.answers
    db.commit()
    return {'status': 'saved', 'project_id': proj.id}

# --- Projekte ---
@router.post('/projects')
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    proj = Project(
        name=data.name, plz=data.plz, power_kw=data.power_kw,
        plant_type=data.plant_type, voltage_kv=data.voltage_kv.value if hasattr(data.voltage_kv,'value') else data.voltage_kv,
        cos_phi=data.cos_phi, einspeiseprofil=data.einspeiseprofil,
        gleichzeitigkeitsfaktor=data.gleichzeitigkeitsfaktor,
        address=data.address, notes=data.notes
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return {'id': proj.id, 'name': proj.name, 'status': proj.status.value if proj.status else 'draft'}

@router.get('/projects')
def list_projects(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Project).order_by(Project.created_at.desc())
    if status:
        q = q.filter(Project.status == status)
    return q.limit(100).all()

@router.get('/projects/{pid}')
def get_project(pid: int, db: Session = Depends(get_db)):
    p = db.query(Project).get(pid)
    if not p: raise HTTPException(404)
    return p

@router.put('/projects/{pid}/status')
def update_status(pid: int, data: StatusUpdate, db: Session = Depends(get_db)):
    proj = db.query(Project).get(pid)
    if not proj: raise HTTPException(404)
    proj.status = data.status
    db.commit()
    if data.comment:
        c = Comment(project_id=pid, user_id=0, text=f"Status → {data.status.value}: {data.comment}")
        db.add(c)
        db.commit()
    return {'status': proj.status.value}

# --- Kommentare ---
@router.post('/projects/{pid}/comments')
def add_comment(pid: int, data: CommentCreate, db: Session = Depends(get_db)):
    c = Comment(project_id=pid, user_id=0, text=data.text, is_internal=data.is_internal)
    db.add(c)
    db.commit()
    return {'id': c.id}

@router.get('/projects/{pid}/comments')
def get_comments(pid: int, db: Session = Depends(get_db)):
    return db.query(Comment).filter(Comment.project_id == pid).order_by(Comment.created_at.asc()).all()

# --- Berechnung ---
@router.post('/calculate')
def calculate(data: CalcRequest, db: Session = Depends(get_db)):
    proj = db.query(Project).get(data.project_id)
    if not proj: raise HTTPException(404, 'Projekt nicht gefunden')

    # Kernberechnung
    result = calc_ms_grid(data, proj)
    
    # N-1
    n1_result = None
    if data.run_n1:
        n1_result = run_n1_analysis(result, data, proj)
        result['n1'] = n1_result
    
    # Sensitivität
    sensitivity = None
    if data.run_sensitivity:
        sensitivity = run_sensitivity(data, proj)
        result['sensitivity'] = sensitivity
    
    # KI-Empfehlungen
    recommendations = generate_recommendations(result, n1_result, proj)
    result['recommendations'] = recommendations
    
    # Speichern
    calc = Calculation(
        project_id=proj.id,
        sk_mva=data.sk_mv,
        cable_type=data.cable_type,
        cable_length_km=data.cable_length_km,
        transformer_sn_kva=data.transformer_sn_kva,
        uk_percent=data.uk_percent,
        existing_load_kw=data.existing_load_kw,
        delta_u_percent=result['delta_u_percent'],
        i_thermal_a=result['i_total_a'],
        thermal_percent=result['thermal_total_percent'],
        sk_ap_mva=result['sk_ap_mva'],
        sk_ratio=result['sk_ratio'],
        ampel=TrafficLight(result['ampel']),
        n1_result=n1_result,
        sensitivity=sensitivity,
        ki_recommendations=recommendations,
        result_json=result,
    )
    calc.compute_hashes()
    db.add(calc)
    db.commit()
    db.refresh(calc)

    # Snapshot
    snap = Snapshot(
        calculation_id=calc.id,
        snapshot_type='full',
        data={
            'input': data.model_dump(),
            'result': result,
            'project': {'id': proj.id, 'name': proj.name, 'plz': proj.plz, 'power_kw': proj.power_kw},
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0'
        }
    )
    # Hash-Chain
    last_snap = db.query(Snapshot).order_by(Snapshot.id.desc()).first()
    snap.compute_hash(last_snap.data_hash if last_snap else '')
    db.add(snap)
    db.commit()

    # Status update
    proj.status = ProjectStatus.SUBMITTED
    db.commit()

    return {'calculation_id': calc.id, 'result': result}

@router.get('/calculations/{cid}')
def get_calculation(cid: int, db: Session = Depends(get_db)):
    c = db.query(Calculation).get(cid)
    if not c: raise HTTPException(404)
    return c

@router.get('/calculations/{cid}/snapshot')
def get_snapshot(cid: int, db: Session = Depends(get_db)):
    s = db.query(Snapshot).filter(Snapshot.calculation_id == cid).first()
    if not s: raise HTTPException(404)
    return {'data': s.data, 'hash': s.data_hash, 'chain': s.hash_chain}

# --- Dashboard (Netzbetreiber) ---
@router.get('/dashboard/stats')
def dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(Project).count()
    by_status = {}
    for s in ProjectStatus:
        by_status[s.value] = db.query(Project).filter(Project.status == s).count()
    by_ampel = {}
    for a in TrafficLight:
        by_ampel[a.value] = db.query(Calculation).filter(Calculation.ampel == a).count()
    return {'total_projects': total, 'by_status': by_status, 'by_ampel': by_ampel}

@router.get('/dashboard/recent')
def recent(db: Session = Depends(get_db)):
    calcs = db.query(Calculation).order_by(Calculation.created_at.desc()).limit(20).all()
    return calcs

@router.get('/dashboard/queue')
def nb_queue(db: Session = Depends(get_db)):
    """Warteschlange für Netzbetreiber: Alle eingereichten Projekte"""
    projects = db.query(Project).filter(
        Project.status.in_([ProjectStatus.SUBMITTED, ProjectStatus.IN_REVIEW])
    ).order_by(Project.created_at.asc()).all()
    
    result = []
    for p in projects:
        last_calc = db.query(Calculation).filter(
            Calculation.project_id == p.id
        ).order_by(Calculation.created_at.desc()).first()
        result.append({
            'project': p,
            'last_ampel': last_calc.ampel.value if last_calc else None,
            'last_calc_id': last_calc.id if last_calc else None,
            'delta_u': last_calc.delta_u_percent if last_calc else None,
            'thermal': last_calc.thermal_percent if last_calc else None,
        })
    return result

# --- Kabel-Katalog ---
@router.get('/catalog/cables')
def cable_catalog():
    return CABLE_DATA

@router.get('/catalog/questionnaires')
def all_questionnaires():
    return QUESTIONNAIRES
