# Dynasty Genius Backtest Harness — Merged Research Brief (Phases 10/11)

Merged from two independent research reports (May 14, 2026). Where they disagreed, the resolution is documented explicitly.

---

## 0. What This Document Is

This is the research foundation for the Phase 10/11 spec. It is not the spec — that comes after David reviews and approves this synthesis. Nothing in here is implemented yet.

The Backtest Harness has one job: answer whether Engine B v2 has earned the right to drive dynasty decisions, or whether its divergence flags are informed noise. That answer requires three empirical gates, ordered by decision-importance:

1. **Rolling Rank Correlation** — does the model rank players correctly across time? (Kendall's Tau-b, expanding-window holdouts 2021→2024)
2. **Market Rank Superiority** — does the model outperform the FantasyCalc market consensus in identifying valuable players? (NDCG@12/24 vs. market)
3. **Divergence Flag Predictive Validity** — when the model disagrees with the market, does the market eventually correct toward the model? (Mann-Whitney U + bootstrap CIs + Beta adjustment)

---

## 1. The Single Biggest Risk

**FantasyCalc has no historical API.** The public `api.fantasycalc.com/values/current` endpoint returns only the current snapshot. There is no `date` parameter. No historical query is exposed. This is confirmed by direct API documentation review, the FantasyDataPros tutorial, and community developer reports (r/fantasyfootballcoding, r/DynastyFF).

This breaks the cleanest version of Gate 3 (divergence validity) for the 2021–2024 backtest window because that gate requires FantasyCalc values at T₀ *and* at T+6m.

**Resolution — dual track:**

1. **Start snapshotting FantasyCalc daily right now (May 2026).** This is the single highest-leverage one-day engineering task in the entire harness. Storage cost: ~1.5 MB/day, under 1 GB/year. Schema: `fc_snapshots(snapshot_date, league_settings_hash, sleeper_id, value, overall_rank, position_rank, trend_30day)`. Without this, Gate 3 will never have native FC evidence — it will always be proxied.

2. **Use DynastyProcess `values.csv` + community CSV archives as the 2021–2024 backfill proxy.** Two confirmed sources:
   - `github.com/dynastyprocess/data` — open-data dynasty values with commit history going back several years, covering `value_2qb`, `ecr_2qb`, `sleeper_id`. The git commit history can be replayed to reconstruct point-in-time values.
   - Community-maintained CSV dumps of historical KTC and FantasyCalc data (confirmed available via r/DynastyFF; multiple posts link working downloads covering 2020–2025 for both 1QB and SF formats).

3. **Label all 2021–2024 backtest market values** as `market_source: "dp_archive"` or `market_source: "ktc_community_csv"` in the BacktestResult artifact. Never present proxied data as native FC.

4. **Gate 3 earns `DECISION_GRADE` qualification only after ~6 months of native FC snapshots accumulate** (approximately Q4 2026). Gates 1 and 2 can run today without this dependency. This is why the `ACTIVE_B_VALIDATED` sub-state exists (see Section 7).

---

## 2. Rolling Holdout Methodology

### 2.1 Expanding Window (Walk-Forward)

**Use expanding window, not sliding window.** With QB at ~169 total training rows and TE at far fewer, a sliding window that drops old data starves the model of variance. Expanding window accumulates all available history while still respecting time order.

Four folds, strict epoch boundaries at NFL season start:

| Fold | Train | Predict | Approx. Test N (QB) |
|---|---|---|---|
| 1 | 2018–2020 | 2021 | ~24–30 |
| 2 | 2018–2021 | 2022 | ~24–30 |
| 3 | 2018–2022 | 2023 | ~24–30 |
| 4 | 2018–2023 | 2024 | ~24–30 |

**Minimum defensible cohort.** For Kendall's Tau at α=0.05 with 80% power, detecting a real τ ≥ 0.30 requires n ≈ 80; detecting τ ≥ 0.50 requires n ≈ 30. Practically: **QB Kendall from n ≈ 25–30 is directional only, with wide CIs. RB/WR (n ≈ 60–90) are real estimates.** Always report bootstrap 95% CI alongside the point estimate. Never present QB Gate 1 as a hard pass/fail until n ≥ 40.

### 2.2 Temporal Leakage — The Mandatory Checklist

Leakage is the single most common reason static-split numbers collapse on rolling evaluation. Every fold must enforce:

- **Feature window discipline.** All features for prediction year S must be computable from data where `season ≤ S−1`. No exceptions.
- **Lagged features are safe under proper management.** `ppg_t-1`, `ppg_t-2`, `snap_share_t-1` are fine — but when predicting 2022, these lags must be populated from 2021 and 2020 only. Never from the full dataset.
- **Scaling must be fit on the train fold.** StandardScaler (or equivalent) fit on 2018–2021, applied to the 2022 test fold. Fitting a global scaler across all years before the fold boundary is a classic leak.
- **Aggregate features re-computed per fold.** Any league-wide baseline (e.g., average pass rate, positional PPG norm) must be calculated only from the training window. A global baseline computed across 2018–2024 and fed into a 2021 prediction leaks 2022–2024 data.
- **Imputation discipline.** Mean imputation for missing features must use the train-fold mean, not the dataset mean.

### 2.3 Formal Stability Test — Diebold-Mariano with HLN Correction

To formally test whether RMSE is stable across folds (and superior to a naive baseline), use the **Harvey-Leybourne-Newbold corrected Diebold-Mariano test.** The HLN correction is mandatory — the raw DM test over-rejects in small samples (Harvey, Leybourne & Newbold 1997; Döhrn 2018; Coroneo & Iacone 2020).

The naive baseline is: predicted PPG for season S equals actual PPG from season S−1 (prior-year production as the forecast). This is the standard sports analytics naive benchmark.

**Giacomini-White extension validity note.** The Diebold-Mariano test assumes non-nested models. Engine B is nested (it includes lagged PPG as a feature, so it subsumes the naive baseline). The Giacomini-White (2006) extension proves that DM remains asymptotically valid for nested models when model parameters are estimated dynamically at each fold — which is exactly what the refit-per-fold design provides. Document this in the BacktestResult metadata.

**Secondary stability criteria (non-statistical):**
- Flag any fold whose RMSE deviates >25% from the trailing-fold median.
- Flag any fold whose Kendall τ drops below the lower bound of the previous fold's 95% bootstrap CI.
- Maintain a `regime_notes` field in each FoldResult for hand-curated annotations (e.g., "2023: two-high safety prevalence; 2024: kickoff rule change irrelevant to skill PPG").

### 2.4 Published Benchmarks — Reality Check on Current Numbers

Engine B v2 static-split Spearman values (0.69–0.81) are at or above PFF-tier benchmarks and should be treated as **suspicious until validated rolling.** Static splits are inflated by leakage.

Published season-ahead rank correlations from the dynasty/redraft analytics community (RotoViz, FantasyPoints, FantasyPros expert-consensus accuracy reports): **0.40–0.65 for WR/RB, 0.30–0.55 for QB.** A realistic post-rolling Spearman/Kendall target is:

| Position | Realistic Rolling Target |
|---|---|
| QB | Kendall τ 0.35–0.50, Spearman ρ 0.45–0.60 |
| RB | Kendall τ 0.45–0.60, Spearman ρ 0.55–0.70 |
| WR | Kendall τ 0.45–0.60, Spearman ρ 0.55–0.70 |

Any rolling result in the 0.70+ Spearman range should trigger a leakage audit, not celebration.

---

## 3. Statistical Metric Selection

### 3.1 Primary Metric: Kendall's Tau-b (not Spearman)

**Resolution: Kendall's Tau-b is the primary gate metric. Spearman is reported for IC-convention comparability but does not control the gate.**

This resolves the disagreement between the two source reports. The reasoning:

**Why Kendall's Tau-b over Spearman for our context:**
- Spearman computes correlation on rank-transformed data and squares the differences. One injury outlier in a QB fold of n=28 (e.g., a backup QB who starts 10 games, scores far above his preseason rank) creates a massive squared deviation that can collapse the full-fold Spearman score — even if the model ranked all other 27 players correctly.
- Kendall's Tau evaluates pairwise concordance: P(model ranks player A higher than B) vs. P(A actually outscores B). One outlier affects at most (n−1) pairs, not the squared-deviation aggregate.
- Kendall's Tau-b handles tied tiers, which are common in dynasty market rankings where multiple players sit at identical consensus values.
- Kendall's distribution converges to normal faster at small n — p-values are more accurate at n=28 than Spearman's.
- A Kendall vs. Spearman disagreement (e.g., τ=0.42, ρ=0.65) is itself a signal that a small number of extreme observations are driving the ranking — which in dynasty, these are usually injured or breakout outliers. Reporting both surfaces this.

**Why Spearman is still reported:** The quantitative finance Information Coefficient (IC) literature universally uses IC = Spearman correlation between predicted and realized ranks. The IC thresholds (IC ≥ 0.05 = solid, ≥ 0.10 = strong in equities; scaled ~5× for the smaller and less-efficient dynasty cross-section) give a comparability layer. IC literature benchmarks are a useful external reference point.

**Report both. Kendall primary. Spearman as IC-convention secondary.**

### 3.2 Market Comparison: NDCG for the Gate, Precision@k for the UI

**Gate metric: NDCG@12 and NDCG@24 (Normalized Discounted Cumulative Gain).**

Standard precision@k (top-K hit rate) weights a rank-1 error identically to a rank-12 error. In dynasty, that's wrong — correctly identifying the QB1 is exponentially more valuable than correctly identifying QB11. NDCG fixes this with logarithmic discounting: relevance scores decay by log₂(rank+1), so accuracy at the top of the board is heavily rewarded and the long tail contributes marginally.

NDCG procedure:
1. Relevance score = actual realized PPG for the season (continuous graded relevance)
2. DCG = sum of (realized_ppg_i / log₂(predicted_rank_i + 1)) for all players in the evaluation depth
3. IDCG = DCG of the ideal (perfect) ranking — players sorted by actual PPG
4. NDCG = DCG / IDCG, bounded [0, 1]

**Evaluation depths matched to 12-team Superflex roster economics:**
- **NDCG@12** — first-round startup capital tier (QB1–QB12 in Superflex; RB1–12 elite; WR1–12 elite; TE1–12)
- **NDCG@24** — starter-viable assets (full 2-QB leagues fill ~24 QB starts; roughly the boundary of "trade target vs. waiver curiosity")

**Trust Surface UI: Precision@k alongside NDCG.** Precision@k (hit-rate@k = |Top-k_predicted ∩ Top-k_realized| / k) is understandable to a non-coder. Report it on the Trust Surface with Wilson CI on the model-vs-market difference. The gate uses NDCG; the UI communicates in precision@k.

### 3.3 Information Coefficient Framing

Applying quant-finance IC thresholds scaled for dynasty's smaller and less-efficient cross-section:

| IC (Spearman) | Interpretation |
|---|---|
| < 0.30 | Weak — below market value for dynasty |
| 0.30–0.45 | Directional signal — useful but not gate-worthy |
| 0.45–0.60 | Solid — Gate 1 passes if sustained ≥3 of 4 folds |
| 0.60–0.70 | Strong — rare at these sample sizes |
| > 0.70 rolling | Suspicious — audit for leakage before celebrating |

---

## 4. Divergence Flag Predictive Validity (Gate 3)

### 4.1 The Core Hypothesis

When the model flags a player as `model_higher_than_market`, does that player's FantasyCalc dynasty value increase more over the next 6–12 months than comparable non-flagged players? If yes, the divergence flag is productive Alpha. If no, it's informed noise that may entertain but shouldn't drive asset decisions.

### 4.2 Statistical Tests (All Three, In Combination)

**Test 1: Mann-Whitney U (primary significance test)**

Non-parametric — makes no normality assumption on the distribution of value changes, which is right for dynasty (heavy tails, outliers common).

- Treatment group: players flagged as `model_higher_than_market`
- Control group: constructed matched control (see Section 4.4 below)
- Outcome variable: Beta-adjusted forward value change over 6 months and 12 months (see Section 4.3)
- Use `scipy.stats.mannwhitneyu(..., method='exact')` when n_flagged < 20 in any fold

**Test 2: Bootstrap BCa 95% CI (effect size with uncertainty)**

Bootstrap the mean forward-return difference (flagged minus matched control) with bias-corrected and accelerated (BCa) confidence intervals, 5,000 resamples. BCa corrects for skewed sampling distributions — appropriate because value-change distributions in dynasty are right-skewed. Report the point estimate and the full [lower, upper] CI.

**Test 3: Wilson 95% CI on hit-rate (interpretable product metric)**

Binary hit-rate: "did this player's value appreciate more than position-cohort median?" Report as "X% of flagged players beat their position cohort median, CI [lower, upper]." Wilson CI is correct for proportions at small n (normal approximation breaks near 50% and at n < 40).

### 4.3 Market Beta Adjustment

Dynasty fantasy football market values move for reasons unrelated to the model's signal. All WR values may appreciate if WR scarcity increases league-wide. All RB values may depreciate in a run-heavy off-season. Failing to account for this **conflates positional beta with model Alpha**.

Adjustment procedure:
1. Calculate the **position Beta**: mean % change in FantasyCalc value for the entire position group (all players, not just flagged) over the evaluation window.
2. The **model Alpha** for a flagged player = their actual value change minus the position Beta.
3. Gate 3 evaluates the Alpha, not the raw value change.

This isolates whether the flag predicted anything above what the whole position group did.

### 4.4 Matched Control Construction

For each flagged player, the control is the K=3 nearest players (in the same fold) by:
- Position (exact match)
- Age bucket (±2 years)
- Current value tier (±10% of starting FantasyCalc value)
- *Not* flagged as `model_higher_than_market`

Use the matched control's Alpha as the comparison baseline for the Mann-Whitney U test and bootstrap CI. This is more rigorous than "all non-flagged players" because it controls for age and value tier — younger players and cheaper players tend to appreciate more naturally, independent of model signal.

### 4.5 Injury Exclusion Rule

**Remove from the fold evaluation any player who participated in fewer than 4 games due to documented injury.**

A player who the model correctly identifies as undervalued, who then tears an ACL in Week 2, will show negative market-value change. Including them as a flag "failure" introduces survivorship bias — the flag was about talent and opportunity, not ligament durability. This is not signal failure; it is exogenous noise.

Source for injury verification: nflverse `import_injuries()` or nfl_data_py weekly game participation data (verified available 2018+). Document the n_excluded count in DivergenceResult.

### 4.6 Minimum Flagged-Player Pool

Gate 3 requires **n_flagged ≥ 30 pooled across ≥ 2 seasons** for any statistical claim. Below this threshold, the harness must report Gate 3 as `"insufficient_data"`, not `"fail"`. The distinction matters — insufficient data is a forward-looking engineering problem (more snapshots, more folds), not a model failure.

---

## 5. Data Sourcing

### 5.1 nflverse / nfl_data_py (Ground Truth — Confirmed Available)

The canonical source for historical realized PPG. The `nfl_data_py` library exposes:
- `import_seasonal_data(years)` — season aggregates per player, 1999–present
- `import_weekly_data(years)` — game-by-game stats
- `import_ids()` — cross-system ID map: `gsis_id ↔ sleeper_id ↔ mfl_id ↔ pff_id ↔ espn_id ↔ fantasypros_id`

The `import_ids()` map is critical — it's the bridge from nflverse PPG to FantasyCalc's `sleeperId` join key.

Superflex PPR scoring: base PPG columns available (`fantasy_points_ppr`). For the exact league format, apply a custom vectorized formula to raw columns (passing_tds × 4, rushing_tds × 6, receiving_tds × 6, receptions × 1, etc.). This is a few lines of pandas.

### 5.2 FantasyCalc (Market Data — Gap Confirmed, Workaround Confirmed)

**No historical API.** Confirmed by:
- Direct API documentation — no `date` parameter
- FantasyDataPros tutorial article — confirms live-only
- Reddit r/DynastyFF (May 2025 thread): "Why can't we see historical value beyond the last year?" — FC admin confirms they archive old trades for DB performance

**Backfill sources (confirmed exist):**

1. **DynastyProcess `values.csv`** (`github.com/dynastyprocess/data`) — open-data dynasty values with git commit history. Columns include `value_2qb`, `ecr_2qb`, `sleeper_id`. Replay git log to reconstruct point-in-time values. Historically a KTC + FC consensus blend.

2. **Community CSV archives** (r/DynastyFF; multiple confirmed download threads) — separate KTC and FantasyCalc CSV dumps covering 2020–2025, both 1QB and SF formats. These are static files requiring ingestion into a local store.

**Timestamp discipline for pre-season snapshot:** The comparison market rank must be captured from exactly **before the opening kickoff of the target season** — approximately the first Wednesday of September for that year. Pulling a mid-season snapshot (October) introduces severe look-ahead bias; the market will have already absorbed early-season performance data that the model never had.

**Start daily FC snapshotting now (May 2026).** Without this, Gate 3 will permanently rely on proxied data. One cron job, trivial storage, the highest return per engineering hour in the entire harness.

### 5.3 Sleeper (Not a Viable Market Source)

Sleeper does not calculate or expose dynasty trade values. ADP is available but requires complex individual-draft-identifier queries. Not a scalable market baseline source.

### 5.4 Python Stack

| Library | Purpose |
|---|---|
| `nfl_data_py` | Ground truth PPG, player IDs |
| `pandas`, `numpy` | Data manipulation, window slicing, custom scoring |
| `scipy.stats` | `kendalltau`, `spearmanr`, `mannwhitneyu`, `bootstrap` |
| `statsmodels` | HLN-corrected Diebold-Mariano (or manual ~30-line implementation per Harvey et al. 1997) |
| `scikit-learn` | `Ridge`, `TimeSeriesSplit` (guarantees chronological index preservation) |
| `pydantic` v2 | BacktestResult artifact schemas |
| `joblib` | Artifact persistence and hash |

**Do not use Optuna in v1.** Hyperparameter search is over-engineering at 160–390 row cohorts. Hold Ridge α fixed at production v2 values (QB=1000, RB=500, WR=200) and document the constraint. Revisit in v2.

---

## 6. Re-train vs. Frozen Artifact

**Mandate: refit Ridge from scratch at every fold.**

**Why frozen evaluation is invalid:** Engine B v2 was trained on data through 2024. Evaluating it against a 2021 test set means the model has already seen 2022–2024 data for those same players. That is textbook temporal leakage — not a retrospective test, not a generalization test. It will produce optimistic results that prove nothing.

**Why re-training is cheap:** Ridge regression on 160–390 rows with ≤30 features fits in fractional milliseconds. There is no cost argument for avoiding it.

**How:** At each fold boundary, execute the full feature engineering pipeline from a blank state, fit a temporary Ridge instance, predict the test year, evaluate, then discard the temporary model. The harness is testing the **methodology** — not the specific frozen artifact.

**Hold α fixed across folds** at the production v2 values. Re-tuning α per fold via inner time-series CV would require double the data discipline and risks "double-dipping" (the harness appears to tune itself into passing). Document `retrain_mode: "refit_per_fold_fixed_alpha"` in the artifact.

**Pragmatic fallback:** If the full training pipeline is not yet reproducible from source (feature engineering + scaling not re-runnable), the harness may ship in `EXPERIMENTAL` mode evaluating frozen artifacts with explicit `retrain_mode: "frozen_retrospective"` labeling. But this mode **cannot promote to `DECISION_GRADE`** — it can only produce informational output.

---

## 7. Promotion Gates and Grade Levels

### 7.1 The New Grade Level: ACTIVE_B_VALIDATED

The existing grades are: `PRE_MODEL → EXPERIMENTAL → ACTIVE_B → DECISION_GRADE`

Add one sub-state: **`ACTIVE_B_VALIDATED`** — Gates 1 and 2 pass, Gate 3 is deferred pending FC snapshot accumulation. This allows the harness to deliver real signal and reward the work of running Pillars 1 and 2 without requiring the 6-month FC snapshot window to complete before anything meaningful is declared.

`ACTIVE_B_VALIDATED` is not a soft `DECISION_GRADE`. The Trust Surface shows a distinct badge and a specific message: "Model rank validated against market. Divergence-flag forward-return gate pending FC snapshot accumulation — ETA Q4 2026."

### 7.2 Gate Definitions

| Gate | Threshold | Notes |
|---|---|---|
| **G1 — Kendall Rank Correlation** | Mean τ across 4 folds ≥ 0.40 (RB/WR) or ≥ 0.30 (QB), **with bootstrap 95% CI lower bound ≥ 0.20** in ≥ 3 of 4 folds | QB lower bound reflects honest small-n reality |
| **G2 — RMSE Stability (DM test)** | Max per-fold RMSE deviation from median ≤ 25%; HLN-corrected DM p-value vs. naive baseline ≤ 0.10 | Both criteria must pass |
| **G3 — Market Rank Superiority (NDCG)** | Model NDCG@24 ≥ Market NDCG@24 in ≥ 3 of 4 folds; OR model NDCG@12 ≥ market in all 4 folds | "Demonstrably not worse than market" is the minimum; strict superiority in ≥1 fold is required for DECISION_GRADE |
| **G4 — Divergence Validity** | Mann-Whitney p ≤ 0.10 AND bootstrap CI on Beta-adjusted forward-return diff excludes 0 AND hit-rate Wilson CI lower bound > 50%, on n ≥ 30 flagged players pooled across ≥ 2 seasons | `"deferred"` is valid if n_flagged < 30 |
| **TE exception** | TE cannot reach DECISION_GRADE in v1 — flagged `FALLBACK_V1` until per-fold n_test ≥ 40 | Separate diagnostic track |

**G1 + G2 + G3 = `ACTIVE_B_VALIDATED`**  
**G1 + G2 + G3 + G4 = `DECISION_GRADE`**

### 7.3 Rationale for Threshold Calibration

The thresholds in Section 7.2 are anchored to:
- IC literature ("solid ≥ 0.05, strong ≥ 0.10" in equities), scaled ~4–5× for dynasty's smaller and less-efficient cross-section
- The rolling-holdout reality check (Section 2.4): static-split numbers of 0.69–0.81 Spearman will not survive rolling without leakage
- Wilson CI accuracy at n=25–30 (QB fold) — thresholds respect the actual distribution of plausible estimates at these sample sizes

---

## 8. BacktestResult Artifact Schema

Versioned JSON artifact, written to `runs/{model_version}/{position}/{run_id}/backtest_result.json`. The Trust Surface reads this JSON exclusively — no recomputation on the read path.

```
BacktestResult:
  schema_version: str             # "1.0.0"
  run_id: UUID
  run_date: datetime
  git_sha: str | null
  model_version: str              # "engine_b_v2"
  model_artifact_hash: str        # sha256 of the .pkl used
  position: Literal["QB","RB","WR","TE"]
  ridge_alpha: float              # fixed production value
  retrain_mode: Literal["refit_per_fold_fixed_alpha","frozen_retrospective"]

  folds: List[FoldResult]

FoldResult:
  train_years: List[int]
  test_year: int
  n_train: int
  n_test: int
  n_excluded_injury: int          # players removed per injury rule
  rmse: float
  mae: float
  kendall_tau: float              # PRIMARY metric
  kendall_tau_ci95: Tuple[float, float]  # bootstrap BCa
  spearman_rho: float             # IC-convention secondary
  spearman_rho_ci95: Tuple[float, float]
  rank_ic: float                  # alias for spearman_rho for quant audience
  ndcg_at_12: float               # model
  ndcg_at_12_market: float
  ndcg_at_24: float               # model
  ndcg_at_24_market: float
  precision_at_k: Dict[int, PrecisionKResult]   # {12: ..., 24: ..., 36: ...}
  calibration_by_decile: List[float]            # mean residual per predicted-rank decile
  regime_notes: str | null

PrecisionKResult:
  k: int
  model_hit_rate: float
  market_hit_rate: float
  diff_wilson_ci95: Tuple[float, float]

# Aggregate across folds:
rmse_stability:
  mean: float
  cv: float                       # coefficient of variation across folds
  max_deviation_pct: float
  dm_hln_pvalue: float | null     # vs. naive baseline
  dm_method: str                  # "harvey_leybourne_newbold_1997"

# Gate 3 (may be null or "deferred"):
divergence_validity: DivergenceResult | null

DivergenceResult:
  n_flagged: int
  n_excluded_injury: int
  n_matched_controls_per_flag: int  # K=3
  forward_horizon_days: int         # 180 or 365
  position_beta: float              # mean position-group % value change
  mean_alpha_flagged: float         # Beta-adjusted
  mean_alpha_control: float
  diff_bootstrap_bca_ci95: Tuple[float, float]
  mann_whitney_u: float
  mann_whitney_p: float
  mann_whitney_method: str          # "exact" if n_flagged < 20
  hit_rate: float
  hit_rate_wilson_ci95: Tuple[float, float]

market_source: Literal["fc_native","dp_archive","ktc_community_csv"]
market_snapshot_date: date          # first Wednesday of September for that year

# Promotion gate evaluation:
promotion_gate:
  g1_rank_correlation_pass: bool
  g2_rmse_stability_pass: bool
  g3_market_superiority_pass: bool
  g4_divergence_validity_pass: bool | Literal["deferred","insufficient_data"]
  overall_grade: Literal["PRE_MODEL","EXPERIMENTAL","ACTIVE_B","ACTIVE_B_VALIDATED","DECISION_GRADE"]
  gate_version: str                 # "1.0"
  promotion_justification: str      # human-readable sentence
```

---

## 9. Harness Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  nflverse historical PPG (cached parquet, 2018–2024)        │
│         +                                                   │
│  dp_archive / ktc_community_csv (local SQLite or parquet)   │
│         │                                                   │
│         ▼                                                   │
│  Feature Builder                                            │
│  (re-runs per fold; train-fold-only scaling; strict         │
│   temporal window enforcement per Section 2.2 checklist)    │
│         │                                                   │
│         ▼                                                   │
│  Walk-Forward Driver — 4 folds × 3 positions (QB/RB/WR)     │
│         │                                                   │
│         ▼                                                   │
│  Ridge.fit() per fold (fixed α; discard after evaluation)   │
│         │                                                   │
│         ▼                                                   │
│  Metric Computer                                            │
│  (scipy Kendall τ + bootstrap, Spearman, NDCG, precision@k, │
│   HLN-DM stability test, RMSE/MAE)                         │
│         │                                                   │
│         ▼                                                   │
│  Market join (sleeper_id; pre-season snapshot timestamp)    │
│  → NDCG@12/24 model vs. market                              │
│         │                                                   │
│         ▼                                                   │
│  Divergence validator                                       │
│  (injury exclusion → matched controls → Beta adjustment     │
│   → Mann-Whitney U + BCa bootstrap + Wilson hit-rate)       │
│         │                                                   │
│         ▼                                                   │
│  Promotion gate evaluator → grade assignment                │
│         │                                                   │
│         ▼                                                   │
│  BacktestResult.json                                        │
│  runs/{model_version}/{position}/{run_id}/                  │
│         │                                                   │
│         ▼                                                   │
│  Trust Surface (read-only FastAPI route + UI)               │
│  reads JSON only, never recomputes                          │
└─────────────────────────────────────────────────────────────┘
```

The harness is a **separate batch CLI command** (`dg backtest --position WR --model engine_b_v2`), not on the request path. It writes immutable artifacts. The Trust Surface is a read-only consumer.

---

## 10. Trust Surface UX

The Trust Surface is consumed by a non-coder PM. Every design decision must favor honest communication of uncertainty over clean-looking confidence.

**Layout (top to bottom):**

**(a) Trust badge.** One colored chip per position:
- `DECISION_GRADE` — green
- `ACTIVE_B_VALIDATED` — teal (new — distinct from ACTIVE_B)
- `ACTIVE_B` — yellow
- `EXPERIMENTAL` — orange
- `PRE_MODEL` — gray

One sentence below the badge: *"WR model: Kendall τ 0.51 [0.41–0.61], beats market by 9pp on NDCG@24. Trust for WR1–WR36 rankings; treat WR60+ as experimental."*

**(b) Three gate cards.**
- Card 1 — *Rolling Rank Correlation*: Kendall τ per fold with bootstrap CI bars, Spearman as secondary. Sparkline across 4 folds.
- Card 2 — *Market Superiority*: NDCG@24 model vs. market per fold; precision@k side-by-side bars with Wilson CI on the diff.
- Card 3 — *Divergence Validity*: Beta-adjusted forward-return Alpha with bootstrap CI. If deferred: gray card, "Pending FC snapshots — ETA Q4 2026."

**(c) Cohort-conditional trust panel.** Break the WR cohort into quartiles by predicted rank (WR1–9 / WR10–18 / WR19–27 / WR28–36 / WR37+) and show Kendall τ within each bucket. This is the most operationally important UX element. Engine B v2 almost certainly degrades fast in the tail — communicate this honestly. Frame as: *"Trust this model for ranking starters; do not rely on it for deep cuts."*

**(d) Calibration panel (expandable).** (i) Predicted vs. actual PPG scatter with 45° line. (ii) Calibration-by-decile bar chart showing mean residual per predicted-rank decile. These are diagnostic tools for the model builder, not primary PM-facing content.

**(e) Divergence flag confidence overlay.** When the flag `model_higher_than_market` appears on a player, an inline pill: *"backtest-validated (n=42, 3 seasons), hit-rate 67% [Wilson 55–78%]."* If the backtest sample for that position-cohort is below n=20: *"backtest underpowered for this position-tier — treat as low-confidence signal."*

**Anti-patterns to actively avoid:**
- Single Spearman point estimate without CI — invites over-trust on noise
- Aggregate single-number accuracy across positions — hides TE failure and QB weakness
- Hiding the deferred Gate 3 status behind a clean badge
- R² in headline position — lay readers conflate with %; Kendall τ and hit-rate are more honest
- "Equity curve" cumulative plots — implies this is a tradeable strategy

---

## 11. Minimum Viable Harness (v1 — ~2 sprints)

**Must-haves for v1:**
- Walk-forward driver, 4 folds, refit-per-fold Ridge with fixed α
- Feature Builder with strict fold-level temporal isolation (Section 2.2 checklist)
- Per-fold Kendall τ + BCa bootstrap CI, Spearman ρ, RMSE, MAE
- NDCG@12/24 model vs. market; precision@k with Wilson CI on diff
- HLN-corrected Diebold-Mariano stability test
- BacktestResult Pydantic schema + JSON artifact persistence with artifact hash and git_sha
- Trust Surface: trust badge, three gate cards, cohort-conditional table
- FantasyCalc daily snapshot cron started (so Gate 4 accumulates evidence)
- Gate evaluation: g1/g2/g3 → `ACTIVE_B_VALIDATED` if all pass; g4 → `"deferred"` until FC snapshots accumulate

**Defer to v2:**
- Native Gate 4 (divergence forward-return gate) — requires ~6 months of FC snapshots OR completion of the DP/KTC community CSV ingestion pipeline
- Per-fold Ridge α re-tuning via inner time-series CV
- Full matched-control construction (v1 may use simpler position-cohort residualization)
- TE re-engineering — separate research track
- NDCG at additional depths

**v1 cannot claim `DECISION_GRADE`.** The harness ships with `ACTIVE_B_VALIDATED` as the best possible outcome of v1. This makes `DECISION_GRADE` promotion ceremonious and well-evidenced rather than premature.

---

## 12. Prior Art

- **`nflverse/nfl_data_py`** — Python interface to NFL data; canonical PPG + player ID source
- **`dynastyprocess/data`** — open-data dynasty values with `value_2qb`, `ecr_2qb`, `sleeper_id`; commit history is the 2021–2024 backfill source
- **`ffscrapr`** (R) — reference for `dp_values()` schema; Python can pull same CSVs directly
- **`jrioross/dynasty_fantasy_football_ktc`, `ees4/KeepTradeCut-Scraper`** — working KTC historical scrapers
- **r/DynastyFF CSV archives** — community-maintained KTC and FantasyCalc CSV dumps (2020–2025, 1QB and SF)
- **Harvey, Leybourne & Newbold (1997)**, "Testing the Equality of Prediction Mean Squared Errors" — the mandatory small-sample DM correction
- **Giacomini & White (2006)**, "Tests of Conditional Predictive Ability" — DM validity extension for nested models with dynamic parameter estimation
- **Xu, Hou, Hung, Zou (2013)** (arXiv:1011.2009) — canonical comparison of Spearman and Kendall at small n
- **Zhang et al. (2020)** (arXiv:2010.08601) — IC threshold methodology adapted here
- **Croux & Dehon (2010)**, "Influence functions of Spearman and Kendall" — robustness argument for τ
- **Davis et al. (2024)**, "Methodology and evaluation in sports analytics," *Machine Learning* (Springer) — subject-level cross-validation discipline; preventing player-season leakage across folds
- **Evidently AI NDCG explainer** and **Shaped.ai NDCG guide** — NDCG methodology and implementation reference
- **FantasyDataPros, "FantasyCalc API Intro"** — confirms no historical date parameter

---

## 13. Open Questions for David Before Spec

1. **Gate 3 timeline.** Are we comfortable declaring `ACTIVE_B_VALIDATED` (Gates 1–3 only) as the v1 target? Or does David want to hold the full `DECISION_GRADE` gate — which means waiting for FC snapshot accumulation?

2. **DP archive ingestion.** DynastyProcess git history replay requires engineering work. Is that in scope for Phase 10/11, or should v1 simply label Gate 4 as `"deferred"` from the start?

3. **Kendall's Tau gate thresholds.** The thresholds in Section 7.2 are research-informed estimates. Once the first rolling fold runs, the actual numbers will tell us if they're calibrated correctly. Are we comfortable with them as written, or does David want to set them after seeing the first fold's output?

4. **Trust Surface: separate page or inline on dashboard?** This research assumes a standalone Trust Surface page. If it's inline on an existing dashboard route, the layout changes.

5. **TE.** Should Phase 10/11 include a TE diagnostic sub-track, or is TE parked as `FALLBACK_V1` for the entire phase?
