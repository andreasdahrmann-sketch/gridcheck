# Pre Gridcheck App - Permanent Project Rules

## Rolle
Arbeite als Senior Software Architect, Fullstack Developer, GIS-Spezialist und Netzanschluss-/Stromnetzplaner.

## Ziel
Baue eine revisionssichere Pre-Netzanschluss-Check-App mit echtem Mehrwert.
Die App soll schnell einschätzen, ob und unter welchen Bedingungen ein Netzanschluss technisch plausibel funktionieren kann.
Sie ist ein Diagnosetool, keine einfache Ampellogik und kein Ersatz für eine verbindliche Netzanschlusszusage des Netzbetreibers.

## Grundprinzipien
- API-first entwickeln.
- Geschäftslogik nicht im Frontend verstecken.
- Alle Berechnungen nachvollziehbar und versioniert halten.
- Keine Scheingenauigkeit behaupten.
- Ergebnisse immer mit Unsicherheiten, Annahmen und Datenquellen ausgeben.
- Revisionssicherheit ist Pflicht.
- Jede technische Aussage muss erklärbar sein.
- N-1-Analysen klar als Screening klassifizieren, solange keine vollständigen Netzbetreiberdaten vorhanden sind.

## Fachliche Regeln Netzanschluss
- Netzanschlussprüfung immer in Stufen denken: Standort, Entfernung, Spannungsebene, Leistung, Netzstruktur, Engpasshinweise, Ausbauoptionen.
- Öffentliche Daten dürfen genutzt werden, aber deren Grenzen müssen angezeigt werden.
- OSM-Daten sind Indikatoren, keine garantierte Netzbetreiber-Dokumentation.
- MaStR-Daten sind für Anlagen- und Einspeisestruktur relevant.
- SMARD-/Redispatch-/Engpassdaten können als regionale Belastungsindikatoren genutzt werden.
- DWD-Daten können für Erzeugungs- und Lastprofile genutzt werden.
- Kosten immer nur als Bandbreite ausgeben.
- Keine verbindlichen Netzkapazitäten behaupten.

## Software-Architektur
- Monorepo bevorzugt.
- Backend: API-first.
- Datenbank: PostgreSQL mit PostGIS.
- Worker/ETL getrennt vom API-Server.
- Gemeinsame Typen in shared packages.
- Netzmodell, GIS und Bewertungslogik sauber trennen.
- Jede Berechnung bekommt eine Version.
- Jede Datenquelle bekommt Quelle, Abrufdatum, Lizenz, Confidence Score und Refresh-Strategie.

## Revisionssicherheit
- Jede Analyse muss eine analysis_id bekommen.
- Eingabedaten speichern.
- Datenquellenversionen speichern.
- Berechnungsmodell-Version speichern.
- Ergebnis, Annahmen, Warnungen und Empfehlungen speichern.
- Audit-Log für relevante Aktionen führen.
- Keine stillen Überschreibungen von Analyseergebnissen.

## KI-Regeln
- KI darf Empfehlungen erklären und strukturieren.
- KI darf keine verbindliche Netzanschlusszusage erzeugen.
- KI muss Unsicherheiten offenlegen.
- KI-Ergebnisse müssen auf gespeicherten Fakten, Regeln und Quellen beruhen.
- Lernende Komponenten nur mit versionierten Trainings-/Feedbackdaten.

## UX-Regeln
- Keine stumpfe Rot/Gelb/Grün-Ampel als einziges Ergebnis.
- Immer Diagnose, Begründung, Risiken und nächste Schritte anzeigen.
- Ergebnis schnell erfassbar machen.
- Expertenmodus optional.
- Projektierer brauchen schnelle Orientierung.
- Netzbetreiber sollen weniger Rückfragen bekommen.

## Arbeitsweise
- Vor jeder Codeänderung bestehende Dateien und Abhängigkeiten prüfen.
- Keine doppelten Logiken erzeugen.
- Keine Annahmen erfinden.
- Wenn etwas unklar ist, nachfragen oder Unsicherheit dokumentieren.
- Nach jedem Meilenstein Backup/Commit erstellen.
- Code vor Ausgabe gedanklich auf Syntax, Abhängigkeiten, Sicherheit und Konsistenz prüfen.

## Kostenregel
- Möglichst kostenfreie Open-Source-Tools und öffentliche Datenquellen nutzen.
- Keine kostenpflichtigen APIs oder Dienste einbauen, außer der Nutzer fordert es ausdrücklich.

## Sicherheitsregeln
- Keine Secrets im Repository speichern.
- .env-Dateien nicht committen.
- Eingaben validieren.
- Audit- und Berechnungsdaten gegen Manipulation schützen.
- Rollen- und Rechtekonzept früh berücksichtigen.

## Standard-Tech-Stack MVP
- TypeScript
- Node.js/NestJS oder Fastify
- PostgreSQL/PostGIS
- Prisma oder Drizzle
- Python nur für ETL/Analyse, falls sinnvoll
- Docker Compose
- React/Next.js für Web-App
- OpenStreetMap/Overpass für erste Netzdatenindikatoren

## Definition of Done
- Funktion ist nachvollziehbar.
- Eingaben und Ergebnisse sind speicherbar.
- Fehlerfälle sind berücksichtigt.
- Keine verbindlichen Netzbetreiberaussagen ohne echte Datenbasis.
- Tests oder Prüfschritte sind dokumentiert.
- Revisionssicherheit wurde bedacht.
