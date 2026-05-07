VOLTAGE_LEVELS = {
    "NS":    {"u_nom_kv": 0.4,   "delta_u_warn": 0.03, "delta_u_crit": 0.05, "tar": "VDE-AR-N 4105:2026-03"},
    "MS_10": {"u_nom_kv": 10.0,  "delta_u_warn": 0.02, "delta_u_crit": 0.03, "tar": "VDE-AR-N 4110:2023-09"},
    "MS_20": {"u_nom_kv": 20.0,  "delta_u_warn": 0.02, "delta_u_crit": 0.03, "tar": "VDE-AR-N 4110:2023-09"},
    "MS_30": {"u_nom_kv": 30.0,  "delta_u_warn": 0.02, "delta_u_crit": 0.03, "tar": "VDE-AR-N 4110:2023-09"},
    "HS":    {"u_nom_kv": 110.0, "delta_u_warn": 0.02, "delta_u_crit": 0.03, "tar": "VDE-AR-N 4120:2018-11"},
    "HoeS":  {"u_nom_kv": 380.0, "delta_u_warn": 0.015,"delta_u_crit": 0.02, "tar": "VDE-AR-N 4130"},
}

URBAN_PLZ_PREFIXES = ["10", "20", "30", "40", "50", "60", "70", "80"]

REFERENCE_VALUES = {
    "NS":    {"sk_mva": 10,    "trafo_mva": 0.63,  "dist_km": 0.3},
    "MS_10": {"sk_mva": 150,   "trafo_mva": 20,    "dist_km": 5.0},
    "MS_20": {"sk_mva": 250,   "trafo_mva": 20,    "dist_km": 3.0},
    "MS_30": {"sk_mva": 300,   "trafo_mva": 25,    "dist_km": 2.5},
    "HS":    {"sk_mva": 2000,  "trafo_mva": 63,    "dist_km": 10.0},
    "HoeS":  {"sk_mva": 10000, "trafo_mva": 300,   "dist_km": 25.0},
}

CABLE_DATABASE = {
    "NAYY 150":       {"r_ohm_km": 0.206, "x_ohm_km": 0.080, "i_max_a": 270, "u_level": "NS",  "material": "Al"},
    "NAYY 185":       {"r_ohm_km": 0.164, "x_ohm_km": 0.078, "i_max_a": 310, "u_level": "NS",  "material": "Al"},
    "NAYY 240":       {"r_ohm_km": 0.125, "x_ohm_km": 0.075, "i_max_a": 360, "u_level": "NS",  "material": "Al"},
    "NA2XS2Y 150":    {"r_ohm_km": 0.206, "x_ohm_km": 0.110, "i_max_a": 305, "u_level": "MS",  "material": "Al"},
    "NA2XS2Y 185":    {"r_ohm_km": 0.164, "x_ohm_km": 0.108, "i_max_a": 350, "u_level": "MS",  "material": "Al"},
    "NA2XS2Y 240":    {"r_ohm_km": 0.125, "x_ohm_km": 0.105, "i_max_a": 410, "u_level": "MS",  "material": "Al"},
    "NA2XS2Y 300":    {"r_ohm_km": 0.100, "x_ohm_km": 0.102, "i_max_a": 460, "u_level": "MS",  "material": "Al"},
    "Al/St 120":      {"r_ohm_km": 0.236, "x_ohm_km": 0.350, "i_max_a": 410, "u_level": "HS",  "material": "Al/St"},
    "Al/St 185":      {"r_ohm_km": 0.157, "x_ohm_km": 0.340, "i_max_a": 520, "u_level": "HS",  "material": "Al/St"},
    "Al/St 240":      {"r_ohm_km": 0.118, "x_ohm_km": 0.330, "i_max_a": 645, "u_level": "HS",  "material": "Al/St"},
}

DEFAULT_CABLE = {
    "NS": "NAYY 150",
    "MS_10": "NA2XS2Y 150",
    "MS_20": "NA2XS2Y 185",
    "MS_30": "NA2XS2Y 240",
    "HS": "Al/St 185",
    "HoeS": "Al/St 240",
}

TRAFO_DEFAULTS = {
    "NS":    {"s_mva": 0.63,  "uk_percent": 4.0,  "vg": "Dyn5"},
    "MS_10": {"s_mva": 20.0,  "uk_percent": 10.0, "vg": "YNd5"},
    "MS_20": {"s_mva": 20.0,  "uk_percent": 12.0, "vg": "YNd5"},
    "MS_30": {"s_mva": 25.0,  "uk_percent": 12.0, "vg": "YNd5"},
    "HS":    {"s_mva": 63.0,  "uk_percent": 12.0, "vg": "YNyn0d5"},
    "HoeS":  {"s_mva": 300.0, "uk_percent": 14.0, "vg": "YNyn0d5"},
}

COST_REFERENCE = {
    "NS":    {"trasse_eur_km": 60000,   "station_eur": 15000},
    "MS_10": {"trasse_eur_km": 120000,  "station_eur": 80000},
    "MS_20": {"trasse_eur_km": 120000,  "station_eur": 80000},
    "MS_30": {"trasse_eur_km": 130000,  "station_eur": 90000},
    "HS":    {"trasse_eur_km": 350000,  "station_eur": 500000},
    "HoeS":  {"trasse_eur_km": 800000,  "station_eur": 2000000},
}

THRESHOLDS = {
    "sk_sn_green": 20,
    "sk_sn_yellow": 10,
    "sk_sn_red": 5,
    "netzrueckwirkung_hinweis": 0.02,
    "netzrueckwirkung_pruefung": 0.05,
    "netzrueckwirkung_kritisch": 0.10,
    "auslastung_gut": 0.60,
    "auslastung_eingeschraenkt": 0.80,
    "auslastung_kritisch": 1.00,
    "n1_auslastung_warn": 0.70,
    "n1_delta_u_warn": 0.03,
    "n1_delta_u_crit": 0.05,
}

# --- Mittelspannung: einheitliche Screening-Schwellen (Engine, nur MS) ---
# Stationaer: Richtwerte aus VOLTAGE_LEVELS MS_* (warn/crit) + oranges Band bis 5% vor ROT.
_MS_REF = VOLTAGE_LEVELS["MS_20"]
MS_SPANNUNG_SCREENING_STATIONAER = {
    "delta_u_gruen_max_pct": round(_MS_REF["delta_u_warn"] * 100, 2),
    "delta_u_gelb_max_pct": round(_MS_REF["delta_u_crit"] * 100, 2),
    "delta_u_orange_max_pct": 5.0,
    "delta_u_hartgrenze_pct": round(_MS_REF["delta_u_crit"] * 100, 2),
    "tar_verweis": _MS_REF["tar"],
}
# N-1-Spannung (Screening): konsistent mit THRESHOLDS n1_delta_u_warn / n1_delta_u_crit
MS_SPANNUNG_N1_SCREENING = {
    "gruen_max_pct": round(THRESHOLDS["n1_delta_u_warn"] * 100, 2),
    "gelb_max_pct": round(THRESHOLDS["n1_delta_u_crit"] * 100, 2),
}

PLAUSIBILITY = {
    "NS":    {"p_min_kw": 1,     "p_max_kw": 300},
    "MS_10": {"p_min_kw": 100,   "p_max_kw": 20000},
    "MS_20": {"p_min_kw": 100,   "p_max_kw": 30000},
    "MS_30": {"p_min_kw": 100,   "p_max_kw": 40000},
    "HS":    {"p_min_kw": 5000,  "p_max_kw": 200000},
    "HoeS":  {"p_min_kw": 50000, "p_max_kw": 2000000},
}

SCORE_WEIGHTS = {
    "capacity": 0.30,
    "voltage": 0.25,
    "short_circuit": 0.20,
    "security": 0.15,
    "data_quality": 0.10,
}

ALPHA_CU = 0.00393
ALPHA_AL = 0.00403
TEMP_REF = 20.0
