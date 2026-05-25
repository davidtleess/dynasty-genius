# Phase 23 Research Brief: Market Realism & Draft Pick Data Contracts

**Date:** May 24, 2026  
**Author:** Lead Web & Codebase Researcher  
**Destination Path:** `/Users/davidleess/dynasty-genius-product/docs/strategies/2026-05-24-phase23-market-realism-research.md`  
**Governing Document Version:** 1.0.0 (Product Constitution & North Star Architecture Compliant)  
**Status:** PROPOSED (Pending David's PM Review and Approval)

---

## Executive Summary

To support the upcoming **Trade Lab Market Reconciler** and ensure absolute market realism without violating our **Product Constitution** (zero market-derived features in model training or xVAR parameters), this Phase 23 research brief establishes the analytical foundations for:
1. Resolving draft pick valuations between internal position-tied Engine A models and generic, live market assets.
2. Integrating the mathematical principles of **Value Consolidation / Package Penalties** and **Roster Capacity / Opportunity Costs of Forced Cuts** into a unified trade evaluation metric.
3. Specifying exact code contracts and database mappings for FantasyCalc draft pick representation.

---

## Part 1: Primary Research (Local Codebase & Schemas)

### 1.1 FantasyCalc Draft Pick Representation & Cache Mapping
An audit of `src/dynasty_genius/adapters/fantasycalc_adapter.py` and the raw seasonal cache file at `app/cache/fantasycalc/market_values.json` reveals how draft picks are represented, keyed, and priced by FantasyCalc:

*   **JSON Data Structure:** In the raw JSON response, draft picks are represented inside the standard player array but carry a distinct position tag and unique ID patterns:
    *   **Position Identifier:** `position` is explicitly set to `"PICK"`.
    *   **Pick Name Format:** `name` is represented as a string identifying the specific slot (e.g., `"2026 Pick 1.01"`, `"2026 Pick 1.02"`).
    *   **Source Identifiers (Sleeper & MFL):** `sleeperId` and `mflId` are keyed using the draft pick slot template: `"DP_{year_delta}_{pick_index}"`.
        *   *Example:* Current-year Pick 1.01 is represented as `"sleeperId": "DP_0_0"`, Pick 1.02 is `"sleeperId": "DP_0_1"`, and Pick 2.01 is `"sleeperId": "DP_0_12"`.
    *   **Valuation Field:** The market price is stored as an integer under the `value` field (e.g., `"value": 6863` for 2026 Pick 1.01).
*   **Future Picks Representation:** For subsequent years where specific draft slots are not yet determined (e.g., 2027 and 2028), FantasyCalc represents picks generically:
    *   **Generic Pick Buckets:** Future picks are represented in the database as `"2027 Early 1st"`, `"2027 Mid 1st"`, `"2027 Late 1st"`, or `"2027 1st"` (representing a random/consensus pick).
    *   **API Query Parameters:** The current adapter queries the API with:
        `https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1`
        which matches our Superflex PPR (no TEP) league context perfectly.

### 1.2 Market Overlay Divergence Engine Analysis
A detailed review of `src/dynasty_genius/services/market_overlay_service.py` and `src/dynasty_genius/universe_market_divergence.py` shows how the divergence engine operates:

*   **Percentile-Rank Calculation:** The service utilizes a mid-rank tie-breaker formula:
    $$\text{pct\_rank}(V, x) = \frac{\sum (V < x) + 0.5 \times \sum (V == x)}{N}$$
    This calculates positional percentiles for the market cohort ($V_{\text{market}}$, using the full FantasyCalc player list) and the model cohort ($V_{\text{model}}$, using PVOs in the batch containing a valid `projection_2y` / model-backed score).
*   **Draft Pick Percentiles Defect:** The engine currently has **no way to resolve draft pick percentiles**. Under the current codebase:
    *   Draft picks do not have an active player projection (`projection_2y` is `None`).
    *   Because they lack Engine B active projections, they fall into the `if pvo.projection_2y is None:` branch.
    *   This automatically assigns them a `divergence_flag = "model_uninformative_rookie"` or `"UNAVAILABLE"`, completely bypassing percentile-rank calculations.
    *   Furthermore, draft picks are in the position cohort `"PICK"`, but since they lack `projection_2y`, no model cohort is assembled, leaving them permanently unresolved.

### 1.3 Trade Lab Draft Pick Valuation Discrepancies
An inspection of `value_draft_pick` in `src/dynasty_genius/trade_lab/evaluator.py` exposes a significant structural discrepancy:

*   **Internal Model-Native Path:**
    *   The evaluator maps the `pick_bucket` ("early" $\to 3.0$, "mid" $\to 6.5$, "late" $\to 10.5$) to a draft pick number.
    *   It then forces a position assignment and calls the pre-draft prospect scorer: `score_prospect(position, pick, round, age=21.5)`.
    *   It converts the resulting prospect DVS to xVAR: $xVAR = (DVS - ReplacementDVS) \times \Lambda_{\text{pos}}$.
*   **Key Discrepancies:**
    1.  **Position-Tied vs. Asset-Generic:** Our internal model requires a position assignment (QB, RB, WR, TE) to score a pick. In real leagues, future draft picks are highly liquid, position-agnostic assets.
    2.  **Granularity:** The model utilizes coarse three-tier buckets ("early", "mid", "late") for all rounds. The market values specific slots (1.01 through 3.12) with high precision when the order is known.
    3.  **Rookie Fever & Appreciation Curve:** The internal model values future picks statically based on college historical production features. The market values future picks dynamically, showing high appreciation as the rookie draft approaches.

---

## Part 2: Secondary Research (Web Search & Dynasty Theory)

### 2.1 Dynasty Trade Calculator Mechanics
Web-based research on leading industry calculators (KeepTradeCut, FantasyCalc, DynastyNerds) reveals standardized behavioral models for trade realism:

*   **Fairness Parity Bands & Rejection Margins:**
    *   Calculators do not enforce binary accept/reject boundaries but establish "Parity Bands."
    *   A trade is labeled **"Fair"** if the value delta between the two sides is under **10% to 15%** of the more valuable side.
    *   If the value delta exceeds **15%**, it is labeled **"Lopsided"**, triggering rejection or caution indicators. KTC reverse-engineers this delta to suggest a "Player to even the trade."
*   **Value Consolidation / Package Penalty Formulas:**
    *   Dynasty trade markets suffer from the "four quarters for a dollar" problem: a manager cannot trade four bench players for Patrick Mahomes, even if their raw point sums are equal.
    *   Calculators utilize non-linear Value Adjustments (Package Penalties). While KeepTradeCut's exact raw coefficients are proprietary, the consolidation penalty typically applies a decay factor to the smaller assets or a premium to the "stud" asset.
    *   *Mathematical Model:* If Side B contains $N$ roster-consuming players ($N \ge 2$), the consolidated trade value is modeled as:
        $$\text{Value}_{\text{consolidated}} = \text{Value}_{\text{nominal}} \times f_{\text{consolidation}}(N)$$
        Where $f_{\text{consolidation}}(N)$ decays as $N$ increases (e.g., $1.0$ for 1 player, $0.90$ for 2 players, $0.80$ for 3 players).

### 2.2 Roster Capacity Valuation & Opportunity Cost
Analysis of seminal writings by industry-validated analysts (Adam Harstad, Rich Hribar, and Scott Fish) highlights a critical gap in standard trade calculators:

*   **Adam Harstad (Footballguys, "Dynasty, in Theory"):**
    *   *Core Principle:* Roster spots are a **finite, developmental resource**. Benches should be populated with high-upside "prospects" (players with high probability of value appreciation), not low-ceiling roster filler.
    *   *Opportunity Cost:* Every roster spot occupied by an unproductive asset carries a high opportunity cost: the forfeit of churning that spot on the waiver wire for high-upside rookies.
    *   *Strategic Trade Implications:* Managers should actively pursue "2-for-1" or "3-for-1" trades to consolidate talent, which structurally frees up highly valuable roster spots.
*   **Rich Hribar (Sharp Football Analysis / Dynasty Nerds):**
    *   *Core Principle:* Multi-player packages ("2-for-1" or "3-for-1") carry a hidden tax: the receiving team must make **forced cuts** to comply with league roster capacity.
    *   *Opportunity Cost of Forced Cuts:* Standard trade calculators treat the "depth" side of a trade as pure value. In reality, the manager receiving the package must cut active players from their bench. The value of these cut players represents a direct capital loss that must be subtracted from the trade's nominal value.
*   **Scott Fish & RotoViz:**
    *   The value of a roster spot is inversely proportional to bench depth. In leagues with standard or shallow rosters, the package penalty must be severe because the opportunity cost of forced cuts represents starter-adjacent value.

---

## Part 3: Trade Lab Market Reconciler Specs & Formulas

To resolve these market realism anomalies while strictly preserving the **Product Constitution's** market-leakage boundaries, we propose the following mathematical specs for the **Trade Lab Market Reconciler (Phase 23/24)**:

### 3.1 The Draft Pick Realism Contract
Since future picks are position-agnostic and appreciate dynamically, we establish a **Rookie Pick Hybrid Value** ($xVAR_{\text{pick}}$) formula that blends internal model expectation with normalized live market data:

1.  **Market Scale Normalization:** Normalize the raw FantasyCalc points ($Value_{\text{FC}}$) to our xVAR scale:
    $$xVAR_{\text{market}} = \frac{Value_{\text{FC}}}{S}$$
    Where $S$ is a scaling factor calibrated against elite active assets (e.g., if Bijan Robinson has a market value of $10,256$ and an internal xVAR of $10.25$, then $S = 1000.0$).
2.  **Expected Model Value:** Define the expected internal xVAR of a pick by averaging our Engine A prospect values across the four skill positions, weighted by position draft frequency:
    $$\mathbb{E}[xVAR_{\text{Engine\_A}}] = \sum_{p \in \{\text{QB, RB, WR, TE}\}} w_p \times xVAR_{\text{Engine\_A}}(p, \text{slot})$$
    *(Default Weights based on historical Superflex PPR draft capital: $w_{\text{QB}} = 0.25$, $w_{\text{RB}} = 0.25$, $w_{\text{WR}} = 0.40$, $w_{\text{TE}} = 0.10$)*
3.  **Hybrid Valuation Formula:** Blends the internal model expectation and the normalized market price:
    $$xVAR_{\text{pick}} = w_{\text{m}} \times xVAR_{\text{market}} + (1 - w_{\text{m}}) \times \mathbb{E}[xVAR_{\text{Engine\_A}}]$$
    *   For **Current-Year Picks** (where the draft class and order are fully known): $w_{\text{m}} = 0.80$ (highly market-reflective).
    *   For **Future-Year Picks** (e.g., 2027/2028 where standings are unknown): $w_{\text{m}} = 0.50$ (blending long-term asset value with current market expectations).

### 3.2 Integrated Package Penalty & Roster Capacity Reconciler
We mathematically specify how the **Trade Lab Market Reconciler** must adjust trade valuations using our newly implemented Phase 21/22 features:

1.  **Forced Cut Penalty:** Let $C$ be the number of forced cuts required post-trade (Overflow). The forced-cut penalty is the sum of the raw xVAR values of the top-$C$ cut candidates identified by the `RosterCutEngine`:
    $$Penalty_{\text{Forced\_Cuts}} = \sum_{i=1}^{C} xVAR(\text{Candidate}_i)$$
    *(If $C = 0$, $Penalty_{\text{Forced\_Cuts}} = 0.0$)*
2.  **Consolidation Factor:** Let $K$ be the number of active, roster-consuming starter assets on the package side. We apply a non-linear consolidation penalty to that side:
    $$f_{\text{consolidation}}(K) = \max \left( \text{CONSOLIDATION\_FLOOR}, 1.0 - \kappa \times (K - 1) \right)$$
    *(Defaults from `engine_b_contract.py`: $\kappa = 0.05$, Floor $= 0.70$)*
3.  **Unified Reconciled Trade Value:**
    Let Side A be David's sent assets, and Side B be David's received assets. The reconciled value of the trade for David is calculated as:
    $$Value_{\text{Reconciled}} = \left( \sum_{b \in \text{Side B}} xVAR_b \times f_{\text{consolidation}}(K_{\text{received}}) \right) - Penalty_{\text{Forced\_Cuts}}$$

This formula ensures that if David trades 1 star for 3 bench players, the trade is hit with:
*   A consolidation penalty on the incoming package.
*   A forced-cut penalty representing the capital loss of the players he is forced to drop to open up the roster spots.

---

## Part 4: Product Constitution Compliance Audit

We have verified that this proposed design holds the line on our strict architectural boundaries:
*   **Separation of Concerns:** Normalized market values ($xVAR_{\text{market}}$) and the resulting hybrid draft pick value ($xVAR_{\text{pick}}$) are used **exclusively** within the `TradeLab` overlay service and `/api/trade/reconcile` endpoints.
*   **Zero Leakage:** No FantasyCalc data, raw market point scales, or hybrid $xVAR_{\text{pick}}$ calculations are written to the Feature Store or used during Engine A or Engine B model training.
*   **Status Invariance:** Divergence flags and market reconciliation metrics do not modify a player's underlying `dynasty_value_score` or active-player features, maintaining absolute analytical honesty.

---

## Part 5: Live Data Sweep — Verified Findings (Claude Code, 2026-05-24)

> This section documents what the live codebase and artifacts actually contain, verified by direct inspection. It complements Parts 1–4 and flags one governance concern for David's ruling before spec authorship begins.

### 5.1 FC Pick Key Convention — Verified

From live cache (`app/cache/fantasycalc/market_values.json`, captured `2026-05-25T00:54:43Z`, 461 entries):

- **64 pick entries** with `position: "PICK"`.
- Two key schemes confirmed in `sleeperId` / `mflId`:
  - Exact slot: `DP_{round}_{slot}` — both 0-indexed. `DP_0_0` = 1.01, `DP_1_0` = 2.01, `DP_3_11` = 4.12.
  - Generic future: `FP_{year}_{round}` — e.g., `FP_2027_1`, `FP_2028_2`.
- **Part 1.1 correction:** The generic pick buckets are `FP_{year}_{round}` (year-round combos), not "Early/Mid/Late 1st" buckets. FC does not expose early/mid/late at the generic-future level in the API cache — those labels appear in the FC web UI only.
- `maybeMovingStandardDeviation` and `maybeTradeFrequency` are **null on all pick entries** — no volatility or trade-frequency signal is available for picks from the API.
- `trend30Day` is populated on slot picks but null on generic-future picks.

### 5.2 Pick Value Reference (Current Cache)

| Slot | FC Value |   | Generic Future | FC Value |
|---|---|---|---|---|
| 1.01 | 6,863 | | 2026 1st | 3,265 |
| 1.06 | 3,446 | | 2027 1st | 3,054 |
| 1.12 | 2,340 | | 2028 1st | 2,176 |
| 2.01 | 2,223 | | 2029 1st | 2,040 |
| 2.12 | 1,435 | | 2027 2nd | 1,590 |
| 3.01 | 1,390 | | 2027 3rd | 1,101 |
| 3.12 | 1,035 | | 2027 4th | 850 |
| 4.12 | 809  | | | |

Spread within a single round: 1st-round range = 6,863 − 2,340 = **4,523 FC points** (1.01 vs 1.12). This means the generic `FP_2026_1` at 3,265 is roughly mid-round — a +/− 40% range from true value depending on slot. This spread is the primary risk of Option A (generic futures).

### 5.3 Picks Are Absent from PVO and Divergence Pipeline — Confirmed

- `universe_pvo_latest.json`: **0 pick rows**. The PVO assembler (`src/dynasty_genius/pvo_assembler.py`) processes Sleeper player entries only. Future picks are not Sleeper player records — they are structured objects in `snapshot.future_picks[]`.
- `universe_market_divergence_latest.json`: **0 pick rows**. No divergence signal for any pick.
- All 109 `future_picks` in the current snapshot carry `pick_value_status: "deferred"` — no numeric value anywhere in the system.

### 5.4 David's Current Pick Holdings (Snapshot 2026-05-24T17:20Z)

David holds **14 future picks**, all `current_roster_id=1`:

| Year | Round | From Roster | Origin |
|---|---|---|---|
| 2027 | 1 | 1 | own |
| 2027 | 1 | 3 | traded in |
| 2027 | 1 | 10 | traded in |
| 2027 | 2 | 1, 3, 6 | own + 2 traded in |
| 2027 | 3 | 1, 7 | own + 1 traded in |
| 2028 | 1, 2, 3 | 1 | own |
| 2029 | 1, 2, 3 | 1 | own |

Three 2027 firsts owned by David (from teams 1, 3, 10) are best mapped to `FP_2027_1` in the FC cache at 3,054. Without draft order, we cannot resolve which slot is team 1's vs team 3's.

### 5.5 Market Overlay Population — Verified

| Metric | Value |
|---|---|
| Total universe rows | 12,189 |
| FC market overlay rows | 396 |
| Of those: Engine B scored | 211 |
| Of those: Engine A scored (prospects) | 86 |
| Of those: PRE_MODEL (no model score) | 99 |
| `gates_passed` (active divergence signal) | 167 |
| `INSIDE_BAND` | 106 |
| `UNAVAILABLE` (PRE_MODEL or gate fail) | 123 |

xVAR range across 396 market overlay rows: **−101.7 to +58.0** (mean ≈ 0.2).
FC market value range: **11 to 10,290** (mean ≈ 1,748).
|model − market| percentile delta for `gates_passed` rows: **0.100 to 0.866** (mean ≈ 0.261).

**Divergence ledgers (all positions):** All four `divergence_ledger_*.json` files are **empty** — no historical price delta time-series exists yet.

### 5.6 PRE_MODEL in Market Overlay (The Jefferson Case)

99 of the 396 FC-matched rows are PRE_MODEL (no Engine B/A valuation). Their `divergence.signal_status = "unavailable"`. They have an FC market value but no model xVAR. Justin Jefferson is PRE_MODEL **and** absent from the 396 FC-matched rows — he was present in the Sleeper universe but the crosswalk did not resolve his Sleeper ID to an FC entry in the current batch.

For Phase 23 display, these cases require separate treatment: show FC market value with explicit "No model valuation — market estimate only" caveat, and never coerce null xVAR to 0.

### 5.7 Governance Concern: Section 3.1 Hybrid xVAR Formula

**This requires David's ruling before Phase 23 spec is authored.**

Section 3.1 proposes:
$$xVAR_{\text{pick}} = w_m \times xVAR_{\text{market}} + (1 - w_m) \times \mathbb{E}[xVAR_{\text{Engine\_A}}]$$

This blends a market-derived value (`xVAR_market`, normalized from FC points) with model-native xVAR into a single number emitted by the Trade Lab. The Product Constitution states:

> *"Market data is overlay-only and never enters Engine A or Engine B feature inputs."*

The hybrid formula does not modify Engine A/B **training inputs** — it computes a display-layer trade value. However, it does create a number labelled "xVAR" that is partially market-derived, which blurs the model-vs-market distinction the architecture depends on. The Phase 17 governance locks explicitly state market data must remain display-only and `signal_status` must not flip `decision_supported`.

**Three safer alternatives that avoid the governance concern:**

| Option | Pick Value | Governance |
|---|---|---|
| **A (current default):** Engine A only | `value_draft_pick(round, bucket, position, age)` | Clean — model-native, no market blend |
| **B (FC overlay, parallel display):** Show FC market value and Engine A xVAR side-by-side, never blended | Two separate fields | Clean — market is display-only, explicitly labelled |
| **C (hybrid as proposed):** Blend FC + Engine A into a single xVAR-labelled number | `xVAR_pick = w_m * xVAR_mkt + (1-w_m) * xVAR_A` | **Requires explicit David ruling** — creates mixed-provenance xVAR |

The existing Phase 22 reconciler uses **Option A** (Engine A xVAR for pick assets via `value_draft_pick()`). Moving to Option C in Phase 23 would require a governance exception.

### 5.8 Open Questions for David (Data-Layer)

1. **Pick valuation**: Option A (Engine A only, current behavior), B (FC parallel display), or C (hybrid — requires governance ruling)?
2. **Generic vs slot resolution**: Accept mid-round FC estimate for all futures, or block FC pick display until slot is resolved?
3. **PRE_MODEL with market data**: Show FC value with caveat, or suppress market value for assets the model cannot score?
4. **Divergence ledger history**: Populate `divergence_ledger_*.json` before Phase 23, so the UI can show price trend context?
5. **Phase 23 UI scope**: Standalone trade form or integrated into the existing draft board?
