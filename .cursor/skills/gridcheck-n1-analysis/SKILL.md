---
name: gridcheck-n1-analysis
description: >-
  Assesses N-1 resilience and contingency-related connection feasibility under predefined outage scenarios.
  Use when medium-voltage or higher connections are evaluated, transformer or feeder redundancy matters,
  contingency cases affect usable capacity, or operational security constraints are relevant.
  Do not use when no contingency model exists, the project is too small for meaningful N-1 relevance,
  or required topology data is missing.
---

# gridcheck-n1-analysis

## purpose

Assess N-1 resilience and contingency-related connection feasibility under predefined outage scenarios.

## use-when

Use when:

- medium-voltage or higher connection scenarios are evaluated
- transformer or feeder redundancy matters
- contingency cases affect usable capacity
- operational security constraints are relevant

## do-not-use-when

Do not use when:

- no contingency model exists
- project is too small for meaningful N-1 relevance and business rules exclude it
- required topology data is missing

## inputs

| Skill input | Engine / API field | Notes |
|-------------|-------------------|--------|
| `topology_data` | `eingabe.topologie`, `eingabe.restkapazitaet_ms_mva` | MS topologies via `n1_ms.TOPOLOGIEN` (`stich`, `ring_offen`, …) |
| `transformer_configuration` | `eingabe.umspannwerk.trafos[]` | `sn_mva`, `belastung_aktuell_mw` |
| `feeder_configuration` | `eingabe.umspannwerk.abgaenge[]`, `parallele_systeme`, `redundanz` | Abgang: `i_max_a`, `belastung_aktuell_a`, `reserve_n1_a` |
| `switching_options` | `umschaltzeit_min`, `koppelbar`, `verfuegbar_im_n1`, `primary` | Explicit in `bewerte_abgang_n1` assumptions |
| `load_flow_base_case` | `berechne_szenarien` base case + `thermisch` / `spannung` | Not full load-flow; heuristic screening |
| `outage_scenarios` | Szenario `"N-1 Stoerungsfall"` | Feeds `analysiere_n1(thermisch_n1, spannung_n1)` |
| `requested_capacity` | `leistung_mw`, `cos_phi`, `nennspannung` | Project current → `projektstrom_a` |
| `operational_limits` | `engine/n1_analyse.GRENZEN`, `constants.MS_SPANNUNG_N1_SCREENING` | Trafo/Leitung/Spannung/Abgang thresholds |

Data basis: `eingabe.n1_datengrundlage` / `umspannwerk.datenquelle` → `dso_verified` enables N1-4 path.

## outputs

| Skill output | Primary code source |
|--------------|---------------------|
| `n1_status` | `n1.bewertung`, `n1.n1_sicher`, `n1_analyse.gesamt.bewertung` |
| `limiting_scenario` | `n1.engpass_komponente`, component `begruendung_*` |
| `remaining_capacity_estimate` | `n1_ms.kennzahlen.restkapazitaet_ms_mva`, `n1_abgang.beste_reserve_a`, `*_auslastung_n1_prozent` |
| `violated_constraints` | Components with `bewertung == "ROT"` |
| `switching_dependency_notes` | `n1_abgang`, `n1_topologie`, `umschaltzeit_min` |
| `reinforcement_candidates` | `n1.detail_empfehlungen`, `n1_analyse.gesamt.empfehlungen` |
| `confidence_level` | `n1.n1_konfidenz`, `n1_analyse.gesamt.konfidenz`, `n1_klasse` |

Downstream: `engine/gridcheck_report_mapper._n1_screening` → report `technicalAssessment.n1Screening`; stakeholder PDFs via `projektierer.py` / `vnb.py`; frontend `N1AssessmentPanel.tsx`, `analyze.ts` mapping.

## hard-rules

- N-1 analysis must always name the contingency scenario.
- Never state N-1 compliance without topology basis.
- If switching assumptions are used, they must be explicit.
- Distinguish asset outage, feeder outage, and transformer outage.
- If result depends on operator action, mark as operationally conditional.
- If topology is incomplete, produce no false-positive N-1 result.

### N-1 levels (project binding)

From `.cursor/rules/06-arbeitsweise-gridcheck.mdc` and `03-elektrotechnik.mdc`:

| Level | Meaning |
|-------|---------|
| N1-0 | Keine N-1-Aussage möglich |
| N1-1 | Heuristisches Screening |
| N1-2 | Topologische Näherung |
| N1-3 | Lastfluss mit geschätzten Parametern |
| N1-4 | Lastfluss mit verifizierten Netzbetreiberdaten |

**MVP policy:** ohne Netzbetreiberdaten extern **maximal N1-1 oder N1-2** behaupten — auch wenn die Engine intern `N1-3` liefert (heuristische Komponenten vollständig). In UI/Reports die Stufe nennen, Limitationen aus `nachweise_fehlend` / `detail_annahmen` mitführen, keine Compliance-Zusage.

**Implementation:** `engine/n1_analyse.bestimme_n1_klasse` setzt N1-4 nur bei `dso_verified`; N1-3 bei allen fünf Komponenten geprüft (ohne DSO).

## commands

### build-contingency-set

**Workflow**

1. Confirm `parallele_systeme`, `topologie`, `redundanz` in engine input.
2. Read `berechne_szenarien` in `backend/engine/berechnung.py` — four mandatory scenarios; outage case is `"N-1 Stoerungsfall"`.
3. If `parallele_systeme >= 2`, scenario scales `r_ges`/`x_ges` and recomputes `thermisch` + `spannung` for one parallel system out.
4. Pass scenario outputs into `analysiere_n1` as `thermisch_n1` / `spannung_n1`.

**Maps to**

- `szenarien[]` in engine result
- `n1_szenario = next(s for s in szenarien if s["name"] == "N-1 Stoerungsfall")`
- Missing scenario → `n1_analyse = {"status": "NICHT_BEWERTET", ...}`

### evaluate-transformer-outage

**Workflow**

1. Require `eingabe.umspannwerk.trafos` (≥2 for redundancy screening).
2. Call `bewerte_trafo_n1(umspannwerk, zusatzlast_mw, cos_phi)` — simulates loss of largest transformer.
3. Record scenario label: **transformer outage** at UW.

**Maps to**

- `n1_analyse.n1_trafo` (`auslastung_n1_prozent`, `engpass_trafo_idx`, `bewertung`)
- Prescreen: `berechne_n1_prescreen` → `trafo_n1`, `trafo_text`
- Engpass key: `trafo`

### evaluate-feeder-outage

**Workflow**

1. **Feeder / line outage:** `bewerte_leitung_n1(thermisch_n1)` from N-1 scenario thermal block (`auslastung_prozent`, `i_max_a`, `i_betrieb_a`).
2. **Feeder / switching path outage:** `bewerte_abgang_n1(eingabe, projektstrom_a)` — primary vs best alternative `reserve_n1_a` / `reserve_i_a`; switching explicit in `begruendung_technisch`.
3. **Topology / MS feeder concept:** `bewerte_n1_ms` via `analysiere_n1` → `n1_topologie`.
4. Never merge line and abgang violations into one unnamed scenario.

**Maps to**

- `n1_leitung`, `n1_abgang`, `n1_topologie`
- `berechne_n1_prescreen` → `leitung_n1`, `n1_auslastung_prozent`

### assess-remaining-capacity

**Workflow**

1. Topology reserve: `restkapazitaet_ms_mva` vs `scheinleistung_mva` in `n1_ms.kennzahlen`.
2. Abgang reserve: `n1_abgang.beste_reserve_a`, `reserve_ratio` vs `GRENZEN["abgang_reserve_ratio"]`.
3. Trafo reserve: implied by `100 - auslastung_n1_prozent` on remaining bank.
4. State units (MVA, A, %) and whether value is **screening estimate**, not guaranteed capacity.

**Maps to**

- `n1_ms.kennzahlen`, `n1_abgang`, `n1_trafo.auslastung_n1_prozent`
- Report mapper does not expose a dedicated “remaining kW” field — derive in agent narrative from above.

### detect-constraint-violations

**Workflow**

1. Collect all components where `bewertung == "ROT"` (and `GELB` as marginal).
2. Map to constraint classes: thermal (line/trafo), voltage (`delta_u_n1_prozent`), topology (`n1_sicher == False`), abgang reserve.
3. Merge with `scores.harte_verstoesse` if present in full engine run.
4. If `NICHT_GEPRUEFT`, list as **missing evidence**, not as pass.

**Maps to**

- Per-component blocks in `n1_analyse`
- `n1.bewertung` after `konsolidiere_n1_ergebnis`
- `warnungen` when `n1_klasse in ("N1-0","N1-1","N1-2")`

### summarize-limiting-scenario

**Workflow**

1. Read `n1.engpass_komponente` / `n1_analyse.gesamt.engpass_komponente` (`abgang` > `leitung` > `trafo` > `spannung` > `topologie` priority in engine).
2. Name the **named contingency**: e.g. “N-1 Stoerungsfall — Ausfall eines Parallelsystems” or “Trafo-N-1 — Ausfall groesster UW-Trafo”.
3. Attach `stufenbegruendung`, `n1_klasse`, `detail_text`.
4. Flag `n1_sicher is None` or `stich_mit_notverbindung` as **operationally conditional**.

**Maps to**

- `n1.detail_text`, `n1.stufenbegruendung`
- `gridcheck_report_mapper` → `n1Screening.summary`, `limitations`, `requiredFollowUp`

## success-criteria

- limiting contingency is identified
- usable capacity under outage is documented
- operational assumptions are explicit
- no fake certainty

## failure-mode

If topology data is incomplete:

- output `"N-1 not assessable"`
- list missing topology information

### Failure JSON (agent output)

Use when `topologie` is `unbekannt`/empty, `n1_klasse == "N1-0"`, or critical inputs absent **before** implying compliance:

```json
{
  "n1_status": "N-1 not assessable",
  "limiting_scenario": null,
  "remaining_capacity_estimate": null,
  "violated_constraints": [],
  "switching_dependency_notes": [],
  "reinforcement_candidates": [
    "Topologie und Restkapazitaet beim Netzbetreiber erfragen"
  ],
  "confidence_level": "low",
  "n1_klasse": "N1-0",
  "operationally_conditional": false,
  "missing_topology": [
    "topologie (MS-Anbindung: stich | ring_offen | doppelstich | …)",
    "restkapazitaet_ms_mva"
  ],
  "engine_reference": {
    "n1_topologie_bewertung": "NICHT_GEPRUEFT",
    "nachweise_fehlend": []
  }
}
```

Populate `missing_topology` from `n1.nachweise_fehlend`, `n1_analyse.annahmen[].feld`, and gaps in `eingabe` (no `umspannwerk`, no `abgaenge`, no `N-1 Stoerungsfall` scenario). Do **not** set `n1_sicher: true`.

## Standard-Workflow (Gridcheck)

1. **Scope:** MS+ or explicit N-1 requirement; one task only.
2. **Read** `backend/engine/n1_analyse.py`, `n1_ms.py`, N-1 section in `berechnung.py`.
3. **Run or inspect** engine path: `berechne(...)` → `n1`, `n1_analyse`, `szenarien`.
4. **Apply commands** above in order for structured review.
5. **Map** to skill output JSON (below).
6. **Tests:** `pytest backend/tests/test_n1_ms.py backend/tests/test_n1_analyse.py -q`; integration: `test_berechnung.py`, `test_gridcheck_report_mapper.py`.
7. **Report:** never upgrade N1 level beyond MVP policy without DSO data.

## Output JSON template (full fields)

After a successful engine run, normalize to:

```json
{
  "n1_status": "GRUEN | GELB | ROT | NICHT_GEPRUEFT | N-1 not assessable",
  "n1_sicher": true,
  "n1_klasse": "N1-2",
  "limiting_scenario": {
    "contingency_name": "N-1 Stoerungsfall",
    "outage_type": "feeder_outage | transformer_outage | topology | voltage",
    "engpass_komponente": "leitung",
    "summary": "Engine detail_text or stufenbegruendung"
  },
  "remaining_capacity_estimate": {
    "restkapazitaet_ms_mva": 10.0,
    "scheinleistung_mva": 5.26,
    "beste_abgangsreserve_a": 120.0,
    "trafo_n1_auslastung_prozent": 62.5,
    "unit_notes": "Screening-Werte, keine Kapazitätsgarantie"
  },
  "violated_constraints": [
    {
      "component": "n1_leitung",
      "bewertung": "ROT",
      "metric": "auslastung_n1_prozent",
      "value": 150.0,
      "limit": 100.0
    }
  ],
  "switching_dependency_notes": [
    "Konservativ nur beste einzelne alternative Abgangsreserve",
    "umschaltzeit_min: 15"
  ],
  "reinforcement_candidates": [
    "Groesseren Kabelquerschnitt oder zusaetzliches Parallelsystem pruefen"
  ],
  "confidence_level": 0.55,
  "operationally_conditional": true,
  "missing_topology": [],
  "disclaimer": "Vorläufiges N-1-Screening, keine Netzanschlusszusage.",
  "engine_reference": {
    "berechnungs_version": "n1-analyse-1.1.0",
    "backend": "heuristik_v2_planer",
    "components": ["n1_topologie", "n1_leitung", "n1_abgang", "n1_trafo", "n1_spannung"]
  }
}
```

## Command → code map (quick reference)

| Command | Python entry | Result keys |
|---------|--------------|-------------|
| `build-contingency-set` | `berechnung.berechne_szenarien` | `szenarien["N-1 Stoerungsfall"]` |
| `evaluate-transformer-outage` | `n1_analyse.bewerte_trafo_n1` | `n1_trafo` |
| `evaluate-feeder-outage` | `bewerte_leitung_n1`, `bewerte_abgang_n1`, `n1_ms.bewerte_n1_ms` | `n1_leitung`, `n1_abgang`, `n1_topologie` |
| `assess-remaining-capacity` | `n1_ms.kennzahlen`, abgang/trafo metrics | see template |
| `detect-constraint-violations` | component `bewertung`, `gesamt.bewertung` | `violated_constraints[]` |
| `summarize-limiting-scenario` | `n1_analyse._engpass`, `konsolidiere_n1_ergebnis` | `n1.detail_text`, report `n1Screening` |

Orchestrator: `n1_analyse.analysiere_n1` · Pipeline: `berechnung.berechne` → `berechne_n1_prescreen` + `analysiere_n1` → `konsolidiere_n1_ergebnis`.

## Verbindliche Leitplanken

1. Geschäftslogik bleibt im Backend; Frontend nur Anzeige (`N1AssessmentPanel`, `analyze.ts`).
2. `n1_sicher: true` nur wenn Topologie **und** Pfad **und** Trafo konsistent grün — `None` = Datenlücke, nicht Bestanden.
3. `stich` / `unbekannt` → kein positives N-1-Fazit ohne Nachweis.
4. Stakeholder-Reports: `n1_status` BESTANDEN/NICHT BESTANDEN ist grob — immer `n1_klasse` + `detail_text` daneben stellen.
5. Keine N1-4-Aussage ohne `n1_datengrundlage: dso_verified` (oder equivalent verified flags).

## Cross-reference: gridcheck-netzdiagnose

- **Cursor skill** `gridcheck-netzdiagnose`: not present under `.cursor/skills/` (optional future skill).
- **Legacy runtime skill:** `engine/skills/gridcheck-netzdiagnose.js` — high-level grid + N-1 feasibility narrative from simplified `engineResult.details`; **does not** replace MS topology / component N-1 engine.
- **Complementary use:** run **netzdiagnose** for overall connection diagnosis summary; run **gridcheck-n1-analysis** for contingency depth, N1 class, and explicit outage typing. Do not duplicate full N-1 component breakdown in netzdiagnose prose.

## Referenz-Dateien

| Area | Path |
|------|------|
| N-1 orchestrator | `backend/engine/n1_analyse.py` |
| MS topology screening | `backend/engine/n1_ms.py` |
| Engine integration | `backend/engine/berechnung.py` (`berechne_n1_prescreen`, `konsolidiere_n1_ergebnis`) |
| Report N-1 block | `backend/engine/gridcheck_report_mapper.py` (`_n1_screening`) |
| Tests | `backend/tests/test_n1_ms.py`, `test_n1_analyse.py`, `test_berechnung.py` |
| UI | `frontend/components/N1AssessmentPanel.tsx`, `frontend/lib/api/analyze.ts` |
| Rules | `.cursor/rules/06-arbeitsweise-gridcheck.mdc`, `03-elektrotechnik.mdc` |

## Ausgabeformat bei Skill-Arbeit

Kurzes Ergebnis mit:

1. `n1_klasse` + named contingency
2. Limiting component / scenario
3. MVP-policy caveat if engine > N1-2 without DSO
4. Tests (ausgeführt/offen)
