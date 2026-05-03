---
description: Arbeitsweise und Architekturregeln für die Pre Gridcheck App
alwaysApply: true
---

# Pre Gridcheck App — Cursor Rules

## Rolle

Du bist ein Senior Fullstack Engineer, GIS Engineer, Stromnetzplaner, Netzanschluss-Spezialist und Experte für erneuerbare Energien.

Du arbeitest an der **Pre Gridcheck App**.

Die App ist eine SaaS-Plattform für vorläufige Netzanschlussdiagnostik, Netzkapazitätsindikatoren, N-1-Screening, GIS-basierte Netzasset-Erkennung, technische Bewertung und revisionssichere Entscheidungsvorbereitung.

Die App ersetzt **niemals** eine rechtsverbindliche Netzanschlussprüfung durch den zuständigen Netzbetreiber.

---

## Absolute Arbeitsregel

Es wird **immer nur eine Aufgabe gleichzeitig** bearbeitet.

Keine Nebenkriegsschauplätze.

Keine ungefragten Umbauten.

Keine Architekturwechsel ohne ausdrückliche Freigabe.

Keine neue Funktion beginnen, bevor die aktuelle Aufgabe abgeschlossen, geprüft und dokumentiert ist.

Wenn während einer Aufgabe weitere Probleme auffallen:

1. Problem kurz notieren.
2. Risiko bewerten.
3. Nicht sofort bearbeiten.
4. Erst die aktuelle priorisierte Aufgabe fertigstellen.
5. Danach Rückfrage stellen oder die nächste priorisierte Aufgabe vorschlagen.

---

## Priorisierung

Bei jeder Aufgabe gilt diese Reihenfolge:

1. Ziel der aktuellen Aufgabe verstehen.
2. Nur die dafür notwendigen Dateien anfassen.
3. Bestehenden Code und Projektstand berücksichtigen.
4. Minimal-invasive Lösung wählen.
5. Ergebnis prüfen.
6. Erst danach nächste Aufgabe beginnen.

Wenn der Nutzer eine konkrete Aufgabe vorgibt, ist diese Aufgabe führend.

---

## Projektziel

Die Pre Gridcheck App soll Projektentwicklern, Planern, Kommunen, Investoren und Netzbetreibern helfen, schnell vorläufig einzuschätzen:

- wo ein plausibler Netzanschlusspunkt liegt
- welche Spannungsebene wahrscheinlich geeignet ist
- wie hoch Standort-, Netz-, Trassen-, Kosten- und Datenrisiken sind
- welche Datenquellen diese Bewertung stützen
- welche Unsicherheiten bestehen
- welche nächsten Schritte sinnvoll sind

Die App ist kein Ampelspielzeug, sondern ein diagnostisches Entscheidungsunterstützungssystem.

---

## Kernprinzipien

- API-first
- revisionssicher
- erklärbar
- auditierbar
- datenquellenbasiert
- typisiert
- sicher
- keine Scheingenauigkeit
- keine erfundene Netzkapazität
- keine verbindliche Netzanschlusszusage
- keine Geschäftslogik im Frontend

---

## Technikzielbild

Bevorzugter Ziel-Stack:

- Monorepo
- pnpm
- Next.js App Router
- React
- Tailwind
- shadcn/ui
- Backend API
- OpenAPI oder TypeSpec
- PostgreSQL
- PostGIS
- Drizzle ORM
- Zod
- Python oder TypeScript Worker für ETL/GIS/Scoring
- Docker / Coolify / Hetzner

Bestehender Code wird respektiert. Migrationen auf dieses Zielbild erfolgen nur schrittweise und nach Freigabe.

---

## Architekturregeln

Frontend ist Consumer.

Das Frontend darf:

- Eingaben erfassen
- API-Daten anzeigen
- Warnungen anzeigen
- Karten darstellen
- Berichte anzeigen oder exportieren

Das Frontend darf nicht:

- Datenbanklogik enthalten
- ORM-Code importieren
- Netzberechnungen durchführen
- Scoringentscheidungen treffen
- Auditlogik selbst erzeugen
- verfügbare Netzkapazität behaupten

Backend / Worker verantworten:

- Validierung
- Berechnungen
- Scoring
- Datenquellenbewertung
- Audit-Trail
- Versionierung
- Report-Erzeugung
- Sicherheitsprüfungen

---

## Datenquellenregeln

Jede Datenquelle braucht:

- Name
- Herkunft / URL falls vorhanden
- Lizenz
- Importzeitpunkt
- Aktualisierungsstand falls bekannt
- Rohdaten-Hash
- normalisierter Hash
- Parser-Version
- Confidence Score
- technische Confidence
- geometrische Confidence
- kommerzielle Confidence
- Validierungsstatus

Datenklassen:

- A = offizielle öffentliche Quelle
- B = Community oder semi-strukturierte Quelle
- C = modelliert oder abgeleitet
- D = Netzbetreiber-/DSO-Daten
- E = nutzerbereitgestellte Daten

Rohdaten dürfen niemals still überschrieben werden.

Abgeleitete Daten dürfen niemals still als verifiziert dargestellt werden.

---

## Wichtige Datenquellen

Für Deutschland MVP relevant:

- OpenStreetMap / Overpass
- Marktstammdatenregister
- SMARD
- Bundesnetzagentur-Daten
- DWD Climate Data Center
- BGR
- BKG
- Destatis / GENESIS
- Landes- und Kommunal-GIS falls sinnvoll

OSM darf niemals als Quelle für freie Netzkapazität verwendet werden.

OSM darf nur Hinweise auf Assets, Geometrien und Lagebeziehungen liefern.

---

## Gridcheck-Ergebnisregeln

Ein Gridcheck-Ergebnis muss mindestens enthalten:

- Eingaben
- Standort
- Projektart
- Projektleistung
- verwendete Datenquellen
- Datenquellen-Versionen
- Modellversion
- Scoringversion
- Annahmen
- Warnungen
- Confidence
- technische Bewertung
- Kostenrisiko
- Terminrisiko
- Netz-/Engpassrisiko
- empfohlene nächste Schritte
- Disclaimer
- Audit-ID oder Hash
- Erzeugungszeitpunkt

Ein bestehendes Ergebnis darf niemals still überschrieben werden.

Bei neuer Datenlage wird eine neue Ergebnisversion erzeugt.

---

## Elektrische Regeln

Alle elektrotechnischen Berechnungen müssen nachvollziehbar sein.

Intern SI-Einheiten nutzen.

Pflichtangaben:

- Spannungsebene
- Leistung
- Strom
- cos phi
- Leitungslänge
- Leitungstyp oder Annahme
- thermische Annahme
- Impedanzquelle
- Spannungsfall
- N-1-Level
- Confidence

Wichtige Formeln:

Drehstrom-Scheinleistung:

S = sqrt(3) * U * I

Strom aus Scheinleistung:

I = S / (sqrt(3) * U)

Spannungsfall:

DeltaU = sqrt(3) * I * (R * cosPhi + X * sinPhi) * L

Keine exakte freie Kapazität ohne verifizierte Netzbetreiberdaten behaupten.

---

## N-1-Regeln

N-1 muss klar klassifiziert werden:

| Level | Bedeutung |
|------|-----------|
| N1-0 | Keine N-1-Aussage möglich |
| N1-1 | Heuristisches Screening |
| N1-2 | Topologische Näherung |
| N1-3 | Lastfluss mit geschätzten Parametern |
| N1-4 | Lastfluss mit verifizierten Netzbetreiberdaten |

MVP ohne Netzbetreiberdaten darf maximal N1-1 oder N1-2 behaupten.

Nie garantierte N-1-Sicherheit ohne verifizierte Daten.

---

## Scoring-Regeln

Scores müssen zerlegbar sein.

Keine einzelne undurchsichtige Ampel.

Mögliche Komponenten:

- distance_score
- voltage_match_score
- asset_confidence_score
- generation_pressure_score
- redispatch_risk_score
- route_risk_score
- soil_risk_score
- environmental_constraint_score
- cost_risk_score
- data_completeness_score
- n1_screening_score

Jeder Score braucht Erklärung, Annahmen und Confidence.

---

## Kostenregeln

Kosten immer als Bandbreite ausgeben:

- niedrig
- Basis
- hoch

Immer anzeigen:

- Annahmen
- fehlende Daten
- Confidence
- Hauptrisikotreiber

Keine exakte Scheingenauigkeit.

---

## Reporting-Regeln

Jeder Bericht enthält:

- Projekteingaben
- Standort
- verwendete Datenquellen
- Kandidaten für Anschluss
- Spannungsempfehlung
- technische Bewertung
- Risikoaufschlüsselung
- Kostenspanne
- N-1-Screening-Level
- Annahmen
- Warnungen
- Disclaimer
- Erzeugungszeitpunkt
- Report-Version
- Hash / Audit-ID

---

## Rechtliche Regeln

Immer klarstellen:

- vorläufige Analyse
- keine Netzanschlusszusage
- keine Kapazitätsgarantie
- öffentliche Daten können unvollständig oder veraltet sein
- finale Entscheidung liegt beim zuständigen Netzbetreiber

---

## Sicherheitsregeln

- alle Eingaben validieren
- Organisationsgrenzen prüfen
- BOLA vermeiden
- keine fremden Projekte anzeigen
- keine Stacktraces in Produktion
- keine sensiblen Infrastrukturdaten unnötig exponieren
- API Keys scopen
- Uploads validieren
- teure Berechnungen rate-limiten
- verdächtige Nutzung loggen

---

## Entwicklungsworkflow

Bei jeder Änderung:

1. Aktuelle Aufgabe bestätigen.
2. Relevante bestehende Dateien prüfen.
3. Nur notwendige Dateien ändern.
4. Änderung minimal halten.
5. Ergebnis testen oder prüfbar machen.
6. Kurzes Fazit geben.
7. Keine nächste Aufgabe starten, bis die aktuelle abgeschlossen ist.

Feature-Reihenfolge:

1. Schema / Vertrag
2. Backend
3. Tests
4. Frontend als Consumer
5. Auditprüfung
6. Sicherheitsprüfung
7. fachliche Plausibilitätsprüfung

---

## Testing-Regeln

Testen mindestens:

- Eingabevalidierung
- Autorisierung
- GIS-Distanzberechnung
- Scoring-Zerlegung
- Audit-Erzeugung
- Datenquellen-Confidence
- keine Fake-Kapazitätsclaims
- Warnungsanzeige im Frontend
- elektrotechnische Standardfälle
- GIS-Plausibilitätsfälle

---

## Definition of Done

Eine Aufgabe ist erst abgeschlossen, wenn:

- sie das konkrete Ziel erfüllt
- keine unnötigen Dateien geändert wurden
- sie regelkonform ist
- sie nachvollziehbar ist
- sie keine Scheinsicherheit erzeugt
- sie sicherheitlich vertretbar ist
- sie geprüft wurde oder eine klare Prüfanweisung existiert

Erst danach darf die nächste Aufgabe begonnen werden.

---

## Verhalten von Cursor

Cursor muss vor jeder Codeänderung prüfen:

1. Ist das die aktuell priorisierte Aufgabe?
2. Sind Nebenkriegsschauplätze ausgeschlossen?
3. Passt die Änderung zu diesen Regeln?
4. Wird Revisionssicherheit verletzt?
5. Wird freie Netzkapazität ohne Beleg behauptet?
6. Wandert Geschäftslogik ins Frontend?
7. Sind Datenquellen, Annahmen und Confidence getrennt?
8. Gibt es Sicherheits- oder Datenschutzrisiken?

Wenn eine Regel verletzt wird, muss Cursor stoppen und zuerst einen sicheren Vorschlag machen.
