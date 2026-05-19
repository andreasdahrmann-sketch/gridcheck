# Netzbetreiber-Akzeptanz Screening (Gaps 6–12)

Transparente Vorprüfungen in `grid_calculation_v2` — **keine Scheinberechnungen**, keine freie Trafo-Kapazität.

## Engine-Block

Ausgabe im JSON-Feld `grid_calculation_v2` (Version ≥ 2.2.0):

| Feld | Gap | Inhalt |
|------|-----|--------|
| `transformer_assessment` | 6 | ONT/Trafo-Auslastung: `insufficient_data` oder konservatives Screening |
| `protection_concept_screening` | 7 | Checkliste Schutzkonzept Einspeiseanlagen |
| `network_feedback_screening` | 8 | EN 61000 / IEC 61000 qualitative Hinweise |
| `coincidence_factor_screening` | 9 | Einzelanschluss, Warnung bei großer NS-Leistung |
| Annahmen + Spannungsfall | 10 | Netzform (radial/ring/meshed) + Kabel/Freileitung |
| `norm_references_applied` | 11 | Tabelle angewandter Normen |
| `eeg_feed_in_screening` | 12 | EEG 2023 § 9 (≥ 25 kW), Direktvermarktung-Hinweis (≥ 100 kW) |

## Eingaben (optional)

| Frontend / API | Engine |
|----------------|--------|
| `trafo_sr_kva` | `transformer_power_kva` |
| `vorbelastung_pct` | `transformer_load_percent` |
| `topologie` | `grid_topology` |
| `leitungsart` (`kabel` / `freileitung`) | `cable_type` |

Fehlen Trafo-Nennleistung **und** Bestandsauslastung → `transformer_assessment.status = insufficient_data`, **kein** Auslastungs-%.

## Tests

```powershell
cd backend
python -m pytest tests/test_nb_akzeptanz_screening.py tests/test_grid_calculation_v2.py -q
```

## Disclaimer

Alle Blöcke sind **vorläufiges Screening** für die Entscheidungsvorbereitung. Verbindliche Bewertung nur durch den zuständigen Netzbetreiber.
