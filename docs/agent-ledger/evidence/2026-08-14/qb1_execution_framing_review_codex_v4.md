# QB-1 execution framing v4 — independent round-4 review (Codex v4)

Date: 2026-08-14  
Work item: `TW14-QB1-1`  
Reviewed artifact: `qb1_execution_framing_claude_v4.md`  
Reviewed SHA-256: `c96ada669575306653f181139bb9bf05685d125a0f53a9d3c4abe502e45546ae`  
Verdict: **NOT CLEAR — one BLOCKER**

No provider call or study execution was performed. QB rushing production (H2)
remains **UNDER TEST** with no result.

## Checks

1. Reproduced the v4 hash exactly.
2. Verified the dataset vocabulary now matches `VALIDATION_DATASETS` in spec
   order: weekly, season summary, players, rosters, ff-playerids, draft picks,
   and play-by-play.
3. Verified the F32 consequence, no-tuning rule, and advisory/binding-execution
   distinction remain intact.
4. Verified the model-lane wording is corrected: F32-unaffected, power unknown
   until the registered fold/n guards run.
5. Verified the backup path is exact and the semantic-vs-structured round
   undercount is now explicitly disclosed.
6. Compared the table's claimed “nflreadpy call scope” with the installed
   function signatures and the shipped adapter's fetch-before-parse behavior.

## Finding

### QB-R4-B1 — BLOCKER — the authorization packet still does not describe one deterministic provider operation

The seven names are now correct, but the “call scope” column mixes provider
calls with downstream consumption and leaves the provider count undecided:

- `players` is not “cross-check only.” `load_players()` supplies
  `birth_date`, which directly produces the registered H4
  `age_at_season_start` feature; only its draft fields are cross-check-only.
- `load_rosters(2015..2025)` fetches the seasonal roster frames; REG-only is a
  downstream cohort-consumption rule, not a provider-call filter.
- the shipped adapter calls `load_draft_picks()` with no season argument and
  snapshots that full provider frame before filtering admitted rows to
  1980–2025. “Coverage 1980–2025” is therefore the parse/admission scope, not
  the actual fetch scope.
- the `ff_playerids` row asks David to authorize seven provider fetches while
  deferring to RED whether only six will occur and a transformed local JSON
  will be re-enveloped instead. The earlier 0/7 finding established that file
  is not presently an admitted D1 raw snapshot; silently manufacturing new
  raw-snapshot/timestamp/parser metadata later would reopen the barred
  legacy-substitution route.

**Required v5 correction:** make the gate deterministic before David answers.
Either:

1. ask for the seven literal provider calls implemented today and remove the
   local-reuse option; or
2. first present a separately reviewed, provenance-preserving local
   `ff_playerids` admission contract, then ask David for exactly six provider
   calls plus that named local reuse.

For either option, distinguish **provider fetch scope**, **raw snapshot
contents**, and **post-parse/admission scope** in the table. The literal current
seven-call shape is:

- `load_player_stats(2015..2025, summary_level="week")`, then REG parse;
- `load_player_stats(2015..2025, summary_level="reg")`;
- `load_players()` full frame, used for H4 age plus draft cross-checks;
- `load_rosters(2015..2025)` full returned frames, REG rows consumed later;
- `load_ff_playerids()` full frame;
- `load_draft_picks()` full returned frame, then 1980–2025 admission filter;
- `load_pbp(2015..2025)` full returned frames, then REG parse.

This remains BLOCKER severity because the artifact is the exact external-action
packet defining what David's yes would authorize. A maximum authorization with
a later agent-selected six/seven split is not the promised exact scope.

## Gate posture

Framing remains open for semantic round 5. No RED, fetch, local re-enveloping,
data copy, study execution, result, config mutation, commit, or push is
authorized by this review.

