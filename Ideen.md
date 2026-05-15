# Ideen

Diese Datei ist die zentrale Ideensammlung fuer die Pre-Gridcheck-App.  
Ziel: priorisieren, automatisch Vorschlaege ableiten und schrittweise abarbeiten.

## Grundidee der App

- [ ] Deutschlandweite Pre-Netzanschlusspruefung bereitstellen.
- [ ] Keine verbindliche Netzanschlusszusage, sondern technisch-wirtschaftliche Vorbewertung.
- [ ] Diagnose-Tool mit folgenden Kernergebnissen:
  - Netzanschlusswahrscheinlichkeit
  - geeignete Spannungsebene
  - Standort- und Trassenrisiken
  - Kostenindikatoren
  - Einspeisedruckanalyse
  - Empfehlungen fuer naechste Schritte

## Zentrale Datenstrategie

- [ ] Mehrschichtige Datenbasis aufbauen (keine Einzelquelle).
- [ ] Datenquellen nach Relevanz und Verlaesslichkeit priorisieren.

### Offizielle Primaerquellen

- [ ] MaStR
- [ ] SMARD
- [ ] DWD
- [ ] Bundesnetzagentur
- [ ] Destatis
- [ ] BGR
- [ ] BKG

### Geografische Kandidatenquellen

- [ ] OpenStreetMap
- [ ] Overpass API
- [ ] Spaeter: manuelle Asset-Erfassung in der Karte (Umspannwerk, Trafostation, Leitungssegmente) pro Projekt mit Quelle, Confidence, Nutzer und Zeitstempel fuer revisionssicheren Datenaufbau.

### Spaetere Ergaenzungen

- [ ] VNB-Kapazitaetskarten
- [ ] Netzbetreiber-Preisblaetter
- [ ] Anschlussrichtlinien
- [ ] Kommunale und Landes-GIS-Daten

## Wichtige Datenquellen und Nutzen

### OpenStreetMap / Overpass

- [ ] Findet Umspannwerke, Leitungen, Masten, Kraftwerke, moegliche Netzanschlusspunkte.
- [ ] Nutzbar fuer Naehe, Standortkandidaten, Trassenindikatoren.
- [ ] Nicht als Beweis fuer freie Netzkapazitaet verwenden.

### MaStR

- [ ] Offizielle Quelle fuer Erzeugungsanlagen, Speicher, Leistung, Standort, Status.
- [ ] Relevant fuer Einspeisedruck, Anlagencluster, lokale Netzpraegung.

### SMARD

- [ ] Markt-, Redispatch-, Engpass- und Systemdaten.
- [ ] Relevant fuer regionale Engpassindikatoren und Abregelungsrisiken.

### DWD

- [ ] Wetter-, Wind-, Strahlungs- und Klimadaten.
- [ ] Relevant fuer Ertragsprognosen, Einspeisespitzen, Bau-/Wetterrisiken.

### BGR

- [ ] Boden, Geologie, Grundwasser, Baugrund.
- [ ] Relevant fuer Trassenkosten, Tiefbaurisiken, Genehmigungsindikatoren.

### BKG

- [ ] Amtliche Geodaten, Verwaltungsgrenzen, Kartenbasis.
- [ ] Wichtig fuer Reporting und Georeferenzierung.

### Destatis

- [ ] Baupreisindex, Preisstatistiken, Strukturdaten.
- [ ] Nützlich fuer Kostenmodelle.

### ENTSO-E (optional spaeter)

- [ ] Europaeische Strommarkt-, Last-, Erzeugungs- und Engpassdaten.
- [ ] Optional fuer spaetere System- und Plausibilitaetsmodelle.

## Empfohlenes Kern-Datenmodell

### `asset_candidates`
- [ ] Netzasset-Kandidaten aus OSM/GIS.
- [ ] Umspannwerke, Leitungen, Schaltanlagen, Transformatorstandorte.
- [ ] Spannungsebenen, Betreiber, Geometrie, Confidence.

### `generation_assets`
- [ ] Anlagen aus MaStR und Kraftwerksliste.
- [ ] Leistung, Energietraeger, Standort, Status, Netzebene.

### `system_signals`
- [ ] Daten aus SMARD / ENTSO-E.
- [ ] Redispatch, Abregelung, Preise, Last, Engpassindikatoren.

### `weather_resource`
- [ ] Wetter- und Ertragsdaten aus DWD.
- [ ] Wind, Strahlung, Temperatur, Niederschlag.

### `ground_risk`
- [ ] Baugrund- und Trassenrisiken.
- [ ] Bodenklasse, Geologie, Grundwasser, Grabungsrisiko.

### `cost_indices`
- [ ] Kosten- und Preisindikatoren.
- [ ] Baukosten, Netzentgeltumfeld, regionale Kostenfaktoren.

### `gridcheck_result_audit`
- [ ] Revisionssichere Speicherung aller Ergebnisse.
- [ ] Inputdaten, Quellenstaende, Modellversion, Score, Warnungen, Annahmen.

## Revisionssicherheit (Pflicht)

Jede App-Antwort soll speichern:

- [ ] verwendete Datenquellen
- [ ] Datenstand
- [ ] Modellversion
- [ ] Annahmen
- [ ] Unsicherheiten
- [ ] Scoring-Komponenten
- [ ] verwendete Geometrie- und Zuordnungslogik
- [ ] finale Bewertung
- [ ] Warnungen und Review-Hinweise

## Markt- und Konkurrenzumfeld

### Bestehende Loesungen

- [ ] Netzampeln einzelner VNB
- [ ] PowerFactory / NEPLAN
- [ ] envelio
- [ ] PV*SOL / Polysun
- [ ] Energy Brainpool / Enervis
- [ ] Excel-basierte Eigenloesungen

### Beobachtete Luecke

- [ ] Niederschwellige Tools fehlen, die Folgendes verbinden:
  - Netz-Physik
  - Wirtschaftlichkeit
  - Standortdiagnose
  - Netzanschlussrisiko
  - Auflagen
  - revisionssichere Reports

## Moegliche Killer-Features

### Was-waere-wenn-Optimierer

- [ ] Zeigt, welche Leistung unter welchen Bedingungen moeglich waere.
- [ ] Beispiel-Szenarien:
  - maximale Leistung ohne Auflage
  - Leistung mit Q(U)-Regelung
  - Leistung mit Spitzenkappung
  - Leistung mit Speicherbetrieb

### N-1-Auflagen-Generator

- [ ] Technische Auflagenvorschlaege fuer Netzbetreiber erzeugen.
- [ ] Textbausteine und Referenzen auf technische Anschlussregeln.

### Bankfaehiger Risk- und Rendite-Report

- [ ] Verknuepft Netzrisiko, Curtailment, CAPEX, Strompreisszenarien, Rendite.
- [ ] Zielgruppen: Investoren, Banken, Speicherparkbetreiber.

### Lernende KI mit Audit-Trail

- [ ] Nutzt freigegebene reale Anschlussfaelle zur Modellverbesserung.
- [ ] Jede Empfehlung bleibt versioniert und nachvollziehbar.

### Multi-VNB-Vergleich (spaeter)

- [ ] Vergleich von Standorten nach Netzbetreibergebiet, erwarteter Dauer, Kosten, Risiko.

## Zielgruppen

### Projektierer

Kaufen vor allem:
- [ ] schnellere Standortentscheidung
- [ ] bessere Trefferquote
- [ ] Vermeidung von Sackgassen

Wichtige Funktionen:
- [ ] Standortcheck
- [ ] Netzebenen-Vorschlag
- [ ] Netzanschlusspunkt-Kandidaten
- [ ] Was-waere-wenn-Optimierer
- [ ] Kostenbandbreite
- [ ] Export

### Speicherparkbetreiber / Investoren / Asset Owner

Kaufen vor allem:
- [ ] Investierbarkeitspruefung
- [ ] Risiko- und Renditebewertung
- [ ] bessere CAPEX- und Zeitannahmen

Wichtige Funktionen:
- [ ] Due-Diligence-Report
- [ ] Portfoliovergleich
- [ ] Szenarioanalyse
- [ ] Regionenranking
- [ ] Risk-/Rendite-Report

### Netzbetreiber

Kaufen vor allem:
- [ ] Prozessentlastung
- [ ] standardisierte Vorpruefung
- [ ] bessere Priorisierung
- [ ] Fallakte und Dokumentation
- [ ] Revisionssicherheit

Wichtige Funktionen:
- [ ] Intake-Management
- [ ] automatische Vorpruefung
- [ ] N-1-Auflagen-Generator
- [ ] Rollen/Rechte
- [ ] Audit-Trail
- [ ] internes Dashboard

## Monetarisierungsideen

### Paket 1: Project Developer

Fuer Projektierer.

Moegliche Features:
- [ ] Standortcheck
- [ ] Netzebenen-Vorschlag
- [ ] Anschlusskandidaten
- [ ] Bedingungsdiagnose
- [ ] PDF-Export
- [ ] einfache Kostenbandbreite

Moegliche Preise:
- [ ] 499-1.490 EUR/Monat
- [ ] oder 99-490 EUR pro Analyse

### Paket 2: Storage / Investment Intelligence

Fuer Speicherparkbetreiber, Betreiber und Investoren.

Moegliche Features:
- [ ] alle Developer-Funktionen
- [ ] CAPEX-/Timeline-/Risiko-Modell
- [ ] Szenariorechnungen
- [ ] Portfoliovergleich
- [ ] Management-Report
- [ ] Regionenranking

Moegliche Preise:
- [ ] 2.500-10.000 EUR/Monat
- [ ] oder 5.000-25.000 EUR pro Projekt-/Portfolioanalyse

### Paket 3: Grid Operator Suite

Fuer Netzbetreiber.

Moegliche Features:
- [ ] Intake-Management
- [ ] automatische Vorpruefung
- [ ] Priorisierung
- [ ] Fallakte
- [ ] Audit-Trail
- [ ] Rollen/Rechte
- [ ] Schnittstellen
- [ ] internes Dashboard

Moegliche Preise:
- [ ] Setup: 15.000-100.000 EUR
- [ ] Lizenz: 30.000-200.000 EUR+ pro Jahr
- [ ] Support/SLA zusaetzlich

### Umsetzungsstand (konkretisiert)

- [x] Paketstruktur und Scope-Grenzen in `docs/monetarisierungspakete.md` dokumentiert.
- [ ] Feature-Mapping in konkrete Tickets mit Akzeptanzkriterien ueberfuehren.
- [ ] Preisannahmen je Zielsegment in Vertriebshypothesen testen.

## Zusaetzliche Umsatzhebel

- [ ] API-Zugriff
- [ ] White-Label-Version
- [ ] Premium-Reports
- [ ] regionale Exklusivitaet
- [ ] historische Entwicklung und Trends
- [ ] Monitoring von Netzausbau-Massnahmen
- [ ] Team-Schulungen
- [ ] Upload eigener Projektdaten
- [ ] CRM-/GIS-Integrationen
- [ ] individuelle Standortanalysen
- [ ] Portfolio-Screenings
- [ ] Marktberichte
- [ ] Netzanschluss-Heatmaps
- [ ] Anschlusskosten-Benchmarking

## Spaetere Folgeideen (nicht aktueller Sprint)

Diese Punkte sind bewusst **nicht** Teil des aktuellen Sprints und dienen nur als strukturierter Spaeter-Backlog fuer den aktuellen Themenblock.

### Mobile / Vor-Ort-Erfassung

- [ ] PWA-Setup fuer mobile Homescreen- und Install-Nutzung vorbereiten.
- [ ] MVP-Idee: Vor-Ort-Trafo- und Umspannwerk-Marker direkt in der Karte erfassen.
- [ ] GPS-, Kamera- und Foto-Upload fuer Feldbegehungen vorsehen.
- [ ] Spaeter: OCR fuer Typenschilder und andere Foto-Metadaten pruefen.

### Community- und Grid-Scout-Daten

- [ ] Crowdsourced Grid Data / "Grid Scout" als spaeteres Community-Modul pruefen.
- [ ] Trust-Level fuer Community-Hinweise fuehren: unverified, confirmed, verified.
- [ ] Community-Daten immer klar von offiziellen Quellen trennen und nicht als verifizierte Netzkapazitaet darstellen.
- [ ] Gamification / Level-System nur als spaeteren Motivationslayer betrachten, nicht als MVP-Bestandteil.
- [ ] Community-Datenzugriff oder erweiterte Scout-Daten als Premium-Funktion pruefen.

### Validierung / Operations

- [ ] VNB-Validierungs-Dashboard fuer Sichtung, Freigabe und Nachpflege externer/community-basierter Daten vorsehen.
- [ ] Workflow fuer spaetere manuelle Verifikation von Fotos, Standort-Hinweisen und Asset-Meldungen definieren.

### Monetarisierung / Datenprodukte

- [ ] Datenverkauf und API-Zugriff fuer aggregierte oder validierte Grid-Daten spaeter bewerten.
- [ ] Pruefen, welche Datenprodukte als Premium-, API- oder B2B-Modul vermarktbar sind.

### Recht / Datenschutz

- [ ] Rechtliche und DSGVO-Hinweise fuer Standortdaten, Fotos, Uploads und Community-Beitraege frueh mitdenken.
- [ ] Einwilligung, Rechte an Uploads, sensible Infrastrukturdaten und Loesch-/Pruefprozesse spaeter konkretisieren.

## Abarbeitungsmodus (Vorschlag)

- [ ] Ideen regelmaessig priorisieren (Impact x Umsetzbarkeit).
- [ ] Je Sprint 1-3 Punkte aus dieser Liste fix einplanen.
- [ ] Jede erledigte Idee mit Datum und kurzem Ergebnis dokumentieren.
- [ ] Offene Punkte in konkrete Tickets mit Akzeptanzkriterien ueberfuehren.
