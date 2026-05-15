"""Regression: Netzbetreiber-Check speichert [NB:Aktenzeichen] im Projektname."""
from __future__ import annotations

import pytest

from db.models import Base, Project, User
from services.stakeholder_service import run_netzbetreiber_check
from tests.postgres_test_utils import build_isolated_postgres_session_factory


@pytest.fixture
def postgres_db():
    _, Session, cleanup = build_isolated_postgres_session_factory(Base.metadata, label="netzbetreiber")
    session = Session()
    try:
        yield session
    finally:
        session.close()
        cleanup()


def test_netzbetreiber_projektname_mit_nb_prefix(postgres_db):
    actor = User(
        email="netzbetreiber@example.com",
        password_hash="fixture-hash",
        role="netzbetreiber",
        is_active=True,
    )
    postgres_db.add(actor)
    postgres_db.commit()
    postgres_db.refresh(actor)
    req_data = {
        "projektname": "Solar Nord",
        "plz": "10115",
        "anlagentyp": "pv",
        "leistung_kw": 500.0,
        "spannungsebene": "20",
        "cos_phi": 0.95,
        "einspeiseart": "volleinspeisung",
        "speicher": False,
        "speicher_kwh": None,
        "trafo_mva": 0.63,
        "leitungslaenge_km": 1.0,
        "leitungstyp": "NAYY",
        "querschnitt_mm2": "150",
        "netzverknuepfungspunkt": "",
        "skv_mva": None,
        "parallelsysteme": 1,
        "eigentumsgrenze": "HAK",
        "vorbelastung_mw": 0,
        "netz_typ": "kabel",
        "gewuenschte_massnahmen": [],
        "pruefer_id": "pr-1",
        "aktenzeichen": "AZ-12345",
        "pruefvermerk": "",
    }
    out = run_netzbetreiber_check(postgres_db, req_data, actor)
    pid = out["project_id"]
    p = postgres_db.get(Project, pid)
    assert p is not None
    assert p.name == "[NB:AZ-12345] Solar Nord"
    assert p.owner_user_id == actor.id
