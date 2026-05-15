import math

LEITUNGSDATEN = {
    'NAYY150': (270, 0.206, 0.080),
    'NAYY185': (310, 0.164, 0.080),
    'NAY2Y150': (270, 0.206, 0.080),
    'NA2XS2Y110': (355, 0.164, 0.113),
    'NA2XS2Y150': (410, 0.124, 0.110),
    'NA2XS2Y185': (455, 0.099, 0.108),
    'NA2XS2Y240': (530, 0.077, 0.105),
    'AL240': (645, 0.120, 0.390),
    'AL_STAHL240': (645, 0.120, 0.390),
    'ACSR240': (645, 0.120, 0.390),
}

GRENZWERTE_SPANNUNG = {
    'NS': 3.0,
    'MS': 2.0,
    'HS': 1.0,
}


def bestimme_spannungsebene(u_kv):
    if u_kv >= 60:
        return 'HS'
    elif u_kv >= 1:
        return 'MS'
    else:
        return 'NS'


def validiere_eingabe(eingabe):
    fehler = []
    pflichtfelder = ['nennspannung', 'leistung_mw', 'leitungstyp', 'entfernung_km', 'anschlussart']
    for feld in pflichtfelder:
        if feld not in eingabe:
            fehler.append(f'Pflichtfeld fehlt: {feld}')

    if not fehler:
        try:
            u = float(eingabe['nennspannung'])
            if u <= 0 or u > 380:
                fehler.append(f'Nennspannung unrealistisch: {u} kV')
        except (ValueError, TypeError):
            fehler.append('Nennspannung ist keine gueltige Zahl')

        try:
            p = float(eingabe['leistung_mw'])
            if p <= 0 or p > 2000:
                fehler.append(f'Leistung unrealistisch: {p} MW')
        except (ValueError, TypeError):
            fehler.append('Leistung ist keine gueltige Zahl')

        try:
            d = float(eingabe['entfernung_km'])
            if d <= 0 or d > 500:
                fehler.append(f'Entfernung unrealistisch: {d} km')
        except (ValueError, TypeError):
            fehler.append('Entfernung ist keine gueltige Zahl')

        lt = eingabe.get('leitungstyp', '')
        if lt not in LEITUNGSDATEN:
            fehler.append(f'Unbekannter Leitungstyp: {lt}. Verfuegbar: {", ".join(LEITUNGSDATEN.keys())}')

        aa = eingabe.get('anschlussart', '')
        if aa not in ('Einspeisung', 'Entnahme', 'Speicher'):
            fehler.append(f'Anschlussart ungueltig: {aa}. Erlaubt: Einspeisung, Entnahme, Speicher')

        try:
            ps = int(eingabe.get('parallele_systeme', 1))
            if ps < 1 or ps > 6:
                fehler.append(f'Parallele Systeme unrealistisch: {ps}. Erlaubt: 1-6')
        except (ValueError, TypeError):
            fehler.append('Parallele Systeme ist keine gueltige Zahl')

    return fehler


def berechne_thermisch(u_kv, p_mw, leitungstyp, cos_phi=0.95, parallele_systeme=1):
    u_v = u_kv * 1000.0
    p_w = p_mw * 1e6
    i_max, r_km, x_km = LEITUNGSDATEN[leitungstyp]

    # Gesamtstrom auf parallele Systeme aufteilen
    i_gesamt = p_w / (math.sqrt(3) * u_v * cos_phi)
    i_pro_system = i_gesamt / parallele_systeme
    auslastung = (i_pro_system / i_max) * 100.0

    if auslastung <= 60:
        bewertung = 'GRUEN'
        text = 'Thermisch unkritisch. Genuegend Reserve vorhanden.'
    elif auslastung <= 80:
        bewertung = 'GELB'
        text = 'Thermisch akzeptabel. Reserve eingeschraenkt.'
    elif auslastung <= 100:
        bewertung = 'ORANGE'
        text = 'Thermisch grenzwertig. Kaum Reserve fuer N-1.'
    else:
        bewertung = 'ROT'
        text = 'Thermische Ueberlastung! Leitung nicht ausreichend dimensioniert.'

    return {
        'i_betrieb_gesamt_a': round(i_gesamt, 1),
        'i_pro_system_a': round(i_pro_system, 1),
        'i_max_a': i_max,
        'auslastung_prozent': round(auslastung, 1),
        'parallele_systeme': parallele_systeme,
        'bewertung': bewertung,
        'text': text,
    }


def berechne_spannung(u_kv, p_mw, leitungstyp, entfernung_km, cos_phi=0.95, parallele_systeme=1):
    u_v = u_kv * 1000.0
    p_w = p_mw * 1e6
    i_max, r_km, x_km = LEITUNGSDATEN[leitungstyp]

    # Bei parallelen Systemen: Impedanz reduziert sich (Parallelschaltung)
    r_gesamt = (r_km * entfernung_km) / parallele_systeme
    x_gesamt = (x_km * entfernung_km) / parallele_systeme

    i_gesamt = p_w / (math.sqrt(3) * u_v * cos_phi)
    sin_phi = math.sqrt(1 - cos_phi ** 2)

    delta_u_v = math.sqrt(3) * i_gesamt * (r_gesamt * cos_phi + x_gesamt * sin_phi)
    delta_u_proz = (delta_u_v / u_v) * 100.0

    ebene = bestimme_spannungsebene(u_kv)
    grenzwert = GRENZWERTE_SPANNUNG[ebene]

    if delta_u_proz <= grenzwert * 0.6:
        bewertung = 'GRUEN'
        text = 'Spannungsfall unkritisch.'
    elif delta_u_proz <= grenzwert * 0.85:
        bewertung = 'GELB'
        text = 'Spannungsfall akzeptabel, aber eingeschraenkte Reserve.'
    elif delta_u_proz <= grenzwert:
        bewertung = 'ORANGE'
        text = 'Spannungsfall grenzwertig. Grenzwert fast erreicht.'
    else:
        bewertung = 'ROT'
        text = f'Spannungsfall ueberschreitet Grenzwert ({grenzwert}%)!'

    return {
        'delta_u_prozent': round(delta_u_proz, 2),
        'delta_u_v': round(delta_u_v, 1),
        'grenzwert_prozent': grenzwert,
        'spannungsebene': ebene,
        'parallele_systeme': parallele_systeme,
        'bewertung': bewertung,
        'text': text,
    }


def berechne_n1(thermisch, spannung, redundanz=False):
    parallele = thermisch['parallele_systeme']

    if parallele >= 2:
        # N-1: ein System faellt aus, Rest traegt die Last
        n1_auslastung = thermisch['auslastung_prozent'] * parallele / (parallele - 1)
        n1_sicher = n1_auslastung <= 100
        n1_redundanz = True
    elif redundanz:
        # Redundanz-Flag aber nur 1 System = 2. System als Reserve
        n1_auslastung = thermisch['auslastung_prozent']
        n1_sicher = n1_auslastung <= 100
        n1_redundanz = True
    else:
        n1_auslastung = thermisch['auslastung_prozent']
        n1_sicher = False
        n1_redundanz = False

    if n1_sicher:
        if n1_auslastung <= 80:
            bewertung = 'GRUEN'
            text = 'N-1 sicher mit ausreichend Reserve.'
        else:
            bewertung = 'GELB'
            text = 'N-1 sicher, aber eingeschraenkte Reserve.'
    else:
        if n1_redundanz:
            bewertung = 'ROT'
            text = 'Trotz Redundanz: N-1 fuehrt zu Ueberlastung!'
        else:
            bewertung = 'ROT'
            text = 'Kein redundanter Pfad. N-1 nicht erfuellt.'

    return {
        'n1_sicher': n1_sicher,
        'n1_auslastung_prozent': round(n1_auslastung, 1),
        'redundanz': n1_redundanz,
        'parallele_systeme': parallele,
        'bewertung': bewertung,
        'text': text,
    }


def erzeuge_empfehlungen(thermisch, spannung, n1):
    empfehlungen = []

    if thermisch['bewertung'] in ('ORANGE', 'ROT'):
        empfehlungen.append('Leitung hoeher dimensionieren oder zusaetzliches paralleles System einplanen.')
    if thermisch['bewertung'] == 'ROT':
        empfehlungen.append('Naechsthoehere Spannungsebene pruefen.')

    if spannung['bewertung'] == 'ROT':
        empfehlungen.append('Anschlusspunkt naeher am Umspannwerk waehlen oder Spannungsregelung vorsehen.')
    if spannung['bewertung'] in ('GELB', 'ROT'):
        empfehlungen.append('Blindleistungskompensation pruefen (cos phi optimieren).')

    if not n1['n1_sicher']:
        empfehlungen.append('Redundanten Anschluss (zweiter Einspeisestrang) einplanen fuer N-1 Sicherheit.')
    if n1['bewertung'] == 'ROT' and n1['redundanz']:
        empfehlungen.append('Auch mit Redundanz kritisch: Netzverstaerkung erforderlich.')

    if not empfehlungen:
        empfehlungen.append('Anschluss technisch machbar. Standardverfahren beim Netzbetreiber einleiten.')

    return empfehlungen


def erzeuge_fazit(thermisch, spannung, n1):
    bewertungen = [thermisch['bewertung'], spannung['bewertung'], n1['bewertung']]

    if 'ROT' in bewertungen:
        return 'KRITISCH: Netzanschluss in dieser Konfiguration nicht realisierbar. Anpassungen zwingend erforderlich.'
    elif 'ORANGE' in bewertungen:
        return 'EINGESCHRAENKT: Netzanschluss moeglich, aber Detailpruefung und Massnahmen erforderlich.'
    elif 'GELB' in bewertungen:
        return 'MACHBAR MIT AUFLAGEN: Netzanschluss realisierbar, einzelne Punkte beachten.'
    else:
        return 'MACHBAR: Netzanschluss technisch problemlos realisierbar.'


def berechne_netzanschluss(eingabe):
    fehler = validiere_eingabe(eingabe)
    if fehler:
        return {'status': 'FEHLER', 'fehler': fehler}

    u_kv = float(eingabe['nennspannung'])
    p_mw = float(eingabe['leistung_mw'])
    leitungstyp = eingabe['leitungstyp']
    entfernung_km = float(eingabe['entfernung_km'])
    cos_phi = float(eingabe.get('cos_phi', 0.95))
    redundanz = eingabe.get('redundanz', False)
    parallele_systeme = int(eingabe.get('parallele_systeme', 1))

    thermisch = berechne_thermisch(u_kv, p_mw, leitungstyp, cos_phi, parallele_systeme)
    spannung = berechne_spannung(u_kv, p_mw, leitungstyp, entfernung_km, cos_phi, parallele_systeme)
    n1 = berechne_n1(thermisch, spannung, redundanz)
    empfehlungen = erzeuge_empfehlungen(thermisch, spannung, n1)
    fazit = erzeuge_fazit(thermisch, spannung, n1)

    return {
        'status': 'OK',
        'eingabe': eingabe,
        'thermisch': thermisch,
        'spannung': spannung,
        'n1': n1,
        'empfehlungen': empfehlungen,
        'fazit': fazit,
    }
