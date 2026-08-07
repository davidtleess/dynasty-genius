# PR #157 post-merge audit and A-C open-clocks review

**Reviewer:** Codex, independent reviewing lane  
**Layer:** Layer 1 ingestion inventory  
**Date:** 2026-08-06 ET

## 1. PR #157 post-merge audit — CLEAR

Freshly fetched and independently verified:

- local `HEAD` and `origin/main` are both
  `fc89db69c78fa2ef76817cb2d95abd0e958b0e20`, with ahead/behind `0/0`;
- PR #157 is `MERGED`, with head
  `3ab84edae81d08f2db5162331e18122e8838c635`, merge commit `fc89db69...`, and merged time
  `2026-08-07T03:30:42Z`;
- PR-head CI run `31144378681` and merged-main CI run `31144571634` are both terminal
  `completed/success`, with Python and Frontend checks successful;
- the three CH1 blobs on `origin/main` match the GREEN CLEAR pins exactly:
  `ce9caf74...`, `019229c2...`, and `a14261e5...`;
- the parked wire paths remain byte-identical at `b3247ec8...` and `fd924eb1...`; and
- the isolated merge worktree is absent.

The ledger-union conflict resolution was docs-only and did not alter the CLEARed CH1 content.

## 2. A-C open-clocks artifact — NOT CLEAR

Artifact reviewed in full:
`docs/agent-ledger/evidence/2026-08-06/ac_open_clocks_measurement_claude_v1.md`.

The principal conclusions are directionally correct:

- held PlayerProfiler data cannot establish a source-publication cadence;
- the 22 N18 snapshots support a bounded, off-season normalized-change profile for the overlapping
  Sleeper families, not a source-publish cadence;
- the reported Sleeper section-change counts reproduce; and
- neither clock is closed and no A-C checkbox should move.

Three corrections are required before the artifact is adopted into the catalog.

### C1 — PlayerProfiler has one held vintage per stream, not one proved ingest session

Lines 22–27 call the entire store one ingest session and describe the three `pp_capture` timestamps
as phases of it. The durable markers instead show four separate manual ingest runs on 2026-08-01:

- base/player capture: `03:47:21Z`;
- weekly roster: `04:19:20Z`;
- advanced gamelog: `04:37:53Z`; and
- advanced PBP: `13:36:26Z`.

The valid inference is narrower and sufficient: each canonical PlayerProfiler stream has only one
held captured vintage, so no same-stream time series exists from which to infer provider cadence.
The four runs need not be collapsed into one session to reach that conclusion.

### C2 — `0.00` is not an upper bound on stability

Lines 68–72 correctly say normalization can hide raw endpoint changes, but the final sentence uses
the wrong quantity. Each table `0.00` is an observed **normalized change rate**, not a stability
rate. It therefore cannot itself be an upper bound on stability.

Correct formulation: a normalized change proves at least one relevant input changed; normalized
no-change does not prove raw endpoint stability. Equivalently, the observed normalized change rate
is a lower bound on changes detectable in the raw inputs, subject to the documented transformation;
the raw stability rate is not established by these snapshots.

### C3 — clarify the last-interval player symmetric difference grain

Line 58's `36 rows only in the earlier snapshot, 38 only in the later` is a full-row set symmetric
difference, not a player-identity difference. Keying by `sleeper_player_id` gives:

- 0 player IDs removed;
- 2 player IDs added; and
- 36 shared player IDs whose normalized rows changed.

The stated 36/38 counts are mathematically consistent, but without the grain they can be read as
36 removals and 38 additions. State the keyed decomposition or label the values explicitly as
full-row set differences.

## 3. Reproducing checks

- Queried `pp_capture` and `pp_pbp_capture` by stream and distinct `ingested_at`.
- Read all four PlayerProfiler `*_status_latest.json` markers.
- Recomputed every Sleeper section-change count across the 22 snapshots.
- Compared ordered-list hashes with order-insensitive row multisets; `players` still changes 21/21
  and `rosters` 9/21, so those rates are not list-order artifacts.
- Recomputed the last player interval keyed by `sleeper_player_id`.
- Confirmed `league` changes only at `settings.daily_waivers_last_ran`.

**Verdict:** PR #157 post-merge audit CLEAR. Open-clocks evidence NOT CLEAR pending C1–C3. No
catalog edit or checkbox movement is warranted yet.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
