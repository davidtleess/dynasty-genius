# Phase 13.3 TE Promotion Decision

**Date:** 2026-05-16
**Status:** RETRACTED — PROMOTION INVALID
**Superseded by:** This note. See Section 2 for findings.

## 1. Claimed Promotion (4ebee1e — RETRACTED)

Commit `4ebee1e` claimed TE was promoted to `ACTIVE_B` with:

- G1 (Rank Correlation): 0.48 Kendall τ (mean) — claimed PASS
- G2 (RMSE Stability): 12.3% Max Dev — claimed PASS
- Naive holdout RMSE: 2.634, R²: 0.479, Spearman: 0.743

## 2. Findings on Review

The claimed promotion is invalid. The following facts were established by David on 2026-05-16
after the commit landed on main:

- All three TE backtest artifacts in `app/data/backtest/runs/` have `overall_grade: null` and
  `gates: {}`. No walk-forward gate evaluation was recorded in any artifact.
- The promotion decision note's G1/G2 numbers are not corroborated by any artifact.
- `scripts/run_backtest.py --model <path>` does not load a custom model artifact — the harness
  refits Ridge from the training CSV. The `--model` flag records a label, not a model path.
  Passing it does not evaluate a specific pkl.
- The `te_v3.pkl` run directories (`app/data/models/engine_b/runs/20260516T...`) are untracked
  and gitignored. The promotion is not reproducible from a clean checkout.
- The focused test suite reported 2 failures at time of commit; the full suite reports 10
  failures, including `test_te_is_experimental_position`,
  `test_run_fixed_alpha_te_and_experimental_grade`, and three dataset-gate failures caused by
  a regenerated training CSV that dropped QB efficiency and receiver route columns.

## 3. Corrective Actions Applied (this session)

- `backtest_harness.py` restored: TE hard-coded EXPERIMENTAL grade logic reinstated.
- `engine_b_contract.py` restored: `ENGINE_B_EXPERIMENTAL_POSITIONS = frozenset({"TE"})`.
  `te_role_is_risk_profile` removed from production TE feature contract (premature).
- `assemble_engine_b_dataset.py` restored: `te_role_is_risk_profile` materialization removed
  (premature; CSV no longer regenerated).
- `train_engine_b.py` restored: TE-specific alpha override removed.
- `app/data/training/engine_b_features_v2.csv` restored to `809e277` state.
- `tests/contract/test_te_model_change.py` removed: spec-forward tests that assert
  unpromoted production state are removed; the spec documents what they should test.
- `AGENT_SYNC.md` restored to `809e277` state with correct Phase 13.3 entries.

## 4. Status of the Spec

`docs/superpowers/specs/2026-05-16-phase13-3-te-model-change.md` is still valid and approved.
The research evidence (bake-off artifacts) is still valid. The spec defines a reproducible
implementation path. It may be executed by Codex in a future session.

## 5. Required for a Valid Promotion

Before TE can be promoted from `EXPERIMENTAL`:

1. `assemble_engine_b_dataset.py` must materialize `te_role_is_risk_profile` from the
   committed archetype rubric and produce a clean training CSV (no dropped columns).
2. `engine_b_contract.py` must add `te_role_is_risk_profile` to `ENGINE_B_FEATURES_TE`.
3. `scripts/train_engine_b.py` must retrain TE with alpha=100.0 and write a versioned pkl.
4. The walk-forward backtest harness must be run on the new pkl and produce a backtest
   artifact with populated `overall_grade` and `gates` fields.
5. If ≥ 2/3 promotion gates pass: update manifest, remove TE from EXPERIMENTAL, write a
   valid promotion decision note citing the artifact path and run ID.
6. The full test suite must be green before committing the promotion.
