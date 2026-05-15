"""Smoke-Test: PV 5 MW an realistischem UW (2x40 MVA)."""
import json
from engine.n1_analyse import analysiere_n1

# Realszenario: PV-Park 5 MW, MS-Anschluss
eingabe = {
    "leistung_neu_mw": 5.0,
    "spannungsebene": "MS",
    "uw_daten": {
        "name": "UW Musterstadt",
        "spannungsebene": "MS",
        "trafos": [
            {"sn_mva": 40, "belastung_aktuell_mw": 18},
            {"sn_mva": 40, "belastung_aktuell_mw": 18},
        ],
    },
    "leitung_daten": {
        "typ": "Freileitung",
        "querschnitt_mm2": 240,
        "laenge_km": 4.5,
        "ir_a": 645,
        "auslastung_aktuell_prozent": 55,
    },
    "delta_u_prozent": 1.8,
    "u_nenn_kv": 20.0,
}

ergebnis = analysiere_n1(eingabe)

print("=" * 70)
print("SMOKE-TEST: PV 5 MW an UW Musterstadt (2x40 MVA, MS)")
print("=" * 70)
print(f"\nEngine-Version: {ergebnis['version']}")
print(f"N1-Klasse:      {ergebnis['n1_klasse']}")
print(f"Konfidenz:      {ergebnis['konfidenz']:.2f}")
print(f"Gesamt:         {ergebnis['gesamt']['bewertung']}")
print(f"\n--- Trafo-N-1 ---")
t = ergebnis["trafo"]
print(f"  Bewertung:        {t['bewertung']}")
print(f"  Auslastung N-1:   {t.get('auslastung_n1_prozent', 'n/a')}%")
print(f"  Begruendung:      {t['begruendung_technisch']}")
print(f"\n--- Leitung-N-1 ---")
l = ergebnis["leitung"]
print(f"  Bewertung:        {l['bewertung']}")
print(f"  Begruendung:      {l['begruendung_technisch']}")
print(f"\n--- Spannung-N-1 ---")
s = ergebnis["spannung"]
print(f"  Bewertung:        {s['bewertung']}")
print(f"  Delta-U:          {s.get('delta_u_prozent', 'n/a')}%")
print(f"\n--- Empfehlungen ---")
for e in ergebnis["empfehlungen"]:
    print(f"  - {e}")
print(f"\n--- Annahmen ({len(ergebnis['annahmen'])}) ---")
for a in ergebnis["annahmen"][:5]:
    print(f"  - {a}")
print("\n" + "=" * 70)
print("VOLLES JSON:")
print("=" * 70)
print(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str))
