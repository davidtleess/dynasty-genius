# Dynasty Genius Phase 14 Research Brief
## Dynasty Value Score Normalization and Prospect-to-Veteran Bridging

---

## 1. Executive Recommendation

**Adopt Option C (Engine B–native position-specific P90 ceilings) for DVS normalization, stored internally on a 0–100 scale and surfaced unchanged to the user. Confirm Option B (explicit caveat, no fallback) for the rookie-to-veteran bridge. Re-derive Superflex VAR thresholds from the Engine B training distribution and league structure rather than importing external 1QB-derived numbers — the current thresholds (QB25, RB33, WR53, TE13) are directionally correct for 12-team Superflex Full PPR and should be retained pending an internal calibration pass. Confidence: HIGH on DVS architecture (the P90 empirical finding is decisive and methodology literature supports min-max-style ceiling normalization for bounded interpretive scales); HIGH on bridge (single-league data volume does not support blended-prior complexity); MEDIUM on VAR counts (external Superflex-native evidence is thin, requires league-internal validation against Engine B's actual starter-population P-cutoffs).** DVS is the dependency for VAR, divergence flag expansion, and Trade Lab; nothing else in Phase 14 unlocks until DVS normalization is shipped and audited.

---

## 2. Evidence Table

| # | Claim | Source | Type | Confidence | Implementation Implication |
|---|---|---|---|---|---|
| 1 | Engine B P90 exceeds Engine A P90 by 20.2% (QB), 13.9% (WR), 7.6% (RB), 2.8% (TE) | Local diagnostic on `engine_b_features_v2.csv` (David, May 2026) | Primary empirical | High | Reusing Engine A P90s caps ~29% of QBs and ~17% of WRs at DVS 100; Option A is disqualified |
| 2 | Min-max scaling to bounded 0–100 range is the standard technique when an absolute interpretable upper bound is required; standardization (z-score) is preferred when no fixed bound is mandated | Statistics literature (multiple normalization references) | Methodology | High | Validates 0–100 bounded scale over z-score for user display |
| 3 | Isotonic regression is monotonic, ranking-preserving, and the standard non-parametric calibration check; it is appropriate as a calibration audit (not a training signal) | scikit-learn calibration docs; Berta/Bach/Jordan 2023 ("IR preserves the convex hull of the ROC curve"); Menon et al. 2012 | Methodology | High | Use isotonic regression as a one-shot validation that DVS rank-order tracks market consensus, not as part of the scoring pipeline |
| 4 | VORP/VBD orthodoxy is to compute value relative to a position-specific replacement, then compare across positions via the difference-from-baseline — i.e., within-position first, cross-position second | FantasyPros VBD methodology; Subvertadown VBD guide; Keith Woolner VORP heritage | Analytics methodology | High | Validates within-position DVS → VAR-derived cross-position layer; do NOT bake cross-position scaling into DVS itself |
| 5 | KTC uses a 0–9999 internal scale via an adapted ELO algorithm on crowdsourced KTC submissions; top QBs ~9000+ in Superflex; values are *market consensus*, not projections | KTC FAQ; Javelin Fantasy Football analysis of KTC adjustment | Production platform | High | KTC scale is informative for display-scale selection but its market origin disqualifies it as a model-input source (consistent with David's constraint) |
| 6 | FantasyCalc derives values from real trade behavior across leagues, publishes scaled buy/sell midpoints; DailyDynasties and others normalize to the FantasyCalc scale specifically for 1:1 market comparison | FantasyCalc Dynasty Research; DailyDynasties site | Production platform | High | A second market overlay option for divergence/audit purposes; same constraint as KTC |
| 7 | DynastyProcess Trade Calculator is built on FantasyPros Dynasty Ranks; not a from-scratch valuation model | DynastyProcess.com | Production platform | Med | Useful as an additional consensus overlay but downstream of FantasyPros ranks |
| 8 | In 12-team Superflex Full PPR with QB/2RB/3WR/TE/Flex/Superflex starting lineups (9 starters), aggregate starter populations across 227 leagues (2020–21) showed 9% QB / 33% RB / 45% WR / 12% TE among "usable" players (those exceeding a points threshold) | Campus2Canton Superflex roster construction study | Dynasty primary | Med-High | Supports current VAR ratios (QB25/RB33/WR53/TE13) as directionally correct for 12-team Superflex; suggests WR threshold could go higher in 3WR builds |
| 9 | In 2QB/Superflex leagues a "replacement-level QB" does not exist on the waiver wire; all 32 starting QBs should be considered rostered; QB24 is effectively the worst startable QB | Fantasy Footballers Canons of Superflex; Footballguys Superflex roster construction | Dynasty primary | High | QB replacement level in Superflex sits at QB24–QB25, fundamentally different from 1QB (QB12); **any imported VAR cutoff derived from 1QB league composition must be discarded** |
| 10 | Bayesian/hierarchical projection models for rookies improve point estimates but require multi-season pooled data and add interpretability cost; single-league deployments rarely show net benefit | Footballguys "Bayes and Bob"; Bayesian Hierarchical FF (Rome); FFA 2025 rookie projection analysis | Methodology + dynasty primary | Med | Supports Option B at Dynasty Genius's data volume; blended-prior complexity is not justified by current sample |
| 11 | FFA's 2025 rookie projection retrospective showed QB rookie projections had the largest per-game error; RB rookies the lowest; outcome variance driven by opportunity/role stability, not talent grade | FantasyFootballAnalytics.net 2025 rookie review | Dynasty primary | High | Reinforces value of a *caveat* (Option B) over a fallback (Option A): the Engine A score is least reliable in exactly the cases where Engine B has no data |
| 12 | KTC's Superflex and 1QB databases run entirely separately because format alters non-QB value too | KTC FAQ | Production platform | High | Confirms that Superflex calibration is a categorical league setting, not a tuning knob |
| 13 | Isotonic regression introduces ties; "if rank discrimination matters more than absolute probability, isotonic may not be the right calibration method" | scikit-learn calibration docs | Methodology | High | Argues against isotonic as the primary normalization for DVS (DVS needs to rank-discriminate at the top tier); confirms it should be calibration audit only |

---

## 3. Recommended DVS Architecture

**Formula (Option C — Engine B–native P90 ceilings):**

```
DVS_raw = (predicted_avg_ppg_t1_t2 / POSITION_P90_PPG_ENGINE_B) * 100
DVS = clamp(DVS_raw, 0, 100)
```

With Engine B P90 constants frozen at the May 2026 diagnostic values:
- QB = 20.1
- RB = 15.7
- WR = 14.5
- TE = 9.4

For prospects (Engine A), the existing formula remains in place with its own P90 constants (WR 12.7, RB 14.6, TE 9.1, QB 16.7).

**Pipeline location:** `pvo_assembler.py`, immediately after both engines have produced their per-player raw outputs and before VAR is computed. DVS is the unified surface on which VAR operates.

**Fields populated:**
- `dvs` (0–100, clamped)
- `dvs_engine` (`A` | `B`) — provenance flag
- `dvs_p90_ref` — the P90 constant used, stored for audit
- `dvs_clamped` (bool) — true when raw exceeded 100
- `dvs_caveat` — string, populated for PRE_MODEL or insufficient-data cases

**Internal vs display scale:** Store and display 0–100. Internal precision: two decimal places. **Do not adopt the KTC 0–9999 scale.** KTC's scale exists because it represents market consensus *plus* implicit pick-and-package liquidity and is calibrated to be additive in trade-fairness sums. DVS is a projection-quality score, not a trade liquidity score; expanding the scale would imply additivity that the model does not guarantee. The 0–100 scale also maps cleanly to the P90-ceiling interpretation: a DVS of 70 means "70% of the position's elite-tier (P90) production rate."

**Cross-engine comparability — explicit statement to surface in the decision card:** A DVS of 70 from Engine A (prospect) and a DVS of 70 from Engine B (veteran) share the same *conceptual* basis ("70% of position-elite production rate") but reference different P90 distributions (projected rookie-year PPG vs projected 2-year veteran PPG). This is defensible for *ranking within engine* and *VAR within position*, and is the orthodox VORP-family approach (Woolner-lineage). It is **not** defensible for direct numeric comparison across engines without an explicit overlay. The decision card should never display a side-by-side prospect-vs-veteran DVS without that caveat. If David later needs strict numeric equivalence across engines, isotonic regression of Engine A DVS onto Engine B DVS using the cohort that has aged through both engines (the 2024–2025 rookie classes once they reach two pro seasons) is the correct retrofit — but that is a Phase 15+ question, not Phase 14.

---

## 4. Calibration Options — Scored

| Method | Bounded output | Preserves rank within position | Cross-engine comparable | Interpretability | Implementation cost | Verdict |
|---|---|---|---|---|---|---|
| **P90 ceiling (Option C, recommended)** | Yes (clamped 0–100) | Yes | Conceptual only ("% of position-elite rate") | High — single divisor per position | Low — already half-implemented | **Recommended** |
| Percentile rank within position | Yes (0–100 by construction) | Yes | Yes (every position's 70th percentile is by definition equivalent) | Medium — uniformly distributed, destroys magnitude information | Medium | Strong alternative; main cost is that you lose the "how much elite-tier production is this player projected for" interpretation, replacing it with "how many veterans is this player better than." For dynasty asset valuation, magnitude matters — a QB projected at 25 PPG vs 18 PPG is more separable in P90 space than in percentile space. **Reject as primary; consider as a parallel auxiliary field** (`dvs_pct`) for tier-construction UIs |
| Isotonic regression to a reference scale | Depends on target | Yes (monotonic) | Yes if mapped to common target | Low — piecewise constant function, hard to explain | Medium | Best used as a *calibration audit* against a market overlay (KTC or FantasyCalc consensus), not as the primary normalization. Introduces ties at the top, which would erase the top-of-tier discrimination the P90 finding was designed to preserve. **Recommended as Phase 14 audit step; rejected as primary** |
| Z-score (two-sided, standardized) | No native bound | Yes | Yes (by σ units) | Medium — requires explaining "elite QB is +2σ" | Low | Statistically clean but produces an unbounded scale and inverts the user's mental model (negatives are below average, hard to display). **Reject for user-facing DVS; viable for internal diagnostic** |
| Hybrid: P90 ceiling within position, then percentile-equivalence overlay across engines | Yes | Yes | Yes for the overlay | Mixed | High | Defers the cross-engine question correctly but adds a second surface that competes with VAR for "the cross-position number." **Premature for Phase 14**; revisit once the 2024–2025 prospect cohorts have aged into Engine B |

**Reasoning for P90-ceiling recommendation:**
1. The empirical P90 finding shows the per-position ceilings are genuinely different across engines because the engines forecast different quantities (rookie-year PPG vs 2-year veteran PPG). Forcing them to a common ceiling (Option A) destroys ~17–29% of top-tier discrimination at QB and WR; this is decisive evidence against ceiling unification.
2. The P90 approach is the dynasty/fantasy-football-native expression of robust min-max scaling, which the methodology literature endorses for any application requiring an interpretable bounded scale.
3. Within-position-first → VAR-second is the VORP-family architecture used across sabermetrics, FantasyPros VBD, and Subvertadown. It is the dominant pattern because cross-position comparability is itself a *use-case-dependent* function of league settings, not a property the score should bake in.

---

## 5. Superflex Replacement-Baseline Recommendation

**Recommended counts (retain current thresholds, validate internally):**

| Position | Current threshold | Recommendation | Derivation |
|---|---|---|---|
| QB | 25 | **Keep at 25** | 12-team Superflex with QB + Superflex slot = 24 starting QBs + 1 = QB25 as last-roster startable. Confirmed by Fantasy Footballers, Footballguys, KTC's separate Superflex database treatment, and Campus2Canton 2QB/Superflex starter-distribution analysis. **Flag**: this is the threshold that breaks hardest if imported from 1QB sources (1QB replacement is QB12–QB14); any future external benchmark must be Superflex-native or discarded. |
| RB | 33 | **Keep at 33** | 12-team × 2 starting RBs = 24, plus ~9 expected from the standard flex (Campus2Canton aggregate flex distribution ~60% RB-leaning historically, but Full PPR pushes this toward WR; using ~9 RB-flex slots = RB33 as the marginal startable RB). |
| WR | 53 | **Keep at 53**, candidate for raise to 55–60 in 3WR builds | 12-team × 3 starting WRs = 36, plus ~17 from flex/superflex non-QB pool. Campus2Canton showed 45% of usable players are WR in Full PPR. If David's league is 3WR (not 2WR+Flex), WR53 may slightly underestimate; recommend internal validation against Engine B WR PPG cutoff. |
| TE | 13 | **Keep at 13** | 12-team × 1 starting TE = 12, plus 1 buffer for the TE-flex edge case. If David's league is 1.5-TE or TE-premium, this rises; current state assumes standard 1-TE. |

**Critical methodology note — Superflex-native evidence is thin across the board.** Only the Campus2Canton study provides large-sample Superflex starter-distribution data, and even that uses 1-PPR with 0.5 TEP, not strict Full PPR. **Recommendation: derive Engine-B-native VAR thresholds directly from the `engine_b_features_v2.csv` `avg_ppg_t1_t2` distribution by counting how many players at each position exceed a startable threshold defined by 12 teams × Superflex roster composition.** Specifically:

1. For each position, rank Engine B PPG projections in descending order.
2. The VAR threshold is the rank N such that N corresponds to `(starting_slots × 12) + flex_share`.
3. Veteran VAR baseline PPG = `predicted_avg_ppg_t1_t2` at that rank.
4. Veteran DVS_VAR_baseline = baseline_PPG / P90_Engine_B × 100.

This produces league-structure-derived VAR cutoffs in DVS-space that are guaranteed to be internally consistent with Engine B's own distribution. External Superflex starter counts should be used only as a sanity check.

**Strict flag:** Any source deriving QB cutoffs from 1QB league composition — including most FantasyPros VBD content, Subvertadown's defaults, and any RotoViz/4for4 piece that does not explicitly call out Superflex — must be rejected for the QB threshold. The QB25 number stands on Superflex-native logic (12 teams × 2 QB slots = 24 + buffer), not on imported VBD analysis.

---

## 6. Rookie-to-Veteran Bridge Recommendation

**Confirm Option B (explicit caveat, allow dead window).**

**Reasoning:**
1. **Data volume.** Dynasty Genius operates on a single league with ~600 active players and ~250 prospects per year. Bayesian hierarchical models and blended priors (Option C) derive their efficiency gains from cross-league or cross-cohort pooling. The Bayesian-FF literature (Footballguys "Bayes and Bob," Rome's hierarchical model) consistently uses many seasons of pooled data; the single-league deployment lacks the sample to estimate prior strengths credibly.
2. **The Engine A signal is weakest exactly where you'd want to lean on it.** FFA's 2025 rookie projection retrospective showed QB rookie projections produced the largest per-game error of any position, and rookie outcomes are driven by *opportunity and role stability*, neither of which is in Engine A's input set (draft pick, round, age). Option A (fall back to Engine A in the dead window) would hide red flags — a 2026 first-round RB who saw a 12% snap share as a rookie would still display his Engine A draft-capital DVS, masking the data the user most needs.
3. **Auditability.** Option B has a single, visible code path: "no Engine B score → show caveat." Option C (blended prior weighting Engine A and Engine B by `games_t`) introduces a transition zone where the displayed DVS is a function of two engines with no clean attribution, complicating any future divergence-flag logic and making decision-card explanations harder. Phase 14's stated trust priority makes auditability the dominant constraint.
4. **Transition smoothness is the only real cost of Option B**, and it is small. The dead window affects at most one annual cohort transitioning from Engine A to Engine B (the prior year's rookies, ~250 players, of which only ~80–120 are dynasty-relevant). A caveat string is sufficient.

**Cost statement for the road not taken (Option C / blended prior):**
- Implementation cost: **High.** Requires defining a games-played weighting function, validating its shape (linear? sigmoid? threshold?), and re-running calibration each time the function changes.
- Auditability cost: **High.** The blended DVS for a 14-game rookie is neither Engine A nor Engine B; explaining it on a decision card requires exposing both intermediate scores.
- Transition smoothness gain: **Low–medium.** The blended prior smooths the visual jump but does not change the underlying knowledge — you still don't know if the player can play.
- **Verdict: not worth it at current data volume.** Revisit only if Dynasty Genius expands to multi-league deployment with pooled historical data sufficient to estimate priors.

**Identity handoff verification requirement (mandatory for Phase 14 ship):** Before DVS is exposed to the user, the pipeline must verify that every player in the 2024 and 2025 rookie classes has a unique persistent ID that tracks across Engine A (their draft-year score) and Engine B (their post-NFL-season score). The handoff is the highest-risk silent-failure point — a player who silently re-IDs at engine transition could appear as PRE_MODEL forever, or worse, display two DVS entries. **Required artifact: a 2024–2025 cohort reconciliation report showing 100% identity continuity before DVS goes live.**

---

## 7. Failure Modes and Governance Risks

1. **DVS calibration drift between engines.** If Engine A and Engine B P90 constants are recomputed on different cadences (e.g., Engine B refreshed annually, Engine A refreshed each draft cycle), the cross-engine "conceptual basis" interpretation can drift. **Mitigation:** version the P90 constants in `dvs_p90_ref` per player-row, log the constants used at scoring time, and require an explicit version-bump checkpoint when either engine retrains.

2. **DVS = 100 saturation creep.** As Engine B's training distribution evolves (better usage data, more seasons), the P90 ceiling will move. If it moves upward, current DVS-100 players will drop below 100; if downward, more players will saturate. **Mitigation:** track the fraction of players at the DVS ceiling per position quarterly; if it exceeds ~12% (above the 10% by-construction expectation), re-fit P90.

3. **VAR activation before NOISE_BAND closes (mid-July 2026).** NOISE_BAND is locked through mid-July 2026 by stated governance. If VAR is activated for veterans before NOISE_BAND closes, divergence flag logic that consumes VAR cutoffs will fire prematurely against a known-noisy reference set, producing high-frequency false signals that erode user trust in the divergence system. **Mitigation:** make VAR activation conditional on the NOISE_BAND end-state. Phase 14 ships DVS but defers VAR-driven veteran divergence flags until NOISE_BAND is released. VAR can compute and store quietly; flags should not surface.

4. **Engine A/B scale drift via independent retraining.** If Engine A's P90 (currently WR 12.7, RB 14.6, TE 9.1, QB 16.7) is updated without rerunning the cross-cohort calibration check, the rookie–veteran transition can produce step changes in DVS for players in their first Engine B year. **Mitigation:** require a paired-cohort regression of Engine A DVS vs Engine B DVS for the same players (2024–2025 classes once they reach two pro seasons) before any P90 change is committed.

5. **TE Engine B promotion not yet decision-grade.** TE was promoted to ACTIVE_B in Phase 13.3 but has not been validated to decision-grade. TE DVS computed via Option C is structurally correct (TE Engine B P90 of 9.4 vs Engine A P90 of 9.1 — only a 2.8% gap, the closest match of any position) but underlying Engine B TE projections may not be reliable. **Mitigation:** display TE DVS with a "TE model in validation" annotation through Phase 14; do not let TE DVS drive VAR-based decisions until separately certified.

6. **Crowdsourced market overlay misuse.** KTC and FantasyCalc values are correlated with future production but also reflect hype, recency bias, and rookie-fever cycles (Calculator City notes April–May rookie value spikes). Using them as a calibration check is appropriate; using them as ground truth for "is DVS wrong?" is not. **Mitigation:** state explicitly in the divergence-flag spec that DVS-vs-market disagreement is a signal worth surfacing, not evidence that DVS is wrong.

---

## 8. Explicit Out-of-Scope for Phase 14

- **TE demotion or re-modeling.** Engine B TE P90 (9.4) is only 2.8% above Engine A's (9.1) — the smallest gap of any position. No structural reason to revisit TE modeling in Phase 14.
- **Divergence flag expansion to veterans.** Locked behind NOISE_BAND release (mid-July 2026). VAR can compute internally; user-facing veteran divergence flags wait.
- **VAR activation for veterans on the decision card.** Conditional on NOISE_BAND. If NOISE_BAND closes on schedule (mid-July 2026), Phase 14 can ship VAR activation in a follow-up release; if NOISE_BAND slips, VAR ships dark.
- **Trade Lab DVS-based valuation.** Trade Lab requires a stable, audited DVS *and* a defensible cross-position valuation model. Phase 14 establishes the first; the second is Phase 15+.
- **Market features as model inputs.** KTC/FantasyCalc/DynastyProcess remain overlay-only per constraint. No deviation.
- **Cross-engine isotonic remapping of prospect DVS onto veteran DVS scale.** Premature — requires the 2024–2025 cohorts to have aged through both engines, which is not the case until end of 2026 season at earliest.
- **Display scale change.** No reason to move from 0–100. Reject any future suggestion to "match KTC's 0–9999" — those scales encode different quantities.
- **UI polish on DVS surface.** Per constraint: trust before polish. Phase 14 ships the number; visual treatment is Phase 15.

---

## 9. Open Decisions for David

1. **Do you want Engine-B-distribution-derived VAR thresholds to override the current QB25/RB33/WR53/TE13 if they materially diverge, or to be used only as a sanity check?** Recommendation: use as a sanity check first; override only if divergence exceeds ~15% at any position.
2. **Auxiliary percentile field (`dvs_pct`) alongside `dvs` — yes or no?** Adds tier-construction utility for any future Trade Lab work at low implementation cost; declines auditability cost. Recommendation: yes, but compute only, do not display in Phase 14.
3. **Cohort reconciliation report for the 2024–2025 rookie identity handoff — block Phase 14 ship on this, or run in parallel and patch?** Recommendation: block. Silent identity failure is the highest-risk regression vector.
4. **NOISE_BAND release date confidence — is mid-July 2026 firm enough to plan VAR activation as a follow-up release, or should VAR ship dark indefinitely?** This determines whether veteran-side divergence flag work is staged into Phase 14.5 or deferred entirely.
5. **Isotonic regression calibration audit against KTC Superflex Full-PPR consensus — Phase 14 or defer?** Adds ~1 week of work; produces a one-time validation artifact that DVS rank-order is not pathologically misaligned with market. Recommendation: yes, Phase 14, run after DVS ships and before VAR activation.

---

## 10. Phase 14 Implementation Workstreams (Dependency-Ordered)

**WS-1: DVS normalization implementation** *(blocking dependency for everything else)*
- Freeze Engine B P90 constants: QB 20.1, RB 15.7, WR 14.5, TE 9.4.
- Implement Option C formula in `pvo_assembler.py`.
- Populate `dvs`, `dvs_engine`, `dvs_p90_ref`, `dvs_clamped`, `dvs_caveat`.
- Verify ceiling fraction (~10% per position by construction).

**WS-2: Identity handoff verification for 2024–2025 cohorts** *(blocks DVS ship)*
- Run reconciliation between Engine A scoring records and Engine B feature-store entries.
- Required: 100% identity continuity for the 2024 class; 100% for the 2025 class (most still on Engine A but transitioning).
- Output: cohort reconciliation report archived.

**WS-3: Bridge logic — Option B implementation**
- Define PRE_MODEL state for players with insufficient Engine B data after one pro season.
- Implement `dvs_caveat` string population.
- Verify no Engine A fallback path exists in code (assert dead window is preserved).

**WS-4: VAR threshold validation against Engine B distribution**
- Compute Engine-B-derived VAR cutoffs at QB25/RB33/WR53/TE13 rank positions.
- Compare to current thresholds; flag any >15% deviation for David review.
- Output: VAR baseline DVS values per position.

**WS-5: Calibration audit — isotonic regression vs market consensus**
- Pull KTC Superflex full-PPR consensus and FantasyCalc dynasty values (overlay only).
- Fit isotonic regression of DVS rank against market rank by position.
- Output: calibration plot per position; flag any non-monotonic or extreme-tail divergence.
- This is an audit artifact, not a code change.

**WS-6: VAR activation (conditional, holds for NOISE_BAND)**
- Implement but gate behind NOISE_BAND end-state flag.
- Do not surface veteran VAR-derived divergence flags until NOISE_BAND closes (target mid-July 2026).

**WS-7: Decision-card surface updates**
- Display DVS with engine provenance and caveat strings.
- No UI polish; minimal styling sufficient to expose the data.
- Defer Trade Lab DVS integration to Phase 15.

**Critical path:** WS-1 + WS-2 in parallel → WS-3 → WS-4 → WS-5 → WS-6 (gated) → WS-7 (gated).

**Estimated ship gate:** WS-1 through WS-5 are tractable inside Phase 14. WS-6 ships when NOISE_BAND closes; if NOISE_BAND slips past mid-July 2026, WS-6 defers to Phase 14.5 without blocking the rest of Phase 14.

---

*End of Phase 14 research brief. The brief recommends; David decides.*