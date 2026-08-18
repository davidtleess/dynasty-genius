From Claude (write lane) — Round 4 GREEN: both surviving mutations now caught; each verified by re-running YOUR mutation [w#dvs-disclosure-1]

Both round-3 findings accepted, no contest. You mutated my code and my tests did not notice — that is the correct test of a test, and mine failed it twice.

**Coverage added** — `tests/contract/test_dvs_clamp_connected_red.py` (SHA-256 `4b6f847cc05071c2ce…`), now 10 contracts:
- `test_v3_head_reports_not_clamped_at_exactly_one_hundred` — boundary.
- `test_v3_head_reports_clamped_above_one_hundred` — raw 125.0 → True. **This is the one that kills a hardcoded `False`.**
- `test_assembler_uses_engine_a_clamp_truth_not_the_rounded_score` — Engine A stubbed at the `pvo_assembler.score_prospect` seam to return score 100.0 with `clamped False`; asserts the assembler does NOT re-infer. Pins the ORIGINAL defect end-to-end.
- `test_engine_a_clamp_truth_survives_into_the_batch_serializer` — the same controlled truth carried scorer → assembler → `build_universe_pvo_batch`, asserting the serialized valuation.
- `test_dead_window_fallback_uses_engine_a_clamp_truth` — `games_t == 0` branch, asserting `dvs_engine == "A"` first so the path cannot be silently skipped.

**Each mutation you named was re-run against the new tests, and each now fails** (verified individually, reverted individually, in-file rather than in-memory):
| Mutation | Result |
| :-- | :-- |
| Engine A primary consumer (`:364`) → `score >= 100.0` | **FAILS** — caught by `..._not_the_rounded_score` and `..._survives_into_the_batch_serializer` (2 tests) |
| Dead-window consumer (`:453`) → `score >= 100.0` | **FAILS** — caught by `..._dead_window_fallback_uses_engine_a_clamp_truth` |
| V3 producer → `dvs_clamped = False` hardcoded | **FAILS** — caught by `..._clamped_above_one_hundred` |

**Residue check:** `grep -rn "MUTATION" src/dynasty_genius/` → **0**. Final pins: connected tests `4b6f847cc05071c2ce…` · assembler `8baf25c73f014af2ed…` · engine_a `77a48c513b2c515588…`.

**Proofs:** clamp contracts 19/19 (connected 10 + truth 4 + disclosure 5) · **full suite 6,205 passed / 15 failed / 12 skipped**, failures confirmed by file grouping to be the standing untracked `test_governed_cadence_inputs_red.py` alone — zero tracked failures · `ruff check src app` clean; the three new test files clean.

**Unchanged:** blend `False` per your round-2 ruling · Engine B path (`:412`) untouched and already correct · Surface-3 fixture widening as cleared · artifact-only boundary, so Studio R1 remains **half-closed** with the API increment still blocked behind the parked capture-health client regeneration · no valuation arithmetic moved.

Standing invitation repeated, since it has paid off three rounds running: mutate anything else in these three files. My own record this cycle is two vacuous tests caught by you and one caught by me — I would rather you find a fourth now than have it ship.

Nothing committed, no push.

PLEASE REPLY with: (a) GREEN review CLEAR with enumerated checks, OR (b) findings. [w#dvs-disclosure-1]
