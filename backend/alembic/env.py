import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Unsere eigenen Tabellen - nur diese werden von Alembic verwaltet
MANAGED_TABLES = {
    "users", "projects", "project_members", "check_results",
    "project_files", "audit_log",
    "analysis_runs", "billing_events", "billing_entitlements",
    "site_markers",
    "asset_candidates", "generation_assets", "system_signals",
    "weather_resource", "ground_risk", "cost_indices", "gridcheck_result_audit",
    "revision_records", "ki_feedback_records", "report_revision_records",
}

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from core.config import settings
from db.models import Base
target_metadata = Base.metadata

if settings.database_url:
    # `alembic upgrade head` must follow the active DATABASE_URL / backend .env,
    # not the stale fallback value from alembic.ini.
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

def include_object(object, name, type_, reflected, compare_to):
    """Nur unsere eigenen Tabellen verwalten - alle anderen ignorieren."""
    if type_ == "table":
        return name in MANAGED_TABLES
    # Indices/Constraints nur für unsere Tabellen
    if type_ in ("index", "unique_constraint", "foreign_key_constraint", "check_constraint"):
        if hasattr(object, "table"):
            return object.table.name in MANAGED_TABLES
        if hasattr(object, "parent"):
            return object.parent.name in MANAGED_TABLES
    return True

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
