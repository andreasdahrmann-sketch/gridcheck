# GridCheck - Technische Zusammenfassung v3
## Stand: 12.04.2026 23:05

---

## 1. UEBERBLICK

GridCheck ist eine Pre-Netzanschluss-Check Web-App fuer Netzanschlussbegehren
im Mittelspannungsnetz (10-30 kV, primaer 20 kV).

Die App liefert Projektierern und Netzbetreibern eine schnelle, fundierte
Erstbewertung, ob ein Netzanschluss (Einspeisung/Bezug) an einem bestimmten
Standort im MS-Netz technisch machbar ist.

Zielgruppe: Projektierer (EE-Anlagen), Netzbetreiber, Planungsbueros
Anwendungsbereich: Ausschliesslich Mittelspannung 10-30 kV
Typischer Leistungsbereich: 100 kW bis 10 MW
Regelwerk: VDE-AR-N 4110 (MS-Anschlussregeln)
Monetarisierung: SaaS-Modell (Pay-per-Check / Abo)

---

## 2. TECH-STACK

- Frontend: React 18 + TypeScript
- Build-Tool: Vite
- Styling: Tailwind CSS
- State: React Hooks
- Backend (geplant): Python FastAPI
- Datenbank (geplant): PostgreSQL

---

## 3. PROJEKTSTRUKTUR

gridcheck/frontend/src/
- App.tsx - Haupt-App mit Tab-Navigation
- components/QuickCheck.tsx - Schnell-Check (Eingabe + Ergebnis)
- components/DetailAnalysis.tsx - Detail-Analyse (Platzhalter)
- components/OperatorDashboard.tsx - Netzbetreiber-Dashboard (Platzhalter)
- engine/gridEngine.ts - Berechnungskern
- types/index.ts - TypeScript Typdefinitionen

---

## 4. BERECHNUNGSKERN (gridEngine.ts)

### 4.1 Anwendungsbereich
- Ausschliesslich Mittelspannungsnetz (MS)
- Nennspannung: 20 kV (primaer), 10 kV (sekundaer)
- Leistungsbereich: 100 kW bis 10 MW
- Regelwerk: VDE-AR-N 4110

### 4.2 Eingabeparameter
- PLZ: Heuristisches Netzgebiet-Mapping (Region, Netzbetreiber, Sk)
- Leistung (kW): Wirkleistung der Anlage (100 kW - 10 MW)
- Anlagentyp: PV / Wind / Batterie / Ladepark / Industrie / Waermepumpe
- Nennspannung: 20 kV (Standard) / 10 kV (waehlbar)
- cos(phi): Leistungsfaktor (Default 0.95)

### 4.3 Kurzschlussleistung (Sk) nach PLZ-Heuristik
- Grossstadt (1xxxxx, 2xxxxx): Sk = 250 MVA
- Mittelstadt: Sk = 150 MVA
- Laendlich: Sk = 80 MVA
- Alle Werte beziehen sich auf die MS-Sammelschiene (20 kV)

### 4.4 Kernformeln (alle bezogen auf 20 kV MS-Ebene)

Scheinleistung:
  S = P / cos(phi)

Anschlussstrom (MS-seitig):
  I = S / (sqrt(3) * U_MS)
  mit U_MS = 20 kV

Spannungsaenderung nach VDE-AR-N 4110:
  delta_u = (P * R + Q * X) / (U_MS^2)
  Vereinfacht: delta_u_prozent = (S / Sk) * 100

Kurzschlussstrom-Beitrag:
  Ik_anteil = S / (sqrt(3) * U_MS)

Thermische Auslastung (MS-Trafo / UW):
  Typische MS-Trafo-Leistung: 20-63 MVA (HS/MS-Umspanner)
  Standard-Annahme: S_trafo = 40 MVA
  Auslastung = S / S_trafo * 100

### 4.5 VDE-AR-N 4110 Pruefungen (MS-spezifisch)
- Spannungsaenderung: max 2% am Netzverknuepfungspunkt (NVP)
- Kurzschlussstrom: Ik_anteil < 10% von Ik_netz
- Thermische Belastung: < 70% Trafo-Nennleistung (N-1 Reserve)
- Oberschwingungen: THD < 8% (vereinfacht, nicht modelliert)
- Flickerbeitrag: Pst < 0.46 / Plt < 0.37 (vereinfacht, nicht modelliert)

### 4.6 N-1 Pruefung (MS-Netz)
- Reduzierte Sk: Sk_n1 = Sk * 0.6 (Ausfall eines MS-Strangs)
- Alle Pruefungen werden mit reduzierter Sk wiederholt
- N-1 ist im MS-Netz immer relevant (Ringbetrieb -> Stichbetrieb)

### 4.7 MS-spezifische Randbedingungen
- Typische MS-Kabelleitungen: NA2XS2Y, NAYY (Impedanzwerte hinterlegt)
- Typische Leitungslaengen MS: 5-30 km
- Schaltanlagen: Einschleifung in bestehenden MS-Ring oder Stichleitung
- Schutzkonzept: UMZ-Schutz, Distanzschutz am UW

---

## 5. SCORING-SYSTEM

### 5.1 Punkte (max 100)
- Spannungsaenderung: 35 Punkte (< 50% des 2%-Grenzwerts = voll, > 100% = 0)
- Kurzschlussstrom: 25 Punkte (< 50% Grenzwert = voll, > 100% = 0)
- Thermische Belastung: 25 Punkte (< 50% = voll, > 100% = 0)
- N-1 Sicherheit: 15 Punkte (bestanden = 15, nicht = 0)

### 5.2 Ampel-Bewertung
- GRUEN (>= 70 Punkte): Anschluss voraussichtlich machbar
- GELB (40-69 Punkte): Eingeschraenkt machbar, Massnahmen noetig
- ROT (< 40 Punkte): Kritisch, erhebliche Netzmassnahmen erforderlich

### 5.3 Szenarien-Analyse
Drei Szenarien werden parallel berechnet:
- Optimistisch: Sk * 1.3 (starkes Netz, stadtnah)
- Realistisch: Sk * 1.0 (Standardannahme)
- Konservativ: Sk * 0.7 (schwaches Netz, laendlich, langer MS-Strang)

---

## 6. UI-STRUKTUR

### Tab 1: Schnell-Check
- Eingabeformular (PLZ, Leistung, Anlagentyp, Nennspannung 20/10kV, cos phi)
- Ergebnisanzeige: Ampel, Score, Detailwerte
- Szenarien-Vergleich
- Empfehlungen + Einschraenkungen

### Tab 2: Detail-Analyse (Platzhalter)
### Tab 3: Netzbetreiber-Dashboard (Platzhalter)

---

## 7. DATENQUALITAET / CONFIDENCE

- Level A: Reale Netzdaten vom Betreiber (Sk am NVP bekannt)
- Level B: Verifizierte Regionaldaten (Netzbetreiber-Richtwerte)
- Level C: Statistische Schaetzung
- Level D: PLZ-Heuristik (aktueller Stand)

---

## 8. ROADMAP

1. PDF-Export (revisionssicher)
2. Detail-Analyse + Netzplan-Visualisierung
3. Backend API (FastAPI)
4. Datenbank (PostgreSQL)
5. KI-Modul (Lernfaehigkeit)
6. Netzbetreiber-Dashboard
7. User Auth + Rollen
8. Echte Netzdaten-Integration (Sk-Werte je UW)
9. Billing / Abo-System
10. Mobile Optimierung

---

## 9. BEKANNTE EINSCHRAENKUNGEN

1. Rein clientseitige Berechnung (kein Backend)
2. PLZ-Heuristik statt realer Netzdaten
3. Vereinfachtes Impedanzmodell (keine Leitungslaengen-Differenzierung)
4. Keine Beruecksichtigung bestehender Einspeiser am selben NVP
5. Trafo-Daten sind Standardwerte (nicht UW-spezifisch)
6. Keine Blindleistungskompensation modelliert
7. Kein Oberschwingungseinfluss beruecksichtigt
8. Kein Flickerbeitrag berechnet
9. Keine Schaltanlagen-Topologie (Ring/Stich) beruecksichtigt

---

Generiert am 12.04.2026 23:05 - GridCheck v3
