# QB-1 missing-identity placeholders — corrected registration read

Date: 2026-08-16 09:34 EDT
Disposition: **IMPLEMENTATION, not amendment**, but outside the currently
authorized Round-13 name-based predicate.

This document supersedes only the measured-shape and predicate portions of
`qb1_team_aggregate_registration_read_codex_v1.md`. Its registration-clause
analysis, label-only placement, full-pool preservation, and no-input-mutation
boundary remain valid.

## Correction of record

The earlier claim that the pinned admitted weekly pool carried 236 rows all
having missing `player_id` and exact `player_name == "Team"` was false. The
underlying census printed `head(3)` and the sample was generalized to the
class. It also mixed all season types with the REG-only label input.

Independent full-frame reproduction against the pinned weekly Parquet found:

- 199,868 total rows;
- 191,281 REG rows reaching the label adapter before identity handling;
- 192 REG rows with missing `player_id`;
- 181 with missing player name, display name, and position;
- 10 with exact `player_name == "Team"`, missing display name and position;
- 1 with `player_name == "R.Rodgers"`, missing display name and position.

The exact Round-13 name predicate therefore excludes only 10 of 192 relevant
rows and leaves 182 missing identities. The label builder still refuses with
`label_row_invalid`. These rows are not team aggregates: sampled rows carry
zero while identified same-team/week player rows sum to nonzero production.
The accurate label is **provider placeholder rows**.

## Independent label-content census

Codex checked every one of the 192 REG missing-id rows across the complete D2
input set, not the 11-column subset used by Claude's first content probe:

- qualifying inputs: `attempts`, `sacks_suffered`, `carries`;
- all 14 raw fields in exported `SCORING_COMPONENTS`: passing yards, TDs,
  interceptions, and 2PT conversions; rushing yards, TDs, and 2PT
  conversions; receptions, receiving yards, TDs, and 2PT conversions; and
  the three fumbles-lost fields.

Result: zero missing cells, zero nonzero rows, zero nonzero column totals,
and **192/192 rows exact zero across all 17 fields**.

## Registration classification

The corrected narrow classifier is still an implementation of the frozen
registration:

1. §3 defines `y(p,t)` for a player `p` and pins a qualifying game to
   `(attempts + sacks_suffered) >= 1 OR carries >= 1`. Every measured
   placeholder has all three inputs exactly zero, so none is a qualifying
   game.
2. §2.1 pins all scoring components used by the label. Every measured
   placeholder is exact zero in all 14 raw scoring fields, so none can change
   points.
3. §4 pins the cohort to `QB_at_matrix_build`. Every measured placeholder has
   no player id and missing position. It cannot instantiate a player or a QB
   cohort row.
4. §5 still requires the admitted pool intact for all-position,
   pre-QB-filter team aggregation. Classification therefore remains only on
   the copied records passed to `build_label_table`; `pool` must remain
   byte-untouched and must reach `build_study_matrix` unchanged.

The registration's zero-qualifying attrition semantics do not license
dropping an identified zero-stat player row. That is why missing identity and
missing position are mandatory limbs: an identified player or a position-QB
row stays in the label path. The content limbs prove label neutrality; they
do not become a general zero-row drop.

## Revised exact boundary

The smallest defensible predicate is:

`missing player_id AND missing position AND exact validated zero in all 17 D2 scoring/predicate inputs`

Names are audit evidence only, never predicate inputs. Apply the predicate to
the list passed to `build_label_table` and nowhere else.

Fail closed — do not exclude — when any limb is not proven, including:

- any usable player id;
- any non-missing position, especially `QB`;
- any absent, null, non-numeric, non-finite, boolean, lossy, negative-count,
  or nonzero D2 field;
- any caller-controlled scalar whose zero comparison is not reduced through
  trusted value semantics;
- any non-REG row (the existing REG filter remains the prior step).

Required contracts cover all three measured name shapes, all 17 one-at-a-time
nonzero mutants, missing/null/malformed value mutants, a missing-id `QB`
zero-row, an identified zero-row, input immutability, exact 192-row real-store
exclusion, zero residual missing identities at label input, and proof that the
original full pool reaches `build_study_matrix`.

## Authority boundary

David authorized Round 13 with the explicit name-based predicate `null
player_id + player_name "Team"`. The corrected content/position predicate is
a material scope change even though it is registration implementation. It
must not be substituted silently. Round 13 is NOT CLEAR and the registered
rerun remains held. A fresh David word is required to authorize one bounded
correction round under this revised boundary.

H2 QB rushing remains **UNDER TEST with no result**.
