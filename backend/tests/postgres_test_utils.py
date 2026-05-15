from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg2://gridcheck:gridcheck_dev_2026@localhost:5433/gridcheck_test"


def _is_postgres_url(url: str) -> bool:
    lowered = url.strip().lower()
    return lowered.startswith("postgresql://") or lowered.startswith("postgresql+") or lowered.startswith("postgres://")


def require_postgres_url(url: str, *, env_name: str = "DATABASE_URL") -> str:
    normalized = url.strip()
    if not normalized:
        raise RuntimeError(f"{env_name} fehlt. GridCheck unterstuetzt aktiv nur PostgreSQL.")
    if not _is_postgres_url(normalized):
        raise RuntimeError(f"{env_name} muss auf PostgreSQL zeigen. SQLite und andere Engines sind nicht unterstuetzt.")
    return normalized


def get_test_database_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL", "").strip()
    if explicit:
        return require_postgres_url(explicit, env_name="TEST_DATABASE_URL")
    inherited = os.getenv("DATABASE_URL", "").strip()
    if inherited:
        return require_postgres_url(inherited, env_name="DATABASE_URL")
    return DEFAULT_TEST_DATABASE_URL


def _connect_args() -> dict[str, int]:
    return {"connect_timeout": 10}


def _admin_url(url: str) -> URL:
    parsed = make_url(url)
    return parsed.set(database="postgres")


def _database_name(url: str) -> str:
    parsed = make_url(url)
    if not parsed.database:
        raise RuntimeError("PostgreSQL-URL ohne Datenbanknamen ist fuer Tests nicht gueltig.")
    return parsed.database


def ensure_postgres_database_exists(url: str) -> None:
    require_postgres_url(url)
    db_name = _database_name(url)
    admin_engine = create_engine(
        _admin_url(url),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args=_connect_args(),
    )
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


def run_alembic_upgrade(url: str, *, revision: str = "head") -> None:
    require_postgres_url(url)
    backend_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    env["TEST_DATABASE_URL"] = url
    env["AUTO_CREATE_SCHEMA"] = "false"
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=backend_root,
        env=env,
        check=True,
    )


def build_isolated_postgres_session_factory(base_metadata, *, label: str = "test"):
    base_url = get_test_database_url()
    require_postgres_url(base_url, env_name="TEST_DATABASE_URL")
    parsed = make_url(base_url)
    base_db_name = _database_name(base_url)
    safe_label = re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_") or "test"
    db_name = f"{base_db_name}_{safe_label}_{uuid4().hex[:8]}"
    db_url = parsed.set(database=db_name).render_as_string(hide_password=False)

    ensure_postgres_database_exists(db_url)

    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        connect_args=_connect_args(),
    )
    run_alembic_upgrade(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def cleanup() -> None:
        engine.dispose()
        admin_engine = create_engine(
            _admin_url(db_url),
            isolation_level="AUTOCOMMIT",
            poolclass=NullPool,
            pool_pre_ping=True,
            connect_args=_connect_args(),
        )
        try:
            with admin_engine.connect() as conn:
                conn.execute(
                    text(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = :db_name AND pid <> pg_backend_pid()
                        """
                    ),
                    {"db_name": db_name},
                )
                conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        finally:
            admin_engine.dispose()

    return engine, SessionLocal, cleanup
