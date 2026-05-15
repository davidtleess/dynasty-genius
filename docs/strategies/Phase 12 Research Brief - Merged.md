# Dynasty Genius — Phase 12 Research Brief (Merged)
*Prepared May 2026 · Superflex PPR (12-team, 2QB, full PPR)*

---

## 1. Executive Recommendation

**Phase 12 committed scope: Operational Artifacts + Trust Surface v2.**

Phase 12 has a natural two-act structure, but only Act 1 is committed scope. Act 2 is a conditional candidate pending Act 1 review.

**Act 1 — Committed (prerequisite):** Execute the first operational backtest run end-to-end on the Phase 10/11 harness, generating versioned, auditable artifacts per position (QB, RB, WR as active; TE as experimental). This converts Phase 10/11 from "harness exists" to "harness has spoken." The Trust Surface is currently a route without a payload; Act 1 gives it one. This is the highest-confidence, lowest-risk Phase 12 work: no new modeling, no governance edges, pure productionization of validated infrastructure.

**Act 2 — Conditional (DVS design + implementation):** Operationalize the `dynasty_value_score` field using isotonic regression calibration and exponential decay transformation. This is architecturally important — it unifies Engine A's 0–100 prospect composite and Engine B's PPG forecast into a single cross-positional currency — but it is **not approved Phase 12 scope** until: (a) Act 1 artifacts are generated and reviewed, (b) calibration diagnostics confirm the fold outputs are a valid calibration surface, and (c) a written spec is approved. Until those gates pass, DVS implementation belongs to Phase 13.

The research in Sections 5–6 documents the DVS design so the spec can be written immediately after Act 1. It is design-ready, not implementation-approved.

**Deferred — TE Diagnosis (Phase 13):** Once Phase 12 artifacts document *quantitatively* where TE failed (calibration? rank correlation? archetype heterogeneity?), a targeted remodel is possible.

**Deferred — RB feature expansion:** RYOE has near-zero year-over-year stability (nfeloapp analysis: effectively a coin flip after one season). Weighted Opportunity has strong evidence (0.95–0.97 PPR point correlation) but adding it before baseline validation introduces noise. Defer until Phase 13 baseline metrics exist.

---

## 2. Why Artifacts Must Precede DVS

The DVS-focused report correctly identifies a real architectural need: Dynasty Genius eventually needs a single comparable value currency. The issue is sequence.

Until the first operational artifacts exist, the system does not know:
- which positions pass which gates on current operational data;
- how calibrated PPG forecasts are by decile (the calibration surface DVS requires);
- where exactly TE breaks (rank, calibration, market comparison, sample size, or role-feature absence);
- whether market-comparison folds are populated enough for G3;
- what the disagreement ledger says about model-vs-market cases;
- how confidence intervals should be exposed to downstream decision surfaces.

The governance-safe order is fixed:

1. Generate evidence (operational artifacts).
2. Expose evidence (Trust Surface v2 with model cards).
3. Diagnose weak points (TE failure mode, calibration drift).
4. Calibrate and normalize into a unified value score (DVS v1).

Shipping DVS before this sequence would launder unverified model uncertainty into a single number that appears authoritative. The artifacts are not overhead before DVS; they are the mathematical substrate DVS is calibrated on.

DVS design notes from the research should be retained as a **Phase 12 appendix** (Section 4), not as the Phase 12 core build.

---

## 3. Phase 10/11 Backtest Harness — Implications

The Phase 10/11 harness creates capability; Phase 12 creates evidence. The harness (walk-forward 2018–2023, 4 folds, market comparison, G1–G4 gates, artifact persistence, CLI, Trust Surface route) builds the infrastructure. The operational first run populates it.

### 3.1 What the First Run Must Produce (per active position and experimental TE)

1. **Per-fold prediction logs** — predicted vs. actual `avg_ppg_t1_t2`, with player_id, age at prediction, fold boundary year.
2. **Calibration plot data** — predicted-decile mean vs. observed mean PPG (reliability diagram inputs), residual histograms. This is the DVS calibration substrate.
3. **Rank metrics** — Spearman ρ and Kendall τ-b between model rank and realized rank within position, per fold and pooled.
4. **Market comparison ledger** — model rank vs. KTC/FC/DP rank at the start of each holdout year with realized outcome. The head-to-head scorecard governance requires for overlay-only credibility.
5. **G1–G4 gate evaluations** — pass/fail per position with raw metrics exposed, not just boolean.
6. **Subgroup slices** — age buckets, draft capital buckets, sample-size buckets — surfaces where calibration breaks down (tells you *why* TE failed).
7. **A Model Card per position** (Mitchell et al., 2018 schema — see Section 6).

### 3.2 The Expanding Window and Temporal Validity

Traditional static train-test splits are inadequate for sports analytics due to constant tactical evolutions (e.g., the league-wide shift to two-high safety shells suppressing deep passing efficiency). The walk-forward strategy ensures the model adapts to regime shifts without introducing look-ahead bias. The protocol retrains from scratch at each fold — evaluating frozen models is scientifically invalid.

**One high-value cheap upgrade:** Extend the walk-forward window to include the 2024 fold (2018–2024 training, 2025 holdout) if 2025 PPG outcomes are settled. This is among the highest-value additions at low engineering cost.

### 3.3 Market Outperformance and the NDCG Paradigm

The transition from Spearman's ρ to Kendall τ-b is a critical statistical correction. In small datasets with heavy tails (e.g., ~30–50 starting QBs), Spearman is disproportionately skewed by injury-driven outliers. Kendall τ-b evaluates pairwise directional agreement and is robust in restricted sample sizes with tied market values.

NDCG addresses the economic reality of Superflex dynasty: accurately ranking the 50th WR matters exponentially less than identifying the top-12 elite assets. The logarithmic discount heavily penalizes the model for missing on championship-leverage players while forgiving variance at replacement level. Passing the NDCG benchmark at depths of 12 and 24 proves the model optimizes for the decisions that actually determine dynasty outcomes.

### 3.4 Divergence Flag Validity

When algorithmic valuation significantly deviates from the market consensus, the system flags the asset as undervalued or overvalued. The Mann-Whitney U test validates these flags non-parametrically (distribution of year-over-year value changes violates normality assumptions). Crucially, hit rates must be adjusted against positional market beta — a flagged RB who depreciates 2% when the RB market depreciates 15% generated alpha, even though the absolute direction is negative. Bootstrap confidence intervals (10,000 resamples) wrap these rates to confirm the signal is not a statistical anomaly.

### 3.5 Risks to Mitigate

- **Phantom trust:** Trust Surface route exists but renders nothing decision-grade. If exposed externally before artifacts populate it, users overweight the model.
- **Silent overlay leakage:** Code review during artifact generation should confirm no path lets KTC/FC values into training labels or features.
- **`dynasty_value_score` time-bomb:** A field that's always `None` tends to get implemented under deadline pressure without validation. Phase 12 must either populate it under a gate or ship a guarded v0.
- **TE experimental status with no expiry:** "Experimental" becomes permanent without a scheduled remediation phase. Phase 12 artifacts make the diagnosis case for Phase 13.
- **Absolute prohibition on market feature leakage** remains the system's paramount governance rule. Market data exists solely as a post-scoring overlay for delta analysis. Recursive bias destroys long-term predictive validity.

---

## 4. Industry Landscape — Dynasty Valuation Methodologies

| Platform | Primary Data Source | Core Methodology | Output Scale |
|---|---|---|---|
| **KeepTradeCut (KTC)** | Crowdsourced K/T/C answers | Aggregate + hidden raw adjustment formula | 0–9,999 integer |
| **FantasyCalc (FC)** | Executed league trades (~2M scraped) | Convex optimization + 14-day half-life weighting | 0–10,000 |
| **DynastyProcess (DP)** | Expert Consensus Rankings (ECR) | Exponential decay + GAM pick blending + LOESS SF adjustment | 0–10,041 |

### 4.1 KeepTradeCut

Pure sentiment aggregator: users answer forced K/T/C three-way rankings before accessing data. KTC maintains **two entirely separate databases for Superflex and 1QB** — there is no formulaic conversion; the Superflex pool is independently crowdsourced, meaning positional scarcity is implicitly baked into the crowd's answers. Tight End Premium is layered algorithmically on top of the base PPR database rather than crowdsourced separately. The hidden raw adjustment formula (based on baseline value, best player in the trade, and the highest-valued asset overall) prevents users from executing trades where multiple low-value assets equal an elite asset. Values update continuously with each submission. Scale: **0–9999 integer** (top QB/WR sit ~9000+, depth pieces <2000).

**Limitation for Dynasty Genius:** Severe recency bias, wild fluctuations after single-game performances, overvaluation of unproven draft picks. Represents a tertiary market signal useful only for price discovery, not intrinsic player evaluation.

### 4.2 FantasyCalc

Empirical methodology: scrapes millions of executed trades from Sleeper and MyFantasyLeague (~129k leagues). A convex optimization algorithm treats each trade as a matrix equation where assets on both sides are presumed equal, minimizing the difference across hundreds of thousands of transactions to extract an isolated average trade value per player. Time-weighting applies a 14-day half-life to recent trades. The platform filters unfair trades and adjusts values for specific league settings, applying a calculated QB premium in Superflex formats. FantasyCalc also publishes Moving Standard Deviation (MSTD) as a volatility proxy and redraft-minus-dynasty value as a contender/rebuilder signal.

**Strength:** Most empirically grounded. **Limitation:** Reflects human decision-making, which is inherently biased and poor at long-horizon forecasting.

### 4.3 DynastyProcess

Most transparent methodology. Player values derived from **FantasyPros Expert Consensus Rankings (ECR)** transformed via an exponential decay curve. The 1QB-to-Superflex conversion is done via **LOESS regression on 1QB-vs-2QB overall ADP** (DLF/Mizelle ADP data) rather than separate crowdsourcing. Rookie pick values use a **blended GAM model** of two sub-models: "Perfect Knowledge" (value if you knew which player the pick became) and "Hit Rate" (probabilistic over historical hit rates at each draft slot), blended ~80/20 by default. Future picks discounted at ~80% per year (present-value). The `ffscrapr::dp_values()` R function returns a tidy frame with `value_1qb`, `value_2qb`, `ecr_1qb`, `ecr_2qb` on a 0–10,041 scale. Data CSVs available openly at github.com/dynastyprocess/data.

**Strength:** Open-source, tunable decay coefficient, rookie pick GAM blend. **Limitation:** Inherits ECR expert bias; not trained on realized outcomes.

### 4.4 Cross-Platform Observations

All three majors output cardinal values but the underlying signal is fundamentally **ordinal** (K/T/C responses, trade direction, ECR rank). The cardinal scale is a fitted *transform* of ordinal data — relevant to Dynasty Genius because the isotonic calibration approach (Section 5) maps model outputs through the same kind of monotone transform, but anchored to realized PPG outcomes rather than market sentiment.

None of the three platforms publishes a formal "positional replacement value" calculation. Positional scarcity handling is either implicit (crowd behavior for KTC/FC) or applied via a separate regression layer (DP LOESS). Dynasty Genius can improve on all three by anchoring explicitly to replacement-level PPG baselines derived from backtest folds.

---

## 5. DVS Deep Dive — Normalization, Calibration, and Bridge Design (Design Appendix)

### 5.1 Failure Modes of Naive Normalization

Standard normalization methods present significant failure modes with heterogeneous sports analytics data:

- **Min-max scaling:** Hyper-sensitive to outliers; assumes uniform distribution. A single season like Christian McCaffrey's 2023 compresses the rest of the RB distribution into an indistinguishable cluster.
- **Z-score / standardization:** Effective for normally distributed data but fails on the heavy right-skew inherent in elite athlete performance. Also produces values centered at zero, which is unintuitive for dynasty users.
- **Percentile rank within position:** Recommended as the *primary intermediate step*. Monotone, robust to outliers, directly interpretable ("89th percentile WR2 in PPG forecast"). However, discards magnitude of gap — the 99th and 95th percentile QBs may be miles apart in realized fantasy value.

### 5.2 The QB Problem in Superflex

Pooled cross-position normalization has a fatal flaw: in Superflex, QB1s naturally project ~22–25 PPG vs. ~15–18 for WR1s. A naïve scaling that pools all positions will push every elite QB to the top decile and suppress elite WR/RB assets to mathematically irrelevant tiers. This is not a calibration artifact — it is correct that QB1s are worth more than WR1s in Superflex. The challenge is expressing *how much more* in a principled way rather than through arbitrary weighting.

**Empirical evidence:** DraftExpert Pro auction data shows QB1-tier assets valued at $42–65 in a $200 Superflex budget vs. $14–22 in 1QB — approximately a 2.5–3× premium. KTC runs entirely separate databases for SF and 1QB, meaning this premium cannot be formulaically derived from 1QB values.

**Principled solution — VORP (Value Over Replacement Player):** Subtract the replacement-level PPG for each position before normalization. In a 12-team Superflex: **QB24, RB36, WR48, TE12** as replacement baselines (already encoded in the architecture's VAR constants). This converts PPG to "PPG above the last playable starter at your position" before any cross-positional comparison, making the Superflex QB premium emerge organically from the market structure rather than from a hardcoded multiplier.

### 5.3 Recommended Normalization Pipeline

**Step 1 — Positional VORP:** Subtract replacement-level PPG per position from Engine B outputs. This anchors all scores relative to replacement.

**Step 2 — Isotonic Regression Calibration:** Fit a monotone calibration from each engine's output to "realized positional percentile" using the backtest fold outputs. This maps both Engine A's 0–100 composite and Engine B's PPG floats to a uniform, tie-aware percentile rank. Isotonic regression is non-parametric and monotone — it preserves rank ordering and is robust to skewed data. This is the step that *requires* Phase 10/11 artifacts as input.

**Step 3 — Exponential Decay Scaling:** Map calibrated percentiles to a 0–10,000 cardinal scale via an exponential decay function. This replicates the steep premium on elite dynasty assets and eliminates the fractional-asset exploit (multiple depth pieces equaling one elite player) without requiring an arbitrary hidden adjustment formula like KTC's.

**Note:** The exponential coefficient should be empirically tuned against walk-forward fold data in the validation gate, not hardcoded until Act 1 artifacts confirm the distribution shape.

### 5.4 Prospect-to-Active Bridge

The hardest single design decision. Three candidate approaches:

1. **Direct calibration (recommended):** Fit a regression from Engine A's 0–100 composite to realized avg_ppg_t1_t2 for rookies once they have 1–2 NFL seasons. Backtest sample is small (~5–10 rookie classes) but tractable. This is the most honest approach: does Engine A's composite actually predict Engine B outcomes? Mark bridged values with high uncertainty bands; flag explicitly in the Trust Surface that rookie-year DVS is provisional.

2. **Common-currency in expected fantasy points:** Have Engine A output a *prior* on PPG (predicted mean + variance for years 1–3), then Engine B's output takes over as data accumulates — Bayesian model averaging across the transition. More elegant but requires Engine A to be reconfigured to emit PPG priors, which is out of scope for Phase 12.

3. **DP-style "Perfect Knowledge + Hit Rate" blend:** Score each prospect as a weighted average of (best-case projection, expected miss probability, present-value discount). This is operationally feasible using existing draft capital data. Useful as a v0 bridge if Approach 1 has insufficient calibration data at Phase 12 launch.

**Transition mechanics:** Two-engine blended weight: 100% Engine A pre-draft → linear handoff over years 1–2 → 100% Engine B by year 3. Display both source values during the transition period with confidence bands. Dynasty markets assign a "flexibility premium" to unassigned draft picks that evaporates the moment a pick is converted to a specific player — the Trust Surface should expose this effect explicitly.

### 5.5 Age Decay — Continuous, Never a Hard Cliff

A key governance rule: the unified valuation score must ingest biological aging as a continuous decay function, never as hardcoded binary cliffs. The evidence below confirms this is correct.

| Position | Peak Window | Modal Peak Age | Decline Initiation | Primary Predictive Metric |
|---|---|---|---|---|
| **RB** | 23–27 | 24–25 | ~26 (stairs, not cliff) | Yards Created + Missed Tackles Forced |
| **WR** | 25–29 | 26.95 | ~29 (gentle) | Yards Per Route Run (YPRR) |
| **TE** | 23–29 | Late-career jump Y1→Y2 | ~30 | Route participation + aDOT |
| **QB** | 28–34 | Long plateau | Mobile QBs ~33 | EPA per play + CPOE |

**RB:** The biological decline resembles a fall down a set of stairs beginning at 26, not a sudden cliff at 30. Apex Fantasy Leagues data: 76.5% of 15+ PPR seasons occur in the 22–26 window; average peak age 25.46. ESPN: 25.2% PPG decline from age-28 to age-29.

**WR:** Average peak age 26.95 (Apex). Elite route runners can sustain production into early 30s via technique, but efficiency metrics begin a sustained decline after age 28. YPRR ≥ 2.5 is the elite dynasty threshold; target share growth Y2Y is a useful early signal.

**TE:** ESPN data: TEs see ~98.5% increase from Y1 to Y2 — the largest sophomore jump of any skill position. Footballguys data: 85% of TE breakouts occur by Year 3. Biological cliff typically not until age 30. However, TE is TE only after role-stratified segmentation (see Section 5.1).

**QB:** Long plateau; meaningful production well into early 30s in Superflex. Mobile QBs: loss of rushing floor around age 33 destroys the elite ceiling. EPA per play and CPOE are the most stable predictors, effectively isolating QB contribution from surrounding offensive environment.

**Decay implementation:** For two players with identical 2-year PPG forecasts but different ages, apply a conditional continuous decay to the *3rd-year+ tail*: `expected_remaining_PPG-years × position_decay(age + 2)`, where `position_decay` is an empirically fit smooth function (logistic survival curve or LOESS on historical data). Never a hard threshold.

### 5.6 Scale and UX — Two-Tier Design

| Scale | Pro | Con |
|---|---|---|
| **0–10,000 (KTC-style)** | Market-familiar; integer-comfortable; supports trade math | False precision (no one knows what 7842 vs. 7891 means) |
| **0–100** | Intuitive percentile-flavored | Ceiling compression; Mahomes and Chase both register 99 |
| **Z-score** | Statistically clean | Opaque to non-technical users |
| **Positional rank + cardinal annotation (e.g., "WR4 — DVS 8,940")** | Combines ordinal interpretability with cardinal trade utility | Requires both surfaces |

**Recommendation:** 0–10,000 cardinal with positional rank and percentile annotations in the Trust Surface. This matches the market mental model players already have from KTC/FC. Internally, normalize via isotonic regression to realized positional percentile (5.3), then linearly scale to 0–10,000.

**Two-tier DVS design:** The DVS should expose two distinct fields rather than collapsing to a single number prematurely:
- `within_position_percentile` — calibrated percentile rank within position (e.g., 89th percentile WR). Achievable once backtest calibration data exists. Easier, safer, and interpretable.
- `cross_position_value_score` — 0–10,000 cardinal cross-positional score. Requires validated VORP anchoring and the prospect bridge. Phase 13 target.

The first field closes the `dynasty_value_score` `None` time-bomb without overclaiming. The second should not be shipped until artifact evidence supports it.

---

## 6. Position-Specific Research

### 6.1 TE Diagnosis (critical, sets Phase 13 agenda)

**Why TE modeling fails:**

- **Role heterogeneity:** Inline blocker, big slot, Y-iso wide-flexed, and move TE are effectively four different positions sharing one label. A model trained on the pooled population learns the "average TE," which describes few actual TEs.
- **Small effective sample:** ~32 TE starters/year × 4–5 walk-forward folds ≈ 160 starter-season rows per fold before subgroup splits. This is the hard data floor.
- **TD variance dominates short-window PPG:** TE fantasy output is more touchdown-dependent than RB/WR, making PPG noisy and calibration unstable.
- **Career arc divergence:** Many TEs jump dramatically Y1→Y2 (+98.5% ESPN estimate), violating the linear extrapolation assumption implicit in Ridge regression.

**Likely diagnoses (to be confirmed by Phase 12 artifacts):**
- Calibration drift in the receiving-TD-driven tail (most likely)
- Insufficient route-share/role features (the model likely relies on prior-year PPG which conflates volume and TD luck)
- Pool heterogeneity from archetype mixing

**What TE alignment data is actually free via nflverse:**
Direct per-player slot/inline alignment data is NOT freely available at scale — that is a paid FTN tier feature. Available free proxies:
- **Route participation rate:** routes run / team dropbacks — derivable from `load_pfr_advstats(stat_type="rec")`
- **Yards Per Route Run (YPRR)** and **Targets Per Route Run (TPRR):** same PFR advanced stats source
- **aDOT:** `load_nextgen_stats(stat_type="receiving")` as `avg_intended_air_yards`
- **2-TE-formation rate:** from `load_participation()` `offense_personnel` strings (e.g., "1 RB, 2 TE, 2 WR") — strong proxy for TE-friendly scheme
- **Snap share and route share:** `load_snap_counts()` from PFR (2012+)

**Coverage constraint:** FTN charting data (most precise) is consistently available only from 2022 onward, which severely restricts the historical training window for walk-forward validation. This is the data availability risk for Phase 13.

**Recommended Phase 13 experiment:** Cluster TEs by archetype using k-means on (route participation, aDOT, slot rate proxy, YAC rate), then either (a) fit one model with archetype indicator features, or (b) fit separate models per archetype. Validate via walk-forward before any promotion claim.

**TE status in Phase 12:** Remains EXPERIMENTAL. The Phase 12 Model Card for TE must explicitly state the failure mode(s) with quantitative evidence from the first operational run.

### 6.2 RB Feature Expansion

**Predictive validity ranking (from PFF/Sharp Football/nfeloapp):**

| Metric | Y2Y Correlation | Source | Phase 12 verdict |
|---|---|---|---|
| Weighted Opportunity | **0.95–0.97** | Scott Barrett / PFF 2019 | High priority for Phase 13 |
| High-Value Touches (HVT) | Strong (PPR-specific) | PFF | Phase 13 candidate |
| Targets / route participation | Strong (PPR-specific) | PFR advanced stats | Phase 13 candidate |
| RYOE (Rushing Yards Over Expected) | ~0 (coin flip) | nfeloapp analysis | **Reject** |
| Yards Before Contact / Evaded Tackles | Modest | PFR advanced stats | Phase 13 secondary |

**High-Value Touches defined:** receptions and carries inside the 10-yard line — the highest-leverage PPG drivers in PPR. The same players who dominate red-zone touches also dominate target share in passing situations, making HVT a natural complement to Weighted Opportunity.

**RYOE rejection is firm:** Year-over-year correlation is essentially zero per nfeloapp. RYOE reflects offensive line blocking scheme and situational box counts, not isolated runner talent. Do not add it as a primary predictor. May be appropriate as a context flag (risk/upside) only after seeing backtest evidence.

**Recommended action for Phase 12:** Publish RB model's current calibration and subgroup weaknesses in the Model Card, making the later feature-expansion test measurable. Any feature change waits for Phase 13 baseline gates. Document RYOE rejection explicitly so it is not relitigated.

### 6.3 WR and QB

**WR:** Passed gates. Non-feature improvements appropriate in Phase 12 or 13: calibration plot publication, subgroup analysis by age/target share/aDOT, documentation of earmarked features (YPRR Y2Y stability, target share growth) for future backtest consideration.

**QB:** Passed gates. **Do not touch the model.** In Superflex, QB calibration errors translate to ~2× starter slot impact. Rushing-points share as an additional feature has reasonable evidence but must go through a gate-passing backtest before any training change.

---

## 7. Trust Surface and Model Reporting

### 7.1 Model Cards (Mitchell et al., 2018 Schema)

Each active position should receive a Model Card with all 9 sections. TE gets a card too, explicitly documenting its failure. The 9 sections:

1. **Model Details** — Engine version, training window, features list, hyperparameters (Ridge alpha).
2. **Intended Use** — Dynasty trade decision support for Superflex PPR. Explicitly: not for redraft start/sit; not for keeper cap decisions without manager review.
3. **Factors** — Position, age, sample size, draft capital.
4. **Metrics** — RMSE, Spearman ρ, Kendall τ-b, calibration ECE, market-comparison Brier-style.
5. **Evaluation Data** — Walk-forward folds 2018–2023 (+ 2024 if extended), breakdown by year.
6. **Training Data** — Same.
7. **Quantitative Analyses** — Subgroup performance (age buckets, draft capital buckets).
8. **Ethical Considerations** — Decision aid only; market-overlay separation; TE outputs are not decision-grade.
9. **Caveats and Recommendations** — TE EXPERIMENTAL until promotion; rookie-year DVS provisional; do not extrapolate beyond t+2 without continuous-age decay layer.

### 7.2 What the Trust Surface Should Expose After Artifacts Exist

- Gate pass/fail by position with raw metrics (not just booleans)
- Calibration plot (JSON data or embedded HTML)
- Rank correlation per fold (Spearman ρ, Kendall τ-b)
- Market disagreement examples: predictions where model and KTC/FC differ by more than a threshold, with realized outcome where available
- Confidence bands on each prediction (bootstrap CIs from the harness)
- **TE:** explicit "EXPERIMENTAL — do not use for trade decisions" banner with documented failure mode

### 7.3 What the Trust Surface Must Not Imply

The Trust Surface should expose evidence, not manufacture confidence. It must never imply:

- TE is decision-grade or comparable to QB/RB/WR outputs.
- `dynasty_value_score` is trustworthy before calibration and bridge validation.
- Market data is ground truth (KTC/FC are overlays, not labels).
- A model disagreement with market is alpha before G4 evidence.
- Promotion gates are guarantees rather than statistical thresholds.
- A hard age cliff is encoded as a model input.

### 7.4 The Counter-Argument Protocol

The system architecture prohibits emitting vague deterministic verdicts ("Bust," "Sell Now"). Every strong valuation recommendation must be accompanied by a Red Team case — a steel-manned, data-driven argument against the model's own conclusion. If the algorithm generates a high valuation for an incoming RB based on elite draft capital and collegiate production, the Counter-Argument field must automatically surface opposing contextual data: the drafting team's run-blocking grade, or the mathematical probability of a committee backfield.

This protocol preserves the mandated 65:35 Quantitative-to-Qualitative discipline: falsifiable metrics anchor the primary score, while high-fidelity qualitative context is visible to the end user for final decisions. The system never issues verdicts; it presents evidence.

---

## 8. nflverse / nfl_data_py Data Access Reference

| Endpoint | What it gives | Coverage | Relevant to |
|---|---|---|---|
| `load_pbp` / `import_pbp_data` | Play-by-play + EPA/WPA | 1999+ | Feature engineering base |
| `load_player_stats` / `import_weekly_data` | Weekly box-score stats | 1999+ | Realized PPG, training labels |
| `load_nextgen_stats` / `import_ngs_data` | NGS rushing/receiving/passing | Receiving/passing 2016+; rushing 2018+ | RYOE, aDOT, CPOE |
| `load_participation` | Formations, personnel, defenders | NGS 2016–2022; FTN 2023+ | TE personnel/formation proxies |
| `load_ftn_charting` | Manual charts (motion, PA, screen) | **2022+ only** | TE/RB context features |
| `load_pfr_advstats` | Routes, YPRR components, broken tackles | 2018+ | Route participation, YPRR for TE/WR/RB |
| `load_snap_counts` | Weekly snap counts | 2012+ | Role share |
| `load_ff_opportunity` (ffopportunity) | xgboost expected fantasy points | 2006+ (model 2006–2020) | Denoised volume feature, external benchmark |
| `load_combine`, `load_draft_picks` | Combine + draft capital | Long history | Engine A inputs (already in use) |
| `nflreadpy` | Python port of nflreadr (Polars-based) | 2025-ongoing | Preferred over `nfl_data_py` going forward |

**2024–2026 key notes:**
- **nflreadpy** is the official Python port of nflreadr (Polars-based); preferred by nflverse maintainers over `nfl_data_py` for new work.
- **FTN charting via nflverse** (since 2022, CC-BY-SA 4.0). Note: true per-player alignment (inline vs. slot) is a paid FTN tier; nflverse gets a useful subset.
- **Participation data source switched** mid-2023 from NFL NGS (which stopped mid-season) to FTN. 2023+ participation only updates after postseason — important for any in-season pipeline.
- **ffopportunity v1.0.0** stable. Strong candidate as a feature source for Phase 13 (post-validation).

---

## 9. Recommended Phase 12 Scope

### In-Scope

**Act 1 — Operational Backtest Run:**
1. Run operational backtest end-to-end for QB, RB, WR (active) and TE (experimental, flagged)
2. Extend walk-forward window to include 2024 fold if 2025 outcomes are settled
3. Generate full artifact suite: per-fold prediction logs, calibration data, rank metrics, market-comparison ledger, G1–G4 gate evaluations, subgroup slices
4. Model Cards for all 4 positions (Mitchell schema, all 9 sections)
5. Trust Surface v2: publish model cards, calibration plots as JSON, gate pass/fail with raw metrics, "EXPERIMENTAL" banner for TE
6. Divergence ledger v0: for each player, store `(engine_b_pred, ktc_value, fc_value, realized_t1_t2_when_known)` — passive storage only, not yet a signal
7. `ARTIFACTS.md`: every artifact, location, schema, and which gate it informs

**Act 2 — DVS Pipeline (conditional — requires Act 1 artifact review and spec approval):**

The following tasks are ready to spec but are NOT committed Phase 12 scope. They become in-scope only after David reviews Act 1 artifacts and approves the DVS spec. The design detail is in Section 5.

- Isotonic calibration pipeline: map Engine A and Engine B outputs to calibrated positional percentile using walk-forward fold calibration surface
- Exponential scaling function: convert calibrated percentiles to 0–10,000 cardinal scale, VORP-anchored against QB24/RB36/WR48/TE12 baselines
- Prospect bridge v0 (Approach 1): regression from Engine A composite to realized avg_ppg_t1_t2 for historical rookie classes; provisional flag in Trust Surface
- PVO integration: `dynasty_value_score` → `within_position_percentile` for QB/RB/WR; TE stays null
- DVS gate: unified valuation board passes NDCG@24 against pre-season market consensus snapshot

### Out of Scope (Defer)

- TE remodeling / archetype clustering (Phase 13, after diagnosis artifacts confirm failure mode)
- New features for any position: RYOE rejected; weighted opportunity requires baseline gate
- Platt/isotonic recalibration as a deployed inference layer (Phase 13 after calibration diagnostics)
- G4 divergence-as-signal logic (Phase 13 after divergence ledger has data)
- Live external API calls in the backtest/calibration environment
- Market feature leakage of any kind (KTC, DP, ADP into training labels or features)

### Acceptance Criteria (Act 1 — Committed)

- ≥1 operational backtest run with complete artifact set for all 4 positions on disk
- All 4 positions have populated Model Cards with all 9 Mitchell sections
- TE Model Card explicitly states failure mode(s) with quantitative evidence
- Trust Surface route returns model cards + gate status with no 500s; integration test passes
- Spearman ρ, RMSE, ECE, market-comparison metrics persisted per-fold and pooled
- Divergence ledger schema designed and ≥1 season populated
- Code review confirms zero market data path into training labels or features
- `ARTIFACTS.md` documents every artifact, its location, and which gate it informs

*Act 2 acceptance criteria (DVS) will be defined in the approved DVS spec.*

### Test Strategy

- **Unit:** Schema validation for every artifact; model card serializer; calibration report transforms
- **Integration:** End-to-end CLI invocation produces all artifacts deterministically (fixed seed)
- **Golden tests:** Lock 2018–2023 baseline metrics so future regressions are detected
- **Property tests:** Percentile ranks in [0,1]; gate booleans match raw threshold comparisons
- **Contract tests:** Trust Surface v2 route shape; missing-artifact and stale-artifact states

### Data Dependencies

- nfl_data_py / nflreadpy endpoints already in use
- KTC/FC/DP overlay snapshots at each fold boundary year (needed for market comparison ledger): DP available via github.com/dynastyprocess/data, no API key required
- No new external data sources required for Phase 12

---

## 10. Open Questions for Domain Governance

1. **DVS scope gate:** Act 1 (artifacts) is committed. Act 2 (DVS implementation) requires David's explicit approval after reviewing Act 1 artifacts. Should the Phase 12 spec include a formal review checkpoint, or should Act 2 be scoped as a separate Phase 13 from the start?
2. **Trust Surface visibility:** Should it be externally visible (shared with leaguemates) or owner-only? Affects model card phrasing and TE "experimental" banner severity.
3. **Walk-forward extension to 2024 fold:** In-scope for Phase 12 or its own mini-step?
4. **DVS v0 feature flag:** Ship within-position percentile only under a flag, or hold entirely until full cross-position DVS is ready?
5. **Divergence ledger:** Passive storage in Phase 12, or does it need a CLI report to be useful?
6. **Engine A Phase 12 touch:** Does Engine A need any update, or is it stable enough to leave for Phase 14+?
7. **Market snapshot policy:** Daily, weekly, or at fold boundaries only? Versioned?
8. **TE remodel scope gate:** If Phase 12 diagnosis surfaces archetype heterogeneity as the primary failure, is a multi-model approach within Engine B acceptable, or is a single model per position non-negotiable?
9. **Exponential decay coefficient:** Dynamically tuned per validation fold from League Pulse transaction data, or hardcoded to a 12-team Superflex baseline? Should be resolved before implementing the scaling function.
10. **DVS target scale preference:** When cross-position DVS ships, which format is preferred — 0–100 (percentile-flavored), 0–10,000 (KTC-familiar), or positional rank + percentile annotation with no cardinal score yet?
11. **Draft pick valuation:** The 80% present-value discount is industry standard (DP). Does this adequately capture the projected historical strength of highly touted future classes, or should it be a tunable parameter? Should pick valuation be included in DVS design or held for a dedicated Trade Lab phase?

---

## 11. Source Appendix

- **KeepTradeCut** — keeptradecut.com, keeptradecut.com/frequently-asked-questions, keeptradecut.com/about/tight-end-premium. K/T/C crowdsourcing; 0–9999 integer; separate SF/1QB databases; algorithmic TEP overlay.
- **FantasyCalc** — fantasycalc.com/about, fantasycalc.com/dynasty-research. Convex optimization on ~2M trades; 14-day half-life; MSTD volatility metric; SF QB adjustment.
- **DynastyProcess** — github.com/dynastyprocess (data, apps-calculator); dynastyprocess.com/values. ECR-derived; LOESS 1QB→SF; GAM rookie pick blend (Perfect Knowledge + Hit Rate); `ffscrapr::dp_values()`.
- **Mitchell et al., 2018** — arxiv.org/abs/1810.03993. "Model Cards for Model Reporting" — canonical 9-section schema.
- **Apex Fantasy Leagues** — apexfantasyleagues.com/peak-age-nfl-running-back/ (2025). RB peak age 25.46; 76.5% of 15+ PPR seasons in 22–26 window.
- **4for4** — 4for4.com/2025/preseason/production-curves-positional-breakouts-prime-years-and-falloffs-age (2025). Multi-position curves; RB peaks ~26.
- **ESPN** — espn.com/fantasy/football/story/_/id/37933720 (2023). 25.2% PPG decline RB age-28→29; TE sophomore +98.5% jump.
- **nfelo / nfeloapp** — nfeloapp.com/analysis/over-expected-explained. RYOE Y2Y correlation effectively zero.
- **PFF (Weighted Opportunity)** — Scott Barrett, 2019. Weighted opportunity 0.95–0.97 PPR points Y2Y correlation.
- **DraftExpert Pro** — draftexpertpro.com/guides/superflex-auction-values. Empirical Superflex QB premium ~2.5–3×.
- **nflverse R docs** — nflreadr.nflverse.com. Coverage windows, FTN transition notes, participation dictionary.
- **nflreadpy** — github.com/nflverse/nflreadpy. Polars-based Python port; preferred going forward.
- **ffopportunity** — ffopportunity.ffverse.com. xgboost expected fantasy points; 2006–2020 training; CC-BY-SA license.
- **FTN Data** — ftnfantasy.com/stats/sports-data. Charting data licensing; per-player alignment is paid tier.
- **Footballguys / BrainyBallers** — TE breakout research. 85% of TE breakouts by Year 3 (Footballguys); college breakout age weak signal (BrainyBallers 20-year study).
- **FantasyLife (Dwain McFarland)** — fantasylife.com. TE pre-prime 21–22 at 72% of max; prime 23–27.
- **nflverse FTN charting** — nflreadr.nflverse.com/reference/load_ftn_charting.html. Charting 2022+; CC-BY-SA 4.0.

*All sources accessed or verified May 2026. Where evidence is weak or contested (RYOE Y2Y stability, college breakout age), this is flagged in-line.*

---

## 12. Bottom Line

Both research reports agree on the long-term destination: Dynasty Genius needs a trustworthy valuation layer that can explain itself. They disagree on the immediate next move.

The correct Phase 12 is not the unified score yet. The correct Phase 12 is the evidence layer that makes the unified score safe to build. The governance-safe sequence is fixed: generate evidence → expose evidence → diagnose weak points → then calibrate into a unified value score.

Phase 12 committed scope is clear: generate operational backtest artifacts, expose them through Trust Surface v2 with model cards, and publish the TE failure diagnosis. DVS implementation is design-ready (see Section 5) but requires a formal review gate after Act 1 artifacts exist before any implementation begins. Whether DVS lands in Phase 12 Act 2 or Phase 13 is a decision for David after seeing the artifact diagnostics — not a decision this research brief makes. The TE remodel and RB feature expansion belong to Phase 13 in either case.
