---
document: Phase 13 Final Spec
version: 1.0.0
status: APPROVED
date: 2026-05-15
owner: David
prepared_by: Codex final synthesis
phase: 13
approved_by: David
approved_at: 2026-05-15
source_reports:
  - docs/strategies/Phase13-round2-research.md
  - docs/strategies/Phase13-Round2-Dynasty Genius Framework Review.md
agent_syntheses:
  - docs/strategies/phase13-agent-merge-gemini.md
  - docs/strategies/phase13-agent-merge-claude.md
  - docs/strategies/phase13-agent-merge-codex.md
governance_read:
  - docs/governance/02-agent-operating-loop.md
  - docs/governance/00-product-constitution.md
  - docs/governance/01-north-star-architecture.md
  - AGENT_SYNC.md
---

# Phase 13 Final Spec

Identity Audit + Engine A Draft-Capital Bake-Off + TE Remodel Step 0

## 1. Provenance

This spec is the final synthesis of five inputs:

1. `docs/strategies/Phase13-round2-research.md`
2. `docs/strategies/Phase13-Round2-Dynasty Genius Framework Review.md`
3. `docs/strategies/phase13-agent-merge-gemini.md`
4. `docs/strategies/phase13-agent-merge-claude.md`
5. `docs/strategies/phase13-agent-merge-codex.md`

The earlier Phase 13 draft spec is intentionally not a source for this document. This file supersedes it after David approval.

The agent merge consensus is strong on sequencing:

- Identity audit is the first hard gate.
- Engine A draft-capital work may be researched in parallel, but promotion waits for a locked historical identity cohort.
- TE remodel begins with data feasibility and archetype labeling only.
- TE remains `EXPERIMENTAL`.
- DVS remains out of scope.
- Market-derived data remains an overlay only.

The main conflicts were methodological, not strategic.

| Conflict | Final Resolution |
|---|---|
| `gsis_id` vs internal canonical key | Dynasty Genius owns canonical `player_id`; `gsis_id` is the strongest NFL crosswalk anchor, not the app-level canonical key. |
| Draft-capital transform | Do a bake-off: current baseline, log-decay, bucketed categorical, and monotonic/isotonic step. Do not pre-choose the winner. |
| Draft-capital thresholds | Use QB top-15, WR pick-75, RB Day-2/Day-3, and TE R1/rest as research priors only. Final thresholds require validation. |
| TE archetype granularity | Phase 13 uses a Step 0 rubric with receiving-leaning, blocking-leaning, and ambiguous labels. Four-archetype modeling is deferred. |
| PFF grades | Subjective PFF grades are diagnostic context only. Objective participation/rate fields are the only Phase 13 feature candidates. |
| TE coverage denominator | All drafted TEs remain in the primary identity denominator. A fantasy-relevance denominator may be reported as secondary context. |
| `prospect_alias_bridge.json` scope | Existing bridge may seed Phase 13, but Phase 13 should create a broader source-ID override registry rather than overloading the prospect bridge. |
| Identity failure artifacts | Use identity-specific artifacts. Do not overload the Phase 12 divergence ledger terminology. |

## 2. Executive Decision

Phase 13 is a foundation and validation phase. It should not become a broad model rewrite.

The implementation order is:

1. **13.1 Identity Resolution Audit**
2. **13.2 Engine A Draft-Capital Bake-Off**
3. **13.3 TE Remodel Step 0**

13.1 starts first because incorrect player joins are the highest-severity Phase 13 failure mode. A missing feature creates a caveat. A wrong identity join silently poisons training data.

13.2 can start in parallel for design and offline validation because it uses existing draft metadata. It cannot promote any Engine A feature change until the historical backtest identity snapshot is locked.

13.3 is gated by 13.1. No PFF collegiate alignment rows may enter any training or feature materialization path until the TE identity coverage gate passes.

## 3. Phase 13 Objective

Phase 13 improves the data foundations and validation discipline behind rookie and TE evaluation.

It exists to answer three questions:

1. Can Dynasty Genius deterministically join active, historical, prospect, and source-specific rows without silent identity corruption?
2. Does a position-specific draft-capital step transform beat the current Engine A baseline under class-based validation?
3. Can TE role heterogeneity be measured cleanly enough to justify a future TE model change?

The phase is successful if it produces trustworthy artifacts and gates, even if no model promotion happens.

## 4. Non-Goals

The following are out of scope for Phase 13:

- DVS implementation or `dynasty_value_score` promotion.
- Any market-derived field as an Engine A or Engine B feature.
- KTC, FantasyCalc, ADP, DynastyNerds, FantasyPros, or consensus values in training data.
- TE promotion out of `EXPERIMENTAL`.
- Engine B retraining using collegiate alignment or prospect data.
- Per-archetype TE submodels.
- Subjective PFF grades as model features.
- Silent fuzzy identity matching.
- Adapter-local production identity logic.
- CFB Reference / Sports Reference as training features without explicit license approval.
- Hardcoded age cliffs as model inputs.
- RAS as positive model lift unless separately validated.
- Permanent hardcoded draft-capital breakpoints before backtest validation.

## 5. Governance Constraints

Phase 13 must preserve these rules:

- The Product Constitution has authority over analytical choices.
- The North Star Architecture has authority over technical shape.
- Dynasty Genius owns one canonical `player_id`.
- Source IDs live in the identity layer.
- Adapters emit source-native IDs and metadata; they do not resolve production identity independently.
- Fuzzy matching can create review candidates only. It cannot auto-resolve production identity.
- Unresolved rows are rejected to triage, not silently scored.
- Market data remains physically and semantically separate from model features.
- TE decision surfaces must continue to disclose experimental status.
- Feature formulas and thresholds must be versioned artifacts with provenance.

## 6. Workstream 13.1: Identity Resolution Audit

### Goal

Build an auditable identity layer that proves Dynasty Genius can resolve current players, rookies, historical backtest rows, and PFF/college rows without silent corruption.

### Inputs

- Sleeper `/v1/players/nfl`
- nflverse / `ff_playerids`
- existing `app/data/prospect_alias_bridge.json`
- existing Dynasty Genius player identifiers
- PFF export IDs when available
- PFR / CFBRef IDs as reference fields where licensed and available

### Canonical Model

Dynasty Genius canonical identity remains internal `player_id`.

`gsis_id` is the strongest NFL crosswalk anchor and should be used to bridge Sleeper, nflverse, PFF, PFR, and other source IDs. It is not the app-level canonical key.

Required source-ID columns for audit artifacts:

- `player_id`
- `sleeper_id`
- `gsis_id`
- `pff_id`
- `pfr_id`
- `cfbref_id`
- `espn_id`
- `yahoo_id`
- `sportradar_id`
- `fantasypros_id`
- `rotowire_id`
- `fantasy_data_id`
- `name`
- `date_of_birth`
- `position`
- `college`
- `draft_year`
- `draft_round`
- `draft_pick`
- `source`
- `source_timestamp`

### Deterministic Cascade

Resolution order:

1. Direct ID join through existing source-ID map.
2. `ff_playerids` crosswalk join using `gsis_id` where present.
3. Sleeper payload pass-through for active players with native source IDs.
4. Existing prospect alias bridge for pre-NFL or unresolved prospect rows.
5. Composite deterministic key: normalized name + DOB + position + draft year.
6. Composite prospect key: normalized name + college + position + draft year.
7. Review queue.

No production path may resolve a row through fuzzy matching.

Fuzzy/token similarity may be used only to populate review candidates with scores and evidence. Manual approval writes a versioned override; rejected candidates remain blocked.

### Override Registry

Phase 13 should create a broader source-ID override registry rather than expanding `prospect_alias_bridge.json` into a universal identity table.

Recommended path:

- keep `app/data/prospect_alias_bridge.json` for prospect alias lookups;
- add a source-ID override registry for cross-source identity corrections;
- allow the prospect bridge to seed the registry;
- keep both schemas documented and tested.

The override registry must include:

- canonical `player_id`
- source ID fields being asserted
- source row evidence
- author
- timestamp
- reason
- confidence level
- review status
- supersedes / invalidates fields where applicable

### Required Artifacts

- `identity_contract.md`
- `identity_coverage_matrix_{run_id}.json`
- `identity_review_queue_{run_id}.jsonl`
- `identity_override_registry.json`
- `identity_failure_report_{run_id}.md`
- `identity_snapshot_{run_id}.json`

These names are proposed. The implementation may adjust names if the spec preserves the same contracts.

### Coverage Gates

Minimum gates for David approval:

- David roster: 100% resolved or explicitly queued with no silent missing rows.
- Active high-value players: 100% resolved or explicitly queued.
- Active Sleeper/NFL cohort: at least 99% deterministic coverage.
- Historical backtest cohort: at least 95% deterministic coverage.
- 2018-2025 drafted TE cohort: at least 98% resolved before PFF/TE rows enter feature materialization.

All drafted TEs remain in the primary identity denominator. Pure inline blockers may be reported in a secondary fantasy-relevance denominator, but they do not disappear from the identity gate.

### Tests

Required tests:

- adapters declare source IDs they emit;
- no adapter resolves production identity independently;
- duplicate non-null `player_id`, `sleeper_id`, or `gsis_id` conflicts fail;
- unresolved PFF/college rows cannot enter training materialization;
- row counts are preserved through identity enrichment;
- manual overrides require author, timestamp, reason, and source evidence;
- historical identity snapshots are immutable per backtest run;
- prospect-to-veteran transitions resolve to one canonical `player_id`;
- fuzzy candidates remain review-only.

## 7. Workstream 13.2: Engine A Draft-Capital Bake-Off

### Goal

Determine whether a position-specific nonlinear draft-capital transform improves Engine A rookie ranking quality over the current baseline.

This workstream is a bake-off, not a predetermined implementation.

### Candidate Transforms

Evaluate:

1. Current Engine A baseline.
2. Smooth log-decay baseline.
3. Position-specific bucketed categorical bins.
4. Monotonic/isotonic step transform fit per position.

Optional research-only variant:

- hierarchical or pooled priors for small positions, especially TE.

Hierarchical priors are not a default implementation target because they add complexity outside the current sklearn/Ridge path.

### Candidate Priors

These are starting hypotheses only:

| Position | Candidate Priors |
|---|---|
| QB | top 15, 16-32, 33-64, 65+; also test 1-32, 33-64, 65+ |
| RB | 1-32, 33-64, 65-105, 106+, UDFA |
| WR | 1-32, 33-75, 76-105, 106+; also test 33-64 and 65-105 split |
| TE | 1-32 vs 33+ or broad shrinkage only |

### Validation Protocol

The primary validation protocol is leave-one-draft-class-out validation.

Primary metric:

- within-class rank correlation, preferably Kendall tau and Spearman rho by position.

Secondary metrics:

- calibration / bucket reliability where target framing supports it;
- Brier or AUC if the outcome is framed as hit / non-hit;
- bootstrap confidence intervals;
- pick-jitter sensitivity;
- fold-level stability.

The model card must state whether draft capital is measuring talent, opportunity assignment, or both. RB is especially confounded by early opportunity assignment.

### Promotion Gate

A draft-capital change may be promoted only if:

- 13.1 has locked the relevant historical identity snapshot;
- the candidate beats the current baseline and log-decay baseline on within-class rank correlation;
- confidence intervals support a real lift, not just a point-estimate improvement;
- breakpoints remain stable under reasonable pick jitter;
- no market-derived fields enter training data;
- model-card and validation artifacts are generated.

If no candidate clears the gate, Phase 13 should keep the current Engine A behavior and record the failed bake-off.

## 8. Workstream 13.3: TE Remodel Step 0

### Goal

Determine whether TE role heterogeneity can be measured cleanly enough to justify a later model change.

Phase 13 does not promote TE.

### Dependency

13.3 cannot begin PFF/college feature materialization until 13.1 passes the 2018-2025 drafted TE identity gate.

### Step 0 Scope

Step 0 produces:

- PFF manual CSV feasibility memo;
- PFF field inventory;
- license and storage constraints;
- 2018-2025 drafted TE identity coverage;
- TE archetype rubric v0;
- labeled sample cohort;
- public fallback comparison;
- gap report;
- recommendation for whether a later TE remodel implementation spec is warranted.

### Archetype Rubric

Phase 13 should start with a three-label rubric:

- `receiving_leaning`
- `blocking_leaning`
- `ambiguous`

The four-archetype research model is retained as future context:

- receiving specialist / move TE;
- big-slot hybrid;
- in-line receiving TE;
- blocking-first / TE2.

The four-way taxonomy is not a Phase 13 model structure.

Candidate objective thresholds for Step 0 review:

- `slot_wide_route_pct >= 0.40` suggests receiving-leaning / detached usage.
- `inline_blocking_rate >= 0.60` suggests blocking-leaning usage.
- strong YPRR or target-per-route signals may create an upside caveat for inline-heavy players.

These thresholds are not production law. They are rubric candidates that must be reviewed against labeled examples.

### Candidate Fields

Allowed Phase 13 TE feature candidates are objective participation and rate fields:

- routes run;
- route participation;
- slot snaps or routes;
- wide snaps or routes;
- inline snaps or routes;
- slot plus wide route percentage;
- inline blocking rate;
- YPRR;
- targets per route run where available;
- RYPTPA / normalized receiving usage;
- targets;
- receptions;
- YAC per reception;
- contested-catch rate;
- drop rate.

PFF grades are diagnostic-only unless David separately approves a future validation plan.

### Data Source Plan

Preferred path:

- PFF collegiate manual CSV fixture for objective alignment and route fields.

Fallback path:

- cfbfastR / CollegeFootballData for production and usage context;
- PlayerProfiler / combine / athletic metrics for context;
- nflverse participation/personnel data for active NFL TE diagnostics.

CFB Reference / Sports Reference may be used for spot-checking only unless a training-use license is approved.

### Explicit Non-Promotion Rule

At the end of Phase 13:

- TE remains `EXPERIMENTAL`;
- Engine B remains unchanged;
- no TE production model is promoted solely from Step 0;
- the output is a decision on whether to write a later TE remodel implementation spec.

## 9. Artifacts And Schemas

Phase 13 should produce these artifact families.

### Identity Artifacts

- identity contract;
- identity coverage matrix;
- identity review queue;
- identity override registry;
- identity failure report;
- locked identity snapshot.

### Draft-Capital Artifacts

- draft-capital candidate manifest;
- validation results by position and class;
- breakpoint / transform artifact;
- calibration report;
- sensitivity report;
- model-card update or failed-bake-off memo.

### TE Step 0 Artifacts

- PFF feasibility memo;
- TE field inventory;
- TE identity coverage report;
- archetype rubric;
- labeled TE sample;
- fallback data gap report;
- TE remodel recommendation.

Artifacts must include:

- run ID;
- source files;
- source timestamps;
- parser or rubric version;
- governance version;
- author or agent;
- caveats;
- immutable output location.

## 10. Test Plan

### Identity Tests

- adapter source-ID declaration tests;
- deterministic cascade tests;
- no silent fuzzy production tests;
- duplicate ID tests;
- row-count preservation tests;
- override registry schema tests;
- review-queue append tests;
- PFF unresolved-row rejection tests;
- historical snapshot immutability tests;
- prospect-to-veteran transition tests.

### Draft-Capital Tests

- candidate transform schema tests;
- current baseline included in bake-off tests;
- no market field in candidate matrix tests;
- LOOCV fold construction tests;
- within-class rank metric tests;
- breakpoint artifact provenance tests;
- jitter sensitivity report tests;
- model-card update tests.

### TE Step 0 Tests

- PFF fixture schema tests;
- objective-field-only tests;
- PFF grade exclusion tests;
- archetype rubric version tests;
- labeled-sample schema tests;
- TE identity gate enforcement tests;
- Engine B untouched regression tests;
- TE experimental status regression tests.

## 11. Acceptance Criteria

Phase 13 is complete when:

1. Identity contract and source-ID ownership are documented.
2. Identity coverage matrix is generated for the required cohorts.
3. Review queue and override registry exist with auditable schema.
4. PFF/college unresolved rows are blocked from training materialization.
5. Historical identity snapshots are locked per backtest run.
6. Draft-capital bake-off evaluates all required candidates against the current baseline.
7. Draft-capital results report within-class rank lift, confidence intervals, calibration, and sensitivity.
8. Any promoted Engine A draft-capital change has a model-card update and contains no market fields.
9. TE PFF feasibility and license constraints are documented.
10. TE archetype rubric v0 and labeled sample exist.
11. TE remains `EXPERIMENTAL`.
12. Engine B artifacts are unchanged.
13. DVS remains out of scope.
14. The ledger records the phase outcome and next decision.

## 12. Open Decisions For David

1. Confirm whether 98% coverage is the correct hard gate for 2018-2025 drafted TEs.
2. Confirm that all drafted TEs stay in the primary identity denominator.
3. Approve creating a broader source-ID override registry instead of expanding `prospect_alias_bridge.json` into the universal identity map.
4. Confirm whether manual PFF CSV export is acceptable for Step 0.
5. Confirm PFF grades as diagnostic-only for Phase 13.
6. Decide whether 13.2 may promote an Engine A draft-capital change if the bake-off passes, or whether Phase 13 should produce validation only.
7. Decide whether TE Step 0 may proceed to a later implementation spec in the same phase if feasibility is strong.
8. Name the owner of manual identity review decisions.
9. Choose the authoritative draft-class window for 13.2: 10 classes, 15 classes, or all available with recency weighting.
10. Decide whether hierarchical draft-capital priors remain deferred or appear as a research-only benchmark.

## 13. Deferred Work

Deferred to later phases:

- DVS implementation.
- TE model retraining.
- TE promotion.
- per-archetype TE models.
- hierarchical Bayesian draft-capital model.
- CFB Reference licensing work.
- SIS or enterprise charting subscriptions.
- Engine B feature expansion from active TE alignment.
- RB feature expansion beyond draft-capital validation.

## 14. Implementation Order

### Task 13.1.0: Identity Contract

Write the contract for canonical `player_id`, source-ID fields, adapter expectations, review states, and override schema.

### Task 13.1.1: Identity Coverage Matrix

Build the audit runner and fixture-driven coverage matrix for active, rookie, historical, and TE cohorts.

### Task 13.1.2: Review Queue And Override Registry

Implement review queue output and override registry schema with tests.

### Task 13.1.3: Identity Gates

Add training-materialization gates that reject unresolved PFF/college rows and fail on duplicate identities.

### Task 13.2.0: Draft-Capital Candidate Manifest

Define candidate transforms and validation artifact schema.

### Task 13.2.1: Draft-Class LOOCV Harness

Build or extend the validation harness for leave-one-draft-class-out evaluation.

### Task 13.2.2: Draft-Capital Bake-Off

Run baseline, log-decay, bucketed, and isotonic candidates; emit results and recommendation.

### Task 13.2.3: Draft-Capital Promotion Decision

If David approves and gates pass, implement the winning transform. If not, record validation-only outcome.

### Task 13.3.0: PFF Feasibility Memo

Inventory fields, CSV workflow, license constraints, and cohort coverage.

### Task 13.3.1: TE Archetype Rubric

Create objective rubric and labeled sample for 2018-2025 drafted TEs.

### Task 13.3.2: TE Step 0 Decision

Emit recommendation for a later TE remodel implementation spec. No TE promotion.

## 15. Next-Agent Handoff

Do not start implementation until David approves this spec or edits the open decisions.

The first implementation task should be 13.1.0, not TE feature ingestion.

Implementation agents must:

- read governance files before work;
- log the session in the daily ledger;
- keep edits scoped to Phase 13;
- preserve market-overlay isolation;
- treat PFF data as private source data;
- write tests before feature materialization;
- keep TE experimental;
- avoid using the earlier superseded Phase 13 draft as authority.
