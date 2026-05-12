# Report Generator Spezifikation

## Ziel
Revisionssichere PDF-Reports aus Gridcheck-Analysen erzeugen.

## Stakeholder
- Projektierer
- Netzbetreiber
- Investor

## Pflichtprinzipien
- Keine verbindliche Netzanschlusszusage
- Jede Aussage braucht Datenquelle, Annahme oder Modellwert
- Jede Reportversion bekommt audit_id, input_hash und result_hash
- Finalisierte Reports sind immutable
- Jede Aenderung erzeugt eine neue Revision

## Reporttypen

### Projektierer-Report
- Kurzfazit
- Anschlussvarianten
- technische Bewertung
- Kostenbandbreite
- Risiken
- naechste Schritte

### Netzbetreiber-Vorpruefbericht
- Eingangsdaten
- Datenvollstaendigkeit
- N-1-Screening
- offene Pruefpunkte
- technische Auflagen
- Audit-Trail

### Investor-Risk-Report
- Executive Summary
- Investment-Fazit
- Risikomatrix
- CAPEX-Bandbreite
- Zeitplanrisiko
- Due-Diligence-Punkte

## Audit
- report_id
- analysis_id
- audit_id
- report_version
- model_version
- scoring_version
- created_at
- stakeholder_type
- input_hash
- result_hash

## Disclaimer
Dieser Report ist eine automatisierte technische Vorbewertung und ersetzt keine verbindliche Netzanschlusspruefung durch den zustaendigen Netzbetreiber.
