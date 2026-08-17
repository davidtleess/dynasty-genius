# QB-1 registration read — season-summary non-player aggregate wall

Date: 2026-08-16 13:24 ET  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`, revision 103  
Classification: **IMPLEMENTATION, not amendment**

## Evidence read

The revision-103 census is internally fit for this classification. Its script
SHA-256 is
`6b1321cbba0701037b37e470060d8ad4a86265bfae2d48395e0f93969df0f96e`;
its 3,831-line output SHA-256 is
`a8cfb6c6561502fda3e2adffe873f32a3ee03b6c43143e31543d891ab5d5fcd4`.
Code audit confirms one call to `admit_and_load_validation_pool`, a counted
single load per each of 17 admitted paths, shipped identity helpers rather than
replacement semantics, and before/after digests for every admitted frame.

Measured facts:

- `season_summary` has exactly 11 unusable-identity rows in 21,377, one per
  season 2015–2025; first refusal is index 1845.
- All 11 have missing `player_id`, missing `position`, valid study season,
  null `passing_cpoe`, and provider league-total `games` of 256, 271, or 272.
- Their name shapes (`Team`, `R.Rodgers`, then anonymous) recur in the weekly
  provider non-player aggregate rows. They are the same upstream **provider
  non-player aggregate class**, though not the same exact weekly predicate.
- All 11 are content-free in every field the season-summary consumer uses for
  a player feature: no player key, no position, and no CPOE. Their nonzero
  league totals are in fields the registered composition does not consume.
- The other six admitted datasets expose no remaining identity-law refusal.
  This says nothing about non-identity walls and makes no last-wall claim.

## Registration read

This is implementation, not a post-result analytical choice:

- Registration §3 defines the target as `y(p,t)` for player `p`; a row with no
  player identity is not a player-season observation.
- Registration §4 defines the cohort as QBs. The measured rows have no player
  identity or position and instead carry full-league game totals; they cannot
  be cohort members.
- Registration §5 registers H1 `cpoe` as the official REG season-summary value
  at `[t-1]`, consumed as-is for the player's `(player_id, season)` join. The 11
  rows have neither a player key nor a CPOE value, so they cannot supply or
  change any registered feature.
- Registration §5's fail-closed manifest law remains intact: no required
  column is substituted, recomputed, or relaxed. The player-row identity,
  duplicate, and numeric guards remain fail closed.
- Registration §0's anti-forking-path rule is untouched: no cohort, feature,
  target, fold, estimator, inference, threshold, or result-facing value moves.

The earlier shorthand “empty provider placeholder” is retired. These are
provider **non-player league aggregates** with nonzero unconsumed totals. The
lawful exclusion is grounded in entity class and registered consumer scope,
not a claim that the whole row is zero.

## Exact bounded implementation boundary

One private season-summary aggregate classifier in
`study_matrix.py`, plus contracts only:

```text
unusable/missing player_id
AND valid registered study season
AND missing position
AND null passing_cpoe
AND games is an exact validated integer >= 256
```

`player_name` and `player_display_name` are audit evidence only and never
predicate inputs. `games >= 256` is the measured league-aggregate signature
(versus a real player's maximum 21), and prevents an arbitrary empty or corrupt
missing-id row from being silently swallowed.

Apply the classifier only to the defensive copied `season_summary` records,
after F1 admission, F14/F15 shape/manifest gates, and exact season-coverage
validation, immediately before stage-1b identity/duplicate/CPOE validation.
The admitted pool, copied frame, raw artifact, manifests, and every other
dataset remain untouched.

Every near miss stays fail closed at the existing stage-1b law, including:
non-null `passing_cpoe`; present position; invalid or missing season; missing,
non-integral, or `<256` games; or any missing-id row not matching the full
predicate. Rows with a usable player id are never classified, regardless of
their other values. Existing duplicate and CPOE validation remains unchanged.

Required proof in the bounded round:

1. RED-before-GREEN positive and one-field near-miss contracts.
2. Exact real-surface classification 11/11, zero residual unusable identity,
   and first stage-1b refusal removed.
3. Whole-matrix equality with versus without injected exact aggregates; no
   player CPOE, cohort, target, or analytic value changes.
4. Admission/frame digests unchanged and no mutation.
5. Existing scoped contracts, five-file bundle, Ruff, compile, and diff scope.

No registered rerun is part of implementation or proof. David's fresh rerun
authority remains held and fires only after Codex independently CLEARs the
bounded round. The readout then goes to David for his ruling. H2 QB rushing
remains **UNDER TEST with no result**.
