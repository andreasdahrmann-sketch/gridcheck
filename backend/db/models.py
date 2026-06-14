from sqlalchemy import BigInteger, Column, Date, Integer, Float, Numeric, String, DateTime, Boolean, Text, ForeignKey, UniqueConstraint, Index
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
    plz = Column(String(5), nullable=True)
    ort = Column(String, nullable=True)
    street = Column(String, nullable=True)
    house_number = Column(String, nullable=True)
    city = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
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
    analysis_runs = relationship("AnalysisRun", back_populates="project")


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
    vnb_verification_status = Column(String, nullable=False, default="none")
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    plan_tier = Column(String, nullable=False, default="free")
    billing_status = Column(String, nullable=False, default="free")
    stripe_customer_id = Column(String, nullable=True, unique=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, unique=True, index=True)
    stripe_price_id = Column(String, nullable=True)
    billing_current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    # DSGVO Art. 17 Soft-Delete: harte Loeschung verbietet Revisionssicherheit (Rule 05),
    # daher anonymisiert + deaktiviert; Datensatz bleibt fuer Audit-Trail / Hash-Chain bestehen.
    deleted_at = Column(DateTime, nullable=True, index=True)
    # SHA256(lower(original_email)) zur Re-Registrierungs-Sperre nach Anonymisierung.
    # Klartext-E-Mail wird beim Soft-Delete entfernt; der Hash bleibt fuer Account-Enum-Schutz
    # und zur Erfuellung der Konto-Sperre nach Loeschung (siehe DSGVO-Self-Service-Bericht).
    deleted_email_hash = Column(String(64), nullable=True, index=True)

    owned_projects = relationship("Project", back_populates="owner")
    memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    uploaded_files = relationship("ProjectFile", back_populates="uploader")
    analysis_runs = relationship("AnalysisRun", back_populates="user")
    billing_events = relationship("BillingEvent", back_populates="user")
    conversion_events = relationship("ConversionEvent", back_populates="user")
    billing_entitlements = relationship("BillingEntitlement", foreign_keys="BillingEntitlement.user_id", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    vnb_threads_created = relationship("VnbThread", back_populates="created_by", foreign_keys="VnbThread.created_by_user_id")
    vnb_messages_sent = relationship("VnbMessage", back_populates="sender", foreign_keys="VnbMessage.sender_user_id")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_user_expires", "user_id", "expires_at"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="password_reset_tokens")


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


class SiteMarker(Base):
    __tablename__ = "site_markers"
    __table_args__ = (
        Index("ix_site_markers_created_by_created", "created_by_user_id", "created_at"),
    )
    id = Column(Integer, primary_key=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    asset_type = Column(String, nullable=False)
    location_source = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    verification_status = Column(String, nullable=False, default="unverified")
    photo_file_name = Column(String, nullable=False)
    photo_mime_type = Column(String, nullable=False)
    photo_size_bytes = Column(Integer, nullable=False)
    photo_storage_path = Column(Text, nullable=False)
    photo_checksum = Column(String, nullable=False)
    revision_hash = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        Index("ix_analysis_runs_user_created", "user_id", "created_at"),
        Index("ix_analysis_runs_project_created", "project_id", "created_at"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    source = Column(String, nullable=False, default="interactive")
    status = Column(String, nullable=False, default="completed")
    input_json = Column(Text, nullable=False)
    request_checksum = Column(String, nullable=False)
    result_json = Column(Text, nullable=True)
    result_checksum = Column(String, nullable=True)
    score = Column(Float, nullable=True)
    decision_code = Column(String, nullable=True)
    revision_hash = Column(String, nullable=True, index=True)
    offer_id = Column(String, nullable=True, index=True)
    package_scope = Column(String, nullable=False, default="basic")
    usage_bucket = Column(String, nullable=False, default="free")
    entitlement_id = Column(Integer, ForeignKey("billing_entitlements.id"), nullable=True, index=True)
    billing_category = Column(String, nullable=False, default="free")
    free_quota_consumed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="analysis_runs")
    project = relationship("Project", back_populates="analysis_runs")
    entitlement = relationship("BillingEntitlement", back_populates="analysis_runs")


class BillingEvent(Base):
    __tablename__ = "billing_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_billing_provider_event"),
        Index("ix_billing_events_user_created", "user_id", "created_at"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    provider = Column(String, nullable=False, default="stripe")
    event_type = Column(String, nullable=False)
    provider_event_id = Column(String, nullable=True)
    checkout_session_id = Column(String, nullable=True, index=True)
    provider_customer_id = Column(String, nullable=True, index=True)
    provider_subscription_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="received")
    amount_cents = Column(Integer, nullable=True)
    currency = Column(String, nullable=True)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="billing_events")


class ConversionEvent(Base):
    __tablename__ = "conversion_events"
    __table_args__ = (
        Index("ix_conversion_events_user_created", "user_id", "created_at"),
        Index("ix_conversion_events_name_created", "event_name", "created_at"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_name = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    properties_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="conversion_events")


class BillingEntitlement(Base):
    __tablename__ = "billing_entitlements"
    __table_args__ = (
        Index("ix_billing_entitlements_user_status", "user_id", "status"),
        Index("ix_billing_entitlements_user_offer", "user_id", "offer_id"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    offer_id = Column(String, nullable=False, index=True)
    offer_category = Column(String, nullable=False, default="pay_per_use")
    package_scope = Column(String, nullable=False, default="basic")
    source = Column(String, nullable=False, default="checkout")
    status = Column(String, nullable=False, default="pending")
    total_credits = Column(Integer, nullable=True)
    used_credits = Column(Integer, nullable=False, default=0)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    checkout_session_id = Column(String, nullable=True, index=True)
    stripe_price_id = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    express_requested = Column(Boolean, nullable=False, default=False)
    ops_followup_required = Column(Boolean, nullable=False, default=False)
    ops_status = Column(String, nullable=False, default="not_required")
    ops_assignee_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    ops_assigned_at = Column(DateTime, nullable=True)
    ops_started_at = Column(DateTime, nullable=True)
    ops_completed_at = Column(DateTime, nullable=True)
    ops_last_comment = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id], back_populates="billing_entitlements")
    analysis_runs = relationship("AnalysisRun", back_populates="entitlement")
    ops_assignee = relationship("User", foreign_keys=[ops_assignee_user_id])


class AssetCandidate(Base):
    __tablename__ = "asset_candidates"
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    source_license = Column(String, nullable=True)
    source_imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_updated_at = Column(DateTime, nullable=True)
    source_raw_hash = Column(String, nullable=False)
    source_normalized_hash = Column(String, nullable=False)
    source_parser_version = Column(String, nullable=False)
    confidence_score = Column(Integer, nullable=False, default=0)
    confidence_technical = Column(Integer, nullable=False, default=0)
    confidence_geometric = Column(Integer, nullable=False, default=0)
    confidence_commercial = Column(Integer, nullable=False, default=0)
    validation_status = Column(String, nullable=False, default="UNKNOWN")
    data_class = Column(String, nullable=False, default="C")
    asset_type = Column(String, nullable=False)
    geometry_wkt = Column(Text, nullable=True)
    properties_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GenerationAsset(Base):
    __tablename__ = "generation_assets"
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    source_license = Column(String, nullable=True)
    source_imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_updated_at = Column(DateTime, nullable=True)
    source_raw_hash = Column(String, nullable=False)
    source_normalized_hash = Column(String, nullable=False)
    source_parser_version = Column(String, nullable=False)
    confidence_score = Column(Integer, nullable=False, default=0)
    confidence_technical = Column(Integer, nullable=False, default=0)
    confidence_geometric = Column(Integer, nullable=False, default=0)
    confidence_commercial = Column(Integer, nullable=False, default=0)
    validation_status = Column(String, nullable=False, default="UNKNOWN")
    data_class = Column(String, nullable=False, default="C")
    external_id = Column(String, nullable=True)
    energy_carrier = Column(String, nullable=False)
    capacity_kw = Column(Float, nullable=True)
    plz = Column(String(5), nullable=True)
    status = Column(String, nullable=True)
    properties_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SystemSignal(Base):
    __tablename__ = "system_signals"
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    source_license = Column(String, nullable=True)
    source_imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_updated_at = Column(DateTime, nullable=True)
    source_raw_hash = Column(String, nullable=False)
    source_normalized_hash = Column(String, nullable=False)
    source_parser_version = Column(String, nullable=False)
    confidence_score = Column(Integer, nullable=False, default=0)
    confidence_technical = Column(Integer, nullable=False, default=0)
    confidence_geometric = Column(Integer, nullable=False, default=0)
    confidence_commercial = Column(Integer, nullable=False, default=0)
    validation_status = Column(String, nullable=False, default="UNKNOWN")
    data_class = Column(String, nullable=False, default="C")
    signal_type = Column(String, nullable=False)
    signal_value = Column(Float, nullable=True)
    signal_unit = Column(String, nullable=True)
    region = Column(String, nullable=True)
    measured_at = Column(DateTime, nullable=True)
    properties_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class WeatherResource(Base):
    __tablename__ = "weather_resource"
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    source_license = Column(String, nullable=True)
    source_imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_updated_at = Column(DateTime, nullable=True)
    source_raw_hash = Column(String, nullable=False)
    source_normalized_hash = Column(String, nullable=False)
    source_parser_version = Column(String, nullable=False)
    confidence_score = Column(Integer, nullable=False, default=0)
    confidence_technical = Column(Integer, nullable=False, default=0)
    confidence_geometric = Column(Integer, nullable=False, default=0)
    confidence_commercial = Column(Integer, nullable=False, default=0)
    validation_status = Column(String, nullable=False, default="UNKNOWN")
    data_class = Column(String, nullable=False, default="C")
    station_id = Column(String, nullable=True)
    region = Column(String, nullable=True)
    measured_at = Column(DateTime, nullable=True)
    temperature_c = Column(Float, nullable=True)
    wind_ms = Column(Float, nullable=True)
    irradiation_wm2 = Column(Float, nullable=True)
    properties_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GroundRisk(Base):
    __tablename__ = "ground_risk"
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    source_license = Column(String, nullable=True)
    source_imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_updated_at = Column(DateTime, nullable=True)
    source_raw_hash = Column(String, nullable=False)
    source_normalized_hash = Column(String, nullable=False)
    source_parser_version = Column(String, nullable=False)
    confidence_score = Column(Integer, nullable=False, default=0)
    confidence_technical = Column(Integer, nullable=False, default=0)
    confidence_geometric = Column(Integer, nullable=False, default=0)
    confidence_commercial = Column(Integer, nullable=False, default=0)
    validation_status = Column(String, nullable=False, default="UNKNOWN")
    data_class = Column(String, nullable=False, default="C")
    region = Column(String, nullable=True)
    soil_class = Column(String, nullable=True)
    groundwater_level_m = Column(Float, nullable=True)
    excavation_risk_score = Column(Float, nullable=True)
    properties_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CostIndex(Base):
    __tablename__ = "cost_indices"
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    source_license = Column(String, nullable=True)
    source_imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_updated_at = Column(DateTime, nullable=True)
    source_raw_hash = Column(String, nullable=False)
    source_normalized_hash = Column(String, nullable=False)
    source_parser_version = Column(String, nullable=False)
    confidence_score = Column(Integer, nullable=False, default=0)
    confidence_technical = Column(Integer, nullable=False, default=0)
    confidence_geometric = Column(Integer, nullable=False, default=0)
    confidence_commercial = Column(Integer, nullable=False, default=0)
    validation_status = Column(String, nullable=False, default="UNKNOWN")
    data_class = Column(String, nullable=False, default="C")
    index_type = Column(String, nullable=False)
    region = Column(String, nullable=True)
    index_value = Column(Float, nullable=True)
    index_unit = Column(String, nullable=True)
    valid_from = Column(DateTime, nullable=True)
    properties_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GridcheckResultAudit(Base):
    __tablename__ = "gridcheck_result_audit"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    model_version = Column(String, nullable=False)
    scoring_version = Column(String, nullable=False)
    norm_version = Column(String, nullable=False)
    app_version = Column(String, nullable=False)
    inputs_json = Column(Text, nullable=False)
    assumptions_json = Column(Text, nullable=False, default="[]")
    warnings_json = Column(Text, nullable=False, default="[]")
    score_components_json = Column(Text, nullable=False, default="{}")
    sources_json = Column(Text, nullable=False, default="[]")
    result_json = Column(Text, nullable=False)
    result_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RevisionRecord(Base):
    __tablename__ = "revision_records"
    __table_args__ = (
        UniqueConstraint("revisionsnummer", name="uq_revision_records_number"),
        UniqueConstraint("uuid", name="uq_revision_records_uuid"),
        UniqueConstraint("hash", name="uq_revision_records_hash"),
        Index("ix_revision_records_id", "id"),
        Index("ix_revision_records_revisionsnummer", "revisionsnummer"),
        Index("ix_revision_records_hash", "hash"),
        Index("ix_revision_records_actor_user_id", "actor_user_id"),
        Index("ix_revision_records_project_id", "project_id"),
        Index("ix_revision_records_project_number", "project_id", "revisionsnummer"),
        Index("ix_revision_records_action_timestamp", "action_type", "timestamp"),
    )

    id = Column(Integer, primary_key=True)
    revisionsnummer = Column(Integer, nullable=False)
    uuid = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    schema_version = Column(String, nullable=False)
    engine_version = Column(String, nullable=False)
    previous_hash = Column(String, nullable=False)
    hash = Column(String, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    data_json = Column(Text, nullable=False)

    actor = relationship("User", foreign_keys=[actor_user_id])
    project = relationship("Project", foreign_keys=[project_id])


class KiFeedbackRecord(Base):
    __tablename__ = "ki_feedback_records"
    __table_args__ = (
        UniqueConstraint("feedback_nummer", name="uq_ki_feedback_records_number"),
        UniqueConstraint("uuid", name="uq_ki_feedback_records_uuid"),
        UniqueConstraint("hash", name="uq_ki_feedback_records_hash"),
        Index("ix_ki_feedback_records_id", "id"),
        Index("ix_ki_feedback_records_feedback_nummer", "feedback_nummer"),
        Index("ix_ki_feedback_records_hash", "hash"),
        Index("ix_ki_feedback_records_actor_user_id", "actor_user_id"),
        Index("ix_ki_feedback_records_revision_hash", "revision_hash"),
        Index("ix_ki_feedback_records_revision_number", "revision_hash", "feedback_nummer"),
    )

    id = Column(Integer, primary_key=True)
    feedback_nummer = Column(Integer, nullable=False)
    uuid = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    schema_version = Column(String, nullable=False)
    previous_hash = Column(String, nullable=False)
    hash = Column(String, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    revision_hash = Column(String, nullable=True)
    data_json = Column(Text, nullable=False)

    actor = relationship("User", foreign_keys=[actor_user_id])


class VnbThread(Base):
    __tablename__ = "vnb_threads"
    __table_args__ = (
        Index("ix_vnb_threads_board_last_message", "board_scope", "last_message_at"),
        Index("ix_vnb_threads_category", "category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    board_scope = Column(String(32), nullable=False, default="austausch")
    title = Column(String(200), nullable=False)
    category = Column(String(40), nullable=False)
    target_vnb_region = Column(String(80), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_message_at = Column(DateTime, nullable=True)

    created_by = relationship("User", back_populates="vnb_threads_created", foreign_keys=[created_by_user_id])
    messages = relationship("VnbMessage", back_populates="thread", cascade="all, delete-orphan")


class VnbMessage(Base):
    __tablename__ = "vnb_messages"
    __table_args__ = (Index("ix_vnb_messages_thread_created", "thread_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("vnb_threads.id"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    thread = relationship("VnbThread", back_populates="messages")
    sender = relationship("User", back_populates="vnb_messages_sent", foreign_keys=[sender_user_id])
    audit_entries = relationship("VnbMessageAudit", back_populates="message", cascade="all, delete-orphan")


class VnbMessageAudit(Base):
    __tablename__ = "vnb_message_audit"
    __table_args__ = (Index("ix_vnb_message_audit_message_created", "message_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("vnb_messages.id"), nullable=False, index=True)
    event_type = Column(String(40), nullable=False, default="message_created")
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    payload_json = Column(Text, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    message = relationship("VnbMessage", back_populates="audit_entries")
    actor = relationship("User", foreign_keys=[actor_user_id])


class ReportRevisionRecord(Base):
    __tablename__ = "report_revision_records"
    __table_args__ = (
        UniqueConstraint("revisionsnummer", name="uq_report_revision_records_number"),
        UniqueConstraint("uuid", name="uq_report_revision_records_uuid"),
        UniqueConstraint("hash", name="uq_report_revision_records_hash"),
        Index("ix_report_revision_records_id", "id"),
        Index("ix_report_revision_records_revisionsnummer", "revisionsnummer"),
        Index("ix_report_revision_records_hash", "hash"),
        Index("ix_report_revision_records_engine_revision_hash", "engine_revision_hash"),
        Index("ix_report_revision_records_type_number", "report_type", "revisionsnummer"),
        Index("ix_report_revision_records_engine_hash", "engine_revision_hash"),
    )

    id = Column(Integer, primary_key=True)
    revisionsnummer = Column(BigInteger, nullable=False)
    uuid = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    schema_version = Column(String, nullable=False)
    report_type = Column(String, nullable=False)
    previous_hash = Column(String, nullable=False)
    hash = Column(String, nullable=False)
    engine_revision_hash = Column(String, nullable=True)
    report_json = Column(Text, nullable=False)
    html_content = Column(Text, nullable=False)


class MastrUnit(Base):
    """Marktstammdatenregister-Anlagenstamm (Datenklasse A laut Rule 06).

    Skeleton fuer BL-GIS-003. Liefert Einspeisedruck-Indikatoren, KEIN Kapazitaetsclaim.
    raw_hash/normalized_hash/parser_version sind Pflicht (Provenienz, Rule 06).
    """

    __tablename__ = "mastr_units"
    __table_args__ = (
        Index("ix_mastr_units_plz", "plz"),
        Index("ix_mastr_units_bundesland", "bundesland"),
        Index("ix_mastr_units_latitude", "latitude"),
        Index("ix_mastr_units_longitude", "longitude"),
        Index("ix_mastr_units_unit_type", "unit_type"),
    )

    mastr_id = Column(String(64), primary_key=True)
    unit_type = Column(String(20), nullable=False)
    installed_capacity_kw = Column(Numeric(14, 3), nullable=False)
    commissioning_date = Column(Date, nullable=True)
    decommissioning_date = Column(Date, nullable=True)
    plz = Column(String(10), nullable=True)
    bundesland = Column(String(50), nullable=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    dso_name = Column(String(200), nullable=True)
    voltage_level = Column(String(50), nullable=True)
    data_source = Column(String(20), nullable=False, default="mastr")
    data_class = Column(String(1), nullable=False, default="A")
    confidence = Column(Numeric(4, 3), nullable=False, default=0.95)
    raw_hash = Column(String(64), nullable=False)
    normalized_hash = Column(String(64), nullable=False)
    parser_version = Column(String(20), nullable=False)
    imported_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    source_updated_at = Column(DateTime, nullable=True)


class MastrImport(Base):
    """Audit-Tabelle pro MaStR-Importlauf (running/success/failed)."""

    __tablename__ = "mastr_imports"
    __table_args__ = (
        Index("ix_mastr_imports_started_at", "started_at"),
        Index("ix_mastr_imports_status", "status"),
    )

    id = Column(String(36), primary_key=True)
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    parser_version = Column(String(20), nullable=False)
    source_file = Column(String(500), nullable=False)
    rows_total = Column(Integer, nullable=False, default=0)
    rows_inserted = Column(Integer, nullable=False, default=0)
    rows_updated = Column(Integer, nullable=False, default=0)
    rows_skipped = Column(Integer, nullable=False, default=0)
    rows_failed = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="running")
    error_summary = Column(Text, nullable=True)

