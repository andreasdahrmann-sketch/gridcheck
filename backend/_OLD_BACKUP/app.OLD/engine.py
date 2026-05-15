import math
from typing import Optional

# Defaults pro Kundentyp
DEFAULTS = {
    "household": {
        "trafo_kva": 400,
        "sk_mva": 10.0,
        "cable_length_m": 150,
        "cable_type": "NAYY",
        "cable_mm2": 150,
    },
    "commercial": {
        "trafo_kva": 630,
        "sk_mva": 15.0,
        "cable_length_m": 100,
        "cable_type": "NAYY",
        "cable_mm2": 240,
    },
    "industrial": {
        "trafo_kva": 1000,
        "sk_mva": 25.0,
        "cable_length_m": 50,
        "cable_type": "NYY",
        "cable_mm2": 300,
    },
}

# Spezifische Widerstaende in mOhm/m pro mm2
CABLE_RESISTANCE = {
    50: 0.641,
    95: 0.320,
    150: 0.206,
    185: 0.164,
    240: 0.125,
    300: 0.100,
}

CABLE_REACTANCE_MOHM_PER_M = 0.08  # typisch fuer NS-Kabel


def analyze_grid(data: dict) -> dict:
    ct = data["customer_type"]
    defaults = DEFAULTS[ct]
    voltage_v = 400.0  # 3-phasig NS

    # Parameter mit Fallbacks
    trafo_kva = data.get("trafo_power_kva") or defaults["trafo_kva"]
    sk_mva = data.get("sk_mva") or defaults["sk_mva"]
    cable_length = data.get("cable_length_m") or defaults["cable_length_m"]
    cable_mm2 = data.get("cable_cross_section_mm2") or defaults["cable_mm2"]
    cable_type = data.get("cable_type") or defaults["cable_type"]
    power_kw = data["power_kw"]

    # Confidence: wie viele Werte sind real vs. default
    user_fields = ["trafo_power_kva", "sk_mva", "cable_length_m", "cable_cross_section_mm2"]
    provided = sum(1 for f in user_fields if data.get(f) is not None)
    confidence = round(0.4 + (provided / len(user_fields)) * 0.6, 2)

    # --- Impedanzberechnung ---

    # 1. Netzimpedanz (vorgelagertes Netz)
    z_netz = (voltage_v ** 2) / (sk_mva * 1e6) * 1000  # mOhm

    # 2. Trafoimpedanz (uk=4% typisch)
    uk = 0.04
    z_trafo = uk * (voltage_v ** 2) / (trafo_kva * 1000) * 1000  # mOhm

    # 3. Kabelimpedanz
    r_per_m = CABLE_RESISTANCE.get(cable_mm2, 0.206)
    r_cable = r_per_m * cable_length  # mOhm
    x_cable = CABLE_REACTANCE_MOHM_PER_M * cable_length  # mOhm
    z_cable = math.sqrt(r_cable**2 + x_cable**2)

    # Gesamtimpedanz
    z_total = z_netz + z_trafo + z_cable

    # --- Kurzschlussstrom ---
    ik = (voltage_v / (math.sqrt(3) * z_total / 1000)) / 1000  # kA

    # --- Spannungsfall ---
    current_a = (power_kw * 1000) / (math.sqrt(3) * voltage_v)
    delta_u_v = math.sqrt(3) * current_a * (r_cable + x_cable * 0.3) / 1000  # vereinfacht
    delta_u_percent = round((delta_u_v / voltage_v) * 100, 2)

    # --- Max. Kapazitaet (bei 3% Spannungsfall) ---
    max_delta_u_v = 0.03 * voltage_v
    max_current = (max_delta_u_v * 1000) / (math.sqrt(3) * (r_cable + x_cable * 0.3))
    max_capacity_kw = round((math.sqrt(3) * voltage_v * max_current) / 1000, 1)

    # --- Score ---
    score = 100
    if delta_u_percent > 5:
        score -= 40
    elif delta_u_percent > 3:
        score -= 20
    elif delta_u_percent > 1.5:
        score -= 5

    if ik < 1.0:
        score -= 30
    elif ik < 3.0:
        score -= 15

    capacity_ratio = power_kw / max(max_capacity_kw, 1)
    if capacity_ratio > 1.0:
        score -= 30
    elif capacity_ratio > 0.8:
        score -= 15
    elif capacity_ratio > 0.6:
        score -= 5

    score = max(0, min(100, score))

    # Risk level
    if score >= 80:
        risk_level = "low"
    elif score >= 50:
        risk_level = "medium"
    else:
        risk_level = "high"

    # Recommendations
    recommendations = []
    if delta_u_percent > 3:
        recommendations.append("Spannungsfall ueberschreitet 3%% - groesseren Kabelquerschnitt pruefen")
    if delta_u_percent > 5:
        recommendations.append("Kritischer Spannungsfall - Netzverstaerkung erforderlich")
    if capacity_ratio > 0.8:
        recommendations.append("Netzauslastung ueber 80%% - Kapazitaetserweiterung empfohlen")
    if ik < 3.0:
        recommendations.append("Kurzschlussstrom niedrig - Selektivitaet pruefen")
    if power_kw > trafo_kva * 0.8:
        recommendations.append("Trafoleistung fast ausgeschoepft - groesseren Trafo pruefen")
    if not recommendations:
        recommendations.append("Netzanschluss erscheint ausreichend dimensioniert")

    return {
        "score": score,
        "risk_level": risk_level,
        "voltage_drop_percent": delta_u_percent,
        "max_capacity_kw": max_capacity_kw,
        "impedance_mohm": round(z_total, 2),
        "short_circuit_ka": round(ik, 2),
        "recommendations": recommendations,
        "confidence": confidence,
        "details": {
            "z_netz_mohm": round(z_netz, 2),
            "z_trafo_mohm": round(z_trafo, 2),
            "z_cable_mohm": round(z_cable, 2),
            "cable_type": cable_type,
            "cable_mm2": cable_mm2,
            "cable_length_m": cable_length,
            "trafo_kva": trafo_kva,
            "sk_mva": sk_mva,
            "current_a": round(current_a, 1),
        },
    }
