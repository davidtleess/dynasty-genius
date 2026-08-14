# Realized-outcome scorer wiring — green review round 3 (Codex v1)

Date: 2026-08-14
Work item: `TW0813-SCORER-1`
Role: adversarial reviewer / RED owner
Verdict: **NOT CLEAR — one BLOCKER**

## Pinned inputs verified

- `scripts/run_realized_outcome_scoring.py`: `42f5b736afe77076abef0834bb36d0254067288fde05e41cb10f203f1e773677`
- `tests/contract/test_realized_outcome_scorer_wiring_hardening.py`: `cb719113c4675323697ef4655867646349825aa46115d1eda347a21defb78b7e`
- `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py`: `e0b9f23449c57de47a942b6b51ff3448badea7e423aeb99d5efec48a96689009`
- `app/config/realized_outcome_frozen_predictions.json`: `77544b3b02850ceee1658806508af6e1af739fdf4cb0d756107195d6bb8bfce8`

## Checks and results

1. Replayed the two round-2 escaping shapes. Missing `games`, `games: null`, missing `rows`, `rows: null`, string `rows`, and string `coverage` all fail with their pinned named reason and write a terminal marker. A present empty `games` list remains a healthy off-season control.
2. Read the implementation boundaries. `_schedule_shape_ok` requires a present list `games` and dict rows. Prediction-envelope normalization requires a present list `rows`, mapping `coverage`, and dict rows; the legacy bare-list adapter remains explicit.
3. Ran the five primary scorer suites: **89 passed**.
4. Ran the four related store/bridge/route/registration suites: **52 passed**.
5. Replayed local stores read-only: prediction rows `501`; declared denominator `581`; excluded `capture_incomplete=80`; identity mappings `501`; identity duplicates `0`; util rows for 2026 week 1 `0`. No provider call and no scoring run were made.
6. `uvx ruff check`: clean. Strict `py_compile`: clean. `git diff --check`: clean.
7. Counted the offered hardening file: **22 tests**.
8. Performed a mutation-sensitivity break attempt against the proposed RED adoption. A schedule mutant that removes the explicit list guard while retaining the dict-row predicate passes all **5/5** schedule-shape rows, yet accepts `{"games": ()}` because `all(...)` is vacuously true. A prediction-envelope mutant that accepts tuple `rows` passes all **6/6** malformed-envelope rows. These are precisely the list-type contracts described by the implementation comments, so the current RED does not prove either guard.

## Finding

### R3-B1 — BLOCKER — empty non-list collections leave both list-shape guards mutation-insensitive

The current product code is correct. The blocker is the requested final adoption of the 22 hardening rows as the pinned RED set: neither parameterization contains an empty wrong-type collection. Consequently, deleting or weakening either explicit list guard survives the offered tests.

Smallest required RED correction:

1. Add `{"games": ()}` to the malformed-schedule parameterization and retain the terminal-marker/no-downstream-loader assertions.
2. Add `{"rows": (), "coverage": {}}` to the malformed-prediction-envelope parameterization and retain its terminal-marker/no-downstream-loader assertions.
3. Add a mapping-envelope positive control for `{"rows": [], "coverage": {}}` proving validation occurs before the existing `no_predictions_for_target` noop. The current bare-list positive control proves only the legacy adapter.

Expected hardening census after the minimal correction: **25 rows**. No product-code change is requested.

## Disposition

The round-2 implementation fixes are independently verified and correct, but the 22-row hardening set is **not adopted** as final RED while R3-B1 remains open. The first live finalized-week run remains David-gated; it was not performed.
