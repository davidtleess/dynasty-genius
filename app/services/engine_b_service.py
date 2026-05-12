"""Engine B Service Layer.

Provides active-player forecasting by surfacing Engine B predictions.
Loads the latest trained model and scores the inference partition.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_EXPERIMENTAL_POSITIONS,
    validate_no_temporal_leakage,
    validate_no_prohibited_features
)

_ROOT = Path(__file__).resolve().parents[2]
_MODELS_DIR = _ROOT / "app" / "data" / "models" / "engine_b" / "runs"
_DATASET_PATH = _ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"

class EngineBService:
    _instance = None
    _model_bundle = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EngineBService, cls).__new__(cls)
        return cls._instance

    def _load_model(self) -> dict[str, Any]:
        """Lazy-load the latest Engine B artifact and validate its contract."""
        if self._model_bundle is not None:
            return self._model_bundle

        if not _MODELS_DIR.exists():
            return {}

        # Find the latest timestamped directory
        runs = sorted([d for d in _MODELS_DIR.iterdir() if d.is_dir()])
        if not runs:
            return {}

        latest_run = runs[-1]
        model_path = latest_run / "engine_b_v1.pkl"
        
        if not model_path.exists():
            return {}

        with open(model_path, "rb") as f:
            bundle = pickle.load(f)
            
        # Fail-closed: reject any artifact whose feature list violates the
        # current contract. Guards against loading a stale pre-fix artifact.
        features = bundle.get("features", [])
        try:
            validate_no_prohibited_features(features)
            validate_no_temporal_leakage(features)
        except ValueError as e:
            print(f"CRITICAL: Engine B model contract violation in {model_path}: {e}")
            return {}

        self._model_bundle = bundle
        return self._model_bundle

    def predict_player_season(self, player_features: dict[str, Any]) -> dict[str, Any]:
        """Generate prediction for a single player-season."""
        bundle = self._load_model()
        if not bundle:
            return {"error": "model_not_found"}

        model: Ridge = bundle["model"]
        imputer: SimpleImputer = bundle["imputer"]
        features: list[str] = bundle["features"]

        # Build single-row DataFrame
        # Ensure all required features exist, filling missing with NaN for imputer
        row_dict = {f: player_features.get(f) for f in features}
        df_row = pd.DataFrame([row_dict])

        # Impute and Predict
        X = imputer.transform(df_row)
        prediction = model.predict(X)[0]

        position = player_features.get("position", "UNKNOWN")
        is_experimental = position in ENGINE_B_EXPERIMENTAL_POSITIONS
        
        caveats = ["engine_b_mvp_not_decision_grade"]
        if is_experimental:
            caveats.append("engine_b_does_not_beat_baseline_for_this_position")

        return {
            "predicted_avg_ppg_t1_t2": round(float(prediction), 3),
            "engine": "engine_b_v1",
            "feature_season": player_features.get("feature_season"),
            "position": position,
            "decision_supported": False,
            "experimental": is_experimental,
            "caveats": caveats,
        }

    def score_inference_partition(self) -> list[dict[str, Any]]:
        """Score the 2024 rows for active-player forecasting."""
        if not _DATASET_PATH.exists():
            return []

        df = pd.read_csv(_DATASET_PATH)
        # 2024 rows are flagged as training_eligible=False
        inference_df = df[df["training_eligible"] == False].copy()
        
        predictions = []
        for _, row in inference_df.iterrows():
            # Convert row to dict
            player_features = row.to_dict()
            pred = self.predict_player_season(player_features)
            if "error" in pred:
                continue
            
            # Enrich with identity for display
            pred["player_id"] = player_features.get("player_id")
            pred["team"] = player_features.get("team")
            predictions.append(pred)
            
        # Sort by predicted value descending
        predictions.sort(key=lambda x: x.get("predicted_avg_ppg_t1_t2", 0), reverse=True)
        return predictions

# Singleton instance access
service = EngineBService()

def predict_player_season(player_features: dict) -> dict:
    return service.predict_player_season(player_features)

def score_inference_partition() -> list[dict]:
    return service.score_inference_partition()
