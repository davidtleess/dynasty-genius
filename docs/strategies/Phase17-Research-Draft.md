# Phase 17 Research Brief — Sleeper Universe Valuation & League Opportunity Map

## TL;DR

- **Build Phase 17 as a five-stage governed pipeline (17.1 → 17.5)** anchored on a once-per-day full pull of Sleeper's `/v1/players/nfl` (Sleeper docs: *"The average size of this query is 5MB… You do not need to call this endpoint more than once per day"*), a versioned full-universe PVO artifact, a team-value matrix that uses **starter-weighted xVAR with diminishing-returns depth credit** (never raw sums), and a market-divergence layer that keeps FantasyCalc **strictly overlay-only**. Ship Universe + Coverage (17.1) and full PVO (17.2) **before** any buy/sell language.
- **Resolve the TE hardcode in Phase 17.4 by deleting the forced `model_unreliable` branch** and routing TE through the standard ACTIVE_B veteran path with a temporary `TE_REVIEW=true` label on the first two weekly artifacts. Future picks are preserved from `/league/{id}/traded_picks` but carry `pick_value_status: "deferred"` — no numeric value is assigned in Phase 17.
- **The highest-leverage user-facing deliverable is the Team Value Matrix + Opportunity Cards (17.3 + 17.5)**: they convert per-player edges into actionable trade-partner targeting against the Redzone Champions League (12-team Superflex Full PPR, league_id `1314363401744416768`) — which is the actual product motivation given David's 4-24 Woodbury Riders rebuild.

## Key Findings

1. **Sleeper exposes everything Phase 17 needs but no delta endpoint.** The `/v1/players/nfl` bulk pull (Sleeper docs: *"average size… 5MB"*) is the only player-object source; no `If-Modified-Since`/ETag/`updated_after` parameter exists. Rate limit is documented as *"A general rule is to stay under 1000 API calls per minute, otherwise, you risk being IP-blocked"* — Phase 17's full daily refresh uses fewer than 30 endpoint calls per minute even during live drafts.
2. **`status` is free-form text, not a closed enum.** Observed values include `Active`, `Inactive`, `Injured Reserve`, `Practice Squad`, `PUP`, `NFI`, `Suspended`, `Reserve/Retired`, plus historical `Reserve/COVID-19`. Defenses use the team abbreviation as `player_id` (e.g., `"DET"`); retired players linger as `Active` with stale `team`; `news_updated` is a content-team blurb timestamp, **not** an authoritative event timestamp.
3. **Cross-source IDs on the Sleeper object are limited.** Present: `sportradar_id`, `gsis_id`, `fantasy_data_id`, `espn_id`, `yahoo_id`, `rotowire_id`, `rotoworld_id`, `stats_id`, `swish_id`, `pandascore_id`, `oddsjam_id`, `dl_trading_id`. **Not present**: `mfl_id`, `pfr_id`, `pff_id`, `fantasypros_id`, `cbs_id` — these require joining the nflverse `ff_playerids` crosswalk (12,186 rows × 35 columns; per nflreadr docs, last shown update `2026-01-10 14:34:27 UTC` — no advertised daily SLA).
4. **Every credible league-view tool does anti-spam aggregation.** Per KeepTradeCut's FAQ: *"Just adding up player values isn't enough! Similarly to how our trade calculator adjusts packages based upon the studs/depth in the trade, our power rankings run leagues through an algorithm to weight the top end assets appropriately."* DG must replicate this concept (with DG's own values, never KTC's).
5. **FantasyCalc methodology already gives DG a divergence-suppression signal.** From fantasycalc.com homepage: *"We run millions of real fantasy football trades from our database through an optimization algorithm to calculate trade values and rankings."* From fantasycalc.com/dynasty-research: *"A high MSTD also implies a more volatile player value and a potential for a market swing."* DG should use FantasyCalc's MSTD as a suppress-the-flag input, not a fire-the-flag input.
6. **The TE → `model_unreliable` hardcode is now actively misleading.** Since Phase 15 promoted TE to ACTIVE_B, the hardcode silently drops TEs from any decision-supported divergence flag, which then poisons team-level TE surplus/deficit analysis — the exact thing Phase 17 needs to be reliable.

## Details

### 1. Executive Recommendation

Ship Phase 17 as five sequential sub-phases. Foundation first, language last:

- **17.1 Universe Snapshot & Coverage**: daily Sleeper full pull + league context; emit `universe_snapshot`, `universe_diff`, `coverage_report`. Every Sleeper `player_id` lands in one of seven cohorts (see § 4). No model changes.
- **17.2 Full PVO Batch**: wrap Engine A / Engine B in a batch driver with explicit `engine_path` routing including `BLEND_AB`, `PRE_MODEL`, `MARKET_ONLY`, `INACTIVE`, `UNRESOLVED_IDENTITY`. Emit `universe_pvo`. **No buy/sell.**
- **17.3 Team Value Matrix**: four parallel team views per roster, value-weighted age, surplus/deficit z-scores, contender/rebuild index, future picks preserved with `pick_value_status: "deferred"`.
- **17.4 Market Divergence v2**: extend overlay to full universe, remove TE hardcode, six validation gates, CI lint test forbidding `dg.market.*` imports under `dg.engines.*`.
- **17.5 League Opportunity Map**: partner ranking, opportunity cards with `decision_supported` flag.

### 2. Phase 17 Objective

> Produce a continuously refreshed, governed valuation of every relevant Sleeper player; aggregate by team and position across Redzone Champions League (12-team Superflex Full PPR, league_id `1314363401744416768`); and surface evidence-backed opportunity cards — without compromising the rule that market data is overlay-only and without inventing buy/sell language the underlying validation cannot support.

### 3. Sleeper Universe Ingestion Design

**Endpoints used**

| Endpoint | Role | Cadence |
|---|---|---|
| `GET /v1/players/nfl` | Player universe (~5 MB; ~6,000+ rows incl. retired/inactive) | 1×/day (Sleeper docs limit) |
| `GET /v1/league/{league_id}` | League settings, roster_positions, scoring | 1×/day; on settings change |
| `GET /v1/league/{league_id}/rosters` | 12 rosters, starters, reserve/IR/taxi arrays | 4×/day offseason · hourly during rookie draft · every 15 min gameday |
| `GET /v1/league/{league_id}/users` | Display name, team name | Daily |
| `GET /v1/league/{league_id}/traded_picks` | Future picks (current + up to 3 future seasons per Sleeper Support) | Daily |
| `GET /v1/league/{league_id}/transactions/{week}` | Trades, waivers | Hourly during active windows |
| `GET /v1/draft/{draft_id}` and `/draft/{draft_id}/picks` | Live draft state | 30 s during active picks; otherwise daily |
| `GET /v1/state/nfl` | Active week, season phase | 1×/day |

**No delta endpoint exists.** DG must diff against its own prior snapshot and emit `universe_diff_<ts>.json` (added / removed / mutated fields).

**Inclusion rules.** A player enters the valuation universe if ALL:
- `position ∈ {QB, RB, WR, TE}` (the Redzone Champions roster positions); team defenses excluded by default since the league doesn't roster DEF.
- `status ∉ {"Retired", "Reserve/Retired"}` **OR** player appears on any league roster (then `cohort: "roster_legacy"`).
- `search_rank` is not Sleeper's `9999999` sentinel — unless rostered.

Players outside scoring scope (K, IDP, dormant FAs) are kept as `valuation_status: "context_only"` not silently dropped.

**Refresh cadence by phase**

| Phase | `/players/nfl` | rosters | transactions | drafts |
|---|---|---|---|---|
| Deep offseason (Feb–April) | daily | daily | daily | n/a |
| Pre-draft + rookie draft | daily | hourly | hourly | 30 s active |
| Post-draft → training camp | daily | 4×/day | 4×/day | n/a |
| Preseason | daily | hourly | hourly | n/a |
| Regular season | daily | 4×/day non-game, 15 min gameday | hourly | n/a |
| Playoffs | daily | daily | daily | n/a |

**Identity fields.** Sleeper `player_id` is the Phase 17 universe key. Cross-source IDs known to be on the Sleeper object: `sportradar_id`, `gsis_id`, `fantasy_data_id`, `espn_id`, `yahoo_id`, `rotowire_id`, `rotoworld_id`, `stats_id`, `swish_id`, `pandascore_id`, `oddsjam_id`, `dl_trading_id`. `mfl_id` / `pfr_id` / `pff_id` / `fantasypros_id` are **not** on the Sleeper response and require the nflverse `ff_playerids` crosswalk join.

**Failure modes to handle explicitly:** retired players still marked Active; `""` vs `null` sentinels in ID fields; `fantasy_positions` differing from `position` (FB→RB); defense pseudo-players with team abbrev `player_id`; `news_updated` set when Sleeper posts a blurb (asynchronous, not authoritative); duplicate names (never join by name); free-form `status` strings mapped into a DG-internal enum with `unknown_status` fallback rather than crashing.

### 4. Full-Universe PVO Artifact

Artifact: `artifacts/pvo/universe_pvo_<ISO_TIMESTAMP>.json` + `universe_pvo_latest.json` symlink + paired `.md` coverage report.

```json
{
  "schema_version": "pvo.v1",
  "sleeper_player_id": "6794",
  "dg_canonical_id": "DG-WR-JEFFERSONJ-1999",
  "id_map": {
    "gsis_id": "00-0036322", "sportradar_id": "...",
    "espn_id": "4262921", "pfr_id": null, "pff_id": null,
    "mfl_id": "14836", "fantasypros_id": null
  },
  "identity": {
    "full_name": "Justin Jefferson", "first_name": "Justin", "last_name": "Jefferson",
    "team": "MIN", "position": "WR", "fantasy_positions": ["WR"], "dg_position": "WR",
    "age": 26.9, "birth_date": "1999-06-16", "years_exp": 6,
    "college": "LSU", "height_in": 73, "weight_lb": 195
  },
  "sleeper_status": {
    "raw_status": "Active", "raw_injury_status": null, "dg_status": "ACTIVE",
    "depth_chart_order": 1, "depth_chart_position": "LWR",
    "news_updated_ms": 1747000000000
  },
  "league_context": {
    "rostered": true, "roster_id": 4, "owner_user_id": "...",
    "slot": "WR", "in_starters": true, "on_taxi": false, "on_ir": false
  },
  "valuation": {
    "engine_path": "ENGINE_B", "valuation_status": "DECISION_SUPPORTED",
    "dvs": 88.4, "xvar": 6.21,
    "xvar_percentile_overall": 0.97, "xvar_percentile_position": 0.98,
    "model_version": "engine_b_v2.3.1",
    "feature_completeness": 0.96, "model_uncertainty": 0.11
  },
  "market_overlay": {
    "source": "fantasycalc",
    "settings": "isDynasty=true&numQbs=2&numTeams=12&ppr=1",
    "market_value": 10726, "market_overall_rank": 1, "market_position_rank": 1,
    "market_percentile": 0.998, "market_trend_30d": -144,
    "market_mstd_pct": 0.06, "asof_ms": 1747000200000
  },
  "divergence": {
    "model_percentile": 0.97, "market_percentile": 0.998,
    "delta": -0.028, "noise_band": 0.10,
    "signal": "INSIDE_BAND", "decision_supported": false, "notes": []
  },
  "lineage": {
    "captured_at": "2026-05-17T13:00:00Z",
    "pipeline_run_id": "phase17-20260517-1300",
    "universe_snapshot_hash": "sha256:..."
  }
}
```

**`engine_path` values**: `ENGINE_A` (rookies/prospects) · `ENGINE_B` (active NFL) · `BLEND_AB` (Y2 / just-drafted / late-career; `score = w·B + (1−w)·A`, `w = clip((games_played + 0.5·feature_completeness)/10, 0, 1)`) · `PRE_MODEL` (known player, insufficient features) · `MARKET_ONLY` (only FantasyCalc value, never promoted to input) · `INACTIVE` · `UNRESOLVED_IDENTITY`.

**`valuation_status` cohorts**: `DECISION_SUPPORTED` (uncertainty under threshold; ≥4 weeks data this season or verified ENGINE_A) · `CONTEXT_ONLY` · `PRE_MODEL` · `MARKET_ONLY` · `INACTIVE` · `UNRESOLVED`.

**Minimum coverage gate** before league-wide recommendations:
- ≥ 95% of every league roster slot resolves to a DG canonical ID.
- ≥ 90% of rostered offensive skill players are `DECISION_SUPPORTED` or `CONTEXT_ONLY`.
- 100% of David's roster (Woodbury Riders) is at minimum `CONTEXT_ONLY`.
- `UNRESOLVED` count is explicitly published.

### 5. Team-Level Roster Valuation

**Philosophy.** Never sum raw values. Per KeepTradeCut's FAQ: *"Just adding up player values isn't enough! Similarly to how our trade calculator adjusts packages based upon the studs/depth in the trade, our power rankings run leagues through an algorithm to weight the top end assets appropriately."* DG computes **four parallel team views**:

1. **Starter-Weighted xVAR (primary)**: xVAR across required starter slots filled optimally + diminishing-returns bench credit `Σ max(0, xvar_i − bench_replacement) · 0.5^(rank_within_pos_on_bench − 1)`.
2. **Total xVAR (capped)**: `Σ max(0, xvar_i)`.
3. **Top-N by position**.
4. **Market-overlay total** (FantasyCalc Superflex dynasty): comparison only, never truth.

**Replacement level (12-team Superflex Full PPR).** Starter baseline = last starter at each position across the league (QB24 in Superflex, RB30, WR42, TE12 with flex absorption — confirm in spec). Bench replacement = best non-rostered player at each position from the live universe diff against `/rosters`.

**Superflex math.** Top-N (top-2 QB) view preserves QB2 premium; starter-weighted view fills SF with the best remaining QB/RB/WR/TE (QB almost always wins — correct behavior).

```json
{
  "schema_version": "team_value.v1",
  "league_id": "1314363401744416768",
  "roster_id": 1,
  "owner": {"user_id": "...", "display_name": "...", "team_name": "Woodbury Riders"},
  "record": {"wins": 4, "losses": 24, "ties": 0, "fpts": 2400.5},
  "positional_summary": {
    "QB": {"n_rostered": 3, "starters_used": 2, "starter_xvar": 8.4, "depth_xvar_adj": 0.6, "best_player_id": "..."},
    "RB": {"...": "..."}, "WR": {"...": "..."}, "TE": {"...": "..."}
  },
  "team_value_views": {
    "starter_weighted_xvar": 41.2,
    "total_xvar_capped": 58.0,
    "top_n_xvar": 36.8,
    "market_overlay_total": 41250
  },
  "age_profile": {
    "value_weighted_age": 24.3,
    "median_age": 25.1,
    "pct_value_over_28": 0.12
  },
  "surplus_deficit": {"QB": "deficit", "RB": "surplus", "WR": "neutral", "TE": "deficit"},
  "future_picks": {
    "owned": [
      {"season": "2027", "round": 1, "original_roster_id": 1, "pick_value_status": "deferred"},
      {"season": "2027", "round": 2, "original_roster_id": 8, "pick_value_status": "deferred"}
    ],
    "outgoing": []
  },
  "taxi_ir": {"taxi": ["..."], "ir": ["..."]},
  "contender_rebuild_index": {
    "score": -0.71, "label": "REBUILD",
    "inputs": {"record_z": -1.4, "age_z": -0.9, "starter_xvar_z": -0.8, "pick_capital_z": 0.5}
  },
  "lineage": {"captured_at": "...", "pipeline_run_id": "..."}
}
```

**Value-weighted age** (Dynasty Assistant pattern): `Σ (age_i · max(0,xvar_i)) / Σ max(0,xvar_i)` prevents a no-value aging QB3 from skewing the mean.

**Surplus/deficit** = per-position z-score of `starter_xvar` vs. league mean: `surplus` if z > +0.75, `deficit` if z < −0.75, else `neutral`.

**Future picks**: stored verbatim from `/league/{id}/traded_picks`; all carry `pick_value_status: "deferred"`. Contender/rebuild index treats pick count as a categorical bonus only — no numeric valuation.

### 6. Over/Undervalued Detection (with TE Hardcode Resolution)

Two parallel divergence streams:

- **Veteran divergence** (ENGINE_B + BLEND_AB): `Δ = model_percentile_overall − market_percentile_overall`. Within `|Δ| < NOISE_BAND` (0.10, locked until mid-July 2026) → `INSIDE_BAND`.
- **Rookie/prospect divergence** (ENGINE_A): compare *within-class* percentile (model rookie rank vs. FantasyCalc rookie rank). Rookie market overlays are incomplete; many rookies → `UNAVAILABLE` (not zero).

**Six validation gates before `decision_supported = true`:**
1. `valuation_status == "DECISION_SUPPORTED"`.
2. `market_overlay.asof_ms` within last 7 days.
3. `|Δ| ≥ NOISE_BAND + 0.05`.
4. `market_mstd_pct < 0.40` — FantasyCalc says *"A high MSTD also implies a more volatile player value and a potential for a market swing"*; DG treats high MSTD as a **suppress** signal.
5. Cohort size ≥ 30 at the player's position-and-tier.
6. `sleeper_status.dg_status == "ACTIVE"`.

Only when all six pass does the signal become `MODEL_HIGH_MARKET_LOW` or `MODEL_LOW_MARKET_HIGH` with `decision_supported = true`. Language map:
- `MODEL_HIGH_MARKET_LOW + decision_supported` → *"model favors over market (consider buy window)"*
- `MODEL_LOW_MARKET_HIGH + decision_supported` → *"market favors over model (consider sell window)"*
- `decision_supported = false` → *"asymmetry observed; insufficient validation"*

Never emit imperative "buy" / "sell."

**Preventing market leakage**: A CI lint test (`tests/governance/test_no_market_in_models.py`) asserts no symbol from `dg.market.*` is imported under `dg.engines.a.*` or `dg.engines.b.*`. Build fails on violation.

**TE Hardcode — explicit resolution:**
1. Delete the conditional forcing TE → `model_unreliable` in the Phase 9 divergence engine. TE now routes through the standard ACTIVE_B path identical to RB/WR.
2. Add `TE_REVIEW=true` to TE divergence outputs for the first two weekly artifact runs (label-only, no behavior change).
3. After two clean weeks, drop the flag.
4. Acceptance: TE divergence rows in `universe_pvo_latest.json` never carry `signal == "model_unreliable"` purely from hardcode; any such value traces to an explicit gate failure recorded in `notes`.

This is correct because (a) the hardcode contradicts Phase 15's promotion of TE to ACTIVE_B, (b) it silently poisons team-level TE surplus/deficit analysis, and (c) the six gates already protect against unreliable TE outputs without a position-specific override.

### 7. League Opportunity Map

`artifacts/opportunity/league_opportunity_<ts>.json` + `.md`. Each opportunity card = `(perspective_team, counterparty_team, asset, direction, rationale, score)` tuple.

```json
{
  "schema_version": "opportunity.v1",
  "card_id": "opp-20260517-0042",
  "card_type": "TRADE_TARGET_ACQUIRE",
  "perspective_roster_id": 1,
  "counterparty_roster_id": 8,
  "counterparty_team_name": "...",
  "direction": "ACQUIRE",
  "asset": {
    "sleeper_player_id": "11534",
    "dg_canonical_id": "DG-WR-XYZ",
    "position": "WR"
  },
  "rationale": {
    "primary": "POSITIONAL_SURPLUS_ON_COUNTERPARTY",
    "secondary": ["AGE_PROFILE_MISMATCH", "MARKET_HIGH_VS_MODEL_LOW_FOR_COUNTERPARTY_OLD_VET"],
    "evidence": {
      "counterparty_WR_starter_xvar_z": 1.4,
      "counterparty_RB_starter_xvar_z": -1.1,
      "perspective_WR_starter_xvar_z": -0.9,
      "counterparty_contender_rebuild_label": "CONTENDER",
      "perspective_contender_rebuild_label": "REBUILD"
    }
  },
  "validation_state": "decision_supported",
  "opportunity_score": 0.78,
  "score_components": {
    "fit_score": 0.85, "divergence_score": 0.62, "feasibility_score": 0.88
  },
  "suggested_framing": "Counterparty has WR surplus (z = +1.4) and RB deficit (z = -1.1); perspective is reverse. Asset is age-mismatched for counterparty's contender window.",
  "decision_supported": true,
  "caveats": ["market_overlay_age_days=2", "cohort_size=42"],
  "lineage": {"...": "..."}
}
```

`card_type ∈ {TRADE_TARGET_ACQUIRE, TRADE_TARGET_SEND, BUY_WINDOW_MARKET, SELL_WINDOW_MARKET, WAIVER_TARGET, DRAFT_DAY_MISMATCH}`.

**Partner ranking**: `partner_score(j) = w1·complementarity(i,j) + w2·divergence_density(j) + w3·activity_recency(j)`.

**Output**: JSON + Markdown only per assumption 2. Schema is UI-ready (`card_id`, `score_components`, `caveats`) for a later UI phase.

### 8. External Tool Comparison

| Tool | Methodology | Copy conceptually | Do NOT copy |
|---|---|---|---|
| Dynasty Nerds League Analyzer | Sync Sleeper/ESPN/MFL; per-team value by QB/RB/WR/TE; Dynasty Mode vs Contender Mode | Two-mode lens; positional team breakdown; trade-partner targeting from positional asymmetry | Analyst-set values as truth; their UI as a model |
| KeepTradeCut Power Rankings | Crowdsourced K/T/C; anti-spam top-heavy weighting; orphan/dispersal; multi-platform sync | Anti-spam aggregation philosophy; waiver-best-available concept | KTC as production input (already excluded by constraint); crowdsourcing as the value source |
| FantasyCalc | Per fantasycalc.com: *"We run millions of real fantasy football trades from our database through an optimization algorithm to calculate trade values and rankings"*; MSTD volatility per player; rebuilder/contender modes; open API | MSTD as divergence suppressor; rebuilder/contender modes as team-context input; the open API | Their values as model input — overlay only per hard constraint |
| DynastyProcess | Open data + `ffscrapr` (R) + FantasyPros ECR-based values + 2QB LOESS conversion; rookie picks via Perfect Knowledge + Hit Rate GAM blend | ID crosswalk approach (`db_playerids.csv`); open-data pipeline pattern; rookie-pick blend architecture for a later phase | FantasyPros-ECR-derived values as production input |
| DLF Trade Analyzer | Rankings + ADP + recent trade data; "Package Value Adjustment" for stud-vs-spam imbalance; MFL trade finder | Package adjustment philosophy; surfacing comparable trades as context | Their values as input |
| DynastyDaddy | Open-source; ADP Daddy proprietary values; dual "overall value" + "starter value" power rankings; 10K-season simulation; queues Sleeper trade offers | Dual overall + starter ranking dimensions; season simulation as a future contender/rebuild calibrator | Coupling engine to one ADP source |
| Draft Sharks 3D Value+ | Projection + last 2 yrs production → 3/5/10-yr forecasts → aging curves → cross-position normalization | Multi-horizon projection thinking; explicit per-position aging curves | Closed methodology / scoring opacity |
| Dynasty Assistant | Imports Sleeper/MFL/Fleaflicker; uses DynastyProcess values; value-weighted age | Value-weighted age formula (adopted) | Their value source as production input |

**Net pattern**: every serious league-view tool does (1) anti-spam aggregation, (2) contender vs. dynasty modes, (3) positional surplus/need, (4) surfacing real comparable trades. Phase 17 adopts concepts (1)–(3); (4) is deferred (DG does not crawl other leagues).

### 9. Data Source Table

| Source | Endpoint / Export | Role | Refresh | Governance | Failure Behavior |
|---|---|---|---|---|---|
| Sleeper `/v1/players/nfl` | HTTPS JSON, ~5 MB (Sleeper: *"average size of this query is 5MB"*) | Universe key + identity + status | 1×/day per Sleeper docs | Authoritative for universe membership only; never a valuation input | If 5xx/timeout: keep prior snapshot; raise coverage alert; mark `universe_age_hours` |
| Sleeper `/league/{id}/rosters` | HTTPS JSON | Roster membership, starters, IR/taxi | 4×/day → hourly active | Authoritative for league context | If error: keep prior; alert if >12 h stale during active |
| Sleeper `/league/{id}/traded_picks` | HTTPS JSON | Future pick ownership (current + up to 3 future seasons) | Daily | `pick_value_status: "deferred"` | If error: keep prior |
| Sleeper `/league/{id}/transactions/{week}` | HTTPS JSON | Trade/waiver activity → partner-activity score | Hourly active | Context only | Tolerate gaps |
| Sleeper `/draft/{id}` + `/picks` | HTTPS JSON | Live draft state | 30 s active; daily otherwise | Drives draft-day cards | If error during active: degrade to 5-min; never block other artifacts |
| FantasyCalc `api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1` | HTTPS JSON | Market overlay (per FantasyCalc: algorithm over *"millions of real fantasy football trades"*) | 2×/day | **Overlay only.** Never an Engine A/B input. `sleeperId` is the join key. | If error: divergence layer marks `market_overlay_status: stale`; team views still produced; cards downgraded |
| nflverse `ff_playerids` | CSV/Parquet on GitHub | Cross-source ID crosswalk (mfl/pfr/pff/fantasypros/gsis/sleeper/espn); 12,186 rows × 35 cols per nflreadr (last documented update `2026-01-10 14:34:27 UTC`; no advertised daily SLA) | Pull weekly | Identity layer input; failures → `UNRESOLVED_IDENTITY` | If stale >30 d: alert, continue |
| nflverse `load_players` | CSV/Parquet (24,336 rows) | Authoritative bio (DOB, draft info) for ENGINE_B features | Nightly | Optional enrichment | Tolerate missing rows |
| KeepTradeCut | (deferred) | Future second-overlay candidate | n/a | **Not active production** per constraint | n/a |
| PlayerProfiler / PFF / RAS | Existing feeds | ENGINE_A/B feature inputs | As-is from prior phases | Staleness reported | If missing: feature_completeness drops; may slide to PRE_MODEL |

### 10. Proposed Artifacts and Schemas

All JSON-serializable, Pydantic-friendly. Every artifact carries `schema_version`, `pipeline_run_id`, `captured_at`.

1. `universe_snapshot_<ts>.json` — normalized Sleeper rows (raw + DG fields).
2. `universe_diff_<ts>.json` — added/removed/mutated since prior.
3. `universe_pvo_<ts>.json` — list of PVOs (§ 4).
4. `coverage_report_<ts>.json` + `.md` — cohort counts; UNRESOLVED list with reasons.
5. `team_value_<ts>.json` — array of 12 Team Value Objects (§ 5).
6. `divergence_<ts>.json` — divergence rows.
7. `league_opportunity_<ts>.json` + `.md` — opportunity cards (§ 7).
8. `pipeline_manifest_<ts>.json` — run id, schema versions, source hashes, timing.

### 11. Proposed Workstreams and Sequencing

- **17.1** Universe loader + identity crosswalk + coverage report. Exit: every Sleeper `player_id` in one of seven cohorts.
- **17.2** Batch PVO driver with `engine_path` routing + BLEND_AB rule + PRE_MODEL fallback + MARKET_ONLY tagging. Exit: coverage gates of § 4 met.
- **17.3** Team Value Matrix with four parallel views + value-weighted age + surplus/deficit z-scores + contender/rebuild index + deferred future picks.
- **17.4** Market Divergence v2: full-universe overlay, **TE hardcode removed + `TE_REVIEW` for 2 weeks**, six validation gates, CI lint test for market-leakage prevention.
- **17.5** Opportunity Map: partner ranking + cards; default `decision_supported=false` until validation rate stabilizes.

### 12. Acceptance Criteria for Phase 17 Spec

1. Daily `universe_pvo_latest.json` exists, schema-valid, with a PVO for every rostered player in league_id `1314363401744416768`.
2. Coverage report enumerates all cohorts; UNRESOLVED count is published, not silently zero.
3. Team Value Matrix produces all 12 teams with four views and surplus/deficit labels.
4. TE divergence rows are no longer forced to `model_unreliable` by hardcode; any unreliable signal traces to an explicit gate failure recorded in `notes`.
5. CI lint test passes: no symbol from `dg.market.*` is imported under `dg.engines.*`.
6. Future picks appear with `pick_value_status: "deferred"`; no numeric value assigned.
7. Opportunity cards emit only when `fit_score >= 0.5` and at least one of `divergence_score >= 0.5` or hand-validated rationale.
8. All artifacts include `schema_version`, `pipeline_run_id`, `captured_at`.
9. Markdown reports render the JSON without extra templating logic.
10. End-to-end pipeline run time < 5 minutes on a single laptop.

### 13. Risks and Failure Modes

| Risk | Severity | Mitigation |
|---|---|---|
| Sleeper `/v1/players/nfl` schema changes unannounced | High | Pin to observed field set; tolerate extra/missing; coverage alerts on shape change |
| Retired players appearing `status: "Active"` create false PVOs | Medium | Cross-check `team`, `news_updated`, `years_exp`; demote to INACTIVE on multi-signal confirmation |
| FantasyCalc downtime/rate-limit | Medium | Cache `asof_ms`; degrade divergence layer; do not block team views |
| Identity resolution failures cluster on rookies | High | Surface as `UNRESOLVED_IDENTITY`, not silently dropped; manual-override JSON like nflverse `players_manual_overwrite.json` |
| Market leakage into Engine A/B via accidental refactor | High | CI lint test forbids `dg.market.*` import under `dg.engines.*` |
| Buy/sell language on shaky signal | High | Six-gate validation; default `decision_supported=false` |
| TE post-hardcode behaves badly | Medium | `TE_REVIEW` flag for 2 weeks; manual eyeball |
| Anti-spam aggregation still rewards bench-stuffing | Medium | Diminishing-returns coefficient `0.5^rank`; review after first full team-value run |
| Future picks "look" valued because they exist in JSON | Medium | `pick_value_status: "deferred"` propagates to all surface text |
| Position changes (FB→RB) cause double-counting | Low | Use `fantasy_positions[0]` as `dg_position`; log mismatches |
| Live rookie draft 30 s cadence overruns rate limit | Low | <30 calls/min total; well under Sleeper's *"general rule… 1000 API calls per minute"* |
| Sleeper `status` is free-text not enum | Medium | DG-internal enum mapping with `unknown_status` fallback |

### 14. Out-of-Scope for Phase 17

- Building a real future-pick valuation model (assumption 3; deferred).
- Promoting KTC to active production input.
- Any web UI beyond rendering Markdown.
- Multi-league support (single-user, single-league personal app).
- Adding new Engine A/B model features (Phase 17 is plumbing + aggregation).
- IDP / kickers / team defense valuation (not in Redzone Champions roster_positions).
- Auctions / contracts / salary-cap layers.
- Predicting trade acceptance probability (later phase; cards stop at "likely partner").
- A cross-league trade database mirror (DLF/KTC own this space).

### 15. Open Decisions for David

1. **Bench depth coefficient**: 0.5^rank is a reasonable default; 0.6 or 0.4 are defensible. Pick before 17.3.
2. **Contender/rebuild thresholds**: confirm `|z| > 0.75` and equal-vs-weighted inputs to `contender_rebuild_index`.
3. **Cohort_size threshold for divergence**: 30 is conventional; verify against actual position cohort sizes during 17.4.
4. **TE_REVIEW duration**: 2 weeks suggested. Extend to 4?
5. **FantasyCalc parameter set**: confirm `isDynasty=true&numQbs=2&numTeams=12&ppr=1` matches Redzone Champions exactly.
6. **Identity manual-overwrite file**: ship a `players_manual_overwrite.json` (nflverse pattern) for one-off ID fixes? Recommended **yes**.
7. **Artifact retention**: 365 days recommended (disk is cheap; enables trend analysis).
8. **Opportunity card cap**: 20 per artifact, or unlimited above `opportunity_score >= 0.5`? Recommend **cap of 20**.
9. **REBUILD label override**: with 4-24, auto-classification will land on REBUILD; expose an explicit override field anyway, or trust the index? Recommend **explicit override** so David can flip mid-season.

## Recommendations

**Build now (Phase 17.1):** Universe loader + identity crosswalk + coverage report. This is foundation. No model risk.

**Build next (Phase 17.2):** PVO batch with explicit cohort routing. **Do not surface buy/sell.** Goal is a defensible artifact, not a UI moment.

**Build after coverage gates pass (Phase 17.3):** Team Value Matrix. This is the first artifact David will actually use weekly.

**Build with care (Phase 17.4):** Market Divergence v2. The TE hardcode removal is the single highest-leverage code change because every TE on every team has been silently excluded from team-level divergence math since Phase 15. Add the CI lint test in the same PR — leakage prevention is more important than expansion.

**Build last (Phase 17.5):** Opportunity Map. Without 17.4's gates, the cards are noise. With them, they are the actual product.

**Defer:** future-pick valuation model, KTC, UI, IDP, multi-league. Reopen each only after Phase 17 hits acceptance criteria.

**Thresholds that should change the plan:**
- If after 17.2 the `UNRESOLVED_IDENTITY` count exceeds 8% of rostered players, halt and fix identity before 17.3.
- If after 17.4 fewer than 15% of veterans hit `decision_supported = true`, the noise band or gates are too tight; consult before 17.5.
- If FantasyCalc's API contract or query parameters change, treat as a Sev-1 because the overlay layer cannot degrade gracefully without a working `sleeperId` join.

## Caveats

- Sleeper publishes no formal schema or enum for `status`, `injury_status`, or `position`. Field set described here is from docs.sleeper.com's sample object plus the ffscrapr `sleeper_players()` deserialization. Phase 17 must defensively type-coerce and add an `unknown_status` fallback rather than crashing.
- nflverse `ff_playerids` is community-maintained. Per nflreadr docs, the last shown table refresh is `2026-01-10 14:34:27 UTC`; there is no advertised daily SLA. Sleeper IDs for new rookies often appear before nflverse adds them. Manual override JSON is the standard mitigation.
- FantasyCalc's `value` numeric scale is not commensurable with DG's xVAR; comparisons must be percentile-to-percentile, never absolute-to-absolute. The market overlay layer must enforce this.
- The four "team views" are intentionally redundant. They will disagree. Pick a primary view (starter-weighted xVAR) and treat the others as diagnostic, not authoritative.
- KeepTradeCut and Dynasty Nerds are explicitly **conceptual references** here, not production sources. Any future decision to promote either to overlay status requires its own governance review (and KTC remains excluded by hard constraint).
- This brief takes positions where the source material is consistent (anti-spam aggregation, MSTD suppression, value-weighted age, percentile-based divergence). Where it states thresholds (`0.10` noise band, `0.75` z-score, `30` cohort size, `0.5^rank` bench coefficient), those are defaults to be tuned during implementation, not laws.