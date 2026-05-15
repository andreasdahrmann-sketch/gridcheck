from .berechnung import berechne_netzanschluss
from .ki_modul import ki_bewertung
from .revision import speichere_revision
from .pdf_report import erstelle_pdf


def berechne_netzcheck(
    typ='PV', leistung_kw=100.0, plz='00000', spannung_kv=None,
    skv_mva=None, bestehende_einspeisung_kw=0, leitungstyp='NAYY150',
    leitungslaenge_km=1.0, einspeiseart='Volleinspeisung',
    cos_phi=0.95, parallele_systeme=1,
):
    leistung_mw = leistung_kw / 1000.0

    if spannung_kv is None or spannung_kv <= 0:
        if leistung_mw <= 0.1:
            spannung_kv = 0.4
        elif leistung_mw <= 5.0:
            spannung_kv = 20.0
        else:
            spannung_kv = 110.0

    leitungstyp_map = {
        'NAYY 150': 'NAYY150', 'NAYY 240': 'NAYY240',
        'NA2XS2Y 150': 'NA2XS2Y150', 'NA2XS2Y 240': 'NA2XS2Y240',
    }
    leitungstyp_norm = leitungstyp_map.get(leitungstyp, leitungstyp)

    anschlussart_map = {
        'Volleinspeisung': 'Einspeisung', 'Ueberschusseinspeisung': 'Einspeisung',
        'Bezug': 'Entnahme', 'Speicher': 'Speicher',
    }
    anschlussart = anschlussart_map.get(einspeiseart, 'Einspeisung')

    eingabe = {
        'anlagentyp': typ, 'p_kw': leistung_kw, 'plz': plz,
        'leistung_mw': leistung_mw, 'nennspannung': spannung_kv,
        'leitungstyp': leitungstyp_norm, 'entfernung_km': leitungslaenge_km,
        'anschlussart': anschlussart, 'cos_phi': cos_phi,
        'parallele_systeme': parallele_systeme,
        'bestehende_einspeisung_mw': bestehende_einspeisung_kw / 1000.0,
    }

    if skv_mva is not None and skv_mva > 0:
        eingabe['sk_mva'] = skv_mva

    result = berechne_netzanschluss(eingabe)

    if result.get('status') == 'FEHLER':
        return {
            'score': 0, 'spannungsband_ok': False,
            'thermische_auslastung_ok': False, 'kurzschluss_ok': False,
            'n1_ok': False, 'netzebene': 'unbekannt',
            'empfehlung': '; '.join(result.get('fehler', ['Berechnung fehlgeschlagen'])),
            'details': result,
        }

    try:
        result = ki_bewertung(result)
    except Exception:
        result['ki'] = {'konfidenz_prozent': 0, 'hinweise': ['KI-Modul nicht verfuegbar']}

    try:
        speichere_revision(result)
    except Exception:
        pass

    scores = result.get('scores', {})
    thermisch = result.get('thermisch', {})
    spannung = result.get('spannung', {})
    kurzschluss = result.get('kurzschluss', {})
    n1 = result.get('n1', {})
    fazit = result.get('fazit', {})

    spannungsband_ok = spannung.get('bewertung', 'ROT') in ('GRUEN', 'GELB')
    thermisch_ok = thermisch.get('bewertung', 'ROT') in ('GRUEN', 'GELB')
    kurzschluss_ok = kurzschluss.get('bewertung', 'ROT') in ('GRUEN', 'GELB')
    n1_ok = n1.get('n1_sicher', False)

    empfehlungen = result.get('empfehlungen', [])
    empfehlung_str = ' | '.join(empfehlungen) if isinstance(empfehlungen, list) else str(empfehlungen)

    if spannung_kv <= 1.0:
        netzebene = 'NS'
    elif spannung_kv <= 50.0:
        netzebene = 'MS'
    else:
        netzebene = 'HS'

    return {
        'score': scores.get('gesamt', 50),
        'spannungsband_ok': spannungsband_ok,
        'thermische_auslastung_ok': thermisch_ok,
        'kurzschluss_ok': kurzschluss_ok,
        'n1_ok': n1_ok,
        'netzebene': netzebene,
        'empfehlung': empfehlung_str,
        'details': {
            'fazit': fazit, 'scores': scores, 'thermisch': thermisch,
            'spannung': spannung, 'kurzschluss': kurzschluss, 'n1': n1,
            'szenarien': result.get('szenarien', []),
            'kosten': result.get('kosten', {}),
            'wirtschaftlichkeit': result.get('wirtschaftlichkeit', {}),
            'ki': result.get('ki', {}),
            'impedanz': result.get('impedanz', {}),
            'pqs': result.get('pqs', {}),
            'datenqualitaet': result.get('datenqualitaet', {}),
            'warnungen': result.get('warnungen', []),
            'nb_check': result.get('nb_check', {}),
            'empfehlungen': empfehlungen,
        },
    }


__all__ = ['berechne_netzanschluss', 'berechne_netzcheck', 'ki_bewertung', 'speichere_revision', 'erstelle_pdf']
