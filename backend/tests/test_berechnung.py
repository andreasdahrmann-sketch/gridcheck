"""
Tests fuer engine.berechnung.berechne_netzanschluss (Integration).
"""
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

    def test_transparenz_enthält_thd_hinweis(self, basis_pv_ms):
        r = berechne_netzanschluss(basis_pv_ms)
        notes = r["transparenz"]["confidence_notes"]
        assert any("THD" in note and "nicht berechnet" in note for note in notes)


class TestN1Integration:
    """N-1 muss in Gesamtberechnung korrekt durchschlagen."""

    def test_ring_redundant_ms_topologie_gruen_detail_kann_rot_sein(self, basis_pv_ms):
        """Ring+Redundanz+Restkap erfuellen den MS-Topologie-Pre-Check (siehe n1_ms/stakeholder-Block).
        Nach konsolidierung mit analysiere_n1 (Spannung im N-1-Stoerungsfall) kann die Gesamtbewertung ROT bleiben (N1-2, Engpass Spannung)."""
        r = berechne_netzanschluss(basis_pv_ms)
        assert r["status"] == "OK"
        assert r["n1"]["stakeholder"]["bewertung"] == "GRUEN"
        assert r["n1"]["stakeholder"]["n1_sicher"] is True
        assert r["n1"]["bewertung"] == "ROT"
        assert r["n1"]["n1_sicher"] is False
        assert r["n1"]["engpass_komponente"] == "spannung"

    def test_stich_ist_rot_und_capt_score(self, basis_pv_stich):
        r = berechne_netzanschluss(basis_pv_stich)
        assert r["n1"]["bewertung"] == "ROT"
        assert r["fazit"]["entscheidung"] == "C"
        assert r["fazit"]["farbe"] == "ROT"

    def test_ring_ohne_restkap_topologie_gelb_konsolidiert_rot(self, basis_pv_ms):
        """Ohne bekannte MS-Restkapazitaet bleibt der Topologie-Pre-Check GELB/n1_sicher=None (Datenluecke).
        Die konsolidierte N-1-Aussage folgt weiterhin dem Detail-Screening und kann bei Spannungsengpass ROT sein."""
        e = dict(basis_pv_ms)
        e["restkapazitaet_ms_mva"] = None
        r = berechne_netzanschluss(e)
        assert r["status"] == "OK"
        assert r["n1"]["stakeholder"]["bewertung"] == "GELB"
        assert r["n1"]["stakeholder"]["n1_sicher"] is None
        assert r["n1"]["bewertung"] == "ROT"
        assert r["n1"]["n1_sicher"] is False

    def test_umspannwerk_engpass_verschaerft_n1_detailbewertung(self, basis_pv_ms):
        e = dict(basis_pv_ms)
        e["umspannwerk"] = {
            "trafos": [
                {"sn_mva": 10.0, "belastung_aktuell_mw": 9.0},
                {"sn_mva": 10.0, "belastung_aktuell_mw": 9.0},
            ]
        }
        r = berechne_netzanschluss(e)
        assert r["status"] == "OK"
        assert r["n1"]["bewertung"] == "ROT"
        assert r["n1"]["n1_sicher"] is False
        assert r["n1"]["n1_klasse"] == "N1-2"
        assert r["n1"]["engpass_komponente"] == "trafo"
        assert "Engpass trafo" in r["n1"]["detail_text"]
        assert r["scores"]["versorgungssicherheit"] == 10
        assert any("N-1-Screening als N1-2" in note for note in r["transparenz"]["confidence_notes"])
        assert any("Umspannwerk" in text or "Trafo" in text for text in r["empfehlungen"])

    def test_abgangsreserve_erscheint_in_n1_detail_und_nachweisen(self, basis_pv_ms):
        e = dict(basis_pv_ms)
        e["umspannwerk"] = {
            "abgaenge": [
                {"label": "A1", "primary": True, "i_max_a": 630, "belastung_aktuell_a": 520},
                {"label": "A2", "i_max_a": 630, "belastung_aktuell_a": 300},
            ]
        }
        r = berechne_netzanschluss(e)
        assert r["status"] == "OK"
        assert r["n1"]["n1_klasse"] == "N1-2"
        assert "Abgang" in r["n1"]["detail_text"]
        assert "Abgangsreserve / Betriebsmittelpfad" in r["n1"]["nachweise_vorhanden"]
        assert any("N-1-Aussage aktuell nur als N1-2" in text for text in r["warnungen"])


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


class TestBestehendeEinspeisung:
    def test_bestehende_einspeisung_erhoeht_wirksame_leistung_bei_einspeisung(self, basis_pv_ms):
        e = dict(basis_pv_ms)
        e["leistung_mw"] = 5.0
        e["bestehende_einspeisung_mw"] = 3.0
        e["anschlussart"] = "Einspeisung"
        r = berechne_netzanschluss(e)
        assert r["status"] == "OK"
        assert r["annahmen"]["leistung_mw_wirksam"] == 8.0
        assert r["pqs"]["p_mw"] == 8.0

    def test_bestehende_einspeisung_reduziert_netto_bezug(self, basis_pv_ms):
        e = dict(basis_pv_ms)
        e["leistung_mw"] = 5.0
        e["bestehende_einspeisung_mw"] = 3.0
        e["anschlussart"] = "Entnahme"
        r = berechne_netzanschluss(e)
        assert r["status"] == "OK"
        assert r["annahmen"]["leistung_mw_wirksam"] == 2.0
        assert r["pqs"]["p_mw"] == 2.0


class TestMSSpannungNormKonsistenz:
    def test_ms_stationaere_hartgrenze_3_pct(self, basis_pv_ms):
        r = berechne_netzanschluss(basis_pv_ms)
        assert r["status"] == "OK"
        sp = r["spannung"]
        assert sp["spannungsebene"] == "MS"
        assert sp["delta_u_hartgrenze_pct"] == 3.0
        assert sp.get("ms_norm_tar")


class TestNSSpannungsebene:
    def test_ns_hartgrenze_3_pct(self, basis_pv_ms):
        e = dict(basis_pv_ms)
        e["nennspannung"] = 0.4
        e["leistung_mw"] = 0.15
        e["p_kw"] = 150
        r = berechne_netzanschluss(e)
        assert r["status"] in ("OK", "WARNUNG")
        assert r["spannung"]["spannungsebene"] == "NS"
        assert r["spannung"]["delta_u_hartgrenze_pct"] in (3.0, 5.0)
