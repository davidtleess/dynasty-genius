# Next Sprint Plan

## Sprint Goal

Reframe execution around the two-engine architecture while improving model credibility and reproducibility.

## Priority Tasks

1. Stabilize configuration and remove hardcoded league/user settings from services.
2. Expand training features from available `nfl_data_py` Year 1 signals.
3. Add RAS ingestion pipeline and map RAS into rookie feature set.
4. Build holdout validation and sanity-check suite with pass/fail gates by position.
5. Add model versioning (artifact metadata + saved metrics) for traceability.

## Definition of Done

- Two distinct modeling tracks are represented in code and docs:
  - incoming rookie forecast track
  - active player forecast track
- Validation report is generated for each training run.
- TE model improves to non-negative explanatory signal on agreed validation.
- Model artifacts are versioned and not silently overwritten.
- Trade evaluator remains internal but reads from the shared valuation direction.

## Deferred

- KTC live integration (explicitly deferred for this sprint).
- Frontend expansion until validation thresholds are met.
