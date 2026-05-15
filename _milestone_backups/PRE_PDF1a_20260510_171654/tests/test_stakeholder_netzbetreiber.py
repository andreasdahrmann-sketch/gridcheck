"""Regression: Netzbetreiber-Check speichert [NB:Aktenzeichen] im Projektname."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base, Project
from services.stakeholder_service import run_netzbetreiber_check


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_netzbetreiber_projektname_mit_nb_prefix(memory_db):
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
    out = run_netzbetreiber_check(memory_db, req_data)
    pid = out["project_id"]
    p = memory_db.get(Project, pid)
    assert p is not None
    assert p.name == "[NB:AZ-12345] Solar Nord"
