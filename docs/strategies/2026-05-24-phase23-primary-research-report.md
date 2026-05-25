# Phase 23 Primary Research Report: Codebase & Data Schema Audits

**Date:** May 24, 2026  
**Author:** Dynasty Genius PM (Gemini)  
**Governing Document Version:** 1.0.0 (Product Constitution & North Star Architecture Compliant)  
**Status:** COMPLETE (Ready for David's Review)

---

## 1. Executive Summary

This report documents the **Primary Research** conducted for **Phase 23: Trade Lab Market Overlay & Competitive Realism Engine**. 

Through a targeted, read-only audit of the local codebase, raw caches, and schemas, we have mapped out exactly how Dynasty Genius represents draft picks, models trade parity, calculates package/consolidation penalties, and runs the post-trade roster reconciliation pipeline. 

This research establishes the precise technical boundaries, data contracts, and options for integrating FantasyCalc market data overlays without violating our core product rule: **zero market data leakage into model training or xVAR parameters.**

---

## 2. Codebase Audits & Data Contracts

### 2.1 The FantasyCalc Pick Schema Contract
An audit of `src/dynasty_genius/adapters/fantasycalc_adapter.py` and the active API cache at `app/cache/fantasycalc/market_values.json` confirms the exact conventions used to serialize and cache draft picks:

1. **JSON Data Structure**: In the raw JSON response, draft picks are represented inside the standard player array but carry a distinct position tag and unique ID patterns:
   * **Position tag**: `"position": "PICK"`.
   * **Slot Pick Key (Current Year)**: `sleeperId` is keyed using the slot template `"DP_{round}_{slot}"` (both 0-indexed).
     * *Example*: `DP_0_0` = 1.01, `DP_0_11` = 1.12, `DP_1_0` = 2.01, `DP_3_11` = 4.12.
   * **Generic Future Pick Key**: `sleeperId` is keyed using the year-round template `"FP_{year}_{round}"`.
     * *Example*: `FP_2027_1` = 2027 1st, `FP_2028_2` = 2028 2nd.
   * **Value Field**: Market value is stored as an integer under `value` (e.g., `"value": 6863` for 1.01).
2. **Missing Signals on Picks**: 
   * `maybeMovingStandardDeviation` and `maybeTradeFrequency` are **permanently null** for all pick entries in the API response.
   * `trend30Day` is populated for slot picks but remains null for generic future picks.

### 2.2 Trade Lab Evaluator Math (`evaluator.py`)
Our core trade evaluation utilizes pure model-native xVAR calculations:

*   **Pydantic Models**:
    *   `TradeAsset`: Carries `player_id`, `xvar`, `dvs`, `dvs_engine`, `position`, `is_prospect`, and `decision_supported`.
    *   `TradeEvaluation`: Aggregates the two sides, calculates `fairness_delta`, and evaluates if it is within the parity band.
    *   `_lock_decision_supported`: Both models enforce a strict `mode="before"` class validator that coerces `decision_supported` to `False` under all construction flows.
*   **Consolidation Factor (Package Penalty)**:
    We apply a non-linear decay multiplier based on the number of roster-consuming assets ($N$) with positive, non-null xVAR:
    $$f_{\text{consolidation}}(N) = \max \left( \text{CONSOLIDATION\_FLOOR}, 1.0 - \text{CONSOLIDATION\_KAPPA} \times (N - 1) \right)$$
    *   *Constants*: Loaded from `engine_b_contract.py` where $\kappa = 0.05$ and Floor $= 0.70$.
*   **Parity Band**:
    $$\text{TRADE\_PARITY\_BAND} = 0.10 \quad (10\% \text{ of the max side value})$$
*   **Draft Pick Valuation (`value_draft_pick`)**:
    Maps bucket types (`early` $\to 3.0$, `mid` $\to 6.5$, `late` $\to 10.5$) and fits them through Engine A prospect scoring:
    $$xVAR = (DVS - ReplacementDVS_{\text{Engine\_A}}) \times \Lambda_{\text{pos}}$$
    *   No market data is touched in this path.

### 2.3 Roster Reconciler Pipeline (`reconciler.py`)
The Phase 22 reconciler (`reconcile_trade_roster()`) handles capacity and forced-cut calculations:

1. **Roster Footprint**: Splits assets into players and picks. Roster capacity math (`players_out` / `players_in`) excludes assets where `is_prospect` is `True`.
2. **Post-Trade Headcount**:
   $$\text{post\_trade\_total} = \text{current\_total} - |players\_out| + |players\_in|$$
3. **Forced Cut Penalty**:
   If $\text{post\_trade\_total} > \text{total\_capacity}$, it copies the Sleeper snapshot, removes sent players, appends received players, runs the `RosterCutEngine` via `compute_roster_cut_candidates()`, and selects the top-$C$ cut candidates (where $C$ is the overflow count).
4. **xVAR Deduction**:
   The reconciler sums the positive raw model xVAR values of the cut candidates and subtracts it directly from the received side's value:
   $$\text{adjusted\_received\_value} = \max(0.0, \text{base\_received\_value} - \text{forced\_cut\_penalty})$$

---

## 3. Percentile Divergence & Volatility Gates

An audit of `market_overlay_service.py` and `universe_market_divergence.py` outlines how percentiles are computed post-scoring:

*   **Mid-Rank Tie-Breaker Formula**:
    $$\text{pct\_rank}(V, x) = \frac{\sum (V < x) + 0.5 \times \sum (V == x)}{N}$$
    This calculates positional percentiles for the market cohort ($V_{\text{market}}$, full FantasyCalc list) and the model cohort ($V_{\text{model}}$, valid PVO `projection_2y` rows in the active batch).
*   **Divergence Band**:
    $$\text{NOISE\_BAND} = 0.10$$
    *   Delta = Model Percentile - Market Percentile.
    *   $|Delta| < 0.10 \to$ `"aligned"`.
    *   $Delta \ge 0.10 \to$ `"model_higher_than_market"`.
    *   $Delta \le -0.10 \to$ `"model_lower_than_market"`.
*   **Safety Gates**: Full-universe signals are suppressed (`gates_blocked`) if:
    1.  **Freshness Gate**: Stale market cache data exists.
    2.  **Volatility Gate**: Market standard deviation exceeds `volatility_threshold` ($150.0$).
    3.  **Cohort Gate**: Position cohort size is less than $30$ players.

---

## 4. The Governance & Pick Valuation Option Space

A core analytical decision for Phase 23 is how we resolve pick valuations between the internal position-tied model and generic market values. We have mapped out three distinct option paths:

### Option A: Pure Model-Native (Current Default)
*   **Mechanism**: Value picks solely via `value_draft_pick()` using Engine A prospect scores. 
*   **Pros**: 100% compliant with the Product Constitution. No market data is blended.
*   **Cons**: Coarse bucket limits ("early/mid/late") ignore exact market price differentials between specific draft slots.

### Option B: Parallel Display (Recommended)
*   **Mechanism**: Maintain clean Engine A prospect xVAR and display the normalized FantasyCalc market values side-by-side on the trade reconciliation card. Never mathematically blend them into a single score.
*   **Pros**: Zero market-leakage risk. David sees both model-native production projection and real-world market liquidity value. Maintains absolute analytical honesty.
*   **Cons**: Requires displaying two separate numeric evaluation blocks on the Trade Lab interface.

### Option C: The Hybrid Blended Value
*   **Mechanism**: Blend normalized FantasyCalc value with expected Engine A prospect DVS:
    $$xVAR_{\text{pick}} = w_m \times \left(\frac{Value_{\text{FC}}}{1000}\right) + (1 - w_m) \times \mathbb{E}[xVAR_{\text{Engine\_A}}]$$
    *Where expected Engine A xVAR is the position-weighted average ($25\%$ QB, $25\%$ RB, $40\%$ WR, $10\%$ TE).*
*   **Pros**: Emits a single blended pick score that represents both long-term production and current market liquidity.
*   **Cons**: **Requires an explicit governance exemption**. Creates a mixed-provenance "xVAR" that violates the display-only market-isolation invariant.

---

## 5. Live Data Audit Findings

*   **Total Universe Rows**: 12,189.
*   **FC Market Overlay Rows**: 396.
*   **Engine B Scored**: 211.
*   **Engine A Scored**: 86.
*   **PRE_MODEL (no model score)**: 99.
*   **The Jefferson Case**: Justin Jefferson is `PRE_MODEL` (unvalued in the active PVO batch due to inactivity). For Phase 23, `PRE_MODEL` assets must display raw FantasyCalc value with an explicit caveat warning, and never coerce null xVAR to 0.0.

---

### Verification and Compliance Signature
**Gemini PM Core Audit:** Passed. This design preserves the medallion silver/gold layers, maintains identity mappings via Sleeper player IDs, enforces Pydantic coercion locks on all Trade and Cut models, and guarantees that no market data enters predictive training pipelines.
