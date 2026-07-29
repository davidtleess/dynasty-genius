# TW29 layers 1–2 census — Codex runtime-trace enumeration

**Date:** 2026-07-29
**Lane:** Codex, independent runtime/call-graph enumeration
**Authority:** findings only. Nothing below authorises a repair, specification, schema
change, ingestion, refresh, credentialed query, commit, scheduler action, or backup drill.

## Answer first

**The foundation is not established as sound enough to treat its present source inventory as
complete or its provenance names as literal runtime lineage.**

The product does ingest useful foundation data. Runtime evidence establishes active ingestion
from Sleeper, FantasyCalc, nflverse through `nflreadpy`, CFBD, historical PlayerProfiler caches,
PFF-derived manual artifacts, and a DynastyProcess/FantasyPros archive. It also mirrors Sleeper
CDN headshots. But the inventory contract does not describe that executable reality:

1. The registry calls the foundational draft/outcome source `nfl_data_py`, while the executable
   client has been `nflreadpy` since commit `fa99562`. The migration deliberately retained the
   old registry/provenance string. This is a legacy logical alias, not literal client lineage.
2. The registry omits the general `nflreadpy` Engine B source family, DynastyProcess,
   Sleeper CDN assets, Databricks inputs, and first-party/manual identity inputs, while listing
   sources for which production ingestion is not established (MFL, RAS, RotoViz,
   Campus2Canton, and deferred market vendors).
3. The general Engine A/B `nflreadpy` paths fetch directly into derived CSV/runtime output.
   No repo-local raw parquet/source snapshot exists for those production loads, despite the
   registry declaring `cache_policy="parquet_snapshot"`.
4. A source can be present in one curated store and absent in another. The strongest example is
   draft capital: `pick` and `round` are present for all 874 prospect rows and join to 375 of
   505 latest-season Engine B rows, although Engine B's own 33-column store carries neither.
   Therefore absence from one expected table is not evidence of non-ingestion.
5. Several declared sources are not production sources. MFL has a runnable adapter but no local
   cache or output artifact. RAS/RotoViz/Campus2Canton resolve only to mock fixtures. The current
   PlayerProfiler probe contains 874/874 `parse_error` results, while an older cache and v2
   curated table contain values.
6. The current 874-row Engine A v3 store explicitly carries entire unpopulated feature classes:
   transfer-portal flag 0/874; college YPRR 0/874; position RAS composites 0 for every eligible
   RB/WR/TE; QB sack rate 0/126; and other named gaps below. These are honest null+missing
   encodings, not measured values.
7. I found no layer-1/2 field proven to publish an unmeasured numeric constant as though measured.
   Two curated combine flags are constant-valued (`wr_meets_athletic_floor=1` for 262 measured
   WR rows; `rb_meets_athletic_floor=1` for 168 measured RB rows), but both are computed from
   varying source measurements and very low declared thresholds. They are degenerate
   measurements, not fabricated constants. Defaults and provenance labels are separately
   disclosed as defaults/metadata.

The minimum **implied work**, not authorised work, is at the end of this report.

## Coverage and independence boundary

### Method actually used

I did not begin from the source registry, source documentation, Claude's list, LaunchAgents, the
FastAPI route tree, or a grep inventory. I first:

1. AST-parsed all 581 tracked Python files.
2. Seeded 106 executable entrypoints from `__main__` guards plus `app/main.py`.
3. Resolved repo-local imports transitively to 222 reachable modules.
4. Classified 561 reachable boundary calls:
   489 file/store, 22 SQLite, 20 network, 18 subprocess, 9 external-library loaders,
   and 3 workspace-client calls.
5. Replayed the Sleeper, FantasyCalc, MFL, and CFBD boundaries with mocked transports and
   production orchestrators, so the trace exercised branch behavior without network calls or
   writes.
6. Only after freezing that source universe, reconciled it against actual CSV/JSON/SQLite stores,
   source registry declarations, and declared cadence configs.

The static call graph misses calls hidden behind aliases. For example, it did not initially
classify `nfl.load_player_stats` in `assemble_engine_b_dataset.py` as external because the alias
does not contain `nflreadpy`; direct boundary replay/search added that family. This is recorded as
a method miss, not silently folded into an assertion of completeness.

### Coverage bound

Covered:

- all tracked Python executable entrypoints and their statically reachable repo-local imports;
- direct HTTP, external-library, SQLite, subprocess, workspace-client, and file boundaries;
- current and historical repo-local layer-1/2 CSV, JSON, cache, runtime, identity, asset, and
  SQLite stores;
- missing-class searches across every enumerated store family, with stable-key joins when
  available;
- declared cadence only, from tracked configuration/registry declarations.

Structurally cannot see or prove:

- dynamically constructed imports/endpoints that evade AST resolution;
- branches not reached by the safe synthetic replay;
- untracked/manual activity, including past one-off probes;
- external scheduler activity not encoded in tracked files;
- private raw PFF exports that are intentionally absent from the repository;
- contents or truth of credentialed Databricks tables;
- provider fields not represented in local raw artifacts without making a new live/credentialed
  request;
- whether executable-but-unobserved adapters have ever been run on another machine.

**Independence disclosure:** the initial call-graph source universe and store candidates were
frozen before viewing Claude's census. Later, a package-provenance `rg` command was scoped too
broadly to `docs/` and surfaced two short matching lines from Claude's artifact: one mentioning
the already-known draft-capital join and one mentioning an off-season `nflreadpy` pull. I did not
open or review his artifact. The affected draft-capital fact was independently recomputed here
(375/505 against this lane's selected stores); no off-season freshness verdict from that snippet
is used. This is a post-freeze contamination limitation, not claimed full isolation.

## Enumerated source matrix

`Established` means the evidence compels that data from the source exists in a layer-1/2 store.
It does not mean the source is complete, current, authorised for every role, or decision-grade.

| Source / status | What arrives; grain; declared frequency | What is missing, after cross-store search | Staleness basis only | Silently a constant |
|---|---|---|---|---|
| **Sleeper API — established, active** | Runtime replay exercised league drafts, league, rosters, users, traded picks, player map, NFL state, draft, and draft picks. Current run: 12,203 player rows, 12 rosters, 14 users, 109 reconstructed future-pick rows; player curation keeps name, position, team, age, years experience, and status. Declared producer cadence: daily 09:20 in `app/config/report_freshness.json`; registry freshness contract: 1 hour. | No transaction or trending endpoint in the production replay. Raw player records are not retained; most `/players/nfl` fields are dropped during curation. Transactions were searched repo-wide and are not a production implementation. Draft capital is not in the Sleeper player curation, but exists in the nflverse prospect store and joins to part of Engine B, so it is not globally absent. | **Conflicting declarations:** daily capture vs 1-hour source freshness contract. No freshness verdict here. | Snapshot `defaults` contains disclosed constants (`bench_depth_decay=0.5`, `divergence_noise_band=0.1`, fixed FantasyCalc settings). Future-pick valuation is derived from a versioned curve. No undisclosed unmeasured source metric established. |
| **nflverse via `nflreadpy` — established, active** | Draft picks, weekly/seasonal player stats, rosters, snap counts, PBP, participation, combine, schedules, players, and `ff_playerids` are called across foundation entrypoints. Grains range from player-week and play to player-season, player-draft, player-roster-season, and identity row. Engine B current store has 2,741 player-season rows; prospect store has 874 player-draft rows. Feature refresh is declared weekly 09:15; registry aliases this family to a 168-hour contract. | No repo-local raw source snapshot for general Engine A/B loads. Engine B omits draft fields locally, but latest-season join finds `pick` and `round` for 375/505 rows. Current v3 gaps after all-store search include 0/874 transfer-portal flags; 0/874 college YPRR; 0/233 RB 10-yard split; and 0 for all three position RAS composites. | Registry says 168 hours for `nfl_data_py` and QB context; feature report config says weekly. No freshness verdict. | `nfl_data_py` provenance is a retained alias after a client migration, not literal runtime lineage. Combine floor flags are all `1` among measured rows, but are computed from varying measurements; not fabricated constants. |
| **CFBD — established** | Direct HTTP paths exercise player season passing/rushing, team season stats, PPA, WEPA, SP+, games count, rosters, and teams. Local caches contain 3,330 legacy enrichment entries plus split cache families: 217 games-count, 15 receiving-season, 14 rushing-season, 126 QB, 14 SP+, and 424 team-pass-attempt files. Curated grains are player-draft/player-season features. Registry declares 720 hours for historical seasons. | Current v3 coverage: career dominator 306/355 WR, 198/233 RB, 136/160 TE; SP+ 219/233 RB; `ryptpa` 305/874; TE final RYPTPA 138/160; QB completion/YPA/TD:INT 32/126 each; QB sack rate 0/126. Transfer portal and college YPRR are absent from every current training store. Provider-wide offered fields cannot be exhaustively assessed without a new credentialed/live schema pull. | 720-hour registry declaration. No freshness verdict. | No unmeasured numeric constant established. Missing classes are encoded null with missing/source companions. |
| **FantasyCalc — established, active** | Current SF/PPR/12-team endpoint; local JSON has 475 player rows. Daily append-only store has 16,718 `fc_native` rows at player-date-settings grain. Raw cache retains value/rank/trend/volatility/tier/ADP/roster/trade-frequency fields and player identity/demographic fields. Declared capture: daily 09:00; cache TTL 6h in-season, 24h offseason; registry says 24h. | Curated/SQLite rows drop cache-retained ADP, roster %, trade frequency, owner, tier, height, weight, college, birthday, draft info, and several volatility variants. Three redraft/combined fields are intentionally stripped before cache. Those are curated omissions, not non-ingestion of the raw cache. | Daily 09:00 capture; seasonal 6h/24h cache TTL; registry 24h. No freshness verdict. | Endpoint settings are fixed, disclosed configuration. No fabricated measurement established. |
| **DynastyProcess archive / FantasyPros ECR — established, historical** | A sibling Git history supplies `files/values.csv` plus `db_playerids.csv`; `value_2qb` is mapped to Sleeper IDs. SQLite contains 2,185 `dp_archive` player-date rows over four historical snapshot dates. | PICK pseudo-rows, unmapped IDs, malformed values, and after-target commits are explicitly excluded. The store carries value, rank slots (null here), position, source, and insertion metadata—not the archive's full row. No current-feed path exists. | **No declared cadence.** It is a four-date historical backfill. | No fabricated measurement established; unavailable ranks are null. |
| **PlayerProfiler — established historically; current path not established** | Older caches contain 5,125 ID mappings and 655 stats entries with target share, breakout age, speed score, and a YPTT/YPRR-era field. The v2 training table has target share 608/874, breakout age 572/874, speed score 652/874. | Current probe artifact is 874/874 `parse_error`. Current v3 omits PlayerProfiler fields entirely. A successful present-day parser/feed is therefore not established, even though historical ingestion is. | **No declared cadence** (`freshness_hours=None`). | No fabricated numeric constant established. |
| **PFF manual exports — established in derived/redacted stores; raw not assessable** | Phase16 training artifact has college YPRR for 336/874 and RYPTPA for 325/874 using PFF yards/routes plus CFBD attempts. TE identity/rubric artifacts also carry PFF-derived eligibility and archetype data. Grain: player-draft/player-season. Raw exports are private and absent by design. | Current v3 has college YPRR 0/874 and explicitly names PFF routes-run data as required. Raw offered columns and exact loss through parsing cannot be independently assessed because the input CSV is not present. | **No declared cadence.** | No unmeasured numeric constant established from available redacted outputs. |
| **Sleeper CDN headshots — established** | Script mirrors one image per valid Sleeper player ID. Manifest has 261 entries, all recorded `fresh` at its capture; grain is player asset. | Only 261 IDs have manifest entries. Whether absent assets were never requested, unavailable, invalid, or out of the input cohort cannot be reconstructed solely from the final manifest. | **No declared cadence.** | Status/source URL are metadata, not measurements. |
| **MFL rookie ADP + player map — executable, production ingestion not established** | Mock runtime replay confirms two calls: 2026 rookie ADP and 2026 player map. Normalized grain is rookie-player-season with rank, average/min/max pick, selection %, drafts selected, identity, and caveats. | No `app/cache/mfl_adp/` cache and no MFL divergence output exist locally. Therefore “the product has ingested MFL data” is **not established**. The adapter intentionally cannot filter blended QB count or TE premium. | Adapter TTLs: ADP 24h, player map 168h; registry says 24h. These are declarations, not evidence of an active producer. | `decision_supported=False`, source, and intrinsic caveats are disclosed metadata. No fabricated measurement established. |
| **RAS — fixture-only; production ingestion not established** | Adapter reads `resources/fixtures/ras_mock.csv` and returns a low-score risk flag, a missing flag, and provenance. | Current v3 has RB 0/233, WR 0/355, and TE 0/160 RAS composites. No non-mock RAS cache/export was found. | **No declared cadence.** | On missing data the adapter emits `low_ras_risk_flag=False` plus `missing_athletic_profile=True`; the false value is explicitly caveated, not silently measured. |
| **RotoViz — fixture-only; production ingestion not established** | Generic manual-export adapter can read `resources/fixtures/rotoviz_mock.csv`. | No production export, cache, curated provenance, or active call path was found. | **No declared cadence.** | Not established. |
| **Campus2Canton — fixture-only; production ingestion not established** | Generic manual-export adapter can read `resources/fixtures/campus2canton_mock.csv`. | No production export, cache, curated provenance, or active call path was found. | **No declared cadence.** | Not established. |
| **First-party/manual identity and league inputs — established** | David's league context, college alias bridge, college prospect registry, prospect-to-NFL bridge, frozen 2025 source bundle, and `ff_playerids` pins enter identity/league curation. Grains are league, player identity, alias decision, and frozen source row. | These are not represented in `SOURCE_REGISTRY`; their update authority/cadence is generally not machine-declared. The frozen 2025 bundle names NFL.com, PFF, and Spotrac UDFA references, but the code stores only the source manifest—no fetched UDFA contents—so those three are references, not established ingests. | **No declared cadence** for the manual identity inputs. | Manual confirmations/default IDs are metadata. No unmeasured metric established. |
| **Databricks Bronze/Silver/Gold — enumerated, not assessed — needs David's word** | Tracked SQL/code names `gen_alpha.bronze.nfl_production_2025`, `silver.efficiency_metrics`, `silver.claude_code_staging`, `gold.anchors`, `gold.governance_rules`, and `gold.genius_state`; static governance checks also name additional Gold candidate/evaluation tables. `infrastructure/README.md` declares `gold.genius_state` hourly. | Contents, row grains, completeness, current existence, and field loss are **not assessed**. No credentials or warehouse budget were used. | Hourly is declared for `genius_state`; other named tables have no established cadence in this census. | **Not assessed — needs David's word.** |
| **Deferred/prohibited registry entries — not ingested** | Registry names Dynasty Data Lab, Dynasty Nerds, KTC, Sportradar, Genius Sports, Stats Perform, and Rolling Insights. | No production boundary/store was found for any. `ingest_market_archive.py` accepts `ktc_community_csv`, but no local KTC rows exist in the market store. | No declared cadence. | Not established. |

## Cross-source findings that survive attempted refutation

### F1 — the source registry is not an executable census

This stands. The registry describes a policy allowlist, not runtime reality:

- It retains the `nfl_data_py` name after the code migrated to `nflreadpy`.
- It declares parquet snapshots for the general NFL source, but none exist under `app/` or
  `resources/`.
- It omits several established sources.
- It lists fixture-only, deferred, prohibited, and executable-but-unobserved sources beside active
  ingests without a lifecycle-status field.
- Its Sleeper note says the source provides trending players, but the production replay does not
  call the trending endpoint.

Consequently, a product decision based only on `SOURCE_REGISTRY` can confuse “allowed,”
“implemented,” “has run,” and “currently feeding a curated store.”

### F2 — the foundational NFL source lacks replayable raw lineage

This stands. General Engine A/B loaders call `nflreadpy` directly and write derived CSV/runtime
artifacts. The runtime readiness file preserves a content hash, inference season, and validation
result, but not the raw source frames, source URL/release identifiers, or a per-dataset retrieval
timestamp. A source hash proves equality to some input bytes; it does not make those inputs
reviewable after the fact.

The separate QB validation-study adapter has a raw-snapshot contract, but no QB-validation raw
files currently exist and that study lane is not the production Engine A/B loader.

### F3 — “missing” is store-relative; draft capital disproves expected-place reasoning

This stands. Current probes found:

- prospect source: 874/874 non-null `pick` and `round`;
- Engine B store: no `pick` or `round` columns;
- latest Engine B season: 375/505 player IDs join to the prospect source with non-null capital;
- 130/505 latest rows do not join to that source.

Therefore:

- “draft capital was never ingested” is false;
- “draft capital is available for all current Engine B rows” is also false;
- whether Engine B should carry or consume it is outside this findings-only census.

### F4 — entire declared feature classes remain absent from the current v3 store

This stands after searches across all training CSVs, CFBD caches, manual fixtures, identity
artifacts, and joins:

| Current v3 feature | Populated / eligible denominator | What the store says |
|---|---:|---|
| `transfer_portal_flag` | 0 / 874 | null, missing=1, no source |
| `yprr_college` | 0 / 874 | null, missing=1, no source |
| `rb_10_yard_split` | 0 / 233 RB | null, missing=1, no source |
| `rb_ras_composite` | 0 / 233 RB | null, missing=1, no source |
| `wr_ras_composite` | 0 / 355 WR | null, missing=1, no source |
| `te_ras_composite` | 0 / 160 TE | null, missing=1, no source |
| `wr_rec_tds_per_game_final` | 0 / 355 WR | null, missing=1, no source |
| `te_deep_yard_share` | 0 / 160 TE | null, missing=1, no source |
| `qb_sack_rate_final` | 0 / 126 QB | 26 labeled `below_volume_gate`; remainder null |

This is not a silent-null defect: companions disclose absence. It is still a foundation coverage
fact. A schema containing named fields is not evidence that the source class exists.

### F5 — no fabricated numeric constant established at layers 1–2

The constant-column sweep attempted to break this conclusion.

- Engine B v1 has six entirely null columns, but v2 populates them; null is not a constant
  measurement.
- Engine A v3 has many constant provenance strings, missing flags, version labels, and degradation
  flags. Those are metadata.
- WR/RB combine floor flags are constant `1` among measured rows, but the inputs vary and the code
  computes each row against declared thresholds (29-inch vertical; speed score 80).
- Sleeper/FantasyCalc/MFL fixed settings are disclosed configuration.

Accordingly, **no layer-1/2 unmeasured numeric value masquerading as a measurement was
established**. This does not review or clear the separate “silently a constant” findings owned by
the implementing lane.

## Enumerated but not assessed / not established

- Databricks table contents: **NOT ASSESSED — NEEDS DAVID'S WORD.**
- Full PFF raw-field loss: **NOT ASSESSED — PRIVATE RAW EXPORT ABSENT.**
- Full provider schemas for CFBD, Sleeper, FantasyCalc, and MFL beyond locally observed payloads:
  **NOT ASSESSED — no new live/credentialed schema pull authorised.**
- Whether MFL ever ran outside this workspace: **NOT ESTABLISHED.**
- Whether manual RotoViz/Campus2Canton/RAS production files existed and were later removed:
  **NOT ESTABLISHED.**
- Dynamically built/untracked/manual endpoints and one-off activity: **NOT ESTABLISHED.**
- Actual freshness/staleness of any source: **NOT ASSESSED HERE; Gemini owns telemetry.**

## What must exist first — implied, explicitly not authorised

Before treating the layer-1/2 foundation as a complete build substrate, the evidence implies the
need for:

1. **One runtime-backed source manifest** that distinguishes logical provider, client library,
   dataset/endpoint, producer entrypoint, raw store, curated store, lifecycle status
   (`active`, `historical`, `fixture-only`, `implemented-unobserved`, `deferred`, `prohibited`),
   declared cadence, and last successful lineage marker. This is implied work only.
2. **Replayable raw lineage for every active Engine A/B source dataset**, especially the general
   `nflreadpy` frames, with retrieval/release identity and parser version before derivation. A hash
   without preserved inputs is insufficient for independent replay. This is implied work only.
3. **A ruling on the legacy `nfl_data_py` alias:** either it is an explicitly documented logical
   nflverse source name, or runtime provenance must name `nflreadpy` separately from provider.
   This is implied work only.
4. **A reconciled cadence contract** where source freshness thresholds and producer schedules do
   not conflict, especially Sleeper's 1-hour registry contract versus daily capture. This is
   implied work only.
5. **An explicit disposition for every all-missing current feature class**: source it, retire it,
   or keep it as an explicitly deferred schema field. This census does not choose among those.
6. **A David decision on credentialed Databricks enumeration** before any claim that Gold is part
   of the sound current foundation.

## Rerunnable commands

These commands are read-only. They do not run live fetches or credentialed queries.

### Call-graph coverage

The AST scanner used in-session was `/private/tmp/tw29_runtime_census.py` and reported:
581 tracked/parsed Python files, 106 entrypoints, 222 reachable modules, and 561 boundaries.
The durable cross-check below reproduces the external boundary candidates without relying on the
temporary scanner:

```bash
rg -n --glob '*.py' \
  'httpx\.(get|post)|requests\.(get|post)|AsyncClient|urlopen|sqlite3\.connect|WorkspaceClient|load_(player_stats|rosters|snap_counts|pbp|participation|draft_picks|combine|ff_playerids|schedules|players)' \
  app scripts src
```

### Sleeper

```bash
rg -n 'get_(league|rosters|users|traded_picks|league_drafts|draft|draft_picks|all_players|nfl_state)|transactions|trending' app scripts src
run_id=$(jq -r '.run_id' app/data/league_runtime/ready_latest.json)
jq '{player_count:(.players|length),roster_count:(.rosters|length),user_count:(.users|length),future_pick_count:(.future_picks|length),player_fields:(.players[0].player|keys)}' "app/data/league_runtime/runs/$run_id/snapshot.json"
```

### nflverse / `nflreadpy` and draft-capital everywhere join

```bash
rg -n --glob '*.py' 'nflreadpy|nfl\.load_' app scripts src
find app resources -type f \( -name '*.parquet' -o -name '*.pq' \) -print
.venv/bin/python3.14 - <<'PY'
import pandas as pd
b = pd.read_csv("app/data/training/engine_b_features_v2.csv", low_memory=False)
p = pd.read_csv("app/data/training/prospects_with_outcomes_v3.csv", low_memory=False)
x = b[b.feature_season.eq(b.feature_season.max())]
j = x.merge(p[["gsis_id","pick","round"]], left_on="player_id", right_on="gsis_id", how="left")
print({"engine_b_latest_rows": len(x), "joined_with_pick": int(j["pick"].notna().sum())})
PY
```

### CFBD and current v3 missing classes

```bash
rg -n --glob '*.py' 'collegefootballdata|/stats/|/ppa/|/wepa/|/roster|/teams' scripts src
.venv/bin/python3.14 - <<'PY'
import pandas as pd
d = pd.read_csv("app/data/training/prospects_with_outcomes_v3.csv", low_memory=False)
for c in ("transfer_portal_flag","yprr_college","rb_10_yard_split","rb_ras_composite","wr_ras_composite","te_ras_composite","wr_rec_tds_per_game_final","te_deep_yard_share","qb_sack_rate_final"):
    pos = c[:2].upper()
    x = d[d.position.eq(pos)] if pos in {"QB","RB","WR","TE"} else d
    print(c, int(x[c].notna().sum()), len(x))
PY
```

### FantasyCalc and market stores

```bash
jq '{rows:(.data|length),entry_keys:(.data[0]|keys),player_keys:(.data[0].player|keys),ttl_hours}' app/cache/fantasycalc/market_values.json
sqlite3 -header -column app/data/fc_forward_capture.db \
  'select source,count(*) rows,count(distinct snapshot_date) days from fc_forward_capture_raw group by source;'
sqlite3 -header -column app/data/fc_snapshots.db \
  'select source,count(*) rows,count(distinct snapshot_date) days from fc_snapshots group by source;'
```

### PlayerProfiler, PFF, MFL, and fixture-only sources

```bash
jq -r '[.[].status] | group_by(.) | map({status:.[0],count:length})' app/data/cache/pp_probe_results.json
jq '{total,coverage,pp_unresolved}' app/data/cache/enrichment_report.json
find . -type f \( -iname '*pff*' -o -iname '*rotoviz*' -o -iname '*campus2canton*' -o -iname '*ras*' \) -not -path './.git/*' -not -path './.venv/*' -print
find app/cache -maxdepth 3 -type f -print
rg -n 'fetch_rookie_adp_rows|mfl_rookie_adp|load_manual_export|fetch_ras_context' app scripts src
```

### Sleeper CDN assets

```bash
jq '{generated_at,count:(.entries|length),statuses:([.entries[].status]|group_by(.)|map({status:.[0],count:length}))}' app/data/assets/headshot_manifest.json
```

### Databricks enumeration without access

```bash
rg -n -i 'gen_alpha\.(bronze|silver|gold)\.' infrastructure scripts src resources --glob '*.{py,sql,md}'
```

### Declared cadence only

```bash
jq '.stores[] | {store_id,expected_cadence,scheduled_time_local}' app/config/capture_cadence.json
jq '.artifacts[] | {artifact_id,cadence,scheduled_time_local}' app/config/report_freshness.json
rg -n 'freshness_hours=' src/dynasty_genius/sources/source_registry.py
```
