# League-scope fixture migration ruling — Codex v1

**Date:** 2026-08-08 20:52 ET  
**Layer:** Layer 1 ingestion control  
**Ruling:** **inside the cleared GREEN scope**

The cleared contract explicitly removes flat game-calendar fallback and requires kickoff, final and
completion facts to be competition-scoped. Translating tracked test fixtures that still supply the
deleted flat shape is therefore a necessary part of implementing that contract, not a new product or
ingestion scope. The migration may touch the existing cadence and daily-controller contract files.

## Migration constraints

1. Move only `week1_kickoff`, `final_game` and `game_week_completions` into the appropriate
   `calendar.competitions.<nfl|fbs>` block. Preserve the original synthetic timestamps, event order,
   availability facts and asserted cadence behavior.
2. Fixtures shared by NFL and FBS behavioral cases must carry both explicit blocks; NFL-only cases
   may carry only NFL. Omission of FBS remains a deliberate evidence-absence case, not a shortcut in
   tests that intend to evaluate FBS.
3. Mutation/validator helpers must mutate the nested scoped field itself. Adding a bad flat
   `week1_kickoff` beside an unchanged valid scoped block would be ignored and make the rejection
   test vacuous.
4. No production governed-input artifact, source capture, provider contact, paid call or scheduler
   action is created by this fixture work.

## Two implementation-time corrections required before GREEN review

- `test_s7c...` currently uses
  `hasattr(m, "EXPECTED_STREAM_KEYS") ... else True`. The production module does not own the test's
  `EXPECTED_STREAM_KEYS`, so this branch is always `True`. Assert the test-local
  `("pff", "grades") not in EXPECTED_STREAM_KEYS` directly, or remove the redundant assertion;
  do not retain a knowingly vacuous guard.
- `_declarations()` and its local `out` still claim a list of three-field tuples while the collection
  now intentionally contains both legacy/non-game three-field declarations and scoped four-field
  declarations. Correct the annotation to the actual declaration union/type alias.

The 20 flat-fixture failures are therefore inside scope. Full unmasked gates remain required after
the migration; untracked withdrawn REDs must not be counted as clean-tree regressions.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
