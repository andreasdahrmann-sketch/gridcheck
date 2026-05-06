# GridCheck — Project State (Single Source of Truth)

**Letzte Aktualisierung:** 2026-05-02
**Regel:** Diese Datei ist verbindlich. Vor jeder Code-Aenderung lesen.

---

## 1. Vision
Pre-Netzanschluss-Check-App mit echter Diagnose (nicht nur Ampel).
N-1-Analyse, Netzplan, Empfehlungen, lernende KI, revisionssicher.
Ziel: Projektierer bekommen schnelle Antwort, VNB sparen Arbeit.

---

## 2. Aktueller Stand

### Backend (FastAPI, Python)
- [x] Scoring-Engine (Kapazitaet, Spannung, Kurzschluss, N-1, Datenqualitaet)
- [x] Szenarien-Analyse (Normal, Schwachlast, Starklast, N-1)
- [x] Impedanzmodell (Z_Quelle, Z_Trafo, Z_Leitung, Z_gesamt)
- [x] Kurzschluss-Berechnung (Ik_min, Ik_max, Sk am NVP)
- [x] Kostenindikation + Bauzeit-Schaetzung
- [x] Empfehlungs-Generator (regelbasiert)
- [x] SQLite-Persistenz
- [x] PDF-Export mit Hash + Zeitstempel
- [x] PLZ-Heuristik (Confidence D bei unbekannter Topologie)

### Frontend (React/TypeScript)
- [x] Eingabeformular (generisch)
- [x] Ergebnisseite mit Score 0-100, Confidence A-D
- [x] Sektionen: Kerndaten, Bewertung, Szenarien, N-1, Kurzschluss, Kosten, Empfehlungen, Impedanz
- [x] PDF-Export-Button
- [x] Stakeholder-Auswahl-Buttons (AKTUELL NUR KOSMETISCH - siehe Sprint 1)

---

## 3. Stakeholder-Spezifikation (FIX)

### Prioritaet 1: Projektierer / EPC
- Frage: "Geht das hier - und was kostet es mich?"
- Zusatz-Inputs: Budget, Zeitfenster, Flexibilitaet (Standort/Leistung anpassbar)
- Outputs: Geht/Bedingt/Nein + Was-waere-wenn-Optimierer + Kosten + Zeitachse
- Killer: Was-waere-wenn-Optimierer

### Prioritaet 2: Netzbetreiber (VNB)
- Frage: "Kann ich das integrieren ohne N-1 zu verletzen?"
- Zusatz-Inputs: Bestandsnetz-Daten, Trafo-Daten (Sn/uk), Sk am NVP, geplante Ausbauten
- Outputs: Netzanschlussbeurteilung-Entwurf, Auflagen-Katalog, N-1-Detail, TAR-Konformitaet
- Killer: N-1-Auflagen-Generator (VDE-AR-N 4110/4120-Textbausteine)

### Prioritaet 3: Asset Owner / Investor / Bank
- Frage: "Lohnt es sich, welches Risiko?"
- Zusatz-Inputs: Strompreis-Annahme, Foerderregime, Betriebsstunden, Renditeerwartung
- Outputs: Curtailment-Prognose, ROI, Sensitivitaetsmatrix, Bankfaehiger 1-Pager
- Killer: Bankfaehiger Risk- & Rendite-Report

### Phase 4 (spaeter): Gutachter, Kommune

---

## 4. Architektur

### Routing (FIX)
- /                 -> Landing mit Rollenauswahl
- /projektierer     -> Projektierer-Modul (Phase 1)
- /vnb              -> Netzbetreiber-Modul (Phase 2)
- /invest           -> Investor-Modul (Phase 3)

### Backend-Endpunkte (FIX)
- POST /api/v1/projektierer/analyze
- POST /api/v1/vnb/analyze
- POST /api/v1/invest/analyze
- Gemeinsame Engine in core/ (Lastfluss, Kurzschluss, N-1)
- Rollenspezifische Layer in roles/projektierer.py, roles/vnb.py, roles/invest.py

### Frontend-Komponenten (FIX)
- forms/ProjektiererForm.tsx
- forms/VnbForm.tsx
- forms/InvestForm.tsx
- forms/BaseFields.tsx (gemeinsame Pflichtfelder)
- results/ProjektiererResult.tsx
- results/VnbResult.tsx
- results/InvestResult.tsx
- results/SharedBlocks/ (Score, Impedanz, PDF-Button)

---

## 5. Monetarisierung (FIX)

| Tier              | Zielgruppe     | Preis            |
|-------------------|----------------|------------------|
| Free              | Lead-Gen       | 0 EUR            |
| Pro Projektierer  | EPC            | 49-99 EUR/Mon.   |
| Pro Asset Owner   | Betreiber      | 99-199 EUR/Mon.  |
| VNB-Edition       | Netzbetreiber  | 500-2000 EUR/Mon.|
| Gutachten-Modul   | Berater        | 29 EUR/Gutachten |
| API/White-Label   | Grosskunden    | individuell      |

---

## 6. Killer-Features (FIX, Reihenfolge)

1. Was-waere-wenn-Optimierer (Projektierer) - Phase 1 MVP-Variante (a) schlank
2. N-1-Auflagen-Generator (VNB) - Phase 2
3. Bankability-Report (Invest) - Phase 3
4. KI lernend + Audit-Trail - parallel
5. Multi-VNB-Vergleich - Phase 4

---

## 7. Revisionssicherheit (FIX)
- SHA256 Hash-Chain in SQLite
- Zeitstempel + Modellversion + Annahmen pro Analyse
- PDF mit Hash sichtbar
- Disclaimer: nicht qualifizierter Zeitstempel

---

## 8. Was NICHT mehr diskutiert wird
- Stakeholder-Trennung getrennte Routen -> JA, fix
- Killer-Features Reihenfolge -> fix
- Stack: FastAPI + React + SQLite -> fix
- Revisionssicherheit via Hash-Chain -> fix fuer MVP

---

## 9. CURSOR/AI RULES (WICHTIG!)
- IMMER PowerShell-Befehle liefern (User arbeitet auf Windows PowerShell)
- KEINE rohen Markdown-Bloecke zum copy-paste in PowerShell - nutze @'...'@ Here-Strings + Out-File
- Encoding immer UTF-8: -Encoding UTF8
- Keine Sonderzeichen wie Emojis in PowerShell-Strings (Encoding-Probleme)
- Bei Code-Aenderungen: erst PROJECT_STATE.md lesen, dann handeln
- Keine Doppel-Diskussionen abgeschlossener Themen
