# Minimum Ingestion Contract — PROPOSAL v1

**For David to accept, alter, or reject.** Authored by Claude Code; reviewer seat held by Codex.

**This is not a platform, a tool adoption, a dependency, a migration, a schema change, or an
implementation.** No running job changes. Nothing here is authorised by its own existence.

**Justification rule, applied to every row below:** each obligation cites either **[R]** the committed
research (`systematic_ingestion_framework_research_codex.md`) or **[M]** a defect this cockpit
*measured today*. **No obligation is here on taste.** Anything I could not justify either way was cut.

---

## Part 1 — What a source must declare (12 fields)

| # | Field | Why it exists |
| --: | :-- | :-- |
| 1 | `source_id` + `owner_path` — the code path that actually performs the read | **[M]** Five established sources were invisible to a host-string sweep, incl. one read from a *git history*. A source that cannot name its read path cannot be enumerated. |
| 2 | `status` — `live` \| `manual` \| `fixture-only` \| `declared-not-ingested` | **[M]** `SOURCE_REGISTRY` has **no status field**: it lists sources that never run *and* omits established ones. A reader cannot tell aspiration from reality. |
| 3 | `mode` — full-refresh \| incremental-cursor \| append-only \| manual-import | **[R]** §2.1 — batch/incremental/CDC answer different source questions. |
| 4 | `write_disposition` — replace \| append \| merge | **[R]** §2.2 — write semantics must follow record semantics. |
| 5 | `primary_key` + `tie_breaker` | **[R]** §2.2/§6 — required for merge and for idempotent replay. |
| 6 | `cursor` + `overlap_window` | **[R]** §2.4 — watermarks need an overlap and a late-data policy. |
| 7 | `delete_behavior` — how source-side deletions are represented | **[R]** §6. |
| 8 | **`declared_cadence` + `cadence_semantics`** — the interval **and** whether it means *ingest interval* or *cache TTL* | **[M]** `freshness_hours` **does not define its own meaning**. `sleeper` declares `1` against a job that runs every 24h, and the two readings imply opposite verdicts. **A cadence without stated semantics cannot support a staleness judgement.** |
| 9 | `schema_policy` — required fields, new-field policy, bad-record vs bad-batch | **[R]** §2.6 — schema evolution and contracts are different policies. |
| 10 | `backfill_range` | **[R]** §2.7 — backfill is a normal execution mode, not an afterthought. |
| 11 | **`raw_retention`** — is the raw payload kept, and where | **[M]** `nflreadpy` loads have **no repo-local raw snapshot** despite a declared parquet cache policy; Sleeper drops most `/players/nfl` fields at curation. Without raw, "what we didn't take" is unanswerable and replay is impossible. |
| 12 | **`fields_declined`** — what the source offers that we deliberately do not take | **[M]** The "what is missing" axis was **unanswerable for 2 of 3 live sources**. Recording declines converts a silent omission into a decision. |

## Part 2 — What every run must record

**[R]** §6 per-run list, plus one obligation from measurement:

`logical_interval` · `run_id` · `code/config version` · `cursor_before` → `cursor_after` ·
`rows_in` / `rows_written` / `rows_rejected` · `raw_artifact_id` · `terminal_status`

**Plus [M] — a lateness signal.** On **2026-07-17 and 2026-07-27** the morning jobs ran ~2h and ~10h
late, together, and **every health surface reported green**. A run record must carry
`scheduled_for` alongside `started_at`, so lateness is a *fact in the record* rather than something
only a human comparing logs can see.

## Part 3 — The negative-control clause (load-bearing; not aspirational)

**[R]** §4 + **[M]** the SQL auditor and the compliance job. The research names the trap exactly: a
quality tool *"can be pointed at zero assets or given a vacuous predicate,"* and a green result is
evidence **only when the check itself has been shown to fail.** Both failure modes are live here.

1. **Every check declares a positive fixture and a negative fixture.** The negative fixture must make
   the check fail.
2. **Every check records `last_proven_failure`** — the timestamp it was last *demonstrated* to fail.
   **A check with no `last_proven_failure` may not gate and may not report green.** It reports
   `unproven`.
3. **An empty target set FAILS. It never passes.**
   **[M]** `codex_audit_sql.py` has printed *"Codex SQL audit passed for 0 SQL file(s)"* and exited 0
   since May, while the four real `.sql` files sat in `infrastructure/src/sql/`.
4. **A non-empty response is not an assertion.**
   **[M]** `codex_audit.py:120-129` returned `PASSED` for any non-empty result without inspecting
   values; 3 of its 5 named "tests" asserted nothing, including the one named for the 65:35 doctrine.
   **A check must state its predicate, not merely return rows.**
5. **A check that has not run within its declared cadence reports `stale`, not green.**
   **[M]** The compliance job produced no observed terminal result for five days; the same day it was
   diagnosed, the telemetry closeout still read *"all pipelines are green."*

## Part 4 — Applied to the three sources that actually ingest daily

*Values measured today, not assumed. `?` = the contract exposes a real unknown — that is the point.*

| Field | **Sleeper** | **FantasyCalc** | **nflreadpy** |
| :-- | :-- | :-- | :-- |
| `owner_path` | `app/data/sleeper.py` → `run_league_snapshot_capture.py` | `fc_forward_capture_driver.py` → `run_fc_forward_capture.py` | `run_feature_refresh.py` |
| `status` | live | live | live |
| `mode` | full-refresh | append-only | full-refresh, source-hash-gated |
| `write_disposition` | replace (per-run immutable dir) | append | replace + noop-if-unchanged |
| `primary_key` | `sleeper_player_id` | player + date + settings | player + season |
| `cursor` / `overlap` | none — full pull | `snapshot_date` / none | source content hash / n/a |
| `delete_behavior` | **?** — a player vanishing from the universe is undefined | append-only, n/a | **?** |
| `declared_cadence` | **`1h` (registry) vs 24h observed — semantics undefined** | `24h`, matches | `168h` registry vs daily job |
| `schema_policy` | **?** — no declared required-field set | **?** | 33 columns, no declared contract |
| `backfill_range` | **?** | full history in SQLite (16,718 rows) | **?** |
| `raw_retention` | **NO** — 6 of many fields kept | **YES** — raw cache retained | **NO** repo-local raw snapshot |
| `fields_declined` | **unrecorded** — incl. transactions, never ingested | ADP, roster %, trade frequency, tier, college… | **unrecorded** |
| Observed reality | 09:20 daily; 12,203 rows; 11 endpoints | 09:00 daily; 475 rows | 09:15 daily; **noop 30 of 31 runs** |

**What the worked example demonstrates — this is the argument for the contract, not decoration.**
Filling twelve fields for three sources surfaced **nine unknowns** in the product's most-exercised
paths: nobody can currently say what happens when a Sleeper player disappears, what fields are
required, what the backfill range is, or what we declined to take. **None of these needed a tool to
find. They needed a form with a blank on it.**

---

## What this proposal does NOT do

- **No tool is adopted and no dependency is added.** The research's own conclusion is that at this
  scale *"the pattern matters; the framework may not"*, and it explicitly does not establish that any
  of dlt, Airbyte, Meltano, dbt, Dagster, Airflow, Prefect, GX, Soda or pandera is necessary.
- **Nothing is implemented, migrated, or rescheduled.** No running job changes.
- **It does not fix a single defect it cites.** Every `?` above stays a `?`.
- **It takes no position** on the SQL job, the cliff-age question, or the Databricks retirement.

## Open questions this proposal cannot answer — David's, not a lane's

1. **Is a daily laptop job expected to run while the laptop is asleep?** (Research §8, and the direct
   cause of the 07-17/07-27 slips.) The contract can *record* lateness; it cannot decide what lateness
   should mean.
2. **What did `freshness_hours` originally mean** — ingest interval or cache TTL? Field 8 needs the
   answer; it does not supply it.
3. **Does a declared contract apply retroactively** to the ~10 non-daily sources, or only to sources
   from here forward?
4. **Where does the contract live** — extending `SOURCE_REGISTRY`, or a new declaration? Extending it
   inherits a schema that today fails in both directions.

**Recommended next step, explicitly not taken:** if David accepts the shape, the smallest useful move
is to fill this form for the **three live sources only** and let the `?` count be the measure of how
well the foundation is understood. That is a proposal, not an authorised action.
