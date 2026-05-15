from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, Enum as SqlEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum, hashlib, json

# --- Enums ---
class TrafficLight(str, enum.Enum):
    GREEN = 'green'
    YELLOW = 'yellow'
    RED = 'red'

class VoltageLevel(str, enum.Enum):
    NS_04 = '0.4kV'
    MS_10 = '10kV'
    MS_20 = '20kV'
    MS_30 = '30kV'
    HS_110 = '110kV'

class PlantType(str, enum.Enum):
    PV = 'pv'
    WIND = 'wind'
    BATTERY = 'battery'
    CHARGING = 'charging'
    INDUSTRY = 'industry'
    HEAT_PUMP = 'heat_pump'
    CHP = 'chp'
    HYBRID = 'hybrid'

class UserRole(str, enum.Enum):
    PROJEKTIERER = 'projektierer'
    NETZBETREIBER = 'netzbetreiber'
    BERATER = 'berater'
    ADMIN = 'admin'

class ProjectStatus(str, enum.Enum):
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    IN_REVIEW = 'in_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    REVISION = 'revision'

# --- User ---
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    company = Column(String(255))
    role = Column(SqlEnum(UserRole), nullable=False)
    netzbetreiber_id = Column(Integer, ForeignKey('netzbetreiber.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    projects = relationship('Project', back_populates='owner')

# --- Netzbetreiber ---
class Netzbetreiber(Base):
    __tablename__ = 'netzbetreiber'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    region = Column(String(255))
    plz_gebiete = Column(JSON)  # ["12xxx","13xxx"]
    kontakt_email = Column(String(255))
    default_sk_mva = Column(JSON)  # {"10kV":150,"20kV":250,"30kV":400}
    default_cable_types = Column(JSON)
    netz_config = Column(JSON)  # Spezifische Netzkonfiguration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    users = relationship('User')

# --- Project (erweitert) ---
class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    name = Column(String(255), nullable=False)
    plz = Column(String(5), nullable=False)
    power_kw = Column(Float, nullable=False)
    plant_type = Column(SqlEnum(PlantType), nullable=False)
    voltage_kv = Column(String(10), default='20kV')
    cos_phi = Column(Float, default=0.95)
    status = Column(SqlEnum(ProjectStatus), default=ProjectStatus.DRAFT)
    netzbetreiber_id = Column(Integer, ForeignKey('netzbetreiber.id'), nullable=True)
    
    # Erweiterte Projektdaten (Fragebogen)
    questionnaire = Column(JSON)  # Rollenspezifische Antworten
    location_lat = Column(Float, nullable=True)
    location_lon = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
    grundstueck_nr = Column(String(50), nullable=True)
    
    # Technische Details
    einspeiseprofil = Column(String(50))  # z.B. "volleinspeisung", "eigenverbrauch"
    gleichzeitigkeitsfaktor = Column(Float, default=1.0)
    geplanter_inbetriebnahme = Column(DateTime, nullable=True)
    
    # Meta
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    owner = relationship('User', back_populates='projects')
    calculations = relationship('Calculation', back_populates='project')
    comments = relationship('Comment', back_populates='project')

# --- Calculation (erweitert) ---
class Calculation(Base):
    __tablename__ = 'calculations'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    
    # Eingabeparameter
    sk_mva = Column(Float)
    cable_type = Column(String(50))
    cable_length_km = Column(Float)
    transformer_sn_kva = Column(Float)
    uk_percent = Column(Float)
    existing_load_kw = Column(Float, default=0)
    
    # Ergebnisse
    delta_u_percent = Column(Float)
    i_thermal_a = Column(Float)
    thermal_percent = Column(Float)
    sk_ap_mva = Column(Float)
    sk_ratio = Column(Float)
    ampel = Column(SqlEnum(TrafficLight))
    scenario = Column(String(20), default='base')
    
    # N-1 Analyse
    n1_result = Column(JSON)
    
    # Sensitivitätsanalyse
    sensitivity = Column(JSON)
    
    # KI-Empfehlungen
    ki_recommendations = Column(JSON)
    ki_confidence = Column(Float)
    
    # Vollständiges Ergebnis
    result_json = Column(JSON)
    
    # Revisionssicherheit
    input_hash = Column(String(64))
    result_hash = Column(String(64))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    project = relationship('Project', back_populates='calculations')
    snapshots = relationship('Snapshot', back_populates='calculation')

    def compute_hashes(self):
        input_data = json.dumps({
            'project_id': self.project_id, 'sk_mva': self.sk_mva,
            'cable_type': self.cable_type, 'cable_length_km': self.cable_length_km,
            'transformer_sn_kva': self.transformer_sn_kva, 'uk_percent': self.uk_percent,
            'existing_load_kw': self.existing_load_kw
        }, sort_keys=True)
        self.input_hash = hashlib.sha256(input_data.encode()).hexdigest()
        if self.result_json:
            self.result_hash = hashlib.sha256(
                json.dumps(self.result_json, sort_keys=True).encode()
            ).hexdigest()

# --- Snapshot (revisionssicher) ---
class Snapshot(Base):
    __tablename__ = 'snapshots'
    id = Column(Integer, primary_key=True, index=True)
    calculation_id = Column(Integer, ForeignKey('calculations.id'), nullable=False, index=True)
    snapshot_type = Column(String(20), default='full')
    data = Column(JSON, nullable=False)
    hash_chain = Column(String(64))  # Hash des vorherigen Snapshots
    data_hash = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    calculation = relationship('Calculation', back_populates='snapshots')

    def compute_hash(self, previous_hash=''):
        raw = json.dumps(self.data, sort_keys=True) + previous_hash
        self.data_hash = hashlib.sha256(raw.encode()).hexdigest()
        self.hash_chain = previous_hash

# --- Comments (Netzbetreiber ↔ Projektierer) ---
class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)  # Nur fuer NB sichtbar
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship('Project', back_populates='comments')

# --- PDF Reports ---
class Report(Base):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True, index=True)
    calculation_id = Column(Integer, ForeignKey('calculations.id'), nullable=False)
    report_type = Column(String(30), default='pre_check')  # pre_check, detail, nb_review
    filename = Column(String(255))
    file_path = Column(String(500))
    file_hash = Column(String(64))  # SHA256 des PDFs
    generated_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- KI Learning ---
class KITrainingData(Base):
    __tablename__ = 'ki_training'
    id = Column(Integer, primary_key=True, index=True)
    input_features = Column(JSON)
    result_ampel = Column(String(10))
    nb_decision = Column(String(20))  # approved/rejected - echtes Feedback
    corrections = Column(JSON)  # Was NB geaendert hat
    region_plz = Column(String(5))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
