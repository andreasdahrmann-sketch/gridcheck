import math


# Leitungsdaten: (R in Ohm/km, X in Ohm/km, Imax in A)
LEITUNGSDATEN = {
    "NAYY 150":  {"r": 0.206, "x": 0.080, "imax": 270},
    "NAYY 240":  {"r": 0.125, "x": 0.072, "imax": 360},
    "NA2XS2Y 150": {"r": 0.206, "x": 0.116, "imax": 275},
    "NA2XS2Y 240": {"r": 0.125, "x": 0.110, "imax": 365},
    "NAKBA 150": {"r": 0.206, "x": 0.080, "imax": 270},
}

# Nennspannungen pro Netzebene
NETZEBENEN = {
    "NS":  0.4,
    "MS":  20.0,
    "HS":  110.0,
}


def bestimme_netzebene(leistung_kw: float, spannung_kv: float = None) -> str:
    if spannung_kv:
        if spannung_kv <= 1.0:
            return "NS"
        elif spannung_kv <= 50.0:
            return "MS"
        else:
            return "HS"
    if leistung_kw <= 30:
        return "NS"
    elif leistung_kw <= 10000:
        return "MS"
    else:
        return "HS"


def get_skv_default(netzebene: str) -> float:
    defaults = {"NS": 10.0, "MS": 250.0, "HS": 3000.0}
    return defaults.get(netzebene, 250.0)


def run_check(
    leistung_kw: float,
    spannung_kv: float = None,
    leitungstyp: str = "NAYY 150",
    leitungslaenge_km: float = 1.0,
    skv_mva: float = None,
    bestehende_einspeisung_kw: float = 0,
    einspeiseart: str = "Volleinspeisung",
    typ: str = "PV",
) -> dict:

    score = 100
    empfehlungen = []
    details = {}

    # --- Netzebene ---
    netzebene = bestimme_netzebene(leistung_kw, spannung_kv)
    u_nenn = NETZEBENEN[netzebene]
    details["netzebene"] = netzebene
    details["u_nenn_kv"] = u_nenn

    # --- Kurzschlussleistung ---
    if skv_mva is None or skv_mva <= 0:
        skv_mva = get_skv_default(netzebene)
        details["skv_quelle"] = "Schätzwert"
    else:
        details["skv_quelle"] = "Benutzereingabe"
    details["skv_mva"] = skv_mva

    # --- Leitungsparameter ---
    leitung = LEITUNGSDATEN.get(leitungstyp, LEITUNGSDATEN["NAYY 150"])
    r_total = leitung["r"] * leitungslaenge_km
    x_total = leitung["x"] * leitungslaenge_km
    imax = leitung["imax"]
    details["leitungstyp"] = leitungstyp
    details["r_total_ohm"] = round(r_total, 4)
    details["x_total_ohm"] = round(x_total, 4)

    # --- Gesamtleistung ---
    p_gesamt_kw = leistung_kw + bestehende_einspeisung_kw
    details["p_gesamt_kw"] = p_gesamt_kw

    # --- cos phi je Anlagentyp ---
    cos_phi_map = {"PV": 1.0, "Wind": 0.95, "BESS": 1.0, "BioGas": 0.9, "KWK": 0.9}
    cos_phi = cos_phi_map.get(typ, 0.9)
    sin_phi = math.sqrt(1 - cos_phi**2)
    tan_phi = sin_phi / cos_phi if cos_phi > 0 else 0
    details["cos_phi"] = cos_phi

    # ============================================================
    # 1) SPANNUNGSBAND (Delta u nach vereinfachter VDE-Formel)
    # ============================================================
    delta_u = (p_gesamt_kw * r_total + p_gesamt_kw * tan_phi * x_total) / (u_nenn * u_nenn * 1000)
    delta_u_percent = abs(delta_u) * 100
    spannungsband_ok = delta_u_percent <= 3.0

    details["delta_u_percent"] = round(delta_u_percent, 2)
    details["spannungsband_ok"] = spannungsband_ok

    if not spannungsband_ok:
        score -= 30
        empfehlungen.append(
            "Spannungsanhebung " + str(round(delta_u_percent, 2))
            + "% überschreitet 3%-Grenze. Leitungsverstaerkung oder kuerzere Anbindung noetig."
        )
    elif delta_u_percent > 2.0:
        score -= 10
        empfehlungen.append(
            "Spannungsanhebung " + str(round(delta_u_percent, 2))
            + "% im Grenzbereich. Detailpruefung empfohlen."
        )

    # ============================================================
    # 2) THERMISCHE AUSLASTUNG
    # ============================================================
    i_betrieb = (p_gesamt_kw) / (math.sqrt(3) * u_nenn * cos_phi) if u_nenn > 0 else 0
    therm_auslastung = (i_betrieb / imax) * 100 if imax > 0 else 999
    thermische_auslastung_ok = therm_auslastung <= 100

    details["i_betrieb_a"] = round(i_betrieb, 1)
    details["imax_a"] = imax
    details["therm_auslastung_percent"] = round(therm_auslastung, 1)
    details["thermische_auslastung_ok"] = thermische_auslastung_ok

    if not thermische_auslastung_ok:
        score -= 30
        empfehlungen.append(
            "Thermische Auslastung " + str(round(therm_auslastung, 1))
            + "% - Leitung ueberlastet! Groesserer Querschnitt oder parallele Leitung noetig."
        )
    elif therm_auslastung > 80:
        score -= 15
        empfehlungen.append(
            "Thermische Auslastung " + str(round(therm_auslastung, 1))
            + "% - Grenzbereich, Leitungsverstaerkung empfohlen."
        )

    # ============================================================
    # 3) KURZSCHLUSSLEISTUNGSVERHÄLTNIS (Skv / Sanlage)
    # ============================================================
    s_anlage_mva = p_gesamt_kw / 1000.0
    skv_ratio = skv_mva / s_anlage_mva if s_anlage_mva > 0 else 999
    kurzschluss_ok = skv_ratio >= 25

    details["s_anlage_mva"] = round(s_anlage_mva, 3)
    details["skv_ratio"] = round(skv_ratio, 1)
    details["kurzschluss_ok"] = kurzschluss_ok

    if not kurzschluss_ok:
        score -= 25
        empfehlungen.append(
            "Kurzschlussleistungsverhaeltnis Skv/S = " + str(round(skv_ratio, 1))
            + " < 25. Netzverstaerkung oder hoeherer Anschlusspunkt noetig."
        )

    # ============================================================
    # 4) N-1 ANALYSE (vereinfacht: doppelte Auslastung)
    # ============================================================
    n1_therm = therm_auslastung * 2
    n1_ok = n1_therm <= 100

    details["n1_therm_percent"] = round(n1_therm, 1)
    details["n1_ok"] = n1_ok

    if not n1_ok:
        score -= 15
        empfehlungen.append(
            "N-1-Kriterium nicht erfuellt (Auslastung im Fehlerfall "
            + str(round(n1_therm, 1)) + "%). Redundanz erforderlich."
        )

    # ============================================================
    # SCORE & EMPFEHLUNG
    # ============================================================
    score = max(score, 0)

    if not empfehlungen:
        empfehlungen.append("Alle Kriterien erfuellt. Netzanschluss voraussichtlich realisierbar.")

    return {
        "score": score,
        "netzebene": netzebene,
        "spannungsband_ok": spannungsband_ok,
        "thermische_auslastung_ok": thermische_auslastung_ok,
        "kurzschluss_ok": kurzschluss_ok,
        "n1_ok": n1_ok,
        "empfehlung": " | ".join(empfehlungen),
        "details": details,
    }
import math

LEITUNGSDATEN = {
    "NAYY 150": (0.206, 0.080, 270),
    "NAYY 240": (0.125, 0.080, 360),
    "NA2XS2Y 150": (0.206, 0.110, 310),
    "NA2XS2Y 240": (0.125, 0.105, 410),
    "Al/St 240/40": (0.120, 0.390, 645),
}

def berechne_netzcheck(typ, leistung_kw, plz, spannung_kv=None,
                        skv_mva=None, bestehende_einspeisung_kw=0,
                        leitungstyp="NAYY 150", leitungslaenge_km=1.0,
                        einspeiseart="Volleinspeisung"):
    score = 100
    empfehlungen = []
    warnings = []

    if spannung_kv:
        if spannung_kv <= 1:
            netzebene = "NS (0.4 kV)"
            u_nenn = 0.4
        elif spannung_kv <= 30:
            netzebene = "MS (10/20 kV)"
            u_nenn = spannung_kv
        elif spannung_kv <= 150:
            netzebene = "HS (110 kV)"
            u_nenn = spannung_kv
        else:
            netzebene = "HoeS (220/380 kV)"
            u_nenn = spannung_kv
    else:
        if leistung_kw <= 30:
            netzebene, u_nenn = "NS (0.4 kV)", 0.4
        elif leistung_kw <= 10000:
            netzebene, u_nenn = "MS (20 kV)", 20.0
        elif leistung_kw <= 100000:
            netzebene, u_nenn = "HS (110 kV)", 110.0
        else:
            netzebene, u_nenn = "HoeS (380 kV)", 380.0

    if skv_mva and skv_mva > 0:
        s_kv = skv_mva
    else:
        defaults = {"NS (0.4 kV)": 10, "MS (20 kV)": 250, "MS (10/20 kV)": 250,
                     "HS (110 kV)": 3000, "HoeS (380 kV)": 10000, "HoeS (220/380 kV)": 10000}
        s_kv = defaults.get(netzebene, 250)
        warnings.append("Skv geschaetzt: " + str(s_kv) + " MVA (kein Wert angegeben)")

    ltg = LEITUNGSDATEN.get(leitungstyp, LEITUNGSDATEN["NAYY 150"])
    r_per_km, x_per_km, i_max_a = ltg
    laenge = max(leitungslaenge_km or 1.0, 0.1)

    r_total = r_per_km * laenge
    x_total = x_per_km * laenge
    z_total = math.sqrt(r_total**2 + x_total**2)

    p_gesamt_kw = leistung_kw + (bestehende_einspeisung_kw or 0)
    p_gesamt_mw = p_gesamt_kw / 1000.0

    i_betrieb = p_gesamt_kw / (math.sqrt(3) * u_nenn)

    therm_auslastung = (i_betrieb / i_max_a) * 100
    thermisch_ok = therm_auslastung <= 80

    if therm_auslastung > 100:
        score -= 30
        empfehlungen.append("Thermisch ueberlastet: " + str(round(therm_auslastung, 1)) + "% - Leitungsausbau zwingend")
    elif therm_auslastung > 80:
        score -= 15
        empfehlungen.append("Thermische Auslastung " + str(round(therm_auslastung, 1)) + "% - Grenzbereich")

    delta_u = (p_gesamt_kw * r_total + p_gesamt_kw * 0.4843 * x_total) / (u_nenn * u_nenn * 1000)
    delta_u_percent = abs(delta_u) * 100
    spannungsband_ok = delta_u_percent <= 3.0

    if delta_u_percent > 3.0:
        score -= 20
        empfehlungen.append("Spannungsaenderung " + str(round(delta_u_percent, 1)) + "% ueber 3% Grenze - Trafo/Reglerausbau pruefen")
    elif delta_u_percent > 2:
        score -= 5
        warnings.append("Spannungsaenderung " + str(round(delta_u_percent, 1)) + "% - im Grenzbereich")

    s_anlage_mva = p_gesamt_mw
    skv_verhaeltnis = s_kv / s_anlage_mva if s_anlage_mva > 0 else 9999
    kurzschluss_ok = skv_verhaeltnis >= 20

    if skv_verhaeltnis < 10:
        score -= 25
        empfehlungen.append("Skv/Sanlage = " + str(round(skv_verhaeltnis)) + " (Minimum 20) - Netz zu schwach")
    elif skv_verhaeltnis < 20:
        score -= 10
        empfehlungen.append("Skv/Sanlage = " + str(round(skv_verhaeltnis)) + " - Flickerberechnung erforderlich")

    n1_therm = therm_auslastung * 2
    n1_ok = n1_therm <= 100

    if n1_therm > 120:
        score -= 20
        empfehlungen.append("N-1: Auslastung " + str(round(n1_therm)) + "% - Redundanz fehlt, Ausbau noetig")
    elif n1_therm > 100:
        score -= 10
        empfehlungen.append("N-1: Auslastung " + str(round(n1_therm)) + "% - knapp, Netzbetreiber-Abstimmung noetig")

    score = max(0, min(100, score))

    if not empfehlungen:
        empfehlungen.append("Netzanschluss voraussichtlich realisierbar ohne Ausbaumassnahmen")

    details = {
        "netzebene": netzebene,
        "spannung_kv": u_nenn,
        "skv_mva": s_kv,
        "p_gesamt_kw": p_gesamt_kw,
        "i_betrieb_a": round(i_betrieb, 1),
        "i_max_a": i_max_a,
        "therm_auslastung_pct": round(therm_auslastung, 1),
        "delta_u_pct": round(delta_u_percent, 2),
        "skv_verhaeltnis": round(skv_verhaeltnis, 1),
        "n1_auslastung_pct": round(n1_therm, 1),
        "leitungstyp": leitungstyp,
        "leitungslaenge_km": laenge,
        "r_total_ohm": round(r_total, 4),
        "x_total_ohm": round(x_total, 4),
        "z_total_ohm": round(z_total, 4),
        "warnings": warnings,
    }

    return {
        "score": score,
        "spannungsband_ok": spannungsband_ok,
        "thermische_auslastung_ok": thermisch_ok,
        "kurzschluss_ok": kurzschluss_ok,
        "n1_ok": n1_ok,
        "netzebene": netzebene,
        "empfehlung": "; ".join(empfehlungen),
        "details": details,
    }
