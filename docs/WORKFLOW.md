# Pre Gridcheck App - Working Workflow

## Standardablauf fuer jede neue Aufgabe

1. Projektregeln lesen: .cursorrules, PROJECT_RULES.md und docs/WORKFLOW.md.
2. Ziel der Aufgabe klaeren.
3. Bestehende Dateien und Abhaengigkeiten pruefen.
4. Kleine, saubere Aenderung umsetzen.
5. Ergebnis auf Funktion, Konsistenz, Sicherheit und Revisionssicherheit pruefen.
6. Kurze Zusammenfassung und naechste Schritte dokumentieren.
7. Nach Meilenstein Git-Commit erstellen.

## Standardpruefung vor Code

- Passt die Aenderung zur Architektur?
- Wird Geschaeftslogik korrekt im Backend/Domain-Layer umgesetzt?
- Werden GIS, Netzmodell und Bewertungslogik getrennt?
- Ist die Analyse spaeter auditierbar?
- Werden Quellen, Annahmen und Unsicherheiten gespeichert?
- Gibt es Konflikte mit bestehendem Code?

## Standardpruefung nach Code

- Laeuft der Build?
- Sind Imports korrekt?
- Sind Typen korrekt?
- Sind Fehlerfaelle beruecksichtigt?
- Gibt es Sicherheitsrisiken?
- Ist das Ergebnis fuer Nutzer verstaendlich?

## Git-Regel

Nach jedem abgeschlossenen Meilenstein:

git add .
git commit -m 'meaningful commit message'

## Cursor-Prompt fuer neue Aufgaben

Lies zuerst .cursorrules, PROJECT_RULES.md und docs/WORKFLOW.md.
Arbeite regelkonform, pruefe bestehende Dateien und gib keine ungetesteten Annahmen als Fakten aus.
Setze die naechste Aufgabe klein, sauber und revisionssicher um.
