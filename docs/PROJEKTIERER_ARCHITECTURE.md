# Projektierer architecture — plant types & grid screening v2

## Purpose

Structured **Projektierer** inputs (plant type, AC/DC, cos φ, Gleichzeitigkeit) feed the **authoritative** Python engine. The frontend captures and displays values only; it does not perform netztechnische Berechnungen.

## Source of truth

| Layer | Role |
|-------|------|
| `backend/engine/plant_types.py` | **Canonical** `PlantType`, `PlantTypeConfig`, `PlantContext`, EEG/reactive defaults |
| `backend/engine/grid_calculation_v2.py` | Maps legacy `eingabe` → `GridConnectionInput`, runs screening |
| `frontend/lib/schemas/plant-types.ts` | **Mirror** for Zod/UI labels — must stay aligned with Python exports |

## Plant type model

### `PlantType` (API / storage)

`pv` | `wind` | `bess` | `hybrid_pv_bess` | `chp` | `hydro` | `consumption`

**Legacy aliases** (read-only, normalized on ingest):

- `hybrid` → `hybrid_pv_bess`
- `solar` / `PV` → `pv` (via `anlagentyp`)

### `FeedInManagementClass`

Derived from **AC** power at grid connection (`classify_feed_in_management`):

| Class | AC power |
|-------|----------|
| `none` | &lt; 25 kW |
| `remote_control` | 25–99.99 kW (§9 EEG 2023 screening) |
| `direct_marketing` | ≥ 100 kW |

Qualitative only — no fabricated curtailment costs.

### `ReactivePowerMode`

Describes how blind power is **expected** to be provided (screening checklist, not automatic Q calculation):

`fixed_cos_phi` | `cos_phi_p` | `q_u` | `q_setpoint` | `bidirectional`

Threshold **135 kW AC** triggers extended reactive-power checklist (VDE-AR-N 4105/4110).

## `PlantTypeConfig` fields

| Field | Use |
|-------|-----|
| `label` / `label_en` | UI & reports (DE primary) |
| `default_power_factor` | cos φ default if user does not override |
| `power_factor_range` | Validation band for user override |
| `default_simultaneity_factor` | Screening power = AC × factor (except consumption → 1.0) |
| `simultaneity_note` | Documented in assumptions / Projektierer perspective |
| `reactive_power_capable` | Whether Q-modes are technically plausible |
| `default_reactive_power_mode` | Default checklist focus |
| `has_dc_side` | PV / hybrid: optional `dc_kwp`, DC/AC ratio in assumptions only |
| `default_norm_reference` | Per `low` / `medium` / `high` voltage level |
| `feed_in_profile_note` | Qualitative Einspeisecharakter (no capacity claim) |
| `project_type` | Maps to `GridConnectionInput.project_type` |

## `GridConnectionInput` — additive extension

Existing v2 API and `grid_calculation_v2` JSON remain valid. New optional fields:

| Field | Meaning |
|-------|---------|
| `plant_type` | Normalized `PlantType` value |
| `ac_kw` | AC-Anschlussleistung (Netz) |
| `dc_kwp` | DC peak (PV/hybrid), assumptions only |
| `screening_power_kw` | AC × Gleichzeitigkeit (engine-filled) |
| `power_factor` | cos φ used in ΔU / thermal — **from plant default unless user override** |
| `simultaneity_factor` | Copy of plant default for audit trail (optional) |
| `reactive_power_mode` | From plant config unless user sets `reactive_power_mode` in `eingabe` |

**Rules**

1. **Calculations use AC** (`power_kw` = `ac_kw` at connection point).
2. **DC kWp** appears only in `CalculationAssumption` / `projektierer_perspective`, not as grid load.
3. **Gleichzeitigkeit** applies to generation/storage screening: `screening_power_kw = ac_kw × default_simultaneity_factor` (consumption: `screening_power_kw = ac_kw`).
4. **Voltage drop & thermal** use `_effective_screening_kw()` = `screening_power_kw` or `power_kw`.
5. **Feasibility** NS power-limit hints use screening kW where noted (conservative for generation).

## Conflict analysis (resolved)

| Topic | Legacy / parallel | Decision |
|-------|-------------------|----------|
| `hybrid` vs `hybrid_pv_bess` | Frontend had `hybrid` | Canonical ID `hybrid_pv_bess`; alias `hybrid` on read |
| `cos_phi` in wizard vs engine | `fachliche_hilfen` + form defaults | Single resolution in `resolve_plant_context`; wizard sends `cos_phi` + optional `cos_phi_known` |
| `leistung_mw` / `p_kw` / `ac_kw` | Multiple power fields | Priority: `ac_kw` / `ac_power_kw` → `leistung_mw`×1000 → `p_kw` |
| `dc_kwp` vs `dc_power_kwp` | Naming drift | Both accepted; alias in resolver |
| Frontend `PLANT_COS_PHI` | Duplicate table | Deprecated for authoritative path; mirror `plant-types.ts` for display hints only |
| `gridcheck-engine.ts` cos φ | Client-side default | Display-only; API payload uses backend resolution after analyze |
| N-1 / Trafo screening | Separate modules | Unchanged; plant type enriches assumptions only |
| No free capacity | OSM / heuristics | NVP recommendation remains heuristic + disclaimer |

## Data flow

```mermaid
flowchart LR
  Wizard[ProjectProfileFields / GridCheckForm]
  API[analyze payload]
  Resolver[resolve_plant_context]
  Map[grid_connection_input_from_engine]
  V2[calculate_grid_connection]
  UI[GridCalculationV2Panel]

  Wizard --> API
  API --> Resolver
  Resolver --> Map
  Map --> V2
  V2 --> UI
```

## Wizard fields (frontend)

Collected in `ProjectProfileFields` (additive):

- `plant_type`, `dc_kwp`, `ac_kw` (optional override of Anschlussleistung)
- `cos_phi` + `cos_phi_known`
- `eigenverbrauch_pct`, `storage_profile.energy_kwh`
- `inbetriebnahme`, `leitungsart` / topology (existing)
- Plant-type hint table (German) from schema mirror

## Tests & DoD

- `pytest tests/test_projektierer_plant_types.py`: PV AC vs DC, wind Gleichzeitigkeit 0.35, EEG 30 kW class
- `npm run build` (frontend) after schema mirror update
- No Impressum changes; no cumulative grid capacity claims

## Related docs

- `docs/NB_AKZEPTANZ_SCREENING.md` — EEG, reactive, coincidence blocks
- `.cursor/rules/03-elektrotechnik.mdc` — norm levels NS/MS/HS
