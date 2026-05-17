# Dynasty Genius Phase 15 Research Brief
## Trade Lab Architecture: Multi-Asset Logic and Cross-Positional Scaling

---

## 1. Executive Recommendation

**Implement a cardinal multi-asset trade evaluation system (Trade Lab) driven by a non-linear cross-positional value bridge.** Transition from position-isolated VAR (Phase 14) to a **Unified Trade Currency (UTC)** anchored in **2027 1st-Round Equivalents (E27)**. Adopt the **Exponential Scarcity Decay** model (DynastyProcess lineage) to prevent "bench-clogger exploitation" (where multiple low-value assets sum to an elite asset). **Confidence: HIGH on UTC anchoring (required for decision-grade trade execution); MEDIUM on cross-positional coefficients (requires league-specific calibration against veteran scoring distribution).** Trade Lab is the capstone of the valuation layer; it transforms predictive modeling into actionable portfolio management.

---

## 2. Research Objectives & Evidence

### **A. Cross-Positional Value Scaling (The Bridge)**
Phase 14 established within-position VAR, but comparing a QB's +5.0 VAR to a WR's +5.0 VAR requires a multiplier to account for Superflex demand.
*   **Evidence:** Campus2Canton studies show QBs in Superflex command a 2.5–3.0x premium over non-QBs at the same production percentile.
*   **Strategy:** Research **Positional Multipliers (β_pos)** derived from the league-specific replacement baseline gap.

### **B. Multi-Asset Summation Logic (The "2-for-1" Problem)**
Traditional addition (Value_A + Value_B = Value_C) fails in dynasty football due to roster spot constraints and "Replacement Cost."
*   **Evidence:** Sabermetric "Winner of the Trade" studies show that the side receiving the best single player wins ~65% of the time, regardless of the summed value of the return.
*   **Strategy:** Research **Scarcity Penalties** for multi-player packages to ensure that consolidating value into a single elite asset is mathematically prioritized.

### **C. E27 Currency Anchoring (2027 1st-Equivalents)**
Trade decisions are ultimately expressed in "Picks."
*   **Evidence:** KTC and FantasyCalc anchor their internal ELO scales to a generic "Mid 1st."
*   **Strategy:** Research the mathematical mapping between **DVS-space** and **Pick-space** to allow "1.50 E27" to mean "One 2027 1st and one 2027 2nd."

---

## 3. Proposed Phase 15 Implementation Workstreams

**WS-1: Unified Trade Currency (UTC) Normalization**
*   Map the 0–100 DVS scale to a scarcity-adjusted UTC scale.
*   Implement the positional scarcity multipliers: **UTC = DVS × β_pos × Scarcity_Coefficient**.

**WS-2: Trade Lab Evaluation Engine**
*   Build the `evaluate_trade()` module in `trade_analyzer.py`.
*   Input: `Side_A (Player list + Picks)` vs `Side_B (Player list + Picks)`.
*   Output: `Trade_Fairness_Index`, `Roster_Spot_Tax`, and `Winner_Flag`.

**WS-3: Cross-Positional Calibration Audit**
*   Run a paired-rank regression of our internal UTC against KTC Superflex consensus.
*   Target: No material rank-inversions (e.g., our model shouldn't value QB32 over WR1 unless the scoring projection justifies a catastrophic market mispricing).

**WS-4: Trade Surface UI (v0)**
*   Implement a minimal CLI/API surface to test trade scenarios: `GET /trade-lab?side_a=dg_123&side_b=dg_456,dg_789`.

---

## 4. Risks & Failure Modes

1.  **The Bench-Clogger Trap:** If the package penalty is too low, the model will suggest trading Justin Jefferson for three WR4s. 
    *   *Mitigation:* Enforce a **Package Decay Function** where every additional player in a trade contributes diminishing marginal UTC.
2.  **Market Drift:** If our UTC becomes too decoupled from KTC/FantasyCalc, the model becomes "untradable" in a real league.
    *   *Mitigation:* Maintain the **Market Overlay** on the Trade Surface to show David "Internal Value" vs "Market Perception" side-by-side.
3.  **Draft Pick Latency:** Evaluating 2027 picks requires a stable "Prior" for class strength.
    *   *Mitigation:* Use the **0.20/1.00/1.50 E27 anchor points** defined in the trade logic decision record.
