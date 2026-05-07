# Databricks Lineage Plan

## Purpose

This is the Phase 2 platform plan for making Dynasty Genius agent work, data transformations, and decision artifacts auditable in Databricks.

The constitution remains the analytical authority. This plan defines platform implementation details only.

## Medallion Mapping

Bronze:

- raw source snapshots and minimally transformed extracts
- source timestamps, ingestion timestamps, and parser metadata
- source-rank fields where available
- replayable inputs for debugging scraper, parser, or model behavior

Silver:

- normalized source rows with canonical identity attached
- standardized metrics and source-rank enforcement
- historical backfills such as efficiency metrics
- parser version, metric version, and completeness flags

Gold:

- decision-grade artifacts and governed outputs
- model or rule outputs with caveats and compliance flags
- agent activity and artifact lineage logs
- market overlays joined after model scoring

## Proposed Table: `gen_alpha.gold.agent_activity_log`

Columns:

- `activity_id STRING NOT NULL`
- `activity_ts TIMESTAMP NOT NULL`
- `agent_name STRING NOT NULL`
- `activity_type STRING NOT NULL`
- `task_summary STRING NOT NULL`
- `governance_versions MAP<STRING, STRING>`
- `repo_branch STRING`
- `commit_sha STRING`
- `workspace_path STRING`
- `input_context STRING`
- `output_artifact_ids ARRAY<STRING>`
- `files_changed ARRAY<STRING>`
- `tables_touched ARRAY<STRING>`
- `checks_run ARRAY<STRING>`
- `compliance_flags ARRAY<STRING>`
- `handoff_note STRING`

Usage:

- every material Databricks or repo session writes one row
- `AGENT_SYNC.md` remains the human-readable current state board
- the daily ledger remains the local repo continuity log

## Proposed Table: `gen_alpha.gold.artifact_registry`

Columns:

- `artifact_id STRING NOT NULL`
- `created_ts TIMESTAMP NOT NULL`
- `created_by STRING NOT NULL`
- `artifact_type STRING NOT NULL`
- `storage_uri STRING NOT NULL`
- `source_system STRING`
- `source_rank INT`
- `governance_version STRING`
- `job_run_id STRING`
- `notebook_path STRING`
- `bundle_target STRING`
- `related_artifact_ids ARRAY<STRING>`
- `data_freshness_ts TIMESTAMP`
- `caveats ARRAY<STRING>`
- `tags ARRAY<STRING>`

Usage:

- register raw snapshots, transformed tables, model artifacts, validation reports, and decision outputs
- link downstream recommendations to upstream data and transformation artifacts
- support audit questions such as "which source snapshot and governance version produced this trade evaluation?"

## Source-Rank Enforcement

- Tier 1 / source-rank 1 data may qualify model-grade tracking or performance features.
- Market and narrative sources may exist only as overlays or caveats.
- Gold outputs must preserve source rank where source rank affects eligibility.
- If source rank is missing for a model-grade feature, downstream outputs must carry a caveat or fail the relevant validation gate.

## DAB, Jobs, And Promotion Expectations

- Use Databricks Asset Bundles or equivalent file-based deployment for production assets.
- Store SQL, job config, and pipeline logic in the repo.
- Avoid UI-only production configuration.
- Pass required business parameters explicitly and log them.
- Promote through Dev -> Staging -> Prod when environments exist.
- Record job run ID, bundle target, code version, and governance version for material outputs.

## Connection To Markdown Loop

Phase 1 remains repo-native:

- `AGENT_SYNC.md` for current state
- `docs/agent-ledger/YYYY-MM-DD.md` for session logs

Phase 2 mirrors this state into Databricks:

- write agent sessions to `gen_alpha.gold.agent_activity_log`
- register durable outputs in `gen_alpha.gold.artifact_registry`
- link table/job/model outputs to the governance version active at creation time

The Markdown loop is still required because every agent can read it. Databricks lineage adds machine-readable auditability.

## First Implementation Order

1. Add SQL DDL for both gold tables under `resources/`.
2. Add a small Python or SQL writer utility for appending agent activity rows.
3. Add a Databricks job or bundle target to create/update lineage tables.
4. Add CI checks ensuring lineage SQL preserves required columns.
5. Pilot logging with one agent session and one generated artifact.
6. Only after the pilot, require lineage writes for Databricks-touching sessions.
