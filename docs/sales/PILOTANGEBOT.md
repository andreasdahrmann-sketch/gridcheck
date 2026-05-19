# GridCheck — Pilotangebot (Vorlage)

**Anbieter:** GridCheck (Betreiber der SaaS-Plattform)  
**Version:** 1.0 · **Stand:** Mai 2026  
**Hinweis:** Platzhalter in eckigen Klammern vor Versand ersetzen. Kein rechtsverbindliches Angebot ohne Unterschrift beider Parteien.

---

## 1. Anschreiben

Sehr geehrte Damen und Herren,

wir bieten Ihnen einen **strukturierten Pilot** der GridCheck-Plattform an — zur vorläufigen Netzanschluss-Diagnostik Ihrer Projektpipeline. Ziel ist eine belastbare Einschätzung von Nutzen, Prozessintegration und technischer Eignung **vor** einem Jahresvertrag.

Mit freundlichen Grüßen  
[Name, Funktion]  
GridCheck · [Straße, PLZ Ort] · kontakt@gridcheck.de

---

## 2. Vertragspartner

| | Kunde (Pilotnehmer) | Anbieter |
|---|---------------------|----------|
| Firma | [Firma Kunde] | [Rechtsform GridCheck] |
| Ansprechpartner | [Name, Rolle] | [Name, Rolle] |
| E-Mail | [email@kunde.de] | kontakt@gridcheck.de |

---

## 3. Leistungsgegenstand (Scope)

### Enthalten

- Zugang zur GridCheck-SaaS (Rolle: **Projektierer** / Paket „Project Developer“)
- Bis zu **[N]** Projekte / Analysen im Pilotzeitraum (z. B. **10**)
- Funktionen gemäß MVP-Stand:
  - Standortcheck, Netzebenen-Vorschlag, Anschlusskandidaten
  - Bedingungsdiagnose, Kostenbandbreite (Bandbreite, nicht Einzelpreis)
  - PDF-Export, revisionssicherer Berechnungsnachweis (Audit-ID / Hash)
- Onboarding: **1×** Remote-Session (60 min) — Eingabe, Report-Interpretation, Grenzen der Diagnose
- E-Mail-Support (siehe SLA)

### Nicht enthalten

- Verbindliche Netzanschluss- oder Kapazitätszusage
- Netzbetreiber-Kommunikation oder Intake beim NB
- Rechtsberatung, Genehmigungsplanung, detaillierte Netzplanung
- Garantierte Datenaktualität Drittanbieter (OSM, MaStR, etc.)
- Penetrationstest / dediziertes ISMS (optional separat)

---

## 4. Laufzeit und Preis

| Parameter | Wert |
|-----------|------|
| **Pilotlaufzeit** | **[4–8] Wochen** ab Freischaltung |
| **Start** | [Datum] (nach Zahlung / PO) |
| **Ende** | [Datum] |
| **Pilotpreis (Pauschal)** | **[X.XXX] EUR** zzgl. gesetzl. MwSt. |
| **Zahlungsziel** | 14 Tage nach Rechnungsstellung |
| **Verlängerung** | Automatisch **nein** — Übergang nur per separatem Rahmenvertrag |

*Orientierung Marktpreis (nicht bindend): siehe `docs/monetarisierungspakete.md` (z. B. 499–1.490 EUR/Monat). Pilotpreis typisch **50–70 %** eines Monatsabos bei begrenztem Volumen.*

---

## 5. Service Level (SLA) — Pilot

| Kategorie | Zusage (Pilot) |
|-----------|----------------|
| **Verfügbarkeit** | Best effort; Ziel **99 %** Monatsverfügbarkeit (ohne geplante Wartung) |
| **Wartungsfenster** | Mit **48 h** Vorankündigung, bevorzugt nachts (MEZ) |
| **Support-Kanal** | E-Mail kontakt@gridcheck.de |
| **Reaktionszeit** | Werktags **≤ 2 Werktage** (P1: Login/Export blockiert) |
| **Störungsbehebung** | P1: Ziel **≤ 5 Werktage** (Workaround oder Fix) |

Kein 24/7-Betrieb im Pilot. Enterprise-SLA separat verhandelbar.

---

## 6. Datenverarbeitung und Sicherheit

- Auftragsverarbeitung: Entwurf **AVV** — `docs/AVV_ENTWURF.md` (vor Vertragsschluss juristisch prüfen)
- Technische Kurzübersicht: `docs/SECURITY_ONEPAGER.md`
- Hosting: Frontend **Vercel (EU)**, API + DB **Railway (EU)**, PostgreSQL
- Verschlüsselung: **TLS** in Transit; Passwörter **bcrypt** (≥ 12 Rounds)
- **Keine** Speicherung von Zahlungskarten in GridCheck (Stripe PCI-DSS)
- Löschung nach Pilotende: auf Wunsch Export, danach Löschung Produktionsdaten gemäß AVV; Audit-Logs ggf. gesetzlich länger

Der Kunde bleibt für die **Richtigkeit der Eingaben** und die **weitere Nutzung der Diagnose** verantwortlich.

---

## 7. Limitationen und Haftung (Kurz)

1. Alle Ergebnisse sind **vorläufige Diagnosen** — keine Netzanschlusszusage.
2. Öffentliche Daten können **unvollständig oder veraltet** sein; Confidence und Warnungen sind Bestandteil des Reports.
3. Haftung im Pilot auf **Vorsatz und grobe Fahrlässigkeit** beschränkt, soweit gesetzlich zulässig; weitergehende Haftung nur im Rahmenvertrag.
4. **Keine** Garantie wirtschaftlicher Einsparung; ROI-Angaben in `docs/sales/ROI_ONEPAGER.md` sind Orientierung.

---

## 8. Erfolgskriterien (gemeinsam vereinbart)

Am Pilotende dokumentieren beide Seiten:

- [ ] Mindestens **[N]** Analysen durchgeführt und Reports exportiert
- [ ] Durchschnittliche **Time-to-First-Result** ≤ **[X] Stunden** (nach vollständigen Eingaben)
- [ ] Mindestens **[N]** interne Go/No-Go-Entscheidungen mit GridCheck-Report belegt
- [ ] Feedback-Gespräch (30 min) — Prozessfit, Datenlücken, Wünsche

---

## 9. Nächste Schritte nach Pilot

| Option | Beschreibung |
|--------|--------------|
| **A — Rahmenvertrag** | Monatsabo oder Pay-per-Analysis gemäß Preisliste |
| **B — Verlängerung Pilot** | max. einmal, 4 Wochen, reduzierter Scope |
| **C — Beendigung** | Export, Löschung, keine automatische Verlängerung |

---

## 10. Annahme

Mit Unterzeichnung akzeptiert der Kunde Scope, SLA, Datenverarbeitung und Limitationen.

| | Kunde | Anbieter |
|---|-------|----------|
| Ort, Datum | _________________ | _________________ |
| Unterschrift | _________________ | _________________ |
| Name | _________________ | _________________ |

---

*Anlagen (optional): ROI-Onepager (`docs/sales/ROI_ONEPAGER.md`), Security-Onepager (`docs/SECURITY_ONEPAGER.md`)*
