# Design Spec: Decision Matrix Dashboard

**Status:** DRAFT  
**Date:** 2026-05-08  
**Author:** Gemini (PM)  
**Objective:** Provide a high-density pre-model context interface for David's dynasty league, merging internal math, market overlays, and situational nuance without issuing trade instructions.

---

## 1. Core Architecture

The dashboard is a **Local-First, decoupled system** designed to operate under a \$10/24h Databricks cost cap.

### Components:
- **Signal Engine (`app/services/signal_engine.py`):** A Python logic layer that calculates context signals by joining internal scores with league context.
- **Data Layer:**
    - `resources/david_league_context.json`: David's current roster and future picks.
    - `resources/mock_market_consensus_seed.sql`: Mock market overlay values for context only.
    - `resources/situational_notes.json`: Curated beat-writer intel and depth chart shifts.
- **The View:** A single-file HTML/JS application served via the Superpowers Visual Companion, enabling interactive sorting and filtering.

---

## 2. The "Context Row" Logic

Each row (Player or Pick) will display the following data points:

| Column | Source | Purpose |
| :--- | :--- | :--- |
| **Internal Value** | Engine A/B | Production forecast component (RAS, Dominator, Usage). |
| **Market Delta** | Market Overlay | % difference between internal value and the market overlay. |
| **Fragility** | Age Cliff Model | Continuous curve risk (0.0 to 1.0) based on position-specific cliffs. |
| **Situational Buzz**| Curated Notes | Depth chart risers, handcuffs, and beat-writer "scoops." |
| **Context Signal** | Signal Engine | Neutral pre-model state such as `AGE_CLIFF_CONTEXT`, `MARKET_DIVERGENCE_CONTEXT`, or `NO_CURRENT_SIGNAL`. |

---

## 3. The "Intel Guardrail" (Governance)

To prevent emotional over-indexing on training camp hype:
1.  **Math-First Hierarchy:** Beat intel will **never** be an input feature for Engine A/B mathematical models.
2.  **Timing Context:** Intel is strictly a context modifier and cannot issue timing instructions on its own.
3.  **Source Reliability:** Notes must be tagged with reliability tiers (Tier 1: Verified Starter Change, Tier 3: Speculative Buzz).

---

## 4. Implementation Strategy (TDD)

1.  **Phase 1: Signal Logic:** Build `test_signal_engine.py` first. Verify CMC receives age-cliff context based on age risk without issuing a trade instruction.
2.  **Phase 2: PVO Assembly:** Populate the `situational_notes.json` structure.
3.  **Phase 3: Visual Mockup:** Build the HTML matrix using the Visual Companion.
4.  **Phase 4: "Scan Intel" Tool:** (Future) Add a `web_fetch` trigger to scan for player-specific updates.

---

## 5. Success Criteria
- [ ] CMC and Jonathan Taylor correctly reflect their "Age Cliff" risk.
- [ ] Ahmad Hardy is identified as a "Riser" based on situational buzz.
- [ ] No market data (KTC) leaks into the internal value calculation.
- [ ] Total Databricks spend for this feature remains \$0.00 (Local-First).
