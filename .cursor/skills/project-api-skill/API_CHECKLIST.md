# API Checklist (Gridcheck)

## Endpoint-Design
- Pfad unter `/api/v1/...`
- Eindeutige Verantwortlichkeit
- Response-Model explizit

## Validation
- Pydantic v2
- Keine impliziten Defaults für sicherheitskritische Felder
- Feldnamen mit Einheit bei elektrotechnischen Werten

## Fehlervertrag
- `detail` als Objekt mit:
  - `code`
  - `message`
  - `hint`

## Security
- AuthN/AuthZ geprüft
- Mandantentrennung/BOLA geprüft
- Keine Secrets in Antworten/Logs

## Fachlogik
- Keine Businesslogik im Router
- Rechenlogik deterministisch
- Annahmen, Normversion, Confidence transparent

## Tests
- Happy Path
- Validierungsfehler
- Fachlicher Fehlerfall
- Regression bei Bugfix
