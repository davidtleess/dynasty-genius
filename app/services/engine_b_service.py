"""Engine B Service Layer — Phase 6 (v2 position routing + v1 fallback).

Loads v2 per-position artifacts when promoted (QB, RB, WR).
Falls back to the v1 unified model for positions not yet promoted (TE).
The TE experimental caveat remains until te_v2.pkl passes its promotion gate.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.impute import SimpleImputer

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_EXPERIMENTAL_POSITIONS,
    validate_no_prohibited_features,
    validate_no_temporal_leakage,
)

_ROOT = Path(__file__).resolve().parents[2]
_MODELS_DIR = _ROOT / "app" / "data" / "models" / "engine_b"
_RUNS_DIR = _MODELS_DIR / "runs"
_DATASET_PATH = _ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
_V2_MANIFEST_PATH = _MODELS_DIR / "v2_manifest.json"


def _validate_bundle(bundle: dict[str, Any], source: str) -> bool:
    features = bundle.get("features", [])
    try:
        validate_no_prohibited_features(features)
        validate_no_temporal_leakage(features)
        return True
    except ValueError as e:
        print(f"CRITICAL: Engine B contract violation in {source}: {e}")
        return False


class EngineBService:
    _instance = None
    _loaded: bool = False
    _v2_bundles: dict[str, Any]
    _v1_bundle: dict[str, Any]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
            cls._instance._v2_bundles = {}
            cls._instance._v1_bundle = {}
        return cls._instance

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load v2 per-position bundles and v1 fallback. Idempotent."""
        if self._loaded:
            return
        self._loaded = True
        self._v2_bundles = self._load_v2_bundles()
        self._v1_bundle = self._load_v1_bundle()

    def _load_v2_bundles(self) -> dict[str, Any]:
        if not _V2_MANIFEST_PATH.exists():
            return {}
        try:
            with open(_V2_MANIFEST_PATH) as f:
                manifest: dict[str, str | None] = json.load(f)
        except Exception as e:
            print(f"Engine B: failed to read v2 manifest: {e}")
            return {}

        bundles: dict[str, Any] = {}
        for pos, artifact_path in manifest.items():
            if artifact_path is None:
                continue
            full_path = _ROOT / artifact_path
            if not full_path.exists():
                print(f"Engine B: v2 artifact missing for {pos}: {full_path}")
                continue
            try:
                with open(full_path, "rb") as f:
                    bundle = pickle.load(f)
                if _validate_bundle(bundle, str(full_path)):
                    bundles[pos] = bundle
            except Exception as e:
                print(f"Engine B: failed to load v2 artifact for {pos}: {e}")
        return bundles

    def _load_v1_bundle(self) -> dict[str, Any]:
        if not _RUNS_DIR.exists():
            return {}
        runs = sorted([
            d for d in _RUNS_DIR.iterdir()
            if d.is_dir() and (d / "engine_b_v1.pkl").exists()
        ])
        if not runs:
            return {}
        model_path = runs[-1] / "engine_b_v1.pkl"
        if not model_path.exists():
            return {}
        try:
            with open(model_path, "rb") as f:
                bundle = pickle.load(f)
            if _validate_bundle(bundle, str(model_path)):
                return bundle
        except Exception as e:
            print(f"Engine B: failed to load v1 bundle: {e}")
        return {}

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict_player_season(self, player_features: dict[str, Any]) -> dict[str, Any]:
        """Score one player-season, routing to the correct v2 model or v1 fallback."""
        self._load()

        position = player_features.get("position", "UNKNOWN")
        uses_v2_bundle = position in self._v2_bundles
        bundle = self._v2_bundles.get(position) or self._v1_bundle

        if not bundle:
            return {"error": "model_not_found"}

        model = bundle["model"]
        imputer: SimpleImputer = bundle["imputer"]
        features: list[str] = bundle["features"]
        engine_version: str = bundle.get("version", "engine_b_v1")

        row_dict = {f: player_features.get(f) for f in features}
        df_row = pd.DataFrame([row_dict])

        X = imputer.transform(df_row)
        prediction = float(model.predict(X)[0])

        is_experimental = (
            position in ENGINE_B_EXPERIMENTAL_POSITIONS
            or not uses_v2_bundle
        )
        caveats = ["engine_b_not_decision_grade"]
        if is_experimental:
            caveats.append("engine_b_does_not_beat_baseline_for_this_position")

        return {
            "predicted_avg_ppg_t1_t2": round(prediction, 3),
            "engine": engine_version,
            "feature_season": player_features.get("feature_season"),
            "position": position,
            "decision_supported": False,
            "experimental": is_experimental,
            "caveats": caveats,
        }

    def score_inference_partition(self) -> list[dict[str, Any]]:
        """Score all 2024 inference rows, routing each by position."""
        if not _DATASET_PATH.exists():
            return []

        df = pd.read_csv(_DATASET_PATH)
        inference_df = df[df["training_eligible"] == False].copy()  # noqa: E712 - preserve pandas mask semantics (CSV bool/int/object dtype)

        predictions = []
        for _, row in inference_df.iterrows():
            player_features = row.to_dict()
            pred = self.predict_player_season(player_features)
            if "error" in pred:
                continue
            pred["player_id"] = player_features.get("player_id")
            pred["team"] = player_features.get("team")
            predictions.append(pred)

        predictions.sort(key=lambda x: x.get("predicted_avg_ppg_t1_t2", 0), reverse=True)
        return predictions


# ── Module-level convenience functions ───────────────────────────────────────

service = EngineBService()


def predict_player_season(player_features: dict) -> dict:
    return service.predict_player_season(player_features)


def score_inference_partition() -> list[dict]:
    return service.score_inference_partition()
