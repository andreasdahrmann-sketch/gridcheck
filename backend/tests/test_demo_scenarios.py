"""Regression tests for sales-demo scenario payloads (aligned with frontend DemoCaseLoader)."""
from __future__ import annotations

from engine.berechnung import berechne_netzanschluss

PV_MS_DEMO = {
    "anlagentyp": "PV",
    "p_kw": 5000,
    "leistung_mw": 5.0,
    "plz": "04109",
    "ort": "Leipzig",
    "anschlussart": "Einspeisung",
    "cos_phi": 0.95,
    "nennspannung": 20,
    "entfernung_km": 2.0,
    "leitungstyp": "NA2XS2Y240",
    "parallele_systeme": 2,
    "topologie": "ring_offen",
    "redundanz": True,
    "trafo_s_mva": 25.0,
    "sk_mva": 250.0,
    "restkapazitaet_ms_mva": 10.0,
}

BESS_GRENZWERTIG_DEMO = {
    "anlagentyp": "BESS",
    "p_kw": 10000,
    "leistung_mw": 10.0,
    "plz": "30159",
    "ort": "Hannover",
    "anschlussart": "Speicher",
    "cos_phi": 0.95,
    "nennspannung": 20,
    "entfernung_km": 3.0,
    "leitungstyp": "NA2XS2Y240",
    "topologie": "ring_offen",
    "redundanz": True,
    "sk_mva": 250.0,
    "restkapazitaet_ms_mva": 8.0,
    "umspannwerk": {
        "trafos": [
            {"sn_mva": 10.0, "belastung_aktuell_mw": 9.0},
            {"sn_mva": 10.0, "belastung_aktuell_mw": 9.0},
        ],
    },
}

NOGO_THERMIK_DEMO = {
    "anlagentyp": "PV",
    "p_kw": 250,
    "leistung_mw": 0.25,
    "plz": "44137",
    "ort": "Dortmund",
    "anschlussart": "Einspeisung",
    "cos_phi": 0.95,
    "nennspannung": 0.4,
    "entfernung_km": 0.3,
    "leitungstyp": "NAYY150",
    "topologie": "stich",
    "redundanz": False,
}


def test_demo_pv_ms_liefert_transparenz_und_empfehlungen():
    r = berechne_netzanschluss(PV_MS_DEMO)
    assert r["status"] == "OK"
    assert r["transparenz"]["confidence_notes"]
    assert r["empfehlungen"]


def test_demo_bess_grenzwertig_trafo_engpass():
    r = berechne_netzanschluss(BESS_GRENZWERTIG_DEMO)
    assert r["status"] == "OK"
    assert r["n1"]["engpass_komponente"] == "trafo"
    assert r["n1"]["bewertung"] == "ROT"
    assert r["n1"]["n1_klasse"] == "N1-2"
    assert r["fazit"]["entscheidung"] == "C"


def test_demo_nogo_thermik_entscheidung_c():
    r = berechne_netzanschluss(NOGO_THERMIK_DEMO)
    assert r["status"] == "OK"
    assert r["fazit"]["entscheidung"] == "C"
    assert r["thermisch"]["bewertung"] == "ROT"
    assert r["spannung"]["bewertung"] == "ROT"
