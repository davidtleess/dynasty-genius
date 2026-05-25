# Trade Lab Market-Side Reconciliation & Forced-Cut Penalty Design

## TL;DR
- **Build the FantasyCalc/KTC overlay as a strictly side-car module.** A single API endpoint returns `market_sent`, `market_received`, `market_penalty_david`, `market_penalty_counterparty`, and `coverage_gaps`, with every row carrying `decision_supported=False`. xVAR remains the only signal that flows into Engine A, Engine B, and `RosterCutEngine`.
- **For roster-clogger penalties, do NOT reinvent KTC's exponential raw-adjustment.** Model the forced-cut penalty *physically* as `Σ market_value(forced_cut_player_i) × α`, where the forced-cut set is selected by xVAR ascending (not by market value) and α ∈ [0.5, 1.0] is a single tunable "cut realization factor" exposed in config. This stays consistent with how FantasyCalc / KTC / DynastyProcess implicitly penalize consolidation, but cut-candidate selection remains 100% xVAR-driven and never reads `market_value`.
- **FantasyCalc is the only viable bulk source.** KTC has no public API and KTC's FAQ explicitly states "scraping player values and other data from the site is expressly forbidden by our Terms and Conditions." KTC values can only be entered manually for spot-checks. Future picks beyond year+1 R1 should land as `market_value=null` with `coverage_gap=generic_round_only` rather than be imputed.

## Key Findings

### 1. Public calculator behavior for consolidation / roster-clogger penalties
- **KeepTradeCut (KTC)** is the most sophisticated public model and the most transparent because its calculator runs in client-side JS. The decompiled "Value Adjustment" algorithm, published September 30, 2022 by Dave C. on Javelin Fantasy Football, shows KTC does **not** simply sum player values. It computes a hidden **raw adjustment** per player whose shape is approximately exponential in the player's KTC value relative to the best player in the trade (`t`) and the best player overall (`v`, e.g. Josh Allen ≈ 9999). Per Dave C.: *"This means that a player's raw adjustment number is between 10% and 42.4% of the player's KTC value."* KTC's fair-trade condition is **equal sums of raw adjustments**, not equal sums of values — this is what enforces the "four 2024 3rds ≠ a stud WR" intuition. KTC's own FAQ language: *"Trading is more than simple addition. We add value to the side of the trade that's giving up more when you look at roster spots, players' 'stud' factor, etc."* and *"The actual adjustment is reverse engineered from the player the lesser side needs to have added to even the trade."*
- **FantasyCalc** does not publish a consolidation penalty formula; its API returns raw `value` per player/pick and any consolidation logic is left to the consuming UI. FantasyCalc's home page states: *"FantasyCalc is a hobby project by two brothers — a data scientist and data engineer — who combined their skill sets to build fantasy football data tools since 2020."* Values are derived from "millions of real fantasy football trades" (currently advertised as 6,380,559 trades) using an optimization algorithm over Sleeper / MFL / Fleaflicker trade data. Updates run multiple times per day.
- **DynastyProcess** (Tan Ho / Joe Sydlowski) explicitly exposes a **"depth/stud preferences"** slider in its calc, which lets the user tune how star players are valued relative to bench players. Rookie picks blend two models — **Perfect Knowledge** and **Hit Rate** — at a user-adjustable ratio, per DynastyProcess's Market Values documentation: *"Both are GAM models trained on 'what is the dynasty value of a player taken at this draft slot Y1 and Y2' and then blended at a ratio - in the calculator app, the ratio is chosen by the user and otherwise is preset at 80%."*
- **UTHDynasty** (Chad Parsons) explicitly models a **"Free Roster Spot"** value: *"Trades with an uneven number of assets on each side will produce a free roster spot (or multiple) to even out the trade, that roster spot value varies by format and represents the average final roster spot in that league."* This is the closest public analogue to a *cut-cost* model.
- **Dynasty Trade Calculator** (`dynastytradecalculator.com`) exposes an explicit **"Unbalanced Trade Reduction"** toggle: *"Optional value adjustment when a trade offer uses a disproportionate quantity of assets on one side while the 'Total' value may be close on both sides."*
- **Draft Sharks** describes its consolidation logic as *"strips away throw-in players and looks for historical relationships to estimate that tax."*
- **Roster size constraint is not modeled** in any major public calculator. None of the public tools consume the receiver's current roster to estimate which specific players would be cut. They all use **value compression / exponential weighting** as an *implicit* proxy for cut cost. This is precisely the gap Dynasty Genius's roster-aware design fills — and it is also why the market overlay must NOT pretend to do that job; the xVAR pipeline already does.

### 2. FantasyCalc methodology (confirmed)
- **Authorship / provenance**: FantasyCalc is, per its own homepage, "a hobby project by two brothers — a data scientist and data engineer — who combined their skill sets to build fantasy football data tools since 2020." This is relevant because it sets reasonable expectations on API stability, support, and rate-limit policy.
- **Source data**: Real accepted trades from Sleeper, MFL, and Fleaflicker leagues. Counter advertises 6,380,559 trades currently.
- **Algorithm**: Undisclosed proprietary optimization. From FantasyCalc's home page: *"We run millions of real fantasy football trades from our database through an optimization algorithm to calculate trade values and rankings. Automatically updated multiple times per day."*
- **Update cadence**: Multiple times per day during active trade volume; the rankings page also states *"Our draft rankings outperform 91% of experts. We're the only one that updates every 3 hours all season long."*
- **Public API**: `https://api.fantasycalc.com/values/current?isDynasty={bool}&numQbs={1|2}&numTeams={int}&ppr={0|0.5|1}` — free, no auth, no documented rate limit. Confirmed live as of May 2026; response is a JSON array of objects with `player`, `value`, `overallRank`, `positionRank`, `trend30Day`, `redraftValue`, `combinedValue`, `maybeMovingStandardDeviation`, `maybeTier`, and player-side identifiers (`sleeperId`, `mflId`, `espnId`, `fleaflickerId`, `ffpcId`).
- **Superflex vs 1QB separation**: Yes — `numQbs=2` returns a distinct dataset where top QB values are materially elevated. The same canonical player id (e.g. Josh Allen `id=6170`) appears in both, but `value` and ranks differ. Values must be cached per `(isDynasty, numQbs, numTeams, ppr)` tuple — never assume interchangeability.
- **Future picks**: Picks have `position == "PICK"` (string literal) and `sleeperId`/`mflId` null. Naming convention is mixed:
  - **Current year**: exact slot (`"2026 Pick 1.03"`, IDs in the ~16500 block) AND generic (`"2026 1st"`, IDs in the ~9660 block).
  - **Year +1 R1**: Early/Mid/Late split (`"2027 Early 1st"`, `"2027 Mid 1st"`, `"2027 Late 1st"`) AND generic (`"2027 1st"`, `id=9692`).
  - **Year +1 R2–R4**: generic only.
  - **Year +2 and beyond**: generic only (`"2028 1st"` `id=9722`, `"2029 1st"`).
- **Rookies / unproven prospects**: Present in the same dataset as veterans (e.g. Jeremiyah Love `value=6710, overallRank=17, maybeYoe=0`), but `trend30Day` magnitudes for rookies are large and `maybeMovingStandardDeviationAdjusted` is comparatively elevated — useful as a market-thinness signal.
- **Coverage gap to flag**: any forward-year, non-R1 round (e.g., "2027 Mid 2nd" does not exist on FantasyCalc — only "2027 2nd"). Any synthetic asset David carries beyond what FantasyCalc emits should land as `market_value=null`.

### 3. KeepTradeCut (KTC) methodology (confirmed)
- **Source data**: Crowdsourced "Keep/Trade/Cut" 3-player ordinal rankings; 25,688,540+ data points as of May 2026. Aggregation via, per KTC's FAQ: *"an adapted ELO algorithm to process all of the KTCs that are submitted and calculate player values that follow a reasonable distribution on the value spectrum."*
- **Format baseline**: 12-team, 0.5 PPR; 1QB and Superflex maintained as **separate** datasets. KTC FAQ: *"Our values are all based on a vanilla 12 team, .5PPR league, so we don't currently support different league scoring settings (PPR, TE Premium, PPC, 2TE, etc) or adjust values based on starters or league size."* TE Premium is then applied algorithmically as a post-process stepper (Off/TE+/TE++/TE+++).
- **Picks**: KTC includes Early/Mid/Late picks for each round for all future years. From the KTC FAQ verbatim: *"KTC includes Early/Mid/Late picks for each round for future years in our crowdsourced rankings and values. For simplicity's sake, all future draft picks in Power Rankings are assumed to be 'Mid' round picks."*
- **API availability**: **None public.** KTC's FAQ is explicit: *"We don't currenly [sic] have an API or any sort of .csv available for our rankings and values data."* And on scraping: *"please note that scraping player values and other data from the site is expressly forbidden by our Terms and Conditions."* And again: *"scraping player values and other data from the site, using full KTC values in tools/resources, or reproducing our rankings and player values in their entirety is expressly forbidden by our Terms and Conditions."*
- **Update cadence**: Real-time, refreshed every ~6–10 minutes per the live "values updated X minutes ago" UI stamp.
- **Implication for Dynasty Genius**: KTC cannot be used as a programmatic market source. Treat KTC as an *optional manual override* — David can paste a KTC value into a `manual_overrides` table that has read priority over the FantasyCalc value when populated, but no scraper / bulk extractor.

### 4. Architectural separation principles
The only inputs that may flow into Engine A, Engine B, `RosterCutEngine`, or xVAR are:
- Model-native projections, age/positional priors, rookie evaluation features, scoring-rule-adjusted production, depth charts.
- Roster context (positional slots filled, roster cap, IR/taxi flags).

**`market_value` (FantasyCalc or KTC) is excluded from all of those pipelines by design and by contract test.** It exists only in the `MarketOverlayService` and is surfaced in the Trade Lab UI as a clearly-labelled secondary panel.

## Details

### Proposed overlay-only reconciliation model (Trade Lab)

Let `S` = set of assets David sends, `R` = set of assets David receives, `M(a)` = FantasyCalc market value of asset `a` (nullable). Let `C_D` = ordered list of David's CURRENT roster players keyed by xVAR ascending (lowest first), `cap_D` = roster size cap, `n_D` = current roster size.

**Step 1 — Base sums (with explicit null handling):**
```
market_sent      = Σ M(a) for a in S where M(a) is not null
market_received  = Σ M(a) for a in R where M(a) is not null
missing_sent     = [a for a in S if M(a) is null]
missing_received = [a for a in R if M(a) is null]
```

**Step 2 — Forced-cut set selection (xVAR-driven, market-blind):**
```
overflow_D = max(0, (n_D - |S| + |R|) - cap_D)
cut_set_D  = first overflow_D entries of (C_D \ S)
             sorted by xVAR ascending, breaking ties by age desc, then position scarcity
```
> **Critical constraint:** `cut_set_D` is selected entirely by xVAR ordering. `market_value` is not consulted in this step. This is the bright-line rule that preserves xVAR's status as the only decision-supported signal.

**Step 3 — Single-sided forced-cut market penalty (David only):**
```
market_penalty_D = α · Σ M(p) for p in cut_set_D where M(p) is not null
```
- `α` ∈ [0.5, 1.0] is the **cut realization factor**, a single tunable config value. `α = 1.0` treats every forced cut as a full market loss; `α ≈ 0.7` reflects that the deepest bench players often have low market liquidity and that some cut value is recovered via waiver churn. Recommended starting value: **α = 0.7**, anchored above the central tendency of KTC's raw-adjustment ratio for mid-tier dynasty assets per Dave C.'s worked example (CeeDee Lamb 5500 KTC → 1400 raw adj ≈ 25.5%; Joe Mixon 4900 → 1100 ≈ 22.4%; Ja'Marr Chase 8200 → 2900 ≈ 35.4%) and adjusted upward to reflect that the cut player is *physically removed*, not abstractly compressed.
- If `p ∈ cut_set_D` has `M(p) == null`, record it in `coverage_gaps.unpriced_cut_candidates`; do **not** impute a value, do **not** drop the penalty silently — surface it.

**Step 4 — Optional double-sided counterparty penalty (when counterparty roster is known):**
```
If counterparty roster CP is known:
  overflow_CP = max(0, (n_CP - |R| + |S|) - cap_CP)
  cut_set_CP  = first overflow_CP entries of (CP \ R) sorted by xVAR_proxy ascending
  market_penalty_CP = α · Σ M(p) for p in cut_set_CP where M(p) is not null
Else:
  market_penalty_CP = null
  coverage_gaps.counterparty_unknown = True
```
For counterparty cut selection, since Dynasty Genius does not maintain a full xVAR for opposing rosters, **substitute FantasyCalc `value` ascending as the xVAR proxy ONLY for opposing-roster ranking**. This is acceptable because (a) the counterparty side is already labelled `decision_supported=False`, (b) Dynasty Genius does not act on the counterparty's behalf, and (c) it is the only computationally feasible ordering.

**Step 5 — Adjusted overlay outputs:**
```
adj_market_received = market_received - market_penalty_D
adj_market_sent     = market_sent     - (market_penalty_CP or 0)
overlay_delta       = adj_market_received - adj_market_sent
```

**Step 6 — Coverage gap surfacing:**
```
coverage_gaps = {
  unpriced_sent: [...],
  unpriced_received: [...],
  unpriced_cut_candidates: [...],
  counterparty_unknown: bool,
  synthetic_picks: [picks where year > current_year+1 AND round > 1],
  thin_market_rookies: [players where maybeMovingStandardDeviationAdjusted >= 6
                        OR |trend30Day| > 30% of value]
}
```

### API contract — `POST /trade-lab/market-overlay`
Request:
```json
{
  "sent_assets":     [{"asset_type":"player","sleeper_id":"12527"}, {"asset_type":"pick","year":2027,"round":1,"slot":"mid"}],
  "received_assets": [{"asset_type":"player","sleeper_id":"4984"}],
  "league_format":   {"is_dynasty":true,"num_qbs":2,"num_teams":12,"ppr":1.0},
  "include_counterparty":false
}
```
Response (every field includes `decision_supported=False` provenance flag):
```json
{
  "decision_supported": false,
  "market_source": "fantasycalc",
  "market_snapshot_ts": "2026-05-25T14:00:00Z",
  "sent":     [{"label":"Ashton Jeanty","market_value":8145,"source":"fantasycalc"},
               {"label":"2027 Mid 1st","market_value":null,"coverage_gap":"generic_round_only"}],
  "received": [{"label":"Josh Allen","market_value":6089,"source":"fantasycalc"}],
  "market_sent_raw":     8145,
  "market_received_raw": 6089,
  "forced_cut_david": {
    "overflow": 0,
    "cut_set": [],
    "penalty": 0,
    "alpha": 0.7
  },
  "forced_cut_counterparty": null,
  "adj_market_received": 6089,
  "adj_market_sent":     8145,
  "overlay_delta":       -2056,
  "coverage_gaps": { ... },
  "caveats": [
    "Overlay is price discovery only and is NEVER input to xVAR, Engine A, Engine B, or RosterCutEngine.",
    "FantasyCalc 2027 Mid 1st: FantasyCalc only exposes a generic '2027 1st'; no mid-slot value available — market_value left null.",
    "KTC value cannot be auto-fetched; KTC's Terms of Service forbid scraping."
  ]
}
```

### Schema / data model

Add a single new table `market_values` keyed by `(source, asset_id, format_key, snapshot_ts)`:
```
market_values (
  source              VARCHAR  -- "fantasycalc" | "ktc_manual"
  asset_id            VARCHAR  -- canonical (sleeper_id for players; synthetic key for picks)
  asset_type          VARCHAR  -- "player" | "pick"
  format_key          VARCHAR  -- e.g. "dyn_sf_12tm_1ppr"
  value               INT
  trend_30d           INT
  std_dev_adj         INT
  snapshot_ts         TIMESTAMP
  decision_supported  BOOLEAN  -- HARD-CODED FALSE; column exists for audit
)
```
And a `pick_asset_map` table mapping Dynasty Genius's synthetic pick keys (e.g. `("2027", 1, "mid")`) to FantasyCalc `player.id` integers; rows without a mapping are tagged `coverage_gap=generic_round_only` and pass through with `market_value=null`.

Critically, **no foreign key from `market_values` into any table consumed by Engine A/B/RosterCutEngine/xVAR.** The only consumers are:
- `MarketOverlayService` (Trade Lab UI panel)
- `LeaguePowerRanking` exports labelled "Market Snapshot"
- The audit/comparison view that lets David diff xVAR vs market for sanity-check purposes.

### Edge case matrix

| Case | Behavior |
|---|---|
| Missing market value on sent asset | Include in `coverage_gaps.unpriced_sent`; do NOT impute; sum proceeds without it; overlay output renders a yellow caveat. |
| Missing market value on received asset | Symmetric to above. |
| Synthetic pick beyond FantasyCalc coverage (e.g. "2027 Mid 2nd") | `market_value=null`, `coverage_gap=generic_round_only`. Optional fallback: substitute the *generic* round value ("2027 2nd") flagged as `imputation=generic_round_proxy`, but **only behind an explicit `--allow-pick-proxy` config flag**, not in default behavior. |
| Rookie with thin market data (`std_dev_adj ≥ 6` OR `|trend30Day|` > 30% of value) | Render value but add `thin_market` warning chip in UI. Underlying value still numeric (xVAR pipeline already handled the *evaluation* via Engine A regardless). |
| Counterparty roster unknown | `market_penalty_counterparty = null`; `coverage_gaps.counterparty_unknown = true`. Single-sided overlay still computed. |
| Player has negative xVAR (sub-replacement) but positive market value | Surface both as-is. The divergence is the *signal* — David can use it to identify market-overvalued depth pieces to sell. This is exactly the legitimate use case for the overlay. Do not blend them into a combined score. |
| Player in xVAR but absent from FantasyCalc | Player present in overlay row with `market_value=null, coverage_gap=fantasycalc_uncovered`. xVAR-side decision unaffected. |
| Player in FantasyCalc but absent from xVAR universe (deep dynasty taxi guys) | Render market value with `coverage_gap=xvar_uncovered`; xVAR decision will not score them. UI explicitly says "no model evaluation available." |
| FantasyCalc API down or stale (snapshot_ts > 24h) | Overlay endpoint returns 200 with `market_source=fantasycalc_stale` and `caveats=[...]`; never 5xxs the Trade Lab — the model-native evaluation is what David acts on. |

### Risks and governance safeguards

1. **Leakage risk: someone adds `market_value` to a feature vector in Engine A or RosterCutEngine.** Mitigation: a contract test that imports each engine's input schema and asserts `market_value` and `fantasycalc_*` columns are absent. A second integration test perturbs `market_values` and asserts xVAR / cut-candidate outputs are bit-identical.
2. **Cognitive leakage: David starts treating the overlay as authoritative.** Mitigation: UI never co-locates xVAR delta and overlay delta in the same headline. Overlay panel is visually de-emphasized and prefixed "Market Snapshot (price discovery only)." When the two disagree by >25%, the UI surfaces the divergence as a *prompt to inspect*, not a recommendation.
3. **KTC ToS violation risk.** Mitigation: hard-code FantasyCalc as the only auto-fetch source; KTC values can only enter the system via a `manual_overrides` table with a "where did you get this number" free-text field on the entry form. Audit log retains entry timestamp.
4. **Imputation drift on synthetic picks.** Mitigation: never impute by default; `--allow-pick-proxy` flag must be explicitly set in the request, and the response carries `imputation=generic_round_proxy`.
5. **α (cut realization factor) being misused.** Mitigation: `α` is config-only, never user-tunable from the trade UI; changing it requires a code-or-config commit so it doesn't become a knob David twiddles to "make a trade look better."

### Contract tests (concrete and enforceable)

```python
def test_roster_cut_engine_ignores_market_value():
    roster = build_test_roster()
    cuts_baseline = RosterCutEngine.rank(roster).top(5)
    perturb_market_values(roster, multiplier=10.0)
    cuts_perturbed = RosterCutEngine.rank(roster).top(5)
    assert cuts_baseline == cuts_perturbed

def test_engine_a_schema_excludes_market_columns():
    schema = EngineA.input_schema()
    forbidden = {"market_value","fantasycalc_value","ktc_value","fantasycalc_rank","market_trend_30d"}
    assert forbidden.isdisjoint(set(schema.columns))

def test_engine_b_schema_excludes_market_columns():
    schema = EngineB.input_schema()
    forbidden = {"market_value","fantasycalc_value","ktc_value"}
    assert forbidden.isdisjoint(set(schema.columns))

def test_xvar_pipeline_pure_of_market_data():
    xvar_baseline = compute_xvar(test_players)
    set_all_market_values(test_players, value=0)
    assert compute_xvar(test_players) == xvar_baseline

def test_market_overlay_decision_supported_flag_is_false():
    resp = market_overlay_endpoint(sent=[...], received=[...])
    assert resp["decision_supported"] is False
    for row in resp["sent"] + resp["received"]:
        assert row.get("decision_supported", False) is False

def test_forced_cut_set_is_xvar_ranked_not_market_ranked():
    roster = build_test_roster_where_xvar_and_market_disagree()
    cut_set = compute_forced_cut_set(roster, overflow=3)
    expected = sorted(roster, key=lambda p: p.xvar)[:3]
    assert cut_set == expected

def test_synthetic_pick_without_fantasycalc_mapping_returns_null():
    resp = market_overlay_endpoint(
        sent=[{"asset_type":"pick","year":2027,"round":2,"slot":"mid"}], received=[])
    assert resp["sent"][0]["market_value"] is None
    assert resp["sent"][0]["coverage_gap"] == "generic_round_only"
```

## Recommendations

**Phase 1 — Ship the read-only overlay (1–2 days work):**
1. Stand up a daily cron that pulls `https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1` and writes to `market_values` with `format_key=dyn_sf_12tm_1ppr`. Cache for 6 hours.
2. Build `pick_asset_map` covering exact-slot 2026 picks, generic 2026/2027/2028 round picks, and Early/Mid/Late 2027 R1.
3. Implement `POST /trade-lab/market-overlay` returning base sums + coverage gaps only (no forced-cut penalty yet, no counterparty). Wire UI panel labelled "Market Snapshot (price discovery — not decision-supported)."
4. Add the four contract tests on schema separation immediately, before any further integration.

**Phase 2 — Add David-side forced-cut penalty (1 day):**
5. Implement `compute_forced_cut_set(roster, overflow)` and confirm via `test_forced_cut_set_is_xvar_ranked_not_market_ranked` that selection is xVAR-driven.
6. Apply α=0.7 and surface `market_penalty_D` in the overlay response.
7. Add UI badge and tooltip explaining what the penalty represents and why it is overlay-only.

**Phase 3 — Optional counterparty penalty (later, only when valuable):**
8. Only build this once David has a clear use case (e.g. evaluating offers from a specific leaguemate whose roster is fully visible via Sleeper API).
9. Use FantasyCalc value ascending as the cut-ordering proxy for the opposing roster; document this clearly in the response caveats.

**Benchmarks that would change these recommendations:**
- If FantasyCalc publishes a documented rate limit < 1 req/hour → switch to nightly snapshot only.
- If KTC ever publishes an official API → re-evaluate KTC as a co-primary source (still overlay-only).
- If α=0.7 produces overlay deltas that David consistently disagrees with by more than 20% over 20+ trade evaluations → tune α (do not blend market into xVAR; tune the single config knob).
- If a position-aware cut-realization factor would meaningfully improve the overlay (e.g. cut-cost is realized closer to 100% for QB depth in superflex but only 40% for RB depth) → upgrade α from scalar to `α[position]` lookup, still config-only.

## Caveats

- The KTC raw-adjustment formula reverse-engineered by Dave C. on Javelin Fantasy Football (published September 30, 2022) is from client-side JS that may have been retuned since publication. KTC has stated they tweak the constants over time. Do not hard-code KTC's exponents into Dynasty Genius — the proposed α-scalar approach is intentionally simpler and more transparent.
- FantasyCalc's underlying optimization algorithm is undisclosed; treat their `value` as a black-box market signal. The `trend30Day` and `maybeMovingStandardDeviationAdjusted` fields are useful confidence indicators but are not normalized to value scale — interpret them relatively, not absolutely.
- FantasyCalc's data points come from public Sleeper/MFL/Fleaflicker trades, which skew toward more-active (and arguably less-sophisticated) league populations. Values for fringe taxi-squad players may swing wildly on small samples.
- DynastyProcess Calculator's "Perfect Knowledge" vs "Hit Rate" rookie pick models are GAM (Generalized Additive Model) regressions trained on draft-slot-to-dynasty-value outcomes at Y1 and Y2 horizons, blended at a default 80/20 ratio. This is a useful conceptual contrast for David's own xVAR-side rookie evaluation (Engine A), but the *blended outputs* are FantasyPros-derived and therefore market-flavored — they cannot enter the xVAR pipeline either.
- The α=0.7 starting value is heuristic. KTC's worked example from Dave C.'s Sep 30, 2022 article shows raw-adjustment ratios for mid-tier players sitting around 22–26% of their KTC value (CeeDee Lamb 25.5%, Joe Mixon 22.4%), and elite players at ~35% (Ja'Marr Chase 35.4%). Because Dynasty Genius's α applies to a *physically cut* player rather than KTC's *abstract compression*, α should be higher than the KTC raw-adjustment ratio — but the KTC numbers anchor a reasonable lower bound for the parameter and argue against α below ~0.5. Empirical tuning against David's accepted-trade outcomes should be the eventual calibration.
- This brief assumes Dynasty Genius runs single-user. Multi-user deployment would surface a separate concern: caching the FantasyCalc snapshot per-user vs globally. Currently a non-issue.