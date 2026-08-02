# nflverse injuries contract — independent CLEAR

Date: 2026-08-01  
Reviewer: Codex  
Layer: 1 (source ingestion)  
Verdict: **CLEAR**

## Enumerated checks

1. **Architecture and identity:** injuries is the fifth spec in the existing
   nflverse adapter/store; it keys on `gsis_id`, preserves source-only identity,
   and retains `full_name` in the unresolved-identity review artifact.
2. **Revision semantics:** `date_modified` is in the bound grain; both real-shaped
   revision rows survive normalization, SQLite, and Parquet. Missing/blank grain
   coordinates refuse through typed `nflverse_blank_grain`.
3. **Three-state semantics:** designated, on-report without designation, and no
   source row remain distinct. No healthy row is synthesized.
4. **Blank normalization:** the exact seven-column policy is pinned; every
   declared column's whitespace path normalizes to null; all four pre-existing
   bound specs retain empty opt-ins.
5. **Bound-spec integrity:** loader, integer typing, grain, blank policy, and
   populated-grain requirement survive `_bind`; the production-bound spec drives
   the integration test.
6. **Source-to-artifact conservation:** an offline real capture path reaches raw
   envelope, SQLite, injury Parquet, ready marker, manifest, and unresolved
   identity. Row count, both revisions, normalized null, and human-review name
   survive.
7. **Read-only summary:** the public CLI now uses SQLite URI `mode=ro` and never
   constructs `UsageStore`. Against a four-stream temp DB, the independently
   recomputed SHA remains
   `037e9f4a601d7bf94571a28782f75dd5c2383b3b994828591331eda9d7a4b7a5`
   before and after; the table set remains five total tables and no injury table
   is created. A missing fifth table is reported as `absent`.
8. **Version contract:** exact `nflverse_usage.v3` is asserted in the constant,
   returned status, status marker, raw envelope, ready marker, and run manifest.
   Script/module help now describe all five streams.

## Independent verification

- Two-file focused slice: **70 passed**.
- Full `-k nflverse` selection: **70 passed, 4,190 deselected** in 20.60s.
- Ruff on `src`, `app`, the capture script, and injuries test: clean.
- Reviewed-file `git diff --check`: clean.

The earlier 71 count was corrected by the implementation lane before final
delivery; 30 injury cases plus 40 existing cases reconciles exactly to 70.

## Boundary

This clears the offline contract and implementation state. It does not claim a
real injury capture has been stored and does not authorize a scheduler, consumer,
promotion, model use, commit, or push.

Reviewer performed read-only repository inspection, offline tests, and temporary
database probes only. No live nflverse call or production database write.

