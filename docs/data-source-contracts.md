# Dynasty Genius — Data Source Contracts

Adapter interface, identity resolution rules, snapshot layout, per-source schemas, and failure-mode policy.

- Strategy layer: [system-design.md](system-design.md)
- Storage substrate (Delta Lake / Unity Catalog / MLflow): [storage-strategy.md](storage-strategy.md)
- Implementation playbook: [agent-execution-plan.md](agent-execution-plan.md)
- Phase advancement criteria: [validation-gates.md](validation-gates.md)

This doc is the contract between the source adapter layer and everything above it. Agents do not change adapter shapes without updating this doc.

## Storage Substrate

Adapter writes target the medallion layers defined in [storage-strategy.md](storage-strategy.md):

- `fetch_automated()` and `ingest_manual_export()` write the raw bytes to the appropriate bronze table under the `gen_alpha.bronze` schema (e.g., `bronze.sleeper_rosters_raw`, `bronze.pff_grades_raw`). Local file caches under `app/data/cache/raw/` continue to exist as a dev-time and offline fallback through Migration Phase M.4.
- `parse()` writes normalized rows to the appropriate silver table under `gen_alpha.silver` (e.g., `silver.player_seasons`, `silver.usage_metrics`).
- Adapters never write to gold. Gold is the output layer for the engines and the API.

The interface below stays unchanged across the local-file → Lakehouse migration. Code reads `DYNASTY_GENIUS_SUBSTRATE` (`local | bronze`) to select the write path; downstream consumers cannot tell which path was taken.

## Adapter Interface

Every source has exactly one adapter at `app/data/<source>.py`. Every adapter implements the same interface.

```python
class SourceAdapter(Protocol):
    source_name: str            # e.g. "sleeper", "nfl_data_py", "pff", "playerprofiler", "ras", "ktc"
    schema_version: str         # bumps when output columns change
    parser_version: str         # bumps when parse logic changes (even if columns unchanged)

    def fetch_automated(self, *, season: int, **kwargs) -> RawSnapshot:
        """Pull from the live source. Writes a raw snapshot. Returns a handle."""

    def ingest_manual_export(self, path: Path, *, season: int, **kwargs) -> RawSnapshot:
        """Ingest a user-provided export (CSV, XLSX, HTML dump). Same shape as fetch_automated."""

    def parse(self, snapshot: RawSnapshot) -> NormalizedRows:
        """Parse a raw snapshot into normalized, source-tagged rows. Pure function."""

    def freshness(self, season: int) -> FreshnessReport:
        """Most recent snapshot timestamp, age, completeness, and stale/missing flags."""
```

Both `fetch_automated` and `ingest_manual_export` return the same `RawSnapshot` shape. Both run through the same `parse`. The downstream system cannot tell which path was taken.

Cross-cutting requirements:

- `parse` is pure — given the same snapshot bytes, it returns the same normalized rows.
- Every normalized row carries `source_name`, `source_timestamp`, `parser_version`, and `completeness_flags`.
- Adapters never call other adapters. They never read from or write to the feature store. They only produce normalized rows.
- Adapters never perform identity resolution. They emit source-native IDs only. The identity layer maps them.

## Raw Snapshot Layout

Snapshots are immutable. They are the audit trail.

### Target layout (Lakehouse mode, post Migration Phase M.1)

Each source has one append-only bronze table:

```
gen_alpha.bronze.<source_name>_raw
    columns:
        bronze_partition_id  string         # composite of source_name + season + fetched_at
        source_name          string
        season               int
        fetched_at           timestamp
        fetch_method         string         # automated | manual_export | replayed_fixture
        source_url           string         # url for automated, filename for manual_export
        schema_version       string
        parser_version       string
        snapshot_bytes       binary         # raw bytes (HTML, JSON, CSV, XLSX)
        snapshot_format      string         # mime hint
```

A pointer manifest is written to `gen_alpha.gold.snapshot_manifests` so a decision card can name the exact bronze partition it consumed without reading the bronze table itself.

### Transitional layout (local-file mode, current)

Until Migration Phase M.4 retires the local fallback, every adapter also writes to:

```
app/data/cache/raw/<source_name>/<season>/<YYYYMMDDTHHMMSSZ>/
    snapshot.<ext>            # the raw bytes (HTML, JSON, CSV, XLSX)
    manifest.json             # source_name, season, fetched_at, fetch_method, url or filename, schema_version, parser_version
```

`fetch_method` is `automated`, `manual_export`, or `replayed_fixture` in both modes. The `app/data/cache/raw/` tree is gitignored. Tests use `tests/fixtures/<source_name>/` checked into the repo, replayed via the same adapter. Do **not** introduce a root-level `data/` directory — all runtime caches live under `app/data/cache/`.

A snapshot is never deleted in-place. Pruning is a separate, audited operation. In Lakehouse mode, "pruning" is a Delta `VACUUM` on a frozen partition with explicit retention policy; in local mode, it is a manual `app/data/cache/raw/` cleanup script that logs what it removed.

## Normalized Row Schema (common columns)

Every adapter emits rows with these columns, plus source-specific columns:

| Column | Type | Notes |
| --- | --- | --- |
| `source_name` | string | Mirrors `SourceAdapter.source_name`. |
| `source_player_id` | string | Source-native ID. Sleeper `player_id`, gsis_id, PFR slug, PFF id, PlayerProfiler id, KTC slug, etc. |
| `source_player_name` | string | Source-native display name. Used by identity layer fuzzy match if needed. |
| `position` | enum | `QB`, `RB`, `WR`, `TE`. Other positions are filtered out at the identity layer, not here. |
| `season` | int | NFL season the row pertains to. |
| `source_timestamp` | timestamp | When the snapshot was produced. |
| `parser_version` | string | Parser version that produced this row. |
| `schema_version` | string | Adapter schema version. |
| `completeness_flags` | list[string] | e.g. `["pff_grade_missing", "rookie_year_partial"]`. |

Source-specific columns are namespaced with the source name when they could collide (e.g. `pff_yprr`, `playerprofiler_dominator`).

## Identity Resolution

Every feature row consumed downstream must carry a canonical `player_id`. The identity layer is the only place this mapping happens.

### Canonical mapping table

In Lakehouse mode, the canonical mapping lives at `gen_alpha.silver.identity_canonical_mapping`, written via `app/data/identity/mapping.py`. In local-file mode (current, through Migration Phase M.2), the same table is materialized as `app/data/identity/canonical_mapping.csv`. The schema is identical:

| Column | Notes |
| --- | --- |
| `player_id` | Canonical internal ID. UUID or stable slug. Owned by Dynasty Genius. |
| `full_name`, `position`, `birthdate`, `college`, `draft_year`, `draft_pick` | Identity attributes used for matching. |
| `sleeper_id`, `gsis_id`, `pfr_slug`, `pff_id`, `playerprofiler_id`, `ras_id`, `ktc_slug` | One column per source. Nullable. |
| `last_reviewed`, `confidence` | Audit fields. `confidence` is `high` (deterministic match) or `manual` (David approved). |

### Resolution rules

1. **Deterministic first.** If a source row has a known source ID and the mapping table has that ID, resolve immediately and stamp `player_id`. No fuzzy logic runs.
2. **Fuzzy only in staging.** If no deterministic match exists, the row is written to `app/data/identity/staging_unresolved.csv` with the source-native fields and a candidate-match list (top 3 by similarity over `full_name + position + draft_year + college`). Fuzzy logic never writes to production directly.
3. **Promotion is explicit.** A staged row is promoted to production only via `scripts/identity/promote.py`, which requires either (a) David's approval recorded in a promotion log or (b) a deterministic confidence rule (e.g., exact name + position + birthdate). Promotions append to `canonical_mapping.csv` with `confidence=manual` and bump a version field.
4. **Unresolved is rejected, not silent.** Feature rows whose source ID cannot be resolved are dropped from the feature store and written to `app/data/identity/triage/<source>_<season>.csv` for review. They never silently appear with a guessed `player_id`.
5. **Cross-source consistency check.** A nightly job verifies that no two source IDs from the same source resolve to the same `player_id`, and that no `player_id` has conflicting birthdates / colleges across sources. Conflicts produce a triage report.

## Failure Modes

Every adapter declares its failure modes and how each degrades. Silent substitution is forbidden.

| Failure | Adapter behavior | Downstream effect |
| --- | --- | --- |
| Live source unreachable | Return last-known snapshot with `is_stale=True` and `staleness_age_hours`. | Decision cards include `caveats: ["<source>_stale_<N>h"]`. |
| Live source returns 4xx (auth / blocked) | Raise `SourceAuthError`. Do not fall back to scraping a different page. | Affected feature columns become `null`; `inputs_missing` lists them. |
| Live source schema changed (parser fails) | Raise `ParserSchemaDrift`. Pin the snapshot for review. | All downstream rows for that source × season are excluded from the feature store until the parser is re-versioned. |
| Manual export missing required column | Raise `ManualExportSchemaError` with the missing columns list. | Ingestion aborts. No partial rows. |
| Identity unresolved | Source row written to triage. | Player is not scored that cycle. Decision cards for that player report `model_grade: unvalidated` if no prior score exists. |

## Per-Source Contracts

### Sleeper API

- Adapter: `app/data/sleeper.py`
- Path: free public API, no auth required.
- Authority: league state, rosters, player universe, draft picks where exposed.
- Refresh: hourly during the season, daily out of season.
- Manual export path: not applicable (free public API; if Sleeper goes down we wait).
- Source ID: Sleeper `player_id`.
- Required normalized columns: `season`, `source_player_id`, `position`, `team`, `roster_id`, `is_active`.
- Failure modes: Sleeper outage → `is_stale=True`. League not found → `RosterConfigError` (already implemented).

### nfl_data_py / Pro Football Reference

- Adapter: `app/data/nfl_data_py_adapter.py`
- Path: `nfl_data_py` Python package; PFR scraping for fields not exposed there.
- Authority: NFL draft capital, historical stats, active-player baselines, rookie outcomes.
- Refresh: weekly during the season; full backfill at season boundaries.
- Manual export path: PFR HTML page dump → `ingest_manual_export(path)`. Fixtures live under `tests/fixtures/nfl_data_py/`.
- Source ID: `gsis_id` for NFL, PFR slug for college / historical.
- Required normalized columns: `season`, `gsis_id`, `position`, `pick`, `round`, `team`, plus per-season production columns for Engine B.

### PFF (subscriber)

- Adapter: `app/data/pff.py`
- Path: authenticated scraping primary; manual CSV export from PFF dashboard as fallback.
- Authority: snap counts, route participation, player grades, YPRR.
- Refresh: weekly during the season.
- Manual export path: CSV downloads from the PFF Premium Stats dashboard. Required columns are documented in `app/data/pff_manual_export_schema.md`.
- Source ID: PFF `player_id`.
- Credentials: in Lakehouse mode, stored as Databricks Secrets in scope `dynasty-genius/pff` and read via the Databricks SDK secrets API. In local-file mode, fall back to `~/.config/dynasty-genius/pff.env` (gitignored) read via `dotenv`. Never logged. Same env-var names in both modes; see [storage-strategy.md](storage-strategy.md#credentials--secrets).
- Failure modes: PFF block → `SourceAuthError`. Adapter logs the block, alerts via the freshness report, and the operator is expected to drop a manual CSV export within 7 days before downstream gates fail.
- Tests: `tests/data/test_pff_parser.py` runs against checked-in fixtures, never against the live site.

### PlayerProfiler / RAS

- Adapter: `app/data/playerprofile.py` (existing) for PlayerProfiler; `app/data/ras.py` (new) for ras.football.
- Path: authenticated scraping for PlayerProfiler; ras.football is free.
- Authority: College Dominator, Breakout Age, athletic testing summary (PlayerProfiler); RAS scores by year and position (ras.football).
- Manual export path: PlayerProfiler player-page HTML dump; RAS yearly leaderboard page dump.
- Source ID: PlayerProfiler internal ID; RAS uses player slug + draft year.
- Failure modes: PlayerProfiler block → `SourceAuthError`. RAS site unreachable → `is_stale=True`.
- Credentials: PlayerProfiler subscriber session lives in Databricks Secret scope `dynasty-genius/playerprofiler` (Lakehouse mode) or `~/.config/dynasty-genius/playerprofiler.env` (local mode). RAS is unauthenticated and needs no secret. See [storage-strategy.md](storage-strategy.md#credentials--secrets).

### KeepTradeCut (KTC)

- Adapter: `app/data/ktc.py`
- Path: scraping the public KTC pages (no subscription required, but scraping is throttled).
- Authority: market value (1QB and Superflex), 30-day trend, market rank.
- Refresh: daily.
- Manual export path: KTC does not offer an export. Fallback is a saved HTML page dump from the user's browser.
- Source ID: KTC slug.
- Failure modes: KTC block → `SourceAuthError`. Operator drops a saved HTML dump as the manual fallback.
- Critical rule: **KTC values never enter Engine A or Engine B training data**. They populate `gold.market_overlay` only, plus the DVU peg job (see [storage-strategy.md](storage-strategy.md#the-currency-dynasty-value-unit-dvu)). A test in `tests/contract/` enforces that no model artifact's feature list contains a KTC column. In Lakehouse mode, this is enforced a second time at the platform level: `silver.market_signals` (where KTC writes) has no read permission from any feature-pipeline service principal — defense in depth.
- Credentials: KTC scrape session, when applicable, lives in Databricks Secret scope `dynasty-genius/ktc` (Lakehouse mode) or `~/.config/dynasty-genius/ktc.env` (local mode).

## Freshness Reporting

Each adapter exposes `freshness(season) -> FreshnessReport`:

```
{
  "source_name": "pff",
  "season": 2025,
  "last_snapshot_at": "2026-04-28T13:02:00Z",
  "age_hours": 53,
  "completeness": 0.92,
  "is_stale": false,
  "stale_reason": null,
  "next_expected_refresh": "weekly",
  "blockers": []
}
```

The decision-card API loads `FreshnessReport` for every source the player's `inputs_present` includes. Stale or low-completeness sources surface as caveats on the card.

## Tests Required

Every adapter has at minimum:

- `tests/data/test_<source>_parser.py` — parses checked-in fixtures, asserts schema and row counts.
- `tests/data/test_<source>_manual_export.py` — manual export path produces the same normalized shape as automated.
- `tests/data/test_<source>_failure_modes.py` — `SourceAuthError`, `ParserSchemaDrift`, stale snapshot path each produce the expected downstream behavior.
- `tests/contract/test_no_silent_substitution.py` — verifies that no adapter falls back to a different source when its primary path fails.
- `tests/contract/test_ktc_not_in_features.py` — ensures KTC columns never appear in any model's feature list.

Identity layer:

- `tests/identity/test_resolution_exact.py`, `test_resolution_ambiguous.py`, `test_resolution_missing.py`, `test_id_conflict.py`, `test_promotion_audit.py`.

Identity rejection produces a triage row, not a silent drop. Tests assert that.
