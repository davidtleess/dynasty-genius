# QB-1 GREEN Round 13 review — NOT CLEAR

Date: 2026-08-16 09:36 EDT
Reviewer: Codex
Verdict: **NOT CLEAR**

## Submitted/observed scope

Round 13 opened at revision 77 with exactly two snapshotted files:

- `scripts/run_qb1_study.py`
- `tests/contract/test_qb1_green_correction_contracts.py`

The implementation diff is confined to those two files. It adds the exact
authorized missing-id + exact-name classifier at the copied label-record seam
and three fixture contracts. The original admitted `pool` still flows to
`build_study_matrix`; the frozen input is not mutated. No registration,
publication-gate, provider, source-pin, commit, push, or registered rerun
occurred.

Focused correction contracts independently pass **133/133**; the five-file
comparable bundle passes **688/688**; Ruff and strict compilation are clean.
This green is not sufficient because the required real-surface invariant is
false.

## BLOCKER R13-G1-LABEL-PLACEHOLDER-PREDICATE-INCOMPLETE

The exact authorized predicate excludes only **10 of 192** REG missing-id
rows in the pinned weekly input. It leaves **182** missing identities in the
records passed to `build_label_table`, so the same named
`label_row_invalid` refusal remains. The fixture positive path uses only two
synthetic `player_name="Team"` rows and therefore cannot detect the real
shape mismatch.

Independent measurements:

- full shape census: 181 fully anonymous, 10 exact `Team`, 1 `R.Rodgers`;
- full 17-column D2 census: 192/192 exact zero, no missing cells and no
  nonzero rows;
- current helper over the pinned REG records: 10 excluded, 182 residual
  missing ids, with the source frame remaining 199,868 rows;
- Claude's full composition probe fails again at the label stage, row 5967,
  season 2015 week 6; no report was published and its returned composition
  was not consumed.

The original “236 exact Team aggregates” premise was a subset-to-whole
measurement error. The rows are label-neutral provider placeholders, not
team aggregates; their production is zero rather than a same-team/week sum.

## Corrected registration read and smallest next action

`qb1_label_placeholder_registration_read_codex_v2.md` classifies a revised
predicate as registration **implementation**, not amendment:

`missing player_id AND missing position AND exact validated zero in all 17 D2 scoring/predicate inputs`

This follows §3's player target and qualifying predicate, §2.1's complete
scoring inputs, §4's QB cohort, and §5's requirement to preserve the full
pool for team aggregation. It excludes only rows that cannot instantiate a
player/QB and are provably neutral to both label points and games. Any
unproven limb remains fail-closed.

That revised predicate is not authorized by the current explicit name-based
word. The smallest resume action is a fresh David word opening one bounded
round under the v2 predicate and contract matrix. Only a subsequent Codex
CLEAR can satisfy the already-granted rerun trigger.

## Verdict

**NOT CLEAR.** Record one BLOCKER, close Round 13, record the failed review,
and re-park without rerunning the registered study. H2 QB rushing remains
**UNDER TEST with no result**.
