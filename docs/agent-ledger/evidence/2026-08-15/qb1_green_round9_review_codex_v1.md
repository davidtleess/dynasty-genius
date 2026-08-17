# TW15 QB-1 GREEN round-9 independent review — NOT CLEAR

Date: 2026-08-15 ET  
Reviewer: Codex  
Authority: David-authorized bounded round 9; TW15-CODEX-WAKE-2  
Layer: 3 validation/publication gate; Layers 1–2 and the registration remained outside write scope.  
Study execution: **not run**. H2 QB rushing remains **UNDER TEST**.

## Pins and scope reviewed

The round-9 run record remained ACTIVE at revision 51 with open-snapshot hash
`205d84b2073a567cd205fde01a74984c087fca742cfbbd1902cd1f12a0058f44`.
No separately named round-9 review-request artifact was present, so the review
used David's wake, the exact open snapshot, the live three-file scope, and the
durable round authorization as its source of truth.

- `execution.py`: `f4ec0b5bfdde224dd3cb892c6e4bd53396d518952a5df01e9d630360d38f442b`
- `run_qb1_study.py`: `605c8b22adc5030aabfcd539125a93d89b54b4908d16efad862d2e3711588170`
- correction contracts: `5c5964222599b1abc0e992094185a45acb8931762e4fa91665851d151b0583d2`
- independent probe: `e9ae56d976e783b4ee6b83b3ff2c527c56bcf28e695936a1e748fc260243b9ea`

The snapshot diff is limited to the three authorized files:

- execution: +143/-46;
- runner: +27/-5;
- correction contracts: +306/-1.

The three pins were stable across inspection and fresh verification.

## Findings

### BLOCKER R9-G1 — H5 “mechanically evaluable” is still an approximation, not the registered producer invariant

`execution.py:1453-1487` derives the H5 evaluable-season set from
`paired_delta is not None` and checks supporting fields only in one direction.
It treats any positive `common_pool_n` as sufficient and never requires the
stored delta to equal `spearman_left - spearman_right`.

That differs materially from both sources of record:

- registration §7 and the closed `fold_floors` block require
  `fold_min_evaluable_n=20`; below that, the fold is `fold_starved` and has no
  point estimate;
- `inference._reconcile_fold` requires exact fold-starvation coherence and
  exact equality of the stored delta to the two Spearmans before admission.

Three impossible payloads publish `run_status=ok` through the public runner:

1. a fold with both Spearmans present and `common_pool_n=24` deletes only its
   delta, is called excluded, and reduces `evaluable_folds` to three; the
   producer would reject the null delta because the point estimate is
   computable;
2. a fold with `common_pool_n=1` retains non-null Spearmans and a delta and is
   counted as evaluable despite the registered 20-row minimum;
3. a fold publishes `paired_delta=1.75` although its two published Spearmans do
   not subtract to 1.75, and is counted as evaluable.

Reproducers:

- `test_h5_null_delta_with_complete_support_publishes_as_excluded`;
- `test_h5_starved_fold_with_statistics_counts_as_evaluable`;
- `test_h5_delta_disagrees_with_published_spearmans`.

Smallest correction: require and validate the registration's
`fold_min_evaluable_n`; for every H5 metric entry compute the producer-shaped
expected delta as `left - right` exactly when the pool meets that floor and
both Spearmans are present, otherwise `None`; require exact equality to the
published `paired_delta`, including nullness; derive the evaluable-season set
from that reconciled result. This replaces both the one-way support check and
the hard-coded `>0` approximation.

### BLOCKER R9-G2 — F13 exactness rests on a new trusted count and non-unique case rows

The runner now emits `window_high_season_count`; the gate at
`execution.py:1728-1815` checks only that it is a nonnegative integer and then
reduces it to `high_count > 0`. It does not bind the count to season evidence,
the three-season window, or the number of non-boundary seasons. The gate also
does not require unique `player_id` values in a fold's boundary cases.

Two impossible payloads therefore publish `run_status=ok`:

1. a case with one boundary season claims **999** high seasons inside the
   registered three-season window; that trusted truthy count masks the genuine
   +1-yard/game flip and the zero aggregate is accepted;
2. the same player row appears twice, and both copies are summed to a forged
   aggregate of two flips even though the shipped producer emits one case per
   evaluable player.

Reproducers:

- `test_f13_impossible_high_season_count_masks_a_flip`;
- `test_f13_duplicate_player_rows_inflate_aggregate_flips`.

Smallest correction: replace the count-only disclosure with mechanically
checkable trailing-window evidence (preferably all observed window rows for
each boundary player, or at minimum explicit high-season witness rows), then
validate season membership, positive games, threshold arithmetic, uniqueness
and disjointness before recomputing all three classifications. Require unique
boundary-case `player_id` values per fold and unique season rows per case;
derive any count, booleans, and fold aggregates from those rows rather than
trusting caller totals.

## Checks without findings

- R8-G1's partial/wholly-unavailable H5 split is now exact: partial evidence
  refuses; the wholly unavailable below-floor schema requires `ni_met=False`
  and the exact registered flag.
- The original four round-8 public-runner reproducers now all reject.
- The correction-contract suite passes **105/105**.
- The execution/program/inference bundle passes **211/211** with 12 known
  numerical warnings.
- The end-to-end composition positive path is included in the 105 passing
  correction contracts.
- Ruff, strict compilation, and `git diff --check` are clean for the three
  scoped files plus the independent probe.

## Independent probe

Artifact:
`docs/agent-ledger/evidence/2026-08-15/qb1_green_round9_adversarial_probe_codex_v1.py`

Reproduce:

```bash
PYTHONPATH=. .venv/bin/python3.14 -m pytest -q \
  docs/agent-ledger/evidence/2026-08-15/qb1_green_round9_adversarial_probe_codex_v1.py
```

Result: **5 passed**. Passing is the defect: every test asserts that a payload
impossible under the registered/shipped producer still reached public
`run_status=ok`.

## Separate verification failure in the frozen bundle

The exact unchanged reinforcement pin
`db351f8c321bd83179a8bab17beffc435709265e23909aff64468ecae981790d`
does not collect under the pinned `.venv/bin/python3.14` runtime:

```text
tests/contract/test_qb_validation_green_reinforcement_red.py:2081
ValueError: invalid signal dict
```

An isolated run of that file and a direct `decimal.Context().traps` comprehension
reproduce the error. This is not attributed to the round-9 three-file diff and
was not edited, but it means the submitted frozen-bundle census is not freshly
reproducible in the current environment. It is an additional reason a CLEAR
cannot be certified until its owning lane repairs the test construct or proves
the supported runtime.

## Disposition

**NOT CLEAR.** The publication gate still accepts five concrete impossible
reports, and one required frozen verification does not collect. No study
execution, publication, commit, push, or result claim. Round 9 closes and the
run re-parks for David; no further remediation round is inferred. H2 QB rushing
remains **UNDER TEST** with no result.
