# Auftragsverarbeitungsvertrag (AVV) — Entwurf

> **Nur Entwurf** zur Anbahnung von Enterprise-Gespraechen. Vor Vertragsschluss juristisch pruefen lassen.

## Parteien

- **Verantwortlicher:** Kunde (Projektierer / Netzbetreiber / Investor)
- **Auftragsverarbeiter:** Anbieter GridCheck (Betreiber der SaaS-Plattform)

## Gegenstand

Technische Vorverarbeitung von Netzanschluss-Projektdaten (Standort, Leistung, technische Parameter) zur Erstellung **vorlaeufiger** Diagnoseberichte.

## Kategorien betroffener Personen / Daten

- Projektbeteiligte (Namen/E-Mails in Nutzerkonten)
- Standort-/Anlagendaten (ggf. personenbezogen bei Anschlussnehmer)

## Zweck & Dauer

Zweck: Bereitstellung der Plattform im Rahmen des SaaS-Vertrags.  
Dauer: Vertragslaufzeit + gesetzliche Aufbewahrungsfristen fuer Audit-Logs.

## Unterauftragsverarbeiter (Stand Entwurf)

| Anbieter | Leistung | Region |
|----------|----------|--------|
| Vercel | Frontend-Hosting | EU/US (konfigurierbar) |
| Railway | API-Hosting, DB | EU |
| Stripe | Zahlungsabwicklung | EU/US |
| Mapbox | Kartenkacheln (optional) | US |

Liste wird im Hauptvertrag aktualisiert.

## Technische & organisatorische Massnahmen (TOMs — Kurz)

Siehe [SECURITY_ONEPAGER.md](./SECURITY_ONEPAGER.md): Verschluesselung Transport, Zugriffskontrolle, Logging, Backups (Railway Postgres).

## Rechte der betroffenen Personen

Kunde als Verantwortlicher bearbeitet Auskunft/Loeschung; Auftragsverarbeiter unterstuetzt ueber Export/Soft-Delete APIs.

## Loeschung

Nach Vertragsende: Export-Frist, danach Loeschung Produktionsdaten; Audit-Logs ggf. gesetzlich laenger.

## Unterzeichnung

_________________________  Verantwortlicher  
_________________________  Auftragsverarbeiter  
Ort, Datum
