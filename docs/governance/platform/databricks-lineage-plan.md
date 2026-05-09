# Databricks Lineage Plan

Version: 1.0.0
Last updated: 2026-05-07
Authority: platform specification
Depends on:

- `docs/governance/00-product-constitution.md`
- `docs/governance/01-north-star-architecture.md`
- `docs/governance/02-agent-operating-loop.md`
- `AGENT_SYNC.md`
- `docs/agent-ledger/YYYY-MM-DD.md`

## Purpose

This document defines the Databricks platform design for Phase 2 lineage, auditability, and governed execution. It translates the repo-first governance operating system into machine-readable platform controls without rewriting product doctrine.

This is a platform specification, not constitutional law. If this file conflicts with the governance canon, the canon wins.

## Scope

This plan covers:

- medallion mapping for governance-relevant data
- lineage and audit tables for agent activity and artifact state
- source-rank enforcement policy in Databricks
- DAB, Jobs, and environment promotion expectations
- connection points between Databricks lineage and Markdown coordination artifacts
- implementation order after the governance seal PR is merged

This plan does not:

- amend `00-product-constitution.md`
- define DVU as constitutional law
- move sprint formulas into the constitution
- replace repo-resident governance artifacts as the primary operating surface in Phase 1

## Platform Principles

1. Repo-first, platform-second
   - `docs/governance/`, `AGENT_SYNC.md`, and the daily ledger remain the canonical Phase 1 operating system.
   - Databricks lineage extends governance visibility; it does not replace the repo source of truth.

2. Auditability over convenience
   - Every governed platform artifact should be attributable to a source, run, environment, and version.

3. Promotion over mutation
   - Production lineage tables and jobs are deployed through DABs and promoted Dev -> Staging -> Prod.
   - UI-only production edits are discouraged except for emergency triage.

4. Governance controls must be machine-checkable
   - Source rank, artifact status, freshness, and execution provenance should be queryable in Databricks.

## Medallion Mapping

### Bronze
Purpose:
* preserve raw operational records and snapshots
* land source extracts with minimal transformation
* retain original provenance and timestamps

Planned Bronze examples:
* raw source snapshots from approved football and metadata providers
* raw agent activity events derived from repo/session logs
* raw artifact discovery snapshots from repo scans or bundle manifests

Minimum Bronze fields:
* `ingest_ts`
* `source_system`
* `source_object`
* `source_version`
* `raw_payload`
* `run_id`
* `environment`

### Silver
Purpose:
* standardize, parse, and normalize lineage-relevant records
* resolve identities and map raw events to governed entities
* enforce schema quality before Gold publication

Planned Silver examples:
* normalized agent actions
* normalized artifact inventory
* source-rank conformance checks
* repo-to-platform linkage tables

Minimum Silver qualities:
* typed columns
* deduplicated natural keys where feasible
* parser/version metadata retained
* failed parsing and unresolved mappings triaged, not silently dropped

### Gold
Purpose:
* serve trusted governance, audit, and lineage tables
* expose compliance-ready operational facts
* support dashboarding, review, and policy checks

Initial Gold targets:
* `gen_alpha.gold.agent_activity_log`
* `gen_alpha.gold.artifact_registry`
* `gen_alpha.gold.roster`
* `gen_alpha.gold.draft_picks`
* `gen_alpha.gold.backtest_history`
* `gen_alpha.gold.opponent_picks`

Gold tables are governed outputs. Writes should be constrained to approved jobs and deployment paths.

## Gold Table Specification

### `gen_alpha.gold.agent_activity_log`

Purpose:
Track material agent and human governance actions across repo, Jobs, and platform execution.

Recommended columns:

| Column | Type | Description |
| --- | --- | --- |
| `activity_id` | string | Unique event identifier |
| `event_ts` | timestamp | When the activity occurred |
| `event_date` | date | Partition/helper date |
| `agent_name` | string | Agent or human actor name |
| `agent_type` | string | e.g. human, Genie, Codex, Gemini, Claude Code |
| `session_id` | string | Session or chat correlation id if available |
| `task_type` | string | review, draft, validate, deploy, lineage-sync, etc. |
| `action_type` | string | create, update, validate, promote, run, fail |
| `artifact_type` | string | doc, file, workflow, table, job, model, pipeline |
| `artifact_path` | string | Repo path or workspace path |
| `artifact_id` | string | Optional workspace/job/table identifier |
| `governance_doc_version` | string | Active doctrine version if tracked |
| `phase_alignment` | string | Active phase from architecture/roadmap |
| `environment` | string | dev, staging, prod |
| `job_name` | string | Lakeflow Job name if applicable |
| `job_run_id` | string | Job run identifier if applicable |
| `git_branch` | string | Source branch when known |
| `git_commit` | string | Commit SHA when known |
| `status` | string | success, warning, failed, blocked |
| `blocker_flag` | boolean | Whether the activity ended blocked |
| `blocker_reason` | string | Reason for blocked/failed state |
| `summary` | string | Concise description of change or action |
| `source_system` | string | repo, github, databricks_job, manual, etc. |
| `ingest_ts` | timestamp | Platform ingest time |

Recommended constraints/policies:
* immutable append-first pattern
* no hard deletes outside approved retention operations
* required `event_ts`, `agent_name`, `action_type`, `artifact_type`, `status`
* controlled vocab for `status`, `action_type`, `environment`

Primary uses:
* audit trail for governance actions
* linking Markdown ledger activity to platform execution
* surfacing blocked runs and doctrine drift
* future dashboarding of governance throughput and bottlenecks

### `gen_alpha.gold.artifact_registry`

Purpose:
Maintain the current governed inventory of key repo and platform artifacts.

Recommended columns:

| Column | Type | Description |
| --- | --- | --- |
| `artifact_registry_id` | string | Unique registry row id |
| `artifact_type` | string | governance_doc, bootstrap_file, script, workflow, table, model, query |
| `artifact_name` | string | Logical artifact name |
| `artifact_path` | string | Repo path or workspace path |
| `artifact_id` | string | Optional Databricks/workspace identifier |
| `canonical_flag` | boolean | Whether this is a canonical governed artifact |
| `authority_level` | string | constitution, architecture, workflow, bootstrap, platform |
| `owner` | string | Logical owner or agent role |
| `environment` | string | dev, staging, prod |
| `current_version` | string | Semantic version, commit, or bundle version |
| `git_commit` | string | Last known repo commit |
| `bundle_name` | string | DAB package name if applicable |
| `deployed_job_name` | string | Linked Lakeflow Job if applicable |
| `upstream_artifact_path` | string | Optional parent/canonical source |
| `lifecycle_state` | string | draft, active, archived, deprecated |
| `validation_status` | string | pass, warning, fail, unknown |
| `source_rank_policy` | string | Policy reference where applicable |
| `last_validated_ts` | timestamp | Last governance validation time |
| `last_promoted_ts` | timestamp | Last environment promotion time |
| `notes` | string | Short operational notes |
| `ingest_ts` | timestamp | Platform ingest time |

Primary uses:
* governed inventory of doctrine and enforcement artifacts
* promotion tracking across environments
* validation visibility for bootstrap files and key controls
* future dependency mapping between repo assets and platform assets

### `gen_alpha.gold.backtest_history`

Purpose:
Track historical model predictions vs actual realized fantasy performance to calibrate the "Trust Flywheel".

Recommended columns:

| Column | Type | Description |
| --- | --- | --- |
| `dg_id` | string | Canonical player identifier |
| `prediction_date` | date | Date of the model prediction |
| `predicted_value` | double | The predicted DVU or rank |
| `actual_points_next_12m` | double | Realized points in subsequent 12m |
| `error_delta` | double | Prediction error (predicted - actual) |
| `ingest_ts` | timestamp | Record ingestion time |

### `gen_alpha.gold.opponent_picks`

Purpose:
Track pick assets owned by league opponents for liquidation monitoring.

Recommended columns:

| Column | Type | Description |
| --- | --- | --- |
| `league_id` | string | Unique league identifier |
| `owner_id` | string | Opponent manager identifier |
| `pick_year` | integer | Year of the draft pick |
| `pick_round` | integer | Round of the pick |
| `dg_id` | string | Projected prospect identity if assigned |
| `ingest_ts` | timestamp | Record ingestion time |

## Source-Rank Enforcement Policy

Source-rank policy belongs in implementation controls and data quality rules, consistent with the governance canon.

### Enforcement rules
1. Source metadata must be retained from ingestion through Gold where source eligibility matters.
2. Records used for exception archetype qualification must require `source_rank = 1`.
3. Rank 3 market-hype sources must never qualify model-grade exception outputs.
4. Where trade/compliance workflows persist source rank, the rank must be queryable and auditable.
5. Missing source rank should fail validation for any table that depends on ranked-source logic.

### Implementation posture
* enforce source-rank expectations in Silver transformation and Gold publish checks
* emit failed records to quarantine/triage tables or validation logs
* never silently coerce unknown ranks into valid ranks
* track validation results in `agent_activity_log` or related validation events

## DAB, Jobs, and Promotion Expectations

### Databricks Asset Bundles

- DABs are the default deployment mechanism for jobs, SQL, and platform artifacts.
- SQL definitions should live in `.sql` files, not inline YAML.
- Bundle configuration should remain environment-aware and promotion-safe.

### DAB Deployment Outline

The first lineage DAB should be intentionally small. Its job is to prove repo-controlled deployment, not to solve every data-platform workflow.

Bundle contents:

- `databricks.yml` declares `dev`, `staging`, and `prod` targets.
- `resources/lineage_tables.yml` declares the table-creation job.
- `resources/lineage_sync.yml` declares the Markdown-to-lineage sync job.
- `resources/sql/create_agent_activity_log.sql` creates or migrates `gen_alpha.gold.agent_activity_log`.
- `resources/sql/create_artifact_registry.sql` creates or migrates `gen_alpha.gold.artifact_registry`.
- `src/dynasty_genius/lineage/sync_markdown.py` parses `AGENT_SYNC.md` and `docs/agent-ledger/*.md`.
- `src/dynasty_genius/lineage/write_events.py` writes validated rows to Gold.

Initial jobs:

- `lineage_create_tables`: runs table DDL and validates required columns.
- `lineage_sync_markdown`: ingests repo Markdown state into activity and artifact records.
- `lineage_validate_governance`: checks required governance artifacts and writes pass/fail activity rows.

Target behavior:

- Dev can run from a feature branch with isolated schemas or bundle variables.
- Staging runs after PR review to certify schema stability and parser behavior.
- Prod runs only from approved `main` commits.
- Every job records repo branch, commit SHA, bundle target, governance version, and job run id.
- Failed sync or validation jobs write a blocked activity row when possible and never mutate canonical Markdown.

Minimum acceptance:

- `databricks bundle validate -t dev` passes.
- Dev table creation job succeeds.
- Markdown sync job writes at least one `agent_activity_log` row and one `artifact_registry` row.
- Re-running sync is idempotent for the same commit and ledger content.
- Market-overlay artifacts may be registered, but market-derived values are never written as Engine A or Engine B feature inputs.

### Lakeflow Jobs

- Use Jobs for scheduled lineage sync, validation runs, and publish workflows.
- Distinguish at minimum:
  - metadata ingestion job
  - governance validation job
  - artifact registry publish job
  - activity log sync job

### Environment promotion

- Dev: iterate on schemas, jobs, and validation logic
- Staging: certify schema stability, validation behavior, and promotion scripts
- Prod: publish only approved bundle versions

Expected promotion rule:

- no direct Prod mutation without traceable deployment metadata
- each promotion should record version, environment, and validation state

## Connection to `AGENT_SYNC.md` and Daily Ledger

Phase 1 remains Markdown-first.

### Canonical operating artifacts
* `AGENT_SYNC.md` is the current state board
* `docs/agent-ledger/YYYY-MM-DD.md` is the detailed session log
* `docs/governance/` remains the governing doctrine

### Databricks connection model
Databricks should mirror and extend these artifacts, not replace them.

Recommended sync behavior:
* ingest summary state from `AGENT_SYNC.md` into `artifact_registry` or a future status table
* ingest ledger entries into `agent_activity_log`
* enrich platform rows with job/run metadata when execution occurred in Databricks
* preserve the original Markdown files as the human-readable canonical source

### Operational benefit
This creates:
* human-readable governance in Git
* machine-readable governance in Databricks
* cross-linkage between repo state, jobs, tables, and validation outcomes

## First Implementation Order After Governance Seal

1. Create the platform doc and approve schema design
   * finalize this file in repo
   * confirm naming, ownership, and scope

2. Add repo-level validator hooks first
   * finish Phase 1 validator and CI guardrails before platform sync jobs
   * ensure bootstrap files and governance docs are enforced in Git

3. Stand up Dev schemas/tables
   * create Dev versions of `agent_activity_log` and `artifact_registry`
   * define table properties, retention, and access expectations

4. Implement basic ingestion from Markdown artifacts
   * parse `AGENT_SYNC.md`
   * parse daily ledger entries
   * land raw records into Bronze
   * normalize to Silver
   * publish to Gold

5. Add Job-based validation and publish workflow
   * scheduled or on-demand sync jobs
   * validation status written as activity events
   * failed syncs visible without mutating canonical Markdown

6. Promote to Staging, then Prod
   * validate schema stability
   * validate source-rank enforcement behavior
   * validate audit visibility and rollback path

## Initial Acceptance Criteria

This plan is ready to move into implementation when:
* the governance seal PR is merged
* the repo validator and CI checks exist
* Gold schemas for `agent_activity_log` and `artifact_registry` are approved
* Dev deployment path via DABs is defined
* Markdown-to-Databricks sync behavior is documented and testable

## Open Questions

* Should artifact registry include non-governance product assets in Phase 2, or only governance/bootstrap assets first
* What retention policy should apply to append-only activity logs
* Should sync be pull-based from repo state, push-based from CI, or hybrid
* Which environment owns the first authoritative backfill of historical ledger entries

## Final Rule

Databricks lineage is an extension of the Dynasty Genius governance operating system, not a substitute for it. The repo remains the first source of truth; the platform makes that truth queryable, promotable, and auditable.
