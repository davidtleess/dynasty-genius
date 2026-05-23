---
document: Engine A Bifurcation Design Spec
version: 0.2 (APPROVED)
last_updated: 2026-05-23
authority: analytical_design
governed_phase: Phase 19 / Engine A v3 — Bifurcated Rookie Forecast
status: approved
supersedes: portions of Phase 16 research brief; portions of v0.1 of this document
references:
  - docs/governance/00-product-constitution.md (authority: highest)
  - docs/governance/01-north-star-architecture.md (authority: technical)
  - docs/governance/03-engine-b-decision-record.md (precedent: bifurcation patterns)
  - docs/superpowers/plans/2026-05-10-data-source-roadmap.md (source registry)
  - src/dynasty_genius/models/engine_a_contract.py (leakage contract)
  - Phase 13 Research Brief (draft-capital transform recommendations)
  - Phase 16 Research Brief (existing in-project — superseded for feature-set recommendations)
  - Phase 16 second research brief (Google Doc, 2026-05-23 — synthesized in §9)
  - Engine A Deep Research Review (Claude, 2026-05-23 — synthesized in §9)
authors: Claude (synthesis of two independent research efforts and existing project research)
---

# Engine A v3 — Bifurcated Rookie Forecast Design Spec

This document formalizes the binding design decisions for Engine A v3. It synthesizes three independent research efforts: (a) the original Phase 16 research brief held in the project repository, (b) a second commissioned research brief delivered 2026-05-23, and (c) a Claude deep-research review delivered 2026-05-23. Where the three efforts agree, the consensus is adopted as Required. Where two of three agree, the position is adopted with appropriate notes. Where only one effort makes a claim, it is treated as Candidate-only and quarantined from load-bearing status until independently replicated.

**Authority:** This document governs Engine A v3 analytical design after David approval on 2026-05-23. Where it conflicts with `00-product-constitution.md`, the constitution wins. Where it conflicts with earlier Phase 16 research, this document wins.

**Sequencing:** David approved this document and resolved Section 10 on 2026-05-23. Implementation may proceed through the governed Phase 19 execution plan.

---

## Section 1: The Bifurcation Decision

### 1.1 Decision

**Engine A v3 splits into two independent prediction heads, trained and promoted separately:**

- **Head A — Absolute Ranking.** Predicts career best-3-of-first-4-years PPR PPG. Includes NFL draft capital as a feature. Goal: be the most accurate rookie ranker available given all public information. Used when David's pick slot dominates the decision (1.01–1.05 in rookie drafts, top-of-Round-1 rookie startup picks).

- **Head B — Market Edge.** Predicts the *residual* of career PPG vs. an empirical expected-PPG-by-draft-pick curve. **Does not include NFL draft capital as a feature.** Goal: identify prospects whose collegiate signal predicts they will beat the public's draft-slot expectation. Used to flag Day 2 / Day 3 sleepers and to flag Round 1 picks whose collegiate profile does not support their slot.

### 1.2 Rationale

Both independent research efforts and the deep-research review converged on the bifurcation thesis. The original Phase 16 brief in the repo framed it as "Objective A / Objective B." The second commissioned brief used the same framing. The deep-research review confirmed the architecture matches the only credible path to extract a market edge from collegiate signal.

The current Engine A v2 is a single per-position Ridge model on pick, round, and age, producing a single dynasty_value_score. It is structurally honest but offers no information beyond what the public draft board already prices in. Per the constitution's evidence hierarchy, model credibility is earned by usefully *diverging* from the market over time, not reconstructing it. A single-headed model that maximizes overall MAE will keep collapsing toward draft capital because draft capital is the strongest single feature. The only architectural mechanism that extracts collegiate edge is to remove draft capital from the feature set in a parallel model whose target is the residual.

This mirrors Engine B v1 → v2: that transition stratified by position to prevent within-model collinearity; this one stratifies by *objective* to prevent within-objective collinearity with the public board.

### 1.3 Constraint

Both heads respect the existing `engine_a_contract.py` PROHIBITED_COLUMNS and LEAKAGE_REGEX. Market overlay fields (`ktc_value`, `fantasycalc_value`, `adp`, `fantasypros_consensus`, etc.) remain banned from both feature matrices. Head B's exclusion of draft capital is an *additional* contract beyond universal leakage rules — encoded in a new `HEAD_B_PROHIBITED_COLUMNS` set that adds `nfl_pick`, `nfl_round`, and any derived draft-capital features.

---

## Section 2: Target Variables

### 2.1 Head A target

**Decision:** Best 3 of first 4 seasons average PPR PPG.

**Rationale:** Mirrors Engine B's 2-year average decision (Q1 of 03-engine-b-decision-record.md) but extends to capture late-blooming Day 3 hits (Adam Thielen Year 4, Tyreek Hill Year 2). Year-1 PPG biases toward immediate-opportunity picks and underweights development.

**Filter:** Players with fewer than 4 NFL seasons of opportunity (2022+ classes) get a censoring flag and are excluded from training but included in scoring inference.

### 2.2 Head B target

**Decision:** `residual_ppg = actual_best3of4_ppg - expected_ppg_at_pick`, where `expected_ppg_at_pick` is computed per position from a position-specific isotonic regression of best-3-of-4 PPG on overall draft pick number, fit on 2010–2021 cohorts.

**Rationale:** Isotonic regression (PAVA algorithm) was the recommended draft-capital transform in the Phase 13 research brief because it respects the observed cliff structure (R1→R2 cliff, R2→R3 cliff for WR, mid-R4 to R5 anomaly for TE). Building Head B's target on the same transform inherits Phase 13's work and keeps the architecture coherent.

**Secondary target:** A binary "beat the bucket median" classifier (top-quartile vs. bottom-three-quartiles within ±20 picks). Easier to calibrate, more intuitive for the rookie board UI. Head B produces both: the continuous residual drives ordering, the binary probability drives the sleeper-alert surface.

### 2.3 Per-position fitting

Curves are fit per position because the decay shapes differ:

- **WR:** Steepest R1→R2 cliff. The second research brief confirmed: "Since 2015, WRs drafted in Round 4 or later have produced a dismal 4.4% hit rate." Round 5 is a within-Day-3 anomaly (Hill, Nacua, Diggs).
- **RB:** Flatter curve. Top-20 RBs over the past five drafts have a 100% top-12 PPR rookie finish rate (Robinson, Gibbs, Jeanty). Meaningful Day 3 hit rate (~6%) persists due to receiving-back archetype.
- **TE:** Non-monotonic raw data due to mid-R4/R5 anomalies (Kittle, Schultz, Ferguson). Must be smoothed before isotonic fitting or use hierarchical pooling with the WR curve as a shrinkage prior (Phase 13 recommendation). TE annual cohort is too small (~3–5 fantasy-relevant TEs/year) for an unpooled isotonic fit to stabilize.

---

## Section 3: Feature Contracts

### 3.1 Universal rules (both heads, all positions)

| Field | Class | Source | Status |
| :--- | :--- | :--- | :--- |
| `age_at_draft` | Foundational | nfl_data_py / verified DOB | Required |
| `nfl_pick` / `nfl_round` | Draft capital | nfl_data_py | **Required for Head A; banned from Head B** |
| `position` | Foundational | nfl_data_py | Required (stratification routing) |
| `early_declare` | College | CFBD (years played) | Required |
| `final_college_age` | College | CFBD | Required |
| `weight` / `height` | Physical | NFL Combine / RAS.football | Required |
| `covid_eligibility_flag` | Era indicator | CFBD (years played > 4 or year-since-HS > 4) | **Required — new in v0.2 per second-research brief; see §7.4** |
| `transfer_portal_flag` | Era indicator | CFBD (school changes in career) | **Required — new in v0.2 per second-research brief; see §7.4** |

### 3.2 NFL Combine feature philosophy (§ new in v0.2)

The second research brief introduced Szekely et al. (2023, arXiv:2303.05774) as the cleanest current peer-reviewed work on Combine predictiveness. Findings:

- **Combine metrics predict NFL matriculation (whether a player will see one NFL snap) with 83% accuracy.**
- **Combine metrics fail to predict long-term career success.** RMSE = 1,210 snaps; explained variance very low.

This crystallizes a framing already implicit in Kuzmits & Adams (2008) and Teramoto et al. (2016): the Combine is a *viability gate*, not a *continuous performance predictor*, with two specific exceptions.

**Decision (v0.2):**

- Use generic Combine composites (broad jump, bench press, shuttle, 3-cone for non-RB positions, raw 40-time for WR) as **viability gates only**. They contribute to a boolean `meets_athletic_floor` feature, not as continuous inputs.
- The two exceptions enter as continuous features per Teramoto et al. (2016):
  - **10-yard split for RB** (peer-reviewed: p < 0.001 on career YPC after draft-position control).
  - **Vertical jump for WR** (peer-reviewed: p = 0.004 on career YPR after draft-position control).
- The Speed Score transform (Barnwell 2008) wraps RB weight + 40-time into a single composite that geometrically penalizes slow times relative to mass. Use as the primary RB speed-size feature; the raw 40 enters only as a component of Speed Score, not as a standalone.
- WR 40-time is not used in isolation. The deep-research review and the second commissioned brief both confirmed Pearson ~0.004 to fantasy outcomes when isolated. May enter as a component of derived features (e.g., personnel-adjusted speed score for WR), not standalone.

### 3.3 WR feature contract

| Feature | Source | Head A | Head B | Evidence | Status |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `wr_breakout_age` | CFBD-computable (20% Dominator) | ✓ | ✓ | Siegele 2014; PFF backtests; both new brief and deep research confirm sub-19 BoA as strongest single age-adjusted signal | Required |
| `wr_dominator_career` | CFBD | ✓ | ✓ | PlayerProfiler 12-yr sample: only Edelman violates 25% min for multi-1000-yard. See §7.2 outlier-handling. | Required |
| `wr_dominator_final` | CFBD | ✓ | ✓ | Standard production filter | Required |
| `wr_market_share_yds` | CFBD | ✓ | ✓ | RotoViz / Siegele team-context-adjusted production | Required |
| `wr_rec_tds_per_game_final` | CFBD | ✓ | ✓ | RotoViz Jefferson heuristic (≥0.45/G) — one input among many | Required |
| `wr_yards_per_reception_career` | CFBD | ✓ | ✓ | aDOT proxy when route-charting unavailable | Required |
| `wr_vertical_jump` | NFL Combine | ✓ | ✓ | **Teramoto et al. 2016, p=0.004 after draft-position control** | Required |
| `wr_meets_athletic_floor` | Boolean (per §3.2) | ✓ | ✓ | **Szekely et al. 2023 viability-gate framing** | Required |
| `wr_ras_composite` | RAS.football | ✓ | ✓ | Floor effect: sub-5 RAS rarely hits top-30. Constitution: RAS is risk/context, not a positive lift. | Required (already adapter-pending in source registry) |
| `wr_yprr_final` | PFF objective charting | ✓ | ✓ | Confirmed strong predictor in both research efforts; PFF objective charted YPRR (not subjective grade) is the load-bearing input | Candidate — gated on §6.1 |
| `wr_yprr_zone` | PFF objective charting | ✗ | candidate | Single original-brief claim; **second research brief did not corroborate. Quarantined.** | **Candidate only — see §7.3** |
| `wr_first_downs_per_route_run` | PFF / Fantasy Points | ✗ | candidate | Single original-brief claim; **second research brief did not corroborate. Quarantined.** | **Candidate only — see §7.3** |
| `wr_contested_target_rate` | PFF | ✗ | candidate | **Single original-brief claim (Fantasy Life #15). Deep-research review flagged as overstated. Second research brief did NOT mention CCTR. Two independent reviews failed to corroborate. Quarantined.** | **Candidate only, low confidence — see §7.3** |
| `wr_early_declare` | CFBD | ✓ | ✓ | RotoViz / Siegele: early declares perform like a full draft round better | Required |

### 3.4 RB feature contract

| Feature | Source | Head A | Head B | Evidence | Status |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `rb_speed_score` | NFL Combine | ✓ | ✓ | Barnwell 2008, 15+ years of evidence; Teramoto 2016 peer-reviewed 10-yard split predicts career YPC after draft-position control (p<0.001) | Required |
| `rb_10_yard_split` | NFL Combine | ✓ | ✓ | **Teramoto et al. 2016 (peer-reviewed): primary biomechanical predictor of career YPC** | Required |
| `rb_weight` | NFL Combine | ✓ | ✓ | Component of Speed Score; durability proxy | Required |
| `rb_3cone` | NFL Combine | ✓ | ✓ | Lateral agility — distinct from WR boundary speed need | Required |
| `rb_meets_athletic_floor` | Boolean (per §3.2) | ✓ | ✓ | Szekely et al. 2023 viability gate | Required |
| `rb_ras_composite` | RAS.football | ✓ | ✓ | Sub-7.4 RAS rarely hits top-10 fantasy (KLP analysis) | Required |
| `rb_career_dominator` | CFBD | ✓ | ✓ | 15% threshold (PlayerProfiler); team-adjusted production | Required |
| `rb_final_dominator` | CFBD | ✓ | ✓ | Final-season weight | Required |
| `rb_scrimmage_ypg` | CFBD | ✓ | ✓ | FantasyLife Rookie Super Model central input | Required |
| `rb_rec_ypg` | CFBD | ✓ | ✓ | Phase 16 prior brief: highest evidence-to-cost ratio new RB input | Required |
| `rb_school_sp_plus` | CFBD | ✓ | ✓ | SOS adjustment — critical for transfer-portal-era stability (see §7.4) | Required |
| `rb_backcast_inputs` | CFBD + Combine | ✓ | ✓ | BackCAST methodology (YPC × weight × dominator-share); not the final BackCAST score, just the components, fit fresh per v3 | Required |
| `rb_age_at_draft` | nfl_data_py | ✓ | ✓ | Phase 16 prior brief: chronological age does NOT improve RB models after draft-capital control (Heath 2026). Expect near-zero coefficient. | Required |
| `rb_mtf_per_touch` | PFF objective charting | ✓ | ✓ | Stable year-over-year; **per-touch only** — raw MTF count is non-predictive (R²~0.04 per Fantasy Life) | Candidate — gated on §6.1 |
| `rb_tprr_final` | PFF objective charting | ✓ | ✓ | Most predictive RB receiving usage variant (Heath) | Candidate — gated on §6.1 |
| `rb_yards_created_per_carry` | Fantasy Points charted | ✗ | candidate | Strong evidence but heavily proprietary; manual CSV ingestion only | **Ablation-only** |

### 3.5 TE feature contract

| Feature | Source | Head A | Head B | Evidence | Status |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `te_ryptpa_final` | CFBD-computable | ✓ | ✓ | FantasyLife Rookie Super Model central TE input; ≥1.50 benchmark, ≥2.83 elite | Required |
| `te_career_dominator` | CFBD | ✓ | ✓ | 15% threshold (PlayerProfiler glossary) | Required |
| `te_yards_per_reception_career` | CFBD | ✓ | ✓ | aDOT/depth proxy; ≥12.0 in PP breakout sample | Required |
| `te_deep_yard_share` | CFBD | ✓ | ✓ | Heath: TEs with <10% deep-yard share essentially never hit ceiling (2/29 historical) | Required |
| `te_height_adj_speed_score` | NFL Combine | ✓ | ✓ | PlayerProfiler: "most important athleticism metric" for TE | Required |
| `te_ras_composite` | RAS.football | ✓ | ✓ | **Both research efforts agree: 3.76 is the lowest RAS observed among top-10 fantasy TEs since 2003. Hard floor warning (not algorithmic kill — see §10 decision 2).** | Required |
| `te_weight` / `te_bmi` | NFL Combine | ✓ | ✓ | **Mulholland & Jensen 2014 (peer-reviewed JQAS): size measures are *over-weighted* in NFL draft. Head B explicitly captures this mispricing — coefficient may be negative or near zero, which is correct.** | Required |
| `te_age_at_draft` | nfl_data_py | ✓ | ✓ | Required for routing but expect near-zero coefficient: Breakout Age does not predict at TE (BrainyBallers; both research efforts confirm). | Required |
| ~~`te_breakout_age`~~ | — | ✗ | ✗ | **Excluded. Both research efforts confirm BoA is not predictive at TE.** | Excluded |
| `te_yprr_career` | PFF objective charting | ✓ | ✓ | PFF rookie TE prospect model load-bearing input | Candidate — gated on §6.1 |
| `te_receiving_grade_pff` | PFF subjective grade | ✗ | ✗ | **Excluded per §6.3 — subjective PFF grades violate constitution. Use objective YPRR instead.** | Excluded |

### 3.6 Excluded features (do not enter either head)

- **All market overlay fields** (KTC, FantasyCalc, FantasyPros, DynastyNerds, ADP) — banned by `engine_a_contract.py`.
- **Subjective PFF film grades** — violates constitution evidence rule. Use PFF objective charting (YPRR, MTF/touch, route counts) instead.
- **Generic Combine composites as continuous features** — broad jump, bench press, shuttle, 3-cone for non-RB positions. Allowed only inside the `meets_athletic_floor` boolean.
- **Raw 40-yard dash for WR in isolation.** May enter as a component of derived features.
- **Bench press and broad jump for all skill positions** — Kuzmits & Adams 2008; both research efforts confirm.
- **Raw forced missed tackles** (counting stat, not per-touch).
- **TE breakout age as a "younger is better" signal** — empirically reversed at TE.

---

## Section 4: Model Architecture

### 4.1 Decision

**Per-position, per-head independent models:** 6 artifacts total — `wr_head_a_v3.pkl`, `wr_head_b_v3.pkl`, `rb_head_a_v3.pkl`, `rb_head_b_v3.pkl`, `te_head_a_v3.pkl`, `te_head_b_v3.pkl`. QB is out of scope for v3 (Engine A v2 QB grade is PROSPECT_D with negative R²; bifurcation premature until QB Head A is rescued separately).

### 4.2 Model class

**Decision:** Per-position bake-off between **Ridge** (current Engine A v2 / Engine B v2 incumbent) and **Gradient-Boosted Trees** (xgboost or lightgbm). Promotion gate selects whichever beats the naive baseline by the larger margin on the composite metric, **subject to a regularization-strength constraint** (see §7.2 outlier-handling).

**Rationale:** Ridge is the project incumbent and reliable. GBT handles non-linear interactions the rookie feature space exhibits (Speed Score × age, BoA × Dominator, RAS × draft bucket, deep-yard-share × YPC). The uploaded original Phase 16 brief prescribed RidgeCV without justification; the deep-research review flagged that as worth contesting; the second research brief was silent on model class. Let the bake-off decide.

**Constraint:** TE small-sample regime (≤120 historical rookies post-2010 with full feature coverage) likely favors Ridge with hierarchical pooling. RB and WR (≥400 each) are more open. Bake-off is per-position independent.

### 4.3 Position stratification

Mirrors Engine B v2 stage 6.2. Each position is its own model. No unified cross-position artifacts. Feature contracts may share rows (e.g., `age_at_draft`) but are evaluated and promoted independently.

### 4.4 Engine A v3 service layer

The existing `EngineAScorer` is extended (not replaced) with a `head` parameter:

```python
scorer.score(prospect, head="absolute")       # returns Head A DVS
scorer.score(prospect, head="market_edge")    # returns Head B residual + beat-bucket prob
scorer.score(prospect, head="both")           # returns both; default for rookie board
```

The rookie board renders both columns. PVO consumers receive both fields with explicit names (`dvs_absolute_v3`, `dvs_market_edge_v3`).

---

## Section 5: Evaluation Suite and Promotion Gates

### 5.1 Head A promotion gate

**Decision:** Head A v3 must outperform the Engine A v2 incumbent on a 2018–2023 holdout cohort on **≥ 2 of 3 metrics**:

- **RMSE** on best-3-of-4 PPG
- **Spearman rank correlation** with realized PPG
- **NDCG@10** of model ranking vs. realized career outcome ranking within position

Mirrors Engine B v2 promotion gate structure.

### 5.2 Head B promotion gate

**Decision:** Head B v3 must demonstrate edge on the holdout cohort on **≥ 2 of 4 metrics**:

- **Residual R²** — positive R² (any value above zero is signal) when predicting residual vs. draft-capital baseline on holdout. **Required.** Per the second research brief's recommendation, the aspirational target is **≥15% R² improvement** over a pure-draft-capital baseline for Day 2 and Day 3 WRs specifically (the highest-leverage market-edge cohort).
- **Within-tier pairwise accuracy** — for prospects within ±10 picks and ±0.5 years of age, percentage of pairs where Head B picks the eventual better fantasy producer. Baseline = 50%.
- **Top-5 Day 3 sleeper precision** — for each holdout year, take Head B's top-5 Day 3 picks (R4+); measure fraction producing a top-30 positional season within 4 years. Baseline = 4–6% (random Day 3 selection). Target ≥15% (3× base rate).
- **Calibration** — predicted residual vs. realized residual must be monotonic in deciles on holdout.

**Required:** Residual R² > 0 is non-negotiable. The other three select for *useful* signal direction.

### 5.3 Per-position independent promotion

Each of the six models is promoted (or held) independently. Failure of TE Head B does not block WR Head B. Mirrors Engine B v2 per-position rule.

### 5.4 Failure modes

- If Head B fails for a position, that position's Head A is the sole v3 output for that position. Market-edge column displays as `n/a` with UI caveat.
- If both heads fail for a position, Engine A v2 remains active for that position; no v3 promotion.

### 5.5 Holdout cohort definition

- **Training:** 2010–2017 cohorts with full feature coverage. Pre-2014 rows where PFF features are unavailable use a missingness indicator (not median imputation per constitution).
- **Validation:** 2018–2021 cohorts.
- **Holdout (gate):** 2022–2023 cohorts. **Censoring flag** for incomplete career arcs (best-3-of-4 may be best-3-of-2 for 2023 picks).
- **Inference:** 2024–2026 cohorts.

---

## Section 6: Conflicts and Source Governance

### 6.1 PFF intake — decision required

The strongest WR/RB/TE candidate features (YPRR, MTF/touch, TPRR) originate from PFF objective charting. Source registry currently classifies PFF as `context_signal`, intake = manual CSV with documented provenance. Both research efforts flagged this as the largest available lift.

**Decision:** This document does not resolve PFF intake. Escalated to David in §10. Until PFF resolves, candidate-marked features in §3.3–3.5 train against missingness-indicator-flagged null columns and the bake-off ablates with vs. without. **No median imputation** — structural missingness >20% drops the feature, not the row.

### 6.2 PlayerProfiler decision gate — orthogonal to v3

PP is `context_signal` per Task 3 of the data source roadmap (probe gate not yet passed). The features the original brief wanted from PP (`breakout_age`, `dominator`, `speed_score`) are all **computable from CFBD raw data**. PP intake remains gated and orthogonal to v3 promotion.

### 6.3 PFF subjective grades vs. PFF objective charting (§ new in v0.2)

The second research brief explicitly addressed this and aligns with the constitution: **subjective PFF "grades" (the proprietary 0–100 film grade) violate the evidence rule and are excluded**. PFF *objective charted data* (per-route output, target counts, route counts, MTF per touch, alignment data) is acceptable as a `model_input` candidate, gated on §6.1. This refinement is encoded in the source registry update accompanying this spec.

### 6.4 Market overlay isolation

Reaffirmed. Market fields remain banned. `validate_governance.py` MARKET_FEATURE_RE check applies. Head B's *evaluation* may compare its sleeper picks against contemporaneous KTC / FantasyCalc rookie pick valuations as an *outcome overlay*, but never as a training feature.

### 6.5 Era boundary handling

Training data 2010–2023. PFF charted features only exist 2014+. Two options:

- **(a)** Train on 2014+ only; lose ~4 cohorts.
- **(b)** Train on 2010+ with missingness indicators for PFF-derived columns and let the model learn the conditional distribution.

**Decision:** (b). Throwing out 40% of pre-PFF cohorts for one feature family is the wrong trade. Explicitly reverses the original Phase 16 brief's truncation proposal.

---

## Section 7: Risks and Mitigations

### 7.1 NCAA Transfer Portal era (§ new in v0.2)

The post-2018 transfer portal has materially changed the stability of collegiate signal. Players frequently change schools mid-career, switching offensive schemes, quarterback quality, and conference strength. Dominator Rating and Breakout Age — both core WR features — depend on team context for normalization. A WR transferring from a Group of 5 powerhouse to an SEC bottom-feeder can show artificially deflated production despite identical underlying ability.

**Mitigation:**
- `transfer_portal_flag` feature (Required per §3.1) counts mid-career school changes.
- `rb_school_sp_plus` and equivalent per-position SOS-adjusted production features explicitly normalize for school-and-season offensive context.
- For prospects with transfer history, weight career signals using the SP+ rating of each school-season rather than career raw averages.
- TDD: a regression test that a synthetic prospect with identical raw counting stats but different SP+ context produces different Head B residuals.

### 7.2 Overfitting to generational outliers / survivorship bias (§ new in v0.2)

Julian Edelman is the singular WR in a 12-year sample with multiple 1,000-yard NFL seasons and a career Dominator <25%. Puka Nacua is a multi-standard-deviation Day-3 anomaly. Adam Thielen entered as UDFA. A naive Head B that successfully retrofits these profiles risks overfitting to their *specific* outlier signatures and flagging structurally similar but talent-inferior comps as sleepers.

**Mitigation:**
- Apply L2 regularization (Ridge) or `min_samples_leaf` constraint (GBT) tuned by cross-validation, not just held-out evaluation.
- Run a "leave-one-outlier-out" ablation: refit Head B without Nacua, Edelman, Hill, Thielen individually. If model coefficients shift materially, the model is too dependent on individual outliers and regularization tightens.
- Required artifact: `head_b_outlier_sensitivity_report.json` documenting coefficient stability under leave-one-out.

### 7.3 Load-bearing-feature quarantine (CCTR, Zone YPRR, 1D/RR)

The original Phase 16 brief proposed making Career Contested Target Rate (CCTR) the central orthogonal feature, citing a 0.40 PPG correlation, -0.03 to draft capital, and a 50% Round 3 hit rate. The deep-research review flagged this as a single-source claim contradicted by Jakob Sanderson's 2025 multivariate analysis. **The second independent research effort (Google Doc, 2026-05-23) did not mention CCTR at all.** Two independent reviews failed to corroborate it.

**Decision:** CCTR, Zone YPRR, and First Downs per Route Run enter Head B as candidate features behind a feature flag. **Head B must pass its promotion gate without any of these three features.** If the bake-off shows Head B passes without them, they are welcomed as marginal lift. If Head B passes *only because of* one of them, the result is held suspect pending replication on at least one additional independent draft class or independent research source.

This rule is encoded in the bake-off ablation matrix.

### 7.4 COVID-19 eligibility distortion (§ new in v0.2)

The 2026 draft class contains athletes who used their COVID-19 extra year of eligibility. This artificially inflates `final_college_age` and may artificially inflate `wr_dominator_final` for fifth- and sixth-year seniors padding stats against younger opposition. Without correction, the sub-19 Breakout Age signal and early-declare signal will both be biased.

**Mitigation:**
- `covid_eligibility_flag` feature (Required per §3.1) for any prospect with years-played > 4 or years-since-HS > 4.
- For prospects with the flag, age-at-draft features remain raw (still useful), but `final_college_age` is normalized to its 22-year-old equivalent (subtract 1 year) only for the purpose of derived early-declare comparison flags.
- TDD: synthetic prospect with covid flag must produce a different early-declare classification than identical non-flag prospect.

### 7.5 Coverage scheme metagame shifts

The Zone YPRR feature (currently quarantined per §7.3, but if promoted later) depends on the NFL maintaining current 66–75% zone coverage distribution. If defensive metagame shifts to predominantly man (e.g., to counter modern spread offenses), historical Zone YPRR coefficients lose predictive validity rapidly.

**Mitigation:** If Zone YPRR is ever promoted out of quarantine, add a yearly drift monitor on NFL aggregate man/zone distribution. If the distribution drifts >5 percentage points in any direction over two consecutive seasons, retrain.

### 7.6 TE evaluation uncertainty

TE annual cohort is small (~3–5 fantasy-relevant per year). The 3.76 RAS floor is an *observed historical* phenomenon, not a biological absolute — applying it as a hard kill could in principle eliminate a productive outlier. The Mulholland & Jensen mispricing finding is from 2014 data; modern TE draft economics may be partially correcting (Bowers R1, LaPorta R2, McBride R2).

**Mitigation:**
- TE RAS below 3.76 generates a UI warning ("Sub-floor athleticism — historically zero top-10 fantasy seasons since 2003"), not an automatic model kill. See §10 decision 2.
- TE Head B uses hierarchical pooling with WR curve as a prior; expect wider confidence intervals on TE residuals.
- Replicate Mulholland & Jensen methodology on 2014+ cohort as a v3 sanity check; if size over-weighting has substantially diminished, demote `te_weight` from Required to Candidate.

### 7.7 Data source attrition

CFBD rate limits (1,000 calls/month free tier; 75,000 calls Patreon Tier 3). PFF intake (whatever §10 decision 1 resolves to) is fragile. The PlayerProfiler shadow-API path remains brittle.

**Mitigation:**
- Nightly cron with cached parquet output.
- Skip-enrichment-fallback behavior must trigger explicit monitoring alerts, not silent null-fill. Existing source-registry governance handles this; v3 inherits.

---

## Section 8: Workstream Plan

Phase 19 proceeds in six workstreams. W1, W2, W3 are sequential. W4 and W5 may parallelize after W3.

### W1 — Head B target pipeline (Claude, 2 sessions)
- Isotonic regression baseline per position on 2010–2021 cohorts.
- Write `residual_ppg` and `expected_ppg_at_pick` columns to `prospects_with_outcomes_v3.csv`.
- Per-position hierarchical pooling for TE.
- TDD: monotonicity test on `expected_ppg_at_pick`.
- Artifact: `app/data/training/expected_ppg_curves_v3.json`.

### W2 — Feature pipeline build-out (Codex, 4 sessions; +1 vs. v0.1 for era-flag work)
- Extend CFBD adapter: Dominator, RYPTPA, school SP+, returning production, deep-yard share.
- New: `covid_eligibility_flag`, `transfer_portal_flag` computation.
- Confirm RAS adapter coverage per Task 5 of data source roadmap.
- Confirm NFL Combine ingestion for vertical, 3-cone, weight, height, 10-yard split.
- Output: `prospects_with_outcomes_v3.csv` with all §3 Required columns populated. Missingness flags for all Candidate columns.
- TDD: feature contract test asserts no `market_overlay` source contributes any column; no `nfl_pick`/`nfl_round` reaches Head B's allowed feature list; subjective PFF grades not present.

### W3 — Head A v3 bake-off (Claude + Codex, 3 sessions)
- Ridge vs. GBT bake-off per position.
- Validation report against Engine A v2 incumbent on 2018–2023 holdout.
- Promotion decision per position.
- Artifacts: `{wr,rb,te}_head_a_v3.pkl` for positions clearing gate.

### W4 — Head B v3 bake-off (Claude + Codex, 4 sessions; +1 vs. v0.1 for outlier-sensitivity work)
- Bake-off structure mirrors W3 but with `HEAD_B_PROHIBITED_COLUMNS` enforced.
- Ablation matrix: with vs. without each candidate feature (CCTR, Zone YPRR, 1D/RR, PFF YPRR, PFF MTF/touch).
- **New: leave-one-outlier-out sensitivity report** (Nacua, Edelman, Hill, Thielen, etc.). Artifact: `head_b_outlier_sensitivity_report.json`.
- Promotion decision per position.

### W5 — Service layer and rookie board integration (Codex, 2 sessions)
- Extend `EngineAScorer` with `head` parameter.
- PVO `dvs_absolute_v3` + `dvs_market_edge_v3` fields.
- Rookie board UI shows both columns side-by-side.
- Caveats propagate per Engine B v2 precedent.
- Regression tests: no Engine A v2 ranking drifts >5 positions for unchanged inputs.

### W6 — Era-drift monitoring (Claude, 1 session)
- TE coefficient-stability check vs. Mulholland & Jensen 2014 baseline.
- NFL man/zone distribution drift monitor (deferred-active until Zone YPRR exits quarantine).
- Transfer portal flag distribution by class — quality control.

**Estimated total: 16 agent sessions** (up from 13 in v0.1 due to era flags, outlier sensitivity work, and the W6 drift monitor).

W1 is authorized to begin after the approved design record and execution plan are committed.

---

## Section 9: Research Synthesis Notes

Three independent research efforts were consulted:

- **(a)** Original Phase 16 research brief in the project repository (existing, pre-2026-05-23).
- **(b)** Phase 16 second research brief commissioned 2026-05-23 (Google Doc).
- **(c)** Engine A deep-research review by Claude, 2026-05-23.

**Consensus across all three (adopted as Required):**

- Bifurcation architecture (Objective A / Objective B).
- Residual-vs-draft-capital target for Head B.
- Position stratification.
- Market data isolation.
- Top-k sleeper hit rate over RMSE as the headline Head B metric.
- Breakout Age (WR) as a strongly predictive feature, with sub-19 BoA as the strongest single signal.
- Mulholland & Jensen (2014) TE size-over-weighting as the theoretical foundation for TE Head B.
- TE Breakout Age as not predictive (excluded).
- WR 40-time in isolation as not predictive (excluded standalone).
- Speed Score (Barnwell 2008) as primary RB speed-size composite.
- 10-yard split (Teramoto 2016) as primary RB biomechanical predictor.
- Vertical jump (Teramoto 2016) as primary WR athletic-test predictor.
- Subjective PFF grades excluded; PFF objective charting allowed (gated on §6.1).

**Consensus across (b) and (c) only (adopted with notes):**

- **Szekely et al. 2023 viability-gate framing** for Combine metrics — incorporated in §3.2.
- **NCAA Transfer Portal era risk** — incorporated in §7.1.
- **COVID-19 eligibility distortion** — incorporated in §7.4.
- **Survivorship-bias / outlier overfit risk** — incorporated in §7.2.

**Claims unique to (a) only — quarantined to candidate-only status:**

- **CCTR as load-bearing orthogonal feature.** Not corroborated by (b) or (c). Quarantined per §7.3.
- **Zone YPRR as load-bearing.** Not corroborated by (b) — only mentioned as a noted-but-not-load-bearing factor. Quarantined per §7.3.
- **First Downs per Route Run.** Same regime. Quarantined per §7.3.

**Claims unique to (b) only — adopted because peer-reviewed:**

- Szekely et al. 2023 study findings (matriculation 83%, success near-zero).
- COVID-19 eligibility distortion analysis.

**Claims unique to (c) only — adopted because peer-reviewed or methodologically anchored:**

- Specific Teramoto 2016 p-values (p=0.004 vertical jump; p<0.001 10-yard split).
- Speed Score historical floor (Arian Foster 94.2).
- BackCAST attribution (Nathan Forster, *Pro Football Prospectus 2008*).

This section is frozen for Phase 19 execution. Any new research claim that would change a Required feature, target, gate, or data source requires a follow-up decision record.

---

## Section 10: Locked Decisions

David approved the following decisions on 2026-05-23. These choices are binding for Phase 19 unless David explicitly reopens them.

1. **PFF intake:** Option A. Manual annual CSV exports against documented snapshots for v3.

2. **TE RAS floor handling:** Option B. UI warning plus severe negative modifier for sub-3.76 RAS; no hard algorithmic kill and no zeroed DVS solely from this floor.

3. **Naming scheme:** Phase 19. This document supersedes much of the existing Phase 16 brief but is executed as Phase 19.

4. **Model class:** Run position-specific GBT vs. Ridge bake-offs. Do not preselect Ridge or GBT globally.

5. **2022–2023 holdout:** Option A. Use 2022–2023 as holdout with an explicit censoring flag for incomplete career arcs.

6. **Combine-decline handling:** Option B. Use pro-day data with explicit error margin, a `pro_day_only_flag`, and the standard discount documented in the feature pipeline.

7. **Outlier-sensitivity threshold:** Option A. Strict threshold: any Head B feature whose coefficient drifts by more than 25% under removal of any single outlier is demoted to Candidate status.

---

## Section 11: Acceptance Criteria for v1.0 Promotion

Drawn from the second research brief and refined for v3 specifics. Engine A v3 enters production only after **all five gates pass**:

1. **Identity Integrity Gate.** CI demonstrates 100% deterministic identity matching for the top 100 prospects in the 2026 class across Sleeper, CFBD, nflverse, and (if intake authorized) PFF. Zero fuzzy matches in production logs.

2. **Model Segregation Gate.** Head B codebase audit confirms `nfl_pick`, `nfl_round`, and all derived draft-capital features are absent from training features. `HEAD_B_PROHIBITED_COLUMNS` is enforced by a unit test, not just convention.

3. **Baseline Replication Gate.** Head A correctly identifies ≥80% of top-12 rookie running back finishers in 2021–2025 backtests within its top-12 absolute-rank output per class. (Tunable; if 80% is unachievable, this becomes "≥the v2 incumbent's hit rate" with a documented delta.)

4. **Residual Validity Gate.** Head B Day 2 + Day 3 WR cohort achieves ≥15% R² improvement over a pure-draft-capital baseline when predicting best-3-of-4 PPR PPG residual. (Stretch target; if this is unachievable, gate is "≥5% R² improvement and ≥2× top-5 sleeper hit-rate over baseline.")

5. **Data Ingestion Gate.** System computes Speed Score, Breakout Age, Dominator Rating, RYPTPA, and `meets_athletic_floor` for the full 2026 class automatically. No manual data entry except authorized PFF CSV (per §10 decision 1).

Plus the universal governance gate:

6. **Constitution Conformance Gate.** `validate_governance.py` passes with no warnings. Source registry leakage scan returns zero violations. `engine_a_contract.py` + new `head_b_contract.py` both pass test suite.

---

## Section 12: Document Status and Promotion Path

- **Current status:** Approved Phase 19 design record.
- **Promotion path:** This v0.2 document governs Phase 19 execution. A later v1.0 governance record may move to `docs/governance/04-engine-a-v3-decision-record.md` after implementation evidence and validation reports exist.
- **During Phase 19:** Implementation proceeds through the repo-native execution plan. No production Engine A v3 model artifacts may be promoted until the Section 11 gates pass and David approves the promotion decision.
- **Supersession:** Existing Phase 16 feature recommendations remain historical context; this document controls Engine A v3 bifurcation scope.
