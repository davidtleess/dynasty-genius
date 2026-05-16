"""WalkForwardDriver — expanding-window walk-forward evaluation of Engine B v2.

Task 10.3: _build_fold_data + _get_feature_columns.
Task 10.5: run() — full fold loop, Ridge refit, metrics, BacktestResult.
Task 10.7: market comparison — _compute_market_ndcg, run() market_store param.
Gate evaluation (10.8) added later.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    DivergenceResult,
    FoldResult,
    GateResult,
    StabilityResult,
)
from src.dynasty_genius.eval.backtest_metrics import compute_ndcg, compute_rank_correlation
from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_FEATURES_BY_POSITION,
    OUTCOME_COLUMN,
    validate_no_temporal_leakage,
    validate_no_prohibited_features,
)

if TYPE_CHECKING:
    from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore


# ── Market comparison helpers ─────────────────────────────────────────────────

def _market_snapshot_date(test_year: int) -> str:
    """Sep 8 of test_year + 1 = start of first outcome season."""
    return f"{test_year + 1}-09-08"


_MARKET_SOURCE_MAP: dict[str, str] = {
    "fc_native": "fc_native",
    "ktc_community_csv": "ktc_community_csv",
    "dp_archive": "dp_archive",
}


def _compute_ranks_desc(scores: list[float]) -> list[int]:
    """Rank n scores descending: highest score gets rank 1."""
    order = np.argsort(scores)[::-1]
    ranks = [0] * len(scores)
    for rank, idx in enumerate(order, 1):
        ranks[int(idx)] = rank
    return ranks


def _compute_market_ndcg(
    y_pred: np.ndarray,
    player_ids: list[str],
    y_realized: np.ndarray,
    market_rows: list[dict],
    id_map: dict[str, str],
) -> dict[str, Optional[float]]:
    """Compute NDCG@12 and @24 for model and market on the sleeper-matched pool.

    Players without a gsis_id → sleeper_id mapping, or whose sleeper_id is absent
    from the market snapshot, are excluded from the comparison pool but do NOT
    affect the fold's prediction metrics (y_pred / y_realized stay untouched).

    Returns a dict with keys: ndcg_at_12_model, ndcg_at_12_market,
    ndcg_at_24_model, ndcg_at_24_market.  All None when pool is empty.
    """
    _null: dict[str, Optional[float]] = {
        "ndcg_at_12_model": None, "ndcg_at_12_market": None,
        "ndcg_at_24_model": None, "ndcg_at_24_market": None,
    }
    if not market_rows:
        return _null

    market_by_sleeper = {row["sleeper_id"]: float(row["value"]) for row in market_rows}

    pool_pred: list[float] = []
    pool_market: list[float] = []
    pool_realized: list[float] = []

    for i, gsis_id in enumerate(player_ids):
        sleeper_id = id_map.get(gsis_id)
        if sleeper_id and sleeper_id in market_by_sleeper:
            pool_pred.append(float(y_pred[i]))
            pool_market.append(market_by_sleeper[sleeper_id])
            pool_realized.append(float(y_realized[i]))

    n = len(pool_pred)
    if n == 0:
        return _null

    model_ranks = _compute_ranks_desc(pool_pred)
    market_ranks = _compute_ranks_desc(pool_market)

    result: dict[str, Optional[float]] = {}
    for k in [12, 24]:
        if n >= k:
            result[f"ndcg_at_{k}_model"] = compute_ndcg(model_ranks, pool_realized, k)
            result[f"ndcg_at_{k}_market"] = compute_ndcg(market_ranks, pool_realized, k)
        else:
            result[f"ndcg_at_{k}_model"] = None
            result[f"ndcg_at_{k}_market"] = None

    return result


def _load_gsis_to_sleeper_map() -> dict[str, str]:
    """Build GSIS → Sleeper ID map from nflreadpy. Returns {} if unavailable."""
    try:
        import nflreadpy  # type: ignore[import]
        ff = nflreadpy.load_ff_playerids()
        valid = ff[ff["gsis_id"].notna() & ff["sleeper_id"].notna()]
        return dict(zip(valid["gsis_id"].astype(str), valid["sleeper_id"].astype(str)))
    except Exception:
        return {}

CSV_PATH = Path("app/data/training/engine_b_features_v2.csv")

_METADATA_COLS: frozenset[str] = frozenset({
    "player_id", "position", "feature_season", "team",
    "depth_chart_position", "aging_curve_position",
    "training_eligible", OUTCOME_COLUMN,
    # Component outcome columns — must never enter X
    "ppg_t1", "ppg_t2", "games_t1", "games_t2",
})


def evaluate_promotion_gates(
    folds: list[FoldResult],
    stability: StabilityResult,
    position: str,
    divergence: Optional[DivergenceResult] = None,
) -> GateResult:
    """Evaluate G1–G3 (v1) and G4 (v2) promotion gates.

    G1 — Kendall Rank Correlation:
      Pass if: mean kendall_tau >= THRESHOLD[position]
               AND BCa CI lower bound >= 0.20 in >= 3 of 4 folds.
      Thresholds: QB >= 0.30, RB >= 0.40, WR >= 0.40.

    G2 — RMSE Stability:
      Pass if: rmse_max_deviation_pct <= 25.0%
               AND stability.dm_hln_pvalue <= 0.10 (if computed).

    G3 — Market Superiority:
      Pass if: ndcg_at_24_model >= ndcg_at_24_market in >= 3 of 4 folds
               where market data is available.

    G4 — Divergence Validity (Deferred to v2):
      Pass if: MW p <= 0.10, diff CI > 0, and hit-rate CI > 0.50 on n >= 30.
    """
    # G1 — Rank Correlation
    threshold = 0.30 if position == "QB" else 0.40
    mean_tau = (
        sum(f.kendall_tau for f in folds) / len(folds) if folds else 0.0
    )
    # Count folds where the 95% BCa CI lower bound is at least 0.20
    ci_pass_count = sum(
        1 for f in folds if f.kendall_tau_bca_ci95[0] >= 0.20
    )
    g1_pass = mean_tau >= threshold and ci_pass_count >= 3

    # G2 — RMSE Stability
    g2_pass = stability.rmse_max_deviation_pct <= 25.0
    if stability.dm_hln_pvalue is not None:
        g2_pass = g2_pass and stability.dm_hln_pvalue <= 0.10

    # G3 — Market Superiority
    market_available_folds = [
        f for f in folds if f.ndcg_at_24_market is not None
    ]
    if not market_available_folds:
        g3_result: bool | str = "deferred"
        g3_status = "deferred"
    else:
        wins = sum(
            1 for f in market_available_folds
            if (f.ndcg_at_24_model or 0) >= (f.ndcg_at_24_market or 0)
        )
        g3_result = wins >= 3
        g3_status = "passed" if g3_result else "failed"

    # G4 — Divergence Validity
    if divergence is None:
        g4_status = "deferred"
    elif divergence.n_flagged < 30:
        g4_status = "insufficient_data"
    else:
        g4_pass = (
            divergence.mann_whitney_p <= 0.10
            and divergence.diff_bca_ci95[0] > 0.0
            and divergence.hit_rate_wilson_ci95[0] > 0.50
        )
        g4_status = g4_pass

    # Overall Grade Assignment
    if not g1_pass or not g2_pass:
        grade = "ACTIVE_B"
    elif g3_status == "deferred":
        grade = "ACTIVE_B"
    elif g3_result is not True:
        grade = "ACTIVE_B"
    elif g4_status is True:
        grade = "DECISION_GRADE"
    else:
        grade = "ACTIVE_B_VALIDATED"

    # Justification text
    just_parts = []
    if g1_pass:
        just_parts.append(f"G1 rank-corr pass ({mean_tau:.2f} tau)")
    if g2_pass:
        just_parts.append(
            f"G2 stability pass ({stability.rmse_max_deviation_pct:.1f}% dev)"
        )
    if g3_result is True:
        just_parts.append("G3 market superiority pass")

    if grade == "ACTIVE_B":
        failed = []
        if not g1_pass: failed.append("G1")
        if not g2_pass: failed.append("G2")
        if g3_status != "passed": failed.append("G3")
        justification = f"Promotion blocked by {', '.join(failed)}."
    else:
        justification = ", ".join(just_parts) + "."

    return GateResult(
        g1_rank_correlation_pass=g1_pass,
        g2_rmse_stability_pass=g2_pass,
        g3_market_superiority_pass=g3_result,
        g4_divergence_validity_pass=g4_status,
        overall_grade=grade,
        promotion_justification=justification,
    )


class WalkForwardDriver:
    """Expanding-window walk-forward evaluation of Engine B v2.

    Usage (full — Task 10.5):
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

    FIXED_ALPHA: dict[str, float] = {
        "QB": 1000.0,
        "RB": 500.0,
        "WR": 200.0,
        "TE": 1.0,
    }

    def __init__(self, position: str, model_version: str = "engine_b_v2") -> None:
        self.position = position
        self.model_version = model_version

    def _get_feature_columns(self, position: str, df_columns: list[str]) -> list[str]:
        """Contract ∩ CSV columns, minus all metadata and outcome columns."""
        contract = ENGINE_B_FEATURES_BY_POSITION[position]
        available = contract & set(df_columns) - _METADATA_COLS
        return sorted(available)

    def _build_fold_data(
        self,
        df: pd.DataFrame,
        test_year: int,
        position: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Return (X_train, X_test) — imputed, scaled, feature-only DataFrames.

        Enforces the full temporal isolation checklist (spec Section 6):
        - Train: feature_season < test_year, training_eligible=True, position filter
        - Test:  feature_season == test_year, training_eligible=True, position filter
        - Features: ENGINE_B contract ∩ CSV columns, minus metadata and outcome
        - Imputation: SimpleImputer(mean) fit on train only
        - Scaling: StandardScaler fit on train only
        """
        train_mask = (
            (df["feature_season"] < test_year)
            & df["training_eligible"].astype(bool)
            & (df["position"] == position)
        )
        test_mask = (
            (df["feature_season"] == test_year)
            & df["training_eligible"].astype(bool)
            & (df["position"] == position)
        )

        train_df = df[train_mask].copy()
        test_df = df[test_mask].copy()

        feature_cols = self._get_feature_columns(position, list(df.columns))

        validate_no_temporal_leakage(feature_cols)
        validate_no_prohibited_features(feature_cols)

        X_train = train_df[feature_cols].copy()
        X_test = test_df[feature_cols].copy()

        # Impute — fit on train, apply to both.
        # keep_empty_features=True: if a column is entirely null in train (e.g.,
        # ppg_t_minus_2 in fold 1 where train only covers 2018-2019 and T-2 data
        # would require 2016-2017 history not present in the CSV), impute to 0.0
        # and keep the column. The _available flag encodes absence for the model.
        imputer = SimpleImputer(strategy="mean", keep_empty_features=True)
        X_train_arr = imputer.fit_transform(X_train)
        X_test_arr = imputer.transform(X_test)

        # Scale — fit on train, apply to both
        scaler = StandardScaler()
        X_train_arr = scaler.fit_transform(X_train_arr)
        X_test_arr = scaler.transform(X_test_arr)

        return (
            pd.DataFrame(X_train_arr, columns=feature_cols),
            pd.DataFrame(X_test_arr, columns=feature_cols),
        )

    def run(
        self,
        market_store: Optional["MarketSnapshotStore"] = None,
        id_map: Optional[dict[str, str]] = None,
        emit_prediction_log: bool = False,
        emit_market_comparison: bool = False,
    ) -> BacktestResult:
        """Execute the full walk-forward backtest. Returns an immutable BacktestResult.

        For each fold: refit Ridge at fixed alpha on train, predict on test,
        compute Kendall τ-b / Spearman ρ / RMSE / MAE, then optionally join
        market snapshots (market_store) for NDCG@12/24 comparison.

        Args:
            market_store: Optional SQLite snapshot store. When None, all market
                fields in FoldResult are left as None.
            id_map: Optional GSIS → sleeper_id mapping dict. When market_store is
                provided and id_map is None, loads from nflreadpy automatically.
                Pass {} to skip market comparison without network call.
            emit_prediction_log: When True, accumulates per-player test-fold rows
                in self.prediction_rows after run() completes.
            emit_market_comparison: When True, accumulates per-player market
                comparison rows in self.market_comparison_rows after run() completes.
        """
        df = pd.read_csv(CSV_PATH)
        position = self.position
        alpha = self.FIXED_ALPHA[position]

        # Build id_map once if market comparison is active
        _id_map: dict[str, str] = {}
        if market_store is not None:
            _id_map = id_map if id_map is not None else _load_gsis_to_sleeper_map()

        fold_results: list[FoldResult] = []
        market_snapshot_dates_by_fold: dict[int, str] = {}
        market_sources_found: list[str] = []
        _prediction_rows: list[dict] = []
        _market_comparison_rows: list[dict] = []

        for fold_def in self.FOLD_DEFINITIONS:
            fold_index = fold_def["fold_index"]
            test_year = fold_def["test_year"]
            outcome_seasons = fold_def["outcome_seasons"]

            X_train, X_test = self._build_fold_data(df, test_year, position)

            # Same masks used by _build_fold_data — extract outcomes and player IDs
            train_mask = (
                (df["feature_season"] < test_year)
                & df["training_eligible"].astype(bool)
                & (df["position"] == position)
            )
            test_mask = (
                (df["feature_season"] == test_year)
                & df["training_eligible"].astype(bool)
                & (df["position"] == position)
            )
            y_train = df.loc[train_mask, OUTCOME_COLUMN].to_numpy(dtype=float)
            y_test = df.loc[test_mask, OUTCOME_COLUMN].to_numpy(dtype=float)
            player_ids_test = df.loc[test_mask, "player_id"].tolist()

            # Refit with fixed alpha — local variable only; never stored on self
            ridge = Ridge(alpha=alpha)
            ridge.fit(X_train.to_numpy(), y_train)
            y_pred = ridge.predict(X_test.to_numpy())
            del ridge

            residuals = y_pred - y_test
            rmse = float(np.sqrt(np.mean(residuals ** 2)))
            mae = float(np.mean(np.abs(residuals)))

            # Accumulate prediction log rows — test fold only
            if emit_prediction_log:
                model_ranks = _compute_ranks_desc(y_pred.tolist())
                age_values = df.loc[test_mask, "age"].tolist() if "age" in df.columns else [None] * len(y_pred)
                for i, pid in enumerate(player_ids_test):
                    _prediction_rows.append({
                        "player_id": pid,
                        "position": position,
                        "fold_index": fold_index,
                        "feature_season": test_year,
                        "predicted_ppg": float(y_pred[i]),
                        "realized_ppg": float(y_test[i]),
                        "model_rank": model_ranks[i],
                        "residual": float(y_test[i]) - float(y_pred[i]),
                        "age_at_feature_season": age_values[i] if age_values[i] is not None else None,
                        "draft_round": None,
                    })

            tau, tau_ci, rho, rho_ci = compute_rank_correlation(
                y_pred.tolist(), y_test.tolist()
            )

            train_years = sorted(
                int(s) for s in df.loc[train_mask, "feature_season"].unique()
            )

            # Market comparison — only when store provided
            ndcg_fields: dict[str, Optional[float]] = {
                "ndcg_at_12_model": None, "ndcg_at_12_market": None,
                "ndcg_at_24_model": None, "ndcg_at_24_market": None,
            }
            if market_store is not None:
                snap_date = _market_snapshot_date(test_year)
                market_rows = market_store.get_ranked(snap_date, position)
                if market_rows:
                    actual_date = market_rows[0]["snapshot_date"]
                    market_snapshot_dates_by_fold[test_year] = actual_date
                    market_sources_found.append(market_rows[0].get("source", ""))
                    if emit_market_comparison:
                        model_ranks = _compute_ranks_desc(y_pred.tolist())
                        realized_ranks = _compute_ranks_desc(y_test.tolist())
                        market_by_sleeper = {
                            str(row["sleeper_id"]): row for row in market_rows
                        }
                        for i, pid in enumerate(player_ids_test):
                            sleeper_id = _id_map.get(str(pid))
                            market_row = (
                                market_by_sleeper.get(sleeper_id)
                                if sleeper_id is not None
                                else None
                            )
                            fc_rank = (
                                int(market_row["position_rank"])
                                if market_row is not None and market_row.get("position_rank") is not None
                                else (
                                    int(market_row["overall_rank"])
                                    if market_row is not None and market_row.get("overall_rank") is not None
                                    else None
                                )
                            )
                            model_rank = model_ranks[i]
                            _market_comparison_rows.append({
                                "player_id": pid,
                                "sleeper_id": sleeper_id,
                                "position": position,
                                "fold_index": fold_index,
                                "feature_season": test_year,
                                "snapshot_date": actual_date,
                                "predicted_ppg": float(y_pred[i]),
                                "model_rank": model_rank,
                                "fc_value": (
                                    int(market_row["value"])
                                    if market_row is not None and market_row.get("value") is not None
                                    else None
                                ),
                                "fc_rank": fc_rank,
                                "realized_ppg": float(y_test[i]),
                                "realized_rank": realized_ranks[i],
                                "rank_delta": (
                                    fc_rank - model_rank if fc_rank is not None else None
                                ),
                            })
                ndcg_fields = _compute_market_ndcg(
                    y_pred=y_pred,
                    player_ids=player_ids_test,
                    y_realized=y_test,
                    market_rows=market_rows if market_store is not None else [],
                    id_map=_id_map,
                )

            fold_results.append(FoldResult(
                fold_index=fold_index,
                train_years=train_years,
                test_year=test_year,
                outcome_seasons=outcome_seasons,
                n_train=X_train.shape[0],
                n_test=X_test.shape[0],
                kendall_tau=tau,
                kendall_tau_bca_ci95=tau_ci,
                spearman_rho=rho,
                spearman_rho_bca_ci95=rho_ci,
                rank_ic=rho,
                rmse=rmse,
                mae=mae,
                ndcg_at_12_model=ndcg_fields["ndcg_at_12_model"],
                ndcg_at_12_market=ndcg_fields["ndcg_at_12_market"],
                ndcg_at_24_model=ndcg_fields["ndcg_at_24_model"],
                ndcg_at_24_market=ndcg_fields["ndcg_at_24_market"],
            ))

        # Expose accumulated rows as instance attributes
        self.prediction_rows: list[dict] = _prediction_rows
        self.market_comparison_rows: list[dict] = _market_comparison_rows

        rmse_vals = [f.rmse for f in fold_results]
        rmse_mean = float(np.mean(rmse_vals))
        rmse_cv = (
            float(np.std(rmse_vals, ddof=1) / rmse_mean) if rmse_mean > 0 else 0.0
        )
        rmse_max_dev_pct = (
            float(max(abs(r - rmse_mean) / rmse_mean for r in rmse_vals))
            if rmse_mean > 0 else 0.0
        )

        stability = StabilityResult(
            rmse_per_fold=rmse_vals,
            rmse_mean=rmse_mean,
            rmse_cv=rmse_cv,
            rmse_max_deviation_pct=rmse_max_dev_pct,
        )

        # Determine market_source and market_snapshot_dates
        if market_sources_found:
            raw_source = next(
                (s for s in market_sources_found if s in _MARKET_SOURCE_MAP), ""
            )
            final_market_source: str = _MARKET_SOURCE_MAP.get(raw_source, "unavailable")
            final_snapshot_dates: Optional[dict[int, str]] = (
                market_snapshot_dates_by_fold or None
            )
        else:
            final_market_source = "unavailable"
            final_snapshot_dates = None

        pkl_path = self._find_model_pkl(position)
        artifact_hash = (
            BacktestResult.artifact_hash(pkl_path)
            if pkl_path is not None and pkl_path.exists()
            else "unavailable"
        )

        gate = evaluate_promotion_gates(
            folds=fold_results,
            stability=stability,
            position=position,
        )

        return BacktestResult(
            run_date=datetime.now(timezone.utc),
            model_version=self.model_version,
            model_artifact_hash=artifact_hash,
            position=position,
            ridge_alpha=alpha,
            retrain_mode="refit_per_fold_fixed_alpha",
            folds=fold_results,
            rmse_stability=stability,
            market_source=final_market_source,
            market_snapshot_dates=final_snapshot_dates,
            promotion_gate=gate,
        )

    def _find_model_pkl(self, position: str) -> Optional[Path]:
        """Return pkl Path from v2_manifest.json, or None if missing/null."""
        manifest = Path("app/data/models/engine_b/v2_manifest.json")
        if not manifest.exists():
            return None
        data = json.loads(manifest.read_text())
        rel = data.get(position.upper())
        return Path(rel) if rel else None
