# Compliance-Registry - TODO & Status

**Stand:** 2025-01
**Pflege:** Bei jeder Norm-Aenderung Eintrag aktualisieren.

## Vollstaendig in `norm_registry.py` gelistet
Siehe `compliance/norm_registry.py` - aktuell 21 Normen/Gesetze.

## Im Code referenziert, Bewertungslogik noch unvollstaendig

| Norm | Modul | Status | Fehlend |
|---|---|---|---|
| VDE-AR-N 4110 | engine/spannung.py | teilweise | Q(U)-Statik komplett, FRT-Pruefung |
| VDE-AR-N 4120 | engine/n1.py | teilweise | Mehrfachausfaelle, Topologie-Erkennung |
| DIN EN 60909 | engine/kurzschluss.py | teilweise | Max/min Kurzschlussstrom |
| EU 2016/631 RfG | - | offen | Anlagentyp-Klassifizierung A/B/C/D |

## Noch nicht implementiert (TODO Sprint 2+)
- [ ] VDE-AR-N 4140 Speicher-Bewertung (separate Logik)
- [ ] DIN EN 50160 Spannungsqualitaets-Pruefung (THD, Flicker, Unsymmetrie)
- [ ] IEC 61000-3-Reihe Oberschwingungsbewertung
- [ ] TAB Hoechstspannung 2019 (HoeS-spezifische Pruefungen)
- [ ] MsbG Messstellen-Anbindung
- [ ] Lokale Netzbetreiber-TAB (NB-spezifische Abweichungen)

## Aenderungsprotokoll
- **2025-01:** Initiale Registry erstellt (Sprint 1, MS PDF-1a)
