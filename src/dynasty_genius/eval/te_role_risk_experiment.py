"""Controlled TE role-risk detector experiment for Phase 13.3.3."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.eval.te_archetype_bakeoff import BASELINE_TE_FEATURES

OUTCOME_COLUMN = "avg_ppg_t1_t2"
PRIMARY_ALPHA = 1.0
SENSITIVITY_ALPHA = 100.0
RANK_DEGRADATION_THRESHOLD = -0.02
ROLE_RISK_CANDIDATE_COLUMNS = (
    "te_role_role_risk",
    "te_role_blocking_specialist",
)
UNIFIED_PENALTY_COLUMN = "te_role_is_risk_profile"
ROLE_RISK_CANDIDATES = {
    "sparse_duo": ROLE_RISK_CANDIDATE_COLUMNS,
    "unified_penalty": (UNIFIED_PENALTY_COLUMN,),
}


def _prepare_matrix(
    train: pd.DataFrame,
    test: pd.DataFrame,
    columns: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    x_train = imputer.fit_transform(train[columns])
    x_test = imputer.transform(test[columns])
    return scaler.fit_transform(x_train), scaler.transform(x_test)


def _fit_predict(
    train: pd.DataFrame,
    test: pd.DataFrame,
    columns: list[str],
    alpha: float,
) -> tuple[np.ndarray, dict[str, float]]:
    x_train, x_test = _prepare_matrix(train, test, columns)
    y_train = train[OUTCOME_COLUMN].to_numpy(dtype=float)
    model = Ridge(alpha=alpha)
    model.fit(x_train, y_train)
    coefficients = {
        column: round(float(coef), 6)
        for column, coef in zip(columns, model.coef_)
    }
    return model.predict(x_test), coefficients


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _rank_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    spearman = float(spearmanr(y_true, y_pred)[0])
    kendall = float(kendalltau(y_true, y_pred)[0])
    return {
        "spearman_rho": 0.0 if np.isnan(spearman) else round(spearman, 4),
        "kendall_tau": 0.0 if np.isnan(kendall) else round(kendall, 4),
    }


def _evaluate_fold(
    frame: pd.DataFrame,
    test_year: int,
    baseline_columns: list[str],
    candidate_columns: list[str],
    alpha: float,
) -> dict[str, Any]:
    train = frame[
        (frame["feature_season"] < test_year) & (frame["training_eligible"] == True)  # noqa: E712
    ]
    test = frame[
        (frame["feature_season"] == test_year) & (frame["training_eligible"] == True)  # noqa: E712
    ]
    y_test = test[OUTCOME_COLUMN].to_numpy(dtype=float)
    baseline_pred, _ = _fit_predict(train, test, baseline_columns, alpha)
    candidate_pred, coefficients = _fit_predict(
        train,
        test,
        baseline_columns + candidate_columns,
        alpha,
    )
    baseline_rank = _rank_metrics(y_test, baseline_pred)
    candidate_rank = _rank_metrics(y_test, candidate_pred)
    return {
        "test_year": test_year,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "baseline_rmse": round(_rmse(y_test, baseline_pred), 4),
        "candidate_rmse": round(_rmse(y_test, candidate_pred), 4),
        "baseline_mae": round(float(mean_absolute_error(y_test, baseline_pred)), 4),
        "candidate_mae": round(float(mean_absolute_error(y_test, candidate_pred)), 4),
        "baseline_spearman_rho": baseline_rank["spearman_rho"],
        "candidate_spearman_rho": candidate_rank["spearman_rho"],
        "baseline_kendall_tau": baseline_rank["kendall_tau"],
        "candidate_kendall_tau": candidate_rank["kendall_tau"],
        "candidate_coefficients": {
            column: coefficients[column]
            for column in candidate_columns
        },
    }


def _with_unified_penalty(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out[UNIFIED_PENALTY_COLUMN] = (
        (out["te_role_role_risk"] == 1)
        | (out["te_role_blocking_specialist"] == 1)
    ).astype(int)
    return out


def _evaluate_candidate(
    frame: pd.DataFrame,
    *,
    candidate_name: str,
    candidate_columns: list[str],
    test_years: list[int],
    alpha: float,
) -> dict[str, Any]:
    baseline_columns = [column for column in BASELINE_TE_FEATURES if column in frame.columns]
    candidate_columns = [column for column in candidate_columns if column in frame.columns]
    folds: list[dict[str, Any]] = []
    for test_year in test_years:
        fold = _evaluate_fold(frame, test_year, baseline_columns, candidate_columns, alpha)
        fold["rmse_delta"] = round(fold["candidate_rmse"] - fold["baseline_rmse"], 4)
        fold["mae_delta"] = round(fold["candidate_mae"] - fold["baseline_mae"], 4)
        fold["spearman_delta"] = round(
            fold["candidate_spearman_rho"] - fold["baseline_spearman_rho"],
            4,
        )
        fold["kendall_delta"] = round(
            fold["candidate_kendall_tau"] - fold["baseline_kendall_tau"],
            4,
        )
        folds.append(fold)

    rmse_deltas = [fold["rmse_delta"] for fold in folds]
    mae_deltas = [fold["mae_delta"] for fold in folds]
    spearman_deltas = [fold["spearman_delta"] for fold in folds]
    kendall_deltas = [fold["kendall_delta"] for fold in folds]
    rmse_win_folds = sum(delta < 0 for delta in rmse_deltas)
    candidate_coefficients: dict[str, float] = {}
    for fold in folds:
        for column, coefficient in fold["candidate_coefficients"].items():
            candidate_coefficients.setdefault(column, 0.0)
            candidate_coefficients[column] += coefficient
    candidate_coefficients = {
        column: round(value / len(folds), 6)
        for column, value in candidate_coefficients.items()
    }

    mean_rmse_gate = float(np.mean(rmse_deltas)) < 0
    mean_mae_gate = float(np.mean(mae_deltas)) < 0
    rmse_win_gate = rmse_win_folds >= 3
    rank_degradation_gate = (
        min(spearman_deltas) >= RANK_DEGRADATION_THRESHOLD
        and min(kendall_deltas) >= RANK_DEGRADATION_THRESHOLD
    )
    negative_coefficient_gate = all(value < 0.0 for value in candidate_coefficients.values())
    acceptance = {
        "rmse_win_gate": rmse_win_gate,
        "mean_rmse_gate": mean_rmse_gate,
        "mean_mae_gate": mean_mae_gate,
        "rank_degradation_gate": rank_degradation_gate,
        "rank_degradation_threshold": RANK_DEGRADATION_THRESHOLD,
        "negative_coefficient_gate": negative_coefficient_gate,
    }
    passes_acceptance = all([
        rmse_win_gate,
        mean_rmse_gate,
        mean_mae_gate,
        rank_degradation_gate,
        negative_coefficient_gate,
    ])

    return {
        "candidate_name": candidate_name,
        "candidate_columns": candidate_columns,
        "folds": folds,
        "summary": {
            "fold_count": len(folds),
            "rmse_win_folds": int(rmse_win_folds),
            "rmse_delta_mean": round(float(np.mean(rmse_deltas)), 4),
            "mae_delta_mean": round(float(np.mean(mae_deltas)), 4),
            "spearman_delta_mean": round(float(np.mean(spearman_deltas)), 4),
            "kendall_delta_mean": round(float(np.mean(kendall_deltas)), 4),
            "candidate_coefficients": candidate_coefficients,
            "passes_acceptance": passes_acceptance,
        },
        "acceptance": acceptance,
    }


def evaluate_te_role_risk_experiment(
    frame: pd.DataFrame,
    *,
    test_years: list[int],
) -> dict[str, Any]:
    experiment_frame = _with_unified_penalty(frame)
    candidates = {
        name: _evaluate_candidate(
            experiment_frame,
            candidate_name=name,
            candidate_columns=list(columns),
            test_years=test_years,
            alpha=PRIMARY_ALPHA,
        )
        for name, columns in ROLE_RISK_CANDIDATES.items()
    }
    alpha_sensitivity = {
        name: _evaluate_candidate(
            experiment_frame,
            candidate_name=name,
            candidate_columns=list(columns),
            test_years=test_years,
            alpha=SENSITIVITY_ALPHA,
        )["summary"]
        for name, columns in ROLE_RISK_CANDIDATES.items()
    }
    return {
        "experiment_name": "te_role_risk_detector",
        "primary_alpha": PRIMARY_ALPHA,
        "alpha_sensitivity": {
            "sensitivity_alpha": SENSITIVITY_ALPHA,
            "candidate_summaries": alpha_sensitivity,
        },
        "candidates": candidates,
        "governance": {
            "diagnostic_only": True,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
            "pff_grades_used": False,
            "player_level_rows_emitted": False,
        },
    }
