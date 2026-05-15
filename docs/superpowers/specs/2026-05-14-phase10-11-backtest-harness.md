---
document: Phase 10/11 — Backtest Harness Specification
version: 1.0.0
status: PENDING_DAVID_APPROVAL
date: 2026-05-14
author: Claude Code
governance_read:
  - docs/governance/02-agent-operating-loop.md v1.0.0
  - docs/governance/00-product-constitution.md v1.0.0
  - docs/governance/01-north-star-architecture.md v1.0.0
phase_sequence_position: 11
prior_phase: "Phase 9.5 — Prospect Identity Join (PR #26, merged 845de98)"
---

# Phase 10/11 — Backtest Harness Specification

## 0. Why This Phase Exists

The product constitution is explicit: *"Backtesting is a trust layer, not optional QA. Dynasty Genius must show whether its model beats or usefully diverges from the market over time. Model credibility is earned through validation and backtest visibility, not attractive UI."*

Engine B v2 currently holds `model_grade = ACTIVE_B` and all surfaces show `decision_supported = False`. The Backtest Harness is the work that earns the right to advance. It answers three questions:

1. Does Engine B rank players correctly across time — not just on a static split?
2. Does Engine B's ranking outperform the FantasyCalc market consensus on the players that matter?
3. When the divergence engine says `model_higher_than_market`, does the market eventually correct?

Until those questions are answered with evidence, the divergence flags are informed noise.

---

## 1. Scope

### 1.1 In Scope — v1

- `WalkForwardDriver`: 4-fold expanding-window evaluation of Engine B v2 (QB, RB, WR)
- Per-fold metrics: Kendall τ-b (primary), Spearman ρ (secondary), RMSE, MAE, NDCG@12/24, Precision@k
- HLN-corrected Diebold-Mariano stability test vs. naive baseline
- Market snapshot store: SQLite at `app/data/fc_snapshots.db`; community CSV archive ingestion
- Daily FantasyCalc snapshot cron: `scripts/snapshot_fantasycalc.py`
- `BacktestResult` Pydantic schema and JSON artifact persistence
- Promotion gate evaluator → `ACTIVE_B_VALIDATED` when G1+G2+G3 pass
- Trust Surface route: `GET /trust-surface/{position}` — read-only JSON
- Full TDD test coverage: unit tests + contract tests

### 1.2 Deferred to v2

- Gate 4 (Divergence Validity / G4): Mann-Whitney U + BCa bootstrap on flag forward-return — requires ~6 months of native FC snapshots. Gate logic is implemented; evaluation is deferred.
- `DECISION_GRADE` promotion — requires Gate 4 evidence
- TE backtest — parked as `FALLBACK_V1`; per-fold n_test too small and TE fails engine gate
- Per-fold Ridge α re-tuning via inner time-series CV (double-dipping risk at small n)
- Trust Surface frontend (HTML/React) — frontend is last per constitution
- nfl_data_py import to refresh the CSV — spec assumes the existing `app/data/training/engine_b_features_v2.csv` is the realized-PPG source

### 1.3 Hard Constraints (Non-Negotiable)

- No market data enters Engine B training features at any fold. The HLN-DM test uses naive baseline (prior PPG), never market value.
- Feature engineering must be recomputed at every fold boundary. No global scaling or aggregate features computed across all years.
- Ridge α is held fixed at production v2 values (QB=1000.0, RB=500.0, WR=200.0) across all folds.
- All BacktestResult artifacts are immutable once written. The Trust Surface route reads JSON only — no recomputation on the read path.
- `NOISE_BAND=0.10` remains locked. Do not touch until mid-July 2026.

---

## 2. Data Architecture

### 2.1 Realized PPG Source

**File:** `app/data/training/engine_b_features_v2.csv`

The existing CSV contains `avg_ppg_t1_t2` (2-year average PPG outcome) for all `training_eligible = True` rows. As of May 2026:
- `feature_season` values: 2018–2023 are fully `training_eligible = True`
- `feature_season = 2024` is `training_eligible = False` (2025+2026 seasons not yet in CSV)

The harness reads this CSV directly. It does not call `nfl_data_py` in v1.

### 2.2 Fold Definitions

The folds are defined by `feature_season`, not by calendar year. The market comparison snapshot corresponds to the start of the first outcome season (T+1).

| Fold | Train: feature_season | Test: feature_season | Outcome seasons | Market snapshot date | Approx. test N (QB/RB/WR) |
|---|---|---|---|---|---|
| 1 | 2018–2019 | 2020 | 2021 + 2022 avg PPG | ~Sep 8, 2021 | 43 / 98 / 160 |
| 2 | 2018–2020 | 2021 | 2022 + 2023 avg PPG | ~Sep 7, 2022 | 46 / 98 / 153 |
| 3 | 2018–2021 | 2022 | 2023 + 2024 avg PPG | ~Sep 7, 2023 | 46 / 96 / 147 |
| 4 | 2018–2022 | 2023 | 2024 + 2025 avg PPG | ~Sep 5, 2024 | 49 / 90 / 153 |

**Why T+1 for the market snapshot:** The model produces a ranking using features from season T. The market snapshot at the start of T+1 represents what the consensus believed before the prediction window opened. Pulling a mid-season T+1 snapshot introduces look-ahead bias.

### 2.3 Market Snapshot Store

**File:** `app/data/fc_snapshots.db` (SQLite, gitignored — add to `.gitignore`)

Schema:
```sql
CREATE TABLE IF NOT EXISTS fc_snapshots (
    snapshot_date TEXT NOT NULL,           -- ISO date "2021-09-08"
    league_settings_hash TEXT NOT NULL,    -- SHA256 of the URL query string
    sleeper_id TEXT NOT NULL,
    value INTEGER NOT NULL,
    overall_rank INTEGER,
    position_rank INTEGER,
    position TEXT,
    trend_30day INTEGER,
    source TEXT NOT NULL,                  -- "fc_native" | "dp_archive" | "ktc_community_csv"
    inserted_at TEXT NOT NULL,             -- ISO datetime
    PRIMARY KEY (snapshot_date, league_settings_hash, sleeper_id)
);
CREATE INDEX IF NOT EXISTS idx_fc_snapshots_date ON fc_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_fc_snapshots_sleeper ON fc_snapshots(sleeper_id, snapshot_date);
```

**Community CSV archive ingestion** (v1 backfill path):
- Source: community CSV dumps covering 2020–2025 (FantasyCalc and KTC, SF format)
- Ingest script: `scripts/ingest_market_archive.py --csv <path> --source ktc_community_csv --date <YYYY-MM-DD>`
- The script maps CSV columns to the store schema and sets `source = "ktc_community_csv"` or `"dp_archive"`

**Daily native snapshot** (forward path — start immediately):
- Script: `scripts/snapshot_fantasycalc.py`
- URL: `https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1`
- Run: daily, any time between midnight and 6 AM ET
- Writes to `fc_snapshots.db` with `source = "fc_native"` and `snapshot_date = today's date`
- On API failure: log error and exit non-zero; do NOT write partial rows

---

## 3. Module Architecture

```
src/dynasty_genius/eval/
    __init__.py
    backtest_artifact.py       ← Pydantic schemas (BacktestResult, FoldResult, etc.)
    backtest_metrics.py        ← Pure statistical functions (Kendall, NDCG, DM, etc.)
    backtest_harness.py        ← WalkForwardDriver class
    market_snapshot_store.py   ← SQLite read/write wrapper

scripts/
    run_backtest.py            ← CLI: python scripts/run_backtest.py --position WR
    snapshot_fantasycalc.py    ← Daily cron: python scripts/snapshot_fantasycalc.py
    ingest_market_archive.py   ← One-time CSV ingestion

app/api/routes/trust_surface.py   ← GET /trust-surface/{position}

app/data/
    backtest/
        runs/{run_id}/
            backtest_result_QB.json
            backtest_result_RB.json
            backtest_result_WR.json
    fc_snapshots.db            ← gitignored

tests/
    test_backtest_metrics.py
    test_backtest_harness.py
    test_market_snapshot_store.py
    contract/
        test_backtest_result_schema.py
```

---

## 4. Pydantic Schemas (`backtest_artifact.py`)

All models use Pydantic v2 (`from pydantic import BaseModel`).

```python
from __future__ import annotations
from datetime import date, datetime
from typing import Dict, List, Literal, Optional, Tuple
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class TopKResult(BaseModel):
    k: int
    model_hit_rate: float
    market_hit_rate: float
    diff_wilson_ci95: Tuple[float, float]


class FoldResult(BaseModel):
    fold_index: int                          # 1–4
    train_years: List[int]                   # e.g. [2018, 2019]
    test_year: int                           # feature_season of test rows
    outcome_seasons: List[int]               # e.g. [2021, 2022]
    n_train: int
    n_test: int
    n_excluded_injury: int = 0               # Phase 10/11 v1: always 0 (no games data yet)

    # Rank correlation
    kendall_tau: float
    kendall_tau_bca_ci95: Tuple[float, float]  # BCa bootstrap
    spearman_rho: float
    spearman_rho_bca_ci95: Tuple[float, float]
    rank_ic: float                            # alias for spearman_rho; IC-convention label

    # Error metrics
    rmse: float
    mae: float

    # Market comparison (None if market data unavailable for this fold)
    ndcg_at_12_model: Optional[float] = None
    ndcg_at_12_market: Optional[float] = None
    ndcg_at_24_model: Optional[float] = None
    ndcg_at_24_market: Optional[float] = None
    precision_at_k: Optional[Dict[int, TopKResult]] = None  # {12: ..., 24: ..., 36: ...}

    # Calibration
    calibration_by_decile: Optional[List[float]] = None  # mean residual per decile

    regime_notes: Optional[str] = None


class StabilityResult(BaseModel):
    rmse_per_fold: List[float]               # length 4
    rmse_mean: float
    rmse_cv: float                           # coefficient of variation
    rmse_max_deviation_pct: float
    dm_hln_statistic: Optional[float] = None
    dm_hln_pvalue: Optional[float] = None
    dm_method: str = "harvey_leybourne_newbold_1997"
    dm_passes: Optional[bool] = None         # p <= 0.10


class DivergenceResult(BaseModel):
    """Gate 4. Populated only when sufficient FC snapshots exist."""
    n_flagged: int
    n_excluded_injury: int
    n_matched_controls_per_flag: int         # K=3
    forward_horizon_days: int                # 180 or 365
    position_beta: float
    mean_alpha_flagged: float
    mean_alpha_control: float
    diff_bca_ci95: Tuple[float, float]
    mann_whitney_u: float
    mann_whitney_p: float
    mann_whitney_method: str                 # "exact" if n_flagged < 20, else "asymptotic"
    hit_rate: float
    hit_rate_wilson_ci95: Tuple[float, float]


class GateResult(BaseModel):
    g1_rank_correlation_pass: bool
    g2_rmse_stability_pass: bool
    g3_market_superiority_pass: bool
    g4_divergence_validity_pass: Literal[True, False, "deferred", "insufficient_data"]
    overall_grade: Literal[
        "PRE_MODEL", "EXPERIMENTAL", "ACTIVE_B",
        "ACTIVE_B_VALIDATED", "DECISION_GRADE"
    ]
    gate_version: str = "1.0"
    promotion_justification: str


class BacktestResult(BaseModel):
    schema_version: str = "1.0.0"
    run_id: UUID = Field(default_factory=uuid4)
    run_date: datetime
    git_sha: Optional[str] = None
    model_version: str                        # "engine_b_v2"
    model_artifact_hash: str                  # SHA-256 of the .pkl used
    position: Literal["QB", "RB", "WR", "TE"]
    ridge_alpha: float
    retrain_mode: Literal[
        "refit_per_fold_fixed_alpha",
        "frozen_retrospective"
    ]

    folds: List[FoldResult]                   # length 4

    rmse_stability: StabilityResult
    divergence_validity: Optional[DivergenceResult] = None

    market_source: Literal["fc_native", "dp_archive", "ktc_community_csv", "unavailable"]
    market_snapshot_dates: Optional[Dict[int, str]] = None  # {test_year: "YYYY-MM-DD"}

    promotion_gate: GateResult
```

---

## 5. Metric Specifications (`backtest_metrics.py`)

All functions are pure (no side effects, no I/O). All use `from __future__ import annotations`.

### 5.1 Kendall's Tau-b and Spearman ρ

```python
def compute_rank_correlation(
    predicted: list[float],
    realized: list[float],
    n_bootstrap: int = 1000,
    rng_seed: int = 42,
) -> tuple[float, tuple[float, float], float, tuple[float, float]]:
    """
    Returns (kendall_tau, kendall_bca_ci95, spearman_rho, spearman_bca_ci95).
    Uses scipy.stats.kendalltau(variant='b') for Tau-b (handles ties).
    BCa bootstrap on both.
    Returns (nan, (nan, nan), nan, (nan, nan)) if len(predicted) < 10.
    """
```

Use `scipy.stats.kendalltau(predicted_ranks, realized_ranks, variant='b')` for Tau-b.
Use `scipy.stats.spearmanr(predicted_ranks, realized_ranks)` for ρ.
For BCa CI: use `scipy.stats.bootstrap((data,), statistic, method='BCa', n_resamples=n_bootstrap, random_state=rng_seed)`.

### 5.2 NDCG

```python
def compute_ndcg(
    predicted_ranks: list[int],              # model's rank order (1=best)
    realized_ppg: list[float],               # continuous relevance scores
    k: int,
) -> float:
    """
    NDCG@k. Realized PPG is the graded relevance score.
    DCG = sum(realized_ppg[i] / log2(predicted_rank[i] + 1)) for rank <= k.
    IDCG = DCG of perfect ranking (players sorted by realized_ppg desc).
    Returns NDCG = DCG / IDCG.
    Returns 0.0 if k > len(predicted_ranks).
    """
```

### 5.3 Precision@k (for Trust Surface UI)

```python
def compute_precision_at_k(
    model_top_k: set[str],                   # player_ids
    market_top_k: set[str],
    realized_top_k: set[str],
    k: int,
) -> TopKResult:
    """
    model_hit_rate = |model_top_k ∩ realized_top_k| / k
    market_hit_rate = |market_top_k ∩ realized_top_k| / k
    Wilson CI on (model_hit_rate - market_hit_rate).
    """
```

### 5.4 HLN-Corrected Diebold-Mariano

```python
def diebold_mariano_hln(
    model_errors: list[float],               # squared errors: (y_hat - y)^2
    naive_errors: list[float],               # (y_naive - y)^2, same length
) -> tuple[float, float]:
    """
    Returns (dm_statistic, p_value).
    Naive: y_naive = ppg_t (prior-season PPG).
    Loss differential: d_t = model_error_t - naive_error_t.
    DM statistic: d_bar / sqrt(HLN-corrected_variance).
    HLN correction: multiply variance by (T+1 - 2h + h(h-1)/T) / T
    where h=1 (1-step-ahead forecast), T = len(model_errors).
    Two-sided p-value from scipy.stats.t.sf(abs(stat), df=T-1) * 2.
    Returns (nan, nan) if T < 4.
    """
```

Reference: Harvey, Leybourne & Newbold (1997) eq. (9). See merged research brief for formula.

### 5.5 Mann-Whitney U + BCa Bootstrap (Gate 4 — implement structure, defer execution)

```python
def compute_divergence_validity(
    flagged_alphas: list[float],             # Beta-adjusted value changes for flagged players
    control_alphas: list[float],             # Beta-adjusted value changes for matched controls
    n_bootstrap: int = 5000,
    rng_seed: int = 42,
) -> DivergenceResult:
    """
    Mann-Whitney U: scipy.stats.mannwhitneyu(flagged, control, method='exact' if n<20 else 'asymptotic').
    BCa bootstrap: scipy.stats.bootstrap((flagged - control_mean,), np.mean, method='BCa', ...).
    Hit rate: fraction of flagged players with alpha > position_beta (already subtracted).
    Wilson CI: statsmodels.stats.proportion.proportion_confint(hits, n, method='wilson').
    Matched control construction is caller's responsibility (see WalkForwardDriver).
    """
```

---

## 6. Feature Isolation — Mandatory Checklist

The `WalkForwardDriver` must enforce this checklist at every fold boundary. These are the temporal leakage failure modes:

| Check | Rule |
|---|---|
| **Train/test split** | Filter by `feature_season`: train = `season < test_year`, test = `season == test_year`. Only `training_eligible = True` rows. |
| **Outcome column** | `avg_ppg_t1_t2` must be present and non-null in all train rows and all test rows used for metric computation. |
| **Scaler** | `StandardScaler` or equivalent must be **fit only on the train fold** and applied to transform the test fold. Never fit on the combined dataset. |
| **Lagged features** | `ppg_t_minus_1`, `ppg_t_minus_2`, `snap_share_t_minus_1` must already be populated in the CSV per row. The harness does NOT compute these — it reads them. Verify they are derived from `feature_season - 1` and `feature_season - 2` respectively, not from future seasons. |
| **Imputation** | Missing values in train-only features (e.g., `cpoe` for Year 1 QBs) must be imputed using the **train fold mean**, then the same imputed value applied to the test fold. |
| **Position filter** | Each fold processes one position at a time. No cross-position scaling or imputation. |
| **Metadata columns** | `player_id`, `position`, `feature_season`, `team`, `depth_chart_position` are excluded from the feature matrix X. They are used for filtering and join keys only. |
| **Outcome exclusion from X** | `avg_ppg_t1_t2`, `training_eligible`, `ppg_t1`, `ppg_t2`, `games_t1`, `games_t2` (if present) must never appear in the feature matrix X. |

---

## 7. WalkForwardDriver (`backtest_harness.py`)

```python
class WalkForwardDriver:
    """
    Manages 4-fold expanding-window evaluation of Engine B v2.

    Usage:
        driver = WalkForwardDriver(position="WR", model_version="engine_b_v2")
        result = driver.run()
        result.save(Path("app/data/backtest/runs/..."))
    """

    FOLD_DEFINITIONS = [
        {"fold_index": 1, "test_year": 2020, "outcome_seasons": [2021, 2022]},
        {"fold_index": 2, "test_year": 2021, "outcome_seasons": [2022, 2023]},
        {"fold_index": 3, "test_year": 2022, "outcome_seasons": [2023, 2024]},
        {"fold_index": 4, "test_year": 2023, "outcome_seasons": [2024, 2025]},
    ]

    FIXED_ALPHA = {"QB": 1000.0, "RB": 500.0, "WR": 200.0}

    def __init__(self, position: str, model_version: str = "engine_b_v2"):
        ...

    def run(self) -> BacktestResult:
        """
        For each fold:
          1. Load and slice the training CSV
          2. Build X_train, y_train, X_test per the isolation checklist (Section 6)
          3. Fit Ridge(alpha=FIXED_ALPHA[position]) on train
          4. Predict y_hat on test
          5. Compute per-fold metrics
          6. Join market snapshot (if available)
          7. Discard the Ridge instance
        Then compute aggregate metrics (DM test, stability).
        Then evaluate promotion gates.
        Return BacktestResult.
        """

    def _build_fold_data(
        self,
        df: pd.DataFrame,
        test_year: int,
        position: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Returns (train_df, test_df) per isolation checklist."""

    def _get_feature_columns(self, position: str) -> list[str]:
        """
        Returns the per-position feature list from ENGINE_B_FEATURES_QB/RB/WR.
        Intersected with columns actually present in the CSV.
        Excludes metadata and outcome columns.
        """
```

---

## 8. Market Snapshot Store (`market_snapshot_store.py`)

```python
class MarketSnapshotStore:
    """
    SQLite-backed store for FantasyCalc snapshots (native + archive).
    Default path: app/data/fc_snapshots.db
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        ...

    def upsert_snapshots(self, rows: list[dict]) -> int:
        """Insert rows; conflict on (snapshot_date, league_settings_hash, sleeper_id) = REPLACE."""

    def get_snapshot(
        self,
        snapshot_date: str,               # "YYYY-MM-DD"
        position: Optional[str] = None,   # None = all positions
    ) -> list[dict]:
        """
        Returns all rows for the given date. If exact date unavailable,
        returns the closest date within ±7 days and logs a warning.
        Returns [] if no data within ±7 days.
        """

    def get_ranked(
        self,
        snapshot_date: str,
        position: str,
    ) -> list[dict]:
        """Returns rows for position sorted by overall_rank asc."""

    def has_snapshot(self, snapshot_date: str) -> bool:
        ...

    def get_coverage(self) -> dict:
        """Returns {earliest_date, latest_date, n_dates, n_rows, sources}."""
```

---

## 9. Promotion Gate Logic

```python
def evaluate_promotion_gates(
    folds: list[FoldResult],
    stability: StabilityResult,
    position: str,
    divergence: Optional[DivergenceResult] = None,
) -> GateResult:
    """
    G1 — Kendall Rank Correlation:
      Pass if: mean kendall_tau across 4 folds >= THRESHOLD[position]
               AND bootstrap CI lower bound >= 0.20 in >= 3 of 4 folds.
      Thresholds: QB >= 0.30, RB >= 0.40, WR >= 0.40.
      Note: thresholds are "Baseline Targets — Dynamic". They will be
      reviewed after the first 4-fold run and adjusted if the market
      baseline itself falls below them.

    G2 — RMSE Stability:
      Pass if: rmse_max_deviation_pct <= 25.0%
               AND stability.dm_hln_pvalue <= 0.10 (if computed).

    G3 — Market Superiority:
      Pass if: ndcg_at_24_model >= ndcg_at_24_market in >= 3 of 4 folds
               where market data is available.
      If market data unavailable for all folds: gate = "deferred".

    G4 — Divergence Validity:
      Pass if: mann_whitney_p <= 0.10
               AND diff_bca_ci95[0] > 0.0
               AND hit_rate_wilson_ci95[0] > 0.50
               on n_flagged >= 30 pooled across >= 2 seasons.
      If n_flagged < 30: gate = "insufficient_data".
      If divergence_validity is None: gate = "deferred".

    Grade assignment:
      G1 + G2 + G3 all pass → "ACTIVE_B_VALIDATED"
      G1 + G2 + G3 + G4 all pass → "DECISION_GRADE"
      G1 + G2 pass, G3 deferred → "ACTIVE_B" (no change)
      Any of G1 or G2 fails → "ACTIVE_B" (no change; harness does not demote)
      TE position → always "FALLBACK_V1" (not evaluated)
    """
```

---

## 10. CLI Interface (`scripts/run_backtest.py`)

```bash
# Run harness for one position:
.venv/bin/python3.14 scripts/run_backtest.py --position WR --model engine_b_v2

# Run all three active positions:
.venv/bin/python3.14 scripts/run_backtest.py --all

# Output:
# app/data/backtest/runs/{run_id}/backtest_result_WR.json
```

The script must:
1. Load the Engine B v2 .pkl path from `v2_manifest.json` to compute `model_artifact_hash`
2. Capture `git_sha` from `git rev-parse HEAD`
3. Instantiate `WalkForwardDriver(position, model_version)`
4. Call `driver.run()`
5. Write the artifact to `app/data/backtest/runs/{run_id}/backtest_result_{position}.json`
6. Print a brief summary table to stdout

---

## 11. Daily Snapshot Cron (`scripts/snapshot_fantasycalc.py`)

```python
"""
Capture today's FantasyCalc dynasty values and write to fc_snapshots.db.

Usage:
    .venv/bin/python3.14 scripts/snapshot_fantasycalc.py

Schedule:
    crontab: 0 5 * * * /path/to/.venv/bin/python3.14 /path/to/scripts/snapshot_fantasycalc.py >> /path/to/logs/fc_snapshot.log 2>&1

Exit codes:
    0 = success
    1 = API error (no rows written)
    2 = DB error (rows fetched but not written)
"""
FC_URL = "https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1"
LEAGUE_SETTINGS_HASH = hashlib.sha256(FC_URL.split("?")[1].encode()).hexdigest()[:16]
```

Fields to write per player:
- `snapshot_date`: today's date
- `league_settings_hash`: LEAGUE_SETTINGS_HASH constant
- `sleeper_id`: from `fc_entry["player"]["sleeperId"]`
- `value`: from `fc_entry["value"]`
- `overall_rank`: from `fc_entry["overallRank"]`
- `position_rank`: from `fc_entry["positionRank"]`
- `position`: from `fc_entry["player"]["position"]`
- `trend_30day`: from `fc_entry["trend30Day"]`
- `source`: `"fc_native"`
- `inserted_at`: UTC datetime

---

## 12. Trust Surface Route (`app/api/routes/trust_surface.py`)

```python
@router.get("/trust-surface/{position}")
async def get_trust_surface(position: str) -> dict:
    """
    Read-only. Returns the most recent BacktestResult artifact for the position.
    Searches app/data/backtest/runs/ for the latest run_id directory.
    Returns 404 if no artifact exists for the position.
    Returns 200 with the full BacktestResult JSON.
    No recomputation. No model calls. File read only.
    """
```

Register at `app/main.py` alongside existing routes.

---

## 13. TDD Task Sequence

All tasks follow the same discipline: write RED test → implement GREEN → verify full suite → commit.

### Task 10.0 — BacktestResult Schema + Contract Tests

**Files:** `src/dynasty_genius/eval/backtest_artifact.py`, `tests/contract/test_backtest_result_schema.py`

Contract tests must enforce:
1. `BacktestResult` validates with all required fields populated
2. `overall_grade` is one of the five valid literals
3. `g4_divergence_validity_pass` accepts `True`, `False`, `"deferred"`, `"insufficient_data"`
4. `model_artifact_hash` is a non-empty string
5. `retrain_mode` is one of the two valid literals
6. A `BacktestResult` with `g1=True, g2=True, g3=True, g4="deferred"` gets grade `ACTIVE_B_VALIDATED`
7. A `BacktestResult` with any G1 or G2 failure gets grade `ACTIVE_B` (not demoted further)
8. `FoldResult` with all metric fields `None` still validates (market data may be absent)

---

### Task 10.1 — Market Snapshot Store

**Files:** `src/dynasty_genius/eval/market_snapshot_store.py`, `tests/test_market_snapshot_store.py`

Unit tests:
1. `upsert_snapshots` writes rows and is idempotent on conflict
2. `get_snapshot` returns exact date if available
3. `get_snapshot` returns nearest date within ±7 days if exact not available
4. `get_snapshot` returns `[]` if no data within ±7 days
5. `has_snapshot` returns True/False correctly
6. `get_ranked` returns rows sorted by overall_rank ascending

All tests use `tmp_path` fixture for the DB path.

---

### Task 10.2 — Daily Snapshot Script

**Files:** `scripts/snapshot_fantasycalc.py`, `tests/test_snapshot_script.py`

Unit tests (all using mocked HTTP — no real API calls in test suite):
1. On successful API response, writes correct number of rows to store
2. `sleeper_id` is populated from `fc_entry["player"]["sleeperId"]`
3. `source` = `"fc_native"` on all rows
4. On HTTP error, exits with code 1 and writes zero rows
5. Skips rows where `sleeperId` is None (some FC entries have no Sleeper ID)

---

### Task 10.3 — Feature Fold Builder

**Files:** `src/dynasty_genius/eval/backtest_harness.py` (partial — just `_build_fold_data`), `tests/test_backtest_harness.py` (partial)

Unit tests:
1. Train set contains only `feature_season < test_year` and `training_eligible = True`
2. Test set contains only `feature_season == test_year` and `training_eligible = True`
3. No future-season data in train (i.e., no `feature_season >= test_year`)
4. `avg_ppg_t1_t2` column is absent from both X_train and X_test
5. Scaler is fit on train only: mean of X_test column is NOT equal to zero after transform (unless it happens to be)
6. Position filter: only rows for the given position are included
7. Imputation uses train fold mean, not global mean

---

### Task 10.4 — Statistical Metric Functions

**Files:** `src/dynasty_genius/eval/backtest_metrics.py`, `tests/test_backtest_metrics.py`

Unit tests for each function:

**Kendall τ-b:**
1. Perfect ranking returns τ = 1.0
2. Reversed ranking returns τ = -1.0
3. Known-result case (manual calc) returns correct τ with tolerance
4. BCa CI lower bound < point estimate < upper bound
5. Returns `(nan, (nan, nan))` when n < 10

**Spearman ρ:**
6. Perfect ranking returns ρ = 1.0
7. Known-result case correct within tolerance
8. BCa CI correct bounds

**NDCG:**
9. Perfect ranking returns NDCG = 1.0
10. `k` larger than list length returns 0.0
11. Logarithmic discounting: rank-1 error penalized more than rank-k error

**Precision@k:**
12. `|overlap| / k` formula correct
13. Wilson CI lower bound ≥ 0.0, upper bound ≤ 1.0

**HLN-DM:**
14. Identical model and naive errors returns p ≈ 1.0
15. Model consistently better than naive returns p < 0.10 on synthetic data
16. Returns `(nan, nan)` when T < 4

---

### Task 10.5 — WalkForwardDriver (Full)

**Files:** `src/dynasty_genius/eval/backtest_harness.py` (complete), `tests/test_backtest_harness.py` (complete)

Unit tests:
1. `driver.run()` returns a `BacktestResult` with exactly 4 `FoldResult` entries
2. Each fold's `n_train` increases with each fold (expanding window)
3. Each fold's `n_test` matches the expected values from Section 2.2
4. `ridge_alpha` in result matches `FIXED_ALPHA[position]`
5. `retrain_mode` = `"refit_per_fold_fixed_alpha"`
6. `kendall_tau` in each fold is between -1.0 and 1.0
7. `rmse` in each fold is positive
8. Per-fold Ridge instance is not retained in the driver after the fold completes (test via memory/state check)

Tests use the real `app/data/training/engine_b_features_v2.csv` (no mocking needed — the CSV is in the repo).

---

### Task 10.6 — BacktestResult Artifact Persistence

**Files:** `src/dynasty_genius/eval/backtest_artifact.py` (add save/load), `tests/contract/test_backtest_result_schema.py` (add persistence tests)

Contract tests:
1. `result.save(path)` writes valid JSON deserializable back to `BacktestResult`
2. Loaded artifact has identical `run_id`, `model_version`, `position`
3. `model_artifact_hash` is the SHA-256 hex of the .pkl file
4. `git_sha` is a 40-character hex string or None
5. `run_date` round-trips through JSON without loss of timezone info

---

### Task 10.7 — Market Comparison Integration

**Files:** `src/dynasty_genius/eval/backtest_harness.py` (add market join), `tests/test_backtest_harness.py` (add market tests)

Unit tests:
1. When `MarketSnapshotStore.get_snapshot` returns empty, all market fields in `FoldResult` are None
2. When market data is available, `ndcg_at_24_model` and `ndcg_at_24_market` are populated
3. Market join uses `sleeper_id` as the key (players without a `sleeper_id` in the test set are excluded from market comparison — they do not fail the fold)
4. Timestamp: harness queries the snapshot store for the date closest to `Sep 8` of `test_year + 1` (i.e., start of the first outcome season)

---

### Task 10.8 — Gate Evaluator

**Files:** `src/dynasty_genius/eval/backtest_harness.py` (add `evaluate_promotion_gates`), `tests/test_backtest_harness.py`

Unit tests:
1. G1+G2+G3 pass, G4 deferred → grade = `"ACTIVE_B_VALIDATED"`
2. G1+G2+G3+G4 all pass → grade = `"DECISION_GRADE"`
3. G1 fail → grade = `"ACTIVE_B"`
4. G2 fail → grade = `"ACTIVE_B"`
5. G3 all folds unavailable → G3 = "deferred", grade = `"ACTIVE_B"`
6. G4 n_flagged < 30 → G4 = `"insufficient_data"`, grade = `"ACTIVE_B_VALIDATED"` (if G1–G3 pass)
7. QB τ threshold is 0.30 (different from RB/WR 0.40)
8. Gate version field = `"1.0"`

---

### Task 10.9 — CLI Script + Trust Surface Route

**Files:** `scripts/run_backtest.py`, `app/api/routes/trust_surface.py`, `app/main.py` (register route)

Tests:
1. `GET /trust-surface/WR` returns 404 when no artifact exists
2. `GET /trust-surface/WR` returns 200 + valid JSON when artifact exists (use `tmp_path` fixture to write a test artifact)
3. Route returns the most recent run_id if multiple exist
4. Route returns `overall_grade` field at the top level of the response

---

### Task 10.10 — Community CSV Ingest Script

**Files:** `scripts/ingest_market_archive.py`, `tests/test_market_snapshot_store.py` (add CSV ingest tests)

Tests:
1. Script correctly maps community CSV columns to store schema
2. `source` field is set from `--source` CLI argument
3. Rows with null/missing `sleeper_id` are skipped and counted in a `skipped_count` log output
4. Idempotent: running twice on the same CSV produces the same row count

---

## 14. Promotion Gate Thresholds

These are **Baseline Targets — Dynamic**. They will be reviewed after the first 4-fold run completes. If the market baseline itself fails to achieve these thresholds (i.e., market Kendall τ < 0.30 for QB), thresholds will be recalibrated to model-vs-market differential framing.

| Gate | Metric | Threshold | Pass Condition |
|---|---|---|---|
| **G1** | Kendall τ-b | QB ≥ 0.30, RB/WR ≥ 0.40 | Mean across 4 folds meets threshold AND BCa CI lower bound ≥ 0.20 in ≥ 3 of 4 folds |
| **G2** | RMSE stability | max deviation ≤ 25% AND DM p ≤ 0.10 | Both sub-criteria pass |
| **G3** | NDCG@24 | model ≥ market | ≥ 3 of 4 folds where market data is available |
| **G4** | Divergence validity | MW p ≤ 0.10 AND BCa CI > 0 AND Wilson lower > 0.50 | n_flagged ≥ 30 pooled across ≥ 2 seasons |

---

## 15. Gitignore Additions

Add to `.gitignore`:
```
# Backtest market snapshot store — operational data, not source code
app/data/fc_snapshots.db
app/data/fc_snapshots.db-journal

# Backtest run artifacts — large JSON, versioned by run_id
app/data/backtest/runs/
```

---

## 16. AGENT_SYNC and Ledger

On completion, the implementing agent must:
1. Update `AGENT_SYNC.md`: active phase → Phase 10/11 Backtest Harness; test count
2. Append to `docs/agent-ledger/2026-05-14.md` with the full ledger entry format
3. Open PR against main once all 384+ tests pass + new tests green

---

## 17. Open Data Questions (for David Before Implementation Starts)

1. **Community CSV download**: Have you sourced the community KTC/FC dynasty CSV archives for 2021–2024? If yes, what's the file path? If no, the market comparison gate (G3) will be skipped in v1 until archives are ingested.

2. **Daily snapshot location**: Where should `fc_snapshots.db` live — in the repo directory (`app/data/`, gitignored) or in a separate data directory outside the repo? The spec defaults to `app/data/`.

3. **Gate threshold direction confirmation**: After the first fold runs, if market Kendall τ < 0.30 for QB, should we use **relative** thresholds (model must exceed market by X) rather than absolute ones? David confirmed in research session that thresholds are "Baseline Targets — Dynamic." The spec implements absolute for now and flags this as a first-run review item.

---

## 18. Deferred Items (Explicit)

| Item | Reason | Review date |
|---|---|---|
| Gate 4 execution | Requires ~6 months native FC snapshots | ~Q4 2026 |
| `DECISION_GRADE` promotion | Requires Gate 4 | After Q4 2026 review |
| TE backtest | Per-fold n too small; TE fails engine gate | Phase 12 |
| nfl_data_py CSV refresh | Assumes existing CSV is current; v2 will pull fresh nflverse data | Phase 12 |
| ~~Matched-control K=3 construction~~ | **Moved to v1** (David, 2026-05-14): positional Beta alone risks the demographic trap — model appears to have Alpha by preferring younger/cheaper players. K=3 match is required for Gate 4 to be scientifically honest from first execution. | ~~v2~~ → **v1** |
| Per-fold Ridge α re-tuning | Double-dipping risk; defer until n improves | After RB feature expansion |
| Trust Surface HTML frontend | Frontend is last per constitution | After DECISION_GRADE earned |
