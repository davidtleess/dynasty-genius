# Dynasty Genius Backtest Harness — Research Report (Phases 10/11)

## 1. Executive Summary

The Backtest Harness should be built around three measurable gates, ordered by decision-importance:

1. **Rolling rank-IC (Spearman ρ between predicted PPG rank and realized PPG rank), computed on expanding-window holdouts 2021→2024**, with **bootstrap 95% confidence intervals** and a Harvey-Leybourne-Newbold–corrected Diebold-Mariano test for RMSE stability across windows.
2. **Top-K hit rate vs. the FantasyCalc market benchmark** at position-appropriate k (QB12, RB24, WR36, TE12), with Wilson confidence intervals on the difference.
3. **Divergence-flag forward-return validity** — a Mann-Whitney U test plus bootstrap CI on the difference in 6- and 12-month FantasyCalc value change between `model_higher_than_market` flagged players and matched controls, residualized against position-cohort drift.

**The single biggest risk surfaced by this research is the FantasyCalc historical-snapshot gap.** The public `api.fantasycalc.com/values/current` endpoint returns only the *current* league-tuned snapshot (plus a `trend30Day` field) and has **no documented `date` parameter** — no historical query is exposed. This breaks the cleanest version of the divergence-flag gate (Pillar 3) because it requires FantasyCalc values at $T_0$ *and* at $T_{+6m}$ for the 2021–2024 backtest window. The recommended fallback is dual-track: (a) **begin daily/weekly snapshotting now** to a versioned local store, and (b) use **DynastyProcess `values.csv` history plus community KTC scrapes** as a retroactive proxy for 2021–2024 market values, with the harness explicitly labeling the divergence gate "provisional, KTC-proxied" until ~6 months of native FantasyCalc snapshots accumulate. A single-source market gate is acceptable; a backfilled approximation of FantasyCalc using KTC is acceptable for v1 if the source is disclosed in the BacktestResult artifact.

Secondary risks: sample sizes are below the rule-of-thumb threshold for stable Spearman estimates at the tails (e.g., n≈30–40 QBs per season), so all reported metrics must carry CIs and be conditioned on cohort (e.g., "QB1–QB18" vs. "QB tail").

---

## 2. Rolling Holdout Methodology

**Design: expanding-window walk-forward** — the standard approach in time-series ML where future data never leaks into past training and the window grows each fold. With four folds (train 2018–2020 → 2021; +2021 → 2022; +2022 → 2023; +2023 → 2024), the harness produces four independent generalization estimates and a stability profile.

**Minimum credible cohort sizes.** For Spearman ρ at α=0.05 with 80% power, detecting a "real" ρ ≥ 0.50 vs. null ρ = 0 requires n ≈ 26; detecting ρ ≥ 0.30 vs. 0 requires n ≈ 84 (standard power-curve results, e.g., Hilaris sample-size charts for rank correlations). Practically: **trust QB Spearman from n ≥ 30 only as a directional signal with wide CIs; trust RB/WR (n ≈ 60–90 per season) as a real estimate.** Always report bootstrap 95% CI (1,000–5,000 resamples) alongside the point estimate.

**Temporal leakage hazards.** In the existing v2 features, the lagged signals (`ppg_t-1`, `ppg_t-2`, `snap_share_t-1`) are safe under proper window management *only if* the lag horizon is strictly before the prediction season. Specifically, when predicting season $S$:
- All features for the prediction set must be computable from data with `season ≤ S − 1`.
- Aggregate features (career averages, age-cohort norms, league-wide pass rates) must be **re-computed at each fold using only the training-window data**, never the full dataset. Computing a single league-wide pass-rate baseline across 2018–2024 and feeding it into a 2021 prediction is a classic leak.
- Position-level scaling (e.g., StandardScaler on PPG) must be **fit only on the train fold** and applied to the test fold.
- The Ridge α (currently 1000/500/200 by position) was chosen on a static split — at each rolling fold this hyperparameter should either be re-tuned via inner time-series CV on the train window or fixed across folds and disclosed as a constraint. **Recommendation: hold α fixed in v1 to avoid the "double-dipping" trap where α-tuning per fold inflates apparent generalization; revisit in v2.**

**Structural-break / drift detection.** Three layered defenses:
1. **RMSE-stability test**: Compute per-fold RMSE, then run the **Harvey-Leybourne-Newbold–corrected Diebold-Mariano test** between the model's loss-differential series and the market's. The HLN correction is mandatory at these sample sizes — the raw DM test over-rejects in small samples (well-documented by Harvey, Leybourne, Newbold 1997; Döhrn 2018; Coroneo & Iacone 2020).
2. **Numeric threshold**: flag any fold whose RMSE deviates >20% from the trailing-fold median, and any fold whose Spearman drops below the lower bound of the previous fold's 95% bootstrap CI.
3. **Domain-aware drift annotation**: hand-curate a `regime_notes` field in BacktestResult — e.g., 2021 = "high-passing era", 2023 = "two-high safety / lower-passing", 2024 = "kickoff rule change irrelevant to skill PPG". Visual inspection of the RMSE-over-folds line chart is the most useful single artifact; a formal CUSUM is overkill at n=4 folds.

**Published Spearman benchmarks.** Public dynasty/redraft writeups (RotoViz, FantasyPoints, FantasyPros expert-consensus accuracy reports) generally land season-ahead Spearman rank correlations in the **0.40–0.65** range for WRs and RBs and **0.30–0.55** for QBs; PFF's own internal projection accuracy claims R² in the 0.30–0.50 band per position. Engine B v2's static-split Spearman (0.69–0.81) is therefore *suspicious* until validated rolling — those numbers are at or above PFF-tier benchmarks and are almost certainly inflated by the static split's leakage. **A realistic post-rolling-holdout Spearman target is 0.55–0.70 for RB/WR and 0.45–0.60 for QB.**

---

## 3. Statistical Deep-Dive

**Spearman ρ vs. Kendall τ.** At n ≈ 30–90 (our cohort sizes), the empirical literature (Xu et al. 2013; Croux & Dehon 2010) shows Spearman has *slightly higher statistical efficiency for detecting weak correlations* while Kendall is more robust to outliers and has a cleaner probabilistic interpretation (P(concordant) − P(discordant)). **Recommendation: report both, treat Spearman as primary** (it's what the literature and quant-finance IC convention use), and use Kendall as a robustness check. Disagreement between them (e.g., Spearman = 0.65, Kendall = 0.30) is itself a finding — it implies a few extreme observations are driving the rank correlation, which matters because in dynasty those are usually injured or rookie outliers.

**Information Coefficient framing.** IC = Spearman correlation between predicted ranks and realized ranks. The quant-equities literature (PyQuant News; Bajaj AMC; Zhang et al. 2020 on arXiv; FE Training) is converged on these thresholds: **IC ≈ 0.02–0.05 = weak; 0.05–0.10 = solid; 0.10–0.15 = strong; >0.15 = rare and usually a red flag for overfit.** Fantasy football is a *much smaller cross-section per period* (30–90 vs. 500–3000 stocks) and a *less efficient market*, so dynasty ICs should plausibly run higher than equities. A reasonable translation: **dynasty rank-IC ≥ 0.30 sustained across ≥3 of 4 rolling windows is the "alpha exists" threshold; ≥ 0.50 is strong evidence; > 0.70 should be treated with suspicion as potential leakage.**

**Top-K hit rate.** Use position-aware k matched to a 12-team Superflex roster: **QB k=12 (Superflex demand), RB k=24, WR k=36, TE k=12.** Definition: hit-rate@k = |Top-k_predicted ∩ Top-k_realized| / k. This is the metric a fantasy manager actually consumes. **Report hit-rate@k for both Engine B and the FantasyCalc market**, then the difference with a Wilson-score 95% CI on the difference of proportions. NDCG is overkill at these sizes and harder to communicate; precision@k is the right metric.

**Divergence-flag predictive validity.** Three statistical tools, used in combination:
1. **Hit-rate with Wilson 95% CI** on the binary question "did flagged players gain market value > position-cohort median?". Wilson is the right interval at n ≈ 30–50 because the normal approximation breaks down near 50% and at small n.
2. **Bootstrap 95% CI (BCa, 5,000 resamples)** on mean forward-return difference (flagged minus matched control), residualized against position-cohort mean movement to remove general dynasty-market beta.
3. **Mann-Whitney U** as a non-parametric significance check; report exact p-value (`scipy.stats.mannwhitneyu(..., method='exact')` when n_flag < 20).

The matched-control construction is critical: for each flagged player, pick the K=3 nearest players by (position, age bucket, current value tier) who were *not* flagged, and use them to compute the cohort baseline forward return. This isolates the model's flag from market-wide drift.

**Information Coefficient vs. RMSE.** For dynasty *valuation*, IC/rank-IC is the right primary metric — fantasy managers consume rankings, not point projections. RMSE is a useful secondary diagnostic for absolute calibration (Is the model systematically over/under-projecting QBs?) and for the DM stability test, but **rank-IC should be the headline number on the Trust Surface.**

---

## 4. Data Sourcing Report

**nflverse / `nfl_data_py` — confirmed.** The package exposes `import_weekly_data(years)` (game-by-game player stats) and `import_seasonal_data(years)` (season aggregates), covering 2018 through current season. Fantasy points for PPR scoring are pre-computed (`fantasy_points_ppr` column); for the half-PPR variant common in Superflex leagues, weekly raw stats permit re-scoring. **The repository also publishes `import_ids()` which maps `gsis_id ↔ sleeper_id ↔ mfl_id ↔ pff_id ↔ espn_id ↔ fantasypros_id`, which is essential for joining nflverse PPG to FantasyCalc's `sleeperId` join key.** This is the canonical source — no realistic substitute.

**FantasyCalc historical — NOT available via API.** Direct probing of `api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1` confirms the endpoint works and returns the league-tuned snapshot including `sleeperId`, `value`, `overallRank`, `positionRank`, `trend30Day`, `redraftValue`, and `maybeMovingStandardDeviation`. **No `date` or `timestamp` parameter is exposed in public documentation, the FantasyDataPros tutorial article, or community usage.** The `trend30Day` field is the only built-in historical signal — and 30 days is too short for divergence validation.

**Recommended fallback (researcher's recommendation, explicitly delegated):**

1. **Start snapshotting FantasyCalc daily *now* (May 2026)** to a versioned table (`fc_snapshots(snapshot_date, league_settings_hash, sleeper_id, value, overall_rank, position_rank, trend_30day)`). Storage cost is trivial (~1.5 MB/day, <1 GB/year). This is the highest-leverage one-day engineering task in the whole harness.
2. **Use DynastyProcess `values.csv` for backfilled 2021–2025 dynasty values** (https://github.com/dynastyprocess/data/tree/master/files; columns include `value_1qb`, `value_2qb`, `ecr_1qb`, `ecr_2qb`, `sleeper_id`). The DP values are themselves a blend (KTC + FantasyCalc consensus historically), and the repo has commit history going back several years that can be replayed to reconstruct point-in-time values.
3. **Acknowledge in the BacktestResult `market_source` field** that 2021–2024 historical market values are KTC/DP-proxied, not native FantasyCalc, with a `market_source: "dp_archive"` vs. `"fc_native"` enum.
4. **Defer the divergence gate's `DECISION_GRADE` qualification by ~6 months** for divergence predictive-validity only. The rolling rank-IC and rank-superiority gates (Pillars 1 & 2) can run today without this dependency.

**KTC scraping (alternative).** The KTC dynasty rankings page exposes per-player history (e.g., the `jrioross/dynasty_fantasy_football_ktc` GitHub repo, `ees4/KeepTradeCut-Scraper`, and the `seh363` Colab notebook all demonstrate working selenium-based scrapers). KTC is more permissive than FantasyCalc historically — per-player pages contain a value history sparkline that is scrapeable. Trade-off: KTC is a *crowdsourced ranking exercise*, not real trades, while FantasyCalc is *imputed from actual league trades*. They measure different markets. For our purpose (model-vs-market check), either is defensible, but the harness must be consistent within a fold.

**Sleeper.** Sleeper's API exposes ADP and roster data but **does not publish historical dynasty trade values**. Not a viable market source.

**Python stack.** `nfl_data_py` for stats; `pandas` + `numpy`; `scipy.stats` for `spearmanr`, `kendalltau`, `mannwhitneyu`, `bootstrap`; `statsmodels` for HLN-corrected DM (or a manual implementation following Harvey et al. 1997, ~30 lines); `scikit-learn` for `Ridge` + `KFold`/`TimeSeriesSplit`; `joblib` for hashing/persistence; `pydantic` v2 for artifact schemas; **`optuna` is *not* recommended for v1** (over-engineering at this sample size).

---

## 5. BacktestResult Artifact Schema

Recommended Pydantic schema, written to `runs/{model_version}/{position}/{run_id}/backtest_result.json`:

```
BacktestResult:
  schema_version: str            # "1.0.0"
  run_id: UUID
  run_date: datetime
  git_sha: str | null
  model_version: str             # e.g. "engine_b_v2"
  model_artifact_hash: str       # sha256 of the .pkl
  position: Literal["QB","RB","WR","TE"]
  ridge_alpha: float
  retrain_mode: Literal["frozen","refit_per_fold"]
  
  folds: List[FoldResult]        # one per holdout year
  
  # Per-fold:
  FoldResult:
    train_years: List[int]
    test_year: int
    n_train: int
    n_test: int
    rmse: float
    mae: float
    spearman_rho: float
    spearman_ci95: Tuple[float, float]   # bootstrap
    kendall_tau: float
    rank_ic: float                        # alias for Spearman, for quant audience
    top_k: Dict[int, TopKResult]          # {12: ..., 24: ..., 36: ...}
    calibration_by_decile: List[float]    # mean residual per predicted-rank decile
    regime_notes: str | null
  
  TopKResult:
    k: int
    model_hit_rate: float
    market_hit_rate: float
    diff_wilson_ci95: Tuple[float, float]
  
  # Aggregate:
  rmse_stability: StabilityResult
    StabilityResult:
      mean: float
      cv: float                         # coefficient of variation across folds
      max_deviation_pct: float
      dm_hln_pvalue: float | null       # vs. market baseline
  
  divergence_validity: DivergenceResult | null
    DivergenceResult:
      n_flagged: int
      forward_horizon_days: int          # 180 or 365
      mean_forward_return_flag: float
      mean_forward_return_control: float
      diff_bootstrap_ci95: Tuple[float, float]
      mann_whitney_u: float
      mann_whitney_p: float
      hit_rate: float
      hit_rate_wilson_ci95: Tuple[float, float]
  
  market_source: Literal["fc_native","dp_archive","ktc_scrape"]
  market_snapshot_date: date
  
  promotion_gate: GateResult
    GateResult:
      rank_ic_pass: bool
      rmse_stability_pass: bool
      top_k_superiority_pass: bool
      divergence_validity_pass: bool | "deferred"
      overall_grade: Literal["EXPERIMENTAL","ACTIVE_B","DECISION_GRADE"]
      gate_version: str                  # "1.0"
```

Hash the artifact itself (`artifact_sha256`) and store alongside. The Trust Surface UI reads only this JSON — never recomputes.

---

## 6. Re-train vs. Frozen Artifact Recommendation

**Recommendation: refit Ridge from scratch at every fold.** Justification:

1. **Scientific correctness.** A "frozen v2 evaluated on past seasons" is a *retrospective* test, not a *generalization* test, because v2 was trained on data including some of those past seasons. Evaluating v2 (trained on 2018–2024) on 2021 is not a real holdout. The HARD-CONSTRAINT-4 requirement of acknowledging sample-size limits implies we cannot let a leaky retrospective pass as a generalization claim.
2. **Cheap on Ridge.** Ridge regression on 160–390 rows with ≤30 features fits in milliseconds. Re-fitting four times is trivial. Compare to a transformer where this would be a real cost.
3. **Reproducibility risk is manageable.** Yes, this requires the full training pipeline (feature engineering, scaling, α selection) to be reproducible from source. Given the Pydantic-schema discipline already in place, this is a 1-week mini-sprint, not a 1-month rewrite. The harness should require it before claiming `DECISION_GRADE`.
4. **Hold α fixed** at the production v2 values (1000/500/200) to avoid double-dipping. Document this constraint in `ridge_alpha` and `retrain_mode: "refit_per_fold_fixed_alpha"`.

**Tradeoff acknowledged:** If the mini-sprint to make training reproducible is blocked, the harness can ship in `EXPERIMENTAL` mode evaluating the frozen artifact and clearly labeling itself "retrospective, not generalization." But it cannot promote anything to `DECISION_GRADE` in that mode.

---

## 7. Trust Surface UX

The Trust Surface is a single page (or one position-tab per QB/RB/WR/TE) consumed by a non-coder PM. Visual prior art that translates well: Evidently AI's regression-performance dashboard, Arize AI's drift/cohort breakdowns, and quantitative finance backtest UIs like QuantConnect's tearsheets. Anti-patterns to actively avoid: portfolio-style "equity curves" implying compounding, single big "accuracy %" numbers without CIs, and reliability-curve charts that PMs misread as ROC curves.

**Layout, top-to-bottom:**

**(a) Top-line trust badge.** A single colored chip per position: `DECISION_GRADE` (green), `ACTIVE_B` (yellow), `EXPERIMENTAL` (orange), `PRE_MODEL` (gray). Underneath, one sentence: *"WR model: rank-IC 0.62 [0.51–0.71], beats market by 8.3pp on Top-36 hit-rate. Trust for WR1–WR36 rankings; avoid for WR60+."*

**(b) The three gates as horizontal cards.** Each card shows pass/fail icon, headline number with CI, and a sparkline across the 4 rolling folds.
- Card 1 — *Rolling Rank-IC*: spearman_rho per fold, bootstrap CI bars
- Card 2 — *Market Superiority*: hit-rate@k vs. FC market, both bars, Wilson CI on the diff
- Card 3 — *Divergence Validity*: forward-return delta with bootstrap CI; if deferred, shows a gray "pending FC snapshots, ETA Q4 2026"

**(c) Cohort-conditional trust panel.** A small table breaking the WR cohort into quartiles by *predicted rank* (WR1–9 / WR10–18 / WR19–27 / WR28–36 / WR37+) showing Spearman within each bucket. This is the single most important UX element for honest model use. The Engine B v2 numbers very likely look great for the top two buckets and degrade fast in the tail — communicate this. Frame as: *"Trust this model for ranking starters; do not trust it for waiver-wire deep cuts."*

**(d) Calibration diagnostics, expandable.** A 2-up of (i) predicted-vs-actual PPG scatter with 45° line, (ii) calibration-by-decile bar chart showing residual per predicted-rank decile. A reliability curve is *not* useful here (it's a classification tool). The rank-rank plot (predicted rank vs. realized rank, scatter) is the most intuitive single visual for a non-coder.

**(e) Drill-down: divergence flags annotated with confidence.** When David sees a flag like `model_higher_than_market` on a player, the UI appends an inline pill: *"backtest-validated (n=42 across 3 seasons), hit-rate 67% [Wilson 55–78%]"*. If the backtest sample for that flag's position-cohort is too small (n<20), the pill says *"backtest underpowered, treat as low-confidence"*. This is the operationally important UX: it converts a 5-class taxonomy into a 5-class taxonomy *plus* a per-instance confidence overlay.

**Anti-patterns to avoid:**
- Showing a single Spearman point estimate without CI (encourages over-trust on noise).
- Aggregating across all positions into one number (hides TE failure).
- Hiding the deferred-divergence-gate status behind a clean green badge.
- Showing R² in headline position (lay readers conflate it with %; rank-IC + hit-rate are more interpretable).
- "Equity curve" style cumulative plots that suggest the model is a tradeable strategy.

---

## 8. Promotion Gate Definition (ACTIVE_B → DECISION_GRADE)

The user proposed:
> Spearman > 0.70 across ≥3 of 4 windows, AND Model Top-K hit rate > Market Top-K hit rate by ≥5pp, AND divergence-flag forward-return hit-rate > 60% with Wilson CI lower bound > 50%, AND no RMSE degradation > 20%.

**Critique:** The 0.70 Spearman bar is *too high* — it implicitly assumes the static-split numbers hold up rolling, which the leakage analysis above suggests they will not. The 5pp Top-K margin and 60% divergence hit-rate are reasonable but need CI-aware framing.

**Revised gate (recommended):**

| Gate | Threshold |
|---|---|
| **G1 — Rank-IC (Spearman)** | Mean across 4 folds ≥ 0.55 (RB/WR) or ≥ 0.45 (QB), with **bootstrap 95% CI lower bound ≥ 0.30** in ≥ 3 of 4 folds. |
| **G2 — RMSE stability** | Max per-fold deviation from median ≤ 25%; HLN-corrected Diebold-Mariano p-value vs. market baseline ≤ 0.10. |
| **G3 — Top-K superiority** | Model hit-rate@k − Market hit-rate@k ≥ 0 with **Wilson 95% CI lower bound ≥ -0.05** in ≥ 3 of 4 folds (i.e., "demonstrably not worse than market"); strict superiority (lower bound > 0) in at least 1 fold. |
| **G4 — Divergence validity** | Mann-Whitney p ≤ 0.10 AND bootstrap CI on forward-return diff excludes 0, on n ≥ 30 flagged players pooled across ≥ 2 seasons. |
| **TE exception** | TE cannot reach DECISION_GRADE in v1 — flagged separately as `FALLBACK_V1` until per-fold n ≥ 40. |

Rationale: thresholds are anchored to the IC literature ("solid ≥ 0.05, strong ≥ 0.10" in equities, scaled up ~5× for the smaller and less-efficient fantasy cross-section) and to standard practice for Wilson CIs on proportions at our sample sizes.

---

## 9. Harness Architecture

```
┌────────────────────────────────────────────────────────────┐
│  PVO (SQLite) ──── nflverse historical (cached parquet)    │
│       │                  │                                  │
│       ▼                  ▼                                  │
│  Feature Builder (re-runs per fold; train-fold-only scaling)│
│       │                                                     │
│       ▼                                                     │
│  Walk-Forward Driver  ──── 4 folds × position               │
│       │                                                     │
│       ▼                                                     │
│  Ridge .fit() per fold → fold_predictions table             │
│       │                                                     │
│       ▼                                                     │
│  Metric Computer (scipy.stats, bootstrap, HLN-DM)           │
│       │                                                     │
│       ▼                                                     │
│  FantasyCalc post-hoc join (sleeper_id; fc_snapshots OR     │
│        dp_archive proxy) ── computes divergence flags       │
│        at simulated $T_0$, then forward returns at $T_+6m$  │
│       │                                                     │
│       ▼                                                     │
│  BacktestResult.json ─── runs/{model_version}/{position}/   │
│        │                       {run_id}/                    │
│        │   ─── promotion_gate evaluated → grade             │
│        ▼                                                    │
│  Trust Surface UI (FastAPI route reads JSON, no recompute)  │
└────────────────────────────────────────────────────────────┘
```

The Backtest Harness is a **separate batch job** (CLI command `dg backtest --position WR --model engine_b_v2`), not part of the request-path. It writes immutable artifacts. The Pydantic schema lives in the same package as the existing PVO schemas. Trust Surface is a read-only FastAPI route + a small React/Jinja UI consuming the JSON.

---

## 10. Minimum Viable Harness (v1)

**Must-haves (v1, ~2 sprints):**
- Walk-forward driver, 4 folds, refit-per-fold Ridge with fixed α
- Per-fold Spearman ρ + bootstrap CI, Kendall τ, RMSE, MAE
- Top-K hit rate at the recommended k values, Wilson CI on diff vs. market
- BacktestResult Pydantic schema + JSON artifact persistence with model_artifact_hash and git_sha
- Trust Surface read-only page with the top-line badge, three gate cards, and the cohort-conditional table
- FantasyCalc daily snapshot cron started (so the divergence gate accumulates evidence)

**Defer to v2:**
- Native divergence-flag forward-return gate (requires accumulated FC snapshots OR the DP/KTC proxy ingestion)
- Per-fold Ridge α re-tuning via inner time-series CV
- Optuna or any HPO
- TE-specific re-engineering
- Causal-style matched-control construction for divergence (v1 uses position-cohort residualization, which is good enough)

**v1 explicitly *cannot* claim `DECISION_GRADE`** without G4 evidence — the harness should be capable of granting `ACTIVE_B_VALIDATED` (a sub-state of ACTIVE_B meaning Pillars 1 & 2 pass but Pillar 3 is deferred). This makes the eventual `DECISION_GRADE` promotion ceremonious and well-evidenced rather than premature.

---

## 11. Relevant Prior Art

- **`nflverse/nfl_data_py`** (github.com/nflverse/nfl_data_py) — the canonical Python interface to NFL play-by-play, weekly, seasonal, ID-mapping data. Authoritative source for realized PPG 2018+.
- **`dynastyprocess/data`** (github.com/dynastyprocess/data) — open-data dynasty values (`values.csv`, `values-players.csv`, `values-picks.csv`) with 1QB/2QB/Superflex ECR + value; commit history is the backfill source for 2021–2024 if FantasyCalc historical proves unrecoverable.
- **`ffscrapr`** (R, ffscrapr.ffverse.com) — reference for the `dp_values()` / `dp_playerids()` schemas; Python users can pull the same CSVs directly.
- **`jrioross/dynasty_fantasy_football_ktc`**, **`ees4/KeepTradeCut-Scraper`**, **`seh363/Dynasty-Lifecycle-Using-KeepTradeCut`** — working community KTC scrapers including per-player historical value extraction (uses Wayback Machine for older devy/rookie values).
- **FantasyDataPros, "FantasyCalc API Intro"** (fantasydatapros.com/fantasyfootball/blog/fantasycalc/1) — author-provided documentation of the live FantasyCalc endpoint and its fields; confirms no historical parameter is exposed.
- **Harvey, Leybourne & Newbold (1997), "Testing the Equality of Prediction Mean Squared Errors,"** *Int. J. Forecasting* 13(2): 281–291 — the small-sample correction to Diebold-Mariano that any honest forecast-comparison test at our n must use.
- **Diebold & Mariano (1995), "Comparing Predictive Accuracy,"** *J. Business & Econ. Statistics* 13: 253–263.
- **Xu, Hou, Hung, Zou (2013), "Comparison of Spearman's Rho and Kendall's Tau in Normal and Contaminated Normal Models"** (arXiv:1011.2009) — the canonical small-sample efficiency/robustness comparison.
- **Zhang et al. (2020), "Information Coefficient as a Performance Measure of Stock Selection Models"** (arXiv:2010.08601) — the quant-finance IC threshold and monitoring methodology this report adapts.
- **Croux & Dehon (2010), "Influence functions of the Spearman and Kendall correlation measures,"** Statistical Methods & Applications — robustness argument for τ.
- **Evidently AI** (evidentlyai.com) and **Arize AI** UI conventions for ML monitoring dashboards — visual prior art for the Trust Surface, especially the cohort breakdown and calibration-by-decile patterns.
- **Davis, De Bock, Van Haaren et al. (2024), "Methodology and evaluation in sports analytics,"** *Machine Learning* (Springer) — subject-level cross-validation discipline directly relevant to keeping a player's seasons from leaking across folds.

The harness, designed against these sources and constraints, will produce versioned, citable evidence that a position-specific Engine B has — or has not — earned the right to drive dynasty decisions.