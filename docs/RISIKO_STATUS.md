# RISIKO_STATUS.md - GridCheck Pre-Netzanschluss-Check App
# Erstellt: 2026-05-16 | Quelle: Testergebnis App (Projektierer, Investor, Netzbetreiber Review)
# Status: LEBENDES DOKUMENT - bei jedem Meilenstein aktualisieren

---

## 1. GESAMTBEWERTUNG (Stand: 2026-05-16)

| Bereich                            | Status          | Prioritaet  |
|------------------------------------|-----------------|-------------|
| Backend-Engine (Berechnung, N-1)   | PRODUKTIONSREIF | -           |
| Auth, Rollen, Billing Backend      | FERTIG          | -           |
| PDF-Reports (3 Stakeholder)        | IMPLEMENTIERT   | -           |
| Frontend UI                        | VORHANDEN       | -           |
| Frontend <-> Backend Integration   | OFFEN           | KRITISCH    |
| Deployment produktiv               | INSTABIL        | KRITISCH    |
| Mock-Daten entfernt                | OFFEN           | KRITISCH    |
| Echte GIS-/Netzdaten               | FEHLEN          | KRITISCH    |
| KI-Lernmodul aktiv/trainiert       | GRUNDGERUEST    | MITTEL      |
| Disclaimer / Haftung Frontend      | FEHLT           | KRITISCH    |
| Pilotmodell definiert              | FEHLT           | KRITISCH    |

---

## 2. KRITISCHE RISIKEN (sofort beheben)

### R-01 - Frontend <-> Backend nicht verbunden
- Wirkung: Kaufentscheidung blockiert. Alle Ergebnisse sind Mock-Daten.
- Gefahr: Vertrauensverlust bei erster Live-Demo.
- Massnahme: API-Integration priorisieren. Mock-Daten als [DEMO] markieren.
- Status: OFFEN

### R-02 - Deployment instabil
- Wirkung: Keine produktive Demo moeglich.
- Massnahme: Railway + Vercel stabilisieren. Health-Checks einrichten.
- Status: OFFEN

### R-03 - Disclaimer / Haftungsausschluss fehlt im Frontend
- Wirkung: Rechtliches Risiko. Missverstaendnis: App = verbindliche Netzpruefung.
- Pflichttext (Frontend + PDF + API-Response):
  "Diese Bewertung ist eine technische Vorpruefung auf Basis der angegebenen
   Daten und Modellannahmen. Sie ersetzt keine verbindliche Netzanschlusspruefung
   durch den zustaendigen Netzbetreiber. Berechnete Werte, insbesondere
   Kapazitaeten und Kosten, sind Indikatoren, keine Zusagen."
- Status: OFFEN

### R-04 - PLZ -> Netzbetreiber-Zuordnung fehlt
- Wirkung: NAP-Ermittlung bleibt rein heuristisch.
- Massnahme: Mindest-Mapping PLZ -> VNB aufbauen.
- Status: OFFEN

### R-05 - Scheingenauigkeit bei Ausgabewerten
- Wirkung: Nutzer interpretiert z.B. "7,42 MW" als verbindlich.
- Massnahme: Alle Ausgaben als Bandbreiten. Niemals Punktwerte ohne Confidence.
- Regel: Statt "7,42 MW" -> "ca. 5-8 MW (Datenqualitaet: mittel, +-30%)"
- Status: TEILWEISE UMGESETZT (Engine), OFFEN (Frontend)

---

## 3. MITTLERE RISIKEN (vor Marktstart beheben)

### R-06 - N-1-Methodik nicht transparent dokumentiert
- Wirkung: Netzbetreiber und Projektierer zweifeln an Aussagekraft.
- Massnahme: N-1-Klassifikation einfuehren (siehe Abschnitt 13).
- Status: OFFEN

### R-07 - KI-Modul kommuniziert staerker als es ist
- Wirkung: Uebersprechen. Investoren und Netzbetreiber skeptisch.
- Massnahme: KI immer als "unterstuetzend / assoziativ" kennzeichnen.
- Status: OFFEN

### R-08 - Fehlende GIS-/Netzdatenpipeline
- Wirkung: NAP-Ermittlung spekulativ. Kaufwahrscheinlichkeit bei 55% statt 85%.
- Massnahme: Datenpipeline als eigener Meilenstein. Interim: OSM-Layer.
- Status: GEPLANT

### R-09 - Szenarienvergleich im UI fehlt
- Wirkung: Portfoliofunktion nicht nutzbar.
- Massnahme: Varianten-Feature als dediziertes UI-Modul.
- Status: GEPLANT (Phase 3)

### R-10 - Security-/Compliance-Dokumentation fehlt
- Wirkung: Enterprise-Einkauf blockiert. Procurement-Gate nicht passierbar.
- Massnahme: Security-Onepager, AVV/DPA, Hosting-Konzept, Datenloesch-Konzept.
- Status: OFFEN

---

## 4. BEKANNTE TECHNISCHE SCHWACHSTELLEN

| Schwachstelle                        | Risiko             | Status        |
|--------------------------------------|--------------------|---------------|
| JSON nicht atomar geschrieben        | Race Condition     | OFFEN         |
| Felder unvollstaendig (scores/trafo) | Audit-Luecke       | OFFEN         |
| Verify-Endpoint /revision/verify     | Revisionssicherheit| IMPLEMENTIERT |
| page.tsx duplizierter Code           | Runtime-Fehler     | PRUEFEN       |
| Auth Frontend-Integration            | Zugriffskontrolle  | PRUEFEN       |

---

## 5. VERBOTENE AUSSAGEN (RED FLAG - im Code-Review blockieren)

Die App darf NIEMALS sagen:
- "Der Netzanschluss ist moeglich."
- "Netzbetreiber wird zustimmen."
- "Freie Kapazitaet betraegt exakt X MW."
- "Dies ist der optimale Netzanschlusspunkt."
- "N-1 ist erfuellt wie beim Netzbetreiber."
- "Keine Netzverstaerkung erforderlich."
- "Kosten betragen exakt X Euro."
- "KI hat die beste Loesung ermittelt."
- "Deployment ist enterprise-ready." (solange instabil)
- "Produktionsreife Reports." (solange PDF nicht final)

---

## 6. PFLICHT-DISCLAIMER (in JEDE Ausgabe - Frontend + PDF + API)

VORLAEUFIGE TECHNISCHE ANALYSE - KEINE VERBINDLICHE NETZZUSAGE

Diese Bewertung basiert auf den eingegebenen Daten und Modellannahmen
(Engine-Version: X.X.X, Stand: DATUM, Confidence: XX%).
Fehlende Netzdaten wurden durch konservative Annahmen ersetzt.
N-1-Bewertung: Level [0-3 angeben].
Offizielle Netzanschlusspruefung durch den zustaendigen Netzbetreiber
bleibt zwingend erforderlich.
Report-ID: [AUDIT-ID] | Input-Hash: [HASH] | Output-Hash: [HASH]

---

## 7. TRENDKONSISTENZ-REGELN (Modellfehler-Erkennung)

Die Engine MUSS diese physikalischen Regeln einhalten.
Verletzung = harter Modellfehler -> Test schreiben + blockieren.

| Eingabe-Aenderung              | Erwartete Reaktion                          |
|--------------------------------|---------------------------------------------|
| Leistung steigt                | Risiko-Score darf nicht sinken              |
| Entfernung zum NAP steigt      | Spannungs-/Thermikrisiko steigt             |
| Kleinerer Leitungsquerschnitt  | Risiko steigt                               |
| Trafoauslastung hoeher         | Anschlussreserve sinkt                      |
| Datenqualitaet schlechter      | Confidence-Level sinkt                      |
| N-1-Pfad fehlt                 | N-1-Risiko-Score steigt                     |
| Hoehere Netzebene verfuegbar   | Techn. Risiko kann sinken, Kosten steigen   |
| BESS-Dynamik hoeher            | Betriebs-/Schutzrisiko steigt               |

---

## 8. KAUFWAHRSCHEINLICHKEITEN (Baseline, Stand: 2026-05-16)

| Kundentyp                | Jetzt | Nach Live-Integration | Nach GIS-Daten |
|--------------------------|-------|-----------------------|----------------|
| PV-/BESS-Projektierer    | 55%   | 75%                   | 85%            |
| Leiter Projektentwicklung| 50%   | 70%                   | 85%            |
| Technischer Vertrieb     | 60%   | 75%                   | 80%            |
| Operativer Nutzer        | 40%   | 65%                   | 75%            |
| Investor / Asset Owner   | 45%   | 65%                   | 80%            |
| Netzbetreiber            | 30%   | 50%                   | 70%            |

---

## 9. PILOTWAHRSCHEINLICHKEITEN

| Kundentyp                     | Jetzt | Nach stabiler Live-Demo |
|-------------------------------|-------|-------------------------|
| Kleiner Projektentwickler     | 60%   | 80%                     |
| Mittelgrosser Projektentwickler| 55%  | 75%                     |
| Grosser Projektentwickler     | 40%   | 65%                     |
| Netzbetreiber                 | 25%   | 50%                     |
| Strategischer Investor        | 50%   | 70%                     |
| Enterprise-Kunde              | 30%   | 60%                     |

---

## 10. PRICING-HYPOTHESEN (zu validieren)

### Pilotmodelle
| Paket       | Umfang               | Laufzeit | Preis         |
|-------------|----------------------|----------|---------------|
| Pilot Basic | 20 Checks, 1 Team    | 30 Tage  | 2.500-5.000 EUR|
| Pilot Pro   | 50 Checks, Multi-User| 60 Tage  | 7.500-15.000 EUR|

### SaaS-Pakete (nach Pilot)
| Paket         | Zielkunde             | Preis/Monat          |
|---------------|-----------------------|----------------------|
| Starter       | Kleine Projektierer   | 299-799 EUR          |
| Professional  | Projektentwickler     | 1.000-3.000 EUR      |
| Enterprise    | Grosse Teams          | 15.000-75.000 EUR/Jahr|
| API/White Label| Partner/Plattformen  | individuell          |

Zahlungsbereitschaft Netzbetreiber: 6-stellig/Jahr moeglich bei Enterprise-Lizenz.

---

## 11. MVP-CHECKLISTE (vor erstem Kundenpilot)

- [ ] Frontend <-> Backend live verbunden
- [ ] Mock-Daten entfernt oder als [DEMO] markiert
- [ ] Deployment stabil (Railway + Vercel)
- [ ] PDF-Report produktionsreif exportierbar
- [ ] Disclaimer sichtbar im Frontend + PDF + API
- [ ] Confidence-Level prominent angezeigt
- [ ] Jede Eingabe mit Quelle markiert (User / Default / Modell)
- [ ] 3 Beispiel-Demo-Cases vorbereitet:
  - [ ] PV 5 MW, MS, machbar mit Auflagen
  - [ ] BESS 10 MW, grenzwertig (N-1/Trafo)
  - [ ] No-Go-Standort (Thermik/Spannungsfall)
- [ ] Pilotangebot schriftlich definiert
- [ ] ROI-Onepager erstellt
- [ ] Security-Onepager erstellt

---

## 12. SALES-DEMO ANFORDERUNGEN (5-Minuten-Pflicht)

Die Demo muss in unter 5 Minuten zeigen:
1. Standort eingeben
2. Anlagenart + Leistung waehlen
3. Ergebnis erhalten
4. Risiken sehen
5. Massnahmen sehen
6. PDF exportieren
7. Audit-ID zeigen

---

## 13. N-1 KLASSIFIKATIONSSYSTEM (verpflichtend in jedem Report)

| Level | Bezeichnung       | Bedeutung                                    |
|-------|-------------------|----------------------------------------------|
| 0     | Nicht beurteilbar | Topologie unbekannt, keine Aussage moeglich  |
| 1     | Heuristisch       | Topologie-Typ bekannt (Stich/Ring/vermascht) |
| 2     | Modelliert        | Vereinfachter Lastfluss im Ersatzfall        |
| 3     | Verifiziert       | Echte Netzbetreiberdaten verwendet           |

---

## 14. ERGEBNISKLASSIFIKATION (Belastbarkeit je Ausgabetyp)

| Ergebnisart                   | Belastbarkeit                                    |
|-------------------------------|--------------------------------------------------|
| Eingabedaten vollstaendig?    | belastbar                                        |
| Berechnung reproduzierbar     | belastbar (Hash)                                 |
| Plausibilitaetsfehler Eingabe | belastbar                                        |
| Lastfluss im Modell           | belastbar innerhalb Modellgrenzen                |
| Thermische Auslastung         | indikativ bis belastbar (abh. von Betriebsdaten) |
| Trafoauslastung               | indikativ (ohne reale Last)                      |
| Spannungsbandverletzung       | indikativ bis belastbar                          |
| Kurzschlussbeitrag            | indikativ (ohne echte Sk-Daten begrenzt)         |
| N-1-Ergebnis                  | indikativ (Level 1-2), belastbar (Level 3)       |
| Netzebene                     | indikativ                                        |
| NAP-Vorschlag                 | indikativ bis spekulativ                         |
| Freie Netzkapazitaet          | spekulativ ohne Netzbetreiberdaten               |
| Kostenabschaetzung            | spekulativ (Bandbreite)                          |
| Netzbetreiberentscheidung     | NICHT ZULAESSIG                                  |
| KI-Empfehlung                 | unterstuetzend / assoziativ                      |

---

## 15. CHANGELOG DIESES DOKUMENTS

| Datum      | Aenderung                                           | Autor  |
|------------|-----------------------------------------------------|--------|
| 2026-05-16 | Initiale Erstellung aus Testergebnis-Review         | System |
| 2026-05-16 | Abschnitte 4-7 + 14-15 ergaenzt (vollstaendige Fassung) | System |

