# Layer 1 live refresh success audit — Codex v1

Date: 2026-08-08 ET  
Layer: 1 — ingestion  
Reviewer: Codex, independent technical lane

## Scope

Audit the authorized one-shot execution of:

```text
.venv/bin/python3.14 scripts/run_layer1_daily_control.py --only nflverse_usage_capture sleeper_transactions
```

No scheduler installation, paid route, provider outreach, or subscriber-data access is in scope.

## Independent checks

1. `app/data/ops/layer1_daily_control_latest.json` reports aggregate `exit_code: 0`.
2. The only entries with `state: executed` are `nflverse_usage_capture` and
   `sleeper_transactions`; both report `failed: false`, `freshness: current`, and
   `age_days: 0.0`.
3. CFBD reports `state: skipped_paid_gate`; no paid route ran.
4. `app/data/nflverse_usage/nflverse_usage_status_latest.json` reports `status: ok`,
   `failed_stage: null`, run
   `nflverse-usage-20260808T0357281958710000`, finished
   `2026-08-08T04:12:37.070589+00:00`.
5. `app/data/nflverse_usage/export/nflverse_usage.ready.json` advanced to that same run.
6. Its manifest contains 14 files, matches the ready marker's file map, and all 14
   manifest SHA-256 values recompute from the written files.
7. `contracts.parquet` reads successfully with 97,022 rows. The SQLite store contains
   two 48,511-row snapshot vintages, one from the earlier failed export run and one from
   the successful rerun. The sets of per-row `content_sha256` values are identical
   across the two snapshots; accumulation across distinct snapshot IDs is the declared
   `apply_snapshot` behavior, not duplicate insertion within one snapshot.
8. `unresolved_identity.parquet` has 259,861 rows and the exact ordered schema:
   `stream`, `source_id`, `identity_kind`, `identity_status`, `season`, `player`,
   `position`, `capture_axis`, `snapshot_id`, `observed_at`; every dtype is String.
9. Its 32,620 `contracts` unresolved rows all carry non-null `snapshot_id`; two distinct
   contracts snapshot IDs are represented. This is the populated production condition
   that failed before the schema repair.
10. The store grew from 1,540,304 to 1,588,816 physical rows: +48,511 contracts rows and
    +1 snapshot-capture row. The 13 pre-existing source-table counts remained unchanged.
11. Sleeper transaction capture finished `status: ok` at
    `2026-08-08T04:13:09.149759+00:00`; table counts remain 937 transactions, 1,698
    movements, and 4 season-capture rows. This proves the route ran and found no new
    league activity since the earlier capture; it does not prove recovery of the prior
    eight-day gap.
12. The earlier failed export directory remains a 13-file orphan without a manifest.
    It was not deleted. The new cleanup guard is prospective.
13. Frozen unrelated paths recompute unchanged:
    `scripts/dg_delivery.py` = `b3247ec8...`; wire-health RED = `fd924eb1...`.

## Verdict

**LIVE-RUN AUDIT CLEAR.** Both authorized free sources executed successfully; the
nflverse consumer-ready export advanced with the repaired schema; no paid or unrelated
route ran.

## Explicit boundary

This clears the live execution evidence only. It does not authorize scheduler
installation, orphan cleanup, paid CFBD access, subscriber-data access, provider contact,
or a cadence reduction. At the current daily target, contracts snapshot accumulation is
about 48.5k rows per run; whether to later reduce capture frequency or retain only changed
snapshots is a separate retention/cadence decision after Layer 1 is filled.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
