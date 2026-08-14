# Realized-Outcome Scorer Wiring — Codex RED v1

**Cycle:** TW0813-SCORER-1 · **Date:** 2026-08-14 · **RED author:** Codex  
**Authority:** framing v3 `71019940…` + v4 `77e92aed…`  
**Framing CLEAR:** `realized_outcome_scorer_wiring_framing_v4_review_codex_v1.md`,
SHA-256 `45112e032970418c83a6dda09da16716876ed901d5d5728747057db2baa32a0a`.

## Frozen RED artifacts

- `tests/contract/test_realized_outcome_scorer_wiring_red.py` — SHA-256
  `723545885e652a3cbcc004b04a398f6904022024a2eece4841bddd6af63a0137`.
- `tests/unit/test_realized_outcome_scorer.py` — SHA-256
  `b7b0d85d3e49545df8222329b37782b175a0970404f18346656f736da10cc7f9`
  (35-line focused addition only).

## Contract frozen for GREEN

1. Default prediction loading returns a `{rows, coverage}` envelope. Coverage is derived from
   the declared capture's five-key joinable/model-supported universe, never from the whole
   snapshot and never from a hardcoded production count. Rows preserve frozen DG identity,
   prediction provenance, and validated parsed utilization roles/values.
2. Declaration roots/seasons/entries, ISO date/timestamp formats, and duplicate JSON keys fail
   with named reasons. Utilization invalid JSON/shape/value/role likewise fails named.
3. Identity wiring reuses canonical `_load_ff_playerids`, pins pull timestamp/file SHA/mapping
   version/duplicate count, and keys mappings by the frozen `dg_player_id`. Empty/conflicting
   crosswalks fail named.
4. Realized utilization reads `player_snap_count` URI-read-only, maps PFR→GSIS through that
   crosswalk, emits snap share only, and rejects non-finite/out-of-range/duplicate weekly rows.
   Unresolved/no-row players receive explicit unavailable facts; `ff_opportunity` remains banned.
5. The outcome universe is seeded from resolved frozen players. A stat-absent player gets an
   explicit zero-game `status_unverified` OutcomeRow and an explicit unavailable weekly-util
   fact, never a guessed football status.
6. Nonfinal targets at day 14 remain healthy `week_not_finalized`; strictly day 15+ fail
   `week_nonfinal_overdue`. The law applies to explicit and scheduled invocation. Missing or any
   mixed malformed target gameday fails `nonfinal_age_indeterminate`.
7. The default score-derived schedule never certifies finality; observed scores remain
   `result_observed_unverified`. Real terminal evidence remains injected and provider-gated.
8. Coverage is copied to result, scorecard, and marker with separately named declared, eligible,
   resolved, outcome-present, graded, and rank-eligible counts plus prediction/identity exclusions.
   Zero graded fails and writes no scorecard; nonzero catastrophic partial coverage is disclosed
   without an invented band.
9. At settlement week 34, zero-game `status_unverified` membership is retained but the floor is
   withheld: realized stays `None`, the row is not rank-eligible, and exact status is
   `survivorship_floor_withheld_status_unverified`. Week 33 stays partial; verified departures
   preserve today's floor.
10. Source stores remain URI `mode=ro`; existing recursive No-Verdict, subprocess/git prohibition,
    ephemeral outcome store, and artifact-only write laws remain green.

## Verification

- Targeted RED: **27 failed, 3 passed, 9 deselected**. The three passes are intentional positive
  controls (day-14 on both invocation modes; `ff_opportunity` remains absent). No collection or
  fixture error.
- Existing scorer unit tests excluding the new case: **9 passed**, two known SciPy degenerate-data
  warnings.
- Existing CLI contract: **10 passed**.
- Combined collection: **39 tests collected**.
- `py_compile`: pass. Touched Ruff: pass. `git diff --check`: pass.
- Product implementation was not edited by Codex. The pre-existing uncommitted prediction-loader
  diff in `scripts/run_realized_outcome_scoring.py` remains implementation-lane work under review.

## Handoff gate

Claude should first adversarially review this RED for false positives/overconstraint, then implement
GREEN. Any proposed contract change returns to Codex before implementation; passing by weakening or
deleting a RED row is not GREEN. No commit or push authority is created.
