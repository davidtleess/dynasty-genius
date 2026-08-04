# CFBD board Step 2 gate ruling — Codex v1

**Date:** 2026-08-03 22:54 ET
**Repo state reviewed:** `HEAD 492669b`, `origin/main 29bd102`, clean worktree before this artifact
**Scope:** independent interpretation and read-only validation of the existing Step 2 gate. No
promotion, rollback, refresh, bakeoff, model write, feature use, or data mutation.

## Verdict

**Board Step 2 is NOT CLOSED, but the claimed G3–G5/bakeoff conflict is false.** The live board
reuses gate labels from two different subsystems. Its `local G3–G5 validation` refers to the CFBD
**ingestion/curation publication gates**, not `backtest_harness.evaluate_promotion_gates`.

The remaining blocking row under the board as written is the **candidate-input override**. The
current board also needs a truth update from `unpromoted`/pending language to the actual live data
state. The data movement itself remains valid and is not a reason to roll back.

## R1 — G3–G5 namespace: no conflict with the bakeoff deferral

The governing lineage is explicit:

- `docs/agent-ledger/evidence/2026-08-01/cfbd_qb_ingest_red_codex_v1.md:14-22` defines:
  - G3 = same-season cross-player complete-vector collision;
  - G4 = scale/plausibility;
  - G5 = zero coverage plus material coverage retention.
- `docs/agent-ledger/evidence/2026-08-01/msg_codex_cfbd_correction_accepted_claude_v1.txt:23-25`
  states that the Phase-20 runner already had its own coverage behavior and that **G3–G5 sit at
  ingestion**; model/bakeoff-layer changes remain outside that repair.
- `src/dynasty_genius/capture/cfbd_foundation_refresh.py:188-254` implements G3, G4, and G5
  zero-coverage; `:263-290` implements G5 retention; `:347` invokes retention before publication.

`src/dynasty_genius/eval/backtest_harness.py:249-275` defines an unrelated model-promotion namespace
with G1–G4. It has no G5, but that absence says nothing about the ingestion G5 named by block A.
No model-promotion gate and no bakeoff must run to satisfy block A's ingestion G3–G5 row.

**Ruling:** no governance conflict exists on this row. The board wording is ambiguous and should be
repaired to name the gates semantically: `local ingestion/curation G3 collision · G4
scale/plausibility · G5 zero-coverage/retention validation (not model-promotion gates)`.

## R2 — local G3–G5 evidence for the pinned candidate

I invoked the existing local `_validate_curated` validator directly on the exact promoted bytes.
It passed:

- row count: **874**
- identity coverage: **1.0**
- `qb_completion_pct_final`: **0.8571428571428571**
- `qb_yards_per_attempt_final`: **0.8571428571428571**
- `qb_td_int_ratio_final`: **0.8571428571428571**
- `qb_sack_rate_final`: **0.6904761904761905**

The active and curated candidate both hash to
`15e17cd9164c5ab05f0440f0ca90bb93f89ce7735efa517d331495cd2bea11d0`. The hash-bound source
manifest records the same four coverage values, `raw_file_count=1202`, and the same curated hash.

As a positive control, the exact durable preimage `b3c28e42…` is refused by the same validator on
G4: `qb_completion_pct_final 0.00572 ... outside the plausible range [0.2, 0.95]`. The corrected
bytes therefore change the real gate result, not merely the hash.

Focused ingestion/curation contracts:

```text
tests/contract/test_cfbd_qb_ingest_red.py
tests/contract/test_cfbd_qb_ingest_green_review.py
22 passed
```

**G5 retention precision:** the 2026-07-31 manifest predates the `feature_coverage` field, so the
2026-08-02 publication had no historical manifest baseline against which to exercise the retention
delta. The run established that baseline for the next refresh. The current candidate passes G5's
actual zero-coverage gate; the focused contracts prove the retention refusal mechanism. A
current-manifest-to-current-bytes retention check also passes but is not presented as historical
evidence because it is tautological.

**Ruling:** for this pinned one-time data promotion, the local G3–G5 row is now satisfied by the
exact-byte rerun, the source-manifest/hash chain, and the focused contracts. No new promotion-module
implementation and no bakeoff are required for this row.

## R3 — candidate-input override remains required before Step 2 closes

The live board says the consumer surface **requires** an explicit candidate-input override. The
implementation does not have one:

- `scripts/run_phase20_bakeoff.py:37` hardcodes its own `V3_CSV`;
- `scripts/run_phase20_bakeoff.py:242-255` has no argument parsing and calls `_load_all_rows()` with
  no path;
- the imported loader in `scripts/run_head_a_bakeoff.py:604-611` separately hardcodes that module's
  `V3_CSV`.

This last point is load-bearing: changing or parameterizing only the Phase-20 module's displayed
`V3_CSV` would still leave `_load_all_rows()` reading the Head-A module's active-file constant.
The override must be threaded into the actual loader and the artifact must record the exact input
path/hash it consumed.

**Ruling:** yes, the candidate-input override is required before Step 2 may be called closed **while
the current board gate stands**. Implementing and testing the override is not running a bakeoff and
must not execute the evaluator, write a model, or claim validation. However, the board gate is
lane-authored and David's quoted authority is DATA-scoped. Altering the model-evaluation runner is
not authority I will infer from a priority or from a reviewer ruling. David must choose one narrow
disposition:

1. authorize the override wiring/tests only, with bakeoff execution still deferred; or
2. rule that the override belongs to the deferred bakeoff work and amend Step 2's closure gate.

Until one occurs and the board is made truthful, **Step 2 remains open**. This does not invalidate
the promoted data, receipt, preimage, rollback availability, prior mechanism CLEARs, or CI result.

## Boundary

No bakeoff was run. No model or feature was promoted or consumed. No rollback is warranted by this
ruling. H2 QB rushing remains **UNDER TEST** with no result; this audit supplies no evidence about
rushing in any direction.
