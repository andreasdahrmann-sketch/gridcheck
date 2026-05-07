import json
import os
import math
from engine.ki_feedback import berechne_kalibrierung

KI_DATEN_PFAD = 'daten/ki_lerndaten.json'

def lade_lerndaten():
    if not os.path.exists(KI_DATEN_PFAD):
        return []
    try:
        with open(KI_DATEN_PFAD, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def speichere_lerndaten(daten):
    os.makedirs('daten', exist_ok=True)
    with open(KI_DATEN_PFAD, 'w', encoding='utf-8') as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)

def berechne_aehnlichkeit(a, b):
    try:
        felder = ['nennspannung', 'leistung_mw', 'entfernung_km']
        summe = 0.0
        for feld in felder:
            va = float(a.get(feld, 0))
            vb = float(b.get(feld, 0))
            maxval = max(abs(va), abs(vb), 1.0)
            diff = (va - vb) / maxval
            summe += diff ** 2
        if a.get('leitungstyp') != b.get('leitungstyp'):
            summe += 1.0
        if a.get('anschlussart') != b.get('anschlussart'):
            summe += 0.5
        distanz = math.sqrt(summe)
        aehnlichkeit = max(0.0, 1.0 - distanz / 3.0)
        return round(aehnlichkeit, 4)
    except Exception:
        return 0.0

def finde_aehnliche(eingabe, lerndaten, top_n=5):
    scored = []
    for eintrag in lerndaten:
        score = berechne_aehnlichkeit(eingabe, eintrag.get('eingabe', {}))
        if score > 0.3:
            scored.append({'score': score, 'eintrag': eintrag})
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_n]

def berechne_konfidenz(aehnliche):
    if not aehnliche:
        return 0.3
    n = len(aehnliche)
    avg_score = sum(a['score'] for a in aehnliche) / n
    konfidenz = min(0.3 + (n * 0.1) + (avg_score * 0.2), 0.98)
    return round(konfidenz, 3)


def _entscheidung_key(fazit):
    if isinstance(fazit, dict):
        return str(fazit.get('entscheidung', '')).strip().upper()
    if isinstance(fazit, str):
        return fazit.split(':')[0].strip().upper()
    return ''

def erzeuge_ki_hinweise(ergebnis, aehnliche):
    hinweise = []
    if not aehnliche:
        hinweise.append('Keine vergleichbaren Faelle in der Datenbank. Ergebnis basiert rein auf Berechnung.')
        return hinweise

    hinweise.append(f'{len(aehnliche)} aehnliche Faelle gefunden.')

    aktuelles_fazit = _entscheidung_key(ergebnis.get('fazit', ''))
    abweichungen = 0
    for a in aehnliche:
        altes_fazit = _entscheidung_key(a['eintrag'].get('fazit', ''))
        if altes_fazit and aktuelles_fazit:
            # Vergleiche Kernaussage (A/B/C Entscheidungsebene)
            if aktuelles_fazit != altes_fazit:
                abweichungen += 1

    if abweichungen > 0:
        hinweise.append(f'ACHTUNG: {abweichungen} von {len(aehnliche)} aehnlichen Faellen hatten ein abweichendes Ergebnis. Manuelle Pruefung empfohlen.')
    else:
        hinweise.append('Ergebnis konsistent mit aehnlichen Faellen. Hohe Validitaet.')

    # Bester Match Info
    bester = aehnliche[0]
    hinweise.append(f'Bester Match: Aehnlichkeit {round(bester["score"]*100,1)}%')

    return hinweise

def ki_bewertung(ergebnis):
    lerndaten = lade_lerndaten()
    eingabe = ergebnis.get('eingabe', {})

    aehnliche = finde_aehnliche(eingabe, lerndaten)
    konfidenz = berechne_konfidenz(aehnliche)
    kalibrierung = berechne_kalibrierung()
    faktor = float(kalibrierung.get('kalibrierungsfaktor', 1.0))
    konfidenz = round(max(0.05, min(0.98, konfidenz * faktor)), 3)
    hinweise = erzeuge_ki_hinweise(ergebnis, aehnliche)
    if kalibrierung.get('samples', 0) > 0:
        hinweise.append(
            f"Kalibrierung aktiv ({kalibrierung['samples']} NB-Feedbacks, Faktor {faktor})."
        )
    else:
        hinweise.append('Kalibrierung inaktiv: noch kein Netzbetreiber-Feedback vorhanden.')

    ergebnis['ki'] = {
        'konfidenz': konfidenz,
        'konfidenz_prozent': round(konfidenz * 100, 1),
        'aehnliche_faelle': len(aehnliche),
        'kalibrierung': kalibrierung,
        'hinweise': hinweise,
    }

    lernfall = {
        'eingabe': eingabe,
        'thermisch': ergebnis.get('thermisch', {}),
        'spannung': ergebnis.get('spannung', {}),
        'n1': ergebnis.get('n1', {}),
        'fazit': ergebnis.get('fazit', ''),
    }
    lerndaten.append(lernfall)
    speichere_lerndaten(lerndaten)

    return ergebnis
