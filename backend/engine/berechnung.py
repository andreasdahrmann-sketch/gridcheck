from engine.fachliche_hilfen import (
    erzeuge_blindleistung_trafo_warnungen,
    erzeuge_technische_details,
    estimate_cable_length_km,
    get_max_short_circuit_current_ka,
    kosten_leistungs_staffel_faktor,
    n1_mvp_dokumentation,
    power_limit_hints,
    resolve_cos_phi_for_calculation,
)
from engine.n1_ms import bewerte_n1_ms
from engine.n1_analyse import analysiere_n1
from engine.revision import speichere_revision
from compliance import APP_VERSION_NORMSTAND, get_normen_fuer_spannungsebene

ENGINE_VERSION = "1.3.1"


def _norm_version_label(u_kv: float) -> str:
    norms = get_normen_fuer_spannungsebene(u_kv, nur_kategorien=["Anwendungsregel", "Norm"])
    details = "; ".join(f"{n.norm_id} ({n.stand})" for n in norms[:8])
    if details:
        return f"Registry {APP_VERSION_NORMSTAND} | {details}"
    return f"Registry {APP_VERSION_NORMSTAND}"
import math
from typing import Optional

from constants import MS_SPANNUNG_SCREENING_STATIONAER

# =============================================================================
# BETRIEBSMITTELDATEN
# =============================================================================

LEITUNGSDATEN = {
    'NAYY150':      {'i_max': 270, 'r_km': 0.206, 'x_km': 0.080, 'ebene': 'NS', 'material': 'Al', 'querschnitt': 150},
    'NAYY185':      {'i_max': 310, 'r_km': 0.164, 'x_km': 0.080, 'ebene': 'NS', 'material': 'Al', 'querschnitt': 185},
    'NAY2Y150':     {'i_max': 270, 'r_km': 0.206, 'x_km': 0.080, 'ebene': 'NS', 'material': 'Al', 'querschnitt': 150},
    'NA2XS2Y110':   {'i_max': 355, 'r_km': 0.164, 'x_km': 0.113, 'ebene': 'MS', 'material': 'Al', 'querschnitt': 110},
    'NA2XS2Y150':   {'i_max': 410, 'r_km': 0.124, 'x_km': 0.110, 'ebene': 'MS', 'material': 'Al', 'querschnitt': 150},
    'NA2XS2Y185':   {'i_max': 455, 'r_km': 0.099, 'x_km': 0.108, 'ebene': 'MS', 'material': 'Al', 'querschnitt': 185},
    'NA2XS2Y240':   {'i_max': 530, 'r_km': 0.077, 'x_km': 0.105, 'ebene': 'MS', 'material': 'Al', 'querschnitt': 240},
    'NA2XS2Y300':   {'i_max': 590, 'r_km': 0.060, 'x_km': 0.102, 'ebene': 'MS', 'material': 'Al', 'querschnitt': 300},
    'AL240':        {'i_max': 645, 'r_km': 0.120, 'x_km': 0.390, 'ebene': 'HS', 'material': 'Al', 'querschnitt': 240},
    'AL_STAHL240':  {'i_max': 645, 'r_km': 0.120, 'x_km': 0.390, 'ebene': 'HS', 'material': 'AlSt', 'querschnitt': 240},
    'ACSR240':      {'i_max': 645, 'r_km': 0.120, 'x_km': 0.390, 'ebene': 'HS', 'material': 'AlSt', 'querschnitt': 240},
}

# Typische R/X-Verhältnisse Vorgelagertes Netz
RX_RATIO_DEFAULT = {
    'NS': 2.5,
    'MS': 1.5,
    'HS': 0.1,
}

# Typische Sk-Werte je Spannungsebene (MVA) - konservative Defaults
SK_DEFAULT = {
    'NS': 10,
    'MS': 250,
    'HS': 3000,
}

# Standard-Trafodaten
TRAFO_DEFAULTS = {
    'NS': {'s_mva': 0.63, 'uk_prozent': 4.0},
    'MS': {'s_mva': 25.0, 'uk_prozent': 12.0},
    'HS': {'s_mva': 63.0, 'uk_prozent': 13.0},
}

# Referenzkosten für Kostenschätzung
REFERENZKOSTEN = {
    'NS': {'tiefbau_eur_m': 120, 'kabel_eur_m': 45, 'trafostation_eur': 35000,
            'schaltanlage_eur': 15000, 'planung_prozent': 12, 'genehmigung_eur': 5000},
    'MS': {'tiefbau_eur_m': 160, 'kabel_eur_m': 85, 'trafostation_eur': 120000,
            'schaltanlage_eur': 85000, 'planung_prozent': 10, 'genehmigung_eur': 15000},
    'HS': {'tiefbau_eur_m': 280, 'kabel_eur_m': 220, 'trafostation_eur': 800000,
            'schaltanlage_eur': 450000, 'planung_prozent': 8, 'genehmigung_eur': 50000},
}

ALPHA_AL = 0.00403   # Temperaturkoeffizient Aluminium
ALPHA_CU = 0.00393   # Temperaturkoeffizient Kupfer

# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

def _float_or(val, default):
    if val is None or val == '' or val == 'None':
        return default
    try:
        v = float(val)
        return v if v > 0 else default
    except (ValueError, TypeError):
        return default


def _float_or_none(val):
    if val is None or val == '' or val == 'None':
        return None
    try:
        v = float(val)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _is_valid_number(val):
    if val is None or val == '' or val == 'None':
        return False
    try:
        return float(val) > 0
    except (ValueError, TypeError):
        return False


def bestimme_spannungsebene(u_kv):
    if u_kv >= 60:
        return 'HS'
    elif u_kv >= 1:
        return 'MS'
    else:
        return 'NS'


# =============================================================================
# P-Q-S GRUNDMODELL
# =============================================================================

def berechne_pqs(p_mw, cos_phi):
    """Berechnet P, Q, S konsistent aus P und cos_phi"""
    p_mw = abs(p_mw)
    cos_phi = max(0.8, min(1.0, cos_phi))
    s_mva = p_mw / cos_phi
    q_mvar = p_mw * math.tan(math.acos(cos_phi))
    return {
        'p_mw': round(p_mw, 4),
        'q_mvar': round(q_mvar, 4),
        's_mva': round(s_mva, 4),
        'cos_phi': round(cos_phi, 4),
    }


def berechne_wirksame_leistung(p_mw: float, bestehende_einspeisung_mw: float, anschlussart: str) -> float:
    """
    Ermittelt die am Netz wirksame Leistung fuer den aktuellen Check.

    - Einspeisung/Speicher (Worst-Case Einspeisung): bestehende Einspeisung additiv.
    - Entnahme: bestehende Einspeisung reduziert den Netto-Bezug (nicht negativ).
    """
    p = max(0.0, float(p_mw))
    bestehend = max(0.0, float(bestehende_einspeisung_mw))
    if anschlussart == 'Entnahme':
        return max(0.0, p - bestehend)
    return p + bestehend


def berechne_betriebsstrom(s_mva, u_kv):
    """I = S / (sqrt(3) * U) - immer S-basiert"""
    u_v = u_kv * 1000.0
    s_va = s_mva * 1e6
    return s_va / (math.sqrt(3) * u_v)


# =============================================================================
# IMPEDANZMODELL: Quelle + Trafo + Leitung
# =============================================================================

def berechne_quellenimpedanz(u_kv, sk_mva, rx_ratio):
    """Z_Q = U² / S_k, aufgeteilt in R_Q und X_Q"""
    u_v = u_kv * 1000.0
    z_q = (u_v ** 2) / (sk_mva * 1e6)
    r_q = z_q / math.sqrt(1 + rx_ratio ** 2)
    x_q = r_q * rx_ratio
    return r_q, x_q


def berechne_trafoimpedanz(u_kv, s_trafo_mva, uk_prozent):
    """Z_T = (uk/100) * U² / S_T"""
    u_v = u_kv * 1000.0
    z_t = (uk_prozent / 100.0) * (u_v ** 2) / (s_trafo_mva * 1e6)
    # Vereinfachung: R_T << X_T, daher X_T ˜ Z_T
    r_t = z_t * 0.1  # typisch 10% R-Anteil
    x_t = z_t * math.sqrt(1 - 0.1**2)
    return r_t, x_t


def berechne_leitungsimpedanz(leitungstyp, entfernung_km, parallele_systeme, temperatur_c=20):
    """Leitungsimpedanz mit Temperaturkorrektur und Parallelschaltung"""
    daten = LEITUNGSDATEN[leitungstyp]
    alpha = ALPHA_AL if daten['material'] in ('Al', 'AlSt') else ALPHA_CU

    r_km_korr = daten['r_km'] * (1 + alpha * (temperatur_c - 20))
    r_l = (r_km_korr * entfernung_km) / parallele_systeme
    x_l = (daten['x_km'] * entfernung_km) / parallele_systeme
    return r_l, x_l


def berechne_gesamtimpedanz(r_q, x_q, r_t, x_t, r_l, x_l):
    """Z_ges = Z_Q + Z_T + Z_L"""
    r_ges = r_q + r_t + r_l
    x_ges = x_q + x_t + x_l
    z_ges = math.sqrt(r_ges**2 + x_ges**2)
    return r_ges, x_ges, z_ges


# =============================================================================
# VALIDIERUNG
# =============================================================================

def validiere_eingabe(eingabe):
    fehler = []
    warnungen = []

    pflichtfelder = ['nennspannung', 'leistung_mw', 'leitungstyp', 'entfernung_km', 'anschlussart']
    for feld in pflichtfelder:
        if feld not in eingabe:
            fehler.append(f'Pflichtfeld fehlt: {feld}')

    if fehler:
        return fehler, warnungen

    # Nennspannung
    try:
        u = float(eingabe['nennspannung'])
        if u <= 0 or u > 380:
            fehler.append(f'Nennspannung unrealistisch: {u} kV')
    except (ValueError, TypeError):
        fehler.append('Nennspannung ist keine gueltige Zahl')
        return fehler, warnungen

    # Leistung
    try:
        p = float(eingabe['leistung_mw'])
        if p <= 0 or p > 2000:
            fehler.append(f'Leistung unrealistisch: {p} MW')
        # Plausibilitaet: Leistung vs Spannungsebene
        ebene = bestimme_spannungsebene(u)
        if ebene == 'NS' and p > 0.3:
            warnungen.append(f'Leistung {p} MW in NS unueblich. MS-Anschluss pruefen.')
        if ebene == 'NS' and p > 1.0:
            fehler.append(f'{p} MW in NS nicht realisierbar. MS oder HS waehlen.')
        if ebene == 'MS' and p > 50:
            warnungen.append(f'Leistung {p} MW in MS unueblich. HS-Anschluss pruefen.')
        if ebene == 'MS' and p < 0.01:
            warnungen.append(f'Leistung {p} MW sehr klein fuer MS. NS-Anschluss pruefen.')
    except (ValueError, TypeError):
        fehler.append('Leistung ist keine gueltige Zahl')

    # Entfernung
    try:
        d = float(eingabe['entfernung_km'])
        if d <= 0 or d > 500:
            fehler.append(f'Entfernung unrealistisch: {d} km')
        if d < 0.01:
            warnungen.append('Entfernung < 10m: Direkt am UW? Leitungsimpedanz vernachlaessigbar.')
    except (ValueError, TypeError):
        fehler.append('Entfernung ist keine gueltige Zahl')

    # Leitungstyp
    lt = eingabe.get('leitungstyp', '')
    if lt not in LEITUNGSDATEN:
        fehler.append(f'Unbekannter Leitungstyp: {lt}')

    # Anschlussart
    aa = eingabe.get('anschlussart', '')
    if aa not in ('Einspeisung', 'Entnahme', 'Speicher'):
        fehler.append(f'Anschlussart ungueltig: {aa}')

    # cos_phi
    try:
        cp = float(eingabe.get('cos_phi', 0.95))
        if cp < 0.8 or cp > 1.0:
            fehler.append(f'cos phi ausserhalb 0.8-1.0: {cp}')
        # Widerspruch: cos_phi=1 bei netzdienlicher Regelung
        if cp == 1.0 and eingabe.get('blindleistung_modus') in ('Q(U)', 'Q(P)'):
            warnungen.append('cos phi = 1.0 bei aktiver Blindleistungsregelung ist widersprüchlich.')
    except (ValueError, TypeError):
        pass

    # Parallele Systeme
    try:
        ps = int(eingabe.get('parallele_systeme', 1))
        if ps < 1 or ps > 6:
            fehler.append(f'Parallele Systeme: 1-6 erlaubt, eingegeben: {ps}')
    except (ValueError, TypeError):
        fehler.append('Parallele Systeme ist keine gueltige Zahl')

    return fehler, warnungen


# =============================================================================
# DATENQUALITAET / CONFIDENCE SCORE
# =============================================================================

def berechne_datenqualitaet(eingabe):
    """Bewertet Guete der Eingabedaten: A=real, B=projektdaten, C=regional, D=heuristik"""

    # Gewichtete Felder
    feld_gewichte = {
        'sk_mva':           ('A', 12),
        'trafo_s_mva':      ('A', 10),
        'trafo_uk_prozent':  ('A', 8),
        'entfernung_km':    ('B', 10),
        'leitungstyp':      ('B', 8),
        'leistung_mw':      ('B', 10),
        'cos_phi':          ('B', 5),
        'nennspannung':     ('B', 8),
        'rx_ratio':         ('A', 5),
        'temperatur_c':     ('B', 3),
        'bestand_trafo_auslastung': ('A', 8),
        'bestand_strang_auslastung': ('A', 8),
        'topologie':        ('A', 5),
    }

    gesamt_gewicht = sum(g for _, g in feld_gewichte.values())
    erreicht = 0
    felder_mit_daten = 0
    felder_gesamt = len(feld_gewichte)
    felder_referenz = 0

    for feld, (klasse, gewicht) in feld_gewichte.items():
        if _is_valid_number(eingabe.get(feld)):
            erreicht += gewicht
            felder_mit_daten += 1
        elif feld in ('leitungstyp', 'nennspannung', 'leistung_mw', 'entfernung_km', 'cos_phi', 'topologie'):
            # Pflichtfelder oder Standard-Defaults gelten als vorhanden
            if eingabe.get(feld) is not None and eingabe.get(feld) != '':
                erreicht += gewicht * 0.7
                felder_mit_daten += 1
        else:
            felder_referenz += 1

    score = round((erreicht / gesamt_gewicht) * 100)

    if score >= 80:
        klasse = 'A'
        text = 'Gute Datenbasis. Ergebnis belastbar.'
    elif score >= 60:
        klasse = 'B'
        text = 'Solide Projektdaten. Ergebnis plausibel.'
    elif score >= 40:
        klasse = 'C'
        text = 'Teilweise Referenzdaten. Ergebnis eingeschraenkt belastbar.'
    else:
        klasse = 'D'
        text = 'Ueberwiegend Heuristik/Defaults. Nur grober Vorcheck.'

    referenz_anteil = (felder_referenz / felder_gesamt) * 100 if felder_gesamt > 0 else 0

    return {
        'score': score,
        'klasse': klasse,
        'text': text,
        'felder_mit_daten': felder_mit_daten,
        'felder_gesamt': felder_gesamt,
        'referenz_anteil_prozent': round(referenz_anteil),
        'belastbar': score >= 40,
        'warnung': 'Ergebnis nur eingeschraenkt belastbar' if referenz_anteil > 40 else None,
    }


# =============================================================================
# THERMISCHE ANALYSE (S-basiert)
# =============================================================================

def berechne_thermisch(s_mva, u_kv, leitungstyp, parallele_systeme=1):
    """Thermische Prüfung: I_betrieb vs I_zul — immer auf S-Basis"""
    daten = LEITUNGSDATEN[leitungstyp]
    i_max = daten['i_max']

    i_gesamt = berechne_betriebsstrom(s_mva, u_kv)
    i_pro_system = i_gesamt / parallele_systeme
    auslastung = (i_pro_system / i_max) * 100.0

    if auslastung <= 60:
        bewertung, text = 'GRUEN', 'Thermisch unkritisch. Genuegend Reserve vorhanden.'
    elif auslastung <= 80:
        bewertung, text = 'GELB', 'Thermisch akzeptabel. Reserve eingeschraenkt.'
    elif auslastung <= 100:
        bewertung, text = 'ORANGE', 'Thermisch grenzwertig. Kaum Reserve fuer N-1.'
    else:
        bewertung, text = 'ROT', 'Thermische Ueberlastung! Leitung nicht ausreichend dimensioniert.'

    return {
        'i_betrieb_gesamt_a': round(i_gesamt, 1),
        'i_pro_system_a': round(i_pro_system, 1),
        'i_max_a': i_max,
        'auslastung_prozent': round(auslastung, 1),
        'parallele_systeme': parallele_systeme,
        's_mva': round(s_mva, 4),
        'bewertung': bewertung,
        'text': text,
        'hinweis_verlegeart': 'Thermische Bewertung basiert auf konservativer Standardannahme (Erdverlegung, 20°C).',
    }


# =============================================================================
# TRAFO-AUSLASTUNG (S-basiert)
# =============================================================================

def berechne_trafo(s_mva, trafo_s_mva, bestand_auslastung_prozent=0):
    """Trafo-Auslastung auf S-Basis mit Bestandsberücksichtigung"""
    bestand_s = trafo_s_mva * (bestand_auslastung_prozent / 100.0)
    gesamt_s = bestand_s + s_mva
    auslastung = (gesamt_s / trafo_s_mva) * 100.0

    if auslastung <= 60:
        bewertung, text = 'GRUEN', 'Trafo unkritisch. Genuegend Reserve.'
    elif auslastung <= 80:
        bewertung, text = 'GELB', 'Trafo akzeptabel. Reserve eingeschraenkt.'
    elif auslastung <= 100:
        bewertung, text = 'ORANGE', 'Trafo grenzwertig.'
    else:
        bewertung, text = 'ROT', 'Trafo ueberlastet!'

    return {
        'trafo_s_mva': round(trafo_s_mva, 2),
        'anlage_s_mva': round(s_mva, 4),
        'bestand_s_mva': round(bestand_s, 4),
        'gesamt_s_mva': round(gesamt_s, 4),
        'auslastung_prozent': round(auslastung, 1),
        'bewertung': bewertung,
        'text': text,
    }


# =============================================================================
# SPANNUNGSAENDERUNG (signiert, Richtung Anhebung/Absenkung)
# =============================================================================

def berechne_spannung(p_mw, q_mvar, u_kv, r_ges, x_ges, anschlussart):
    """
    Signierte Spannungsänderung: ?u ˜ (R*P + X*Q) / U²
    Einspeisung ? Spannungsanhebung (positiv)
    Entnahme ? Spannungsabsenkung (negativ)
    """
    u_v = u_kv * 1000.0
    p_w = p_mw * 1e6
    q_var = q_mvar * 1e6

    # Vorzeichen: Einspeisung hebt Spannung, Entnahme senkt
    if anschlussart == 'Einspeisung':
        vorzeichen = 1.0
        richtung = 'Anhebung'
    elif anschlussart == 'Entnahme':
        vorzeichen = -1.0
        richtung = 'Absenkung'
    else:  # Speicher
        vorzeichen = 1.0  # Worst Case: Einspeisung
        richtung = 'Anhebung (Worst Case Einspeisung)'

    delta_u_v = vorzeichen * math.sqrt(3) * (r_ges * p_w + x_ges * q_var) / (math.sqrt(3) * u_v)
    # Vereinfachte Formel: delta_u ˜ (R*P + X*Q) / U²
    delta_u_v_approx = vorzeichen * (r_ges * p_w + x_ges * q_var) / u_v
    delta_u_proz = (abs(delta_u_v_approx) / u_v) * 100.0

    ebene = bestimme_spannungsebene(u_kv)

    # Ampellogik: MS konsistent mit constants.MS_SPANNUNG_* (VDE-AR-N 4110 Richtwerte in constants).
    # NS/HS: unveraendert (2 / 3 / 5), damit keine Nebenwirkung ausserhalb MS.
    if ebene == 'MS':
        g = MS_SPANNUNG_SCREENING_STATIONAER['delta_u_gruen_max_pct']
        y = MS_SPANNUNG_SCREENING_STATIONAER['delta_u_gelb_max_pct']
        o = MS_SPANNUNG_SCREENING_STATIONAER['delta_u_orange_max_pct']
        hart_du = MS_SPANNUNG_SCREENING_STATIONAER['delta_u_hartgrenze_pct']
        ms_tar = MS_SPANNUNG_SCREENING_STATIONAER.get('tar_verweis')
    else:
        g, y, o = 2.0, 3.0, 5.0
        hart_du = 5.0
        ms_tar = None

    if delta_u_proz <= g:
        bewertung, text = 'GRUEN', f'Spannungs{richtung.lower()} unkritisch.'
    elif delta_u_proz <= y:
        bewertung, text = 'GELB', f'Spannungs{richtung.lower()} akzeptabel, Reserve eingeschraenkt.'
    elif delta_u_proz <= o:
        bewertung, text = 'ORANGE', f'Spannungs{richtung.lower()} grenzwertig.'
    else:
        bewertung, text = 'ROT', f'Spannungs{richtung.lower()} ueberschreitet zulaessigen Bereich!'

    return {
        'delta_u_prozent': round(delta_u_proz, 3),
        'delta_u_v': round(abs(delta_u_v_approx), 1),
        'richtung': richtung,
        'vorzeichen': 'positiv' if vorzeichen > 0 else 'negativ',
        'spannungsebene': ebene,
        'delta_u_hartgrenze_pct': hart_du,
        'ms_norm_tar': ms_tar,
        'r_ges_ohm': round(r_ges, 5),
        'x_ges_ohm': round(x_ges, 5),
        'bewertung': bewertung,
        'text': text,
    }


# =============================================================================
# KURZSCHLUSS-SCREENING
# =============================================================================

def berechne_kurzschluss(u_kv, z_ges, s_mva, sk_mva):
    """
    Kurzschluss-Screening: Ik'', Sk/Sn, Netzrückwirkungs-Screening
    """
    u_v = u_kv * 1000.0
    c = 1.1  # Spannungsfaktor nach IEC 60909

    # Ik'' = c * U / (sqrt(3) * |Z_ges|)
    ik_max = (c * u_v) / (math.sqrt(3) * z_ges) if z_ges > 0 else 0
    ik_min = (0.95 * u_v) / (math.sqrt(3) * z_ges) if z_ges > 0 else 0  # c_min ˜ 0.95

    # Sk/Sn Verhältnis
    sk_sn = sk_mva / s_mva if s_mva > 0 else 999

    # Netzrückwirkungs-Screening: S_anlage/S_k
    rueckwirkung_ratio = s_mva / sk_mva if sk_mva > 0 else 999

    # Sk/Sn Bewertung
    if sk_sn > 20:
        sk_bewertung = 'GRUEN'
        sk_text = 'Kurzschlussniveau ausreichend.'
    elif sk_sn > 10:
        sk_bewertung = 'GELB'
        sk_text = 'Kurzschlussniveau: vertiefte Pruefung empfohlen.'
    else:
        sk_bewertung = 'ROT'
        sk_text = 'Kurzschlussniveau kritisch. Anschluss nur nach Detailpruefung.'

    # Netzrückwirkung
    if rueckwirkung_ratio <= 0.02:
        rw_bewertung = 'GRUEN'
        rw_text = 'Netzrueckwirkungen unkritisch.'
    elif rueckwirkung_ratio <= 0.05:
        rw_bewertung = 'GELB'
        rw_text = 'Netzrueckwirkungen: Hinweis beachten.'
    elif rueckwirkung_ratio <= 0.10:
        rw_bewertung = 'ORANGE'
        rw_text = 'Netzrueckwirkungsstudie empfohlen.'
    else:
        rw_bewertung = 'ROT'
        rw_text = 'Erhebliche Netzrueckwirkungen. Detailstudie zwingend.'

    # Gesamt: schlechtester Wert
    bewertungen = [sk_bewertung, rw_bewertung]
    if 'ROT' in bewertungen:
        gesamt = 'ROT'
    elif 'ORANGE' in bewertungen:
        gesamt = 'ORANGE'
    elif 'GELB' in bewertungen:
        gesamt = 'GELB'
    else:
        gesamt = 'GRUEN'

    return {
        'ik_max_ka': round(ik_max / 1000, 2),
        'ik_min_ka': round(ik_min / 1000, 2),
        'sk_mva': round(sk_mva, 1),
        'sk_sn_ratio': round(sk_sn, 1),
        'sk_bewertung': sk_bewertung,
        'sk_text': sk_text,
        'rueckwirkung_ratio': round(rueckwirkung_ratio, 4),
        'rw_bewertung': rw_bewertung,
        'rw_text': rw_text,
        'bewertung': gesamt,
        'text': sk_text + ' ' + rw_text,
        'schutzpruefung_noetig': sk_sn < 20 or rueckwirkung_ratio > 0.05,
    }


# =============================================================================
# N-1 PRE-SCREEN (umbenannt, korrekte Terminologie)
# =============================================================================

def berechne_n1_prescreen(thermisch, trafo, topologie, parallele, redundanz,
                          pqs=None, cos_phi=1.0, eingabe=None):
    """
    N-1 Wrapper:
    - Topologie-Bewertung kommt aus engine.n1_ms (Stakeholder-faehig, revisionssicher)
    - Leitungs-N-1 und Trafo-N-1 weiterhin hier (vereinfacht)
    Rueckgabe ist rueckwaertskompatibel + zusaetzliches Feld 'stakeholder'.
    """
    pqs = pqs or {}
    eingabe = eingabe or {}

    # 1) Stakeholder-Bewertung (Topologie)
    stakeholder = bewerte_n1_ms({
        "topologie": topologie,
        "leistung_mw": pqs.get("p_mw", 0.0),
        "cos_phi": cos_phi,
        "restkapazitaet_ms_mva": eingabe.get("restkapazitaet_ms_mva"),
    })
    topo_n1 = stakeholder["n1_sicher"]
    topo_text = stakeholder["begruendung_technisch"]
    topo_bewertung = stakeholder["bewertung"]

    # 2) Leitungs-N-1
    if parallele >= 2:
        n1_auslastung = thermisch['auslastung_prozent'] * parallele / (parallele - 1)
        leitung_n1 = n1_auslastung <= 100
        leitung_text = f"Parallelsystem-Ausfall: Auslastung {n1_auslastung:.1f}%."
    elif redundanz:
        n1_auslastung = thermisch['auslastung_prozent']
        leitung_n1 = n1_auslastung <= 100
        leitung_text = "Redundanz vorhanden, aber kein Parallelsystem modelliert."
    else:
        n1_auslastung = thermisch['auslastung_prozent']
        leitung_n1 = False
        leitung_text = "Keine Leitungsredundanz."

    # 3) Trafo-N-1 (vereinfacht)
    trafo_aus = trafo.get('auslastung_prozent', 0)
    trafo_n1 = trafo_aus <= 70
    trafo_text = f"Trafo-Auslastung {trafo_aus:.1f}% ({'N-1 ok' if trafo_n1 else 'kein N-1 Spielraum'})."

    # 4) Gesamtbewertung kombinieren
    # n1_sicher: True nur wenn alle drei Ebenen bestaetigt; None bei Datenluecke; sonst False
    if topo_n1 is None:
        # Topologie grundsaetzlich faehig, aber Restkapazitaet unbekannt
        n1_sicher = None if (leitung_n1 and trafo_n1) else False
    else:
        n1_sicher = bool(topo_n1 and leitung_n1 and trafo_n1)

    # Bewertungs-Kaskade (ROT > GELB > GRUEN)
    if topo_bewertung == 'ROT' or not leitung_n1 or trafo_aus > 100:
        bewertung = 'ROT'
    elif topo_bewertung == 'GELB' or not trafo_n1:
        bewertung = 'GELB'
    elif topo_bewertung == 'GRUEN' and leitung_n1 and trafo_n1:
        bewertung = 'GRUEN'
    else:
        bewertung = 'GELB'

    return {
        'n1_sicher': n1_sicher,
        'bewertung': bewertung,
        'topologie': topologie,
        'topologie_text': topo_text,
        'leitung_n1': leitung_n1,
        'leitung_text': leitung_text,
        'n1_auslastung_prozent': round(n1_auslastung, 2),
        'trafo_n1': trafo_n1,
        'trafo_text': trafo_text,
        'redundanz': redundanz,
        'parallele_systeme': parallele,
        'stakeholder': stakeholder,
    }


def _bewertung_rang(bewertung):
    return {
        'NICHT_GEPRUEFT': -1,
        'GRUEN': 0,
        'GELB': 1,
        'ORANGE': 2,
        'ROT': 3,
    }.get(str(bewertung or '').upper(), -1)


def _schlechteste_bewertung(*bewertungen):
    aktive = [b for b in bewertungen if _bewertung_rang(b) >= 0]
    if not aktive:
        return 'NICHT_GEPRUEFT'
    return max(aktive, key=_bewertung_rang)


def _append_unique_text(items, text):
    if text and text not in items:
        items.append(text)


def _n1_annahmen_texte(n1_detail):
    annahmen = []
    for item in n1_detail.get('annahmen', []) if isinstance(n1_detail, dict) else []:
        if not isinstance(item, dict):
            continue
        begruendung = _safe_text(item.get('begruendung'))
        if begruendung:
            annahmen.append(begruendung)
    return annahmen


def _n1_detailtext(n1_basis, n1_detail):
    detail_gesamt = n1_detail.get('gesamt', {}) if isinstance(n1_detail, dict) else {}
    teile = []
    n1_klasse = _safe_text(detail_gesamt.get('n1_klasse'))
    bewertung = _safe_text(detail_gesamt.get('bewertung') or n1_basis.get('bewertung'))
    engpass = _safe_text(detail_gesamt.get('engpass_komponente'))
    stufenbegruendung = _safe_text(detail_gesamt.get('stufenbegruendung'))

    if n1_klasse:
        teile.append(f'N-1-Level {n1_klasse}')
    if bewertung:
        teile.append(f'Gesamtbewertung {bewertung}')
    if engpass and engpass != 'keine':
        teile.append(f'Engpass {engpass}')
    if stufenbegruendung:
        teile.append(stufenbegruendung)

    komponenten = []
    for label, key in (
        ('Topologie', 'n1_topologie'),
        ('Abgang', 'n1_abgang'),
        ('Leitung', 'n1_leitung'),
        ('Trafo', 'n1_trafo'),
        ('Spannung', 'n1_spannung'),
    ):
        block = n1_detail.get(key, {}) if isinstance(n1_detail, dict) else {}
        if not isinstance(block, dict):
            continue
        if _safe_text(block.get('bewertung')) in ('', 'NICHT_GEPRUEFT'):
            continue
        klartext = _safe_text(block.get('begruendung_klartext'))
        if klartext:
            komponenten.append(f'{label}: {klartext}')

    if komponenten:
        teile.append(' | '.join(komponenten[:2]))
    basis_text = _safe_text(n1_basis.get('topologie_text'))
    if basis_text and not komponenten:
        teile.append(basis_text)

    return '. '.join(teil for teil in teile if teil)


def konsolidiere_n1_ergebnis(n1_basis, n1_detail):
    basis = dict(n1_basis or {})
    if not isinstance(n1_detail, dict):
        basis['detail_text'] = _safe_text(basis.get('topologie_text'))
        basis['detail_empfehlungen'] = []
        basis['detail_annahmen'] = []
        return basis

    detail_gesamt = n1_detail.get('gesamt', {}) if isinstance(n1_detail.get('gesamt'), dict) else {}
    detail_bewertung = _safe_text(detail_gesamt.get('bewertung'))
    detail_empfehlungen = [
        str(item) for item in detail_gesamt.get('empfehlungen', [])
        if str(item).strip()
    ]
    detail_annahmen = _n1_annahmen_texte(n1_detail)

    basis['bewertung'] = _schlechteste_bewertung(basis.get('bewertung'), detail_bewertung)
    basis['n1_klasse'] = detail_gesamt.get('n1_klasse')
    basis['n1_konfidenz'] = detail_gesamt.get('konfidenz')
    basis['engpass_komponente'] = detail_gesamt.get('engpass_komponente', 'keine')
    basis['stufenbegruendung'] = detail_gesamt.get('stufenbegruendung')
    basis['nachweise_vorhanden'] = detail_gesamt.get('nachweise_vorhanden', [])
    basis['nachweise_fehlend'] = detail_gesamt.get('nachweise_fehlend', [])
    basis['dso_daten_vorhanden'] = detail_gesamt.get('dso_daten_vorhanden')
    basis['detail_empfehlungen'] = detail_empfehlungen
    basis['detail_annahmen'] = detail_annahmen

    if detail_bewertung == 'ROT':
        basis['n1_sicher'] = False
    elif detail_bewertung == 'GELB' and basis.get('n1_sicher') is not None:
        basis['n1_sicher'] = False

    detail_text = _n1_detailtext(basis, n1_detail)
    if detail_text:
        basis['detail_text'] = detail_text
        basis['topologie_text'] = detail_text
    else:
        basis['detail_text'] = _safe_text(basis.get('topologie_text'))

    return basis


# =============================================================================
# SZENARIOANALYSE
# =============================================================================

def berechne_szenarien(p_mw, q_mvar, s_mva, u_kv, r_ges, x_ges, leitungstyp,
                       parallele_systeme, anschlussart, sk_mva, z_ges,
                       trafo_s_mva, bestand_trafo_proz):
    """4 Pflichtszenarien gemäss Netzplaner-Vorgabe"""
    szenarien = []

    def run_szenario(name, p_fakt, q_fakt, beschreibung):
        p = p_mw * p_fakt
        q = q_mvar * q_fakt
        s = math.sqrt(p**2 + q**2)
        th = berechne_thermisch(s, u_kv, leitungstyp, parallele_systeme)
        sp = berechne_spannung(p, q, u_kv, r_ges, x_ges, anschlussart)
        tr = berechne_trafo(s, trafo_s_mva, bestand_trafo_proz)
        return {
            'name': name,
            'beschreibung': beschreibung,
            'p_mw': round(p, 4),
            'q_mvar': round(q, 4),
            's_mva': round(s, 4),
            'thermisch': th,
            'spannung': sp,
            'trafo': tr,
        }

    # 1. Maximale Einspeisung / minimale Last
    szenarien.append(run_szenario(
        'Max. Einspeisung',
        1.0, 1.0,
        'Volle Leistung, minimale Netzlast — kritischster Fall fuer Spannungsanhebung.'
    ))

    # 2. Typischer Betrieb (70%)
    szenarien.append(run_szenario(
        'Typischer Betrieb',
        0.7, 0.7,
        'Typischer Betriebspunkt bei 70% Nennleistung.'
    ))

    # 3. Reduzierter Betrieb (40%)
    szenarien.append(run_szenario(
        'Teillast',
        0.4, 0.4,
        'Teillastbetrieb bei 40% — fuer Normalbetriebsbewertung.'
    ))

    # 4. N-1 Reservebetrachtung (100% auf n-1 Systeme)
    if parallele_systeme >= 2:
        p_n1 = p_mw
        q_n1 = q_mvar
        s_n1 = s_mva
        th_n1 = berechne_thermisch(s_n1, u_kv, leitungstyp, parallele_systeme - 1)
        sp_n1 = berechne_spannung(p_n1, q_n1, u_kv, r_ges * parallele_systeme / (parallele_systeme - 1),
                                   x_ges * parallele_systeme / (parallele_systeme - 1), anschlussart)
        tr_n1 = berechne_trafo(s_n1, trafo_s_mva, bestand_trafo_proz)
        szenarien.append({
            'name': 'N-1 Stoerungsfall',
            'beschreibung': f'Volle Leistung auf {parallele_systeme - 1} von {parallele_systeme} Systemen.',
            'p_mw': round(p_n1, 4),
            'q_mvar': round(q_n1, 4),
            's_mva': round(s_n1, 4),
            'thermisch': th_n1,
            'spannung': sp_n1,
            'trafo': tr_n1,
        })
    else:
        szenarien.append(run_szenario(
            'N-1 Stoerungsfall',
            1.0, 1.0,
            'Kein paralleles System: N-1 = Volllast auf einziger Leitung.'
        ))

    return szenarien


# =============================================================================
# TEIL-SCORES (gewichtet)
# =============================================================================

def berechne_scores(thermisch, spannung, kurzschluss, n1, datenqualitaet, trafo):
    """5 Teilscores + gewichteter Gesamtscore"""

    def bew_to_score(bew):
        return {'GRUEN': 95, 'GELB': 65, 'ORANGE': 35, 'ROT': 10}.get(bew, 50)

    s_kap = min(bew_to_score(thermisch['bewertung']), bew_to_score(trafo['bewertung']))
    s_spg = bew_to_score(spannung['bewertung'])
    s_ks = bew_to_score(kurzschluss['bewertung'])
    s_n1 = bew_to_score(n1['bewertung'])
    s_dq = datenqualitaet['score']

    gesamt = round(0.30 * s_kap + 0.25 * s_spg + 0.20 * s_ks + 0.15 * s_n1 + 0.10 * s_dq)

    # Score-Caps:
    # Ein kritischer Einzelparameter darf nicht durch andere gute Teilwerte "weggemittelt" werden.
    # Caps greifen sowohl bei Bewertung==ROT als auch bei niedrigen Teilscores (ORANGE/<=40).
    score_caps = []

    # N-1 / Versorgungssicherheit
    if n1.get('bewertung') == 'ROT' or s_n1 <= 20:
        score_caps.append(('N-1-Kriterium nicht erfuellt (kritisch)', 35))
    elif s_n1 <= 40:
        score_caps.append(('N-1-Kriterium unzureichend', 60))

    # Spannung
    if spannung.get('bewertung') == 'ROT' or s_spg <= 20:
        score_caps.append(('Spannung kritisch', 35))
    elif s_spg <= 40:
        score_caps.append(('Spannung grenzwertig', 60))

    # Thermische Kapazitaet (Leitung)
    if thermisch.get('bewertung') == 'ROT' or bew_to_score(thermisch['bewertung']) <= 20:
        score_caps.append(('Leitung thermisch kritisch', 35))
    elif bew_to_score(thermisch['bewertung']) <= 40:
        score_caps.append(('Leitung thermisch grenzwertig', 60))

    # Trafo
    if trafo.get('bewertung') == 'ROT' or bew_to_score(trafo['bewertung']) <= 20:
        score_caps.append(('Trafo thermisch kritisch', 35))
    elif bew_to_score(trafo['bewertung']) <= 40:
        score_caps.append(('Trafo thermisch grenzwertig', 60))

    # Kurzschluss
    if kurzschluss.get('bewertung') == 'ROT' or s_ks <= 20:
        score_caps.append(('Kurzschlusskriterium kritisch', 30))
    elif s_ks <= 40:
        score_caps.append(('Kurzschlusskriterium grenzwertig', 60))

    if score_caps:
        gesamt = min([gesamt] + [cap for _grund, cap in score_caps])

    # Harte Grenze: echte Grenzwertverletzungen ueberschreiben Score nochmals strenger
    harte_verstoesse = []
    if thermisch['auslastung_prozent'] > 100:
        harte_verstoesse.append('Leitungsueberlastung > 100%')
    if trafo['auslastung_prozent'] > 100:
        harte_verstoesse.append('Trafoueberlastung > 100%')
    du_hart = float(spannung.get('delta_u_hartgrenze_pct', 5.0))
    if spannung['delta_u_prozent'] > du_hart:
        harte_verstoesse.append(
            f"Spannungsaenderung > {du_hart}% (Hartgrenze fuer {spannung.get('spannungsebene', '?')})"
        )

    # Nur KRITISCHE Caps (cap <= 40) gelten als harte Verstoesse -> Auto-C
    # Grenzwertige Caps (cap > 40) reduzieren nur den Score, fuehren aber nicht zwingend zu C
    weiche_hinweise = []
    for grund, cap in score_caps:
        if cap <= 40:
            harte_verstoesse.append(f'{grund} -> Score-Cap {cap}')
        else:
            weiche_hinweise.append(f'{grund} -> Score-Cap {cap}')

    if harte_verstoesse and (
        thermisch['auslastung_prozent'] > 100
        or trafo['auslastung_prozent'] > 100
        or spannung['delta_u_prozent'] > du_hart
    ):
        gesamt = min(gesamt, 25)

    return {
        'kapazitaet': s_kap,
        'spannung': s_spg,
        'kurzschluss': s_ks,
        'versorgungssicherheit': s_n1,
        'datenqualitaet': s_dq,
        'gesamt': gesamt,
        'harte_verstoesse': harte_verstoesse,
        'weiche_hinweise': weiche_hinweise,
    }


# =============================================================================
# KOSTEN-MODUL
# =============================================================================

def berechne_kosten(eingabe, spannungsebene, entfernung_km, parallele_systeme, p_mw=0.0):
    ref = REFERENZKOSTEN[spannungsebene]
    entfernung_m = entfernung_km * 1000
    staffel = kosten_leistungs_staffel_faktor(float(p_mw or 0), spannungsebene)
    leistungs_faktor = staffel['faktor']

    tiefbau_m = _float_or(eingabe.get('kosten_tiefbau_eur_m'), ref['tiefbau_eur_m'])
    kabel_m = _float_or(eingabe.get('kosten_kabel_eur_m'), ref['kabel_eur_m'])
    trafo = _float_or(eingabe.get('kosten_trafostation_eur'), ref['trafostation_eur']) * leistungs_faktor
    schaltanlage = _float_or(eingabe.get('kosten_schaltanlage_eur'), ref['schaltanlage_eur']) * leistungs_faktor
    genehmigung = _float_or(eingabe.get('kosten_genehmigung_eur'), ref['genehmigung_eur'])
    pacht_pa = _float_or(eingabe.get('kosten_pacht_eur_a'), 0)
    bkz = _float_or(eingabe.get('kosten_bkz_eur'), 0)
    netzentgelt_pa = _float_or(eingabe.get('kosten_netzentgelt_eur_a'), 0)

    kosten_trasse = (tiefbau_m + kabel_m) * entfernung_m * parallele_systeme
    kosten_station = trafo + schaltanlage
    kosten_genehm = genehmigung

    zwischensumme = kosten_trasse + kosten_station + kosten_genehm
    planung_prozent = _float_or(eingabe.get('kosten_planung_prozent'), ref['planung_prozent'])
    kosten_planung = zwischensumme * (planung_prozent / 100)

    investition_gesamt = zwischensumme + kosten_planung + bkz
    betriebskosten_pa = pacht_pa + netzentgelt_pa

    eigene_felder = ['kosten_tiefbau_eur_m', 'kosten_kabel_eur_m', 'kosten_trafostation_eur',
                     'kosten_schaltanlage_eur', 'kosten_genehmigung_eur']
    eigene_count = sum(1 for f in eigene_felder if _is_valid_number(eingabe.get(f)))
    konfidenz = 40 + (eigene_count / len(eigene_felder)) * 40
    spread_low = 0.15
    spread_high = 0.25
    risikotreiber = []
    band_annahmen = [
        'Kosten werden bewusst als Bandbreite und nicht als punktgenaue Aussage ausgegeben.',
        'Bandbreite basiert auf Anschlussdistanz, Spannungsebene, Parallelitaet und Anteil projektspezifischer Kosteneingaben.',
        staffel['annahme'],
    ]

    if eigene_count == 0:
        spread_low += 0.05
        spread_high += 0.10
        risikotreiber.append('Kostenbasis beruht ueberwiegend auf Referenzwerten ohne projektspezifische Einzelpreise.')
    if entfernung_km >= 5:
        spread_high += 0.05
        risikotreiber.append('Laengere Trassenentfernung kann Tiefbau-, Kabel- und Wegerechtskosten erhoehen.')
    if spannungsebene in ('MS', 'HS'):
        spread_high += 0.05
        risikotreiber.append('MS/HS-Anschluss erhoeht Stations-, Schutz- und Schaltanlagenscope.')
    if parallele_systeme > 1:
        spread_high += 0.05
        risikotreiber.append('Parallele Systeme erhoehen Material- und Tiefbauaufwand.')

    spread_low = min(spread_low, 0.25)
    spread_high = min(spread_high, 0.45)
    band_niedrig = investition_gesamt * (1 - spread_low)
    band_hoch = investition_gesamt * (1 + spread_high)

    return {
        'kosten_trasse_eur': round(kosten_trasse),
        'kosten_station_eur': round(kosten_station),
        'kosten_genehmigung_eur': round(kosten_genehm),
        'kosten_planung_eur': round(kosten_planung),
        'kosten_bkz_eur': round(bkz),
        'investition_gesamt_eur': round(investition_gesamt),
        'band_niedrig_eur': round(band_niedrig),
        'band_basis_eur': round(investition_gesamt),
        'band_hoch_eur': round(band_hoch),
        'betriebskosten_pa_eur': round(betriebskosten_pa),
        'konfidenz_prozent': round(konfidenz),
        'quelle': 'Eigene + Referenz' if eigene_count > 0 else 'Referenzwerte',
        'band_annahmen': band_annahmen,
        'hauptrisikotreiber': risikotreiber,
        'leistungs_staffel': staffel['stufe'],
        'leistungs_faktor': staffel['faktor'],
    }


# =============================================================================
# WIRTSCHAFTLICHKEIT
# =============================================================================

def berechne_wirtschaftlichkeit(eingabe, kosten, p_mw):
    verguetung_ct = _float_or_none(eingabe.get('wirt_verguetung_ct_kwh'))
    volllaststunden = _float_or_none(eingabe.get('wirt_volllaststunden'))
    eigenverbrauch_pct = _float_or(eingabe.get('wirt_eigenverbrauch_prozent'), 0)
    wartung_pa = _float_or(eingabe.get('wirt_wartung_eur_a'), 0)

    if verguetung_ct is None or volllaststunden is None:
        return None

    p_kw = p_mw * 1000
    jahresertrag_kwh = p_kw * volllaststunden
    einspeisung_kwh = jahresertrag_kwh * (1 - eigenverbrauch_pct / 100)
    einnahmen_pa = einspeisung_kwh * (verguetung_ct / 100)

    betriebskosten_pa = kosten['betriebskosten_pa_eur'] + wartung_pa
    cashflow_pa = einnahmen_pa - betriebskosten_pa
    investition = kosten['investition_gesamt_eur']

    amortisation_jahre = investition / cashflow_pa if cashflow_pa > 0 else None
    laufzeit = 20
    gewinn_20a = (cashflow_pa * laufzeit) - investition
    roi_prozent = (gewinn_20a / investition) * 100 if investition > 0 else 0

    return {
        'jahresertrag_kwh': round(jahresertrag_kwh),
        'einnahmen_pa_eur': round(einnahmen_pa),
        'betriebskosten_pa_eur': round(betriebskosten_pa),
        'cashflow_pa_eur': round(cashflow_pa),
        'amortisation_jahre': round(amortisation_jahre, 1) if amortisation_jahre else None,
        'roi_20a_prozent': round(roi_prozent, 1),
        'bewertung': 'GRUEN' if amortisation_jahre and amortisation_jahre < 12 else
                     'GELB' if amortisation_jahre and amortisation_jahre < 18 else 'ROT',
    }


# =============================================================================
# NB-SCHWELLENWERTE
# =============================================================================

def pruefe_nb_schwellenwerte(eingabe, thermisch, spannung, kurzschluss):
    ergebnisse = []

    max_auslastung = _float_or_none(eingabe.get('nb_max_auslastung_prozent'))
    if max_auslastung is not None:
        ok = thermisch['auslastung_prozent'] <= max_auslastung
        ergebnisse.append({
            'kriterium': 'Max. Auslastung',
            'grenzwert': f'{max_auslastung}%',
            'istwert': f'{thermisch["auslastung_prozent"]}%',
            'erfuellt': ok,
        })

    max_sf = _float_or_none(eingabe.get('nb_max_spannungsfall_prozent'))
    if max_sf is not None:
        ok = spannung['delta_u_prozent'] <= max_sf
        ergebnisse.append({
            'kriterium': 'Max. Spannungsaenderung',
            'grenzwert': f'{max_sf}%',
            'istwert': f'{spannung["delta_u_prozent"]}%',
            'erfuellt': ok,
        })

    min_skv = _float_or_none(eingabe.get('nb_min_kurzschluss_ratio'))
    if min_skv is not None:
        ok = kurzschluss['sk_sn_ratio'] >= min_skv
        ergebnisse.append({
            'kriterium': 'Min. Kurzschlussleistungsverhaeltnis',
            'grenzwert': f'{min_skv}',
            'istwert': f'{kurzschluss["sk_sn_ratio"]}',
            'erfuellt': ok,
        })

    flags = []
    if eingabe.get('nb_netzdienlichkeit_bonus'):
        flags.append('Netzdienlichkeits-Bonus aktiv')
    if eingabe.get('nb_speicher_prio'):
        flags.append('Speicher-Priorisierung aktiv')
    if eingabe.get('nb_eigenkapital_nachweis'):
        flags.append('Eigenkapitalnachweis erforderlich')

    alle_erfuellt = all(e['erfuellt'] for e in ergebnisse if e['erfuellt'] is not None)

    return {
        'pruefungen': ergebnisse,
        'flags': flags,
        'alle_erfuellt': alle_erfuellt,
        'bewertung': 'NICHT_GEPRUEFT' if not ergebnisse else
                     'GRUEN' if alle_erfuellt else
                     'ROT',
    }


# =============================================================================
# EMPFEHLUNGEN (erweitert)
# =============================================================================

def erzeuge_empfehlungen(thermisch, spannung, kurzschluss, n1, trafo, nb_check, dq, pqs, eingabe):
    empfehlungen = []

    # Thermisch
    if thermisch['bewertung'] in ('ORANGE', 'ROT'):
        empfehlungen.append('Leitung hoeher dimensionieren oder zusaetzliches paralleles System einplanen.')
    if thermisch['bewertung'] == 'ROT':
        empfehlungen.append('Naechsthoehere Spannungsebene pruefen.')

    # Trafo
    if trafo['bewertung'] in ('ORANGE', 'ROT'):
        empfehlungen.append('Trafo hoeher dimensionieren oder 2. Trafo einplanen.')

    # Spannung
    if spannung['bewertung'] == 'ROT':
        empfehlungen.append('Anschlusspunkt naeher am UW waehlen oder Spannungsregelung vorsehen.')
    if spannung['bewertung'] in ('GELB', 'ORANGE', 'ROT'):
        empfehlungen.append('Blindleistungskompensation pruefen (cos phi optimieren).')
        if spannung['richtung'] == 'Anhebung':
            empfehlungen.append('Anschluss nur mit aktivierter Blindleistungsregelung plausibel.')

    # Kurzschluss
    if kurzschluss['schutzpruefung_noetig']:
        empfehlungen.append('Vertiefte Schutzpruefung erforderlich.')
    if kurzschluss['rw_bewertung'] in ('ORANGE', 'ROT'):
        empfehlungen.append('Netzrueckwirkungsstudie (Flicker/THD) beauftragen.')

    # N-1
    if not n1['n1_sicher']:
        empfehlungen.append('Redundanten Anschluss einplanen fuer N-1 Sicherheit.')
    if n1['bewertung'] == 'ROT' and n1.get('redundanz'):
        empfehlungen.append('Auch mit Redundanz kritisch: Netzverstaerkung erforderlich.')

    # NB-Check
    if nb_check and not nb_check['alle_erfuellt']:
        for p in nb_check['pruefungen']:
            if p['erfuellt'] is False:
                empfehlungen.append(f'NB-Kriterium nicht erfuellt: {p["kriterium"]} '
                                    f'(Grenzwert {p["grenzwert"]}, Ist {p["istwert"]})')

    # Datenqualität
    if dq['klasse'] in ('C', 'D'):
        empfehlungen.append(f'Datenqualitaet {dq["klasse"]}: Vor Antragstellung reale Netzdaten beim VNB anfordern.')

    if not empfehlungen:
        empfehlungen.append('Anschluss technisch plausibel. Standardverfahren beim Netzbetreiber einleiten.')

    return empfehlungen


# =============================================================================
# ERWEITERTE PROJEKT- / STAKEHOLDER-DIAGNOSE
# =============================================================================

def _safe_text(value, fallback=''):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def normalisiere_projektprofil(eingabe, p_mw):
    raw_components = eingabe.get('project_components') or []
    komponenten = []
    total_installed_kw = 0.0
    summary = []

    for item in raw_components:
        if not isinstance(item, dict):
            continue
        typ = _safe_text(item.get('component_type'), 'other')
        capacity_kw = max(0.0, float(item.get('capacity_kw') or 0))
        energy_kwh = _float_or_none(item.get('energy_kwh'))
        max_export_kw = max(0.0, float(item.get('max_export_kw') or 0))
        max_import_kw = max(0.0, float(item.get('max_import_kw') or 0))
        controllable = bool(item.get('controllable', False))
        label = _safe_text(item.get('label'), typ.upper())
        if capacity_kw <= 0:
            continue
        komponenten.append({
            'component_type': typ,
            'label': label,
            'capacity_kw': round(capacity_kw, 2),
            'energy_kwh': round(energy_kwh, 2) if energy_kwh is not None else None,
            'max_export_kw': round(max_export_kw, 2) if max_export_kw > 0 else None,
            'max_import_kw': round(max_import_kw, 2) if max_import_kw > 0 else None,
            'controllable': controllable,
        })
        total_installed_kw += capacity_kw
        text = f'{label}: {round(capacity_kw, 1)} kW'
        if energy_kwh is not None:
            text += f' / {round(energy_kwh, 1)} kWh'
        summary.append(text)

    if not komponenten:
        fallback_kw = round(max(0.0, float(p_mw)) * 1000, 2)
        fallback_type = _safe_text(eingabe.get('anlagentyp'), 'PV')
        komponenten = [{
            'component_type': fallback_type.lower(),
            'label': fallback_type,
            'capacity_kw': fallback_kw,
            'energy_kwh': None,
            'max_export_kw': fallback_kw,
            'max_import_kw': 0.0,
            'controllable': False,
        }]
        total_installed_kw = fallback_kw
        summary = [f'{fallback_type}: {round(fallback_kw, 1)} kW']

    nap = eingabe.get('netzanschlusspunkt') if isinstance(eingabe.get('netzanschlusspunkt'), dict) else {}
    max_export_kw = _float_or_none(nap.get('max_export_kw'))
    max_import_kw = _float_or_none(nap.get('max_import_kw'))
    if max_export_kw is None:
        exportfaehige_typen = {'pv', 'wind', 'battery', 'other'}
        max_export_kw = sum(
            float(c.get('max_export_kw') or c.get('capacity_kw') or 0)
            for c in komponenten
            if c.get('component_type') in exportfaehige_typen
        )
        if max_export_kw <= 0:
            max_export_kw = round(max(0.0, p_mw) * 1000, 2)
    if max_import_kw is None:
        max_import_kw = sum(float(c.get('max_import_kw') or 0) for c in komponenten if c.get('component_type') in ('battery', 'load', 'charging', 'electrolyzer', 'heat_pump'))

    is_hybrid = len({c['component_type'] for c in komponenten}) > 1
    if is_hybrid:
        text = (
            'Hybridprojekt erkannt. Entscheidend fuer die Bewertung ist die maximale Wirkung am Netzanschlusspunkt, '
            'nicht nur die Summe installierter Leistungen.'
        )
    else:
        text = 'Einzelprojektprofil ohne ausgepraegte Hybridkopplung.'

    return {
        'components': komponenten,
        'total_installed_kw': round(total_installed_kw, 2),
        'component_count': len(komponenten),
        'is_hybrid': is_hybrid,
        'component_summary': summary,
        'max_export_kw': round(max_export_kw or 0.0, 2),
        'max_import_kw': round(max_import_kw or 0.0, 2),
        'summary': text,
    }


def bewerte_speicherprofil(eingabe, projektprofil):
    storage = eingabe.get('storage_profile') if isinstance(eingabe.get('storage_profile'), dict) else {}
    components = projektprofil.get('components', [])
    battery_component = next((c for c in components if c.get('component_type') == 'battery'), None)
    relevant = bool(storage.get('has_storage')) or battery_component is not None
    mode = _safe_text(storage.get('operation_mode'), 'unknown')
    warnings = []
    benefit_flags = []
    score = 10

    if not relevant:
        return {
            'relevant': False,
            'operation_mode': 'unknown',
            'flexibility_score': 0,
            'grid_support_score': 0,
            'benefit_flags': [],
            'warnings': [],
            'summary': 'Kein Speicherprofil angegeben. Zusätzliche Flexibilitätsvorteile werden nicht unterstellt.',
            'disclaimer': 'Netzdienliche Effekte werden nur bewertet, wenn Speicherkonzept und Steuerbarkeit angegeben sind.',
        }

    power_kw = _float_or_none(storage.get('power_kw'))
    energy_kwh = _float_or_none(storage.get('energy_kwh'))
    if battery_component is not None:
        if power_kw is None:
            power_kw = float(battery_component.get('capacity_kw') or 0)
        if energy_kwh is None:
            energy_kwh = _float_or_none(battery_component.get('energy_kwh'))

    if power_kw:
        score += 20
    if energy_kwh:
        score += 10
    if storage.get('reactive_power_capable'):
        score += 15
        benefit_flags.append('Blindleistungsbereitstellung moeglich')
    if storage.get('remote_control_capable'):
        score += 15
        benefit_flags.append('Fernsteuerbarkeit angegeben')
    if storage.get('schedule_based_dispatch'):
        score += 10
        benefit_flags.append('Fahrplanbetrieb vorgesehen')
    if storage.get('dynamic_export_limit'):
        score += 10
        benefit_flags.append('Dynamische Einspeisebegrenzung vorgesehen')
    if storage.get('curtailment_ready'):
        score += 10
        benefit_flags.append('Abregelung / kuratives Verhalten vorgesehen')
    if storage.get('peak_shaving'):
        score += 5
        benefit_flags.append('Peak-Shaving / Lastmanagement moeglich')

    grid_support_bonus = {
        'grid_support': 25,
        'partial_grid_support': 15,
        'hybrid': 10,
        'market': 0,
        'unknown': 0,
    }.get(mode, 0)
    grid_support_score = _clamp_score(score + grid_support_bonus)

    if mode in ('market', 'unknown'):
        warnings.append('Speicherprofil ist nicht eindeutig netzdienlich beschrieben. Positive Effekte werden daher konservativ begrenzt.')
    if not storage.get('remote_control_capable'):
        warnings.append('Fernsteuerbarkeit nicht bestaetigt. Abstimmungsfaehigkeit mit dem VNB bleibt offen.')

    summary = (
        'Speicherprofil mit netzdienlichen Elementen erkannt.'
        if grid_support_score >= 60
        else 'Speicher vorhanden, aber netzdienliche Betriebsweise nur teilweise oder noch offen beschrieben.'
    )

    return {
        'relevant': True,
        'operation_mode': mode,
        'flexibility_score': _clamp_score(score),
        'grid_support_score': grid_support_score,
        'benefit_flags': benefit_flags,
        'warnings': warnings,
        'summary': summary,
        'disclaimer': (
            'Netzdienliche Speicher- oder Flexibilitaetskonzepte koennen die technische Bewertung und Abstimmungsfaehigkeit '
            'verbessern. Eine bevorzugte Behandlung ist daraus nicht ableitbar und haengt vom zustaendigen Netzbetreiber ab.'
        ),
    }


def bewerte_umwelt_trasse(eingabe):
    env = eingabe.get('environmental_route') if isinstance(eingabe.get('environmental_route'), dict) else {}
    drivers = []
    mitigation = [str(x) for x in env.get('mitigation_measures', []) if str(x).strip()]
    score = 85

    route_length = _float_or_none(env.get('route_length_km'))
    if route_length is not None:
        if route_length > 10:
            score -= 20
            drivers.append('Lange Trasse > 10 km')
        elif route_length > 3:
            score -= 10
            drivers.append('Mittlere Trassenlaenge > 3 km')

    crossings = env.get('crossings_count')
    if crossings is not None:
        try:
            crossings_int = int(crossings)
        except (TypeError, ValueError):
            crossings_int = 0
        if crossings_int >= 5:
            score -= 20
            drivers.append('Mehrere Querungen entlang der Trasse')
        elif crossings_int >= 2:
            score -= 10
            drivers.append('Einzelne Querungen entlang der Trasse')

    for flag, malus, text in (
        ('protected_area_touch', 20, 'Beruehrung von Schutzgebieten'),
        ('water_protection_area', 15, 'Wasserschutzthema moeglich'),
        ('forest_crossing', 10, 'Waldquerung moeglich'),
        ('third_party_land', 10, 'Drittrechte / Wegerechte relevant'),
        ('noise_sensitive_area', 5, 'Sensibles Umfeld entlang der Trasse'),
    ):
        if env.get(flag):
            score -= malus
            drivers.append(text)

    complexity = _safe_text(env.get('route_complexity'), 'unbekannt')
    if complexity == 'hoch':
        score -= 20
        drivers.append('Trassenkomplexitaet hoch')
    elif complexity == 'mittel':
        score -= 10
        drivers.append('Trassenkomplexitaet mittel')

    score = _clamp_score(score)
    if score >= 70:
        level = 'niedrig'
        summary = 'Umwelt- und Trassenrisiko im Pre-Check eher begrenzt.'
    elif score >= 45:
        level = 'mittel'
        summary = 'Umwelt- oder Trassenthemen sollten vor Antragstellung vertieft werden.'
    else:
        level = 'hoch'
        summary = 'Erhoehtes Umwelt-/Trassenrisiko. Diese Punkte koennen die Anschlussstrategie stark beeinflussen.'

    return {
        'risk_score': score,
        'risk_level': level,
        'drivers': drivers,
        'mitigation': mitigation,
        'summary': summary,
    }


def bewerte_stakeholder_konflikt(eingabe, projektprofil, speicher, umwelt, kosten):
    stakeholder = eingabe.get('stakeholder_context') if isinstance(eingabe.get('stakeholder_context'), dict) else {}
    nap = eingabe.get('netzanschlusspunkt') if isinstance(eingabe.get('netzanschlusspunkt'), dict) else {}
    priority_focus = _safe_text(stakeholder.get('priority_focus'), 'balanced')

    projektierer_score = 75
    netz_score = 55
    umsetzung_score = 70

    if projektprofil.get('is_hybrid'):
        netz_score += 10
        projektierer_score += 5
    if projektprofil.get('max_export_kw', 0) and projektprofil.get('total_installed_kw', 0):
        if projektprofil['max_export_kw'] < projektprofil['total_installed_kw'] * 0.8:
            netz_score += 10
            projektierer_score += 5
    if nap.get('own_transformer'):
        netz_score += 10
        umsetzung_score += 5
    if nap.get('own_substation'):
        netz_score += 15
        projektierer_score -= 5
    if speicher.get('grid_support_score', 0) >= 60:
        netz_score += 15
        projektierer_score += 5

    umwelt_level = umwelt.get('risk_level')
    if umwelt_level == 'hoch':
        projektierer_score -= 20
        umsetzung_score -= 25
    elif umwelt_level == 'mittel':
        projektierer_score -= 10
        umsetzung_score -= 10

    investition = float((kosten or {}).get('investition_gesamt_eur', 0))
    if investition >= 1_500_000:
        projektierer_score -= 15
    elif investition >= 500_000:
        projektierer_score -= 8

    if priority_focus == 'kosten':
        projektierer_score += 5
        netz_score -= 5
    elif priority_focus == 'netz':
        netz_score += 5
    elif priority_focus == 'genehmigung':
        umsetzung_score += 5
    elif priority_focus == 'zeit':
        umsetzung_score += 5

    netz_score = _clamp_score(netz_score)
    projektierer_score = _clamp_score(projektierer_score)
    umsetzung_score = _clamp_score(umsetzung_score)

    spread = max(netz_score, projektierer_score, umsetzung_score) - min(netz_score, projektierer_score, umsetzung_score)
    if spread >= 30:
        level = 'hoch'
    elif spread >= 15:
        level = 'mittel'
    else:
        level = 'niedrig'

    if level == 'hoch':
        summary = 'Deutlicher Zielkonflikt zwischen Netzsicht, Projektsicht und Umsetzbarkeit. Varianten- und Argumentationsstrategie frueh vorbereiten.'
    elif level == 'mittel':
        summary = 'Erkennbarer Zielkonflikt zwischen den Stakeholder-Perspektiven. Abstimmungsvorbereitung empfohlen.'
    else:
        summary = 'Stakeholder-Perspektiven liegen im Pre-Check noch relativ nah beieinander.'

    recommended_focus = (
        'Kosten- und Trassenargumentation gegenueber dem VNB strukturieren.'
        if projektierer_score < netz_score
        else 'Netz- und Betriebsrobustheit als Kernargument ausarbeiten.'
        if netz_score < projektierer_score
        else 'Ausgewogene Anschlussstrategie mit klaren Annahmen und Variantenhinweisen vorbereiten.'
    )

    return {
        'netzbetreiber_score': netz_score,
        'projektierer_score': projektierer_score,
        'umsetzung_score': umsetzung_score,
        'konflikt_level': level,
        'konflikt_summary': summary,
        'recommended_focus': recommended_focus,
    }


def erzeuge_transparenzblock(eingabe, dq, speicher, umwelt, stakeholder, n1):
    assumptions = [
        'Vorpruefung auf Basis des eingegebenen Projekt- und Anschlussprofils; keine verbindliche Netzanschlusszusage.',
        'Ohne verifizierte VNB-Daten werden Hybrid-, Speicher- und Trassenangaben konservativ als Annahmen behandelt.',
    ]
    disclaimers = [
        'Finale technische und regulatorische Bewertung liegt beim zustaendigen Netzbetreiber.',
        'Netzdienliche Speicher- oder Infrastrukturmassnahmen verbessern moeglicherweise die Abstimmungsfaehigkeit, begruenden aber keine Bevorzugung.',
        'Umwelt- und Trassenhinweise sind Pre-Check-Diagnosen und keine formale Genehmigungspruefung.',
    ]
    confidence_notes = [f'Datenqualitaet {dq.get("klasse", "D")}: {dq.get("text", "")}']

    if speicher.get('warnings'):
        confidence_notes.extend(speicher['warnings'])
    if umwelt.get('drivers'):
        confidence_notes.append('Wesentliche Umwelt-/Trassentreiber: ' + '; '.join(umwelt['drivers']))
    confidence_notes.append(stakeholder.get('konflikt_summary', ''))
    n1_klasse = _safe_text(n1.get('n1_klasse'))
    n1_konfidenz = n1.get('n1_konfidenz')
    if n1_klasse:
        if n1_konfidenz is None:
            confidence_notes.append(f'N-1-Screening als {n1_klasse} klassifiziert.')
        else:
            confidence_notes.append(f'N-1-Screening als {n1_klasse} klassifiziert (Konfidenz {n1_konfidenz}).')
    for annahme in (n1.get('detail_annahmen') or [])[:2]:
        confidence_notes.append(f'N-1-Annahme: {annahme}')
    confidence_notes.append(
        'Oberschwingungs-/THD-Bewertung: nicht berechnet (kein Lastflussmodell); bei Bedarf separate Rueckwirkungsstudie.'
    )

    if eingabe.get('project_components'):
        assumptions.append('Die maximale Einspeise-/Bezugswirkung am Netzanschlusspunkt wurde gegenueber der installierten Gesamtleistung bevorzugt bewertet.')
    if n1_klasse in ('N1-0', 'N1-1', 'N1-2'):
        assumptions.append(
            f'Die N-1-Aussage erreicht aktuell nur {n1_klasse}; fuer belastbare Reserveaussagen fehlen noch verifizierte Netz- oder Umspannwerksdaten.'
        )

    return {
        'assumptions': assumptions,
        'disclaimers': disclaimers,
        'confidence_notes': [note for note in confidence_notes if note],
    }


def erzeuge_erweiterte_scores(speicher, umwelt, stakeholder):
    stakeholder_fit = round((stakeholder['netzbetreiber_score'] + stakeholder['projektierer_score'] + stakeholder['umsetzung_score']) / 3)
    return {
        'netzdienlichkeit': int(speicher.get('grid_support_score', 0)),
        'projektfit': int(stakeholder.get('projektierer_score', 0)),
        'umwelt_trasse': int(umwelt.get('risk_score', 0)),
        'stakeholder_fit': int(stakeholder_fit),
    }


# =============================================================================
# FAZIT / ENTSCHEIDUNGSLOGIK (3 Ebenen)
# =============================================================================

def erzeuge_fazit(scores, harte_verstoesse):
    """
    3 Entscheidungsebenen:
    A = Anschluss grundsätzlich plausibel
    B = Anschluss bedingt plausibel
    C = Anschluss kritisch / nicht plausibel
    """
    if harte_verstoesse:
        return {
            'entscheidung': 'C',
            'text': 'KRITISCH: Netzanschluss in dieser Konfiguration nicht plausibel.',
            'detail': 'Harte Verstoesse: ' + '; '.join(harte_verstoesse),
            'farbe': 'ROT',
        }

    g = scores['gesamt']
    if g >= 70:
        return {
            'entscheidung': 'A',
            'text': 'PLAUSIBEL: Netzanschluss grundsaetzlich realisierbar.',
            'detail': f'Gesamtscore {g}/100. Standardverfahren beim VNB einleiten.',
            'farbe': 'GRUEN',
        }
    elif g >= 40:
        return {
            'entscheidung': 'B',
            'text': 'BEDINGT PLAUSIBEL: Netzanschluss mit Massnahmen moeglich.',
            'detail': f'Gesamtscore {g}/100. Massnahmen und Detailpruefung erforderlich.',
            'farbe': 'GELB',
        }
    else:
        return {
            'entscheidung': 'C',
            'text': 'KRITISCH: Netzanschluss in dieser Konfiguration nicht plausibel.',
            'detail': f'Gesamtscore {g}/100. Erhebliche Anpassungen oder alternatives Konzept noetig.',
            'farbe': 'ROT',
        }


# =============================================================================
# HAUPTFUNKTION
# =============================================================================

def berechne_netzanschluss(eingabe, dry_run=False, revision_context=None):
    # Validierung
    fehler, warnungen = validiere_eingabe(eingabe)
    if fehler:
        return {'status': 'FEHLER', 'fehler': fehler, 'warnungen': warnungen}

    # Grunddaten
    u_kv = float(eingabe['nennspannung'])
    p_mw = float(eingabe['leistung_mw'])
    leitungstyp = eingabe['leitungstyp']
    cable_info = estimate_cable_length_km(eingabe)
    entfernung_km = float(cable_info['entfernung_km'])
    eingabe['entfernung_km'] = entfernung_km
    cos_phi_info = resolve_cos_phi_for_calculation(eingabe)
    cos_phi = float(cos_phi_info['cos_phi'])
    eingabe['cos_phi'] = cos_phi
    redundanz = eingabe.get('redundanz', False)
    parallele_systeme = int(eingabe.get('parallele_systeme', 1))
    anschlussart = eingabe['anschlussart']
    topologie = eingabe.get('topologie', 'unbekannt')
    temperatur_c = _float_or(eingabe.get('temperatur_c'), 20)
    bestehende_einspeisung_mw = _float_or(eingabe.get('bestehende_einspeisung_mw'), 0)
    projektprofil = normalisiere_projektprofil(eingabe, p_mw)

    spannungsebene = bestimme_spannungsebene(u_kv)

    # P-Q-S Modell am wirksamen Netzleistungspunkt (inkl. bestehender Einspeisung)
    p_mw_wirksam = berechne_wirksame_leistung(p_mw, bestehende_einspeisung_mw, anschlussart)
    pqs = berechne_pqs(p_mw_wirksam, cos_phi)

    # Impedanzmodell
    sk_user = _float_or_none(eingabe.get('sk_mva'))
    sk_mva = _float_or(sk_user, SK_DEFAULT[spannungsebene])
    rx_ratio = _float_or(eingabe.get('rx_ratio'), RX_RATIO_DEFAULT[spannungsebene])
    trafo_s_mva = _float_or(eingabe.get('trafo_s_mva'), TRAFO_DEFAULTS[spannungsebene]['s_mva'])
    trafo_uk = _float_or(
        eingabe.get('trafo_uk_prozent', eingabe.get('uk_prozent')),
        TRAFO_DEFAULTS[spannungsebene]['uk_prozent'],
    )
    bestand_trafo_proz = _float_or(
        eingabe.get('bestand_trafo_auslastung', eingabe.get('bestand_auslastung_prozent')),
        0,
    )

    r_q, x_q = berechne_quellenimpedanz(u_kv, sk_mva, rx_ratio)
    r_t, x_t = berechne_trafoimpedanz(u_kv, trafo_s_mva, trafo_uk)
    r_l, x_l = berechne_leitungsimpedanz(leitungstyp, entfernung_km, parallele_systeme, temperatur_c)
    r_ges, x_ges, z_ges = berechne_gesamtimpedanz(r_q, x_q, r_t, x_t, r_l, x_l)

    # Berechnungen
    thermisch = berechne_thermisch(pqs['s_mva'], u_kv, leitungstyp, parallele_systeme)
    trafo = berechne_trafo(pqs['s_mva'], trafo_s_mva, bestand_trafo_proz)
    spannung = berechne_spannung(pqs['p_mw'], pqs['q_mvar'], u_kv, r_ges, x_ges, anschlussart)
    kurzschluss = berechne_kurzschluss(u_kv, z_ges, pqs['s_mva'], sk_mva)
    ik_info = get_max_short_circuit_current_ka(
        spannungsebene,
        sk_mva_user=sk_user,
        ik_berechnet_ka=kurzschluss.get('ik_max_ka'),
    )
    kurzschluss['ik_referenz_ka'] = ik_info['ik_referenz_ka']
    kurzschluss['ik_band_min_ka'] = ik_info['ik_band_min_ka']
    kurzschluss['ik_band_max_ka'] = ik_info['ik_band_max_ka']
    kurzschluss['ik_vorlaeufig'] = ik_info['vorlaeufig']
    kurzschluss['ik_hinweis'] = ik_info['hinweis']
    n1 = berechne_n1_prescreen(thermisch, trafo, topologie, parallele_systeme, redundanz, pqs=pqs, cos_phi=cos_phi, eingabe=eingabe)
    datenqualitaet = berechne_datenqualitaet(eingabe)

    # Szenarien
    szenarien = berechne_szenarien(
        pqs['p_mw'], pqs['q_mvar'], pqs['s_mva'], u_kv,
        r_ges, x_ges, leitungstyp, parallele_systeme,
        anschlussart, sk_mva, z_ges, trafo_s_mva, bestand_trafo_proz
    )

    # N-1 Detailanalyse (aus Szenario "N-1 Stoerungsfall")
    n1_szenario = next((s for s in szenarien if s.get('name') == 'N-1 Stoerungsfall'), None)
    if n1_szenario:
        n1_analyse = analysiere_n1(
            eingabe=eingabe,
            thermisch_n1=n1_szenario.get('thermisch', {}),
            spannung_n1=n1_szenario.get('spannung', {}),
            zusatzlast_mw=p_mw_wirksam,
        )
    else:
        n1_analyse = {'status': 'NICHT_BEWERTET', 'text': 'Kein N-1 Szenario verfuegbar.'}
    n1 = konsolidiere_n1_ergebnis(n1, n1_analyse)
    n1['mvp_dokumentation'] = n1_mvp_dokumentation(eingabe, n1.get('n1_klasse'))

    # Scores
    scores = berechne_scores(thermisch, spannung, kurzschluss, n1, datenqualitaet, trafo)
    fazit = erzeuge_fazit(scores, scores['harte_verstoesse'])

    # Kosten & Wirtschaftlichkeit
    kosten = berechne_kosten(eingabe, spannungsebene, entfernung_km, parallele_systeme, p_mw=p_mw)
    wirtschaftlichkeit = berechne_wirtschaftlichkeit(eingabe, kosten, p_mw)
    speicher_bewertung = bewerte_speicherprofil(eingabe, projektprofil)
    route_environment = bewerte_umwelt_trasse(eingabe)
    stakeholder_bewertung = bewerte_stakeholder_konflikt(
        eingabe, projektprofil, speicher_bewertung, route_environment, kosten
    )
    transparenz = erzeuge_transparenzblock(
        eingabe, datenqualitaet, speicher_bewertung, route_environment, stakeholder_bewertung, n1
    )
    erweiterte_scores = erzeuge_erweiterte_scores(
        speicher_bewertung, route_environment, stakeholder_bewertung
    )

    # NB-Check
    nb_check = pruefe_nb_schwellenwerte(eingabe, thermisch, spannung, kurzschluss)

    # Empfehlungen
    empfehlungen = erzeuge_empfehlungen(thermisch, spannung, kurzschluss, n1, trafo,
                                         nb_check, datenqualitaet, pqs, eingabe)
    for empfehlung in n1.get('detail_empfehlungen', []):
        _append_unique_text(empfehlungen, empfehlung)
    if projektprofil.get('is_hybrid'):
        _append_unique_text(empfehlungen, 'Hybridkonzept mit fixer oder dynamischer Begrenzung am Netzanschlusspunkt dokumentieren.')
    if speicher_bewertung.get('relevant'):
        _append_unique_text(empfehlungen, speicher_bewertung['disclaimer'])
    if route_environment.get('risk_level') in ('mittel', 'hoch'):
        _append_unique_text(empfehlungen, 'Trassen- und Umweltannahmen vor offiziellem Antrag mit einer Vorpruefung absichern.')
    if n1.get('engpass_komponente') not in (None, 'keine') and n1.get('bewertung') in ('GELB', 'ORANGE', 'ROT'):
        _append_unique_text(
            empfehlungen,
            f"N-1-Engpass {n1['engpass_komponente']} gezielt mit dem Netzbetreiber verifizieren und absichern.",
        )
    _append_unique_text(empfehlungen, stakeholder_bewertung['recommended_focus'])

    warnungen.extend(speicher_bewertung.get('warnings', []))
    warnungen.extend(
        erzeuge_blindleistung_trafo_warnungen(eingabe, trafo, pqs, leitungstyp=leitungstyp)
    )
    if cable_info.get('heuristisch'):
        _append_unique_text(warnungen, cable_info['annahme'])
    if cos_phi_info.get('quelle') == 'rolle_default':
        _append_unique_text(warnungen, cos_phi_info['annahme'])
    if ik_info.get('vorlaeufig'):
        _append_unique_text(warnungen, ik_info['hinweis'])
    mvp_doc = n1.get('mvp_dokumentation') or {}
    if mvp_doc.get('hinweis'):
        _append_unique_text(warnungen, mvp_doc['hinweis'])
    if stakeholder_bewertung.get('konflikt_level') == 'hoch':
        _append_unique_text(warnungen, 'Hoher Stakeholder-Zielkonflikt zwischen Netzsicht, Projektsicht und Umsetzbarkeit.')
    if route_environment.get('risk_level') == 'hoch':
        _append_unique_text(warnungen, 'Erhoehtes Umwelt-/Trassenrisiko kann die Anschlussstrategie dominieren.')
    if n1.get('n1_klasse') in ('N1-0', 'N1-1', 'N1-2'):
        _append_unique_text(
            warnungen,
            f"N-1-Aussage aktuell nur als {n1['n1_klasse']} klassifiziert; fuer belastbare Reserveaussagen sind verifizierte Netz- oder Umspannwerksdaten noetig.",
        )

    result = {
        'status': 'OK',
        'eingabe': eingabe,
        'warnungen': warnungen,
        'annahmen': {
            'leistung_mw_neuanlage': round(p_mw, 4),
            'bestehende_einspeisung_mw': round(bestehende_einspeisung_mw, 4),
            'leistung_mw_wirksam': round(p_mw_wirksam, 4),
            'entfernung_km': entfernung_km,
            'entfernung_heuristisch': cable_info.get('heuristisch', False),
            'cos_phi': cos_phi,
            'cos_phi_quelle': cos_phi_info.get('quelle'),
        },
        'technical_details': erzeuge_technische_details(
            eingabe,
            spannung=spannung,
            kurzschluss=kurzschluss,
            leitungstyp=leitungstyp,
            leitung_meta=LEITUNGSDATEN.get(leitungstyp),
            cos_phi_info=cos_phi_info,
            cable_info=cable_info,
            ik_info=ik_info,
        ),
        'power_limit_hints': power_limit_hints(spannungsebene, p_mw * 1000),
        'pqs': pqs,
        'impedanz': {
            'r_q': round(r_q, 5), 'x_q': round(x_q, 5),
            'r_t': round(r_t, 5), 'x_t': round(x_t, 5),
            'r_l': round(r_l, 5), 'x_l': round(x_l, 5),
            'r_ges': round(r_ges, 5), 'x_ges': round(x_ges, 5),
            'z_ges': round(z_ges, 5),
        },
        'thermisch': thermisch,
        'trafo': trafo,
        'spannung': spannung,
        'kurzschluss': kurzschluss,
        'n1': n1,
        'n1_analyse': n1_analyse,
        'szenarien': szenarien,
        'scores': scores,
        'fazit': fazit,
        'kosten': kosten,
        'wirtschaftlichkeit': wirtschaftlichkeit,
        'nb_check': nb_check,
        'datenqualitaet': datenqualitaet,
        'empfehlungen': empfehlungen,
        'projektprofil': projektprofil,
        'speicher_bewertung': speicher_bewertung,
        'route_environment': route_environment,
        'stakeholder_bewertung': stakeholder_bewertung,
        'erweiterte_scores': erweiterte_scores,
        'transparenz': transparenz,
        'disclaimer': transparenz['disclaimers'],
        'engine_version': ENGINE_VERSION,
        'norm_version': _norm_version_label(u_kv),
        'norm_registry_stand': APP_VERSION_NORMSTAND,
    }
    try:
        from engine.grid_calculation_v2 import calculate_grid_connection_from_engine

        result['grid_calculation_v2'] = calculate_grid_connection_from_engine(eingabe)
    except Exception as exc:
        result['grid_calculation_v2'] = {
            'status': 'FEHLER',
            'message': 'Grid-Berechnung v2 konnte nicht ausgefuehrt werden.',
            'detail': str(exc),
        }
    ctx = revision_context if isinstance(revision_context, dict) else {}
    try:
        rev = speichere_revision(
            result,
            dry_run=dry_run,
            actor_user_id=ctx.get("actor_user_id"),
            action_type=ctx.get("action_type") or "ANALYSIS_COMPLETED",
            project_id=ctx.get("project_id"),
            db=ctx.get("db"),
        )
        result['revision'] = rev
    except Exception as e:
        result['revision'] = {'fehler': str(e), 'dry_run': dry_run}
    return result

