# Phase 13.3 TE Promotion Decision

> ⚠️ **SUPERSEDED (2026-06-26)** — this promotion's evidence (incl. the all-negative role-risk
> coefficients and the 760-row train set) was computed on a **contaminated seed** (one player =
> 35.3% of TE training rows). te_v3 was RE-DERIVED as a 14-feature/alpha=100 model with
> `te_role_is_risk_profile` dropped, justified by G2 stability only (accuracy within BCa noise).
> See `docs/validation/2026-06-26-te-v3-rederivation-decision.md`. Preserved for history.

**Date:** 2026-05-16
**Status:** PROMOTED TO `ACTIVE_B` — **SUPERSEDED 2026-06-26 (re-derived)**
**Model:** TE v3 (`te_v3.pkl`)
**Harness artifact:** `app/data/backtest/runs/eba2c2e4-9742-44ed-945a-8b46a0cb670f/backtest_result_TE.json`
**Deployment artifact:** `app/data/models/engine_b/runs/20260516T164503Z/te_v3.pkl`

## 1. Decision

TE is promoted from `EXPERIMENTAL` to `ACTIVE_B`.

The corrected Phase 13.3 sequence was followed:

1. Materialized `te_role_is_risk_profile` into `engine_b_features_v2.csv`.
2. Added `te_role_is_risk_profile` to the TE-only Engine B contract.
3. Updated the walk-forward harness TE alpha to `100.0`.
4. Validated through `scripts/run_backtest.py --position TE`.
5. Retrained a TE-only deployment artifact after the harness gate passed.
6. Removed TE from `ENGINE_B_EXPERIMENTAL_POSITIONS`.

## 2. Walk-Forward Gate Evidence

The harness refit Ridge inside each fold from the updated training CSV. It did not load a
deployment `.pkl`.

| Gate | Result | Evidence |
| --- | --- | --- |
| G1 rank correlation | PASS | Mean Kendall tau clears the TE threshold; all 4 folds have populated rank metrics. |
| G2 RMSE stability | PASS | RMSE max deviation = `10.53%`, below the 25% threshold. |
| G3 market superiority | DEFERRED | No market archive store was passed. |
| Overall grade | `ACTIVE_B` | G1 and G2 pass; G3 remains deferred. |

Fold-local `te_role_is_risk_profile` coefficients were negative in all 4 folds:

- 2020: `-0.0061995538`
- 2021: `-0.0996956560`
- 2022: `-0.2044285032`
- 2023: `-0.2531427466`

## 3. Deployment Artifact

TE-only deployment training wrote:

- `app/data/models/engine_b/runs/20260516T164503Z/te_v3.pkl`
- `app/data/models/engine_b/runs/20260516T164503Z/validation_report_te.json`

Deployment report:

- alpha: `100.0`
- train rows: `760`
- features: `15`
- `te_role_is_risk_profile` coefficient: `-0.4721918577`

No QB/RB/WR artifacts were rewritten by the deployment training path.

## 4. Governance Notes

- TE is `ACTIVE_B`, not `ACTIVE_B_VALIDATED`, because market superiority remains deferred.
- `decision_supported` remains `False`.
- No market-derived fields entered model inputs.
- No PFF grades, raw PFF rows, source-native IDs, local PFF paths, or player-level PFF artifacts
  were committed.
- The deployment manifest is local/ignored operational state, consistent with existing Engine B
  v2 artifact handling.

## 5. Verification

- Focused Phase 13.3 model-change tests: `65 passed`
- Full suite: `683 passed, 11 skipped`
