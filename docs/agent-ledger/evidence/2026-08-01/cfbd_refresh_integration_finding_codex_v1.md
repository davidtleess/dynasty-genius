# CFBD refresh integration finding — Codex v1

## Scope

Layer 1–2 read-only reconciliation of the already-landed CFBD foundation wrapper, its July 31
isolated run, the protected legacy cache/input, and the active Engine A read paths. No API call,
refresh, model change, or source artifact mutation was performed.

## What the repository proves

1. A live isolated run already exists despite the current board saying the runner was unexecuted.
   `app/data/sources/cfbd_foundation/manifest_latest.json` records run
   `20260731T165930158823Z`, 572 raw JSON files, 874 curated rows, and identity coverage 1.0.
   `status_latest.json` calls that run `ok`.
2. The isolated curated output is not byte- or value-equivalent to the active input. Comparing by
   `(gsis_id, position)` gives identical 874-row key sets and 173-column schemas, but 251 cell
   differences across 44 QB rows. Every difference is in the four QB feature families or their
   missing/source siblings; WR/RB/TE fields are unchanged.
3. The QB raw cache is not player-specific in practice. In the protected legacy cache, all seven
   2014 QB files are byte-identical, all fifteen 2015 files are byte-identical, ten of ten 2020
   files are byte-identical, and the largest identical-payload group is 5–14 players in every
   season checked. The isolated run reproduces the same class: largest identical-payload groups
   are 5–14 players per season.
4. Concrete impossible examples exist in the active input. The cached 2016 normalized payload for
   Patrick Mahomes, Deshaun Watson, Mitchell Trubisky, DeShone Kizer, C.J. Beathard, Joshua Dobbs,
   Nathan Peterman, and other distinct players repeats the same statistics. The active curated
   values include `completion_pct=0.00594`, `yards_per_attempt=6.2`, and
   `td_int_ratio=1.090909...`; a 0.594% completion rate is outside the adapter test's own intended
   0–1 fraction contract for a real qualifying QB.
5. The July 31 isolated refresh arbitrarily moves the repeated payload among players. For example,
   Davis Webb changes from missing to that repeated 2016 payload while Mahomes, Watson, Trubisky,
   Kizer, Beathard, Dobbs, and Peterman change from the repeated payload to missing. This is not a
   trustworthy source refresh.
6. The current wrapper can still label this `ok`. `_validate_curated` checks nonzero rows,
   `w2b_cfbd_degraded == 0`, identity coverage, and at least one populated CFBD source column. It
   has no player-response identity check, cross-player collision check, per-feature semantic range
   check, or regression/retention gate.
7. The active Engine A training/bake-off scripts still read
   `app/data/training/prospects_with_outcomes_v3.csv`; nothing reads the isolated curated path.
   Re-running the wrapper therefore cannot, by itself, move Engine A off the May-era input.
8. **Blast-radius correction (15:57 ET):** that read-path fact does not mean a model consumed the
   defective values. In the only Phase 20 artifact, `39.5` is coverage percentage, not feature
   importance. All four CFBD QB fields are in `dropped_features`; the ridge and GBT candidates were
   skipped because enriched features equaled baseline; `passing_candidates` is empty; and the
   artifact records `model_pkl_changed=false` and `latest_json_changed=false`. The promoted QB
   model predates the bakeoff and its model card points to Engine B data. The proven blast radius is
   the ingest/cache/training-CSV layer and a latent future-candidate risk—not a fitted or promoted
   model.

## Root-cause status

The defect is established at the adapter/curation boundary, not at the model or UI layer. The
installed CFBD OpenAPI client (spec version 5.13.2) proves that `/stats/player/season` accepts
`year`, `conference`, `team`, week/season-type, and `category` filters, but **not** `playerName` or
player ID. The adapter nevertheless sends `playerName`, then selects the first matching stat-type
record without proving that the returned `playerId`, player name, and team belong to the requested
player. The stored repeated per-year payloads are the resulting observed failure mode. The same
contract review shows that `/ppa/players/season` supports `playerId`, while
`/wepa/players/passing` supports year/team/conference/position and returns athlete identity for
local filtering. The current adapter uses unsupported `playerName` parameters for all three
families and discards the available response identity.

The historical raw HTTP responses were not retained, so this evidence does not claim a server
implementation detail beyond the public client contract. It proves the actionable defect: the
adapter asks endpoints to perform unsupported identity filtering, performs no exact response-side
identity check, and treats the first record as the requested player.

## Disposition

- Do not run another paid full refresh yet; it would spend calls through the same untrusted QB path.
- Do not copy or wire the isolated curated CSV into the active Engine A input.
- The next contract must resolve one exact player identity before feature extraction; use only
  endpoint-supported filters; match stats/PPA/WEPA rows by the resolved identity (or refuse the
  ambiguous/missing result); distinguish request failure from a legitimate empty result; retain
  identity proof in the normalized raw cache; audit suspicious cross-player same-season payload
  collisions; validate semantic ranges; and prevent `ok` publication when a qualifying feature
  family regresses without an explicit reviewed basis.
- This finding does not authorize a model-feature change or any conclusion about QB rushing. The
  registered QB rushing hypothesis remains **UNDER TEST** and is not used here.
- No model remediation is indicated by the current evidence because the defective CFBD features
  were dropped before the Phase 20 fit and no model artifact changed. Re-evaluate that conclusion
  only if a different consumer artifact is identified.
