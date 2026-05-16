"""Offline TE archetype feature bake-off utilities for Phase 13.3.2."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.audit.te_archetype_taxonomy import derive_te_taxonomy_features

ALIGNMENT_VALUES = ("detached", "balanced", "inline", "taxonomy_missing")
ROLE_VALUES = (
    "receiving_specialist",
    "complete_te",
    "blocking_specialist",
    "role_risk",
    "unclear_role",
    "taxonomy_missing",
)
BASELINE_TE_FEATURES = (
    "ppg_t",
    "games_t",
    "age",
    "route_participation",
    "target_share_nfl",
    "yprr",
    "tprr",
    "weighted_opportunity",
    "snap_share",
)
OUTCOME_COLUMN = "avg_ppg_t1_t2"


def _canonical_by_gsis(eligible_rows: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(row["gsis_id"]): str(row["player_id"])
        for row in eligible_rows
        if row.get("gsis_id") and row.get("player_id")
    }


def _taxonomy_by_canonical(archetype_artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for player_id, row in archetype_artifact["players"].items():
        features = derive_te_taxonomy_features(row)
        if features["taxonomy_status"] == "labeled":
            out[player_id] = features
    return out


def build_te_bakeoff_frame(
    training: pd.DataFrame,
    archetype_artifact: dict[str, Any],
    *,
    eligible_rows: list[dict[str, Any]],
) -> pd.DataFrame:
    frame = training.copy()
    canonical_by_gsis = _canonical_by_gsis(eligible_rows)
    taxonomy_by_canonical = _taxonomy_by_canonical(archetype_artifact)

    alignments: list[str] = []
    roles: list[str] = []
    for gsis_player_id in frame["player_id"].astype(str):
        canonical = canonical_by_gsis.get(gsis_player_id)
        taxonomy = taxonomy_by_canonical.get(canonical or "")
        if taxonomy is None:
            alignments.append("taxonomy_missing")
            roles.append("taxonomy_missing")
            continue
        alignments.append(taxonomy["alignment_archetype"] or "taxonomy_missing")
        roles.append(taxonomy["fantasy_role_archetype"] or "taxonomy_missing")

    frame["alignment_archetype"] = alignments
    frame["fantasy_role_archetype"] = roles
    for value in ALIGNMENT_VALUES:
        frame[f"te_align_{value}"] = (frame["alignment_archetype"] == value).astype(int)
    for value in ROLE_VALUES:
        frame[f"te_role_{value}"] = (frame["fantasy_role_archetype"] == value).astype(int)
    return frame


def _prepare_matrix(train: pd.DataFrame, test: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, np.ndarray]:
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    x_train = imputer.fit_transform(train[columns])
    x_test = imputer.transform(test[columns])
    return scaler.fit_transform(x_train), scaler.transform(x_test)


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _evaluate_columns(frame: pd.DataFrame, columns: list[str], test_year: int) -> dict[str, Any]:
    train = frame[(frame["feature_season"] < test_year) & (frame["training_eligible"] == True)]
    test = frame[(frame["feature_season"] == test_year) & (frame["training_eligible"] == True)]
    x_train, x_test = _prepare_matrix(train, test, columns)
    y_train = train[OUTCOME_COLUMN].to_numpy(dtype=float)
    y_test = test[OUTCOME_COLUMN].to_numpy(dtype=float)
    model = Ridge(alpha=1.0)
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    return {
        "test_year": test_year,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "rmse": _rmse(y_test, pred),
        "mae": float(mean_absolute_error(y_test, pred)),
    }


def evaluate_te_taxonomy_candidate(
    frame: pd.DataFrame,
    *,
    candidate_name: str,
    candidate_columns: list[str],
    test_years: list[int],
) -> dict[str, Any]:
    baseline_columns = [column for column in BASELINE_TE_FEATURES if column in frame.columns]
    full_columns = baseline_columns + candidate_columns
    folds: list[dict[str, Any]] = []
    for test_year in test_years:
        baseline = _evaluate_columns(frame, baseline_columns, test_year)
        candidate = _evaluate_columns(frame, full_columns, test_year)
        folds.append(
            {
                "test_year": test_year,
                "n_train": baseline["n_train"],
                "n_test": baseline["n_test"],
                "baseline_rmse": round(baseline["rmse"], 4),
                "candidate_rmse": round(candidate["rmse"], 4),
                "rmse_delta": round(candidate["rmse"] - baseline["rmse"], 4),
                "baseline_mae": round(baseline["mae"], 4),
                "candidate_mae": round(candidate["mae"], 4),
                "mae_delta": round(candidate["mae"] - baseline["mae"], 4),
            }
        )
    rmse_deltas = [fold["rmse_delta"] for fold in folds]
    mae_deltas = [fold["mae_delta"] for fold in folds]
    rmse_delta_mean = round(float(np.mean(rmse_deltas)), 4)
    mae_delta_mean = round(float(np.mean(mae_deltas)), 4)
    improved_rmse_folds = int(sum(delta < 0 for delta in rmse_deltas))
    return {
        "candidate_name": candidate_name,
        "candidate_columns": candidate_columns,
        "folds": folds,
        "summary": {
            "rmse_delta_mean": rmse_delta_mean,
            "mae_delta_mean": mae_delta_mean,
            "improved_rmse_folds": improved_rmse_folds,
            "fold_count": len(folds),
            "passes_acceptance": (
                rmse_delta_mean < 0.0
                and mae_delta_mean < 0.0
                and improved_rmse_folds >= 3
            ),
        },
        "model_features_changed": False,
        "te_promotion_changed": False,
        "market_data_used": False,
    }
