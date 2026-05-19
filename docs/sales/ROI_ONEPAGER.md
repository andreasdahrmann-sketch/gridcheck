# GridCheck — ROI-Onepager (Projektentwickler)

**Stand:** Mai 2026 · **Zielgruppe:** Projektierer, EPC, Projektentwickler EE-Anlagen (PV, Speicher, Wind)  
**Format:** PDF-ready Markdown (A4, Schrift 10–11 pt empfohlen)

---

## Kurzfassung

GridCheck ist eine **vorläufige Netzanschluss-Diagnostik** (SaaS): Standort, Leistung und öffentliche Datenquellen werden strukturiert ausgewertet — mit nachvollziehbaren Annahmen, Risikohinweisen und revisionssicherem Protokoll.

**Nutzen:** Frühere, dokumentierte Go/No-Go-Entscheidungen **vor** teuren Netzbetreiber-Anfragen und langen Wartezeiten — ohne Scheinsicherheit über „freie Netzkapazität“.

---

## Das Problem (Status quo)

| Phase (typisch) | Dauer (konservativ) | Kosten-/Risikotreiber |
|-----------------|---------------------|------------------------|
| Erste Standortbewertung, interne Recherche | 1–3 Wochen | Planerstunden, verzögerte Pipeline |
| Netzbetreiber-Voranfrage / Kapazitätsklärung | 4–16+ Wochen | Wartezeit, externe Gutachter |
| Iterationen (Standortwechsel, Leistungsanpassung) | +2–8 Wochen je Zyklus | Opportunitätskosten, PPA-/Ausschreibungsdruck |
| Späte Ablehnung / Auflagen | unplanbar | CAPEX-Sprünge, Terminverlust |

**Hinweis:** Fristen variieren stark nach Netzbetreiber, Region und Anlagengröße. GridCheck ersetzt **keine** verbindliche Netzanschlussprüfung.

---

## Was GridCheck liefert (heute, MVP)

- **Strukturierte Vorprüfung** mit Spannungsebenen-Hinweis, Anschlusskandidaten und Bedingungsdiagnose (heuristisch, N-1-Screening max. N1-1/N1-2 ohne DSO-Daten)
- **Datenquellen-Transparenz** (z. B. OSM-Hinweise auf Assets — **nicht** Kapazitätsnachweise)
- **Kostenbandbreite** (niedrig / Basis / hoch) mit Annahmen und Confidence
- **PDF-Report** für interne Freigabe und Stakeholder-Kommunikation
- **Revisionssicherer Audit-Trail** (Input/Output-Hash, Engine-Version, Norm-Version)

---

## Zeitersparnis (konservative Schätzung)

| Aktivität | Ohne GridCheck (typ.) | Mit GridCheck (Ziel) | Einsparung (Orientierung) |
|-----------|------------------------|----------------------|---------------------------|
| Erste strukturierte Standort-/Netzbewertung | 3–10 Planertage | 0,5–2 Tage (Eingabe + Review) | **ca. 2–8 Tage** |
| Dokumentation für internes Gate | 1–3 Tage | im Report enthalten | **ca. 0,5–2 Tage** |
| Sackgassen vor NB-Anfrage erkennen | oft erst nach Wochen | früher im Prozess | **Wartezeit-Risiko ↓** (nicht quantifizierbar ohne NB-Daten) |

**Keine Garantie** auf verkürzte Netzbetreiber-Bearbeitungszeiten. GridCheck beschleunigt die **eigene** Entscheidungsvorbereitung.

---

## Kostenersparnis (konservative Schätzung)

Annahmen (anpassbar im Gespräch):

- Vollkosten Planer/Engineer: **80–120 EUR/h** (Bandbreite)
- Vermiedene externe Vorstudie (nicht immer): **2.000–8.000 EUR** pro Standort
- Kosten eines verschobenen Projektstarts (Opportunität): **projektspezifisch** — nicht pauschal versprochen

| Szenario | Grobe Einsparung (Orientierung) |
|----------|----------------------------------|
| 1 Standort, frühes No-Go | 5.000–15.000 EUR (Planung + vermiedene NB-Kommunikation) |
| 5 Standorte, 2 früh verworfen | 10.000–40.000 EUR (skaliert mit Teamgröße) |
| 1 Standort, Go mit dokumentierter Risikoliste | Qualitätsgewinn; EUR-Ersparnis indirekt (weniger Nacharbeit) |

**GridCheck-Invest:** siehe Paketrahmen in `docs/monetarisierungspakete.md` (z. B. 499–1.490 EUR/Monat oder 99–490 EUR/Analyse — final im Vertrag).

**Break-even (Beispiel):** Bei 100 EUR/h und 40 gesparten Planerstunden → **4.000 EUR** — oft bereits nach **1–2** verworfenen oder präzisierten Standorten erreicht (individuell zu validieren).

---

## Qualitative Vorteile

- **Einheitliche Entscheidungsgrundlage** im Team (nicht nur E-Mail-Wissen)
- **Nachvollziehbarkeit** gegenüber Investoren und EPC-Partnern (Audit-ID, Versionen)
- **Risikotransparenz** statt impliziter „grüner Ampel“-Annahmen
- **Skalierbarkeit** bei Standort-Pipelines (mehrere Varianten dokumentiert)

---

## Abgrenzung (bewusst ehrlich)

GridCheck **behauptet nicht**:

- verfügbare Netzkapazität am Punkt X
- verbindliche Netzanschlusszusage
- garantierte N-1-Sicherheit ohne verifizierte Netzbetreiberdaten
- Ersatz für TAB, VDE-Freigabe oder offizielle NB-Auskunft

GridCheck **liefert**:

- vorläufige, begründete Diagnose mit Confidence und Warnungen
- klare nächste Schritte (z. B. NB-Anfrage, Datenbeschaffung, Standortalternative)

---

## Nächster Schritt

- **Pilot** (4–8 Wochen): siehe `docs/sales/PILOTANGEBOT.md`
- **Technik & Security:** `docs/SECURITY_ONEPAGER.md`
- **Live ohne Custom-Domain:** `docs/GO_LIVE_OHNE_DNS.md`

**Kontakt:** kontakt@gridcheck.de

---

## Disclaimer (rechtlich relevant)

Dieses Dokument ist **Marketing- und Orientierungshilfe**, keine Rechts-, Investitions- oder Netzanschlussberatung. Alle Zeit- und Kostenschätzungen sind **Richtwerte** auf Basis typischer Branchenerfahrung; Ergebnisse hängen von Standort, Netzbetreiber, Anlagengröße und Datenlage ab. Die finale Entscheidung über Netzanschluss und Kapazität liegt beim **zuständigen Netzbetreiber**. Öffentliche und modellierte Daten können unvollständig oder veraltet sein.
