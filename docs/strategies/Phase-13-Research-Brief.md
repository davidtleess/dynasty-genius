# Phase 13 Research Brief: Advancing Engine A and Tight End Integrity

## Executive Recommendation & Phasing

Phase 13 shifts focus toward resolving feature engineering inaccuracies in the rookie prospect evaluation model (Engine A) and addressing the systemic analytical failure of the Tight End valuation pipeline (Engine B). 

The empirical evidence demands a highly rigid sequencing framework to prevent predictive corruption. The introduction of granular collegiate alignment data (PFF) presents a severe risk of silent corruption if player identifiers are improperly mapped. Therefore, Phase 13 is split into two sequential subphases:

**Subphase 13.1 (Parallel Execution):**
- **Workstream 3A:** Engine A Draft-Capital Step Function
- **Workstream 3C:** Identity Resolution Audit

**Subphase 13.2 (Gated Execution):**
- **Workstream 3B:** TE Remodel (Role-Aware)
- *Hard Gate:* Commences **exclusively contingent** upon the 3C Identity Audit confirming a mapping loss-rate of < 2% for the relevant historical cohort (2018–2025 drafted TEs).

---

## 3A: Engine A Draft-Capital Step Function
*Goal: Capture the discrete value cliffs in NFL draft slots to improve Rookie Board signal.*

### Findings
- Draft capital is highly nonlinear. Historical hit rates exhibit severe, position-specific cliffs (e.g., RB value drops sharply after Round 2; QB drops catastrophically outside the top 15 picks).
- Treating `pick` as a continuous linear feature in Ridge regression forces an evenly distributed decay, failing to capture actual NFL organizational commitment.
- **Rejected Alternatives:** Smooth log-decay transforms smooth over actual boundary cliffs (e.g., the 5th-year option boundary). Splines present an unacceptable risk of overfitting small historical draft cohorts.

### Implementation Protocol
- **Ordinal Categorical Encoding:** Transform overall pick numbers into position-weighted ordinal bins (e.g., Tier 1, Tier 2, etc.).
  - *QB:* Tier 1 restricted to Top 15.
  - *RB:* Tier 1 = R1, Tier 2 = R2, Tier 3 = R3 (cliff after R3).
  - *WR:* Tier 2 extends through pick 75 (flatter decay).
- **Interaction Terms:** Incorporate interaction terms between draft tiers and collegiate efficiency (e.g., YPRR) to allow elite production to overpower weak Day 3 capital.

### Validation Gate
- **LOOCV (Leave-One-Class-Out Cross-Validation):** The model must be validated using LOOCV on historical draft classes.
- **Metric:** The primary evaluation metric is the rank correlation (Kendall τ) of players *strictly within* their specific draft class. It must show a statistically significant lift over the linear baseline.

---

## 3C: Identity Resolution Audit (The Gate)
*Goal: Ensure 100% loss-less joins across nflverse, Sleeper, and FantasyCalc/PFF.*

### The Canonical Identifier Mandate
- Introducing collegiate alignment data requires seamlessly joining PFF, CFBD, Sleeper, and nflverse.
- **Governance Rule:** Fuzzy string matching (e.g., Levenshtein distance) is strictly prohibited in production logic due to catastrophic name-collision risks (especially for TEs).

### Implementation Protocol
- **nflverse `ff_playerids` Crosswalk:** The identity layer must leverage the `ff_playerids` crosswalk table to deterministically map `pff_id` to `sleeper_id` using `gsis_id` as the anchor.
- **Null-Value Log & Divergence Ledger:** The audit must produce a Null-Value log identifying all active players (>5 PPG) excluded due to ID mapping gaps, and a Divergence Ledger detailing failed joins sent to manual review.
- **The 2% Gate:** The audit must confirm < 2% loss-rate for the 2018–2025 drafted TE cohort before 3B can begin. (Exception: Pure inline blockers with <10 career collegiate receptions may be excluded from the denominator).

---

## 3B: Tight End Remodel (Role-Aware)
*Goal: Resolve the "Experimental" status by accounting for role heterogeneity.*

### Findings
- The current TE model fails due to "label noise" from homogenizing two distinct functional roles: Pass-Catching Specialists ("Move" TE) and Inline Blockers.
- Inline blockers often secure high draft capital but possess structurally limited fantasy ceilings. The current model systematically overvalues them.

### Implementation Protocol
- **PFF Collegiate Prior:** Evaluate PFF collegiate metrics (Slot Rate, Wide Route Rate, YPRR, TPRR). Pass-catching prospects typically run > 40% of routes unattached; blockers > 70% inline.
- **PFF Ingestion (CSV Fixture):** PFF data must be treated as a `context_signal` utilizing a manual CSV export workflow (`csv_fixture` cache policy) to avoid API scraping fragility.
- **Model Integration:** Inject `slot_wide_route_pct` as a continuous feature into the Engine A matrix. Use a `blocking_first` boolean flag as a sample weight to penalize the projected ceiling of heavy inline blockers.
- **Lock Removal Gate:** The remodeled Engine A must pass rank-correlation gates (Kendall τ > 0.40) and demonstrate successful suppression of inline blockers before the TE `EXPERIMENTAL` lock is removed.

### Governance Constraints
- The remodel applies exclusively to Engine A (rookie evaluations). Engine B (veteran) models must not be modified based on collegiate alignment data.
- Subjective PFF *grades* (e.g., `pff_grade`) are strictly prohibited from the feature matrix. Only objective participation metrics are permitted.
