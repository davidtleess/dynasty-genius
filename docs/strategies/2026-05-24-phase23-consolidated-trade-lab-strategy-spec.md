# Phase 23 Consolidated Strategy Spec: Trade Lab Market Overlay and Competitive Realism

Date: 2026-05-24
Owner: David
Prepared by: Codex
Status: DRAFT - for David review
Governance: Product Constitution v1.0.0, North Star Architecture v1.0.0, Agent Operating Loop v1.0.0

## 1. Executive Summary

Phase 23 should extend Trade Lab with a market-side reconciliation panel and competitive realism warnings while preserving the existing model-native xVAR engine exactly as the decision-support anchor.

The best synthesis across the research reports is:

1. Keep the Phase 15/22 xVAR evaluator and forced-cut reconciler as the model-native lane.
2. Add a separate FantasyCalc market overlay lane that prices the same trade assets and the same RosterCutEngine-selected forced cuts.
3. Do not blend FantasyCalc or KTC values into xVAR, Engine A, Engine B, or RosterCutEngine.
4. Treat KTC as context/manual-only because it has no governed public API path and scraping is explicitly disallowed by source terms reported in the research.
5. Add a competitive realism warning layer for "many small assets for one premium asset" offers, but keep it advisory and `decision_supported=False`.
6. Support FantasyCalc pick market values only through deterministic FantasyCalc pick keys. Exact current-year slots and generic future year/round picks can be displayed as market overlay rows with resolution caveats; unresolved synthetic picks remain `market_value=null`.

This spec intentionally rejects the research proposals that would create a market-derived or blended `xVAR_pick`. Those ideas are useful as market context, but they blur the architecture's model-vs-market boundary.

## 2. Inputs Synthesized

### Google Doc 1

`1HJk36aaICPY1OdjGfr9UBbyfxor7ntS4fHEZZm8wyCE`

Best ideas retained:

- Roster spots are finite assets; package trades impose real opportunity cost.
- Public calculators mostly approximate package costs through hidden or generic compression, while Dynasty Genius can do better because it knows David's actual roster.
- FantasyCalc is the right automated market source for this phase because it has a stable unauthenticated endpoint and format parameters.
- Historical snapshots matter if Trade Lab later evaluates old trades.
- Pick stacking must be allowed; duplicate future picks should be represented as separate trade assets, not deduped by key.

Rejected or modified:

- Automated KTC ingestion is rejected. KTC has no approved API path and the web research cites KTC's no-scraping terms.
- Any "consensus value" blending KTC + FantasyCalc is rejected for Phase 23.
- A replacement-floor `max(cut_market_value, waiver_floor)` penalty is not adopted by default because it can invent value for cuts that the market did not price. If explored later, it needs a separate calibration artifact.

### Local Primary Research Report

`docs/strategies/2026-05-24-phase23-primary-research-report.md`

Best ideas retained:

- Verified Trade Lab currently uses `TradeAsset`, not a separate `DraftAsset`.
- `value_draft_pick()` is model-native: Engine A DVS -> Engine A replacement DVS -> xVAR.
- Phase 22 forced-cut penalty already subtracts positive raw xVAR of RosterCutEngine-selected cuts.
- FantasyCalc pick rows have `position="PICK"` and raw integer `value`.
- The Jefferson/PRE_MODEL case is important: market value can exist when model xVAR is unavailable, but xVAR must remain null.

Corrections:

- Active code constants are `CONSOLIDATION_KAPPA = 0.04` and `CONSOLIDATION_FLOOR = 0.80`, not 0.05 and 0.70.
- FantasyCalc pick keying should follow the verified local cache: exact slots use `DP_{round}_{slot}` with both values 0-indexed; generic future picks use `FP_{year}_{round}`.

### Local Web-Based Research

`docs/strategies/Trade Lab Research - Web based.md`

Best ideas retained:

- Public calculators address consolidation through value compression, depth/stud sliders, or roster-spot adjustments.
- KTC raw adjustment is useful as a conceptual benchmark but should not be implemented or scraped.
- FantasyCalc is the only viable automated market source for this phase.
- Missing market values should not be imputed silently.
- Contract tests should prove that perturbing market values does not change xVAR or cut selection.

Rejected or modified:

- The proposed alpha scalar (`alpha = 0.7`) is rejected for W1. If a cut is selected and has a FantasyCalc market value, the market overlay should initially subtract 100% of that value. A realization factor is a calibration parameter and should not ship without evidence.
- Counterparty cut selection must not use FantasyCalc ascending order by default. Use RosterCutEngine for any roster where local PVO and Sleeper snapshot coverage are available. If counterparty coverage is inadequate, set `counterparty_market_penalty_status="unavailable"` with caveats.

### Google Doc 2

`12SxaF3rlLVNr2f-IrfcNnlii4a4172rOEMoR-w2gIhI`

Best ideas retained:

- A double-sided capacity model is directionally correct when both rosters are known.
- Competitive realism flags are useful to prevent "ten nickels for a dollar" presentations.
- Offseason roster expansion and taxi/IR state can make capacity penalties conditional.
- Pick serialization and duplicate-pick handling need explicit contracts.

Rejected or modified:

- A rookie pick hybrid value formula blending normalized FantasyCalc values with Engine A is rejected.
- The realism gate must not "block approval" or imply decision authority. It can emit warnings and caveats only.
- Engine A and Engine B are not impacted by Phase 23. Phase 23 is a Trade Lab overlay/UI/API extension.

### Existing Codex Addendum

`docs/strategies/2026-05-24-phase22-roster-reconciler-spec.md`

Best ideas retained:

- Add a market overlay sibling object, not fields on `TradeAsset`.
- Keep RosterCutEngine market-blind.
- Distinguish synthetic pick assets from real prospect players; `is_prospect=True` is currently overloaded.
- Add recursive `decision_supported=False` locks on all new response structures.

## 3. Points of Agreement

Across the inputs, the strong consensus is:

- Package trades are non-linear because roster spots are scarce.
- A real roster-aware forced-cut penalty is better than a hidden KTC-style adjustment.
- FantasyCalc can supply market price discovery for players and some picks.
- KTC is useful context but not a governed automated source.
- Market values must be parallel to model-native xVAR, not part of it.
- Missing market coverage must be explicit, not silently treated as zero.
- Future picks need first-class parsing because they are not Sleeper player rows.

## 4. Conflicts and Resolutions

| Conflict | Resolution |
|---|---|
| Hybrid pick xVAR vs market isolation | Reject hybrid xVAR. Keep Engine A xVAR and FantasyCalc market value side-by-side. |
| KTC automated ingestion vs source constraints | Reject automation. Permit future manual KTC override only with provenance and audit fields. |
| Alpha-scaled cut penalty vs full market value | Start with full resolved FC value. Add alpha only after calibration evidence. |
| Counterparty cut ordering by market value vs RosterCutEngine authority | Use RosterCutEngine for counterparty when roster/PVO coverage exists; otherwise mark unavailable. |
| Competitive gate as "block" vs `decision_supported=False` | Emit warnings only. No approval language and no auto-blocking. |
| Generic future pick value vs exact slot value | Exact slots use exact FC rows; unresolved futures use generic `FP_{year}_{round}` only when that exact generic key exists, with a caveat. |
| Pick values in PVO vs separate asset layer | Keep picks outside PVO for Phase 23; resolve them in Trade Lab market overlay and Engine A pick valuation helpers. |

## 5. Recommended Phase 23 Architecture

Phase 23 should add one overlay module and one endpoint extension:

```text
Trade request assets
    |
    +--> model-native lane
    |       TradeAsset -> evaluate_trade()
    |       TradeAsset + universe_pvo + sleeper_snapshot -> reconcile_trade_roster()
    |       Output: xVAR evaluation + xVAR forced-cut penalty
    |
    +--> market overlay lane
            MarketAssetRef -> FantasyCalc resolver
            Forced cuts from RosterCutEngine -> FantasyCalc resolver
            Output: raw FC sent/received values + FC forced-cut penalties + caveats
```

New module:

```text
src/dynasty_genius/trade_lab/market_reconciler.py
```

Responsibilities:

- Resolve player assets to FantasyCalc values by Sleeper ID.
- Resolve pick assets to FantasyCalc pick rows by deterministic FC key.
- Price only the forced cuts selected by RosterCutEngine.
- Compute David-side and optional counterparty-side market penalties.
- Return coverage gaps and caveats.
- Never call Engine A, Engine B, or RosterCutEngine with market values.

Existing modules that remain authoritative:

- `src/dynasty_genius/trade_lab/evaluator.py`: model-native xVAR trade parity.
- `src/dynasty_genius/trade_lab/reconciler.py`: roster-aware xVAR forced-cut penalty.
- `src/dynasty_genius/roster_cut_engine.py`: forced-cut candidate selection.
- `src/dynasty_genius/adapters/fantasycalc_adapter.py`: FantasyCalc fetch/cache/sanitize.

## 6. Data Contracts and Schema Additions

### 6.1 Asset Kind

Add an explicit market-layer asset kind instead of relying only on `is_prospect`.

```python
AssetKind = Literal["player", "prospect_player", "future_pick"]
```

Do not add market fields to `TradeAsset`. Introduce a separate market request/reference model:

```python
class MarketAssetRef(BaseModel):
    asset_kind: Literal["player", "prospect_player", "future_pick"]
    player_id: str | None = None
    sleeper_id: str | None = None
    year: int | None = None
    round: int | None = None
    slot: int | None = None       # 1-12 when exact order is known
    bucket: Literal["early", "mid", "late"] | None = None
    quantity_id: str | None = None
```

`quantity_id` exists so two identical future picks can both appear in a trade without deduping.

### 6.2 Market Asset Overlay

```python
class MarketAssetOverlay(BaseModel):
    asset_ref: MarketAssetRef
    label: str
    source: Literal["fantasycalc"]
    format_key: str
    market_value: int | None
    resolution: Literal[
        "player_sleeper_id",
        "pick_exact_slot",
        "pick_generic_year_round",
        "unresolved",
    ]
    coverage_gap: str | None
    trend_30d: int | None = None
    market_volatility: float | None = None
    source_timestamp: str | None = None
    caveats: list[str]
    decision_supported: bool = False
```

`decision_supported` must be coercion-locked to `False`.

### 6.3 Market Roster Penalty

```python
class MarketRosterPenalty(BaseModel):
    roster_id: int
    post_trade_overflow: int
    forced_cut_candidates: list[MarketAssetOverlay]
    penalty_market_value: int
    unresolved_cut_count: int
    caveats: list[str]
    decision_supported: bool = False
```

Penalty is the sum of resolved FC market values for the already-selected forced cuts.

### 6.4 Trade Market Reconciliation

```python
class TradeMarketReconciliation(BaseModel):
    market_source: Literal["fantasycalc"]
    format_key: str
    source_timestamp: str | None
    sent_assets: list[MarketAssetOverlay]
    received_assets: list[MarketAssetOverlay]
    market_sent_raw: int
    market_received_raw: int
    david_forced_cut_penalty: MarketRosterPenalty | None
    counterparty_forced_cut_penalty: MarketRosterPenalty | None
    adjusted_market_sent: int
    adjusted_market_received: int
    market_delta_for_david: int
    coverage_gaps: list[str]
    caveats: list[str]
    decision_supported: bool = False
```

This object is a sibling to `TradeRosterReconciliation`, not a replacement.

## 7. FantasyCalc Pick Resolution

Use the live cache contract as the implementation source:

- Current exact slots: `DP_{round_index}_{slot_index}`
  - `round_index = round - 1`
  - `slot_index = slot - 1`
  - Example: 2026 1.01 -> `DP_0_0`; 2026 2.01 -> `DP_1_0`
- Generic futures: `FP_{year}_{round}`
  - Example: 2027 1st -> `FP_2027_1`

Resolution rules:

| Input | FC lookup | Resolution | Caveat |
|---|---|---|---|
| `year=current_draft_year`, exact `slot` known | `DP_{round-1}_{slot-1}` | `pick_exact_slot` | none unless stale source |
| Future year/round, no slot | `FP_{year}_{round}` | `pick_generic_year_round` | `generic_future_pick_market_value` |
| Future exact early/mid/late only | no default FC key | `unresolved` unless mapped by explicit future work | `fantasycalc_bucket_pick_unavailable` |
| Pick beyond FC coverage | none | `unresolved` | `fantasycalc_pick_unavailable` |

Do not normalize FC pick value to xVAR. Display it as raw FC market value only.

## 8. Single-Sided Market Forced-Cut Formula

Let:

- `S` = assets David sends
- `R` = assets David receives
- `FC(a)` = resolved FantasyCalc value for asset `a`, nullable
- `C_D` = forced cuts selected by RosterCutEngine for David after the trade

Base market sums:

```text
market_sent_raw = sum(FC(a) for a in S if FC(a) is not null)
market_received_raw = sum(FC(a) for a in R if FC(a) is not null)
```

David-side market forced-cut penalty:

```text
market_cut_penalty_david = sum(FC(c) for c in C_D if FC(c) is not null)
```

Adjusted market received value:

```text
adjusted_market_received = max(0, market_received_raw - market_cut_penalty_david)
adjusted_market_sent = market_sent_raw
market_delta_for_david = adjusted_market_received - adjusted_market_sent
```

Unresolved cut candidates:

```text
unresolved_cut_count = count(c in C_D where FC(c) is null)
```

These unresolved cuts are caveats, not zero-value assertions.

## 9. Double-Sided Market Forced-Cut Formula

Double-sided calculation is allowed only when the counterparty roster is known and coverage is sufficient.

Let:

- `C_D` = David forced cuts after sending `S` and receiving `R`
- `C_CP` = counterparty forced cuts after sending `R` and receiving `S`

Both cut sets must be selected by RosterCutEngine on post-trade snapshots.

```text
market_cut_penalty_david = sum(FC(c) for c in C_D if FC(c) is not null)
market_cut_penalty_counterparty = sum(FC(c) for c in C_CP if FC(c) is not null)

adjusted_market_received = max(0, market_received_raw - market_cut_penalty_david)
adjusted_market_sent = max(0, market_sent_raw - market_cut_penalty_counterparty)
market_delta_for_david = adjusted_market_received - adjusted_market_sent
```

Interpretation:

- `adjusted_market_received`: what the FC market says David receives after David's cut cost.
- `adjusted_market_sent`: what the FC market says the counterparty receives after the counterparty's cut cost.
- `market_delta_for_david`: market-only directional delta.

This is not xVAR, not a trade recommendation, and not a model decision.

## 10. Competitive Realism Warnings

Add warning flags, not blocking logic.

Recommended advisory metrics:

```text
premium_asset_value = max(market_value of assets on the premium side)
incoming_asset_count = number of roster-consuming player/prospect assets received
low_quality_asset_count = count(asset where market_value < gamma * premium_asset_value)
average_package_ratio = mean(market_value of incoming assets) / premium_asset_value
```

Initial config:

```text
gamma = 0.15
psi = 0.25
```

Warnings:

- `package_dilution_warning`: average package ratio below `psi`.
- `roster_filler_warning`: at least two assets below `gamma * premium_asset_value`.
- `market_package_requires_manual_review`: market_delta and xVAR_delta disagree materially.

These warnings must use language like "review", "capacity cost", and "market realism warning". Do not use "accept", "reject", "approve", "block", or "decision-supported".

## 11. Edge Cases

| Case | Required behavior |
|---|---|
| Player has xVAR but no FC value | xVAR lane unchanged; market overlay row has `market_value=null` and `fantasycalc_uncovered`. |
| Player has FC value but PRE_MODEL xVAR | Market lane displays FC value with `model_value_unavailable`; xVAR stays null, not zero. |
| Negative/sub-replacement xVAR with positive FC value | Surface both values. This is a legitimate divergence, not a reason to blend. |
| Synthetic future pick with exact FC generic row | Display raw FC value with `generic_future_pick_market_value`. |
| Synthetic future pick without FC row | `market_value=null`; do not impute. |
| Duplicate identical picks | Preserve both entries using `quantity_id`; do not dedupe by FC key. |
| Counterparty roster unknown | `counterparty_forced_cut_penalty=null`; add `counterparty_roster_unknown`. |
| Counterparty roster known but PVO coverage inadequate | Do not select cuts by FC by default; mark counterparty penalty unavailable. |
| FantasyCalc stale | Return overlay with stale caveats; do not fail model-native Trade Lab. |
| Offseason expanded rosters | Use actual Sleeper roster capacity from the snapshot. If no overflow exists, penalty is zero. |
| Taxi / IR locks | RosterCutEngine remains authoritative; do not duplicate eligibility logic in market overlay. |

## 12. Governance Safeguards

Hard rules:

1. No market field may be accepted by `TradeAsset`.
2. No market value may enter Engine A, Engine B, xVAR, or RosterCutEngine.
3. Roster cut selection is always model-native.
4. Market overlay values are raw FC scale; they are never converted to xVAR.
5. All market reconciliation schemas coerce `decision_supported=False`.
6. KTC automated fetch/scrape is out of scope.
7. Any future manual KTC entry must carry source, entry timestamp, entered_by, and free-text provenance.
8. UI must visually separate "Model View (xVAR)" from "Market Snapshot (FantasyCalc)".

Required caveats:

- `market_overlay_display_only`
- `fantasycalc_raw_scale_not_xvar`
- `market_values_not_model_inputs`
- `decision_supported_false`
- `source_timestamp_is_fetch_time_not_publish_time`

## 13. Required Tests and Acceptance Gates

### Contract tests

| Test | Requirement |
|---|---|
| `test_trade_asset_rejects_or_ignores_market_fields` | Core `TradeAsset` cannot carry `market_value`, `fantasycalc_value`, or `ktc_value`. |
| `test_market_reconciliation_decision_supported_false_recursive` | No nested market object can set `decision_supported=True`. |
| `test_market_overlay_does_not_change_xvar_evaluation` | Adding/perturbing FC values leaves `evaluate_trade()` output bit-identical. |
| `test_market_overlay_does_not_change_cut_selection` | Perturbing FC values leaves RosterCutEngine forced cuts unchanged. |
| `test_david_market_cut_penalty_values_selected_cuts_only` | FC penalty prices only RosterCutEngine-selected cuts. |
| `test_counterparty_market_penalty_uses_roster_cut_engine_when_available` | Counterparty cut set comes from RosterCutEngine, not market sorting. |
| `test_counterparty_penalty_unavailable_when_coverage_missing` | No market-sorted fallback by default. |
| `test_exact_pick_slot_resolves_dp_key` | 1.01 maps to `DP_0_0`; 2.01 maps to `DP_1_0`. |
| `test_generic_future_pick_resolves_fp_key` | 2027 1st maps to `FP_2027_1` with generic caveat. |
| `test_unresolved_pick_market_value_null` | No FC row -> null value and coverage caveat. |
| `test_duplicate_pick_assets_preserved` | Two identical future picks remain two overlay rows. |
| `test_premodel_market_value_does_not_coerce_xvar` | PRE_MODEL xVAR remains null even when FC exists. |
| `test_no_market_columns_in_engine_a_b_contracts` | Governance regex still blocks market features. |

### Acceptance gates

- Governance validator passes.
- Full test suite passes.
- No model pkl, model manifest, Engine A contract, Engine B contract, or RosterCutEngine ranking logic changes unless separately approved.
- Market reconciliation endpoint returns a valid response when FantasyCalc is stale or unavailable, with caveats.
- Recursive `decision_supported=True` count is zero.

## 14. Workstream Breakdown

### W1 - Market Asset Resolver

Scope:

- Implement `MarketAssetRef`, `MarketAssetOverlay`, and pick key resolver.
- Use existing FantasyCalc cache/fetch behavior.
- Resolve players by Sleeper ID.
- Resolve picks by `DP_*` and `FP_*` keys.
- Preserve duplicate picks.

Tests:

- Player resolution.
- Exact pick resolution.
- Generic future pick resolution.
- Missing pick coverage.
- Duplicate pick preservation.
- Recursive `decision_supported=False`.

### W2 - Trade Market Reconciler

Scope:

- Implement `TradeMarketReconciliation`.
- Compute raw sent/received FC sums.
- Compute David-side market forced-cut penalty using Phase 22 forced cuts.
- Keep market lane read-only over the reconciler output.

Tests:

- Market sums.
- David cut penalty.
- Unresolved cut caveats.
- No xVAR mutation.
- No cut-selection mutation.

### W3 - Arbitrage Divergence Context

**David's ruling: include in Phase 23.**

Scope:

- Read `universe_market_divergence_latest.json` for players in the trade.
- Surface `percentile_delta` and `signal_status` per asset in the market overlay response.
- Apply σ threshold = 0.25 to classify as `model_higher_than_market` / `model_lower_than_market` / `inside_band` / `unavailable`.
- No new metric computation — overlay of existing divergence signal only.

Tests:

- Player with `gates_passed` surfaces correct signal label.
- Player with `unavailable` status surfaced without error.
- No BUY/SELL/target language in any response field.
- `decision_supported=False` on all arbitrage rows.

### W3b - Optional Counterparty Penalty (deferred to Phase 23.5)

**David's ruling: defer until David-side overlay is stable.**

Scope (Phase 23.5):

- Accept optional `counterparty_roster_id`.
- Construct counterparty post-trade snapshot.
- Run RosterCutEngine for counterparty if PVO/snapshot coverage exists.
- Return `counterparty_market_penalty_status="unavailable"` with caveats if coverage is inadequate.
- No market-sorted fallback for cut selection under any circumstance.

Tests (Phase 23.5):

- Counterparty penalty with full RosterCutEngine coverage.
- Counterparty unavailable when coverage missing — no market sort fallback.
- No market-sorted counterparty cut selection.

### W4 - Competitive Realism Warnings

Scope:

- Add warning-only package dilution metrics.
- Add caveats to market reconciliation response.
- No blocking/approval semantics.

Tests:

- Many-for-one warnings.
- No warning on balanced one-for-one.
- Banned language absent.

### W5 - API/UI Integration

**David's rulings: separate endpoint; standalone Trade Lab page.**

Scope:

- Create `POST /api/trade/reconcile/market` as a separate route file. Do not extend the existing model-native `/api/trade/reconcile`.
- Frontend: standalone Trade Lab page with two-side asset input form.
- Page displays two side-by-side panels:
  - **Model View**: xVAR evaluation + RosterCutEngine forced-cut penalty (Track 1, Phase 22 output).
  - **Market Snapshot (FantasyCalc — price discovery only)**: FC raw values, market cut cost, generic pick caveats, arbitrage divergence context (Track 2, Phase 23 output).
- Draft board layout unchanged during Phase 23.

Tests:

- `POST /api/trade/reconcile/market` endpoint schema and response structure.
- Stale FantasyCalc graceful degradation (200 with stale caveats, not 503).
- UI/API banned language absent (`buy`, `sell`, `target`, `block`, `approve`, `reject`, `pass`, `fail`).
- `decision_supported=False` on all market overlay rows.
- Model View output bit-identical with and without market endpoint call.

## 15. Out of Scope

- Automated KTC ingestion or scraping.
- Blended `xVAR_market`, hybrid pick xVAR, or any market-derived model-native number.
- Three-team trades.
- IDP or defense valuation.
- Weekly lineup optimization.
- Tuning alpha/realization factors without validation data.
- Writing FantasyCalc values into PVO model fields, Engine A features, Engine B features, or RosterCutEngine ranking inputs.

## 16. David's Rulings — All Decisions Closed (2026-05-24)

All open decisions are now resolved. Implementation may begin.

| Decision | Ruling |
|---|---|
| Endpoint shape | Create a **separate** `POST /api/trade/reconcile/market` endpoint. Physical isolation of all FantasyCalc-dependent Pydantic models, request schemas, and caches from the model-native route. |
| Generic future pick display | **Show with caveats.** Display `FP_{year}_{round}` market value with an explicit ±40% slot-spread note (e.g., 2027 firsts range 2,340–6,863 FC points). Do not suppress. |
| Counterparty forced-cut penalty | **Defer to Phase 23.5 / late workstream.** David-side overlay is the W1/W2 priority. Counterparty scope added only after the David-side API contract is stable. |
| Competitive realism thresholds | **Ship with `gamma=0.15`, `psi=0.25`.** Gate is advisory/warning-only; uncalibrated defaults carry zero risk. Monitor firing frequency; tune in a future sub-phase. |
| Arbitrage context | **Include in Phase 23 late workstream.** Reads existing `universe_market_divergence_latest.json` — zero new metric computation. Use neutral divergence labels only (see Section 16.1). |
| UI scope | **Standalone Trade Lab page first.** Dedicated page for two-side asset input and side-by-side model/market panels. Draft board layout stays untouched during Phase 23. |

### 16.1 Arbitrage Divergence Context — Language Contract

The arbitrage spotter reuses the existing `divergence.percentile_delta` from `universe_market_divergence_latest.json`. It does not compute new metrics.

Permitted signal labels (reusing existing divergence flag vocabulary):

| Signal | Meaning |
|---|---|
| `model_higher_than_market` | Model percentile exceeds market percentile by ≥ σ threshold |
| `model_lower_than_market` | Market percentile exceeds model percentile by ≥ σ threshold |
| `inside_band` | Percentile delta within normal range |
| `unavailable` | Player not in `gates_passed` population |

Initial σ threshold: `0.25` (≈ 1 standard deviation above the positional mean of `|Δ|` for `gates_passed` rows, which averaged 0.261 per the live data sweep).

**Banned language on all arbitrage surfaces:** buy, sell, target, block, approve, reject, pass/fail.

**Permitted UI copy:**
- "Model-market spread"
- "Market is lower than model"
- "Market is higher than model"
- "Inside normal range"
- "Market comparison unavailable"

## 17. Codex Review Checklist

- Verify no market fields were added to `TradeAsset`.
- Verify all new market schemas lock `decision_supported=False`.
- Verify FantasyCalc values are raw market scale only.
- Verify xVAR outputs are identical with and without market overlay.
- Verify RosterCutEngine forced cuts are identical after market perturbation.
- Verify picks resolve through deterministic FC keys and duplicate picks are preserved.
- Verify missing market values produce caveats, not imputed zeros.
- Verify counterparty cuts, if implemented, come from RosterCutEngine.
- Verify KTC is not fetched, scraped, or treated as an automated source.
- Run `scripts/validate_governance.py` and the full suite before promotion.
