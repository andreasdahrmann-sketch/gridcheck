"""Smoke-Test: PV 5 MW an realistischem UW (2x40 MVA)."""
import json

from engine.n1_analyse import analysiere_n1

# Realszenario: PV-Park 5 MW, MS-Anschluss
eingabe = {
    "leistung_mw": 5.0,
    "cos_phi": 0.95,
    "nennspannung": 20.0,
    "topologie": "ring",
    "restkapazitaet_ms_mva": 10.0,
    "umspannwerk": {
        "datenquelle": "planner_assumption",
        "trafos": [
            {"sn_mva": 40, "belastung_aktuell_mw": 18},
            {"sn_mva": 40, "belastung_aktuell_mw": 18},
        ],
        "abgaenge": [
            {"label": "A1", "primary": True, "i_max_a": 630, "belastung_aktuell_a": 520},
            {"label": "A2", "i_max_a": 630, "belastung_aktuell_a": 260},
        ],
    },
}

thermisch_n1 = {"auslastung_prozent": 55.0, "i_betrieb_a": 350.0, "i_max_a": 645.0}
spannung_n1 = {"delta_u_prozent": 1.8}
ergebnis = analysiere_n1(eingabe, thermisch_n1=thermisch_n1, spannung_n1=spannung_n1)

print("=" * 70)
print("SMOKE-TEST: PV 5 MW an UW Musterstadt (2x40 MVA, MS)")
print("=" * 70)
print(f"\nEngine-Version: {ergebnis['berechnungs_version']}")
print(f"N1-Klasse:      {ergebnis['gesamt']['n1_klasse']}")
print(f"Konfidenz:      {ergebnis['gesamt']['konfidenz']:.2f}")
print(f"Gesamt:         {ergebnis['gesamt']['bewertung']}")
print(f"Stufe:          {ergebnis['gesamt']['stufenbegruendung']}")
print(f"\n--- Trafo-N-1 ---")
t = ergebnis["n1_trafo"]
print(f"  Bewertung:        {t['bewertung']}")
print(f"  Auslastung N-1:   {t.get('auslastung_n1_prozent', 'n/a')}%")
print(f"  Begruendung:      {t['begruendung_technisch']}")
print(f"\n--- Leitung-N-1 ---")
l = ergebnis["n1_leitung"]
print(f"  Bewertung:        {l['bewertung']}")
print(f"  Begruendung:      {l['begruendung_technisch']}")
print(f"\n--- Abgang-N-1 ---")
a = ergebnis["n1_abgang"]
print(f"  Bewertung:        {a['bewertung']}")
print(f"  Beste Reserve:    {a.get('beste_reserve_a', 'n/a')} A")
print(f"  Begruendung:      {a['begruendung_technisch']}")
print(f"\n--- Spannung-N-1 ---")
s = ergebnis["n1_spannung"]
print(f"  Bewertung:        {s['bewertung']}")
print(f"  Delta-U:          {s.get('delta_u_n1_prozent', 'n/a')}%")
print(f"\n--- Empfehlungen ---")
for e in ergebnis["gesamt"]["empfehlungen"]:
    print(f"  - {e}")
print(f"\n--- Annahmen ({len(ergebnis['annahmen'])}) ---")
for a in ergebnis["annahmen"][:5]:
    print(f"  - {a['begruendung']}")
print("\n" + "=" * 70)
print("VOLLES JSON:")
print("=" * 70)
print(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str))
