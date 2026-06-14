# Anwalt-Briefing — GridCheck Pre-Netzanschluss-App

> **Status: ENTWURF — keine juristische Beratung, keine Eigenwertung.**
> Stand: 2026-06-14
> Autor: Engineering / Compliance-Vorbereitung
> Adressat: Beauftragter IT-/DSGVO-Anwalt

---

## 1. Zweck dieses Briefings

Wir bitten um die juristische Pruefung und Final-Freigabe der unten gelisteten Rechtstexte und Compliance-Artefakte fuer die SaaS-Plattform **GridCheck** vor dem Live-Gang. Die App ist ein **diagnostisches Entscheidungsunterstuetzungssystem** fuer Netzanschluss-Vorpruefungen — **kein** Ersatz einer rechtsverbindlichen Netzanschlusspruefung des zustaendigen Netzbetreibers. Diese Abgrenzung ist in Disclaimern bereits ueberall konsistent verbaut.

Fokus der Pruefung:

- Rechtssichere Pflichttexte (Impressum, AGB, Datenschutzerklaerung)
- DSGVO-Konformitaet (Art. 13/14, Art. 28 AVV, Art. 44 ff. Drittlandtransfer)
- Haftungs- und Folgeschadens-Ausschluesse (B2B-Kontext, KRITIS-Naehe)
- Verbraucher-AGB-Sonderrechte (Widerrufsrecht, Verbrauchervertrag — falls B2C-Pfade)
- Aufbewahrungs- und Loeschpflichten in Verbindung mit revisionssicheren Audit-Logs
- AVV-Entwurf fuer Enterprise-Kunden (B2B-AVV-Vertrag)

---

## 2. Kontext (Pitch in 1 Absatz)

GridCheck unterstuetzt Projektentwickler, Planer, Kommunen, Investoren und Netzbetreiber bei der **vorlaeufigen** Einschaetzung, ob ein geplanter Netzanschluss (PV, BESS, Wind, Wallbox-Cluster) am gewaehlten Standort plausibel ist: Spannungsebene, Trassendistanzen, N-1-Screening (Klassifikation N1-0 bis N1-4), Kostenbandbreite, Risikoaufschluesselung. Verarbeitet werden personenbezogene Daten von Nutzerinnen / Nutzern (E-Mail, Rolle, Organisation), Projekt- und Standortdaten (auch potenziell personenbezogen, wenn Adresse = Anschlussnehmer) sowie revisionssichere Audit-Logs.

### Datenverarbeitungs-Skizze (Kurzform)

```
Browser (Cookie-Consent)
   |
   v
Vercel (Frontend, EU-Edges bevorzugt) -- TLS -->
   |
   v
Railway (Backend FastAPI + PostgreSQL/PostGIS, EU-Region)
   |  |  |
   |  |  +-- (optional) Sentry (Error-Monitoring)
   |  +----- (optional) Stripe (Zahlungen)
   +-------- Nominatim (OSM, EU/UK) - Geocoding
```

Detail siehe `DATENFLUSS_DIAGRAMM.md`.

---

## 3. Liefer-Set fuer den Anwalt

| # | Dokument | Pfad / Datei | Stand |
|---|----------|--------------|-------|
| 1 | Impressum (Live-Stand) | `frontend/app/impressum/page.tsx` (Render-Vorlage) + `frontend/lib/legal.ts` (Tokens) | Tokens noch nicht final ausgefuellt |
| 2 | AGB (Live-Stand) | `frontend/app/agb/page.tsx` (Render-Vorlage) | ENTWURF |
| 3 | Datenschutzerklaerung (Live-Stand) | `frontend/app/datenschutz/page.tsx` | Aktiv, Tokens teils offen |
| 4 | AVV-Entwurf v2 (B2B) | `docs/legal/AVV_ENTWURF_v2.md` | ENTWURF |
| 5 | Datenfluss-Diagramm | `docs/legal/DATENFLUSS_DIAGRAMM.md` | ENTWURF |
| 6 | Auftragsverarbeiter-Liste (aktive Sub-AV) | `docs/legal/AUFTRAGSVERARBEITER.md` | Synchron zu `frontend/lib/legal.ts` (`DATA_PROCESSORS`) |
| 7 | Tech-Stack-Uebersicht (1 Seite) | `docs/legal/TECH_STACK_FUER_ANWALT.md` | Aktiv |
| 8 | Compliance-Audit (intern) | `docs/COMPLIANCE_AUDIT.md` | 2026-05-19, hilfreich als Hintergrund |

Begleitend nur auf Anfrage:

- ADR-Sammlung (`DECISIONS.md`) — Architekturentscheidungen, insbes. ADR-005 (Hash-Chain Revisionssicherheit), ADR-008 (PostgreSQL/PostGIS EU-souveraen), ADR-007-DETAIL (kein Supabase, EU-Datenhoheit)
- TOMs-Onepager (`docs/SECURITY_ONEPAGER.md`)

---

## 4. Konkrete Pruef-Fragen-Liste

### 4.1 Impressum (TMG / DDG / MStV)

1. Sind die Pflichtangaben nach § 5 DDG (vormals TMG) und § 18 MStV vollstaendig vorgesehen?
2. Reicht der vorgesehene Tokensatz (Firma, Rechtsform, Anschrift, Vertretungsberechtigte, Registergericht, HRB, USt-IdNr., Kontakt-E-Mail, Telefon)?
3. Bedarf es zusaetzlicher Aufsichtsangaben aufgrund der KRITIS-Naehe (Energienetz-Diagnostik)? — Unsere Einschaetzung: nein (vorlaeufige Diagnose, keine Berufsregulierung), Bestaetigung erbeten.

### 4.2 AGB (B2B-Schwerpunkt, optional B2C)

1. Ist die B2B-Praegung der AGB ausreichend abgesichert (kein Verbrauchergeschaeft im Standardfall)?
2. Falls B2C-Pfad (Einzel-Projektierer, Privatperson) eroeffnet wird: Welche Verbraucher-AGB-Sonderrechte sind aufzunehmen (Widerrufsrecht §§ 312g, 355 BGB; Wertersatz; vorzeitiges Erloeschen bei digitalen Inhalten §§ 356, 327 BGB)?
3. Welche Klauseln zu Service-Level / Verfuegbarkeit / Wartungsfenstern sind branchenueblich und AGB-rechtlich zulaessig (insbesondere § 307 BGB Inhaltskontrolle bei B2B)?
4. Preisanpassungs- und Laufzeitklauseln (Auto-Renewal): wirksam gestaltbar, insbesondere im Lichte des FairConsumerContractsAct?

### 4.3 Datenschutz (DSGVO / TTDSG / TDDDG)

1. Sind die Pflichtinformationen nach Art. 13/14 DSGVO vollstaendig und korrekt gewichtet?
2. Drittlandtransfers: Ist die Argumentation (SCC + EU-US DPF fuer Vercel; SCC + DPF fuer Stripe/Sentry; OSM-Foundation EU/UK) tragfaehig in der aktuellen aufsichtsbehoerdlichen Praxis 2026?
3. Cookie-Consent: Reicht der vorgesehene Banner-Aufbau (technisch notwendige ohne Consent; alle anderen ueber Opt-In; granulare Widerruflichkeit) nach TTDSG § 25?
4. **Zustaendige Aufsichtsbehoerde**: Diese wird in der Datenschutzseite automatisch aus dem Sitz-Bundesland des Verantwortlichen aufgeloest (Mapping fuer alle 16 Laender im Code). Bitte plausibilitaetspruefen.
5. Ist die Bestellpflicht eines Datenschutzbeauftragten (§ 38 BDSG, Art. 37 DSGVO) bereits gegeben? Schwellen-Pruefung mit User-Daten erforderlich.

### 4.4 AVV (Art. 28 DSGVO)

1. Ist der Entwurf `AVV_ENTWURF_v2.md` als Modul-Vertrag zu Art. 28 DSGVO tragfaehig?
2. Sub-AV-Liste: Genuegt die generelle Genehmigung mit Widerspruchsrecht oder ist Einzelgenehmigung empfehlenswert?
3. TOMs als Anhang reichen aus oder Einzelnachweis (z. B. ISO 27001 der Sub-AV) erforderlich?
4. Pruefrechte / Audits: praktikable Klauselformulierung gewuenscht (Remote-Audits zumutbar?).
5. Loeschungs- / Rueckgabepflichten nach Vertragsende — Spannungsfeld zu Audit-Aufbewahrungspflichten der Hash-Chain (§ 257 HGB / § 147 AO; ADR-005).

### 4.5 Haftung / Folgeschadens-Ausschluss

1. Welche Haftungsbegrenzung ist bei einem **diagnostischen** Pre-Check rechtlich tragbar (B2B)? Insbesondere: Ausschluss mittelbarer / Folgeschaeden, entgangener Gewinn?
2. Ausreichend, dass jede Diagnose explizit als "vorlaeufig" und "ersetzt nicht die Pruefung des Netzbetreibers" gekennzeichnet ist?
3. Mitverschulden / Mitwirkungspflichten des Kunden (Datenqualitaet) — Klauselformulierung?
4. Verhaeltnis zu KRITIS / § 8a BSIG: Gibt es ueber die Disclaimer hinaus konkrete Hinweispflichten?

### 4.6 Verbraucher-AGB-Sonderrechte (sofern B2C-Pfad)

1. Welche Pflichtinformationen / Belehrungen muss die Plattform anzeigen (Buttonloesung § 312j BGB)?
2. Widerrufsrecht digitaler Dienste — Standardform und Ausnahmen.
3. Faire Verbrauchervertraege (FaVerVtrG): Auswirkungen auf Vertragslaufzeiten / Kuendigungsfristen.

### 4.7 Aufbewahrungspflichten

1. Hash-Chain / Audit-Logs / `revision_records` / `gridcheck_result_audit`: Soft-Delete + dauerhafte Aufbewahrung — vereinbar mit Art. 17 DSGVO unter Berufung auf Art. 17 Abs. 3 lit. b/e DSGVO und § 257 HGB / § 147 AO?
2. Loeschungskonzept fuer Konto-Stammdaten, Projektdaten, Sicherheits-Logs (30–90 Tage), Buchhaltungsdaten (10 Jahre) — unbedenklich?
3. Backup-Aufbewahrung (Railway-Automatik) — gesonderte Regelung in AVV erforderlich?

---

## 5. Timing-Erwartung

- **Wunschzeitfenster fuer Erstpruefung:** ca. 2 Wochen ab Zustellung des Liefer-Sets.
- **Iteration:** 1 Feedback-Runde mit konkreten Aenderungswuenschen, danach Final-Freigabe.
- **Live-Schaltung der Plattform:** abhaengig vom Feedback, fruehestens nach Final-Freigabe der Pflichttexte.

---

## 6. Offene Frage an den User (vor Anwalt-Versand)

- **Anwalt vorhanden?** Falls nicht: Empfehlung DSGVO-/IT-Recht-Anwalt mit SaaS- und B2B-Erfahrung, idealerweise mit Energiewirtschafts-Kontext (EnWG, BNetzA, EEG-Beruehrung).
- **Budget-Rahmen?** Erstpruefung Pflichttexte + AVV typischerweise im Bereich Festpreis vs. Stundensatz — vom User zu klaeren.
- **Sitz-Bundesland des Verantwortlichen?** -> Eintrag in `LEGAL_DATA.HOST_BUNDESLAND` (z. B. "Berlin", "NRW", "Bayern"); die Aufsichtsbehoerde wird dann automatisch in der Datenschutzseite ausgewiesen.
- **Firmendaten-Tokens** in `frontend/lib/legal.ts` final ausfuellen (FIRMA_NAME, RECHTSFORM, STRASSE_HAUSNR, PLZ_ORT, REGISTERGERICHT, HRB_NR, GESCHAEFTSFUEHRER, TELEFON, KONTAKT_EMAIL, DPO_NAME, DPO_EMAIL, GERICHTSSTAND_ORT, STAND_DATUM) — siehe Legal-Worker-Bericht.

---

## 7. Wichtiger Hinweis

Saemtliche in diesem Briefing referenzierten Texte und Vertraege sind **Entwuerfe**, erstellt zur Unterstuetzung der anwaltlichen Pruefung. Sie wurden technisch und fachlich plausibilisiert, **nicht jedoch juristisch geprueft**. Die endgueltige Verantwortung fuer Inhalt und Live-Schaltung liegt beim Verantwortlichen nach DSGVO und beim beauftragten Anwalt.
