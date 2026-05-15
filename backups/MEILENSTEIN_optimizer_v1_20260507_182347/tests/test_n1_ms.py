"""
Tests fuer engine.n1_ms (Stakeholder-N-1-Bewertung).
"""
import pytest
from engine.n1_ms import bewerte_n1_ms


class TestN1Topologie:
    """Topologie-abhaengige Bewertung."""

    def test_stich_ist_rot(self):
        r = bewerte_n1_ms({"topologie": "stich", "leistung_mw": 5.0, "cos_phi": 0.95})
        assert r["bewertung"] == "ROT"
        assert r["n1_sicher"] is False
        assert r["konfidenz"] == "hoch"

    def test_radial_alias_wird_zu_stich(self):
        r = bewerte_n1_ms({"topologie": "radial", "leistung_mw": 5.0, "cos_phi": 0.95})
        assert r["bewertung"] == "ROT"
        assert r["topologie"] == "stich"

    def test_unbekannt_ist_rot(self):
        r = bewerte_n1_ms({"topologie": "unbekannt", "leistung_mw": 5.0, "cos_phi": 0.95})
        assert r["bewertung"] == "ROT"
        assert r["n1_sicher"] is False


class TestN1Restkapazitaet:
    """Ring/vermascht mit/ohne Restkapazitaet."""

    def test_ring_mit_ausreichender_restkapazitaet_ist_gruen(self):
        r = bewerte_n1_ms({
            "topologie": "ring", "leistung_mw": 5.0, "cos_phi": 0.95,
            "restkapazitaet_ms_mva": 10.0,
        })
        assert r["bewertung"] == "GRUEN"
        assert r["n1_sicher"] is True

    def test_ring_mit_zu_kleiner_restkapazitaet_ist_rot(self):
        r = bewerte_n1_ms({
            "topologie": "ring", "leistung_mw": 5.0, "cos_phi": 0.95,
            "restkapazitaet_ms_mva": 2.0,
        })
        assert r["bewertung"] == "ROT"
        assert r["n1_sicher"] is False

    def test_ring_ohne_restkapazitaet_ist_gelb_unbestimmt(self):
        r = bewerte_n1_ms({
            "topologie": "ring", "leistung_mw": 5.0, "cos_phi": 0.95,
            "restkapazitaet_ms_mva": None,
        })
        assert r["bewertung"] == "GELB"
        assert r["n1_sicher"] is None
        assert r["konfidenz"] == "mittel"

    def test_vermascht_verhaelt_sich_wie_ring(self):
        r = bewerte_n1_ms({
            "topologie": "vermascht", "leistung_mw": 5.0, "cos_phi": 0.95,
            "restkapazitaet_ms_mva": 10.0,
        })
        assert r["bewertung"] == "GRUEN"


class TestN1Stakeholder:
    """Output muss Begruendung + Annahmen + Versionierung liefern."""

    def test_pflicht_keys_fuer_revisionssicherheit(self):
        r = bewerte_n1_ms({"topologie": "ring", "leistung_mw": 5.0, "cos_phi": 0.95,
                           "restkapazitaet_ms_mva": 10.0})
        # Revisionssichere Pflichtfelder
        for key in ["bewertung", "n1_sicher", "topologie", "konfidenz",
                    "begruendung_technisch", "begruendung_klartext",
                    "annahmen", "berechnungs_version"]:
            assert key in r, f"Pflicht-Key fehlt: {key}"

    def test_begruendungen_nicht_leer(self):
        r = bewerte_n1_ms({"topologie": "ring", "leistung_mw": 5.0, "cos_phi": 0.95,
                           "restkapazitaet_ms_mva": 10.0})
        assert isinstance(r["begruendung_technisch"], str) and len(r["begruendung_technisch"]) > 10
        assert isinstance(r["begruendung_klartext"], str) and len(r["begruendung_klartext"]) > 10

    def test_annahmen_ist_liste(self):
        r = bewerte_n1_ms({"topologie": "ring", "leistung_mw": 5.0, "cos_phi": 0.95,
                           "restkapazitaet_ms_mva": 10.0})
        assert isinstance(r["annahmen"], list)

    def test_version_string_vorhanden(self):
        r = bewerte_n1_ms({"topologie": "ring", "leistung_mw": 5.0, "cos_phi": 0.95,
                           "restkapazitaet_ms_mva": 10.0})
        assert r["berechnungs_version"].startswith("n1-ms-")


class TestN1Edgecases:
    """Robustheit gegen fehlerhafte Eingaben."""

    def test_leere_eingabe_liefert_rot_oder_unbestimmt(self):
        r = bewerte_n1_ms({})
        assert r["bewertung"] in ("ROT", "GELB")
        assert "begruendung_technisch" in r

    def test_negative_leistung_wird_robust_behandelt(self):
        r = bewerte_n1_ms({"topologie": "ring", "leistung_mw": -5.0, "cos_phi": 0.95,
                           "restkapazitaet_ms_mva": 10.0})
        assert r["bewertung"] in ("GRUEN", "GELB", "ROT")
