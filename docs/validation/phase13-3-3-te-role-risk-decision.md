# Phase 13.3.3 TE Role-Risk Detector Decision

Date: 2026-05-16
Status: APPROVED FOR CONTROLLED EXPERIMENT
Owner: David

## Decision

Advance `role_risk_detector` from validation evidence to a narrow TE-only model-change
experiment.

This is not production adoption. It does not change Engine B production feature contracts,
promoted model artifacts, TE promotion status, PVO scoring, or David-facing decision surfaces.

## Evidence

Phase 13.3.2 bake-off artifact:

- `app/data/backtest/phase13/te_archetype_bakeoff_20260516.json`

Result summary:

| Candidate | Mean RMSE Delta | Mean MAE Delta | RMSE Win Folds | Acceptance |
| --- | ---: | ---: | ---: | --- |
| `role_risk_detector` | -0.0392 | -0.0514 | 4 / 4 | PASS |
| `fantasy_role_one_hot` | -0.1835 | -0.1900 | 2 / 4 | FAIL |
| `snap_alignment_one_hot` | -0.0656 | -0.0725 | 1 / 4 | FAIL |
| `complete_te_detector` | +0.0029 | +0.0028 | 2 / 4 | FAIL |

Interpretation:

- Broad TE taxonomy is not stable enough for production use.
- The narrow risk signal is consistent across folds.
- The useful signal appears to be penalty/risk identification, not a positive boost for
  complete or receiving TEs.

## Approved Experiment Scope

The next experiment may test only this feature family:

- `te_role_risk`
- `te_blocking_specialist_or_role_risk`

The experiment may evaluate whether this signal should enter a future TE-only Engine B candidate.

## Required Constraints

The experiment must preserve all of these:

- TE remains `EXPERIMENTAL`.
- No production model artifact promotion.
- No changes to `app/data/models/engine_b/v2_manifest.json`.
- No changes to the current Engine B production feature contract.
- No market-derived fields.
- No PFF grades.
- No raw PFF rows, raw PFF IDs, source-native IDs, local PFF paths, or player-level PFF artifacts
  committed.
- No David-facing confidence upgrade unless normal promotion gates pass in a later approved spec.

## Minimum Acceptance For Future Promotion Consideration

A future TE model-change experiment must show:

- RMSE improvement in at least 3 of 4 walk-forward folds.
- Mean RMSE improvement.
- Mean MAE improvement.
- No material degradation in rank metrics.
- No leakage or redaction violations.
- TE promotion gates still report `EXPERIMENTAL` unless a separate promotion spec is approved.

Passing this experiment would justify a model-change proposal. It would not automatically promote
TE or alter production scoring.

## Audit Caveat

The Phase 13.3.2 artifact stores repo-relative source paths such as:

- `app/data/training/engine_b_features_v2.csv`
- `app/data/identity/te_archetype_rubric_20260516.json`

These are provenance references, not source-native IDs or private local paths. They may become
stale if the repository layout changes, so any future replay should verify the referenced paths
still exist.

## Next Step

Write a Task 13.3.3 implementation plan for a controlled TE-only model-change experiment using
the `role_risk_detector` family. The plan should use TDD and should keep production model routing
unchanged until David approves a separate promotion decision.
