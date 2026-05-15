"""
Gemeinsame Test-Fixtures fuer GridCheck Engine.
"""
import pytest


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
def isolierte_revisionen(tmp_path, monkeypatch):
    """
    Isoliert die Revisions-Datei in tmp_path, damit produktive
    daten/revisionen.jsonl waehrend Tests NIE veraendert wird.

    Patcht REVISIONS_PFAD modulglobal in engine.revision.
    """
    from engine import revision as rev_mod

    tmp_file = tmp_path / "revisionen.jsonl"
    monkeypatch.setattr(rev_mod, "REVISIONS_PFAD", str(tmp_file))
    # Legacy-Pfad ebenfalls weg-patchen, falls referenziert
    legacy = tmp_path / "revisionen.json"
    if hasattr(rev_mod, "LEGACY_PFAD"):
        monkeypatch.setattr(rev_mod, "LEGACY_PFAD", str(legacy))
    return tmp_file
