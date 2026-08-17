# QB-1 GREEN round-10 review request — Claude (write lane)

Date: 2026-08-15 ET
Authority: David's exact word — "one more bounded round - open round 10 per your
sanctioned mechanism, claude implements your two R9 smallest corrections,
execution only on your clear" — embedded in transition `TW15-QB1-R10-OPEN-CODEX-V1`.
Layer: 3 validation/publication gate. Layers 1–2 and the registration untouched.
Study execution: NOT run. H2 QB rushing remains UNDER TEST with no result.

## Round-10 pins (stable, submitted for review)

- `src/dynasty_genius/eval/qb_validation/execution.py`
  `68c72468c8022ad815ac96eb6594782b618354ae151320bf17c3aae085665eae`
- `scripts/run_qb1_study.py`
  `c9720e1bc08cd0e85c7a4929c6d4bd219b4dca9ffdea3bf59f900b97203fa4cc`
- `tests/contract/test_qb1_green_correction_contracts.py`
  `5246eaa5ca2f577f15635f185ac2ed72b6e5a3257c786d4aa1f03887e428f1e9`

Diff vs the round-10 open snapshot (`green-review-10/open`, hash `78b1d9f7…`):
exactly the three authorized files; changed lines 183 (execution) + 43 (runner)
+ 303 (contracts) = 529.

## R9-G1 — H5 admission now IMPLEMENTS the producer invariant

- `fold_min_evaluable_n` is bound from the registration's `fold_floors` block at
  the same site as the other floors; absence is `registration_drift` by name
  (`validate_registered_report_blocks`, floors block).
- For every H5 metric entry in a registered H5 fold the gate computes the
  producer-shaped expected delta: `spearman_left - spearman_right` exactly when
  `common_pool_n >= fold_min_evaluable_n` AND both Spearmans are non-null,
  otherwise `None`. The published `paired_delta` must EQUAL it, including
  nullness; any disagreement refuses as an unproducible record. The
  evaluable-season set is derived from the reconciled result (non-null expected
  delta), replacing both the one-way support check and the `>0` pool
  approximation. Producer parity notes: the producer nulls all three statistics
  on a starved fold and computes `delta = left - right` whenever both Spearmans
  exist (comparisons.py `_paired_fold`; `inference._reconcile_fold` refuses any
  disagreement), and a degenerate side manifests as a null Spearman in the
  published record — so gate computability from (pool floor + both Spearmans) is
  exact, with no honest-report false refusal. Float exactness is sound because
  the gate recomputes the identical subtraction from the identical published
  values.

## R9-G2 — F13 rests on disclosed evidence, no trusted count, no duplicate rows

- The runner now emits `window_seasons` per boundary case — EVERY observed
  trailing-window row (season, rushing_yards, qualifying_games) the shipped
  classification read — and no longer emits `window_high_season_count`.
- The gate requires the disclosure; validates each row (season inside the
  shipped trailing window, finite yards, nonnegative integer games) with
  unique seasons per case; requires `boundary_seasons` to be EXACTLY the
  boundary-band subset of the window rows under the registered relation
  (concealment and fabrication both refuse); derives the binary classification
  and both flip booleans from the full window evidence; and requires unique
  boundary-case `player_id` values per fold. Fold aggregates still must equal
  the case-row sums; all counts/booleans derive from rows — no caller total
  participates.
- Honest-path guards kept: a zero-qualifying-games window row (the producer's
  weeks counter can honestly be 0) and low rows are admissible; the
  near-season-plus-strong-season case publishes because the strong row is now
  disclosed evidence.

## Census at the pins above (all under the restored 3.14.4 interpreter)

- Correction contracts: **118/118** (105 carried + 13 net-new: 7 H5 admission
  rows incl. Codex probe rows 1–3 + floor-boundary/below-floor positives +
  registration-drift binding; 6 F13 rows incl. Codex probe rows 4–5 +
  subset-mismatch/outside-window/duplicate-season mutants + honest-evidence
  positives).
- Codex round-9 probe `e9ae56d9…`: **5/5 now FAIL** (every impossible payload
  refuses; verified failure mode is `run_status=failed`, not a crash).
- Carried probes all still reject: r1 **12 fail / 1 pass** (the pass is
  `test_admitted_receipt_is_rejected_by_existing_d1_gate`, a positive-path
  assertion whose pass is correct — disclosed) · r2 4 · r3 5 · r4 4 · r5 4 ·
  r6 6 · r7 9 · r8 4 — all fail as required.
- Five-file comparable bundle: **673 passed** (= 660 + the 13 net-new).
- Ruff clean · strict compile clean · `git diff --check` clean on the three
  files.
- Full suite: PENDING at request-write time; the tally is appended below when
  the run completes and is re-verified by name against the standing untracked
  cadence RED.

## Structured state

- Findings `finding-green-review-9-1` and `finding-green-review-9-2` resolved
  in round 10 via the verbs BEFORE this request was routed.
- Non-applying loop verdict: `ADJUDICATION_REQUIRED: PHASE_ROUND_CAP,
  RUN_ROUND_CAP` — expected under the intact ratified counters; round 10 also
  reaches the 10-round run cap. David's direct word is the recorded bounded
  exception; the prior Judge STOP is spent; nothing was applied or re-docketed.

## Boundary

No study execution, publication, registered-value change, provider fetch,
commit, or push. Execution only on Codex's explicit round-10 CLEAR; a BLOCKER
re-parks for David (and the write lane's stated expectation to David: a
round-10 NOT CLEAR goes to him as a redesign decision, not a round-11 request).

## ADDENDUM — full-suite tally

Full suite at the pins above, restored 3.14.4 interpreter, unpiped exit code
captured by the harness (exit 1, from the known failures below):
**6,120 passed / 15 failed / 12 skipped / 363 warnings in 8:04.** All 15
failures verified BY NAME: every one is in the standing UNTRACKED
`test_governed_cadence_inputs_red.py` (do not commit it) — **zero tracked
failures, zero collection errors**. Arithmetic reconciles: round-8's 6,093
+ 14 round-9 contracts + 13 round-10 contracts = 6,120.
