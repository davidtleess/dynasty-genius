# QB-1 GREEN Round 16 Independent Review — Codex v1

Date: 2026-08-16 ET  
Verdict: **CLEAR** for the exact shared matrix-placeholder boundary  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Round: `green-review` 16

## Pins and scope

- Claude request SHA-256:
  `0b8af1c4d082fee71bd5ddce84101587ff98ae8ed97e56934620a1a5fbe19385`.
- `qb_ppg_labels.py`:
  `e5cb3955142b365a9dc929e18a7ceda33f647613fc8610442a2b39fa7ca73edf`.
- `study_matrix.py`:
  `518e4b82c79d6a9637ae5bca5b6eb0aba7b82afc212ce1d01b7fe8a69d50e389`.
- `run_qb1_study.py`:
  `7de911cccdcb17ae0e37ca48b5816a50420dbcd0e61303f663553d381c97a798`.
- Correction contracts:
  `7407dc6c46237d7c3a23e3f3db044f56583db5d553c793fead9486684aab36c9`.
- Diff from the Round-16 open snapshot
  `a9c212426e55cbcd08a96428c184703d2e273e821fe20406150fbc0f810fb542`
  is exactly the four authorized files: 273 changed lines (`+200/-73`). No
  registration, input artifact, source pin, publication gate, dependency,
  configuration, provider, commit, or push change is present.

## Enumerated independent checks

1. **One classifier:** `PLACEHOLDER_D2_COLUMNS` and
   `exclude_provider_placeholder_rows` now live beside `_stat_decimal` in
   `qb_ppg_labels.py`. The runner and matrix import the same function object;
   the former preserves its existing re-exported surface. No second predicate
   or validator exists.
2. **Exact predicate:** the 17-column tuple is derived from the label builder's
   three qualifying inputs plus its 14 scoring columns. Exclusion requires
   missing `player_id`, missing `position`, and a present validated exact zero
   in every column. Names do not participate. The classifier returns a new
   list and does not mutate rows or the admitted frame.
3. **Matrix placement:** source admission receives the original pool. Inside
   `build_study_matrix`, the defensive frame passes shape and manifest gates
   before conversion to defensive records. Classification occurs immediately
   before `_validated_weekly_row`; the pool and frame are not filtered or
   rewritten.
4. **Near-miss totality:** independent direct matrix-seam probing kept and then
   refused **24/24** missing-id near misses with `stat_value_invalid`: one
   nonzero mutation for each of the **17/17** D2 inputs, plus position-bearing,
   null, NaN, boolean, malformed, negative, and missing-column mutants. The
   exact positive placeholder control alone was excluded.
5. **Analytical invariance:** the new contract composes the hermetic study with
   and without both missing-id placeholder forms. Every analytical and
   non-row-count input block is equal; only the honest raw weekly-row disclosure
   differs by two. This covers folds, lanes, panels, and the §5 all-position
   rushing denominator without hiding input cardinality.
6. **Independent real surface:** replay of the final probe against the admitted
   store passed: 199,868 defensive records; **236** exact exclusions comprising
   **192 REG + 44 non-REG**; zero residual missing ids; all 199,632 kept rows
   pass `_validated_weekly_row`; 191,089 REG validated rows; **352** team-season
   rushing-total keys with **0 mismatches** and **0 unparseable rows**; admitted
   weekly-frame digest unchanged. Probe script SHA-256
   `9a30c794275d4f071092d79403f4ae35e59622e2063930f2c14ba4228b3a4283`.
7. **Tests:** independent five-file bundle passed **699/699** in 59.66s.
   Claude's final-pin full suite reports **6,146 passed / 15 failed / 12
   skipped**; all 15 are named in the standing untracked cadence RED, with
   zero tracked failures and zero collection errors.
8. **Static and hygiene:** Ruff on all four scoped files plus the real-surface
   probe, strict Python compilation, and `git diff --check` pass independently.
   No secret, dependency, configuration, cleanup, or scope violation appears.
9. **Wall-language correction:** the Round-15 probe established one observed
   next wall only. Round 16 closes that specific matrix wall. No later stage
   was exercised and no claim is made that no later wall exists; the registered
   rerun must fail closed by name if another exists. This resolves
   `R15-G2-WALL-CENSUS-TOTALITY` without converting the old overclaim into
   evidence.

## Verdict and execution boundary

**CLEAR.** No Round-16 blocker remains. This CLEAR releases exactly the fresh
registered rerun David already granted. It is not a result ruling, publication,
commit, push, merge, source refresh, input mutation, or registered-value change.
The runner must fail closed if another wall exists; any completed registered
readout goes to David untouched for his separate ruling. Until execution and
that ruling, H2 QB rushing remains **UNDER TEST** with no result.
