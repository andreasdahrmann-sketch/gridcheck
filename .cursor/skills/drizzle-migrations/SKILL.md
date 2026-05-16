---
name: drizzle-migrations
description: >-
  Manage database schema changes in a controlled, traceable, reversible way.
  Use when planning or reviewing PostgreSQL schema migrations, Alembic revisions,
  rollback strategy, audit-table safety, or (after approved Drizzle migration project)
  drizzle-kit workflows. Do not use to run upgrades on production without explicit user
  approval, when ADR-010 Alembic path is bypassed, or when schema drift should be stamped
  instead of diagnosed.
---

# drizzle-migrations (Gridcheck)

## Purpose

Manage database schema changes in a **controlled, traceable, reversible** way.

This skill names **Drizzle migration concepts** (diff, generate, safety, rollback, audit context) so agents apply a consistent workflow. **Gridcheck’s binding stack today is Alembic + SQLAlchemy** — see [Stack reality](#stack-reality) below. Do not install Drizzle or run `drizzle-kit` unless the user explicitly approved a **Drizzle migration project** and `DECISIONS.md` was updated.

Cross-references:

- `.cursor/rules/05-workflow.mdc` — Revisionssicherheit, append-only, `deleted_at`
- `.cursor/rules/01-backend.mdc` — Alembic-only migrations, reversible `down()`, PostgreSQL tests
- `DECISIONS.md` — **ADR-008** (PostgreSQL 16 + PostGIS), **ADR-010** (Alembic-only), **ADR-011** (PostgreSQL-only tests)
- `backend/core/config.py` — `AUTO_CREATE_SCHEMA` forbidden; schema only via migrations

---

## Stack reality

| Layer | Current (binding) | Target (not active) |
|-------|-------------------|---------------------|
| ORM | SQLAlchemy 2.x — `backend/db/models.py` | Drizzle schema (future; `PROJECT_RULES.md` mentions Drizzle as Zielbild only) |
| Migrations | **Alembic** — `backend/alembic/`, `backend/alembic/versions/` | `drizzle-kit` + `drizzle/` output dir (no package in repo yet) |
| DB | PostgreSQL 16 + PostGIS (Docker, port 5433 local) | same |
| Tests | `backend/tests/postgres_test_utils.py` → `run_alembic_upgrade()` | same until ADR changes |

**ADR conflict rule:** If this skill’s Drizzle examples contradict **ADR-010**, **ADR-010 wins**. Agents must use **Alembic** until a new ADR approves Drizzle and documents cutover. Never run `npm install drizzle-orm` / add `drizzle-kit` without that approval.

**Naming convention (Alembic, in use):** `YYYYMMDD_NN_short_slug.py` (e.g. `20260512_03_revision_chain_postgres.py`), docstring with ticket/milestone when applicable.

---

## use-when

- Adding or changing tables, columns, indexes, FKs, or PostGIS geometry columns
- Reviewing a migration PR before merge or deploy
- Diagnosing schema drift (tables without Alembic stamp, `DuplicateTable` on upgrade)
- Planning rollback / downgrade and staging verification
- Touching **audit**, **revision**, or **append-only** tables
- Preparing deploy checklist for Railway (`alembic upgrade head` — migrations **before** app in prod per deployment rules)

## do-not-use-when

- User only wants application/API logic with **no** schema change
- Input is “fix data” (DML) — use a one-off script or admin task, not a schema migration skill
- Production upgrade is requested but **staging proof**, **backup**, or **rollback** plan is missing (→ failure-mode)
- Shortcut requested: `alembic stamp head`, `Base.metadata.create_all()`, or silent audit-table rewrite
- Drizzle tooling is requested but **no** approved Drizzle migration ADR exists (→ Alembic path only)

---

## inputs

| Skill input | Gridcheck source |
|-------------|------------------|
| `schema_intent` | Issue/PR description, ticket ID, milestone |
| `model_changes` | Diff in `backend/db/models.py` (SQLAlchemy) |
| `current_db_revision` | `alembic current` against target `DATABASE_URL` |
| `target_environment` | `local` \| `staging` \| `prod` |
| `affected_tables` | From model diff + `backend/alembic/env.py` `include_tables` allowlist |
| `data_volume_risk` | Row counts / `COUNT(*)` on affected tables before destructive ops |
| `ticket_ref` | GitHub issue, milestone, or `DECISIONS.md` note |

## outputs

| Skill output | Description |
|--------------|-------------|
| `migration_file` | New file under `backend/alembic/versions/` (Alembic today) |
| `schema_diff_summary` | Human-readable before/after |
| `rollback_notes` | `downgrade()` steps + `alembic downgrade` target |
| `safety_classification` | `additive` \| `breaking` \| `destructive` |
| `verification_checklist` | Staging/prod steps |
| `audit_context_block` | Ticket, risk, backup path, ADR refs |
| `risk_rollback_report` | Required on high-risk / failure-mode |

---

## hard-rules

1. **Versioned only** — Every schema change = one new migration revision in Git. No `create_all()` in app startup (`backend/core/config.py` enforces this).
2. **Reason required** — Migration docstring: what, why, ticket/milestone link.
3. **Breaking changes** — Require explicit user/product approval in task or PR; classify with `classify-breaking-change` before merge.
4. **Destructive changes** — Mandatory: backup proof + tested `downgrade()` (or documented irreversible rationale + data migration plan). No `DROP`/`TRUNCATE` on populated audit/revision tables without approval.
5. **Audit / revision tables — never silent change** — Includes at minimum: `revision_records`, `ki_feedback_records`, `report_revisions` (and related), `gridcheck_result_audit`, hash-chain columns (`previous_hash`, `hash`, `revisionsnummer`). Prefer **new tables/columns**; never rewrite history in place. Align with append-only rules in `05-workflow.mdc`.
6. **Soft-delete** — Business deletes use `projects.deleted_at` (and same pattern elsewhere). Migrations must not hard-delete project rows for “delete feature”; schema may add `deleted_at`, not remove audit history.
7. **Staging before prod** — `alembic upgrade head` on staging with same migration chain; checklist emitted before prod.
8. **Referential integrity** — FK order in `upgrade()` / `downgrade()`; use `CASCADE` only deliberately; document in `rollback_notes`.
9. **Human-readable timestamped names** — `YYYYMMDD_NN_slug` + clear `revision` id string inside file.
10. **Link ticket/milestone** — Docstring header: `Ticket: #123` or `Milestone: …`.
11. **PostGIS** — Extension and geometry types: verify Docker image has PostGIS; document `CREATE EXTENSION` in migration if new env; test geo queries if geometry columns change.
12. **PostgreSQL-only** — No SQLite compatibility shims (ADR-011).
13. **Managed tables** — Alembic `env.py` scopes autogenerate to explicit table set; new tables must be added to that allowlist when introduced.

---

## commands

Agents invoke this skill by **name** (`drizzle-migrations`) when the task matches `use-when`. Execute the relevant command workflow below; produce outputs using [Output templates](#output-templates).

### Parallel map: Drizzle concept → Gridcheck today (Alembic)

| Skill command | Alembic / repo today | Drizzle (only after approved project) |
|---------------|----------------------|--------------------------------------|
| analyze-schema-diff | Compare `models.py` vs DB; `alembic history`; optional `alembic check`; psql `\d` | `drizzle-kit check` / introspect |
| generate-migration | `alembic revision -m "slug"` (+ hand-edit or `--autogenerate` if configured) | `drizzle-kit generate` |
| validate-migration-safety | Review `upgrade`/`downgrade`, FKs, audit rules | `drizzle-kit check` + manual review |
| prepare-rollback | Implement/test `downgrade()`; `alembic downgrade -1` | `drizzle-kit drop` / down SQL |
| emit-verification-checklist | See template below | Same checklist, different CLI |
| classify-breaking-change | See workflow | Same classification |
| attach-audit-context | Docstring + PR body block | Same |

**PowerShell (ADR-007):** Prefer commands from repo root / `backend/` as documented in `README.md` and `docs/railway-deployment.md`.

---

### analyze-schema-diff

**Workflow**

1. Read `backend/db/models.py` and recent `backend/alembic/versions/*.py`.
2. Confirm `DATABASE_URL` points to intended DB (local Docker 5433 vs staging).
3. Run (from `backend/`, venv active):
   - `python -m alembic current`
   - `python -m alembic history --verbose`
4. Compare live schema: `psql` → `\d table`, `\dx` for PostGIS, list tables vs `env.py` allowlist.
5. If upgrade previously failed: full drift inventory (see `DECISIONS.md` 2026-05-13 — do not stamp blindly).
6. Produce `schema_diff_summary` (tables/columns/indexes/FK deltas).

**Do not** recommend `alembic stamp head` to hide drift.

---

### generate-migration

**Workflow**

1. Complete `analyze-schema-diff` and `classify-breaking-change`.
2. Update SQLAlchemy models in `backend/db/models.py` (single focused change).
3. If new table: add name to `backend/alembic/env.py` `include_tables` / target metadata as required by project setup.
4. Create revision (from `backend/`):
   ```powershell
   python -m alembic revision -m "YYYYMMDD_NN_short_slug"
   ```
   Autogenerate only if project config supports it and diff was reviewed; **always** hand-review generated ops.
5. Implement `upgrade()` and **`downgrade()`** (reversible unless ADR-approved exception).
6. Run `attach-audit-context` in file docstring.
7. Output `migration_file` path + `schema_diff_summary`.

**Forbidden without user approval:** `npm install` Drizzle packages; new `drizzle.config.ts`.

---

### validate-migration-safety

**Workflow**

1. Load generated `migration_file`; trace every `op.create_*`, `op.drop_*`, `op.alter_column`, `batch_alter_table`.
2. Check hard-rules: audit tables, `deleted_at`, FK order, PostGIS.
3. For destructive ops: require `data_volume_risk` = 0 or backup ticket referenced.
4. Confirm `downgrade()` mirrors `upgrade()` and is tested locally:
   ```powershell
   python -m alembic upgrade head
   python -m alembic downgrade -1
   python -m alembic upgrade head
   ```
5. Run tests that migrate DB: `pytest` (fixtures call `run_alembic_upgrade` in `postgres_test_utils.py`).
6. Set `safety_classification` and list blockers.

**Stop auto-execution** if classification is `destructive` or `breaking` without documented approval.

---

### prepare-rollback

**Workflow**

1. Document `down_revision` chain from `migration_file`.
2. Write `rollback_notes`: exact `alembic downgrade <rev>` targets; data preserved/lost; re-upgrade steps.
3. For prod: reference backup path (`pg_dump` custom format — see `DECISIONS.md` milestone backup example).
4. If downgrade is unsafe (column type narrowing with data): mark **irreversible** and require forward-only plan + user sign-off.
5. Output `risk_rollback_report` section when risk ≥ medium.

---

### emit-verification-checklist

**Workflow**

Emit checklist (customize per migration):

- [ ] Docker Postgres + PostGIS up (local 5433)
- [ ] `DATABASE_URL` correct for environment
- [ ] `python -m alembic current` recorded before upgrade
- [ ] Backup taken (staging/prod) — path: `…`
- [ ] `python -m alembic upgrade head` on **staging**
- [ ] App smoke test (auth, project list, analyze path if touched)
- [ ] `alembic current` = expected head revision
- [ ] `downgrade -1` + `upgrade head` tested on disposable DB (if reversible)
- [ ] `pytest` relevant backend tests green
- [ ] Prod deploy: migration job **before** new app version (Railway / CI)
- [ ] Rollback owner + `rollback_notes` linked in PR

---

### classify-breaking-change

**Workflow**

| Class | Examples | Agent action |
|-------|----------|--------------|
| `additive` | New nullable column, new table, new index | Proceed with standard checklist |
| `breaking` | NOT NULL without default, rename column, type change, drop column | Require explicit approval; document app deploy order |
| `destructive` | `DROP TABLE`, `TRUNCATE`, narrow type with data loss | **Stop** auto execution; backup + rollback report mandatory |

Flag audit/revision table **any** non-additive change as at least `breaking`.

---

### attach-audit-context

**Workflow**

Add to migration module docstring and PR description:

```text
Ticket: #<id> | Milestone: <name>
Risk: additive | breaking | destructive
Backup: <path or N/A for local-only additive>
ADR: ADR-010 (Alembic), ADR-008 (Postgres/PostGIS)
Affected audit tables: <list or "none">
Rollback: alembic downgrade <revision_id>
```

For Gridcheck revision chain features, note dependency on `revision_records` / `engine/revision.py` hash chain — schema must not break hash verification in `api/v2_reports.py`.

---

## Output templates

### schema_diff_summary

```markdown
## Schema diff summary
- **Environment:** local | staging | prod
- **DB revision (before):** <alembic current>
- **Intent:** <one sentence>
- **Tables affected:** <list>
- **Columns:** add | alter | drop — <detail>
- **Indexes/FKs:** <detail>
- **PostGIS:** yes/no — <detail>
- **Audit tables touched:** yes/no — <names>
```

### migration_file (Alembic)

```text
Path: backend/alembic/versions/YYYYMMDD_NN_slug.py
Revision ID: <revision>
Revises: <down_revision>
```

### rollback_notes

```markdown
## Rollback
- **Command:** `python -m alembic downgrade <target_rev>` (from `backend/`)
- **Data impact:** <what is lost/preserved>
- **Re-apply:** `python -m alembic upgrade head`
- **Irreversible:** yes/no — <reason>
```

### verification_checklist

Use bullet list from `emit-verification-checklist` with checked items and timestamps when executed.

### risk_rollback_report (high risk / failure-mode)

```markdown
## Risk & rollback report
- **Classification:** breaking | destructive
- **Blockers:** <list>
- **Backup:** <required | missing>
- **Downgrade tested:** yes/no
- **Recommended action:** manual review | proceed staging | do not deploy
- **Stakeholder sign-off required:** yes/no
```

---

## Gridcheck-specific tables (migration sensitivity)

| Table / pattern | Rule |
|-----------------|------|
| `revision_records`, `ki_feedback_records`, report revision tables | Append-only hash chain; no in-place history rewrite |
| `gridcheck_result_audit` | Audit trail; additive only unless explicit compliance review |
| `projects.deleted_at` | Soft-delete; queries filter `deleted_at IS NULL` |
| Monetization / package / ops followup migrations | Follow existing `20260511_*`, `20260512_*` patterns |
| PostGIS geometries | Test on Docker image; document SRID/类型 |

Reference migration: `20260512_03_revision_chain_postgres.py`.

---

## success-criteria

- Migration file exists with paired `upgrade()` and `downgrade()` (or documented irreversible exception with approval)
- `schema_diff_summary` and `safety_classification` produced
- Ticket/milestone linked via `attach-audit-context`
- Staging checklist emitted; prod steps documented if deploy-related
- No violation of ADR-010 or audit hard-rules
- Tests/migration path verified on PostgreSQL (not SQLite)

---

## failure-mode

**Trigger:** high risk (`destructive`, audit-table breaking change), drift with unknown origin, failed upgrade mid-chain, or missing backup/rollback.

**Agent must:**

1. **Stop auto execution** — do not run `alembic upgrade` on prod/staging without user confirmation.
2. **Manual review** — summarize drift, failed revision, psql evidence.
3. **Emit `risk_rollback_report`** — classification, blockers, backup status, recommended next step.
4. **Never** default to `alembic stamp head` to “fix” `DuplicateTable` (see `DECISIONS.md` 2026-05-13).

### Failure JSON (agent output)

```json
{
  "status": "migration_blocked",
  "reason": "high_risk | drift | missing_rollback | adr_conflict",
  "safety_classification": "destructive",
  "auto_execution": false,
  "schema_diff_summary": null,
  "risk_rollback_report": {
    "blockers": ["..."],
    "backup": "missing",
    "recommended_action": "manual_review"
  },
  "next_steps": [
    "Complete drift inventory",
    "Obtain backup proof",
    "Get explicit approval for breaking change"
  ]
}
```

---

## Standard agent workflow (Gridcheck)

1. Read `DECISIONS.md` (ADR-008, ADR-010, ADR-011) and affected `models.py` / latest alembic version.
2. Confirm task is schema migration (one focused change).
3. Run commands in order: `analyze-schema-diff` → `classify-breaking-change` → `generate-migration` → `validate-migration-safety` → `prepare-rollback` → `emit-verification-checklist` → `attach-audit-context`.
4. Deliver outputs; **do not** commit or run prod migrations unless user asked.
5. If Drizzle adoption requested: stop and ask for ADR update + migration project approval first.

---

## How agents invoke this skill

1. Cursor loads skills from `.cursor/skills/*/SKILL.md` when description matches the task.
2. User or parent agent references: **“use drizzle-migrations skill”** or schema/migration keywords in `use-when`.
3. Agent reads this file **first**, follows **Alembic** paths unless Drizzle ADR exists, applies command workflows and templates.
4. For API-only work, use `project-api-skill` instead — do not conflate router changes with schema migrations.

---

## Future: Drizzle cutover (not active)

When approved and documented in `DECISIONS.md`:

- Target layout (proposal only): `backend/drizzle/schema.ts`, `backend/drizzle/migrations/`, `drizzle.config.ts`
- Map `drizzle-kit generate` → `generate-migration`, `drizzle-kit migrate` → deploy step
- **Dual-run period** must be explicitly ADR’d; until then Alembic remains sole source of truth

Do **not** implement cutover as part of this skill file maintenance unless user requests the migration project.
