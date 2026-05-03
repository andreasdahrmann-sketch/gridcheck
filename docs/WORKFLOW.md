# Workflow für die Pre Gridcheck App

## Wichtigste Arbeitsregel

Es wird immer nur eine Aufgabe gleichzeitig bearbeitet.

Erst wenn eine Aufgabe abgeschlossen, geprüft und dokumentiert ist, wird mit der nächsten Aufgabe begonnen.

Keine Nebenkriegsschauplätze.

Keine ungefragten Zusatzumbauten.

Wenn zusätzliche Probleme auffallen, werden sie notiert, aber nicht sofort bearbeitet.

---

## Standardablauf pro Aufgabe

1. Aufgabe verstehen
2. Priorität bestätigen
3. Betroffene Dateien identifizieren
4. Minimal-invasive Lösung umsetzen
5. Ergebnis prüfen
6. Kurz dokumentieren
7. Erst danach nächste Aufgabe beginnen

---

## Definition of Done

Eine Aufgabe ist erst fertig, wenn:

- das konkrete Ziel erfüllt ist
- keine unnötigen Dateien geändert wurden
- die Änderung zu PROJECT_RULES.md passt
- die Änderung zu .cursorrules passt
- Revisionssicherheit nicht verletzt wird
- keine falsche Netzkapazität behauptet wird
- keine Geschäftslogik unnötig ins Frontend wandert
- Prüfung oder Test durchgeführt wurde oder klar beschrieben ist

---

## Pflicht vor jeder größeren Änderung

Cursor muss prüfen:

- Ist das wirklich die aktuelle Aufgabe?
- Muss diese Datei wirklich geändert werden?
- Gibt es eine einfachere Lösung?
- Entsteht ein Sicherheitsproblem?
- Entsteht eine falsche fachliche Aussage?
- Bleibt das Ergebnis auditierbar?

---

## Umgang mit neuen Problemen

Wenn während der Arbeit ein neues Problem auffällt:

1. Nicht sofort bearbeiten.
2. Kurz notieren.
3. Risiko einschätzen.
4. Aktuelle Aufgabe beenden.
5. Danach Rückfrage stellen.

---

## Gridcheck-Fachregeln

Die App darf niemals eine verbindliche Netzanschlusszusage erzeugen.

OSM darf niemals als Quelle für freie Netzkapazität verwendet werden.

Gridcheck-Ergebnisse müssen versioniert, erklärbar und auditierbar sein.

N-1-Aussagen müssen klassifiziert werden.

Kosten dürfen nur als Bandbreite angegeben werden.

Jede Datenquelle braucht Herkunft, Lizenz, Stand, Hash und Confidence.

---

## Frontend-Regel

Frontend ist Consumer.

Berechnungen, Scoring, Auditlogik und Datenquellenbewertung gehören nicht ins Frontend.

---

## Backend-Regel

Backend und Worker verantworten:

- Validierung
- Berechnung
- Scoring
- Audit
- Datenquellenlogik
- Reportlogik
- Sicherheit
