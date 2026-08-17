# QB-1 team-aggregate implementation — Round 13 open receipt

Date: 2026-08-16 09:18 EDT
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`

## Authority

David, verbatim:

> grant both - open one bounded round per your sanctioned mechanism: claude
> implements the team-aggregate exclusion exactly per your pinned boundary
> (build_label_table records only, null player_id + player_name "Team",
> fail-closed preserved, no input mutation), and on your explicit clear the
> study reruns - the registered readout then comes to me for my ruling

This grants two separately controlled actions: one bounded implementation
round now, and one registered rerun only after Codex's explicit CLEAR.

## Pre-open verification

- Run revision `76`, phase/terminal state `blocked/BLOCKED`.
- Round 12 closed with reviewer verdict `CLEAR` and close snapshot
  `95b511a6c16292f417f8eadc7b34762dd11b10e7c13f0ec1356efafaea5c3148`.
- Failed atomic artifact remained byte-pinned at
  `fb222a60957e2ae4a353ed730ff5ddccdfac5cb9bbc803cdc2cefe6c62306244`.
- Registration-read evidence remained byte-pinned at
  `cb64ddf51e0e662dd776c6fd8cfd09a0a2aff67be1f90ab3f1c82928c2324425`.
- Opening runner pin:
  `7c8893cac0d91810b84cde3aa2f94425cb75ff9f1ac2ed6c4e8e62b48a12a297`.
- Opening contract pin:
  `88a39cb88a7c5e1eb3a07b7e1dee80634bf27b8238f1aac702218e1ab160d5af`.
- Exactly twelve green-review rounds were closed and no unresolved review
  BLOCKER remained. The current terminal was the first real-surface label
  refusal, not an open publication-gate finding.

## Transition

Revision-guarded transition script:
`qb1_team_aggregate_round13_open_codex_v1.mjs`.

The script passed strict syntax checking and a non-mutating dry run at
revision 76. It then wrote once through `persistRun`, producing revision
**77**, ACTIVE `green-review`, Round **13** open.

The independently recomputed scoped open-snapshot hash is:

`aba351da7093f7cdb2768b57ba3d7c00779f6a33d784e534ea357a00212f4a00`

The snapshot contains exactly:

- `scripts/run_qb1_study.py`
- `tests/contract/test_qb1_green_correction_contracts.py`

## Bounded implementation and review contract

- The exclusion applies only to records passed to `build_label_table`.
- The exclusion predicate is exactly missing `player_id` AND exact
  `player_name == "Team"`; the measured null-position shape is covered by
  contract but position is not added to the predicate.
- The admitted `pool` remains intact for `build_study_matrix` and the §5
  all-position, pre-QB-filter team rushing-TD aggregation.
- The frozen input artifact is not mutated.
- Every other missing, malformed, ambiguous, or one-sided identity remains
  fail-closed, including null-id non-`Team` and non-null-id `Team` near misses.
- No registration, source pin, publication gate, scoring, cohort,
  qualifying-game predicate, provider, commit, or push change is in scope.
- Claude routes stable pins and evidence to Codex. Codex independently
  reviews exact scope, mutation-resistant near-miss contracts, real-pool
  label composition, input immutability, and preservation of the full pool at
  `build_study_matrix`.
- The study does not rerun before Codex's explicit CLEAR. On CLEAR, David's
  rerun authority is satisfied; the registered terminal readout returns to
  David for his separate ruling.

H2 QB rushing remains **UNDER TEST** throughout; a successful rerun is not
David's ruling and does not lift that status by itself.
