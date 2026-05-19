# Grid Calculation v2

## Philosophie

GridCheck hat **keine verifizierten Netzbetreiber-Topologiedaten** im MVP. Die Engine v2 liefert deshalb eine **transparente Plausibilitätsbewertung** mit dokumentierten Annahmen — keine Scheinkapazität, keine verbindliche Netzanschlusszusage.

Prinzipien:

1. **Jede Annahme wird gespeichert und angezeigt** (`assumptions[]`).
2. **Spannungsfall** nach DIN EN 50480: `ΔU = √3 × I × L × (R·cosφ + X·sinφ)` (3-phasig).
3. **Kurzschluss**: IEC 60909 nur vereinfacht **wenn** Sk'' oder Trafo-Daten vorliegen; sonst `cannot_calculate: true` mit Pflicht-Disclaimer.
4. **N-1**: Ausgabe heißt **N-1-Bewertung (Assessment)**, keine Voll-Lastflussanalyse; Disclaimer ist Pflicht.
5. **Machbarkeit**: differenzierte Status (`feasible`, `conditionally_feasible`, `requires_study`, `likely_infeasible`) — kein reines Ampel-Spielzeug.

## Architektur (bindend)

| Schicht | Ort | Rolle |
|--------|-----|--------|
| Rechenkern | `backend/engine/grid_calculation_v2.py` | Autoritative Berechnung |
| Typen | `backend/engine/grid_calculation_types.py` | Pydantic v2 |
| Kabel-DB | `backend/engine/cable_database.py` | VDE 0276-603 Werte |
| Kabellänge | `backend/engine/cable_length.py` | Haversine + Trassenfaktor |
| Integration | `backend/engine/berechnung.py` | Feld `grid_calculation_v2` im Analyse-JSON |
| Frontend | `frontend/lib/schemas/grid-calculation.ts` | Zod (read-only) |
| UI | `frontend/components/GridCalculationV2Panel.tsx` | Anzeige |

**Nicht** im Frontend: `calculateGridConnection` o.ä. als autoritative Engine.

## API

Bestehende Endpoints unverändert (`POST /api/v1/analyze`, v2-Route). Zusätzliches JSON-Feld:

```json
{
  "grid_calculation_v2": {
    "calculation_version": "2.1.0",
    "assumptions": [...],
    "voltage_drop_analysis": {...},
    "short_circuit_analysis": {"cannot_calculate": true, ...},
    "n1_assessment": {"disclaimer": "...", ...},
    "feasibility": {"status": "requires_study", ...}
  }
}
```

Revisionssicherheit: vollständiger Block wird mit dem Engine-Ergebnis in Analysis-Run / Revision gespeichert (wie bisher).

## Grenzwerte (Screening)

- NS Spannungsfall: 3 % (TAB-Richtwert)
- MS Spannungsfall: 2 % (BDEW MSRL-Richtwert)
- NS Erzeugung: **100 kW** Screening-Hinweis (VDE-AR-N 4100) — MS-Prüfung empfohlen
- Netzbetreiber-Akzeptanz Gaps 6–12: siehe `docs/NB_AKZEPTANZ_SCREENING.md` (Engine ≥ 2.2.0)

Die Legacy-Engine (`berechnung.py`) bleibt für Fazit A/B/C, Scores und N-1-Detail (`n1_analyse`) aktiv; v2 ergänzt strukturierte Transparenz.

## Tests

```powershell
cd backend
python -m pytest tests/test_grid_calculation_v2.py -q
```

## Manuelle Prüfung

1. Backend starten, `POST /api/v1/analyze` mit MS-PV-Fall (ohne `sk_mva`) → `short_circuit_analysis.cannot_calculate == true`.
2. Frontend `/projektierer` → Analyse → Abschnitt „Strukturierte Vorprüfung (Engine v2.1.0)“.
