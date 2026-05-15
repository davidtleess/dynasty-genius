# Directive: Architect the Dynasty Genius Backtest Harness (Phases 10/11)

**Context:** You are tasked with implementing the "Trust Layer" for the Dynasty Genius platform. This Backtest Harness will mathematically validate whether the predictive models (Engine B v2) and their "Divergence Signals" (against the FantasyCalc market) generate actual, tradeable *Alpha*. It serves as the immutable gatekeeper for promoting an algorithm to `DECISION_GRADE`.

We are abandoning static train/test splits. NFL data is non-stationary, and our datasets are extremely small (e.g., ~160 QBs). The harness must utilize an **expanding-window (walk-forward) methodology** and rely on robust non-parametric statistics.

Your implementation must strictly adhere to the following four architectural pillars, synthesized from our foundational research:

### Pillar 1: Temporal Validity via Walk-Forward Validation
Static splits inherently leak future macroeconomic trends (e.g., the rise of two-high safeties). 
*   **Methodology:** Implement a 4-fold expanding window. 
    *   Fold 1: Train 2018-2020 -> Test 2021
    *   Fold 2: Train 2018-2021 -> Test 2022
    *   Fold 3: Train 2018-2022 -> Test 2023
    *   Fold 4: Train 2018-2023 -> Test 2024
*   **Strict Isolation:** Feature engineering (especially lagged features and mean imputations) must be executed *dynamically* at the boundary of each fold. The model (Ridge regression) must be instantiated, trained from scratch, evaluated, and destroyed at each fold.
*   **Stability Test:** Implement the **Harvey-Leybourne-Newbold (HLN) corrected Diebold-Mariano test**. You must compare the model's RMSE against a naive benchmark (e.g., player's Y_t = player's Y_t-1). To pass, the p-value must be < 0.05, proving the model's outperformance is not random variance.

### Pillar 2: Market vs. Model Rank Superiority
Global rank correlations (like Spearman) over-penalize errors at the bottom of the roster where dynasty value is negligible. Because our dataset is small and prone to injury outliers, squared-deviation metrics are too fragile.
*   **Global Metric:** Implement **Kendall's Tau-b** (to account for tied tiers). This provides a robust probabilistic measure of pairwise directional agreement between the model's rank and realized PPG.
*   **Top-Tier Metric:** Implement **Normalized Discounted Cumulative Gain (NDCG)** at depths **k=12** (Elite/1st-round startup value) and **k=24** (Starter viability). The model's NDCG must outperform the FantasyCalc preseason market consensus NDCG to satisfy this gate.
*   **Timestamp Discipline:** The market baseline must be a snapshot taken *exactly* prior to week 1 kickoff to avoid look-ahead bias.

### Pillar 3: Divergence Flag Predictive Validity (The Alpha Gate)
When the model flags a player as `model_higher_than_market`, we must prove that the player's value appreciates over the subsequent season.
*   **Test:** Implement the **Mann-Whitney U test**. The treatment group is flagged players; the control group is unflagged players. The outcome variable is the delta in market value (T_1yr - T_0).
*   **Market Beta Adjustment:** You must adjust the outcome variable for positional "Market Beta" (e.g., if the entire RB market depreciates 10%, a flagged RB that depreciates 2% represents an 8% Alpha).
*   **Survivorship Bias:** Exclude players who miss >4 games due to documented injuries from the evaluation fold to prevent stochastic injury noise from failing the algorithm.
*   **Reporting:** Output the "Hit Rate" wrapped in **Bootstrap 95% Confidence Intervals** (10,000 resamples). A point estimate on n=30 is useless; we need bounds.

### Pillar 4: The Artifact & Data Sourcing
*   **Artifact Schema:** Define a comprehensive Pydantic `BacktestResult` schema. It must capture `kendalls_tau`, `ndcg_at_12`, `ndcg_at_24`, `dm_p_value`, `hit_rate_bootstrap_ci95`, and boolean flags for `passed_temporal`, `passed_rank`, `passed_divergence`.
*   **Data Workaround:** Because the FantasyCalc API does not expose historical dates, the harness must be built to ingest static CSV archives (e.g., from `dynastyprocess/data` or community KTC scrapes) for the 2021-2024 evaluations. 

**Execution:** Provide the Pydantic schemas, the Python class structures for the `WalkForwardDriver`, and the exact `scipy.stats` and `sklearn` implementations for the metrics described above.