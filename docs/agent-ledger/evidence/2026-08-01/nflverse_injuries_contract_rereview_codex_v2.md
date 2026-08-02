# nflverse injuries contract — corrected-state re-review

Date: 2026-08-01  
Reviewer: Codex  
Layer: 1 (source ingestion)  
Verdict: **NOT CLEAR — one new regression, one incomplete closure**

## Six-row disposition

Rows 1, 2, 4, and 5 are closed:

- Injury `full_name` now reaches the unresolved-identity export, and the new
  end-to-end test fails if the fallback is removed.
- The production-bound injuries spec carries loader/options/grain, and bound
  legacy specs retain empty opt-ins.
- The seven-column blank policy is exactly pinned and every declared column's
  whitespace path is exercised.
- Missing/blank `date_modified` now refuses by typed
  `nflverse_blank_grain`; revision rows remain distinct.

Row 3's core is closed: the new offline capture reaches SQLite and Parquet,
preserves both revisions and the normalized null, and retains the source-only
name. Row 6's code change is present (`v3` and module prose), but the version is
not locked by an assertion.

Independent focused census: **69 passed** in 8.42s. Ruff and diff-check are clean.

## Remaining blockers

### 1. `--summary` now mutates an existing four-stream database

The public script promises “`--summary` is read-only, full stop.” Its summary
path calls `UsageStore(db_path, build_streams())`. `build_streams()` now returns
five specs, and `UsageStore.__init__` executes `CREATE TABLE IF NOT EXISTS` for
each spec. Therefore the first summary against the existing four-stream store
creates `nflverse_injury_report` even though no capture was requested.

Reproduced in a temporary database initialized with the four pre-injury specs:

```text
before sha256 037e9f4a601d7bf94571a28782f75dd5c2383b3b994828591331eda9d7a4b7a5
after  sha256 b8687d5cfba8b8d083fc92433808bee7fd913f2fdf4880d51822ed99f2fd6d86
bytes_changed = True
tables_before = nflverse_capture + four data tables
tables_after  = tables_before + nflverse_injury_report
```

This is a state-changing regression caused by registering the fifth stream. Make
the summary path genuinely read-only (for example, URI `mode=ro` plus inspection
of only tables that already exist), and add a subprocess-level test that hashes a
four-stream database before/after `--summary`, asserts byte identity, and asserts
the injuries table was not created.

The script's header/help text also still says “Next Gen Stats + snap counts” and
“Two streams,” although its default capture now runs the injury report too.

### 2. `nflverse_usage.v3` is changed but not locked

No new injury test imports `SCHEMA_VERSION`, asserts `nflverse_usage.v3`, or reads
that label from the raw/status/export artifacts. Reverting the constant to v2
leaves the 69-test slice green, so original row 6's “bump and lock” requirement is
only half closed.

Extend the end-to-end injury test to assert the exact v3 label in the returned
status, raw envelope, and export/ready manifest. That also supplies the raw and
manifest reconciliation checks requested in the first review without another
test harness.

## Reviewer actions

Read-only repository inspection, offline tests, and a temporary four-stream DB
summary probe. No live nflverse call, production database write, scheduler,
consumer, promotion, model work, commit, or push.

