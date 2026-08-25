# DG-022 — Frozen prediction membership truth

## Outcome

Expose whether a player had a prediction in the declared 2026 frozen evaluation cohort. This is a
historical fact, separate from current model status and separate from canonical identity. Leave
universe identity, forward-capture joinability, and scorer eligibility unchanged.

The ticket premise is corrected by evidence: null `dg_player_id` is not the join discriminator,
and current `PRE_MODEL` cannot prove historical exclusion. Tank Dell had a stable Sleeper key in
the raw August 5 capture, with `PRE_MODEL`; he was absent from joinable capture and therefore had no
frozen prediction for 2026 evaluation.

## Evidence chain

- `app/config/realized_outcome_frozen_predictions.json:4-16` declares the 2026 frozen capture as
  `2026-08-05`, source `model_pvo`.
- `src/dynasty_genius/capture/model_forward_capture_store.py:81-110` prefers Sleeper for the stable
  player key and restricts joinable rows to model-supported routes; null `dg_player_id` does not
  block a Sleeper-keyed raw row.
- `scripts/run_realized_outcome_scoring.py:741-835` uses the declared joinable + prediction-snapshot
  set as its immutable denominator.
- Read-only SQLite evidence:
  `sqlite3 -readonly app/data/model_forward_capture.db "... sleeper_id='9502' ..."` returns Tank as
  raw `PRE_MODEL` on every capture including August 5 and returns no joinable row.
- A read-only current-runtime-roster/frozen-set intersection measured 274 rostered skill players,
  221 with captured frozen predictions, and 53 without. That count is current-roster coverage
  against an immutable historical set; it is not an identity-remediation counter and must not be
  described as retroactively shrinkable.

## Test-first implementation sequence

1. Add a small read-only resolver that loads the declared season/date/source, opens the capture DB
   in SQLite `mode=ro`, and joins raw → joinable → prediction snapshot on all five key columns.
2. RED/GREEN the historical classifications: included, not in frozen cohort, incomplete capture,
   unavailable, missing player, and agreeing/conflicting same-day vintages.
3. Add a nested typed `frozen_prediction` response lane; do not overload current `model_status`.
4. RED/GREEN both temporal counterexamples: current PRE_MODEL + frozen included, and current modeled
   + frozen excluded.
5. Regenerate OpenAPI/types/Zod and render the historical lane in full detail and inspector.
6. Probe Tank and the aggregate current-roster coverage against the shared store read-only, then run
   focused/full gates and independent visual/contract review.

## Falsification matrix

| Input class | Expected result |
| --- | --- |
| frozen joinable + captured finite prediction | `included` |
| frozen raw PRE_MODEL, Sleeper known, dg null | `not_in_frozen_prediction_cohort`; never identity pending |
| no frozen raw row for Sleeper | excluded with `not_present_in_frozen_universe` basis |
| model-supported raw but joinable absent | `unavailable`; storage inconsistency is not exclusion |
| joinable row with missing/incomplete prediction | `prediction_capture_incomplete` |
| duplicate same-day rows with agreeing semantics | deterministic shared classification |
| duplicate same-day rows with conflicting semantics | `unavailable`; never first-row-wins |
| malformed/missing declaration or store | historical lane unavailable; current player and market lanes stay usable |
| current PRE_MODEL + frozen included | current score unavailable; historical lane included |
| current modeled + frozen excluded | current score shown; historical lane excluded |
| later promotion/demotion | frozen state unchanged |
| wrong-type/non-finite prediction | unavailable/fail closed |

## Presentation composition artifact

**Five-second answer:** David sees two independent truths: whether the player has a score now, and
whether a model prediction was frozen for the 2026 outcome evaluation.

**Focal hierarchy:** player identity remains first; current model/market lanes remain primary; a
compact neutral evaluation strip follows the current model-state block and precedes valuation. The
strip has a short label, one plain-language state, and one roster coverage sentence.

**Desktop sketch:** existing player header → existing current-state disclosure → neutral `2026
evaluation` strip (`Included in frozen model snapshot`, `Not in 2026 model snapshot`, `Prediction
snapshot incomplete`, or `Evaluation status unavailable`) → one sentence of manager copy → `221 of
274 current rostered skill players were included` → existing two-lane model/market content.

**Mobile sketch:** the same strip becomes a single vertical stack. State and coverage wrap; there is
no table, horizontal scroll, tooltip dependency, raw token, ID, or ISO timestamp.

**Visual rules:** slate/neutral border only; no win/loss hue, model blue, or market amber. The year is
human-readable; basis tokens and frozen date remain API evidence and are not printed in the card.

## Acceptance evidence

- RED observed before each production seam.
- Focused resolver/API/UI contracts and relevant regression suites pass.
- OpenAPI and generated TypeScript/Zod match the backend contract.
- Read-only Tank probe reports frozen exclusion with basis `non_model_route_at_freeze` and roster
  coverage 221/274 included, 53 excluded.
- Desktop, mobile, and mid-scroll browser captures pass an independent unanchored visual audit.
- No universe identity, capture joinability, scorer eligibility, frozen declaration, or shared data
  changes.
