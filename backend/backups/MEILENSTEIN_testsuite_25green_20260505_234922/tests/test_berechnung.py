"""
Tests fuer engine.berechnung.berechne_netzanschluss (Integration).
"""
import pytest
from engine.berechnung import berechne_netzanschluss


class TestBerechnungSmoke:
    """Lauffaehigkeit + Pflichtfelder."""

    def test_basis_pv_ms_laeuft_durch(self, basis_pv_ms):
        r = berechne_netzanschluss(basis_pv_ms)
        assert r["status"] == "OK"

    def test_pflicht_keys_vorhanden(self, basis_pv_ms):
        r = berechne_netzanschluss(basis_pv_ms)
        for key in ["thermisch", "spannung", "kurzschluss", "n1",
                    "trafo", "scores", "fazit", "empfehlungen"]:
            assert key in r, f"Pflicht-Key fehlt: {key}"

    def test_scores_struktur(self, basis_pv_ms):
        r = berechne_netzanschluss(basis_pv_ms)
        s = r["scores"]
        for k in ["kapazitaet", "spannung", "kurzschluss",
                  "versorgungssicherheit", "datenqualitaet", "gesamt"]:
            assert k in s
            assert isinstance(s[k], (int, float))
            assert 0 <= s[k] <= 100


class TestN1Integration:
    """N-1 muss in Gesamtberechnung korrekt durchschlagen."""

    def test_ring_redundant_ist_gruen(self, basis_pv_ms):
        r = berechne_netzanschluss(basis_pv_ms)
        assert r["n1"]["bewertung"] == "GRUEN"
        assert r["n1"]["n1_sicher"] is True

    def test_stich_ist_rot_und_capt_score(self, basis_pv_stich):
        r = berechne_netzanschluss(basis_pv_stich)
        assert r["n1"]["bewertung"] == "ROT"
        assert r["fazit"]["entscheidung"] == "C"
        assert r["fazit"]["farbe"] == "ROT"

    def test_ring_ohne_restkap_ist_gelb_unbestimmt(self, basis_pv_ms):
        e = dict(basis_pv_ms)
        e["restkapazitaet_ms_mva"] = None
        r = berechne_netzanschluss(e)
        assert r["n1"]["bewertung"] == "GELB"
        assert r["n1"]["n1_sicher"] is None


class TestFazitLogik:
    """Fazit-Kaskade: harte Verstoesse -> C, weiche -> B, sauber -> A."""

    def test_harte_verstoesse_fuehren_zu_C(self, basis_pv_stich):
        r = berechne_netzanschluss(basis_pv_stich)
        if r["scores"]["harte_verstoesse"]:
            assert r["fazit"]["entscheidung"] == "C"

    def test_score_konsistent_mit_fazit(self, basis_pv_ms):
        r = berechne_netzanschluss(basis_pv_ms)
        score = r["scores"]["gesamt"]
        ent = r["fazit"]["entscheidung"]
        if ent == "A":
            assert score >= 75
        elif ent == "B":
            assert 40 <= score < 85
        elif ent == "C":
            assert score < 70 or r["scores"]["harte_verstoesse"]


class TestRobustheit:
    """Engine darf bei unvollstaendigen Eingaben nicht abstuerzen."""

    def test_minimale_eingabe(self):
        e = {
            "anlagentyp": "PV", "p_kw": 1000, "leistung_mw": 1.0,
            "plz": "00000", "anschlussart": "Einspeisung",
            "cos_phi": 0.95, "nennspannung": 20,
            "entfernung_km": 2.0, "leitungstyp": "NA2XS2Y240",
        }
        r = berechne_netzanschluss(e)
        assert r["status"] in ("OK", "WARNUNG")
