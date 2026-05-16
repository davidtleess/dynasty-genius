# Phase 13 Research Synthesis: Advancing Engine A and Tight End Integrity
**Status:** Merged Research Brief (Round 2)
**Lanes:** 3A (Engine A Draft Capital), 3B (TE Remodel), 3C (Identity Audit)

## 1. Executive Recommendation

The fundamental recommendation for Phase 13 is a **gated, multi-track execution model** that prioritizes data integrity (3C) as the non-negotiable substrate for model improvement (3B).

**Recommended Sequencing:**
*   **Subphase 13.1 (Parallel Track):** Execute the **Identity Resolution Audit (3C)** and the **Engine A Draft-Capital Step Function research (3A)**. 3A is decoupled from high-fidelity collegiate features and relies on existing verified draft metadata, allowing it to move asynchronously.
*   **Subphase 13.2 (Gated Track):** Commences the **TE Remodel (3B)** only after the 3C audit confirms a **deterministic mapping loss-rate of < 2%** for the 2018–2025 drafted TE cohort.

This structure adheres to the "Be right, not fast" Prime Directive, ensuring that granular PFF collegiate features do not "silently poison" the training matrix through identifier collisions.

---

## 2. Evidence Table

| Claim | Source Document | Confidence | Implementation Implication |
| :--- | :--- | :--- | :--- |
| RB peak production age is **25.46** (Apex Fantasy Leagues). | Research (A) | High | Anchor RB aging curves at 25-26; avoid hard cliffs. |
| Draft capital signal is a non-linear **step function**, not linear/log. | Framework (B) | High | Transition Engine A from `pick` integer to Ordinal Categorical bins. |
| QB fantasy hit rate collapses from **59.5%** (R1) to **14.3%** (R2). | Framework (B) | High | Tighten QB Tier 1 bin to picks 1–15/32. |
| WR viability extends to **Pick 75** (Mid-Round 3). | Research (A) | Medium | Extend WR Tier 2 bin through pick 75; prioritize YPRR beyond this. |
| TE sophomore jump is **+98.5%** (ESPN). | Research (A) | High | Rookie-year TE features are weak; require multi-year/ collegiate priors. |
| PFF alignment data is structural (e.g., Loveland 43% slot / 39% inline). | Research (A) | High | Use Slot/Wide snap % to segment TE archetypes before Ridge weights. |
| PFF API is enterprise-only; Consumer is **Manual CSV Export** only. | Research (A) | High | Plan for operational tax of manual fixtures in Phase 13/14. |
| `gsis_id` is the community canonical anchor for `ff_playerids`. | Research (A) | High | Centralize identity in a Silver-layer transformation; remove adapter-level logic. |

---

## 3. Conflict Resolution

| Topic | Conflict | Resolution |
| :--- | :--- | :--- |
| **Phasing** | Report A suggests 3 phases (3C -> 3A -> 3B); Report B suggests 2 (3A+3C parallel -> 3B). | **Adopt 13.1 (3A+3C parallel) / 13.2 (3B)**. 3A is safe to research offline as it uses existing metadata. 3B is the only lane truly blocked by the identity audit. |
| **TE Modeling** | Report A suggests archetypes as conditioning variables; Report B suggests sample weighting/penalty. | **Conditioning Variable First**. Inject `slot_wide_route_pct` as a continuous feature and `blocking_first` as an indicator. Use sample weighting only if backtest shows high-capital blockers still distort coefficients. |
| **Draft Bins** | Report B suggests specific integer bins (1-15 for QB); Report A suggests PAVA algorithm to find them. | **PAVA-guided Buckets**. Use Isotonic Regression (PAVA) to find the "cliffs" empirically on the 10-15 year backtest, then snap them to categorical tiers for interpretability. |
| **Fuzzy Matching** | Report A allows fuzzy matching for "residuals"; Report B strictly prohibits it in production. | **Hard Prohibition on Production Fuzzy Join**. Fuzzy matching is allowed only to generate a **Review Queue** for David. Only deterministic matches or manual overrides enter the ID map. |

---

## 4. Phase 13 Workstreams and Ordering

### **Subphase 13.1**
1.  **Workstream 3C: Identity Resolution Audit**
    *   Construct the `gsis_id` ↔ `sleeper_id` ↔ `pff_id` deterministic crosswalk via `ff_playerids`.
    *   Generate the **Null-Value Log** (players > 5 PPG missing IDs).
    *   Target: **< 2% loss-rate** for TE historical cohort (2018–2025).
2.  **Workstream 3A: Engine A Draft-Capital Step Function**
    *   Run backtest on 10–15 draft classes.
    *   Bake-off: Linear vs. Log-Decay vs. Isotonic Step Function.
    *   Evaluate via **Leave-One-Class-Out Cross-Validation (LOOCV)**.

### **Subphase 13.2**
3.  **Workstream 3B: TE Remodel (Role-Aware)**
    *   Manual ingestion of PFF Collegiate CSV Fixtures.
    *   Label prospects by archetype: **Move TE**, **In-line Receiver**, **In-line Blocker**, **Big-Slot Hybrid**.
    *   Integrate Alignment Rate features into Engine A Ridge model.

---

## 5. Explicit Out-of-Scope Items
*   **Engine B Retraining:** Veteran models remain on NFL usage data; no collegiate features injected into B.
*   **Subjective PFF Grades:** `pff_grade` and `pff_pass_block_grade` are banned. Only objective participation rates are allowed.
*   **Dynasty Value Score (DVS):** Promotion of unified score is deferred to Phase 14.
*   **TE Out of EXPERIMENTAL:** Phase 13 is a remodel; promotion requires a Phase 14 backtest validation.
*   **Live Scraping:** PFF data remains a manual `csv_fixture`.

---

## 6. Open Decisions for David
1.  **PFF Manual Tax:** Is the manual CSV-export workflow acceptable for the initial 2018–2025 TE cohort (~300 players)?
2.  **Audit Denominator:** Should "pure inline blockers" (<10 college receptions) be excluded from the 2% identity loss threshold to avoid failing the gate on non-fantasy assets?
3.  **Position-Specific Bins:** Are you comfortable with asymmetric thresholds (e.g., WR cliff at Pick 75 vs RB at Pick 64) if the data supports it, or is mathematical simplicity preferred?

---

## 7. Risks and Failure Modes
*   **Identity Collision (Silent Corruption):** An incorrect join attaches a receiver's profile to a blocker, poisoning the Ridge coefficients without triggering an error. *Mitigation: 3C Identity Audit mandatory first.*
*   **PFF Coverage Gap:** If PFF coverage for pre-2018 cohorts is spotty, the 10-class backtest for 3B may be underpowered. *Mitigation: Public-fallback path (11/12 personnel proxies).*
*   **Label Noise in Archetypes:** Human/rule-based tagging of "Move TEs" may be subjective. *Mitigation: Define thresholds for Slot/Wide Route Rate (e.g., > 40%) as the primary tagger.*

---

## 8. Proposed Acceptance Criteria
*   **3C:** gsis_id map exists for 98% of the 2018–2025 drafted TE cohort.
*   **3A:** Engine A shows a statistically significant lift in **Intra-Class Kendall τ** using step-functions vs. linear pick baseline.
*   **3B:** TE Ridge model demonstrates successful suppression of high-capital "Inline Blockers" (Archetype C) while identifying "receiving specialist" sleepers.
*   **General:** Full 530+ test suite remains green; Model Cards for Engine A updated with new feature provenance.
