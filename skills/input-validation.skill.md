# input-validation

## purpose
Prüft Benutzereingaben auf Vollständigkeit, Wertebereich und Plausibilität.

## use-when
- bei neuer Eingabe
- bei Änderungen
- vor jeder Entscheidung

## inputs
- projectName
- applicantName
- connectionLevel
- requestedCapacityKw
- estimatedAvailableCapacityKw
- loadProfileKnown
- siteSecured

## outputs
- valid
- errors[]
- warnings[]
- normalizedInput

## hard-rules
- Pflichtfelder prüfen
- keine Berechnung
- keine Entscheidung
- nur validieren

## success-criteria
- Fehler sauber getrennt
- Warnungen separat
- strukturierte Ausgabe

## failure-mode
- valid = false bei Fehlern
