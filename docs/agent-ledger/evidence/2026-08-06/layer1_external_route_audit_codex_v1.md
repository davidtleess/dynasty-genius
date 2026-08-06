# Layer 1 external-read route audit — Codex v1

**Date:** 2026-08-06 (America/New_York)  
**Layer:** Layer 1 data foundation  
**Scope:** read-only caller and consumer-edge inventory. No adapter, capture, store, scheduler,
consumer migration, commit, push, or enablement authority is inferred.

## Finding

The five direct reads in Feature Refresh are not the complete external-read universe. More
importantly, several existing sources already have multiple acquisition routes. The correct unit of
reconciliation is **one upstream dataset → one canonical capture → many declared consumers**.
Counting every caller as a new stream would inflate the inventory; ignoring the callers would hide
parallel production routes.

## Scheduled and production/request-triggered routes

| Provider / upstream dataset | Caller and class | Current capture state | Catalog delta |
| :-- | :-- | :-- | :-- |
| nflverse `player_stats`, `rosters`, `snap_counts`, `pbp`, `participation` | daily Feature Refresh,
  `scripts/run_feature_refresh.py:52-103` | live provider reads; B4 also exists separately in the
  canonical store | already rowed B15–B19 |
| same five nflverse datasets | active/manual Engine B builder,
  `scripts/assemble_engine_b_dataset.py:209-232` | second direct consumer of the same streams | add
  consumer edges; do not create five more streams |
| nflverse `pbp` | request-triggered Roster Auditor through
  `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py:128-165` | live, no exact capture/cache | catalog
  already identifies this as another B18 consumer |
| nflverse `schedules` + `player_stats` | weekly Realized Outcome job,
  `scripts/run_realized_outcome_scoring.py:337-383`; LaunchAgent at
  `ops/launchd/com.davidleess.dynasty-realized-outcome-scoring.plist` | currently noops before source
  load because prediction snapshots are absent; becomes live when predictions exist | `schedules`
  stream and the additional `player_stats` consumer are absent |
| Sleeper league/user/roster/player endpoints | request-triggered Roster Auditor,
  `app/services/roster_auditor.py:400-455`, through `app/data/sleeper.py` | direct live reads | parallel
  to N18; consumer route absent from catalog |
| Sleeper league/universe endpoints | daily capture wrapper,
  `scripts/run_league_snapshot_capture.py`, sourced by `build_sleeper_universe_snapshot.py` |
  normalized N18 snapshot; exact endpoint replay absent | already rowed N18 accurately |
| FantasyCalc current values | daily append-only forward capture,
  `scripts/run_fc_forward_capture.py`; LaunchAgent `com.davidleess.dynasty-fc-snapshot` | durable
  forward store | catalog names the store |
| same FantasyCalc values | request-triggered JSON cache/live fetch,
  `src/dynasty_genius/adapters/fantasycalc_adapter.py:89-144`, called by
  `app/api/routes/trade_market.py:92-94` and
  `src/dynasty_genius/services/market_overlay_service.py:190-202` | independent seasonal cache
  (6h in-season / 24h offseason) and live API fallback | parallel acquisition surface absent from
  catalog |

### Consequence

Option A is broader than changing `run_feature_refresh.py`. The Engine B builder, Roster Auditor,
Realized Outcome job, and FantasyCalc/Sleeper request-time paths each need an explicit disposition:
consume canonical last-good, remain a separately governed route under an explicit architecture
amendment, or remain frozen/validation-only. A scheduler alone does not reconcile consumer edges.

## Active/manual builders with uncaptured or bypassable inputs

| Dataset | Caller | Finding |
| :-- | :-- | :-- |
| nflverse Combine, 2015–2025 | `scripts/build_w2_features.py:520-523` | active builder reads live and
  rewrites `prospects_with_outcomes_v3.csv`; no replayable source capture found |
| CFBD foundation | canonical wrapper `scripts/run_cfbd_foundation_refresh.py:21-76` | wrapper stages
  raw and curated output correctly, but `scripts/build_w2b_cfbd.py` remains directly invokable and
  can mutate the active training CSV outside the isolated wrapper |
| PFF NCAA receiving summary | `scripts/build_college_features.py:214-241,327-334` | manual source
  capture and builder exist; active `yprr_college` remains empty, so this is a curation/promotion
  gap rather than a missing provider |

## Non-recurring routes that must not be mislabeled as production streams

| Caller | External reads | Correct class |
| :-- | :-- | :-- |
| `scripts/run_t3_freeze_2025.py` | CFBD roster + nflreadpy draft picks and `ff_playerids` |
  one-time immutable study freeze |
| `scripts/ingest_2026_draft.py` | nflreadpy draft picks + Sleeper `/players/nfl` | one-time draft
  ingest; existing `nfl_data_py_verified_nfl_draft` provenance defect remains |
| `scripts/build_nflreadpy_qb_identity_bridge.py` | nflreadpy rosters | manual identity build |
| `scripts/generate_qb_role_occupancy_labels.py` | player stats, snap counts, rosters | validation
  builder; QB validation remains a registered study that has not run |

These are consumer/freeze routes on existing upstream datasets. They need provenance and replay
classification, but they are not evidence for four new production streams or new providers.

## Required canonical-catalog deltas

1. Add `schedules` as a future-live stream tied to the Realized Outcome job; add that job as another
   consumer of `player_stats`.
2. Add Combine as an active-builder input with no canonical capture.
3. Add Engine B assembly as a second consumer of the five Option A streams.
4. Add Roster Auditor as direct Sleeper and B18 consumer edges; distinguish it from N18.
5. Record FantasyCalc's forward-store route and request-time JSON-cache/live route as a current
   one-source/two-acquisition conflict.
6. Record that the CFBD isolated capture wrapper can still be bypassed by direct builder execution.
7. Keep one-time freezes, identity builds, and validation loaders in their own caller class.

No new provider is implied by any of these findings. They are route reconciliation and replayability
gaps inside sources the repo already uses.
