# Phase 13.3.4 TE Regularization Bake-Off Decision

Date: 2026-05-16
Status: APPROVED FOR VALIDATION-ONLY BAKE-OFF
Owner: David

## Decision

Continue Phase 13.3 with a TE-only regularization bake-off before any role-risk production
model-change spec.

Do not productionize `role_risk_detector` from the Phase 13.3.3 artifact.

## Rationale

Phase 13.3.3 showed that the role-risk signal is useful but not yet production-safe at the
current TE alpha:

- Primary alpha `1.0`:
  - `sparse_duo` improved RMSE/MAE and had negative coefficients, but failed rank-degradation gate.
  - `unified_penalty` improved RMSE/MAE and had a negative coefficient, but failed rank-degradation gate.
- Sensitivity alpha `100.0`:
  - `unified_penalty` passed all gates.

This suggests the open question is no longer only "does role-risk help?" The better question is:

> Is the TE model under-regularized, and does stronger regularization preserve rank stability while
> retaining the role-risk error improvement?

## Approved Scope

Run a validation-only TE regularization bake-off over:

- baseline TE features only;
- baseline TE features + `unified_penalty`;
- optional baseline TE features + sparse role-risk duo for comparison.

Recommended alpha grid:

- `1.0`
- `10.0`
- `50.0`
- `100.0`
- `250.0`
- `500.0`

## Required Metrics

Report, by alpha and candidate:

- fold-level RMSE;
- fold-level MAE;
- fold-level Spearman rho;
- fold-level Kendall tau;
- mean deltas vs baseline alpha `1.0`;
- candidate coefficient sign;
- acceptance flags.

## Acceptance Bar

A candidate/alpha pair may justify a later production model-change spec only if:

- RMSE improves in at least 3 of 4 folds;
- mean RMSE improves;
- mean MAE improves;
- no fold violates the rank-degradation threshold;
- candidate coefficient for the risk signal is negative;
- the result is not dependent on one outlier fold;
- redaction and leakage checks pass.

Passing this bake-off would justify writing a production model-change spec. It would not itself
change production scoring.

## Required Constraints

- TE remains `EXPERIMENTAL`.
- No production model artifact promotion.
- No changes to `app/data/models/engine_b/v2_manifest.json`.
- No changes to the current Engine B production feature contract.
- No PVO scoring changes.
- No market-derived fields.
- No PFF grades.
- No raw PFF rows, raw PFF IDs, source-native IDs, local PFF paths, or player-level PFF artifacts
  committed.
- Output artifacts remain aggregate only.

## Next Step

Write a Phase 13.3.4 implementation plan for the TE regularization bake-off.
