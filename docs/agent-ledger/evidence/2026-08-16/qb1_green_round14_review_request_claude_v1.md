# QB-1 GREEN round-14 review request — Claude (write lane)

Date: 2026-08-16 ET
Authority: David's fresh bounded word for the revised placeholder predicate,
persisted in the round-14 transition (revision 81, open snapshot `0ebb1bf6…`
== round-13 close). Rerun remains held on your explicit CLEAR.
Layer: 2 curation at the label seam. Registration, gate, pins untouched.
Study execution: NOT rerun. H2 QB rushing remains UNDER TEST with no result.

## Round-14 pins (stable, submitted for review)

- `scripts/run_qb1_study.py`
  `8d7d525c1f5da0fa9a7311d0d2fef72353ee63969324d27257cfbcf5c0d87c63`
- `tests/contract/test_qb1_green_correction_contracts.py`
  `3a9c51f9ec8a2b943871ad9aa8f546166de00468e043a2697b0ffd65b59d039a`

Diff vs the round-14 open snapshot: exactly the two authorized files. Your
numstat governs the churn figure.

## Implementation — your revised boundary, exactly

- `exclude_provider_placeholder_rows` replaces the refuted name-based
  classifier: **missing player_id AND missing position AND validated exact
  zero across all 17 D2 inputs.** The 17-column set
  (`PLACEHOLDER_D2_COLUMNS`) is DERIVED from the builder's own constants
  (the 3 qualifying inputs + the 14 `SCORING_COMPONENTS` columns), never
  retyped; a contract pins the set at exactly 17 and equal to the builder's.
- **"Validated" is the builder's own semantics by construction:** the
  predicate imports and calls `qb_ppg_labels._stat_decimal` — yardage =
  finite real, counts = non-negative lossless integers, bool-kind refused.
  One consequence surfaced by mutation testing and DOCUMENTED rather than
  smoothed: the builder's `_lossless_int` parses numeric strings, so a
  string `"0"` IS a validated zero to the builder and therefore to the
  predicate (contracted explicitly as an excluded fixture with the reason in
  the comment); a malformed string (`"zero"`), boolean `False`, `None`,
  `NaN`, a negative count, a nonzero cell, and a MISSING column are all NOT
  validated zeros and stay fail-closed (each is a 1:1 mutant row).
- Names are audit evidence only: the three measured shapes (anonymous,
  "Team", "R.Rodgers") are excluded fixtures with different name values and
  identical predicate facts. Applied only at the copied records passed to
  `build_label_table` (non-mutation + copy both contracted);
  `weekly_records` stays unfiltered for the F13 panel; the untouched `pool`
  reaches `build_study_matrix` (§5).
- RED-before-GREEN: the 4 rewritten R14 contracts failed 4/4 against the
  round-13 classifier before implementation, then 134/134 after. The
  superseded R13 name-based tests were REPLACED (they contracted the refuted
  predicate), stated openly.

## Census at the pins above

- Correction contracts **134/134** · five-file bundle **689 passed** ·
  Ruff clean · strict compile clean · `git diff --check` clean · full-suite
  tally in the ADDENDUM.
- `finding-green-review-13-1` resolved in round 14 via the verb AFTER the
  implementation and the real-surface proof below.

## MANDATORY real-surface proof — AND the next wall, disclosed

Probe `qb1_placeholder_real_surface_probe_claude_v2.py` (derived from v1;
composition result discarded unread by design), run against the real store:

- REG records **191,281** → label records **191,089** → **excluded exactly
  192**; **kept rows with missing player_id: 0**; weekly frame digest
  **unchanged**. The label wall that failed both prior executions is CLOSED
  on the real surface.
- **The composition then advanced one stage and hit a NEW named failure:**
  `manifest_column_missing: pbp: offense_team`. Measured root (read-only):
  the admitted pbp store carries the RAW pin `posteam` (532,376 × 372;
  correct for a hash-before-parse raw snapshot), while the matrix's F15 gate
  (study_matrix.py:215-236) expects the POST-PARSE name via
  `VALIDATION_PARSED_RENAMES` — and NO step on the admitted read-back path
  (`admit_and_load_validation_pool` → `load_validation_sources` →
  `build_study_matrix`) applies the adapter's registered parse (REG filter +
  rename, nflreadpy_qb_adapter.py:565-566). **This is a NEW finding one
  stage downstream, OUTSIDE this round's boundary — nothing was touched.**
  It needs its own registration read (where does the parse step belong on
  the read-back path?) and its own David word.

## Boundary

No rerun (held on your CLEAR — and note the rerun would currently fail
closed at the pbp stage above), no input mutation, no registration/gate/pin
change, no commit, no push.

## ADDENDUM — full-suite tally

Full suite at the pins above (pinned 3.14.4; exit captured unpiped):
**6,136 passed / 15 failed / 12 skipped in 12:36.** All 15 verified BY NAME
in the standing UNTRACKED `test_governed_cadence_inputs_red.py` — zero
tracked failures, zero collection errors. Arithmetic reconciles: 6,132 (R12)
+ 4 net-new R14 contracts = 6,136.
