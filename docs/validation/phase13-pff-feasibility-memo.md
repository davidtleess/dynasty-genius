---
document: Phase 13 PFF Feasibility Memo
phase: 13
task: 13.3.0
status: COMPLETE_WITH_BLOCKERS
date: 2026-05-15
owner: David
prepared_by: Codex with parallel agent review
governance:
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - docs/superpowers/specs/2026-05-15-phase13-final-spec.md
---

# Phase 13 PFF Feasibility Memo

## Decision

PFF collegiate TE data is feasible for **Step 0 review only** after two blockers are resolved:

1. a real PFF collegiate TE manual CSV sample/schema is provided and locked;
2. the 2018-2025 drafted TE identity coverage run passes the Phase 13 gate.

Do not begin TE archetype rubric labeling or PFF/college feature materialization yet.

TE remains `EXPERIMENTAL`. Engine A and Engine B remain unchanged. PFF fields remain `context_signal` only unless David later approves a separate model-input spec and registry change.

## Scope

Task 13.3.0 is a feasibility/risk artifact. It does not ingest PFF data, create model features, retrain any model, promote TE, or alter production valuation behavior.

The approved Phase 13 spec requires this workstream to produce:

- PFF manual CSV feasibility memo;
- PFF field inventory;
- license and storage constraints;
- 2018-2025 drafted TE identity coverage path;
- public fallback comparison;
- gap report;
- recommendation for whether later TE remodel work is warranted.

## Current Repo State

PFF is registered as:

- role: `context_signal`;
- cache policy: `csv_fixture`;
- provenance required: yes;
- freshness: manual/static;
- model-input status: not allowed.

The source registry says Phase 13 PFF access is manual CSV export only. It also says PFF fields never enter model features under any name in the current phase.

There is a stale/aspirational conflict in older source docs: `docs/data-source-contracts.md` describes authenticated scraping as primary and references `app/data/pff_manual_export_schema.md`, but that schema file does not exist and `app/data/pff.py` is only a stub. The Phase 13 source registry posture is stricter and should control until explicitly changed.

## Field Inventory

The following fields are feasible candidates for Step 0 review if they appear in an approved PFF collegiate CSV export.

| Field | Step 0 Status | Rubric Use | Notes |
|---|---|---|---|
| `pff_id` | Required metadata | Required | Source-native ID for audit and override evidence. |
| `player_name` | Required metadata | Required | Review evidence only; not production identity by itself. |
| `college` | Required metadata | Required | Used for deterministic/review context. |
| `season` | Required metadata | Required | Needed for final-college-season or multi-season selection. |
| `position` | Required metadata | Required | Must be TE for this workstream. |
| `draft_year` | Required metadata | Required | Joins to 2018-2025 drafted TE cohort. |
| `routes_run` | Objective field | Required | Denominator for route-based rates and sample checks. |
| `route_participation` | Objective field | Useful | Context signal; not enough alone for label assignment. |
| `slot_routes` or `slot_snaps` | Objective field | Required | Prefer routes if available. |
| `wide_routes` or `wide_snaps` | Objective field | Required | Prefer routes if available. |
| `inline_routes` or `inline_snaps` | Objective field | Required | Needed to distinguish attached vs detached usage. |
| `slot_wide_route_pct` | Derived objective field | Required | Candidate receiving-leaning trigger at `>= 0.40`; not production law. |
| `inline_blocking_rate` | Derived objective field | Required | Candidate blocking-leaning trigger at `>= 0.60`; not production law. |
| `YPRR` | Objective rate | Useful | Upside caveat driver for ambiguous/inline-heavy players. |
| `targets_per_route_run` / `TPRR` | Objective rate | Useful | Receiving-usage support if available. |
| `RYPTPA` / normalized receiving usage | Objective context | Useful | Public fallback comparator and sample sanity check. |
| `targets` | Objective count | Useful | Sample/context check. |
| `receptions` | Objective count | Useful | Sample/context check. |
| `YAC_per_reception` | Objective rate | Secondary | Sample-sensitive diagnostic. |
| `contested_catch_rate` | Objective rate | Secondary | Sample-sensitive diagnostic. |
| `drop_rate` | Objective rate | Secondary | Sample-sensitive diagnostic. |
| `pff_grade`, `pff_route_grade`, receiving grades, run-block grades, pass-block grades | Diagnostic only / prohibited as features | No | Existing Engine A contract prohibits `pff_grade` and `pff_route_grade`; subjective grades must not enter training. |

## Proposed Step 0 Rubric Inputs

The Phase 13 rubric remains three-label:

- `receiving_leaning`
- `blocking_leaning`
- `ambiguous`

Candidate review thresholds:

- `slot_wide_route_pct >= 0.40` suggests `receiving_leaning`;
- `inline_blocking_rate >= 0.60` suggests `blocking_leaning`;
- strong `YPRR` or `TPRR` can create an upside caveat for otherwise inline-heavy or ambiguous players.

These thresholds are review candidates, not production law. They should be checked against labeled examples before any later implementation spec.

## Identity Gate

Before any PFF/college rows enter feature materialization, Dynasty Genius must run the 2018-2025 drafted TE identity audit and pass:

- all drafted TEs included in the denominator;
- TE cohort resolved percentage `>= 98%`;
- row count preserved;
- no duplicate non-null `player_id`, `sleeper_id`, `gsis_id`, or relevant source-ID conflicts;
- unresolved rows written to review queue;
- fuzzy candidates remain review-only;
- approved manual overrides include evidence, author, timestamp, reason, confidence, and status;
- immutable `identity_snapshot_{run_id}.json` generated for the passing run;
- materialization gate allows only `RESOLVED_DETERMINISTIC` or `RESOLVED_MANUAL` PFF/college rows with canonical `player_id`.

Required run inputs:

- full 2018-2025 drafted TE cohort;
- `ff_playerids`/nflverse crosswalk;
- Sleeper passthrough data;
- existing prospect alias bridge;
- approved override registry entries;
- PFF CSV identity evidence when available;
- source timestamps and run metadata.

Required run outputs:

- `identity_coverage_matrix_{run_id}.json`;
- `identity_review_queue_{run_id}.jsonl`;
- `identity_failure_report_{run_id}.md`;
- `identity_snapshot_{run_id}.json`;
- PFF materialization eligibility manifest.

## Workflow

Recommended manual workflow:

1. Obtain a PFF collegiate TE CSV sample for the target seasons/classes.
2. Store only private/manual artifacts in ignored local paths or governed bronze storage; do not commit proprietary raw exports.
3. Create a checked-in schema/fixture using synthetic or redacted rows only.
4. Validate required columns, provenance columns, and prohibited grade handling.
5. Run the TE identity audit.
6. Resolve review queue items through the override registry.
7. Generate immutable identity snapshot.
8. Apply materialization gate.
9. Only after the gate passes, write Task 13.3.1 rubric/labeled-sample work.

## License And Storage Constraints

Repo-local evidence supports these constraints:

- PFF exports are private/subscriber data and should not be redistributed.
- Credentials/session files must never be committed.
- Raw scrape dumps, browser artifacts, API caches, and proprietary CSV exports should remain untracked.
- Public repo fixtures should be synthetic or redacted.
- The exact PFF contractual terms are not present in the repo. Do not infer broader usage rights from local notes.

Before durable feature-store use, David should verify the current PFF subscription/API/export terms outside this memo.

## Public Fallback Comparison

Public fallback sources can support a gap analysis, but they do not replace PFF alignment data.

| Source | Useful For | Limitation |
|---|---|---|
| cfbfastR / CollegeFootballData | Receiving production, inferred usage, RYPTPA, target share, team/context checks | Weak or absent slot/inline/wide alignment and blocking-role detail. |
| PlayerProfiler / combine context | Dominator, breakout/production context, athletic profile | No direct college alignment or blocking-rate replacement. |
| nflverse participation/personnel | Active NFL TE diagnostic proxy | NFL usage proxy only; not a college prospect replacement and must not leak into Engine A prospect training. |

Fallback comparison should answer whether public data can approximate receiving profile enough for a caveat. It should not claim equivalence to PFF alignment.

## Blockers

| Blocker | Severity | Why It Blocks |
|---|---|---|
| No real PFF collegiate TE CSV sample/schema | High | Exact export column names and denominators are unknown. |
| No 2018-2025 drafted TE identity coverage artifact | Critical | Phase 13 requires the identity gate before PFF/college materialization. |
| Exact PFF license/export terms not verified | High | Repo notes are insufficient for durable storage/training-use decisions. |
| Manual export tests are governance-only today | Medium | They verify source posture, not actual parser/schema behavior. |
| PFF registry role is `context_signal` | High for future model use | Any later model-input use requires explicit David approval and registry/test changes. |

## Recommendation

Complete Task 13.3.0 with a blocked-forward recommendation:

- PFF Step 0 is worth pursuing because the field set directly targets the TE label-noise hypothesis.
- Do not start Task 13.3.1 rubric labeling until a real PFF CSV sample/schema and TE identity coverage artifact exist.
- Do not alter Engine A, Engine B, PVO scoring, or TE model grade.
- Keep PFF as `context_signal` until David approves a later model-input spec.

## Acceptance Criteria

Task 13.3.0 is accepted if:

- this memo is tracked;
- field inventory is documented;
- identity gate checklist is documented;
- public fallback limitations are documented;
- blockers are explicit;
- no model code or feature contracts are changed.
