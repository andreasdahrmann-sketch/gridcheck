# Auftragsverarbeitungsvertrag (AVV) — ENTWURF v2

> **Status: ENTWURF — keine juristische Beratung, nicht juristisch geprueft.**
> Stand: 2026-06-14
> Loest `docs/AVV_ENTWURF.md` (v1) nicht ab, sondern ergaenzt sie als Briefing-Vorlage fuer die anwaltliche Pruefung.
> Anwendung: B2B, Modul fuer Auftragsverarbeitung im Sinne **Art. 28 DSGVO**.

---

## Vorbemerkung / Kontext fuer den Anwalt

Dieser Entwurf orientiert sich an den **EU-Standardvertragsklauseln** (Durchfuehrungsbeschluss (EU) 2021/915 der Kommission vom 4. Juni 2021 — Modul fuer Auftragsverarbeitung Art. 28 DSGVO). Wo Wahlmoeglichkeiten bestehen, ist der konservative Default markiert (`[Default: ...]`). Zur produktiven Verwendung sind die in `{{...}}`-Klammern hinterlegten Tokens mit Firmen- und Vertragsdaten zu fuellen.

---

## § 1 Parteien

**Verantwortlicher:**

- Firma: `{{KUNDE_FIRMA}}`
- Anschrift: `{{KUNDE_ANSCHRIFT}}`
- Vertretungsberechtigte/r: `{{KUNDE_VERTRETUNG}}`
- Kontakt fuer Datenschutz: `{{KUNDE_DSB_KONTAKT}}`

**Auftragsverarbeiter:**

- Firma: `{{FIRMA_NAME}}` (`{{RECHTSFORM}}`)
- Anschrift: `{{STRASSE_HAUSNR}}, {{PLZ_ORT}}, {{LAND}}`
- Vertretungsberechtigte/r: `{{GESCHAEFTSFUEHRER}}`
- Datenschutzbeauftragte/r: `{{DPO_NAME}}`, `{{DPO_EMAIL}}`

---

## § 2 Gegenstand und Dauer

**Gegenstand:** Verarbeitung personenbezogener Daten durch den Auftragsverarbeiter im Rahmen der Bereitstellung und des Betriebs der SaaS-Plattform **GridCheck** (Pre-Netzanschluss-Diagnostik, Audit-Trail, Reporting) gemaess dem zugrundeliegenden Hauptvertrag.

**Dauer:** Laufzeit des Hauptvertrags, einschliesslich gesetzlich vorgegebener Aufbewahrungsfristen fuer Audit-/Buchhaltungs-Logs (siehe § 8).

---

## § 3 Art und Zweck der Verarbeitung

| Verarbeitung | Zweck |
|--------------|-------|
| Bereitstellung Konto/Login | Identifikation, Zugriffskontrolle, Sicherheit |
| Speicherung Projekt- und Standortdaten | Vorlaeufige Netzanschluss-Diagnostik |
| Berechnung / Scoring / N-1-Screening | Erzeugung diagnostischer Reports |
| Geocoding (Nominatim) | Adressaufloesung Standortbezug |
| Audit-Hash-Chain | Revisionssicherheit / Nachweisbarkeit |
| Zahlungsabwicklung (optional Stripe) | Vertragsdurchfuehrung Abrechnung |
| Error-Monitoring (optional Sentry) | Stabilitaet / Sicherheitsanalyse |

---

## § 4 Art der personenbezogenen Daten

- Stammdaten Nutzerkonten (E-Mail, Name, Rolle, Organisation)
- Authentifizierungs- und Sicherheitsdaten (Passwort-Hash bcrypt, Session-Tokens)
- Standort- und Projektdaten (Adresse, Koordinaten — kann Personenbezug zum Anschlussnehmer aufweisen)
- Verbindungs- und Logdaten (IP, User-Agent, Zeitstempel, Audit-Events)
- Optional: Zahlungs- und Rechnungsmetadaten (bei aktiviertem Stripe)

## § 5 Kategorien betroffener Personen

- Kontoinhaberinnen / Kontoinhaber des Verantwortlichen (Mitarbeiter, Projektierer)
- Im Standortbezug ggf. Anschlussnehmerinnen / Anschlussnehmer (mittelbar betroffen)
- Ansprechpartner im Rahmen der Vertragsdurchfuehrung

---

## § 6 Pflichten des Auftragsverarbeiters

Der Auftragsverarbeiter verpflichtet sich, die Verarbeitung ausschliesslich nach den Weisungen des Verantwortlichen durchzufuehren (Art. 28 Abs. 3 lit. a DSGVO). Im Einzelnen:

1. Verarbeitung nur in der EU/EWR oder mit geeigneten Garantien gemaess Art. 46 DSGVO bei Drittlandbezug der Sub-AV (siehe Anhang).
2. Vertraulichkeitsverpflichtung aller mit der Verarbeitung befassten Personen (Art. 28 Abs. 3 lit. b DSGVO).
3. Durchfuehrung und Dokumentation der TOMs nach Art. 32 DSGVO (Anhang B).
4. Unterstuetzung des Verantwortlichen bei Betroffenenrechten (Art. 12–22 DSGVO) durch Export- und Loeschfunktionen ueber das Self-Service-Modul.
5. Unterstuetzung bei Datenschutzfolgenabschaetzungen (Art. 35) und bei der Meldung von Verletzungen (Art. 33 DSGVO; Frist: unverzueglich, spaetestens 24 Stunden nach Kenntnis).
6. Loeschung / Rueckgabe nach Vertragsende (siehe § 8).

---

## § 7 Sub-Auftragsverarbeiter

Der Verantwortliche genehmigt allgemein die Inanspruchnahme der im Anhang A gelisteten Sub-AV. Aenderungen sind dem Verantwortlichen mit `[Default: 4 Wochen]` Vorlauf textlich anzuzeigen; ein begruendeter Widerspruch ist innerhalb dieser Frist moeglich.

### Anhang A — aktuelle Sub-AV (synchron zu `frontend/lib/legal.ts`, `DATA_PROCESSORS`)

| Anbieter | Leistung | Sitz / Region | Transfergrundlage | AVV |
|----------|----------|---------------|-------------------|-----|
| Railway Corp. | Hosting Backend-API + verwaltete PostgreSQL/PostGIS | EU-Region (z. B. Frankfurt/Amsterdam) | EU/EWR | Ja |
| Vercel Inc. | Hosting Frontend (Next.js), Edge-CDN, Build-Pipeline | USA (EU-Edges bevorzugt) | SCC + EU-US DPF | Ja |
| OpenStreetMap Foundation / Nominatim | Geocoding / Reverse-Geocoding | EU/UK (gemeinnuetzige Stiftung) | EU/EWR | Nein (oeffentliche Schnittstelle, Abfrageprotokoll konservativ) |
| Stripe Payments Europe Ltd. / Stripe Inc. (**optional, derzeit inaktiv**) | Zahlungsabwicklung | Irland (EU) + USA | SCC + EU-US DPF | Ja |
| Sentry / Functional Software Inc. (**optional, derzeit inaktiv**) | Fehler- und Performance-Monitoring | USA (EU-Region waehlbar) | SCC + EU-US DPF | Ja |

> Aktivierung "optional" markierter Sub-AV nur nach gesonderter Aktivschaltung und vor Live-Gang anwaltlicher Doppelpruefung.

---

## § 8 Loeschung, Rueckgabe und Aufbewahrung

Nach Beendigung des Hauptvertrags loescht der Auftragsverarbeiter die personenbezogenen Daten gemaess folgender Staffelung:

| Datenkategorie | Frist nach Vertragsende |
|----------------|-------------------------|
| Konto-Stammdaten (`users`) | Soft-Delete sofort, harte Loeschung nach `[Default: 90 Tage]` |
| Projekt- und Fachdaten | Soft-Delete sofort, harte Loeschung nach `[Default: 90 Tage]` (vorbehaltlich vereinbarter Exportfrist) |
| Audit-Hash-Chain (`revision_records`, `gridcheck_result_audit`) | Aufbewahrung gemaess gesetzlicher Pflichten — typischerweise 6 bzw. 10 Jahre (§ 257 HGB / § 147 AO) — danach Loeschung in geordnetem Verfahren |
| Buchhaltungs-/Rechnungsdaten | 10 Jahre (§ 257 HGB / § 147 AO) |
| Sicherheits-Logs | 30–90 Tage, laenger nur bei Sicherheitsvorfaellen |

Dem Verantwortlichen wird vor harter Loeschung ein Export-Fenster eingeraeumt (`[Default: 30 Tage]`).

---

## § 9 Pruefrechte

Der Verantwortliche kann sich von der Einhaltung dieser AVV einmal jaehrlich und anlassbezogen ueberzeugen. Vor-Ort-Audits sind nur nach vorheriger Abstimmung und unter Beachtung der Sicherheits- und Vertraulichkeitsinteressen anderer Mandanten zulaessig. Anstelle eines Vor-Ort-Audits koennen Nachweise ueber Zertifizierungen, Pruefberichte oder vergleichbare Dokumente vorgelegt werden.

## § 10 Haftung

Die Haftung richtet sich nach Art. 82 DSGVO und den Regelungen des Hauptvertrags. Eine Haftung des Auftragsverarbeiters fuer mittelbare Schaeden / entgangenen Gewinn ist im Rahmen der gesetzlichen Zulaessigkeit ausgeschlossen.

---

## Anhang B — TOMs (Technische und Organisatorische Massnahmen, Kurzform)

- **Vertraulichkeit:** Zugriffskontrolle (RBAC), MFA optional, bcrypt-Passwortspeicherung, JWT-Token mit kurzer Lebensdauer + Refresh, BOLA-Schutz auf Projektressourcen, Organisationsgrenzen serverseitig erzwungen.
- **Integritaet:** Append-only Audit-Hash-Chain (SHA256), Alembic-Migrationen versioniert, kein Silent-Schema-Drift, signierte Releases.
- **Verfuegbarkeit:** Railway-Automatik-Backups (taeglich), wiederherstellbare PostgreSQL-Dumps, Monitoring optional via Sentry / strukturiertes JSON-Logging.
- **Belastbarkeit:** Rate-Limiting auf oeffentliche Endpoints, CORS-Whitelist, Healthcheck-Endpoint.
- **Pseudonymisierung / Verschluesselung:** TLS Ende-zu-Ende, sensible Konfiguration ausschliesslich ueber ENV (keine Secrets im Code).
- **Datentrennung:** Mandantentrennung ueber `organization_id` und ACLs auf Projektebene.
- **Auftragskontrolle:** Sub-AV mit AVV, Drittlandtransfer ausschliesslich mit SCC + DPF.

---

## Anhang C — Norm-Bezug

- DSGVO (Verordnung (EU) 2016/679)
- BDSG (insb. § 38 — DSB-Bestellpflicht)
- EU-Standardvertragsklauseln (Durchfuehrungsbeschluss (EU) 2021/915 — Modul Auftragsverarbeitung)
- TTDSG / TDDDG — Cookie- und Endgeraete-Zugriff
- HGB § 257, AO § 147 — Aufbewahrungspflichten

---

## Unterzeichnung

```
Ort, Datum

_____________________________
Verantwortlicher

_____________________________
Auftragsverarbeiter
```

---

> **Hinweis:** Dieser Entwurf wurde technisch plausibilisiert. Vor Verwendung mit Endkunden ist eine **anwaltliche Pruefung** zwingend. Insbesondere die Klauseln zu Haftung, Pruefrechten, Sub-AV-Genehmigung und Loeschung muessen in der konkreten Vertragsgestaltung abgestimmt werden.
