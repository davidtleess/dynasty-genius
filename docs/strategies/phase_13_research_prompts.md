# Phase 13 Research Prompts

Three research directives for Phase 13. Execution order: **3C gates 3B**. 3A is independent.

---

## Prompt 3A — Engine A Draft Capital Step-Function

**Context:** You are tasked with designing the feature engineering spec for a draft capital non-linearity change in Dynasty Genius Engine A (the rookie-prospect scoring model). Engine A is a Ridge regression model trained on historical NFL draft classes (2015–2025) using college production metrics (Dominator Rating, YPRR, completion rate) and draft metadata (pick, round, age at entry). The current architecture treats draft capital as a pair of continuous linear features (`pick`, `round`) fed directly into Ridge. This creates a systematic flaw: a pick-10 and a pick-30 receiver are treated as nearly equivalent despite materially different NFL opportunity structures.

**The Architectural Directive:** Move Engine A from linear draft capital weighting to a step-function framework that reflects how starting opportunity — the foundational prerequisite for realizing production value — is actually distributed:

- Picks 1–32 (Round 1): Draft capital is the dominant value driver (~70%). These players arrive with a contractual guarantee of early opportunity. College production and age are secondary modifiers, not primary weights.
- Picks 33–64 (Round 2): Capital and situation split equally (~50/50). Opportunity is expected but not guaranteed. College efficiency metrics become the tiebreaker.
- Picks 65+ (Round 3+): Situation dominates (~70%). Capital is a weak signal; undrafted free agents have reached NFL rosters, so the pick number is nearly noise. College production and age at entry are the primary drivers of survival and opportunity floor.

This is not a cosmetic adjustment. It represents a structural change to how the X matrix is built. Engine A currently has no mechanism to encode categorical jump discontinuities in opportunity distribution.

**Research Questions to Answer:**

1. **Feature Engineering Design:** What is the correct implementation of a draft capital step function inside a Ridge regression model? Evaluate at minimum: (a) ordinal categorical encoding with position-weighted bins, (b) spline basis expansion over pick number, (c) piecewise linear regression with interaction terms. Which approach is compatible with our existing `sklearn.linear_model.Ridge` training loop and produces interpretable coefficients?

2. **Position-Specific Calibration:** Are the pick thresholds (1–32 / 33–64 / 65+) position-invariant? Running backs historically earn opportunity earlier at lower pick numbers than wide receivers or tight ends. Evaluate whether separate bin boundaries per position are justified or whether a shared boundary is defensible given our dataset sizes (approximately 120–180 players per position, 2015–2025).

3. **Backtest Gate Design for Engine A:** The Phase 10–12 harness evaluated Engine B using a 4-fold walk-forward methodology on veteran NFL seasons. Engine A requires a distinct gate design because:
   - The target variable is 3-to-7-year dynasty value, not single-season PPG.
   - Draft class sizes are small (≈30–50 players per position per class).
   - The outcome variable (`y24_ppg`, a 2-to-4-year cumulative average) introduces a look-ahead horizon that is incompatible with a single season's holdout.
   - Specify the correct holdout methodology (e.g., leave-one-class-out cross-validation), the primary gate metric (rank correlation within draft class, not global Kendall τ-b), and what numeric threshold constitutes a promotion-worthy improvement over the current continuous-pick baseline.

4. **Interaction Effects:** The 65/35 analytical discipline requires that college production (Dominator Rating, YPRR) remain primary for 3rd-round picks. Specify whether interaction terms between draft capital tier and college efficiency metrics are appropriate, or whether the step-function bin itself is sufficient to modulate the weight allocation implicitly through Ridge regularization.

5. **Governance Guardrails:** This change touches Engine A's X matrix. Identify the minimum artifact set required before any model is retrained: what provenance tests must pass, what feature contract tests must be updated, and what the rollback condition is if the gate fails.

**Constraints:**
- Market data (KTC, FantasyCalc, ADP) is absolutely prohibited from the feature matrix. Draft pick number from the NFL Draft is not market data — it is ground-truth league information.
- The current `CFBD_MODEL_INPUT_COLUMNS` and `PLAYERPROFILER_CONTEXT_COLUMNS` contracts in `engine_a_contract.py` define the allowed field taxonomy. The step-function feature must be derived from existing allowed inputs (`pick`, `round`) and encoded as a new derived feature, not a new data source.
- `dynasty_value_score` remains `None` on all PVO objects until Engine A passes the redesigned gate.

**Deliverable:** A spec document with sections: (1) feature engineering implementation design, (2) position-specific calibration analysis, (3) Engine A gate definition with numeric thresholds, (4) governance checklist before any training run, (5) failure mode analysis.

---

## Prompt 3C — Prospect Identity Resolver Audit

**Context:** You are tasked with designing the test plan and coverage audit for the Dynasty Genius Prospect Identity Resolver (Phase 9.5). This is a **hard gate for the TE Remodel (Phase 13B)** — no PFF collegiate feature integration should begin until this audit is complete and has reached an acceptable coverage threshold.

The Prospect Identity Resolver maps incoming rookie requests (by name or draft class) to a canonical Sleeper ID using a three-stage pipeline: (1) explicit `sleeper_id` in the request, (2) alias bridge (`app/data/prospect_alias_bridge.json`, currently 80 entries for the 2026 draft class), (3) review log. There is no fuzzy matching — if all three stages fail, the player is flagged as unresolved, not silently scored.

**Why this gates the TE remodel:** The TE remodel (Phase 13B) will ingest PFF collegiate data (Slot/Wide Route Rate, Inline Blocking Rate) keyed by player name or PFF ID. These records must join to the same canonical Sleeper ID that Engine A uses. A TE prospect whose identity resolves incorrectly will receive the wrong collegiate blocking profile — which is worse than receiving no profile at all, because it produces a wrong signal in the correct direction.

**The Audit Population:** The resolver must be validated against TE prospects from the 2018–2025 NFL Draft classes. This is the exact population that would be used to retrain Engine A under the TE remodel. Key challenges specific to this population:

- Many 2018–2022 TE prospects are now active NFL veterans (e.g., Sam LaPorta, Dalton Kincaid, Brock Bowers). Their Sleeper ID may exist in the veteran system, but the alias bridge only contains 2026 draft class entries. The resolver must not fail for pre-2026 prospects.
- Blocking-first TEs (inline blockers) frequently appear in limited statistical databases. PFF IDs for these players may not be in the Sleeper registry at all.
- TEs drafted in rounds 3–7 have lower database coverage across CFBD, PFR, and Sleeper than skill position players.

**Research Questions to Answer:**

1. **Coverage Baseline:** Define the methodology for measuring resolver coverage. What constitutes a "resolved" record: a Sleeper ID match only, or a Sleeper ID match that also links to a CFBD player record? Specify the exact SQL or dataframe query against `app/data/prospect_alias_bridge.json` and the Sleeper API that would produce a coverage report for 2018–2025 TE draft picks. What is the expected resolution rate given the current alias bridge scope (2026 only)?

2. **Failure Mode Taxonomy:** Enumerate the distinct failure modes for the resolver across the 2018–2025 TE population:
   - Stage 1 miss: no `sleeper_id` in request (expected for all historical lookups)
   - Stage 2 miss: player not in alias bridge (expected for pre-2026 classes)
   - Stage 3 miss: player not in review log
   - Silent corruption: resolver returns a Sleeper ID that is incorrect (e.g., name collision between two players)
   Which failure mode is the most dangerous for the TE remodel, and why?

3. **Acceptable Coverage Threshold:** Define what coverage rate constitutes a green light for Phase 13B. Consider: if 30% of TE prospects from 2020–2024 cannot be resolved, the PFF feature join will silently exclude them from training, creating survivorship bias. Propose a minimum acceptable Sleeper resolution rate per draft-class cohort, and specify whether inline-only blockers (players with fewer than 10 career receptions) should be counted in the denominator.

4. **Remediation Path:** If the audit reveals insufficient coverage, what is the minimum remediation required before 13B can proceed? Evaluate: (a) extending the alias bridge to cover 2018–2025 TE draft picks, (b) adding a PFF ID → Sleeper ID crosswalk to the source registry, (c) accepting lower coverage and encoding a `resolver_confident` boolean on the PVO as a caveat flag. Which option preserves the "no fuzzy matching" governance constraint?

5. **Prospect-to-Veteran Transition Tests:** Define the specific test cases that confirm the resolver correctly handles a player who was a draft-class prospect in year T and is now an active veteran in year T+3. The test must verify: (a) a request for the player as a prospect returns their correct Sleeper ID, (b) the same Sleeper ID is recognized in the veteran identity system without duplication.

**Constraints:**
- The resolver must not introduce fuzzy string matching at any stage. The "no fuzzy matching" constraint is non-negotiable and exists specifically because name-based collisions are the dominant failure mode in TE identity resolution (similar names, position changes, international players).
- The existing Phase 9.5 alias bridge format (`app/data/prospect_alias_bridge.json`) is the correct extension point — no new identity infrastructure should be introduced until the audit is complete.

**Deliverable:** A spec document with sections: (1) coverage measurement methodology and baseline estimate, (2) failure mode taxonomy ranked by severity for the TE remodel use case, (3) acceptable coverage threshold with rationale, (4) remediation path decision tree, (5) test case definitions for prospect-to-veteran transitions.

---

## Prompt 3B — TE Remodel and Collegiate Blocking Profile Split

**Dependency: This brief is gated on Prompt 3C (Identity Resolver Audit) completing with an acceptable coverage result. Do not begin implementation research until the resolver audit passes its defined threshold.**

**Context:** You are tasked with designing the feature engineering spec and data acquisition plan for a TE remodel within Dynasty Genius Engine A. The TE position is currently governance-locked at `EXPERIMENTAL` with Kendall τ-b = 0.477 and an `under_26` subgroup τ-b = 0.403 — substantially below the QB/RB/WR promoted thresholds. The root cause hypothesis is **label noise from blocking-first TE profiles**: inline blockers drafted in rounds 2–4 share draft capital and age features with pass-catching specialists, but their production ceilings are structurally different. Engine A cannot distinguish them because it has no collegiate receiving profile features.

**The Architectural Directive:** Ingest PFF Collegiate data to segment TEs by receiving role:

- **Pass-catching profile signal:** Collegiate Slot Route Rate + Wide Route Rate (combined as a percentage of all routes run). Hypothesis: TEs who ran ≥40% of routes outside the numbers in college are disproportionately likely to produce as dynasty pass-catchers.
- **Blocking-first profile signal:** Collegiate Inline Blocking Rate (percentage of snaps in an in-line stance). Hypothesis: TEs with ≥60% inline blocking rate in their final college season have systematically lower production ceilings regardless of draft capital.

**Step 0: Data Acquisition (Required Before Any Feature Engineering)**

PFF collegiate data is classified as a manual CSV export source in the Dynasty Genius source registry (`pff`, role: `context_signal`). It is not a model input yet. Before designing any feature engineering, establish the data acquisition plan:

1. **Source Characterization:** What PFF collegiate data products expose Slot Route Rate, Wide Route Rate, and Inline Blocking Rate for TE draft classes from 2018–2025? Are these available via PFF Premium Stats manual export, PFF College (separate product), or PFF API? What is the approximate cost, format, and field-level granularity? Describe the manual export workflow that satisfies the existing `csv_fixture` cache policy.

2. **Identity Coverage Dependency:** These records will be keyed by PFF player ID or player name. The join to canonical Sleeper ID must pass through the resolver audit (3C). If 3C returns a PFF ID → Sleeper ID crosswalk as part of its remediation, specify how that crosswalk would be consumed here. If 3C does not produce a crosswalk, specify the fallback.

3. **Historical Depth:** What is the minimum number of draft classes needed to retrain Engine A's TE model with a new blocking-profile feature? Given that the TE training population is approximately 30–50 players per class and 7–8 classes (2018–2025), estimate the total N and identify whether a blocking-profile split creates a subgroup (inline-first TEs) too small to train reliably.

**Research Questions to Answer (Post-Step 0):**

4. **Feature Engineering Design:** Given the PFF data is available, what is the correct encoding for the blocking profile signal? Evaluate: (a) a continuous `slot_wide_route_pct` feature added to the TE X matrix, (b) a binary `blocking_first` flag used as a sample weight at training time, (c) two separate TE sub-models (receiving-profile TEs and blocking-profile TEs) trained independently. Which approach is compatible with the existing `ENGINE_B_FEATURES_TE` / Engine A Ridge training loop and produces actionable governance outcomes?

5. **Label Noise Correction:** If blocking-first TEs are confirmed to produce below the TE VAR threshold (bottom 13 by `dynasty_value_score`), they should either be excluded from the training population or receive a `low_production_ceiling` caveat rather than a direct projection. Specify the governance decision point: at what blocking rate, with what sample size, does the caveat trigger vs. the exclusion?

6. **TE EXPERIMENTAL Lock Removal Criteria:** The TE position is governance-locked at `EXPERIMENTAL` independently of gate metrics — the lock exists because the harness confirmed tau=0.477 does not justify promotion. Define the specific numeric conditions under which the EXPERIMENTAL lock can be lifted: minimum tau-b threshold, minimum number of folds passing the G1 rank-correlation gate, and whether the blocking-profile split must independently pass the gate (i.e., pass-catching TEs alone meet the threshold) or whether all TEs must be evaluated as a single population.

7. **Interaction with Engine B TE Track:** Engine B also treats TE as EXPERIMENTAL. The TE Engine A remodel affects rookie scoring only — it does not retrain Engine B. Confirm explicitly that no Engine B TE artifact (`engine_b_v1.pkl` TE fallback) is modified, retrained, or promoted as a side effect of the Engine A TE remodel.

**Constraints:**
- PFF grade fields (`pff_grade`, `pff_route_grade`) remain in `PROHIBITED_COLUMNS` and cannot enter the model under any name. Only participation/rate metrics (route percentage, snap percentage by formation) are candidates for model input.
- Market data (KTC, FantasyCalc dynasty values) cannot be used as a training feature or a label proxy.
- The resolver audit (3C) must be complete and passing before any training data is assembled that includes PFF joins.
- The `ENGINE_B_EXPERIMENTAL_POSITIONS` set for TE is unchanged by this work.

**Deliverable:** A spec document with sections: (1) PFF data acquisition plan (Step 0) with cost/format/identity-join dependency, (2) historical depth and sample size analysis, (3) feature engineering design options with recommendation, (4) label noise correction and caveat logic, (5) TE EXPERIMENTAL lock removal criteria, (6) Engine B isolation confirmation.
