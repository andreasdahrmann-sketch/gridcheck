from engine.n1_ms import bewerte_n1_ms
from engine.revision import speichere_revision

ENGINE_VERSION = "1.2.0"
import math
from typing import Optional

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

# Typische R/X-VerhÃ¤ltnisse Vorgelagertes Netz
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

# Referenzkosten fÃ¼r KostenschÃ¤tzung
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


def berechne_betriebsstrom(s_mva, u_kv):
    """I = S / (sqrt(3) * U) - immer S-basiert"""
    u_v = u_kv * 1000.0
    s_va = s_mva * 1e6
    return s_va / (math.sqrt(3) * u_v)


# =============================================================================
# IMPEDANZMODELL: Quelle + Trafo + Leitung
# =============================================================================

def berechne_quellenimpedanz(u_kv, sk_mva, rx_ratio):
    """Z_Q = UÂ² / S_k, aufgeteilt in R_Q und X_Q"""
    u_v = u_kv * 1000.0
    z_q = (u_v ** 2) / (sk_mva * 1e6)
    r_q = z_q / math.sqrt(1 + rx_ratio ** 2)
    x_q = r_q * rx_ratio
    return r_q, x_q


def berechne_trafoimpedanz(u_kv, s_trafo_mva, uk_prozent):
    """Z_T = (uk/100) * UÂ² / S_T"""
    u_v = u_kv * 1000.0
    z_t = (uk_prozent / 100.0) * (u_v ** 2) / (s_trafo_mva * 1e6)
    # Vereinfachung: R_T << X_T, daher X_T Ëœ Z_T
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
            warnungen.append('cos phi = 1.0 bei aktiver Blindleistungsregelung ist widersprÃ¼chlich.')
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
    """Thermische PrÃ¼fung: I_betrieb vs I_zul â€” immer auf S-Basis"""
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
        'hinweis_verlegeart': 'Thermische Bewertung basiert auf konservativer Standardannahme (Erdverlegung, 20Â°C).',
    }


# =============================================================================
# TRAFO-AUSLASTUNG (S-basiert)
# =============================================================================

def berechne_trafo(s_mva, trafo_s_mva, bestand_auslastung_prozent=0):
    """Trafo-Auslastung auf S-Basis mit BestandsberÃ¼cksichtigung"""
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
    Signierte SpannungsÃ¤nderung: ?u Ëœ (R*P + X*Q) / UÂ²
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
    # Vereinfachte Formel: delta_u Ëœ (R*P + X*Q) / UÂ²
    delta_u_v_approx = vorzeichen * (r_ges * p_w + x_ges * q_var) / u_v
    delta_u_proz = (abs(delta_u_v_approx) / u_v) * 100.0

    ebene = bestimme_spannungsebene(u_kv)

    # Ampellogik nach Netzplaner-Vorgabe
    if delta_u_proz <= 2.0:
        bewertung, text = 'GRUEN', f'Spannungs{richtung.lower()} unkritisch.'
    elif delta_u_proz <= 3.0:
        bewertung, text = 'GELB', f'Spannungs{richtung.lower()} akzeptabel, Reserve eingeschraenkt.'
    elif delta_u_proz <= 5.0:
        bewertung, text = 'ORANGE', f'Spannungs{richtung.lower()} grenzwertig.'
    else:
        bewertung, text = 'ROT', f'Spannungs{richtung.lower()} ueberschreitet zulaessigen Bereich!'

    return {
        'delta_u_prozent': round(delta_u_proz, 3),
        'delta_u_v': round(abs(delta_u_v_approx), 1),
        'richtung': richtung,
        'vorzeichen': 'positiv' if vorzeichen > 0 else 'negativ',
        'spannungsebene': ebene,
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
    Kurzschluss-Screening: Ik'', Sk/Sn, NetzrÃ¼ckwirkungs-Screening
    """
    u_v = u_kv * 1000.0
    c = 1.1  # Spannungsfaktor nach IEC 60909

    # Ik'' = c * U / (sqrt(3) * |Z_ges|)
    ik_max = (c * u_v) / (math.sqrt(3) * z_ges) if z_ges > 0 else 0
    ik_min = (0.95 * u_v) / (math.sqrt(3) * z_ges) if z_ges > 0 else 0  # c_min Ëœ 0.95

    # Sk/Sn VerhÃ¤ltnis
    sk_sn = sk_mva / s_mva if s_mva > 0 else 999

    # NetzrÃ¼ckwirkungs-Screening: S_anlage/S_k
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

    # NetzrÃ¼ckwirkung
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


# =============================================================================
# SZENARIOANALYSE
# =============================================================================

def berechne_szenarien(p_mw, q_mvar, s_mva, u_kv, r_ges, x_ges, leitungstyp,
                       parallele_systeme, anschlussart, sk_mva, z_ges,
                       trafo_s_mva, bestand_trafo_proz):
    """4 Pflichtszenarien gemÃ¤ss Netzplaner-Vorgabe"""
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
        'Volle Leistung, minimale Netzlast â€” kritischster Fall fuer Spannungsanhebung.'
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
        'Teillastbetrieb bei 40% â€” fuer Normalbetriebsbewertung.'
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
    if spannung['delta_u_prozent'] > 5.0:
        harte_verstoesse.append('Spannungsaenderung > 5%')

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
        or spannung['delta_u_prozent'] > 5.0
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

def berechne_kosten(eingabe, spannungsebene, entfernung_km, parallele_systeme):
    ref = REFERENZKOSTEN[spannungsebene]
    entfernung_m = entfernung_km * 1000

    tiefbau_m = _float_or(eingabe.get('kosten_tiefbau_eur_m'), ref['tiefbau_eur_m'])
    kabel_m = _float_or(eingabe.get('kosten_kabel_eur_m'), ref['kabel_eur_m'])
    trafo = _float_or(eingabe.get('kosten_trafostation_eur'), ref['trafostation_eur'])
    schaltanlage = _float_or(eingabe.get('kosten_schaltanlage_eur'), ref['schaltanlage_eur'])
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

    return {
        'kosten_trasse_eur': round(kosten_trasse),
        'kosten_station_eur': round(kosten_station),
        'kosten_genehmigung_eur': round(kosten_genehm),
        'kosten_planung_eur': round(kosten_planung),
        'kosten_bkz_eur': round(bkz),
        'investition_gesamt_eur': round(investition_gesamt),
        'betriebskosten_pa_eur': round(betriebskosten_pa),
        'konfidenz_prozent': round(konfidenz),
        'quelle': 'Eigene + Referenz' if eigene_count > 0 else 'Referenzwerte',
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

    # DatenqualitÃ¤t
    if dq['klasse'] in ('C', 'D'):
        empfehlungen.append(f'Datenqualitaet {dq["klasse"]}: Vor Antragstellung reale Netzdaten beim VNB anfordern.')

    if not empfehlungen:
        empfehlungen.append('Anschluss technisch plausibel. Standardverfahren beim Netzbetreiber einleiten.')

    return empfehlungen


# =============================================================================
# FAZIT / ENTSCHEIDUNGSLOGIK (3 Ebenen)
# =============================================================================

def erzeuge_fazit(scores, harte_verstoesse):
    """
    3 Entscheidungsebenen:
    A = Anschluss grundsÃ¤tzlich plausibel
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

def berechne_netzanschluss(eingabe, dry_run=False):
    # Validierung
    fehler, warnungen = validiere_eingabe(eingabe)
    if fehler:
        return {'status': 'FEHLER', 'fehler': fehler, 'warnungen': warnungen}

    # Grunddaten
    u_kv = float(eingabe['nennspannung'])
    p_mw = float(eingabe['leistung_mw'])
    leitungstyp = eingabe['leitungstyp']
    entfernung_km = float(eingabe['entfernung_km'])
    cos_phi = float(eingabe.get('cos_phi', 0.95))
    redundanz = eingabe.get('redundanz', False)
    parallele_systeme = int(eingabe.get('parallele_systeme', 1))
    anschlussart = eingabe['anschlussart']
    topologie = eingabe.get('topologie', 'unbekannt')
    temperatur_c = _float_or(eingabe.get('temperatur_c'), 20)

    spannungsebene = bestimme_spannungsebene(u_kv)

    # P-Q-S Modell
    pqs = berechne_pqs(p_mw, cos_phi)

    # Impedanzmodell
    sk_mva = _float_or(eingabe.get('sk_mva'), SK_DEFAULT[spannungsebene])
    rx_ratio = _float_or(eingabe.get('rx_ratio'), RX_RATIO_DEFAULT[spannungsebene])
    trafo_s_mva = _float_or(eingabe.get('trafo_s_mva'), TRAFO_DEFAULTS[spannungsebene]['s_mva'])
    trafo_uk = _float_or(eingabe.get('trafo_uk_prozent'), TRAFO_DEFAULTS[spannungsebene]['uk_prozent'])
    bestand_trafo_proz = _float_or(eingabe.get('bestand_trafo_auslastung'), 0)

    r_q, x_q = berechne_quellenimpedanz(u_kv, sk_mva, rx_ratio)
    r_t, x_t = berechne_trafoimpedanz(u_kv, trafo_s_mva, trafo_uk)
    r_l, x_l = berechne_leitungsimpedanz(leitungstyp, entfernung_km, parallele_systeme, temperatur_c)
    r_ges, x_ges, z_ges = berechne_gesamtimpedanz(r_q, x_q, r_t, x_t, r_l, x_l)

    # Berechnungen
    thermisch = berechne_thermisch(pqs['s_mva'], u_kv, leitungstyp, parallele_systeme)
    trafo = berechne_trafo(pqs['s_mva'], trafo_s_mva, bestand_trafo_proz)
    spannung = berechne_spannung(pqs['p_mw'], pqs['q_mvar'], u_kv, r_ges, x_ges, anschlussart)
    kurzschluss = berechne_kurzschluss(u_kv, z_ges, pqs['s_mva'], sk_mva)
    n1 = berechne_n1_prescreen(thermisch, trafo, topologie, parallele_systeme, redundanz, pqs=pqs, cos_phi=cos_phi, eingabe=eingabe)
    datenqualitaet = berechne_datenqualitaet(eingabe)

    # Szenarien
    szenarien = berechne_szenarien(
        pqs['p_mw'], pqs['q_mvar'], pqs['s_mva'], u_kv,
        r_ges, x_ges, leitungstyp, parallele_systeme,
        anschlussart, sk_mva, z_ges, trafo_s_mva, bestand_trafo_proz
    )

    # Scores
    scores = berechne_scores(thermisch, spannung, kurzschluss, n1, datenqualitaet, trafo)
    fazit = erzeuge_fazit(scores, scores['harte_verstoesse'])

    # Kosten & Wirtschaftlichkeit
    kosten = berechne_kosten(eingabe, spannungsebene, entfernung_km, parallele_systeme)
    wirtschaftlichkeit = berechne_wirtschaftlichkeit(eingabe, kosten, p_mw)

    # NB-Check
    nb_check = pruefe_nb_schwellenwerte(eingabe, thermisch, spannung, kurzschluss)

    # Empfehlungen
    empfehlungen = erzeuge_empfehlungen(thermisch, spannung, kurzschluss, n1, trafo,
                                         nb_check, datenqualitaet, pqs, eingabe)

    result = {
        'status': 'OK',
        'eingabe': eingabe,
        'warnungen': warnungen,
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
        'szenarien': szenarien,
        'scores': scores,
        'fazit': fazit,
        'kosten': kosten,
        'wirtschaftlichkeit': wirtschaftlichkeit,
        'nb_check': nb_check,
        'datenqualitaet': datenqualitaet,
        'empfehlungen': empfehlungen,
        'engine_version': ENGINE_VERSION,
    }
    try:
        rev = speichere_revision(result, dry_run=dry_run)
        result['revision'] = rev
    except Exception as e:
        result['revision'] = {'fehler': str(e), 'dry_run': dry_run}
    return result

