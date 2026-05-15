"""WalkForwardDriver — expanding-window walk-forward evaluation of Engine B v2.

Task 10.3 (partial): _build_fold_data + _get_feature_columns.
Full driver (run(), metrics, gates) added in Tasks 10.5, 10.7, 10.8.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_FEATURES_BY_POSITION,
    OUTCOME_COLUMN,
    validate_no_temporal_leakage,
    validate_no_prohibited_features,
)

CSV_PATH = Path("app/data/training/engine_b_features_v2.csv")

_METADATA_COLS: frozenset[str] = frozenset({
    "player_id", "position", "feature_season", "team",
    "depth_chart_position", "aging_curve_position",
    "training_eligible", OUTCOME_COLUMN,
    # Component outcome columns — must never enter X
    "ppg_t1", "ppg_t2", "games_t1", "games_t2",
})


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

    FIXED_ALPHA: dict[str, float] = {"QB": 1000.0, "RB": 500.0, "WR": 200.0}

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
