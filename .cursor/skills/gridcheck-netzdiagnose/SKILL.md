---
name: gridcheck-netzdiagnose
description: >-
  Fuehrt eine strukturierte Pre-Netzanschluss-Diagnose fuer ein Projekt durch
  (Machbarkeit, Engpaesse, Spannungs-/Thermik-/KS-Risiko, Annahmen, naechste Schritte).
  Use when validated project data is available, a feasibility pre-check is required,
  technical bottlenecks must be identified, or alternatives and constraints must be documented.
  Do not use when input validation is incomplete, critical network data is missing without
  allowed assumption mode, or a formal grid-operator decision is expected.
---

# Gridcheck Netzdiagnose

## Zweck

Strukturierte **vorlaeufige** Netzanschluss-Diagnose auf Basis validierter Eingaben und bekannter Netzgrenzen — erklaerbar, auditierbar, ohne verbindliche Zusage.

Dieser Skill steuert **Agent-Arbeit** (Interpretation, Dokumentation, Empfehlungen). Die fachliche Rechenlogik liegt im Backend (`berechne_netzanschluss`), nicht im Skill.

## Wann nutzen

- validierte Projektdaten liegen vor
- Machbarkeits-Pre-Check ist gefragt
- technische Engpaesse muessen benannt werden
- Alternativen und Randbedingungen muessen dokumentiert werden

## Nicht nutzen

- Eingabevalidierung ist nicht abgeschlossen (`validiere_eingabe` / API-422 noch offen)
- kritische Netzdaten fehlen **und** kein dokumentierter Annahmemodus ist erlaubt
- eine **formale** Netzbetreiber-Entscheidung wird erwartet (→ klar abgrenzen)

## Eingaben → Engine / API

| Skill-Input | Gridcheck-Bezug |
|-------------|------------------|
| `validated_project_data` | Pydantic-Request nach `POST /api/v1/analyze` (`backend/api/analyze_v2.py`) oder `ProjektiererRequest` |
| `pcc_data` | `NetzanschlusspunktPayload` / `eingabe` PCC-Felder (`max_export_kw`, Export-Limit, eigener Trafo/UW) |
| `transformer_data` | `trafo_s_mva`, `trafo_uk_prozent`, `umspannwerk.trafos[]` |
| `feeder_data` | `umspannwerk.abgaenge[]` (Abgangsreserve, N-1 in `engine/n1_analyse.py`) |
| `line_data` | `leitungstyp`, `entfernung_km`, `parallele_systeme` (`LEITUNGSDATEN` in `berechnung.py`) |
| `voltage_level` | `nennspannung` (kV) → `bestimme_spannungsebene` → NS/MS/HS |
| `requested_capacity` | `leistung_mw` (+ `bestehende_einspeisung_mw` fuer wirksame Last) |
| `generation_profile` | `project_components` (pv, wind, …), `anschlussart` Einspeisung |
| `load_profile` | Komponenten `load` / `charging`, `anschlussart` Entnahme |
| `operational_constraints` | `constraints` im Projektierer-Flow (`/api/v1/projektierer/analyze`) |
| `data_quality_score` | Engine-Block `datenqualitaet`, `scores.datenqualitaet`, `transparenz` |

**Primaere Rechenquelle:** `engine.berechnung.berechne_netzanschluss` in `backend/engine/berechnung.py`  
**N-1-Detail:** `engine.n1_analyse.analysiere_n1` in `backend/engine/n1_analyse.py`  
**MS-Topologie-Pre-Check:** `engine.n1_ms.bewerte_n1_ms`

**API-Einstiegspunkte (bestehend, nicht erfinden):**

| Route | Datei | Rolle |
|-------|-------|-------|
| `POST /api/v1/analyze` | `backend/api/analyze_v2.py` | Vollstaendiges Engine-Ergebnis, revisionssicher |
| `POST /api/v1/projektierer/analyze` | `backend/api/v1_projektierer.py` | Projektierer + Constraints + Optimizer-Skizze |
| `POST /api/v1/stakeholders/projektierer` | `backend/api/stakeholders.py` | Stakeholder-Ampel + `EngpassInfo`-Liste |

Reports: Pflichtprinzipien in `docs/REPORT_GENERATOR_SPEC.md` (keine verbindliche Zusage, Audit-Hashes).

---

## Verbindliche Hard-Rules

1. **Never issue binding approval.** Keine Netzanschlusszusage, keine Kapazitaetsgarantie.
2. **Distinguish** zwischen *vorlaeufiger Machbarkeit* (Heuristik/Screening) und *bestaetigter Machbarkeit* (verifizierte NB-Daten, N1-3/N1-4).
3. **Every negative or limited result must include reasons** (Scores, Verstoesse, `engpass_komponente`, Warnungen).
4. **Every positive result must include boundary conditions** (`transparenz`, N-1-Klasse, Annahmen, Disclaimer).
5. **If assumptions materially affect the result, downgrade confidence** (`transparenz.confidence_notes`, `n1.konfidenz`, `datenqualitaet`).
6. **Results must be explainable, not just classified** — Fazit-Text + Begruendung, nicht nur Ampel/Farbe.

Zusaetzlich gelten `.cursor/rules/06-arbeitsweise-gridcheck.mdc` (N-1 N1-0..N1-4, keine Scheingenauigkeit, OSM ≠ freie Kapazitaet).

### N-1-Screening-Stufen (Projektstandard)

| Level | Bedeutung |
|-------|-----------|
| N1-0 | Keine N-1-Aussage moeglich |
| N1-1 | Heuristisches Screening |
| N1-2 | Topologische Naeherung |
| N1-3 | Lastfluss mit geschaetzten Parametern |
| N1-4 | Lastfluss mit verifizierten Netzbetreiberdaten |

MVP ohne NB-Daten: maximal **N1-1** oder **N1-2** als belastbare Reserveaussage — in `warnungen` / `transparenz` explizit machen.

---

## Standard-Workflow

```
1. Gate: Eingaben validiert? Annahmemodus dokumentiert?
2. Engine/API ausfuehren (berechne_netzanschluss oder bestehender Analyze-Endpoint)
3. Commands 3.1–3.7 auf Ergebnis anwenden (Reihenfolge flexibel, Summary zuletzt)
4. Diagnose-JSON nach Schema ausgeben
5. Bei unzureichender Basis → failure-mode (unten)
```

Vor jeder Diagnose: **eine Aufgabe**, minimal-invasiv (vgl. `06-arbeitsweise-gridcheck.mdc`).

---

## Commands

Jeder Command liefert einen Teilblock fuer das Ausgabe-JSON. Bei vorhandenem Engine-Run: **aus vorhandenem Result ableiten**, nicht neu rechnen.

### assess-capacity-fit

**Ziel:** Passt die angefragte Leistung zum Trafo, zur Leitung und zur Spannungsebene?

**Schritte:**

1. `pqs`, `annahmen.leistung_mw_wirksam` und `requested_capacity` abgleichen.
2. `trafo` (Auslastung, Reserve) und `thermisch` (Strom vs. `i_max`) lesen.
3. `scores.kapazitaet`, `scores.gesamt`, `fazit.entscheidung` (A/B/C) zuordnen.
4. `feasibility_status` setzen:
   - `provisional_ok` — `fazit.entscheidung` A oder B **und** `n1.n1_klasse` in N1-0..N1-2 oder Datenluecken
   - `provisional_limited` — B mit Warnungen / thermischer Rand
   - `provisional_not_plausible` — C oder harte Verstoesse in `scores.harte_verstoesse`
   - `confirmed_ok` — nur bei dokumentierten NB-Daten (`n1.dso_daten_vorhanden`, N1-3/N1-4) **explizit als bestaetigt kennzeichnen**

**Engine-Keys:** `trafo`, `thermisch`, `scores`, `fazit`, `datenqualitaet`

---

### identify-bottlenecks

**Ziel:** Engpaesse explizit listen.

**Schritte:**

1. `n1.engpass_komponente`, `n1.detail_text`, `n1.bewertung` (GRUEN/GELB/ORANGE/ROT).
2. `n1_analyse.gesamt` falls vorhanden (Trafo-, Leitungs-, Abgangs-Engpass).
3. Stakeholder-API: `_engpaesse(result)` → thermisch / spannung / kurzschluss (`backend/api/stakeholders.py`).
4. Jeden Engpass: Komponente, Schwere, **Begruendung**, betroffene Groesse (z. B. Auslastung %, dU %).

**Engine-Keys:** `n1`, `n1_analyse`, `scores.harte_verstoesse`, `warnungen`

---

### assess-voltage-risk

**Ziel:** Spannungsfall / Spannungsband bewerten.

**Schritte:**

1. Block `spannung` (dU, Grenzwert, Bewertung).
2. `scores.spannung` und N-1-Spannungsszenario (`szenarien` → „N-1 Stoerungsfall“).
3. NS ≤3 %, MS ≤2 % als **Richtwerte** — TAB des VNB kann strenger sein → in `critical_constraints` vermerken.

**Engine-Keys:** `spannung`, `scores.spannung`, `szenarien`

---

### assess-thermal-risk

**Ziel:** Thermische Auslastung Leitung/Trafo.

**Schritte:**

1. `thermisch` (Auslastung, Strom, Bewertung).
2. `trafo` bei MS/HS-Station.
3. Parallele Systeme / Temperatur (`temperatur_c`) als Annahme in `assumption_list`.

**Engine-Keys:** `thermisch`, `trafo`, `scores.kapazitaet`

---

### assess-short-circuit-context

**Ziel:** Kurzschlusskontext — **kein** Sk'' ohne NB-Auskunft behaupten.

**Schritte:**

1. `kurzschluss`, `impedanz`, `sk_mva` (Default vs. Nutzereingabe).
2. Pruefen ob `sk_mva` aus `SK_DEFAULT` stammt → Annahme + Confidence senken.
3. Fehlende NB-Kurzschlussdaten → `critical_constraints` + Empfehlung „Sk'' beim VNB anfordern“.

**Engine-Keys:** `kurzschluss`, `impedanz`, `scores.kurzschluss`, `nb_check`

---

### formulate-boundary-conditions

**Ziel:** Randbedingungen fuer jedes positive/teilpositive Ergebnis.

**Schritte:**

1. `transparenz.disclaimers`, `disclaimer`, `engine_version`.
2. N-1-Klasse und `n1.stufenbegruendung` / `confidence_notes`.
3. Topologie (`topologie`, `redundanz`), fehlende `restkapazitaet_ms_mva`, Hybrid/Speicher (`speicher_bewertung`, `projektprofil`).
4. Kosten nur als Bandbreite (`kosten`) — keine exakte CAPEX-Zusage.

**Engine-Keys:** `transparenz`, `n1`, `warnungen`, `kosten`, `route_environment`

---

### generate-diagnosis-summary

**Ziel:** Verstaendliche Gesamtzusammenfassung (letzter Schritt).

**Schritte:**

1. `fazit.text` + `fazit.detail` in Klartext ueberfuehren.
2. Top-3 Engpaesse + Top-3 naechste Schritte aus `empfehlungen`.
3. `feasibility_status`, `confidence_level`, explizite Abgrenzung vorlaeufig vs. bestaetigt.
4. Disclaimer aus `docs/REPORT_GENERATOR_SPEC.md` sinngemaess einbinden.

**Engine-Keys:** `fazit`, `empfehlungen`, `warnungen`, `transparenz`

---

## Ausgabe-Schema (Diagnose-JSON)

Nach Abschluss aller Commands ein JSON-Objekt (Agent-Antwort oder Report-Vorstufe):

```json
{
  "feasibility_status": "provisional_ok | provisional_limited | provisional_not_plausible | confirmed_ok | insufficient_basis",
  "feasibility_basis": "provisional | confirmed",
  "bottleneck_list": [
    {
      "component": "trafo | leitung | spannung | kurzschluss | abgang | topologie | daten",
      "severity": "low | medium | high | critical",
      "reason": "string",
      "engine_ref": "n1.engpass_komponente | thermisch | ..."
    }
  ],
  "critical_constraints": [
    "string — z. B. N-1 nur N1-2, Sk'' aus Default, MS-Restkapazitaet unbekannt"
  ],
  "assumption_list": [
    {
      "field": "sk_mva | trafo_s_mva | leitungstyp | ...",
      "assumed_value": "string | number",
      "source": "default | user | missing",
      "material_to_result": true
    }
  ],
  "recommended_next_steps": [
    "string — aus empfehlungen, priorisiert, actionable"
  ],
  "confidence_level": "low | medium | high",
  "confidence_drivers": [
    "string — z. B. N1-1, 3 Default-Annahmen, keine DSO-Daten"
  ],
  "diagnosis_summary": "string — 3–8 Saetze, erklaerend",
  "boundary_conditions": [
    "string — Pflicht bei positivem/teilpositivem Ergebnis"
  ],
  "engine_artifacts": {
    "engine_version": "from result.engine_version",
    "fazit_entscheidung": "A | B | C",
    "n1_klasse": "N1-0 .. N1-4",
    "scores_gesamt": 0
  },
  "disclaimer": "Vorlaeufige technische Vorbewertung — keine verbindliche Netzanschlusspruefung durch den zustaendigen Netzbetreiber."
}
```

### Confidence-Ableitung (Richtlinie)

| Signal | confidence_level |
|--------|------------------|
| `datenqualitaet` niedrig, viele Defaults, N1-0/N1-1 | `low` |
| N1-2, einzelne NB-Felder, Score 40–70 | `medium` |
| N1-3+ mit `dso_daten_vorhanden`, wenige Annahmen, Score ≥70 | `high` (weiterhin nur *technisch*, nicht rechtsverbindlich) |

Material assumptions → mindestens eine Stufe abwaerts.

---

## Failure-Mode: insufficient basis

Wenn keine belastbare Diagnose moeglich ist (Validierung fehlgeschlagen, bewusst kein Annahmemodus, widerspruechliche Pflichtdaten):

```json
{
  "feasibility_status": "insufficient_basis",
  "feasibility_basis": "none",
  "diagnosis_summary": "Diagnose auf unzureichender Datenbasis nicht belastbar moeglich.",
  "confidence_level": "low",
  "required_data_for_next_step": [
    "nennspannung_kV",
    "leistung_mw",
    "leitungstyp",
    "entfernung_km",
    "anschlussart",
    "sk_mva_vom_netzbetreiber",
    "umspannwerk_trafos_oder_restkapazitaet_ms_mva"
  ],
  "bottleneck_list": [],
  "critical_constraints": [],
  "assumption_list": [],
  "recommended_next_steps": [
    "Eingabevalidierung abschliessen",
    "Fehlende Pflichtfelder gemaess validiere_eingabe ergaenzen",
    "Bei NB-Abhaengigkeit: formale Netzauskunft einholen"
  ],
  "boundary_conditions": [],
  "disclaimer": "Keine Bewertung — Datenbasis unzureichend."
}
```

Engine-Fehlerfall: `berechne_netzanschluss` → `status: "FEHLER"`, `fehler[]` — 1:1 in `required_data_for_next_step` uebersetzen.

---

## Success-Kriterien (Skill)

- [ ] Ausgabe erklaert **warum** Anschluss funktionieren kann oder scheitern kann
- [ ] Engpaesse sind explizit (`bottleneck_list`)
- [ ] Annahmen sichtbar (`assumption_list`, `transparenz`)
- [ ] Empfehlungen sind umsetzbar (`recommended_next_steps`)
- [ ] Keine verbindliche Freigabe, vorlaeufig vs. bestaetigt getrennt

---

## Agent-Aufruf

1. Skill lesen: `.cursor/skills/gridcheck-netzdiagnose/SKILL.md`
2. Kontext: validiertes Projekt / letztes Analyze-Ergebnis / `POST /api/v1/analyze`-Payload
3. Optional Engine lokal: `from engine.berechnung import berechne_netzanschluss` (Tests: `backend/tests/test_berechnung.py`)
4. Commands der Reihe nach oder parallel auf **demselben** Engine-Result ausfuehren
5. Diagnose-JSON ausgeben; bei Luecken → `insufficient_basis`

**Discovery:** Cursor laedt Project Skills aus `.cursor/skills/` — Beschreibung im Frontmatter fuer automatische Zuordnung; explizit `@gridcheck-netzdiagnose` oder „nutze gridcheck-netzdiagnose“ im Prompt.

---

## Referenzen

| Thema | Pfad |
|-------|------|
| Rechenkern | `backend/engine/berechnung.py` |
| N-1-Analyse | `backend/engine/n1_analyse.py` |
| Analyze-API v2 | `backend/api/analyze_v2.py` |
| Projektierer-API | `backend/api/v1_projektierer.py`, `backend/roles/projektierer.py` |
| Stakeholder-Engpaesse | `backend/api/stakeholders.py` |
| Report-Pflichten | `docs/REPORT_GENERATOR_SPEC.md` |
| Arbeitsweise / N-1-Regeln | `.cursor/rules/06-arbeitsweise-gridcheck.mdc` |
| API-Standard (bei Endpoint-Aenderung) | `.cursor/skills/project-api-skill/SKILL.md` |
