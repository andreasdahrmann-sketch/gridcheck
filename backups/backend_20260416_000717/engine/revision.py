import json
import os
import hashlib
import uuid
from datetime import datetime, timezone

REVISIONS_PFAD = 'daten/revisionen.json'

def lade_revisionen():
    if not os.path.exists(REVISIONS_PFAD):
        return []
    with open(REVISIONS_PFAD, 'r', encoding='utf-8') as f:
        return json.load(f)

def speichere_revisionen(revisionen):
    os.makedirs('daten', exist_ok=True)
    with open(REVISIONS_PFAD, 'w', encoding='utf-8') as f:
        json.dump(revisionen, f, indent=2, ensure_ascii=False)

def erzeuge_hash(daten):
    raw = json.dumps(daten, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def erzeuge_vorgaenger_hash(revisionen):
    if not revisionen:
        return 'GENESIS'
    letzter = revisionen[-1]
    return letzter.get('hash', 'UNBEKANNT')

def speichere_revision(ergebnis):
    revisionen = lade_revisionen()
    revision_id = str(uuid.uuid4())
    zeitstempel = datetime.now(timezone.utc).isoformat()
    vorgaenger_hash = erzeuge_vorgaenger_hash(revisionen)

    revision = {
        'id': revision_id,
        'zeitstempel': zeitstempel,
        'vorgaenger_hash': vorgaenger_hash,
        'eingabe': ergebnis.get('eingabe', {}),
        'thermisch': ergebnis.get('thermisch', {}),
        'spannung': ergebnis.get('spannung', {}),
        'n1': ergebnis.get('n1', {}),
        'ki': ergebnis.get('ki', {}),
        'fazit': ergebnis.get('fazit', ''),
        'empfehlungen': ergebnis.get('empfehlungen', []),
    }

    revision['hash'] = erzeuge_hash(revision)

    revisionen.append(revision)
    speichere_revisionen(revisionen)

    ergebnis['revision'] = {
        'id': revision_id,
        'zeitstempel': zeitstempel,
        'hash': revision['hash'],
        'vorgaenger_hash': vorgaenger_hash,
        'revisionsnummer': len(revisionen),
    }

    return ergebnis

def pruefe_integritaet():
    revisionen = lade_revisionen()
    if not revisionen:
        return {'intakt': True, 'anzahl': 0, 'fehler': []}

    fehler = []
    for i, rev in enumerate(revisionen):
        gespeicherter_hash = rev.get('hash', '')
        rev_ohne_hash = {k: v for k, v in rev.items() if k != 'hash'}
        berechneter_hash = erzeuge_hash(rev_ohne_hash)

        if gespeicherter_hash != berechneter_hash:
            fehler.append({
                'index': i,
                'id': rev.get('id', ''),
                'fehler': 'Hash stimmt nicht ueberein'
            })

        if i == 0:
            if rev.get('vorgaenger_hash') != 'GENESIS':
                fehler.append({
                    'index': i,
                    'id': rev.get('id', ''),
                    'fehler': 'Erster Eintrag hat keinen GENESIS-Vorgaenger'
                })
        else:
            erwarteter_vorgaenger = revisionen[i-1].get('hash', '')
            if rev.get('vorgaenger_hash') != erwarteter_vorgaenger:
                fehler.append({
                    'index': i,
                    'id': rev.get('id', ''),
                    'fehler': 'Verkettung unterbrochen'
                })

    return {
        'intakt': len(fehler) == 0,
        'anzahl': len(revisionen),
        'fehler': fehler,
    }
