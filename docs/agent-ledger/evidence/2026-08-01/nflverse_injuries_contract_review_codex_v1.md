# nflverse injuries contract — independent review

Date: 2026-08-01  
Reviewer: Codex  
Layer: 1 (source ingestion)  
Verdict: **CHALLENGE / NOT CLEAR**

## What is sound

- Injuries belongs in the existing nflverse adapter/store rather than a second
  source path.
- `gsis_id`, not player name, is the identity key.
- `date_modified` belongs in the declared grain: the two-status revision fixture
  produces two distinct row keys, and removing the timestamp would make the
  existing grain gate refuse the real revision pair.
- The three source states remain distinguishable: designated row, on-report row
  without designation, and absence of a row (no information).
- `season_type` is correctly excluded after the single-season schema correction.
- The opt-in normalizer leaves existing specs unchanged in production code.
- Independent focused census: **55 passed** in 8.91s; Ruff and diff-check clean.

## Blocking findings

### 1. The unresolved-identity export drops every injury player name

`publish_export` builds the review artifact's `player` field from `player` or
`player_display_name` only. Injuries carries `full_name`. A real one-row capture
through `run_usage_capture`, `UsageStore`, and `publish_export` produced:

```text
nflverse_injury_report.full_name = "Source Only Player"
injuries.parquet.full_name       = "Source Only Player"
unresolved_identity.player      = None
```

The implementation lane measured 1,140 `source_only` injury rows in 2024, so this
is not a synthetic-only edge: all those identity-review rows would lose the human
name. Add `row.get("full_name")` to the source-aware fallback and lock the exact
exported value with an injury source-only row.

### 2. The production-bound spec is not exercised

Every normalization assertion uses the unbound `INJURIES` constant. The sole
`build_streams()` test checks only that the name `injuries` appears. Therefore
removing `_bind`'s propagation of `blank_as_null_columns` or `integer_columns`
would leave all 15 new cases green even though the default capture path would ship
the wrong behavior.

Take the bound injuries spec from `build_streams()`, assert its loader is
`load_injuries`, assert both option tuples survived binding, and exercise blank
normalization plus typed export through that bound spec.

### 3. “Stored rows equal source rows” never touches the store

`test_stored_rows_equal_source_rows` calls `normalize_rows` and compares two list
lengths. It performs no `UsageStore.apply_season`, no SQLite query, no Parquet
read, and no manifest reconciliation. It cannot support its name or the claimed
stored-row conservation fact. This gap is exactly why finding 1 survived.

Add one offline end-to-end capture with the bound injury spec that asserts:

- raw envelope row count equals source rows;
- SQLite injury-table count equals source rows;
- both revision rows and normalized nulls survive storage;
- injury Parquet and its manifest row count reconcile;
- unresolved identity retains source id, name, position, and typed status.

### 4. Blank normalization is broader than the locked evidence

The spec opts in **seven** columns, not the eight claimed in the message. Tests
exercise whitespace and a real value for `practice_status` only. Removing any of
the other six columns from the tuple leaves the new suite green. Either narrow the
policy to the measured field or pin the intended seven-column set and
parameterize blank/nonblank behavior across every declared column. Also assert
the four pre-existing bound specs retain an empty tuple.

### 5. The load-bearing revision coordinate has no missing-value policy

Schema drift checks column presence only. A row with `date_modified=None` or blank
is accepted and receives a row key containing that value, although the timestamp
is the field that makes revisions a time series. Register and test an explicit
policy: preferably refuse a missing/blank `date_modified` by name, or explicitly
type and report a timeless observation. Leaving it accidental weakens the grain
contract.

### 6. The schema label and module contract still describe the four-stream system

The change adds a fifth table/export and new normalization semantics while
`SCHEMA_VERSION` remains `nflverse_usage.v2`; old four-stream and new five-stream
manifests are therefore labeled identically. The module header also still says
“Next Gen Stats and snap counts” and “four stream specs.” Bump and lock the schema
version for the five-stream artifact, and update the touched contract prose.

## Reviewer actions

Read-only repository inspection, offline tests, and a temporary-directory capture
probe. No live nflverse call, production data write, scheduler, consumer,
promotion, model work, commit, or push.

