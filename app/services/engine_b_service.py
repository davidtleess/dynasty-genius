"""Engine B Service Layer — Phase 6 (v2 position routing + v1 fallback).

Loads v2 per-position artifacts when promoted (QB, RB, WR).
Falls back to the v1 unified model for positions not yet promoted (TE).
The TE experimental caveat remains until te_v2.pkl passes its promotion gate.
"""
from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.impute import SimpleImputer

from src.dynasty_genius.features.feature_source import resolve_feature_source
from src.dynasty_genius.features.inference_partition import (
    player_key,
    select_inference_partition,
)
from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_EXPERIMENTAL_POSITIONS,
    validate_no_prohibited_features,
    validate_no_temporal_leakage,
)

_ROOT = Path(__file__).resolve().parents[2]

logger = logging.getLogger(__name__)
_MODELS_DIR = _ROOT / "app" / "data" / "models" / "engine_b"
_RUNS_DIR = _MODELS_DIR / "runs"
_DATASET_PATH = _ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
_FEATURES_RUNTIME_DIR = _ROOT / "app" / "data" / "features_runtime"
_V2_MANIFEST_PATH = _MODELS_DIR / "v2_manifest.json"


def _validate_bundle(bundle: dict[str, Any], source: str) -> bool:
    features = bundle.get("features", [])
    try:
        validate_no_prohibited_features(features)
        validate_no_temporal_leakage(features)
        return True
    except ValueError as e:
        # H0-0c (finding F3): structured logging, never print — a violating
        # bundle is refused and the refusal must be observable.
        logger.error(
            "Engine B contract violation in %s: %s",
            source,
            e,
            extra={"source": source},
        )
        return False


class EngineBManifestUnavailableError(RuntimeError):
    """The v2 manifest could not be resolved, so the served model set is unknown.

    David's ruling, 2026-08-31, verbatim: "if the model can't read the file, then it
    needs to be a hard error."

    Refusing is the whole point. This class of failure previously resolved to ``{}`` and
    fell through ``self._v2_bundles.get(position) or self._v1_bundle`` to the SUPERSEDED
    v1 model, silently, for every position -- which is how the land gate spent weeks
    validating tickets against a build the repo documents as not beating a naive
    baseline. Nothing errored, nothing logged where anyone read it, and the answers were
    simply worse.

    NOT raised when the manifest is readable and simply does not promote a position:
    ``train_engine_b`` writes entries only for promoted positions, so a ``None`` there is
    a deliberate statement that v1 is the right model for it. That fallback is by design
    and survives.
    """


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
        # Set AFTER the loads, not before: a raise here must not leave a half-loaded
        # singleton that answers every later call from an empty v2 map -- which would
        # silently reinstate the exact v1 fallback this refusal exists to prevent.
        v2 = self._load_v2_bundles()
        v1 = self._load_v1_bundle()
        self._v2_bundles = v2
        self._v1_bundle = v1
        self._loaded = True

    def _load_v2_bundles(self) -> dict[str, Any]:
        if not _V2_MANIFEST_PATH.exists():
            raise EngineBManifestUnavailableError(
                f"Engine B v2 manifest not found at {_V2_MANIFEST_PATH}; refusing to "
                "serve rather than silently falling back to the superseded v1 model."
            )
        try:
            with open(_V2_MANIFEST_PATH) as f:
                manifest: dict[str, str | None] = json.load(f)
        except Exception as e:
            raise EngineBManifestUnavailableError(
                f"Engine B v2 manifest at {_V2_MANIFEST_PATH} could not be read: {e}; "
                "refusing to serve rather than silently falling back to v1."
            ) from e

        bundles: dict[str, Any] = {}
        for pos, artifact_path in manifest.items():
            if artifact_path is None:
                continue
            full_path = _ROOT / artifact_path
            if not full_path.exists():
                raise EngineBManifestUnavailableError(
                    f"Engine B v2 manifest promotes {pos} to {artifact_path}, which does "
                    "not exist. A manifest naming a model that is not on disk is a broken "
                    "deployment, not a reason to serve v1."
                )
            try:
                with open(full_path, "rb") as f:
                    bundle = pickle.load(f)
            except Exception as e:
                raise EngineBManifestUnavailableError(
                    f"Engine B v2 artifact for {pos} at {full_path} could not be loaded: "
                    f"{e}; refusing to serve rather than falling back to v1."
                ) from e
            if not _validate_bundle(bundle, str(full_path)):
                raise EngineBManifestUnavailableError(
                    f"Engine B v2 artifact for {pos} at {full_path} failed validation; "
                    "refusing to serve rather than falling back to v1."
                )
            bundles[pos] = bundle
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
            logger.error("Engine B: failed to load v1 bundle: %s", e)
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

    def score_inference_partition(self, feature_source=None) -> list[dict[str, Any]]:
        """Score the inference partition — one prediction per player — routing by position.

        Reads the feature CSV through the shared resolver (published runtime when
        available, else the committed seed). A caller may inject an already-resolved
        ``feature_source`` so a single resolution backs both the rows and the predictions.

        The partition is the assembler's inference SEASON, selected by the shared
        ``select_inference_partition`` (DG-133). It is not "every row that cannot
        train": since the attrition fix that set also holds complete-window washout
        rows from earlier seasons, and scoring those produced a second, different
        prediction for 29 players every morning.

        Fails closed: a present table that is empty, lacks a season column, carries a
        training row in the inference season or repeats a player raises
        ``InferencePartitionError`` (a ``ValueError`` whose message is a bare token)
        rather than returning a partial list. Only an ABSENT table returns ``[]``. A
        row with no ``player_id`` is skipped, as the producer skips it: it can never
        be joined to anything, and two of them are not the same player twice.
        """
        if feature_source is None:
            if not _DATASET_PATH.exists() and not (
                _FEATURES_RUNTIME_DIR / "engine_b_features_runtime.csv"
            ).exists():
                return []
            feature_source = resolve_feature_source(
                seed_path=_DATASET_PATH, runtime_dir=_FEATURES_RUNTIME_DIR
            )

        df = pd.read_csv(feature_source.path)
        inference_df = select_inference_partition(df)

        predictions = []
        for _, row in inference_df.iterrows():
            player_features = row.to_dict()
            if player_key(player_features.get("player_id")) is None:
                continue
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


def score_inference_partition(feature_source=None) -> list[dict]:
    return service.score_inference_partition(feature_source=feature_source)
