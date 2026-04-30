# Next Sprint Plan

## Sprint Goal

Move from safer prototype surfaces toward a credible valuation foundation: formalize validation gates, expand Engine A features, and start the Engine B active-player path without widening the frontend.

## Priority Tasks

1. Update `docs/decision-output-contracts.md` to formalize the heuristic surface envelope now used by trade and roster.
2. Add pass/fail validation gates by position, using the current temporal holdout reports and saved model metadata.
3. Expand Engine A rookie features beyond pick, round, and age.
4. Add RAS ingestion pipeline and map RAS into the rookie feature set.
5. Define the Engine B active-player MVP boundary: feature collection, training placeholder, and `active_player_valuation` service skeleton.
6. Add focused tests for contract safety:
   - rookie output contract fields
   - centered driver attribution direction
   - trade experimental response has no verdict/totals
   - roster config failure returns structured 422

## Definition of Done

- Heuristic surface envelope is documented and matches roster/trade responses.
- Validation report is generated for each training run and converted into explicit pass/fail gates.
- Model artifacts are versioned and not silently overwritten.
- Rookie outputs stay contract-safe while adding at least one non-draft-capital feature source.
- Engine B has a clear code boundary but does not yet claim decision-grade active-player values.

## Deferred

- KTC live integration (explicitly deferred for this sprint).
- Frontend expansion until validation thresholds are met.
- Waiver prioritization until Engine B usage signals exist.
- Trade verdicts/totals until both sides consume unified valuations with calibrated uncertainty.
