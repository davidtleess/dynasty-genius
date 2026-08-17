# QB-1 team-aggregate failure — Codex registration read

Date: 2026-08-16 08:47 EDT
Classification: **IMPLEMENTATION, not a registration amendment**, under the
narrow boundary below.

## Measured execution fact

The first registered execution wrote the atomic metric-free terminal artifact
`app/data/backtest/qb_validation/qb_validation_report.json`:

- SHA-256:
  `fb222a60957e2ae4a353ed730ff5ddccdfac5cb9bbc803cdc2cefe6c62306244`
- `run_status = "failed"`
- `failure_reason = "label_row_invalid"`
- registration hash:
  `37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d`
- no metric blocks; `decision_supported = false`.

Independent replay of Claude's read-only diagnostic reproduced the exact
refusal: weekly row 1026 has `player_id=nan`, season 2015, week 1. Independent
census reproduced **236 / 199,868** admitted weekly rows with null `player_id`;
all measured examples are provider team-aggregate sentinels with
`player_name="Team"`, null position, and 21–22 rows in every season 2015–2025.

## Registration clauses and classification

The frozen registration defines:

1. §3: target `y(p,t)` is regular-season fantasy points per qualifying game
   **for player p**. A provider team-aggregate entity cannot instantiate
   player `p`.
2. §4: the cohort is **every QB** satisfying the registered prior-dropback and
   roster-presence rules. The canonical object pins
   `cohort.position_filter = "QB_at_matrix_build"`. A null-identity,
   null-position team entity is not a QB cohort row.
3. §5: H2's team rushing-TD denominator comes from the **all-position
   pre-QB-filter aggregation**. That clause requires the admitted source pool
   to remain intact for feature/team aggregation; it does not require a team
   entity to enter the player-label table.
4. §3's fail-closed validation still governs malformed player rows. The
   implementation may classify only the exact provider team-aggregate shape;
   every other missing or unusable player identity must continue to refuse.

Therefore, excluding the exact provider team-aggregate sentinel from the
**label adapter only**, before `build_label_table`, is a mechanical
implementation of the already-registered player/QB domain. It does not change
the cohort, target, qualifying-game predicate, scoring rule, registered input,
or registration hash.

This classification does **not** rely on §2.3's team-only scoring-key
allowlist; that section governs scoring keys, not row/entity membership.

## Required remediation boundary

Any authorized implementation must pin all of the following:

- classify only the exact measured provider sentinel: missing `player_id`
  **and** exact `player_name == "Team"` (with the measured null-position shape
  covered by contract);
- apply it only to the records passed to the label builder; do not mutate the
  pinned artifact or globally filter the admitted pool used by
  `build_study_matrix` and the registered all-position team aggregation;
- preserve the label builder's existing fail-closed identity guard for every
  other missing, malformed, ambiguous, or one-sided mismatch shape;
- make no change to registered values, the qualifying-game predicate, scoring
  components, cohort rules, source pins, or publication gate;
- add negative contracts for a null-id non-`Team` row and a non-null-id
  `Team` row, plus an end-to-end real-shape contract proving the exact 236
  sentinels are excluded only from labels.

A broader missing-identity drop, a global pool filter, a change to team
aggregation, or any registered-value change would cross this classification
and require amendment review.

## Authority boundary

This is a registration read only. No fix or rerun is authorized here. The
registered execution trigger was consumed by the named fail-closed run; David's
explicit word is required for a bounded implementation round and separately
for any rerun.

H2 QB rushing remains **UNDER TEST with no result**.
