# Phase 23 Consolidated Strategy & Spec: Trade Lab Market Overlay & Competitive Realism Engine

**Date:** May 24, 2026  
**Author:** Dynasty Genius PM (Gemini)  
**Governing Document Version:** 1.0.0 (Product Constitution & North Star Architecture Compliant)  
**Status:** PROPOSED — Pending David's final review and approval

---

## 1. Executive Mandate

Phase 22 successfully delivered a model-native trade reconciler that detects post-trade roster capacity overflows, identifies forced cuts via the `RosterCutEngine` (using xVAR-ascending order), and deducts their raw xVAR value as a Forced Cut Penalty. 

**Phase 23 introduces the Market Overlay Sidecar & Competitive Realism Engine.** This is a completely separate, parallel evaluation track that answers the question: *"What is the market-consensual value of this trade, and does the package deal make strategic sense?"* 

### 🛡️ Core Governance Constraint: The Fire Wall
To strictly preserve the **Product Constitution**, all market-derived values (from FantasyCalc, manual KTC overrides, etc.) are **overlays only**. They are physically and semantically walled off from all predictive model inputs:
*   Market values **never** enter the Feature Store.
*   Market values **never** participate in Engine A or Engine B training or inference.
*   Market values **never** alter core xVAR, DVS, or the `RosterCutEngine` selection logic.
*   The entire Phase 23 overlay output carries `decision_supported = False` at all levels.

---

## 2. Key Synthesis & Conflict Resolution

This consolidated specification synthesizes the four foundational research papers:
*   **PR**: Primary Research Report (Gemini's local codebase & schema audit).
*   **WB**: Web-based Trade Lab Research (Claude's industry benchmarks & KTC analysis).
*   **GD1**: Market-Side Valuation Reconciliation & Forced-Cut Penalty Architecture (Google Doc).
*   **GD2**: Market Realism & Roster Capacity Modeling (Google Doc).

| Foundational Conflict | Source Approaches | Consolidated Resolution |
|---|---|---|
| **Data Source Selection** | GD1 proposes a blended KTC/FC consensus; WB warns KTC's Terms of Service strictly forbid scraping. | **FantasyCalc (FC) auto-fetch only** via cached API. **KTC manual overrides** allowed only via local inputs; auto-scraping KTC is prohibited. |
| **Forced Cut Selection** | GD2 uses market-value ascending; PR and WB use model-native xVAR ascending. | **xVAR ascending always** for David's side. This ensures that our model's competitive intelligence determines who is dropped. FC market-value ascending is used *only* as a proxy for counterparty rosters (since we have no xVAR for opposing teams). |
| **Forced Cut Penalty Math** | PR uses positive raw xVAR (Track 1); WB proposes physical market loss scaled by $\alpha$. | **Two independent tracks**: Track 1 uses raw positive xVAR (unchanged). Track 2 (Market Overlay) computes its own market penalty: $\alpha \times \sum \text{market\_value}(cut\_players)$, with $\alpha = 0.7$. |
| **Pick Valuation** | GD2 proposes a time-decay model; PR identifies Option A/B/C spaces; WB leaves generic picks unpriced. | **Option B (Parallel Display)**: Display model-native Engine A xVAR and FantasyCalc market values side-by-side on the trade card. Never mathematically blend them into a single score. |
| **Roster Expansion Status** | GD2 identifies Sleeper offseason states. | **Roster Expansion Gate**: During the offseason (`pre_draft` or `drafting`), Sleeper expands roster slots. The engine bypasses forced-cut penalties in this state. |
| **Deep Bench Floor** | GD2 notes deep leagues can zero out cuts. | **1,000 FC Points Floor**: Minimum floor per cut candidate to prevent zeroing out drops in deep formats. |

---

## 3. Dual-Track Architectural Design

Every trade evaluated in the Trade Lab will return **two independent, side-by-side tracks**. They are never added, averaged, or blended:

```text
                           [Trade Input Card]
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
  [TRACK 1: Model-Native xVAR]                     [TRACK 2: Market Overlay]
  (Phase 22 Reconciler - UNCHANGED)                (Phase 23 Engine - NEW)
  - decision_supported = False                     - decision_supported = False
  - Pick Valuation: Engine A (value_draft_pick)    - Pick Valuation: FantasyCalc API
  - Cut Selection: xVAR ascending                  - Cut Selection: xVAR ascending (David)
  - Cut Penalty: Sum of raw positive xVAR            FC value ascending (Counterparty proxy)
  - Parity: 10% TRADE_PARITY_BAND                  - Cut Penalty: α × Σ Market_Value(cuts)
                                                     (α = 0.7 realization factor)
                                                   - Parity: 10% Parity Band in FC Points
```

---

## 4. Market Overlay Mathematical Specification

Let $S$ be the set of assets David sends, $R$ the received assets, and $M(a)$ the FantasyCalc market value of asset $a$ (nullable). Let $C_D$ be David's current roster players sorted by xVAR ascending, $cap_D$ the roster capacity limit, and $n_D$ the current roster size.

### Step 1: Base Market Sums & Null Handling
Calculate the nominal market sums for both sides, isolating unpriced assets (coverage gaps):
$$market\_sent = \sum_{a \in S, M(a) \ne \text{null}} M(a)$$
$$market\_received = \sum_{a \in R, M(a) \ne \text{null}} M(a)$$
$$unpriced\_sent = \{a \in S \mid M(a) == \text{null}\}$$
$$unpriced\_received = \{a \in R \mid M(a) == \text{null}\}$$

### Step 2: Roster Capacity & Offseason Expansion Check
If the league is in the offseason (`status in ["pre_draft", "drafting"]`), set $overflow = 0$ and $penalty = 0.0$. Otherwise:
$$overflow_D = \max\left(0, (n_D - |S_{\text{players}}| + |R_{\text{players}}|) - cap_D\right)$$

### Step 3: xVAR-Driven Roster Cut Selection
Identify the specific players David is forced to cut:
$$cut\_set_D = \text{first } overflow_D \text{ players of } (C_D \setminus S) \text{ sorted by xVAR ascending}$$
*   **Tie-Breakers**: Chronological age descending (doctrine cliffs), then positional scarcity.
*   **Critical Invariant**: Cut selection is completely blind to market values.

### Step 4: David-Side Forced Cut Market Penalty
Multiply the sum of the market values of the cut set by the **cut realization factor** $\alpha$ ($0.7$):
$$market\_penalty_D = \alpha \times \sum_{p \in cut\_set_D, M(p) \ne \text{null}} \max\left(1000, M(p)\right)$$
*   **Realization Factor ($\alpha = 0.7$)**: Reflects that bottom-of-bench players carry less market liquidity, and some value is recovered through waiver-wire churn.
*   **Deep Bench Floor**: A minimum floor of $1,000$ FC points (matches `BASE_WAIVER_VALUE_SF`) is enforced per player to prevent zeroing out drops.

### Step 5: Counterparty Forced Cut (Optional)
If the counterparty roster ($CP$) is known:
$$overflow_{CP} = \max\left(0, (n_{CP} - |R_{\text{players}}| + |S_{\text{players}}|) - cap_{CP}\right)$$
$$cut\_set_{CP} = \text{first } overflow_{CP} \text{ players of } (CP \setminus R) \text{ sorted by FC value ascending}$$
$$market\_penalty_{CP} = \alpha \times \sum_{p \in cut\_set_{CP}, M(p) \ne \text{null}} \max\left(1000, M(p)\right)$$
*   *Note*: Since we do not maintain a full xVAR projection for opposing rosters, FC value ascending is used as a proxy for the counterparty's cut order. If the counterparty roster is unknown, $market\_penalty_{CP} = \text{null}$.

### Step 6: Adjusted Market Outputs
$$adj\_market\_received = market\_received - market\_penalty_D$$
$$adj\_market\_sent = market\_sent - (market\_penalty_{CP} \parallel 0)$$
$$overlay\_delta = adj\_market\_received - adj\_market\_sent$$

---

## 5. Competitive Realism Gate & Arbitrage Spotter

These two advisory layers run entirely on the display layer of Track 2 (Market Overlay) and never affect Track 1.

### 5.1 Competitive Realism Gate (GD2)
Prevents the "ten nickels for a dollar" exploit by evaluating structural package quality. It evaluates the received side when David is consolidating (receiving a multi-asset package). 

Let $P^*$ be the premier (highest-valued) asset in the received package $R$:
1.  **Asset Quality Floor**: Warn if any asset $a \in R$ fails the floor check:
    $$M(a) < \gamma \times M(P^*) \quad (\gamma = 0.20)$$
    *Failing assets are flagged as "roster filler" warnings.*
2.  **Average Dilution Floor**: Warn if the average value of the package is too diluted:
    $$\text{mean}\left(M(a) \mid a \in R\right) < \psi \times M(P^*) \quad (\psi = 0.35)$$

### 5.2 Arbitrage Spotter (GD2)
Surfaces the existing percentile divergence signal from `universe_market_divergence_latest.json` as an actionable trade context chip:
*   Let $\Delta = model\_percentile(p) - market\_percentile(p)$ for player $p$.
*   **BUY_TARGET (Model High, Market Low)**: $\Delta \ge \sigma_{\text{threshold}} \quad (\sigma_{\text{threshold}} = 0.25)$.
*   **SELL_TARGET (Model Low, Market High)**: $\Delta \le -\sigma_{\text{threshold}} \quad (\sigma_{\text{threshold}} = 0.25)$.
*   *Calibration*: $\sigma_{\text{threshold}} = 0.25$ corresponds to $\approx 1$ standard deviation above the positional mean.

---

## 6. Schema and Data Model

Two new tables are introduced to persist the cached FantasyCalc market data:

```sql
-- Normalised market values cache
CREATE TABLE market_values (
    source             VARCHAR,    -- 'fantasycalc' | 'ktc_manual'
    asset_id           VARCHAR,    -- sleeper_id for players; synthetic key for picks
    asset_type         VARCHAR,    -- 'player' | 'pick'
    format_key         VARCHAR,    -- 'dyn_sf_12tm_1ppr'
    value              INT,
    trend_30d          INT,
    std_dev_adj        INT,
    snapshot_ts        TIMESTAMP,
    decision_supported BOOLEAN DEFAULT FALSE -- Coercion-locked False
);

-- Pick key mappings to FantasyCalc entry IDs
CREATE TABLE pick_asset_map (
    synthetic_key    VARCHAR PRIMARY KEY,  -- e.g. '2027_1_MID'
    fc_player_id     INT,                  -- FantasyCalc player.id integer
    is_generic       BOOLEAN,              -- True if exact slot is unknown
    slot_spread_note VARCHAR               -- e.g. '±40% vs actual slot'
);
```

---

## 7. Concrete Contract Tests

These tests guarantee strict separation of concerns and mathematical compliance under all conditions:

```python
def test_roster_cut_engine_ignores_market_value():
    """Asserts that RosterCutEngine ranking is 100% blind to market value modifications."""
    roster = build_test_roster()
    cuts_baseline = RosterCutEngine.rank(roster).top(5)
    perturb_market_values(roster, multiplier=10.0)
    cuts_perturbed = RosterCutEngine.rank(roster).top(5)
    assert cuts_baseline == cuts_perturbed

def test_engine_a_schema_excludes_market_columns():
    """Guarantees no market columns leak into Engine A's input schema."""
    schema = EngineA.input_schema()
    forbidden = {"market_value", "fantasycalc_value", "ktc_value", "market_trend_30d"}
    assert forbidden.isdisjoint(set(schema.columns))

def test_engine_b_schema_excludes_market_columns():
    """Guarantees no market columns leak into Engine B's input schema."""
    schema = EngineB.input_schema()
    forbidden = {"market_value", "fantasycalc_value", "ktc_value"}
    assert forbidden.isdisjoint(set(schema.columns))

def test_xvar_pipeline_pure_of_market_data():
    """Asserts that core player xVAR calculations are bit-identical regardless of market values."""
    xvar_baseline = compute_xvar(test_players)
    set_all_market_values(test_players, value=0)
    assert compute_xvar(test_players) == xvar_baseline

def test_market_overlay_decision_supported_is_false():
    """Enforces that the overlay endpoint and all nested assets carry decision_supported=False."""
    resp = market_overlay_endpoint(sent=[...], received=[...])
    assert resp["decision_supported"] is False
    for row in resp["sent"] + resp["received"]:
        assert row.get("decision_supported", False) is False

def test_forced_cut_set_is_xvar_ranked_not_market_ranked():
    """Verifies that forced-cut sets are chosen purely by model xVAR ascending."""
    roster = build_test_roster_where_xvar_and_market_disagree()
    cut_set = compute_forced_cut_set(roster, overflow=3)
    expected = sorted(roster, key=lambda p: p.xvar)[:3]
    assert cut_set == expected

def test_offseason_expansion_suppresses_cut_penalty():
    """Asserts that offseason states correctly suppress cut penalties to zero."""
    with patch_league_status("pre_draft"):
        resp = market_overlay_endpoint(sent=[one_player], received=[three_players])
    assert resp["forced_cut_david"]["penalty"] == 0
    assert resp["forced_cut_david"]["overflow"] == 0

def test_competitive_realism_gate_blocks_filler_package():
    """Asserts that the realism gate flags and blocks packages filled with cheap assets."""
    resp = market_overlay_endpoint(
        sent=[{"sleeper_id": "premier_wr", "value": 6000}],
        received=[{"sleeper_id": f"filler_{i}", "value": 800} for i in range(5)]
    )
    assert resp["realism_gate_passed"] is False
    assert len(resp["realism_violations"]) > 0

def test_phase22_reconciler_unchanged_by_market_values():
    """Verifies that the core Phase 22 reconciler output is 100% unaffected by market overlays."""
    result_baseline = reconcile_trade_roster(sent, received, pvo, snapshot)
    perturb_all_fc_market_values(multiplier=100.0)
    result_perturbed = reconcile_trade_roster(sent, received, pvo, snapshot)
    assert result_baseline == result_perturbed
```

---

## 8. Explicit Out-of-Scope (from GD2 & WB)

*   Three-way trade configuration.
*   IDP and defense statistics/ingestion.
*   Auto-scraping KTC values (ToS violation).
*   Databricks bundle promotion or jobs (local-first first).
*   Surfacing market-reconciled totals as model-approved verdicts.
*   Tuning `NOISE_BAND = 0.10` before mid-July 2026.
*   Integrating VORP "Waiver Dead State" (deferred to Phase 24).
