# Phase 17 Research Brief — Sleeper Universe Valuation & League Opportunity Map

## 1. Executive Recommendation

Phase 17 should move Dynasty Genius from query-time valuation to a continuously refreshed league intelligence layer. The system should ingest the full Sleeper universe, produce a governed Player Value Object (PVO) batch for every relevant asset, aggregate those values into a team-by-position matrix, and then use market overlays and roster-fit logic to surface opportunity cards.

The sequencing matters. Ship universe coverage and full PVO batch artifacts before any opportunity language. Team value should use starter-weighted xVAR with diminishing depth credit, not raw value sums. Market divergence should remain overlay-only and gated; FantasyCalc can expose pricing asymmetry, but it must not train Engine A or Engine B. Future picks should be reconstructed for ownership context but not numerically valued in Phase 17.

Phase 17 should be built as five gated sub-phases:

1. **17.1 Universe Snapshot & Coverage** — Sleeper player universe, league rosters, users, traded picks, draft state, and coverage report.
2. **17.2 Full PVO Batch** — batch assembly with explicit engine routing and PRE_MODEL/INACTIVE/UNRESOLVED handling.
3. **17.3 Team Value Matrix** — team-by-position value, starter-weighted xVAR, depth credit, age profile, roster posture, and deferred pick context.
4. **17.4 Market Divergence v2** — full-universe FantasyCalc overlay, TE hardcode cleanup, validation gates, and market-leakage guardrails.
5. **17.5 League Opportunity Map** — partner ranking and evidence cards; `decision_supported` remains `false` in Phase 17 outputs.

The highest-leverage product outcome is not a UI. It is a daily, reproducible artifact set that tells David which teams have surplus, which assets are likely mispriced, and where trade or waiver opportunities may exist across the entire league.

## 2. Phase 17 Objective

Produce a continuously refreshed, governed valuation of every relevant Sleeper player and every roster in David's Superflex PPR league. The output should help David identify trade, waiver, roster, and market-timing opportunities year-round without compromising the system's core rule: market data is price discovery, not model truth.

The first target league is Redzone Champions League:

- Platform: Sleeper
- Format: 12-team Superflex PPR
- League ID: `1314363401744416768`
- Use case: all-year dynasty asset management, not a seasonal draft-only tool

## 3. Key Findings

1. **Sleeper is sufficient for the universe and league context, but not for complete identity.** `GET /v1/players/nfl` provides the player universe and stable Sleeper IDs. League rosters, users, draft state, and traded picks provide roster context. Cross-source IDs still require the Dynasty Genius identity layer and nflverse/ff_playerids-style crosswalks.

2. **Sleeper does not provide a complete "all picks owned" endpoint.** `GET /v1/league/{league_id}/traded_picks` provides traded-pick records, not a full future-pick inventory. Phase 17 should reconstruct future-pick ownership by initializing the league's baseline pick allocation and applying traded-pick deltas. Values remain deferred.

3. **A full PVO batch is a prerequisite for league intelligence.** Current surfaces value selected cohorts. Phase 17 should produce a full-universe artifact so Trade Lab, roster audit, waiver scan, team-value matrix, and opportunity mapping all read from the same valuation layer.

4. **Raw value summation is misleading.** A team with many replacement-level bench players should not outrank a team with elite starters. Team-level value should use starter-weighted xVAR, capped total xVAR, and diminishing depth credit.

5. **FantasyCalc should be a market overlay and divergence suppressor/enabler, not a model input.** FantasyCalc values can support percentile-based divergence. FantasyCalc volatility/MSTD should suppress confidence when the market is unstable.

6. **The TE divergence hardcode is stale.** The current divergence path still forces TEs to `model_unreliable` even though TE was promoted to ACTIVE_B. Phase 17.4 should remove the hardcoded TE suppression and route TE through the same gate framework as other positions, with temporary review labeling.

## 4. Sleeper Universe Ingestion Design

### Endpoints

| Endpoint | Role | Suggested Cadence |
|---|---|---|
| `GET /v1/players/nfl` | Full Sleeper player universe and player metadata | Daily |
| `GET /v1/league/{league_id}` | League settings, roster positions, scoring | Daily; on settings change |
| `GET /v1/league/{league_id}/rosters` | Roster membership, starters, taxi, reserve/IR | 4x/day offseason; hourly in active windows; 15 min gameday if needed |
| `GET /v1/league/{league_id}/users` | Roster owner and display metadata | Daily |
| `GET /v1/league/{league_id}/traded_picks` | Traded future-pick records | Daily |
| `GET /v1/league/{league_id}/transactions/{week}` | Trade/waiver activity and manager activity recency | Hourly during active windows |
| `GET /v1/draft/{draft_id}` | Draft status and metadata | During draft; daily otherwise |
| `GET /v1/draft/{draft_id}/picks` | Current draft pick state | 30 seconds during active draft; final freeze when complete |
| `GET /v1/state/nfl` | NFL season, week, season phase | Daily |

Sleeper's player endpoint is bulk-oriented. Phase 17 should not hammer it repeatedly. Pull it once per day, hash it, and diff against the previous snapshot.

### Inclusion Rules

A Sleeper player enters the Phase 17 valuation universe if any of these are true:

- position is `QB`, `RB`, `WR`, or `TE`
- player appears on any league roster
- player appears in the current rookie draft state
- player appears in a relevant prospect/rookie identity file
- player has a market overlay and is fantasy-relevant

Exclude or mark context-only:

- team defenses, kickers, IDP, coaches, and non-rostered positions
- retired players unless they still appear on a league roster
- dormant free agents with no fantasy relevance
- malformed Sleeper pseudo-players

Do not silently drop excluded rows. Coverage reports should include counts for retained, context-only, inactive, and excluded cohorts.

### Identity Strategy

Use Sleeper `player_id` as the Phase 17 universe key because Sleeper owns the league, roster, draft, and transaction context. Do not treat it as the permanent canonical identity.

Each row should attempt to attach:

- Sleeper `player_id`
- DG canonical `player_id` if available
- GSIS ID if available
- PFR ID if available through crosswalk
- PFF/PlayerProfiler IDs only through governed identity mapping
- unresolved reason if mapping fails

No fuzzy production matching. Fuzzy candidates may be generated for review queues only.

### Failure Modes

Phase 17 should explicitly handle:

- free-form Sleeper `status` strings
- retired players still appearing as active
- missing or empty source IDs
- duplicate names
- players with position changes
- practice squad, PUP, NFI, IR, suspended, retired, inactive, and free-agent statuses
- new rookies appearing in Sleeper before crosswalks update
- stale `news_updated` fields that are not authoritative event timestamps

## 5. Future Pick Ownership Reconstruction

Sleeper exposes traded picks, not a complete future-pick portfolio per roster. Phase 17 should reconstruct ownership but defer numeric pick valuation.

Recommended algorithm:

1. Read league settings to determine rookie draft rounds and eligible future seasons.
2. Initialize baseline picks for every roster:
   - for each eligible future season defined in step 1, one pick per roster per round
   - original owner = roster ID
   - current owner = original owner
3. Load `/league/{league_id}/traded_picks`.
4. For each traded-pick record, match by season, round, and original roster ID.
5. Update current owner to the record's current owner.
6. During an active draft, reconcile current-year picks against `/draft/{draft_id}/picks` so converted player assets are not double-counted as picks.
7. Emit picks with `pick_value_status: "deferred"`.

Phase 17 should not assign numeric xVAR, DVS, or market value to future picks. It should preserve ownership context so opportunity cards can reason about rebuild posture and future optionality without pretending pick valuation is solved.

## 6. Full-Universe PVO Artifact Design

Artifact:

- `app/data/valuation/universe_pvo_{run_id}.json`
- `app/data/valuation/universe_pvo_latest.json`
- paired coverage report in JSON and Markdown

Each row should include:

```json
{
  "schema_version": "universe_pvo.v1",
  "pipeline_run_id": "phase17-20260517-000000",
  "captured_at": "2026-05-17T00:00:00Z",
  "sleeper_player_id": "6794",
  "dg_player_id": "example_player_id",
  "identity_status": "resolved",
  "identity_ids": {
    "gsis_id": "00-0036322",
    "pfr_id": null,
    "pff_id": null,
    "espn_id": "4262921"
  },
  "player": {
    "full_name": "Example Player",
    "position": "WR",
    "team": "MIN",
    "age": 26.9,
    "years_exp": 6,
    "sleeper_status": "Active",
    "dg_status": "ACTIVE"
  },
  "league_context": {
    "rostered": true,
    "roster_id": 4,
    "owner_user_id": "example",
    "in_starters": true,
    "on_taxi": false,
    "on_ir": false
  },
  "valuation": {
    "engine_path": "ENGINE_B",
    "valuation_status": "MODEL_SUPPORTED",
    "dynasty_value_score": 88.4,
    "xvar": 6.21,
    "xvar_percentile_overall": 0.97,
    "xvar_percentile_position": 0.98,
    "model_version": "engine_b",
    "feature_completeness": 0.96,
    "decision_supported": false
  },
  "market_overlay": {
    "source": "fantasycalc",
    "market_value": 10726,
    "market_percentile": 0.998,
    "market_trend_30d": -144,
    "market_volatility": 0.06,
    "as_of": "2026-05-17T00:00:00Z"
  },
  "divergence": {
    "signal": "INSIDE_BAND",
    "signal_status": "inside_band",
    "model_percentile": 0.97,
    "market_percentile": 0.998,
    "delta": -0.028,
    "noise_band": 0.10,
    "decision_supported": false,
    "notes": []
  },
  "lineage": {
    "sleeper_snapshot_hash": "sha256:...",
    "fantasycalc_snapshot_hash": "sha256:...",
    "governance_version": "1.0.0"
  }
}
```

### Engine Routing

Use explicit route labels:

- `ENGINE_A` — rookies/prospects with enough draft/age/feature data
- `ENGINE_B` — active NFL players with enough Engine B feature data
- `BLEND_AB` — players in transition where Engine A prior and Engine B evidence both apply
- `PRE_MODEL` — known player, insufficient features
- `MARKET_ONLY` — market overlay exists but model features are insufficient
- `INACTIVE` — out of scope for current valuation but retained for lineage/context
- `UNRESOLVED_IDENTITY` — cannot safely map identity
- `CONTEXT_ONLY` — retained for league context but not scored

### Valuation Status

Use valuation status labels that do not collide with the governance-level `decision_supported` field:

- `MODEL_SUPPORTED` — a model-backed DVS/xVAR exists and feature coverage is adequate for comparison.
- `MODEL_UNCERTAIN` — model-backed value exists, but uncertainty/caveats require restraint.
- `PRE_MODEL` — known player, insufficient features.
- `CONTEXT_ONLY` — retained for league/team context but not model-scored.
- `MARKET_ONLY` — market overlay exists, but no model-backed value.
- `INACTIVE` — retained for lineage but excluded from current active valuation.
- `UNRESOLVED_IDENTITY` — identity cannot be safely joined.

In Phase 17, `decision_supported` stays `false` in artifacts even when `valuation_status == "MODEL_SUPPORTED"`. The status says the model can support analysis; it does not authorize decision-grade recommendations.

### Coverage Gates

Before league opportunity artifacts run:

- 100% of rostered players appear in the universe artifact.
- 100% of David's roster is at least `CONTEXT_ONLY`.
- unresolved identity count is published, never silently zeroed.
- unresolved identity count for top-300 fantasy-relevant assets must be zero before team-value or opportunity artifacts can be treated as complete. Define top-300 by FantasyCalc dynasty Superflex market value when market data is available, falling back to DG xVAR when market data is unavailable.
- all rostered `QB/RB/WR/TE` players are assigned one of the explicit engine routes.
- market overlay fields are absent from Engine A/B feature inputs.

## 7. Team-Level Roster Valuation Design

### Core Principle

Do not sum raw values and call that team strength. Dynasty rosters are constrained by starting lineup, scarcity, roster churn, taxi rules, and replacement level. Phase 17 should compute multiple views:

1. **Starter-weighted xVAR** — primary team-strength view.
2. **Total capped xVAR** — sum only positive or capped value, not raw depth spam.
3. **Top-N positional xVAR** — position-specific concentration.
4. **Market-overlay total** — diagnostic only, never truth.
5. **Age profile** — value-weighted age and veteran-debt indicators.
6. **Pick context** — future picks owned/lost, no numeric valuation.

### Starter-Weighted xVAR

The starter-weighted view should simulate the best legal lineup from a roster:

- fill required starters first
- fill Superflex with the best remaining eligible QB/RB/WR/TE
- fill flex slots with best remaining RB/WR/TE
- give full credit to starting lineup players
- apply diminishing returns to bench value
- cap or heavily discount sub-replacement players

Bench depth credit should use a configurable coefficient, such as:

```text
depth_credit = max(0, xvar - bench_replacement_xvar) * decay ^ bench_rank
```

The exact decay coefficient should be an open decision for David.

### Taxi Squad Treatment

Taxi players are not zero-utility assets. In David's league, a taxi player can be promoted during the season and used in the active lineup. However, promotion is irreversible:

- once promoted, the player cannot return to the taxi squad
- the taxi slot remains empty for the rest of the season
- David must create an active roster spot, usually by dropping or moving another player

Phase 17 should represent taxi players with two separate values:

- `dynasty_xvar`: full long-term value
- `current_year_utility_xvar`: discounted value after applying taxi activation cost

Recommended fields:

```json
{
  "on_taxi": true,
  "taxi_eligible": true,
  "taxi_promotable": true,
  "taxi_activation_cost": "requires_active_roster_spot_and_irreversible_taxi_loss",
  "starter_weight_multiplier_current_year": 0.0,
  "long_term_value_multiplier": 1.0
}
```

The default current-year starter multiplier can be zero for team-strength calculations unless the player is already a clear lineup upgrade. Opportunity cards may still flag a taxi player as an activation candidate when the xVAR gain exceeds the activation cost.

### IR / Reserve Treatment

IR players retain full long-term dynasty value but have reduced or zero current-year lineup utility depending on injury status and expected return. Phase 17 should separate:

- long-term value
- current-year utility
- return-timeline caveat
- roster-slot relief

### Position Surplus / Deficit

For each team, compute positional z-scores relative to league averages:

- QB surplus/deficit
- RB surplus/deficit
- WR surplus/deficit
- TE surplus/deficit

Use starter-weighted xVAR as the primary signal. Suggested labels:

- `surplus` if z-score > +0.75
- `deficit` if z-score < -0.75
- `neutral` otherwise

Thresholds are configurable and should be reviewed after the first full run.

### Team Value Object

```json
{
  "schema_version": "team_value.v1",
  "league_id": "1314363401744416768",
  "roster_id": 1,
  "owner": {
    "user_id": "example",
    "display_name": "David",
    "team_name": "Woodbury Riders"
  },
  "team_value_views": {
    "starter_weighted_xvar": 41.2,
    "total_xvar_capped": 58.0,
    "top_n_xvar": 36.8,
    "market_overlay_total": 41250
  },
  "positional_summary": {
    "QB": {"n_rostered": 3, "starter_xvar": 8.4, "depth_xvar_adj": 0.6, "surplus_label": "deficit"},
    "RB": {"n_rostered": 8, "starter_xvar": 12.1, "depth_xvar_adj": 3.2, "surplus_label": "surplus"},
    "WR": {"n_rostered": 9, "starter_xvar": 15.0, "depth_xvar_adj": 4.1, "surplus_label": "neutral"},
    "TE": {"n_rostered": 3, "starter_xvar": -1.2, "depth_xvar_adj": 0.3, "surplus_label": "deficit"}
  },
  "age_profile": {
    "value_weighted_age": 24.3,
    "median_age": 25.1,
    "pct_value_over_28": 0.12
  },
  "future_picks": {
    "owned": [
      {"season": 2027, "round": 1, "original_roster_id": 1, "pick_value_status": "deferred"}
    ],
    "outgoing": []
  },
  "posture": {
    "label": "REBUILD",
    "score": -0.71,
    "manual_override_allowed": true
  }
}
```

## 8. Market Divergence v2

### Core Design

Divergence should compare model percentile to market percentile, never raw DVS/xVAR to raw market value. FantasyCalc's numeric scale is not commensurable with Dynasty Genius xVAR.

Recommended streams:

- **Veteran divergence**: Engine B / blend players, compared by overall or position percentile.
- **Rookie/prospect divergence**: Engine A players, compared within rookie/prospect market cohorts when market data exists.
- **Unavailable**: no market match, stale data, insufficient cohort, PRE_MODEL, or unresolved identity.

### Signals

Use neutral, evidence-first labels:

- `MODEL_HIGH_MARKET_LOW`
- `MODEL_LOW_MARKET_HIGH`
- `INSIDE_BAND`
- `UNAVAILABLE`
- `SUPPRESSED_VOLATILE_MARKET`
- `SUPPRESSED_SMALL_COHORT`
- `SUPPRESSED_STALE_MARKET`
- `UNRESOLVED_IDENTITY`

Avoid imperative language:

- Do not emit imperative action labels.
- Do not frame any Phase 17 row as an instruction to transact.
- Do not describe an asset as a target or fade in the schema.

The user-facing language can be:

- "model ranks above market consensus"
- "market ranks above model consensus"
- "asymmetry observed; insufficient validation"

### Validation Gates

In Phase 17, validation gates control `signal_status`, not `decision_supported`. The signal may be structurally valid while the card remains non-decision-grade.

Explicit `signal_status` values:

- `inside_band` — `|delta| < NOISE_BAND`; gates are not evaluated.
- `gates_passed` — `|delta| >= NOISE_BAND + margin` and all gates pass.
- `gates_blocked` — threshold is met but one or more gates fail; `divergence.notes` records the failed gates.
- `unavailable` — no market data, unresolved identity, PRE_MODEL status, or another prerequisite is missing.

Set `signal_status="gates_passed"` only if all relevant gates pass:

1. player has a model-backed valuation status
2. market data is fresh
3. absolute percentile delta exceeds noise band plus margin
4. market volatility is below threshold
5. cohort size is adequate
6. identity is resolved
7. player status is not inactive/context-only

If any gate fails, set `signal_status="gates_blocked"` and record the failed gates in `divergence.notes`.

`decision_supported` remains `false` for Phase 17 outputs. Promotion to decision-supported opportunity language requires a later validation/governance decision.

### Staleness And Volatility Suppression

FantasyCalc market data must suppress confidence when stale or volatile:

- if market data is older than the approved freshness threshold, emit `SUPPRESSED_STALE_MARKET`
- if FantasyCalc volatility/MSTD exceeds threshold, emit `SUPPRESSED_VOLATILE_MARKET`
- stale or volatile market rows may still appear in the artifact for transparency, but they cannot trigger opportunity-card confidence

Default staleness threshold should be 72 hours for divergence signals, with the final threshold left as an open decision for David.

### Noise Band

`NOISE_BAND = 0.10` is already locked until mid-July 2026. Phase 17 may record actual full-universe flag distribution, but it should not silently tune the band without a validation note.

Rookie-specific noise-band expansion may be evaluated, but should remain an open decision until observed rookie market coverage and volatility are known.

### TE Hardcode Cleanup

Phase 17.4 should remove the hardcoded TE path that forces `model_unreliable` solely because `position == "TE"`.

Replacement behavior:

- route TE through normal ACTIVE_B divergence gates
- add `TE_REVIEW=true` metadata for the first two weekly artifact runs
- suppress TE only when an explicit gate fails
- record the failed gate in `divergence.notes`

Acceptance:

- no TE row is marked unreliable solely because it is a TE
- any TE suppression is traceable to stale market, small cohort, volatility, unresolved identity, or model status

### Market Leakage Guard

Add a guardrail test that fails if market overlay modules are imported by Engine A/B training or feature-building code. Current tests already enforce market-overlay separation; Phase 17 should extend them to the new batch pipeline.

## 9. League Opportunity Map Design

Phase 17.5 should combine team matrix, roster posture, and divergence into opportunity cards.

Opportunity cards should answer:

- Which teams have a positional surplus?
- Which teams have a positional deficit?
- Which teams are natural trade partners for David?
- Which players does Genius value differently from market?
- Which assets fit or mismatch a team's contender/rebuild posture?
- Which taxi or IR players have asymmetric long-term value?

### Opportunity Card Schema

```json
{
  "schema_version": "opportunity.v1",
  "card_id": "opp-20260517-0001",
  "card_type": "ROSTER_FIT_ASYMMETRY",
  "perspective_roster_id": 1,
  "counterparty_roster_id": 8,
  "counterparty_team_name": "Example Team",
  "asset": {
    "sleeper_player_id": "11534",
    "dg_player_id": "example",
    "position": "WR"
  },
  "rationale": {
    "primary": "POSITIONAL_SURPLUS_ON_COUNTERPARTY",
    "secondary": ["COUNTERPARTY_DEFICIT_MATCH", "MODEL_MARKET_ASYMMETRY"],
    "evidence": {
      "counterparty_wr_surplus_z": 1.4,
      "counterparty_rb_deficit_z": -1.1,
      "david_wr_deficit_z": -0.9,
      "market_delta": 0.14
    }
  },
  "score_components": {
    "fit_score": 0.85,
    "divergence_score": 0.62,
    "feasibility_score": 0.88
  },
  "opportunity_score": 0.78,
  "signal_status": "gates_blocked",
  "decision_supported": false,
  "caveats": ["market_overlay_age_days=2", "cohort_size=42"]
}
```

An opportunity card's `opportunity_score` is composite and may be high even when `signal_status="gates_blocked"`. Roster fit, positional asymmetry, and feasibility can justify surfacing a card even when market divergence cannot be confirmed.

Initial card types:

- `DIVERGENCE_MODEL_HIGH`
- `DIVERGENCE_MARKET_HIGH`
- `ROSTER_FIT_ASYMMETRY`
- `ROSTER_SURPLUS_DEFICIT_MATCH`
- `WAIVER_CANDIDATE`
- `DRAFT_DAY_MISMATCH`
- `TAXI_ACTIVATION_CANDIDATE`

Partner ranking:

```text
partner_score =
  complementarity_score
  + divergence_density_score
  + activity_recency_score
  + posture_alignment_score
```

Do not predict trade acceptance probability in Phase 17.

## 10. External Tool Comparison

| Tool | Useful Concept | Do Not Copy |
|---|---|---|
| Dynasty Nerds League Analyzer | team value by position, league-wide roster comparison, contender/dynasty framing | proprietary values as truth |
| KeepTradeCut Power Rankings | anti-spam aggregation philosophy, top-heavy weighting | KTC as production input |
| FantasyCalc | transaction-derived market overlay, volatility/MSTD, public API | market values as model inputs |
| DynastyProcess | open data and ID crosswalk patterns, future pick methodology for later phases | FantasyPros/ECR-derived values as truth |
| DLF Trade Analyzer | package adjustment philosophy, comparable trade framing | closed proprietary values |
| DynastyDaddy | starter value vs total value distinction, Sleeper sync, simulation concepts | coupling Dynasty Genius to ADP source |
| Dynasty Assistant | value-weighted age concept | imported market-value source as truth |

Copy concepts, not values. Dynasty Genius should remain model-native and league-specific.

## 11. Data Source Table

| Source | Endpoint / Export | Role | Refresh Cadence | Governance Status | Failure Behavior |
|---|---|---|---|---|---|
| Sleeper | `/v1/players/nfl` | universe baseline, player metadata | daily | approved source adapter | use prior snapshot, flag stale |
| Sleeper | `/league/{id}` | league settings | daily / settings change | approved | preserve prior, flag stale |
| Sleeper | `/league/{id}/rosters` | roster membership, starters, taxi, IR | active windows hourly; otherwise daily/4x daily | approved | preserve prior, flag stale |
| Sleeper | `/league/{id}/users` | owner/team names | daily | approved | fallback to roster ID |
| Sleeper | `/league/{id}/traded_picks` | future pick ownership deltas | daily | approved context | preserve prior, flag stale |
| Sleeper | `/draft/{id}` + `/picks` | draft state and pick conversion | active draft 30 sec; otherwise daily | approved | degrade, do not block universe |
| Sleeper | `/state/nfl` | season/week context | daily | approved | default to prior state |
| FantasyCalc | Superflex PPR dynasty current values | market overlay | 2x daily or daily | overlay only | mark market unavailable/stale |
| nflverse / ff_playerids | cross-source IDs | identity mapping | weekly | identity layer | unresolved rows to review |
| Engine A/B feature stores | model inputs | scoring | existing cadence | model inputs only | PRE_MODEL/context-only on missing |

## 12. Proposed Artifacts

1. `universe_snapshot_{run_id}.json`
2. `universe_diff_{run_id}.json`
3. `universe_coverage_report_{run_id}.json`
4. `universe_coverage_report_{run_id}.md`
5. `universe_pvo_{run_id}.json`
6. `universe_pvo_latest.json`
7. `team_value_matrix_{run_id}.json`
8. `team_value_matrix_latest.json`
9. `team_value_matrix_{run_id}.md`
10. `market_divergence_{run_id}.json`
11. `market_divergence_latest.json`
12. `league_opportunity_{run_id}.json`
13. `league_opportunity_latest.json`
14. `league_opportunity_{run_id}.md`
15. `phase17_pipeline_manifest_{run_id}.json`

All artifacts should include:

- `schema_version`
- `pipeline_run_id`
- `captured_at`
- source hashes
- source freshness
- governance version
- caveats

## 13. Workstreams And Sequencing

### 17.1 — Universe Snapshot & Coverage

Build Sleeper universe loader, roster/user/traded-pick ingestion, normalized snapshot, universe diff, and coverage report.

Exit criteria:

- every Sleeper player is classified
- every league rostered player is present
- unresolved identity list exists
- no PVO scoring yet required

### 17.2 — Full PVO Batch

Batch eligible players through existing PVO paths with explicit routing. Emit full PVO artifact and coverage report.

Exit criteria:

- all rostered `QB/RB/WR/TE` players are `ENGINE_A`, `ENGINE_B`, `BLEND_AB`, `PRE_MODEL`, `CONTEXT_ONLY`, `INACTIVE`, or `UNRESOLVED_IDENTITY`
- no market fields enter features
- David's roster is fully represented

### 17.3 — Team Value Matrix

Aggregate PVOs to team-level views, including position summary, starter-weighted xVAR, depth credit, age profile, taxi/IR treatment, and deferred picks.

Exit criteria:

- all 12 teams emitted
- bench-stuffing test passes
- taxi activation cost represented
- future picks present but unvalued

### 17.4 — Market Divergence v2

Extend FantasyCalc overlay to full universe, compute percentile divergence, remove stale TE hardcode, and apply validation gates.

Exit criteria:

- market data remains overlay-only
- TE no longer suppressed by position alone
- high-volatility/stale/small-cohort signals are suppressed
- no imperative buy/sell language

### 17.5 — League Opportunity Map

Generate opportunity cards from team complementarity, posture, activity, and market/model asymmetry.

Exit criteria:

- opportunity cards are evidence-backed
- `decision_supported=false` in Phase 17 outputs, even when signal gates pass
- no automated trade execution
- output remains JSON/Markdown

## 14. Acceptance Criteria For Phase 17 Spec

1. Full Sleeper universe snapshot is reproducible and schema-valid.
2. Coverage report includes total Sleeper players, fantasy-relevant players, rostered players, free agents, inactive/context-only players, scored players, PRE_MODEL players, and unresolved identities.
3. Full PVO batch contains one row for every rostered player.
4. Every rostered offensive player has an explicit engine route or explicit blocker.
5. Top-300 fantasy-relevant assets have zero unresolved identities, or the run fails before team-value/opportunity completion.
6. No market-derived fields appear in Engine A/B feature inputs.
7. Team Value Matrix emits all 12 teams.
8. Team value uses starter-weighted xVAR as primary operational view, not raw sums.
9. Bench-stuffing regression test proves many low-value bench players cannot outrank elite starter concentration.
10. Taxi players retain long-term value but carry current-year activation-cost discount.
11. Future picks appear with `pick_value_status: "deferred"` and no numeric value.
12. TE divergence no longer hardcodes `model_unreliable` solely by position.
13. Divergence compares percentiles, not raw FantasyCalc values to xVAR.
14. Opportunity cards avoid imperative buy/sell/target/fade language.
15. `decision_supported` remains `false` in Phase 17 outputs; gates populate `signal_status` and notes instead.
16. All artifacts include schema version, run ID, timestamp, source freshness, and lineage.
17. `signal_status` is restricted to `inside_band`, `gates_passed`, `gates_blocked`, or `unavailable`.

## 15. Risks And Failure Modes

| Risk | Severity | Mitigation |
|---|---|---|
| Sleeper schema changes silently | High | defensive parsing, source hash, coverage alert |
| Sleeper status free text breaks enum assumptions | Medium | internal status mapping with `unknown_status` fallback |
| retired players still appear active | Medium | multi-signal inactive detection |
| rookies appear before crosswalk update | High | Sleeper-keyed row plus unresolved identity coverage |
| market overlay outage | Medium | preserve PVO/team matrix, mark market stale/unavailable |
| market leakage into model path | High | contract tests and import guards |
| TE divergence misfires after hardcode removal | Medium | `TE_REVIEW` metadata and gate reporting |
| team value rewards bench spam | High | starter-weighted xVAR and depth decay |
| future picks imply value despite deferral | Medium | explicit `pick_value_status: "deferred"` everywhere |
| taxi players overcount current-year strength | Medium | activation-cost discount and separate current vs long-term value |
| opportunity cards sound too confident | High | conservative language; `decision_supported=false`; gates populate `signal_status` and notes |
| pick reconstruction misses commissioner/manual edge case | Medium | baseline config, validation report, manual override |

## 16. Explicit Out Of Scope

- Real future-pick valuation model
- KTC production integration
- automated trade offers or messages
- polished web UI
- multi-league support
- IDP, kicker, or defense valuation
- new Engine A/B model features
- model retraining
- automated fuzzy identity resolution
- cross-league trade database
- salary/contract/auction logic

## 17. Open Decisions For David

1. Bench depth decay coefficient: default `0.5`, but `0.4` or `0.6` are defensible.
2. Starter-weighted lineup assumptions: confirm exact Redzone Champions lineup slots.
3. Future-pick baseline: confirm rookie draft rounds and number of future years tradable.
4. Pick reconstruction overrides: should manual commissioner corrections live in a JSON override file?
5. Taxi activation multiplier: default current-year utility discount for taxi players.
6. TE review period: two weekly artifacts or four?
7. Divergence cohort threshold: default 30; tune after actual universe run.
8. Rookie divergence noise band: keep 0.10 initially or test 0.15 as candidate?
9. Opportunity card cap: top 20 per run or all cards above threshold?
10. Contender/rebuild manual override: allow David to override computed posture?
11. FantasyCalc freshness threshold: 72 hours or 7 days?
12. FantasyCalc parameter set: confirm `isDynasty=true&numQbs=2&numTeams=12&ppr=1` matches Redzone Champions exactly.
13. Artifact retention: 365 days recommended for trend analysis.

## 18. Recommended Build Order

Build now:

1. **17.1 Universe Snapshot & Coverage** — no model risk, highest foundation value.
2. **17.2 Full PVO Batch** — gives David the full-read artifact he actually needs year-round.

Build after coverage is reliable:

3. **17.3 Team Value Matrix** — first weekly decision artifact.
4. **17.4 Market Divergence v2** — only after full PVO and team matrix prove stable.

Build last:

5. **17.5 League Opportunity Map** — useful only when valuation and divergence are trustworthy.

Defer future-pick valuation, UI polish, KTC, and automated trade language until Phase 17 artifacts pass acceptance criteria.

---

## 19. Phase 17 Decision Memo: League Intelligence & Opportunity Mapping

**Status:** PM Review / Proposed Defaults for David Approval
**Scope:** Phase 17 Structural Logic
**Constraints:** Read-only; Repo-resident evidence only.

### 1. Bench Depth Decay Coefficient
**Question:** How much credit should a team receive for bench strength (xVAR above replacement) vs. starting lineup concentration?

*   **Status:** Recommended default pending David approval.
*   **Default:** **0.5** (`bench rank weight = 0.5 ** bench_rank_index`). Every rank on the bench provides 50% less xVAR utility than the rank above it. Note: This is a surface display parameter, not a model constant, and can be tuned after the first matrix run without a formal governance review cycle.
*   **Counter-Argument:** A higher coefficient (e.g., 0.7) better reflects the "dynasty insulation" value of depth in leagues with deep benches and IR slots.
*   **Governance Risk:** A coefficient that is too high rewards "bench stuffing" and hides a weak starting core.
*   **Revisit Trigger:** If the first matrix run places a depth-heavy team above a top-heavy team.

### 2. Pick Reconstruction Overrides
**Question:** Should we rely purely on Sleeper logic or implement a manual override file?

*   **Status:** Recommended default pending David approval.
*   **Recommended Default:** **Automated Reconstruction Only**. Add manual override capability as a named follow-up *if and only if* a confirmed discrepancy surfaces during Phase 17.1.
*   **Counter-Argument:** A manual override file provides a critical safety net for known Sleeper inconsistencies. Without it, a known pick-inventory mismatch would block Phase 17 outputs until code changes are made.
*   **Governance Risk:** Silent errors in pick ownership can lead to "League Opportunity" cards suggesting trades with assets that David does not actually own.
*   **Revisit Trigger:** Any instance where the `team_value_matrix` disagrees with the Sleeper UI.

### 3. Divergence Noise Band
**Question:** What threshold should we use to suppress "noise" in the model-vs-market percentile delta?

*   **Status:** Recommended default pending David approval.
*   **Default:** **0.10** (Global).
*   **Counter-Argument:** A wider band (0.15) for rookies would prevent "False Positives" in the high-volatility window post-draft.
*   **Governance Risk:** Reducing the band increases the risk of "Market Leakage" or reacting to temporary hype cycles.
*   **Revisit Trigger:** If the first full-universe run surfaces more than 20% of the league as "Divergent." (Note: The rookie-exception argument belongs in a later bake-off, not a Phase 17 spec. It should be added to the Phase 17 follow-up list.)

### 4. FantasyCalc Parameter Confirmation
**Question:** Which specific FantasyCalc API parameters should define our market overlay reference?

*   **Status:** Recommended default pending David approval.
*   **Recommended Default:** `isDynasty=true & numQbs=2 & numTeams=12 & ppr=1`.
*   **Verified Context:** Repo-resident `david_league_context.json` confirms `te_premium: 0.0`. `ppr=1` is correct.
*   **Counter-Argument:** Using a generic "PPR" parameter may mismatch market valuation if league-specific bonuses (like TEP) were present.
*   **Governance Risk:** Using the wrong market reference (e.g., 1QB vs. 2QB) will generate massive, false "Divergence" signals.
*   **Validation Dependency:** Claude/Codex should confirm Sleeper league settings during Phase 17.1 implementation before locking market-overlay params.
*   **Revisit Trigger:** Any discovered scoring mismatch, league setting change, or FantasyCalc API parameter change.

---

**These are proposed Phase 17 defaults for David approval.** They remain research/spec guidance only until David approves implementation and Claude/Codex execute the governed closeout and Phase 17.1 work.
