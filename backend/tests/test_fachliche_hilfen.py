"""Tests for conservative engine helpers (fachliche_hilfen)."""
from engine.fachliche_hilfen import (
    estimate_cable_length_km,
    erzeuge_blindleistung_trafo_warnungen,
    get_max_short_circuit_current_ka,
    kosten_leistungs_staffel_faktor,
    n1_mvp_dokumentation,
    power_limit_hints,
    resolve_cos_phi_for_calculation,
)


class TestEstimateCableLength:
    def test_user_distance_not_heuristic(self):
        r = estimate_cable_length_km({"nennspannung": 20, "entfernung_km": 3.5, "plz": "30159"})
        assert r["heuristisch"] is False
        assert r["entfernung_km"] == 3.5

    def test_missing_distance_is_heuristic_labeled(self):
        r = estimate_cable_length_km({"nennspannung": 20, "plz": "30159"})
        assert r["heuristisch"] is True
        assert "heuristische" in r["annahme"].lower()
        assert "keine gps" in r["annahme"].lower() or "Keine GPS" in r["annahme"]


class TestResolveCosPhi:
    def test_explicit_cos_phi(self):
        r = resolve_cos_phi_for_calculation({"cos_phi": 0.9, "anlagentyp": "PV"})
        assert r["cos_phi"] == 0.9
        assert r["quelle"] == "nutzer"

    def test_pv_default_near_one(self):
        r = resolve_cos_phi_for_calculation({"anlagentyp": "PV", "anschlussart": "Einspeisung"})
        assert r["cos_phi"] == 1.0
        assert r["quelle"] == "rolle_default"

    def test_bess_default_lower(self):
        r = resolve_cos_phi_for_calculation(
            {
                "project_components": [{"component_type": "battery", "capacity_kw": 2000}],
            }
        )
        assert r["cos_phi"] == 0.92


class TestShortCircuitBands:
    def test_ms_band_not_stuck_at_16ka(self):
        r = get_max_short_circuit_current_ka("MS", ik_berechnet_ka=5.0)
        assert r["ik_referenz_ka"] >= 16.0
        assert r["vorlaeufig"] is True
        assert "vorläufig" in r["hinweis"].lower() or "Vorläufig" in r["hinweis"]

    def test_user_sk_not_vorlaeufig(self):
        r = get_max_short_circuit_current_ka("MS", sk_mva_user=250, ik_berechnet_ka=22.0)
        assert r["vorlaeufig"] is False


class TestCostTier:
    def test_large_plant_higher_factor_than_small(self):
        small = kosten_leistungs_staffel_faktor(0.5, "MS")["faktor"]
        large = kosten_leistungs_staffel_faktor(25.0, "MS")["faktor"]
        assert large > small
        assert large > 1.0

    def test_no_flat_500kw_cap_semantics(self):
        """Tier continues scaling above 500 kW (2 MW MS plant)."""
        r = kosten_leistungs_staffel_faktor(5.0, "MS")
        assert r["leistung_kw"] == 5000
        assert r["faktor"] >= 1.25


class TestBlindleistungWarnings:
    def test_warns_when_not_modeled(self):
        warnings = erzeuge_blindleistung_trafo_warnungen(
            {"anschlussart": "Einspeisung"},
            {"auslastung_prozent": 50},
            {"q_mvar": 0, "p_mw": 5},
        )
        assert any("§9 EEG" in w or "nicht modelliert" in w for w in warnings)


class TestN1MvpDoc:
    def test_ms_large_plant_screening_active(self):
        doc = n1_mvp_dokumentation({"nennspannung": 20, "leistung_mw": 8.0}, "N1-2")
        assert doc["ms_screening_aktiv"] is True
        assert doc["mvp_max_klasse_ohne_dso"] == "N1-2"
        assert "2 MW" in doc["hinweis"] or "8.00 MW" in doc["hinweis"]


class TestPowerLimitHints:
    def test_ns_typical_limit(self):
        h = power_limit_hints("NS", 200)
        assert h["typical_max_kw"] == 135
        assert h["ueber_typischem_richtwert"] is True
