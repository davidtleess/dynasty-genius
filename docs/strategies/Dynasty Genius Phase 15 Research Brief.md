# Dynasty Genius Phase 15 Research Brief
*Trade Lab & Cross-Positional Valuation*

Date: 2026-05-16
Status: DRAFT — for research agent input
Prepared by: Claude

---

## System Context

Dynasty Genius is a machine learning asset management system for a 12-team Superflex Full PPR dynasty league. The system scores players using two engines:

- **Engine A** (prospects): draft pick, round, age → peak PPG projection. P90 constants: QB 16.7 / RB 14.6 / WR 12.7 / TE 9.1.
- **Engine B** (veterans): NFL usage signals → 2-year average PPG projection. P90 constants: QB 20.1 / RB 15.7 / WR 14.5 / TE 9.4.

**Phase 14 delivered:**
- **Dynasty Value Score (DVS)**: 0–100 float, normalized to Engine B P90 ceiling per position. Formula: `clamp(predicted_avg_ppg_t1_t2 / P90[position] * 100, 0, 100)`.
- **Dead Window Bridge**: players with < 8 NFL games retain Engine A DVS with a mandatory caveat.
- **Within-position VAR**: `value_above_replacement = player_DVS - replacement_DVS`, where replacement is the DVS of the player at rank QB25 / RB33 / WR53 / TE13 within the active Engine B population.
- **DVS provenance fields**: `dvs_engine` ("A" or "B"), `dvs_p90_ref`, `dvs_clamped`.

**What Phase 14 explicitly deferred to Phase 15:**
- Cross-positional VAR (a QB VAR of +20 ≠ a WR VAR of +20)
- Trade execution logic (DVS/VAR as a trade currency)
- DVS scale expansion to 0–1000 (if needed for trade math)
- Bayesian blending for Dead Window players
- `dvs_pct` auxiliary within-position percentile field
- Trade Lab DVS-based cross-position valuation surface

**Locked constraints that must not change:**
- Market data (KTC, FantasyCalc, ADP) is overlay-only. It cannot enter DVS formula or Engine A/B model features under any circumstances.
- NOISE_BAND = 0.10, locked until mid-July 2026. Veteran market-divergence flags must not surface in the UI before then.
- TE G3 (market superiority gate) is deferred. TE `decision_supported` remains False.
- Engine B P90 constants are frozen at May 2026 values until a new diagnostic run with David's approval.
- `decision_supported` remains False on all surfaces in Phase 15.

---

## Research Question 1: Cross-Positional Scarcity-Adjusted VAR

**The problem:**

Within-position VAR is computed against a position-specific P90 denominator. This means DVS units are not equivalent across positions:
- A QB at DVS 80 is 80% of QB25 = 20.1 PPG → ~16.1 PPG predicted
- A WR at DVS 80 is 80% of WR14.5 → ~11.6 PPG predicted
- A QB VAR of +20 (above QB25) and a WR VAR of +20 (above WR53) are not the same scarcity signal

For trade evaluation, cross-positional comparison is unavoidable. We need a principled method to say whether trading a WR at VAR +15 for a QB at VAR +10 is fair.

**Questions to answer:**

1. What is the correct mathematical framework for cross-positional VAR in a 12-team Superflex Full PPR dynasty league? Consider: P90 ratio normalization, positional scarcity multiplier, marginal value above replacement (from redraft VBD literature), or a hybrid.

2. In Superflex, QBs command a premium because every team starts two (QB + Superflex slot). How should this premium be quantified? Is it derived from the ratio of replacement thresholds (QB25 vs WR53), from the P90 ratio (20.1 vs 14.5), from market data, or from a formula? Note: market data cannot enter the model — any multiplier must be derivable from model-native signals.

3. What are the known approaches from dynasty community research (VBD, positional scarcity scoring, Rotoviz methodology, etc.)? Which translates most cleanly to a 2-year forward-looking PPG model?

4. Is there a single "trade unit" — a common currency — that allows comparing a TE at VAR +5 against a WR at VAR +12? What is its definition and how is it computed?

5. What are the failure modes? Which positions or player archetypes produce misleading cross-positional comparisons even with a multiplier applied?

---

## Research Question 2: Trade Execution Logic

**The problem:**

The Trade Lab needs to evaluate proposed trades and characterize them as fair, favorable, or unfavorable from David's perspective. A trade is typically: give {asset list} receive {asset list}, where assets are players (with DVS/VAR) and draft picks (Engine A scored, pick+round+age → DVS).

**Questions to answer:**

1. **Trade fairness definition:** Should fairness be defined as DVS sum parity, VAR sum parity, cross-positional scarcity-adjusted VAR parity, or something else? What are the tradeoffs of each approach for dynasty (multi-year) vs. redraft (single-year) valuation?

2. **Multi-asset trades:** How should a 2-for-1 trade be evaluated? (e.g., WR1 + pick vs. QB1 + RB2). Does asset count matter, or is it purely a value sum?

3. **Age and trajectory:** Should a 24-year-old WR at DVS 70 be valued differently than a 29-year-old WR at DVS 70 in trade math? The aging curve is captured in Engine B's feature inputs, but should it also appear explicitly in the trade fairness calculation? Or is DVS already trajectory-adjusted because Engine B predicts T+1/T+2?

4. **Draft picks in trade math:** Draft picks have Engine A scores (pick + round + age → DVS). How do you represent a pick whose age is unknown? What is the appropriate age assumption for a 2027 first-round pick? What about conditional picks?

5. **Minimum viable Trade Lab surface:** What is the simplest defensible Phase 15 implementation? Which features are essential for the first iteration vs. which should be deferred to Phase 16?

6. **Buy low / sell high signal:** Should the Trade Lab display a recommended trade direction (e.g., "model favors receiving this trade")? If so, what threshold on the value delta triggers a recommendation, and how does NOISE_BAND suppression interact with this?

---

## Research Question 3: DVS Scale — 0–100 vs. 0–1000

**The problem:**

Phase 14 kept DVS on a 0–100 float scale. The PDF research framework and some community tools (KTC) use wider integer ranges. The question is whether 0–100 is sufficient for trade math or whether expansion is warranted.

**Questions to answer:**

1. Does trade evaluation math require more precision than a 0–100 float with one decimal place (effectively 1000 distinct values)? Is there a real scenario where two players tie on DVS at 0.1 precision and the tie matters for trade evaluation?

2. What breaks in the current PVO schema if DVS expands to 0–1000? What changes in the normalization formula? Are there downstream surfaces (Rookie Board sort, Trade Lab delta display) that would need updates?

3. Is there a user-facing argument for 0–1000 (market familiarity, alignment with KTC's scale) that outweighs the schema migration cost? Or does DVS serve a distinct purpose (model-native, engine-calibrated) that makes KTC alignment undesirable?

4. What is the recommendation: stay at 0–100, expand to 0–1000, or use a two-field approach (dvs_0_100 for internal model use, dvs_display for surface presentation)?

---

## Research Question 4: Dead Window Bayesian Blending

**The problem:**

Phase 14 explicitly deferred Bayesian blending for Dead Window players (veterans with < 8 NFL games) in favor of the simpler explicit caveat approach (retain Engine A score + caveat string). The rationale was: operationally premature, difficult to audit, single-league data volume too small.

The 2024 draft class now has ~2 seasons of NFL data. Some of those players have crossed the Engine B eligibility threshold. The question is whether blending is now warranted.

**Questions to answer:**

1. For the 2024 draft class, how many players have crossed from Dead Window into full Engine B eligibility? How many remain in the Dead Window? Does the cohort size justify revisiting blending?

2. What is the simplest defensible Bayesian blending formula for a player with `games_t` between 1 and 7? A linear weight of `games_t / ENGINE_B_MIN_GAMES_T` applied to Engine B prediction with `(1 - weight)` on Engine A prior is the natural starting point. What are its failure modes?

3. Does blending produce meaningfully different DVS outputs compared to the pure Engine A prior for typical Year 1 players? If the delta is small (< 5 DVS points), blending adds complexity with no material benefit.

4. Is the provenance auditability concern solvable? The existing `dvs_engine` field is "A" or "B". Blending would require a new value (e.g., "AB") and `dvs_blend_weight` field. Is this audit trail sufficient, or does blending fundamentally obscure which engine is driving the score?

5. Recommendation: implement in Phase 15, defer further, or permanently reject?

---

## Research Question 5: dvs_pct Auxiliary Field

**The problem:**

Within-position percentile rank (`dvs_pct`) was deferred from Phase 14 as "compute-only, not display." The question is whether it is needed for Phase 15 trade math and what its exact definition should be.

**Questions to answer:**

1. Is `dvs_pct` the within-position percentile of the player's DVS against all active Engine B players at that position? Or against all scored players (including Engine A prospects)?

2. Does trade evaluation math require `dvs_pct`, or is raw DVS sufficient? Is percentile rank more intuitive for the Trade Lab display than a raw 0–100 score?

3. Should `dvs_pct` be a PVO field (computed at assembly time) or a derived field computed at query time from the current active population?

4. What is the reference population for percentile computation — all ACTIVE_B players for that position, or all players including PRE_MODEL?

---

## Deliverable Format

For each research question, provide:

1. **Recommendation** — a specific, actionable answer with any mathematical formula needed
2. **Alternatives considered** — other approaches and why they are rejected
3. **Implementation complexity** — what new infrastructure is required (new PVO fields, new scripts, schema migrations, route changes)
4. **Dependencies** — what must exist before this can be built
5. **Risk flags** — what could go wrong; which player archetypes or edge cases require special handling

---

## Non-Negotiable Constraints for All Recommendations

The following must not appear in any Phase 15 recommendation:
- Market data (KTC, FantasyCalc, ADP, any dynasty consensus value) entering the DVS formula, trade math formula, or any Engine A/B model feature
- Veteran market-divergence flags surfaced before NOISE_BAND recalibration (mid-July 2026)
- Any change to Engine B P90 constants without a new diagnostic run and David's approval
- Any recommendation that sets `decision_supported = True` on any surface
- Any recommendation that changes Engine A or Engine B model artifacts or training pipelines

---

*Hand this brief to research agents (Compass, framework reviewers, etc.) independently. Each agent should produce a response covering all five research questions. Claude will compare responses, identify conflicts, and synthesize a corrected roadmap before the Phase 15 spec is written.*
