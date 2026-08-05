# Depth charts post-commit review — Codex v1

Date: 2026-08-05
Target: `7654a199ddbf6f2e0b49e5c6ffe4a4a21bfe8692`
Disposition: **NOT CLEAR**

## Positive evidence

- Reviewed the immutable commit in a detached worktree; its focused contract passed **18 tests**.
- Live last-good run `nflverse-usage-20260805T1259254581500000` carries 812,074 depth rows:
  257,859 weekly rows across 2018-2024 plus 554,215 daily rows in 2025.
- Era resolution, union-table persistence, identity accounting, exact-duplicate collapse, collapse
  reconciliation, deterministic replay, and semantic-collision refusal are sound in the reviewed
  fixture paths.
- The corrective coverage fingerprint in `7de9357` closes the transferred stale-collapse-count
  defect.
- No Engine consumer was introduced.

## Blocking findings

### D1 — allowing null `week` disables every grain population check in both eras

`DEPTH_CHARTS` sets `require_populated_grain=False` because weekly `SBBYE` rows legitimately have a
null `week` (`7654a19:src/dynasty_genius/nflverse_usage.py:962-974`). The flag is stream-wide, so it
also permits blank `season`, `game_type`, `club_code`, `gsis_id`, position coordinates, and every
coordinate in the daily grain—even though the commit's measured claim is that all six daily
coordinates are populated.

Reproducer: set `pos_rank=None` on a real daily fixture row. Normalization succeeds and emits:

```text
dt=2025-08-03T10:09:07Z|team=ARI|espn_id=3693166|pos_grp=Base 4-3 D|pos_slot=1|pos_rank=None
```

Required closure: a per-active-era nullable-grain declaration. Weekly may allow only `week`; daily
allows none. Add falsifiers for a blank required weekly coordinate and a blank daily coordinate.

### D2 — numeric ordering coordinates publish as strings

The spec declares only `season` as integer (`7654a19:src/dynasty_genius/nflverse_usage.py:971`).
The source fixtures carry weekly `week` as int/null and daily `pos_rank`/`pos_slot` as ints, but the
live Parquet publishes all three as String:

```text
season=Int64, week=String, pos_rank=String, pos_slot=String
```

This makes ordinary numeric ordering unsafe (`"10"` sorts before `"2"`) and leaves the landed
stream short of a usable typed substrate. Required closure: declare the union-era integer columns
(`season`, `week`, `pos_rank`, `pos_slot`) and add a two-era emitted-Parquet dtype/value-count
reconciliation test. `espn_id`, `pos_grp_id`, and `pos_id` may remain String because that is their
measured source representation.

## Factual correction

The code comment at `7654a19:src/dynasty_genius/nflverse_usage.py:908` says the weekly era is
2020-2024. The live landing and status evidence show the same weekly era in 2018 and 2019 as well;
the actual captured range is 2018-2024. Correct the comment while closing the blockers.

