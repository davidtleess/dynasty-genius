# Codex challenge — bakeoff execution-status reporting framing v2

**Date:** 2026-08-01  
**Reviewer:** Codex  
**Artifact reviewed:** `framing_inert_feature_defect_signal_claude_v2.md`  
**Verdict:** **CHALLENGE — 3 blocking framing defects. No RED opens.**

## Checks performed

- Read v2 in full and reconciled its claims against
  `scripts/run_phase20_bakeoff.py:104-202,242-306`,
  `scripts/run_head_a_bakeoff.py:131-144`, the committed Phase-20 artifact's `positions.QB`, and
  `docs/agent-ledger/2026-05-24.md:981-1004`.
- Distinguished the full 126-row CSV population from the 38 non-censored rows on which the runner's
  50% coverage filter actually operated.
- Walked the proposed arm status, candidate status, run status, and exit-code branches for mixed
  pass/fail/blocked/no-op cases.

## Findings

### 1. The framing binds the block to the wrong coverage denominator and overstates cause

**What failed.** Lines 12–14 say all four columns were below the threshold at a measured 25.4% and
that the cause was the layers-1/2 ingest defect. That conflates two measurements:

- `25.4% = 32/126` is the ledger's full-QB-table population figure.
- The runner calls `_filter_available_features(eligible, spec_features)` after reducing QB to **38
  non-censored rows**. Its committed artifact records **39.5% = 15/38** for completion percentage,
  YPA, and TD:INT, and **0.0%** for sack rate.

The arm did block because every candidate field was below 50%, but the runner did **not** gate on
25.4%. Further, the inputs were proven defective, but without a post-repair refresh their causal
share in the coverage failure is unknowable. The correct statement is: *the runner observed
39.5/39.5/39.5/0.0 coverage on its eligible cohort; those inputs are proven defective; repaired
coverage and whether the arm would still block are unknown.*

**Why it matters.** The proposed historical reader exists to prevent a misleading summary. It
cannot begin by misreporting the exact denominator it will classify.

### 2. The status contract is internally contradictory and lacks an aggregation truth table

**What failed.** Seed 6 requires a run-level `PARTIAL`, while seed 9 says the status vocabulary is
closed to `NOT_RUN`, `BLOCKED`, `EXECUTED_FAIL`, and `EXECUTED_PASS` and that no other value may be
emitted. The framing does not say seed 9 is arm-only. It also leaves these branches undefined:

- ridge passes and GBT fails for one executed arm;
- one candidate errors after another executes;
- declared candidate delta is empty (`no_candidate_features_declared`) — which status carries that
  reason;
- all arms execute with a mix of pass and fail;
- all arms block.

**Required correction.** Define separate closed enums for **candidate/model**, **arm**, and **run**
status, plus an explicit aggregation truth table. At minimum, state whether an arm is
`EXECUTED_PASS` when *any* candidate passes or only when all do, and define the run-level equivalent
of complete/mixed/all-blocked. `PARTIAL` cannot simultaneously be required and forbidden.

### 3. Exit-code semantics depend on an undefined concept of “required arm”

**What failed.** Section 6 asks what happens when a “required arm” is blocked, but the current runner
has no required/optional field; it merely hardcodes `WR`, `RB`, and `QB`. Without a registered
requiredness basis, the same artifact can exit differently depending on an implementer's inference.

**Technical position.** Preserve the artifact-first constraint. Then:

- invalid configuration (`no_candidate_features_declared`) exits non-zero;
- a blocked **explicitly required** arm exits non-zero;
- an executed scientific failure exits zero — a valid negative result is not a process failure;
- an optional blocked arm may remain zero only if optionality is explicit and the run artifact says
  `PARTIAL`.

The v3 framing must either declare every hardcoded Phase-20 arm required or introduce an explicit
requiredness field. Do not infer requiredness from list membership after the fact. The exact
non-zero code may remain implementation detail; the zero/non-zero partition may not.

## Constitutional and architectural alignment

- Historical artifacts remain immutable and source-hashed.
- `decision_supported=False` recursively remains correct.
- No model, threshold, data source, or promotion decision is opened by these findings.

