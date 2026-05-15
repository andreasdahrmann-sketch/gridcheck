"""
Tests fuer engine/n1_analyse.py
Deckt ab:
  - Trafo-N-1 (verschiedene UW-Konfigurationen)
  - Leitung-N-1 (mit/ohne thermisch-Input)
  - Spannung-N-1 (verschiedene ΔU)
  - Aggregation, N1-Klassen, Konfidenz
  - Revisionssicherheit (Pflichtfelder, Versionierung)
  - Edgecases (None, leer, negativ)
"""
from engine.n1_analyse import (
    analysiere_n1,
    bewerte_abgang_n1,
    bewerte_trafo_n1,
    bewerte_leitung_n1,
    bewerte_spannung_n1,
    bestimme_n1_klasse,
    berechne_konfidenz,
    VERSION,
)


# ======================================================================
# 1. TRAFO-N-1
# ======================================================================
class TestTrafoN1:
    def test_keine_uw_daten_ist_nicht_geprueft(self):
        r = bewerte_trafo_n1(None, 5.0, 0.95)
        assert r["bewertung"] == "NICHT_GEPRUEFT"

    def test_nur_ein_trafo_ist_rot(self):
        uw = {"trafos": [{"sn_mva": 25, "belastung_aktuell_mw": 10}]}
        r = bewerte_trafo_n1(uw, 5.0, 0.95)
        assert r["bewertung"] == "ROT"
        assert "Redundanz" in r["begruendung_technisch"] or "1 Trafo" in r["begruendung_technisch"]

    def test_zwei_trafos_genug_reserve_ist_gruen(self):
        # 2x 40 MVA, je 10 MW belastet, +5 MW neu -> bei Ausfall: 25 MVA Last auf 40 MVA Rest = 62.5%
        uw = {"trafos": [
            {"sn_mva": 40, "belastung_aktuell_mw": 10},
            {"sn_mva": 40, "belastung_aktuell_mw": 10},
        ]}
        r = bewerte_trafo_n1(uw, 5.0, 0.95)
        assert r["bewertung"] == "GRUEN"
        assert r["auslastung_n1_prozent"] < 100

    def test_zwei_trafos_grenzwertig_ist_gelb(self):
        # 2x 25 MVA, je 14 MW -> N-1: ~31 MVA Last auf 25 MVA = 124% -> GELB
        uw = {"trafos": [
            {"sn_mva": 25, "belastung_aktuell_mw": 14},
            {"sn_mva": 25, "belastung_aktuell_mw": 14},
        ]}
        r = bewerte_trafo_n1(uw, 1.5, 0.95)
        assert r["bewertung"] in ("GELB", "ROT")

    def test_zwei_trafos_ueberlastet_ist_rot(self):
        # 2x 25 MVA, je 22 MW -> N-1: deutlich > 120%
        uw = {"trafos": [
            {"sn_mva": 25, "belastung_aktuell_mw": 22},
            {"sn_mva": 25, "belastung_aktuell_mw": 22},
        ]}
        r = bewerte_trafo_n1(uw, 5.0, 0.95)
        assert r["bewertung"] == "ROT"

    def test_groesster_trafo_wird_als_engpass_erkannt(self):
        uw = {"trafos": [
            {"sn_mva": 20, "belastung_aktuell_mw": 5},
            {"sn_mva": 40, "belastung_aktuell_mw": 5},
        ]}
        r = bewerte_trafo_n1(uw, 2.0, 0.95)
        assert r["engpass_trafo_idx"] == 1


# ======================================================================
# 2. LEITUNG-N-1
# ======================================================================
class TestLeitungN1:
    def test_kein_input_ist_rot(self):
        r = bewerte_leitung_n1(None)
        assert r["bewertung"] == "ROT"

    def test_auslastung_80_ist_gruen(self):
        r = bewerte_leitung_n1({"auslastung_prozent": 80, "i_betrieb_a": 400, "i_max_a": 500})
        assert r["bewertung"] == "GRUEN"

    def test_auslastung_120_ist_gelb(self):
        r = bewerte_leitung_n1({"auslastung_prozent": 120, "i_betrieb_a": 600, "i_max_a": 500})
        assert r["bewertung"] == "GELB"

    def test_auslastung_150_ist_rot(self):
        r = bewerte_leitung_n1({"auslastung_prozent": 150, "i_betrieb_a": 750, "i_max_a": 500})
        assert r["bewertung"] == "ROT"

    def test_i_pro_system_key_wird_akzeptiert(self):
        r = bewerte_leitung_n1({"auslastung_prozent": 90, "i_pro_system_a": 450, "i_max_a": 500})
        assert r["bewertung"] == "GRUEN"
        assert r["i_n1_a"] == 450.0


# ======================================================================
# 3. ABGANG-N-1
# ======================================================================
class TestAbgangN1:
    def test_keine_abgaenge_ist_nicht_geprueft(self):
        r = bewerte_abgang_n1({}, 180.0)
        assert r["bewertung"] == "NICHT_GEPRUEFT"

    def test_alternative_reserve_reicht_ist_gruen(self):
        r = bewerte_abgang_n1(
            {
                "umspannwerk": {
                    "abgaenge": [
                        {"label": "A1", "primary": True, "i_max_a": 630, "belastung_aktuell_a": 520},
                        {"label": "A2", "i_max_a": 630, "belastung_aktuell_a": 300},
                    ]
                }
            },
            180.0,
        )
        assert r["bewertung"] == "GRUEN"
        assert r["engpass_abgang_label"] == "A2"

    def test_alternative_reserve_unzureichend_ist_rot(self):
        r = bewerte_abgang_n1(
            {
                "umspannwerk": {
                    "abgaenge": [
                        {"label": "A1", "primary": True, "i_max_a": 630, "belastung_aktuell_a": 520},
                        {"label": "A2", "i_max_a": 630, "belastung_aktuell_a": 520},
                    ]
                }
            },
            180.0,
        )
        assert r["bewertung"] == "ROT"
        assert r["reserve_ratio"] < 0.8


# ======================================================================
# 4. SPANNUNG-N-1
# ======================================================================
class TestSpannungN1:
    def test_kein_input_ist_nicht_geprueft(self):
        r = bewerte_spannung_n1(None)
        assert r["bewertung"] == "NICHT_GEPRUEFT"

    def test_3prozent_ist_gruen(self):
        r = bewerte_spannung_n1({"delta_u_prozent": 3.0})
        assert r["bewertung"] == "GRUEN"

    def test_8prozent_ist_gelb(self):
        r = bewerte_spannung_n1({"delta_u_prozent": 8.0})
        assert r["bewertung"] == "GELB"

    def test_12prozent_ist_rot(self):
        r = bewerte_spannung_n1({"delta_u_prozent": 12.0})
        assert r["bewertung"] == "ROT"

    def test_negative_delta_wird_als_betrag_bewertet(self):
        r = bewerte_spannung_n1({"delta_u_prozent": -8.0})
        assert r["bewertung"] == "GELB"

    def test_ms_mit_nennspannung_nutzt_schwellen_3_5_pct(self):
        r = bewerte_spannung_n1({"delta_u_prozent": 4.0}, nennspannung_kv=20.0)
        assert r["bewertung"] == "GELB"
        assert r["grenze_prozent"] == 5.0

    def test_ms_2prozent_gruen(self):
        r = bewerte_spannung_n1({"delta_u_prozent": 2.0}, nennspannung_kv=10.0)
        assert r["bewertung"] == "GRUEN"

    def test_ms_8prozent_rot(self):
        r = bewerte_spannung_n1({"delta_u_prozent": 8.0}, nennspannung_kv=20.0)
        assert r["bewertung"] == "ROT"


# ======================================================================
# 5. N1-KLASSE + KONFIDENZ
# ======================================================================
class TestN1Klasse:
    def test_alles_geprueft_ist_n1_3(self):
        r = bestimme_n1_klasse(
            {"bewertung": "GRUEN"}, {"bewertung": "GRUEN"},
            {"bewertung": "GRUEN"}, {"bewertung": "GRUEN"}, {"bewertung": "GRUEN"},
        )
        assert r == "N1-3"

    def test_nur_topo_und_leitung_ist_n1_2(self):
        r = bestimme_n1_klasse(
            {"bewertung": "GRUEN"}, {"bewertung": "GRUEN"},
            {"bewertung": "NICHT_GEPRUEFT"}, {"bewertung": "NICHT_GEPRUEFT"}, {"bewertung": "NICHT_GEPRUEFT"},
        )
        assert r == "N1-2"

    def test_nur_topo_ist_n1_1(self):
        r = bestimme_n1_klasse(
            {"bewertung": "GRUEN"}, {"bewertung": "NICHT_GEPRUEFT"},
            {"bewertung": "NICHT_GEPRUEFT"}, {"bewertung": "NICHT_GEPRUEFT"}, {"bewertung": "NICHT_GEPRUEFT"},
        )
        assert r == "N1-1"

    def test_nichts_ist_n1_0(self):
        r = bestimme_n1_klasse(
            {"bewertung": "NICHT_GEPRUEFT"}, {"bewertung": "NICHT_GEPRUEFT"},
            {"bewertung": "NICHT_GEPRUEFT"}, {"bewertung": "NICHT_GEPRUEFT"}, {"bewertung": "NICHT_GEPRUEFT"},
        )
        assert r == "N1-0"

    def test_mit_dso_daten_ist_n1_4(self):
        r = bestimme_n1_klasse(
            {"bewertung": "GRUEN"}, {"bewertung": "GRUEN"},
            {"bewertung": "GRUEN"}, {"bewertung": "GRUEN"}, {"bewertung": "GRUEN"},
            dso_daten_vorhanden=True,
        )
        assert r == "N1-4"

    def test_konfidenz_n1_3_ohne_defaults(self):
        assert berechne_konfidenz("N1-3", 0) == 0.80

    def test_konfidenz_sinkt_mit_defaults(self):
        k0 = berechne_konfidenz("N1-3", 0)
        k3 = berechne_konfidenz("N1-3", 3)
        assert k3 < k0
        assert k3 >= 0.10


# ======================================================================
# 6. AGGREGATION (analysiere_n1)
# ======================================================================
class TestAnalysiere:
    def test_minimal_eingabe_liefert_struktur(self):
        r = analysiere_n1({})
        for key in ["n1_topologie", "n1_leitung", "n1_abgang", "n1_trafo", "n1_spannung",
                    "gesamt", "annahmen", "berechnungs_version", "backend"]:
            assert key in r

    def test_gesamt_pflichtfelder(self):
        r = analysiere_n1({})
        for key in ["bewertung", "engpass_komponente", "n1_klasse", "konfidenz", "empfehlungen"]:
            assert key in r["gesamt"]

    def test_version_korrekt(self):
        r = analysiere_n1({})
        assert r["berechnungs_version"] == VERSION
        assert r["backend"] == "heuristik_v2_planer"

    def test_realistisches_szenario_pv_5mw_gut(self):
        eingabe = {
            "topologie": "ring",
            "leistung_mw": 5.0,
            "cos_phi": 0.95,
            "restkapazitaet_ms_mva": 10.0,
            "umspannwerk": {"trafos": [
                {"sn_mva": 40, "belastung_aktuell_mw": 10},
                {"sn_mva": 40, "belastung_aktuell_mw": 10},
            ]},
        }
        thermisch_n1 = {"auslastung_prozent": 70, "i_betrieb_a": 350, "i_max_a": 500}
        spannung_n1 = {"delta_u_prozent": 3.5}
        r = analysiere_n1(eingabe, thermisch_n1, spannung_n1)
        assert r["gesamt"]["bewertung"] == "GRUEN"
        assert r["gesamt"]["n1_klasse"] == "N1-3"
        assert r["gesamt"]["konfidenz"] >= 0.7

    def test_engpass_wird_erkannt(self):
        eingabe = {
            "topologie": "ring", "leistung_mw": 5.0, "cos_phi": 0.95,
            "restkapazitaet_ms_mva": 10.0,
            "umspannwerk": {"trafos": [
                {"sn_mva": 40, "belastung_aktuell_mw": 10},
                {"sn_mva": 40, "belastung_aktuell_mw": 10},
            ]},
        }
        thermisch_n1 = {"auslastung_prozent": 150, "i_betrieb_a": 750, "i_max_a": 500}
        spannung_n1 = {"delta_u_prozent": 2.0}
        r = analysiere_n1(eingabe, thermisch_n1, spannung_n1)
        assert r["gesamt"]["bewertung"] == "ROT"
        assert r["gesamt"]["engpass_komponente"] == "leitung"

    def test_abgangsreserve_und_verifizierte_daten_heben_klasse_auf_n1_4(self):
        eingabe = {
            "topologie": "ring",
            "leistung_mw": 5.0,
            "cos_phi": 0.95,
            "nennspannung": 20.0,
            "restkapazitaet_ms_mva": 10.0,
            "n1_datengrundlage": "dso_verified",
            "umspannwerk": {
                "datenquelle": "dso_verified",
                "trafos": [
                    {"sn_mva": 40, "belastung_aktuell_mw": 10},
                    {"sn_mva": 40, "belastung_aktuell_mw": 10},
                ],
                "abgaenge": [
                    {"label": "A1", "primary": True, "i_max_a": 630, "belastung_aktuell_a": 520, "datenquelle": "dso_verified"},
                    {"label": "A2", "i_max_a": 630, "belastung_aktuell_a": 250, "datenquelle": "dso_verified"},
                ],
            },
        }
        thermisch_n1 = {"auslastung_prozent": 70, "i_betrieb_a": 350, "i_max_a": 500}
        spannung_n1 = {"delta_u_prozent": 3.5}
        r = analysiere_n1(eingabe, thermisch_n1, spannung_n1)
        assert r["gesamt"]["n1_klasse"] == "N1-4"
        assert r["gesamt"]["dso_daten_vorhanden"] is True
        assert "Abgangsreserve / Betriebsmittelpfad" in r["gesamt"]["nachweise_vorhanden"]

    def test_n1_2_begruendet_unvollstaendige_nachweistiefe(self):
        eingabe = {
            "topologie": "ring",
            "leistung_mw": 5.0,
            "cos_phi": 0.95,
            "nennspannung": 20.0,
            "umspannwerk": {
                "abgaenge": [
                    {"label": "A1", "primary": True, "i_max_a": 630, "belastung_aktuell_a": 520},
                    {"label": "A2", "i_max_a": 630, "belastung_aktuell_a": 300},
                ],
            },
        }
        r = analysiere_n1(eingabe, thermisch_n1=None, spannung_n1=None)
        assert r["gesamt"]["n1_klasse"] == "N1-2"
        assert "Topologie plus Leitungs- oder Abgangsreserve" in r["gesamt"]["stufenbegruendung"]
        assert "Umspannwerks-Traforeserve" in r["gesamt"]["nachweise_fehlend"]


# ======================================================================
# 7. REVISIONSSICHERHEIT
# ======================================================================
class TestRevisionssicherheit:
    def test_annahmen_ist_liste(self):
        r = analysiere_n1({})
        assert isinstance(r["annahmen"], list)

    def test_default_annahmen_haben_quelle(self):
        r = analysiere_n1({})
        for a in r["annahmen"]:
            assert "feld" in a and "quelle" in a and "begruendung" in a
            assert a["quelle"] in ("user", "default")

    def test_empfehlungen_nicht_leer(self):
        r = analysiere_n1({})
        assert len(r["gesamt"]["empfehlungen"]) > 0
