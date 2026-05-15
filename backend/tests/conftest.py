"""
Gemeinsame Test-Fixtures fuer GridCheck Engine.
"""
import os

from sqlalchemy import create_engine, text

from tests.postgres_test_utils import (
    ensure_postgres_database_exists,
    get_test_database_url,
    run_alembic_upgrade,
)

# API-Tests importieren `main` beim Sammeln; daher PostgreSQL-Test-URL vor allen
# anderen Imports setzen und die Datenbank bei Bedarf anlegen.
TEST_DATABASE_URL = get_test_database_url()
ensure_postgres_database_exists(TEST_DATABASE_URL)
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "pytest-gridcheck-access-secret-32-chars")
os.environ.setdefault("JWT_REFRESH_SECRET", "pytest-gridcheck-refresh-secret-32")
os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")
# Starlette TestClient nutzt Host "testserver"; TrustedHostMiddleware sonst 400.
os.environ["TRUSTED_HOSTS"] = "localhost,127.0.0.1,testserver"

import pytest  # noqa: E402

from db.database import Base, engine, get_db  # noqa: E402
from main import app  # noqa: E402


def _purge_audit_chain_tables() -> None:
    """Leert Audit-Chain-Tabellen inklusive Sequenzen fuer stabile Revisionsnummern."""
    with engine.connect() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE "
                "ki_feedback_records, report_revision_records, revision_records "
                "RESTART IDENTITY CASCADE"
            )
        )
        conn.commit()
    engine.dispose()


def _test_touches_audit_chain(request: pytest.FixtureRequest) -> bool:
    nodeid = request.node.nodeid.replace("\\", "/")
    audit_markers = (
        "revision",
        "revisions_",
        "ki_feedback",
        "stakeholder_reports",
        "projektierer_report",
        "site_markers",
        "analyze_v2_route",
    )
    if any(token in nodeid for token in audit_markers):
        return True
    return any(
        name in request.fixturenames
        for name in ("isolierte_revisionen", "isolierte_ki_feedback", "isolierte_report_revisionen", "chain_mit_3")
    )


@pytest.fixture(autouse=True)
def _reset_fastapi_dependency_overrides():
    """Auth/Billing-Tests setzen get_db-Overrides; global zuruecksetzen."""
    app.dependency_overrides.pop(get_db, None)
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolated_audit_chain_tables(request: pytest.FixtureRequest):
    """Revision-/Report-/KI-Feedback-Tabellen vor Revision-bezogenen Tests leeren."""
    if _test_touches_audit_chain(request):
        _purge_audit_chain_tables()
    yield


_bootstrap_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 10})
run_alembic_upgrade(TEST_DATABASE_URL)
_bootstrap_engine.dispose()


@pytest.fixture
def basis_pv_ms():
    """Basis-PV-Anlage Mittelspannung, valide Defaultdaten."""
    return {
        "anlagentyp": "PV",
        "p_kw": 5000,
        "leistung_mw": 5.0,
        "plz": "00000",
        "anschlussart": "Einspeisung",
        "cos_phi": 0.95,
        "nennspannung": 20,
        "entfernung_km": 5.0,
        "leitungstyp": "NA2XS2Y240",
        "parallele_systeme": 2,
        "topologie": "ring",
        "redundanz": True,
        "trafo_s_mva": 25.0,
        "bestand_trafo_proz": 30.0,
        "sk_mva": 250.0,
        "restkapazitaet_ms_mva": 10.0,
        "bestehende_einspeisung_mw": 0,
    }


@pytest.fixture
def basis_pv_stich():
    """PV ueber radialen Stich (kein N-1)."""
    return {
        "anlagentyp": "PV",
        "p_kw": 5000,
        "leistung_mw": 5.0,
        "plz": "00000",
        "anschlussart": "Einspeisung",
        "cos_phi": 0.95,
        "nennspannung": 20,
        "entfernung_km": 5.0,
        "leitungstyp": "NA2XS2Y240",
        "parallele_systeme": 1,
        "topologie": "stich",
        "redundanz": False,
        "trafo_s_mva": 25.0,
        "bestand_trafo_proz": 30.0,
        "sk_mva": 250.0,
        "bestehende_einspeisung_mw": 0,
    }


@pytest.fixture
def isolierte_revisionen():
    """Alias fuer explizite Revision-Tests; Autouse-Fixture leert bereits vor jedem Test."""
    yield


@pytest.fixture
def isolierte_ki_feedback():
    yield


@pytest.fixture
def isolierte_report_revisionen():
    yield


@pytest.fixture
def isolierte_ki_lerndaten(tmp_path, monkeypatch):
    """
    Isoliert Legacy-Lerndaten, damit der KI-Pfad nur explizit gesetzte Daten nutzt.
    """
    from engine import ki_modul as ki_mod

    tmp_file = tmp_path / "ki_lerndaten.json"
    monkeypatch.setattr(ki_mod, "KI_DATEN_PFAD", str(tmp_file))
    return tmp_file
