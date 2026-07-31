# Multi-season transaction ingestion — design note (TW30N-BUILD-01)

**Claude Code, 2026-07-30 evening. Tower's word carrying David's: "focus on layer 1 and 2 … lets get
our data." Layer 1.** Extends `transaction_ingestion_design_claude_v1.md`, same bar as `c841c52`.

Layers 1–2 dependency check is not applicable in the usual direction: this **is** layer-1 work. It
was opened because layer 4 (context — the twelve managers, per the 2026-07-30 order amendment) has a
substrate one season deep, and a manager cannot be characterised from one season. **Priority is not
authorization and this note opens no layer-4 thread** — it ingests, stores and resolves. Nothing
reads it.

## What the live chain actually returned — measured 2026-07-30, not assumed

`previous_league_id` walked from `1314363401744416768`:

| Season | league_id | Transactions | Legs with activity | Status |
| :-- | :-- | --: | :-- | :-- |
| 2026 | `1314363401744416768` | 67 | 1 | in_season |
| 2025 | `1183088915091423232` | 299 | 1–17 | complete |
| 2024 | `1049152209134424064` | 323 | 1–17 | complete |
| 2023 | `912589367620100096` | 243 | 1–17 | complete |

**4 seasons, 932 transactions, 1,692 movements.** The chain terminates on a genuine `null`, so the
league's entire Sleeper history is reachable. 2026 is 14× smaller than a full season because only
leg 1 has been played — not a capture defect.

## The finding that changed the design

**`roster_id` → owner is a per-league-season fact, not a league fact.** Sleeper reissues `roster_id`
1..12 in every season of a chain, and the slot changes hands between them. On David's own chain:

| roster_id | 2026 owner | earliest differing season |
| --: | :-- | :-- |
| 11 | `1005290797896036352` | 2025 → `928767555920064512` |
| 2 | `1124744818174812160` | 2024 → `978702566609444864` |
| 3 | `1049829521757237248` | 2023 → `727609206567428096` |

The obvious extension — build one resolver, pass it to every season — type-checks, passes every
existing test, and is **wrong**. It files a departed manager's moves under whoever later took their
slot, **silently and with a confident display name attached**. For layer 4, where the whole product
value is "what does this specific manager do," that is the worst available failure mode: not missing
data, but confident wrong data.

Every season is therefore normalized against a resolver built from **its own** `/rosters` + `/users`
(`IdentityResolver.with_managers`). `build_resolver` is a per-link callable in the chain runner's
signature specifically so that passing one shared resolver is not expressible by accident.

Verified against the **live** API, not the fixture: **1,692 / 1,692 movements match the owner of
their roster in their own season, 0 mismatches.**

## Three-valued identity, per season

Coverage is reported per league-season and aggregated without flattening. Measured:

| Season | Players | canonical_resolved | sleeper_only | unknown |
| :-- | --: | --: | --: | --: |
| 2026 | 99 | 97 | **2** | 0 |
| 2025 | 476 | 476 | 0 | 0 |
| 2024 | 524 | 524 | 0 | 0 |
| 2023 | 409 | 409 | 0 | 0 |

The two unresolved (`13324`, `13400`) are in **2026 only** — recent additions the frozen
`ff_playerids` crosswalk predates. **The gap is in the newest season, not the oldest**, which is the
opposite of the intuition the ticket wrote it against, and it is exactly why the per-season block is
reported rather than a chain total: 1,506 / 1,508 rounds to "resolved" and loses which season the
hole is in. `chain_coverage.seasons_with_unresolved_players` names the season explicitly.

Manager identity: **0 unresolved in all four seasons.** 2026 shows `managers_total: 11` because one
of the twelve has not transacted this season — a true fact about the season, not a resolution gap.

## Schema v3 and what it refuses

- `league_transaction_movement` gains `league_id` + `season`. A movement without them is
  uninterpretable, because `roster_id` means a different manager in each season. A v2 store therefore
  **fails closed by name** rather than mixing schemas.
- New `league_season_capture` table: one row per league-season with its own status, legs, totals and
  coverage. The store can answer "which seasons do I hold, and did each land completely?" **without
  trusting a status marker that describes only the most recent run.** A failed season gets a row
  saying `failed`; a season the run never reached gets no row at all.
- `transaction_id` is the primary key, so a collision across two seasons would silently REPLACE one
  league-season's history. Measured: 932 transactions, **zero** collisions — so the store **refuses**
  on a cross-league collision rather than re-keying around a problem that does not exist.
- Raw snapshots are named per league-season. A timestamp-only name would have four seasons overwrite
  each other at one `captured_at`.

## Failure semantics — a short chain and a broken chain must never look alike

1. The marker is written `running` **before chain discovery**, so no run inherits a prior `ok`.
2. Discovery completes **before any leg is fetched**. An unreadable mid-chain league, a cycle, an
   implausible depth, or a league with no season each raise a **named** `league_chain_*` failure with
   the partial walk quoted — nothing is fetched and no store is created.
3. A season failing mid-chain writes `status=failed` naming league, season, stage and (for a fetch)
   leg, plus `seasons_captured` — what landed is a stated fact, never an inference. Earlier seasons
   keep their real data and the store's own season table records which are `ok` and which are not.

## Idempotence, verified by content on live data

Two consecutive live chain runs: content fingerprint over all three tables **identical**
(`351a4f94…`), 932 `unchanged`, 0 inserted, 0 updated. The season table is content-addressed too, so
an unchanged re-capture leaves even its `ingested_at` untouched.

## Boundaries held

No scheduler, plist, launchd or cron. No `report_freshness.json` registration. No producer change and
nothing in the 09:00–10:15 morning cluster. No `backup_manifest.json` edit — its deferral test still
passes unchanged. Not committed.

**Separate item, same turn:** the `.gitignore` entry for the transaction store path was restored
(`app/data/league_transactions.db`, `-journal`, `app/data/league_transactions/`), closing the exposure
where a rebuilt store in the default location sat untracked and visible. Independent of the manifest
deferral, which is untouched.
