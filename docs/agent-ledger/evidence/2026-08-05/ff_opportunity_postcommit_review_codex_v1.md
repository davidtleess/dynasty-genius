# ff_opportunity post-commit review — Codex v1

Date: 2026-08-05  
Target: `da00235463351065bd2eec346abb86476c7f3f0c`  
Disposition: **NOT CLEAR**

## Scope and checks

- Reviewed `git show da00235` from an immutable detached worktree.
- Focused committed contracts: **73 passed** (`test_ff_opportunity_ingestion_red.py` plus the
  edited `test_nflverse_injuries_red.py`).
- Live last-good artifact anchored to run `nflverse-usage-20260805T0326292827190000`:
  44,137 rows, seasons 2018-2025, zero blank player ids, zero duplicate declared grains,
  44,061 `canonical_resolved`, 76 `source_only`, typed Int64 season/week and Float64 metrics.
- The existing-contract edit is accepted: replacing the proxy “everything except injuries” with
  the four named pre-injury streams matches the test's documented scope and also fails if one of
  those four registrations disappears.

## Blocking findings

### F1 — excluded rows bypass the exact source-shape contract

At `da00235:src/dynasty_genius/nflverse_usage.py:812-824`, rows with blank identity are removed
before era selection and the per-record exact-schema check. An additive or missing provider column
confined to a residual row is therefore accepted and dropped. Reproducer: one valid player row plus
one residual carrying `provider_new_field="drift"` returned one accepted row and one excluded row;
no `UsageCaptureError` was raised. The committed additive-column test mutates every row, so it
cannot see this branch.

Required closure: validate the shape of every source record before exclusion, and add a falsifier
whose drift exists only on an excluded row (additive and missing cases).

### F2 — the exclusion predicate does not enforce the premise that makes exclusion safe

The implementation excludes every blank-`player_id` row, but the factual justification is narrower:
the measured residual class has no player/name and zero realized production. A synthetic residual
with `total_fantasy_points=10.0` and `full_name="Unidentified Producer"` was accepted and excluded.
Counting that row is not equivalent to retaining its production.

Required closure: declare and enforce the FF-specific eligibility invariant for exclusion (at
minimum no player/name signal and zero/null realized-production fields), and refuse by name if a
blank-id row violates it. Add a falsifier that mutates a residual to carry realized production and
another that gives it a player name.

### F3 — durable coverage becomes stale when only the excluded class changes

`UsageStore.apply_season()` hashes only normalized stored rows plus the projection
(`da00235:src/dynasty_genius/nflverse_usage.py:1241-1253`). Coverage is persisted only on the write
path (`:1266-1279`). Two captures with the same player row and one then two residual rows produced:

```text
second_applied=unchanged
latest_status rows_excluded_unidentified=2
SQLite nflverse_capture.coverage_json rows_excluded_unidentified=1
```

This mechanism broke the prior equivalence “same stored rows means same coverage.” Required
closure: make the opted-in excluded count part of the content identity (or otherwise update durable
coverage without misrepresenting row idempotence), with a two-capture regression.

## Boundary

The 44,137-row artifact is real and usable, and no Engine consumer was added. These findings do not
call for deleting it or rewriting the already-disclosed commit. Close them in a corrective commit,
rerun the focused tests and live reconciliation, then request a fresh post-commit review.
