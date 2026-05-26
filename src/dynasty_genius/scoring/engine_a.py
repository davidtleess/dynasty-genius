"""Engine A scorer — rookie forecast Ridge model.

Loads the trained per-position Ridge models (pick, round, age → y24_ppg) from
the latest model run and normalizes predictions to a 0-100 dynasty_value_score.

Fires only for prospects (is_prospect=True) when pick, round, and age are all
present. Veterans remain PRE_MODEL until Engine B is trained.

Normalization: y24_ppg / POSITION_P90_PPG * 100, clamped to [0, 100].
p90 is derived from the full training distribution (see train_models.py stats).
A first-round elite pick scores ~80-100; late-round speculative picks score 0-30.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = ROOT / "app" / "data" / "models"
LATEST_POINTER = MODELS_DIR / "latest.json"
V3_MANIFEST_POINTER = MODELS_DIR / "head_a" / "v3_manifest.json"

# p90 of y24_ppg from the full training distribution (prospects_with_outcomes.csv).
# Used as the soft ceiling for dynasty_value_score normalization.
# Elite-range picks (~top 5) score 80-100; p90 picks score exactly 80.
_P90_PPG: dict[str, float] = {
    "WR": 12.7,
    "RB": 14.6,
    "TE": 9.1,
    "QB": 16.7,
}

# Public, governed alias of the Engine-A training P90 PPG ceilings, so downstream
# governed consumers (e.g. the draft-pick value curve) need not import a private name.
ENGINE_A_P90_PPG: dict[str, float] = dict(_P90_PPG)

# model_grade propagated from the validation report. QB is D (negative R²).
_ENGINE_A_GRADES: dict[str, str] = {
    "WR": "PROSPECT_C",
    "RB": "PROSPECT_C",
    "TE": "PROSPECT_C",
    "QB": "PROSPECT_D",
}

# Caveats added to every Engine A card, beyond the per-position ones from
# the validation report. These clarify scope: Engine A is a prospect-only,
# draft-capital model — it does not score veteran careers.
_UNIVERSAL_CAVEATS = [
    "engine_a_rookie_forecast_only",
    "veteran_scoring_requires_engine_b",
    "no_usage_efficiency_signal",
]

_POSITION_CAVEATS: dict[str, list[str]] = {
    "QB": ["qb_rookie_signal_inherently_low_ceiling", "low_sample_holdout", "negative_r2_lower_bound"],
    "RB": ["rb_career_arc_capped_by_aging_cliff", "low_sample_holdout"],
    "TE": ["te_population_per_class_small", "low_sample_holdout"],
    "WR": [],
}


class EngineAScorer:
    """Loads Engine A artifacts once and scores prospects on demand."""

    def __init__(self) -> None:
        self._models: dict[str, object] = {}
        self._version: Optional[str] = None
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        if not LATEST_POINTER.exists():
            raise FileNotFoundError(f"Engine A model pointer not found: {LATEST_POINTER}")
        pointer = json.loads(LATEST_POINTER.read_text())
        self._version = pointer["model_version"]
        run_dir = ROOT / pointer["run_dir"]
        for pos in _ENGINE_A_GRADES:
            artifact = run_dir / f"{pos}_model.pkl"
            if not artifact.exists():
                raise FileNotFoundError(f"Engine A artifact missing: {artifact}")
            with open(artifact, "rb") as f:
                self._models[pos] = pickle.load(f)
        self._loaded = True

    def score(
        self,
        position: str,
        pick: float,
        round_: float,
        age: float,
    ) -> Optional[dict]:
        """Score a prospect and return a dict ready to merge into PVO fields.

        Returns None if position is not supported by Engine A.
        """
        pos = position.upper()
        if pos not in _ENGINE_A_GRADES:
            return None

        self._load()
        model = self._models[pos]
        X = np.array([[pick, round_, age]])
        y24_ppg = float(model.predict(X)[0])

        p90 = _P90_PPG[pos]
        raw_score = max(0.0, y24_ppg) / p90 * 100.0
        dynasty_value_score = round(min(100.0, raw_score), 2)

        caveats = list(_UNIVERSAL_CAVEATS) + list(_POSITION_CAVEATS.get(pos, []))

        return {
            "dynasty_value_score": dynasty_value_score,
            "engine_used": "engine_a_rookie_forecast_ridge",
            "model_version": self._version,
            "model_grade": _ENGINE_A_GRADES[pos],
            "y24_ppg_raw": round(y24_ppg, 4),
            "caveats": caveats,
        }


# Module-level singleton — loaded once, reused across all assemble_pvo calls.
_scorer = EngineAScorer()


def score_prospect(
    position: str,
    pick: float,
    round_: float,
    age: float,
) -> Optional[dict]:
    """Public interface. Returns scoring dict or None if unsupported position."""
    return _scorer.score(position, pick, round_, age)


# ── Engine A v3: TE Head A Ridge (Phase 19 W5) ───────────────────────────────

# Features required by the v3 model for each position, in prediction order.
# Only positions listed here have a v3 contract.
HEAD_A_V3_FEATURE_CONTRACTS: dict[str, list[str]] = {
    "TE": [
        "nfl_pick",
        "nfl_round",
        "final_college_age",
        "te_ryptpa_final",
        "te_yards_per_reception_career",
    ],
}

_ENGINE_A_V3_GRADES: dict[str, str] = {
    "TE": "PROSPECT_C",
}


class EngineAV3Scorer:
    """Loads v3 Head A artifacts once per manifest entry and scores on demand.

    Silently returns None on any missing artifact — this allows CI to run
    without requiring the gitignored pkl to be present.
    """

    def __init__(self) -> None:
        self._models: dict[str, object] = {}
        self._loaded = False

    def _load(self) -> bool:
        if self._loaded:
            return True
        if not V3_MANIFEST_POINTER.exists():
            return False
        manifest = json.loads(V3_MANIFEST_POINTER.read_text())
        for pos, pkl_path_str in manifest.items():
            pkl_path = Path(pkl_path_str)
            if not pkl_path.is_absolute():
                pkl_path = ROOT / pkl_path
            if not pkl_path.exists():
                continue
            with open(pkl_path, "rb") as f:
                self._models[pos] = pickle.load(f)
        self._loaded = True
        return True

    def score(self, position: str, features: dict) -> Optional[dict]:
        pos = position.upper()
        contract = HEAD_A_V3_FEATURE_CONTRACTS.get(pos)
        if contract is None:
            return None

        # All required features must be present and non-None.
        for feat in contract:
            if features.get(feat) is None:
                return None

        if not self._load():
            return None

        model = self._models.get(pos)
        if model is None:
            return None

        X = np.array([[features[feat] for feat in contract]])
        y_ppg = float(model.predict(X)[0])

        p90 = _P90_PPG[pos]
        raw_score = max(0.0, y_ppg) / p90 * 100.0
        dynasty_value_score = round(min(100.0, raw_score), 2)

        caveats = (
            ["head_a_v3_college_features_used"]
            + list(_UNIVERSAL_CAVEATS)
            + list(_POSITION_CAVEATS.get(pos, []))
        )

        return {
            "dynasty_value_score": dynasty_value_score,
            "engine_used": "engine_a_v3_head_a_ridge",
            "model_version": "head_a_te_v3_ridge",
            "model_grade": _ENGINE_A_V3_GRADES[pos],
            "y24_ppg_raw": round(y_ppg, 4),
            "caveats": caveats,
        }


_v3_scorer = EngineAV3Scorer()


def score_prospect_v3(position: str, features: dict) -> Optional[dict]:
    """Score a TE prospect using the v3 Head A Ridge model.

    Returns None when:
    - position has no v3 contract (WR/RB/QB)
    - any required college feature is absent or None
    - v3_manifest.json does not exist (CI / pre-promotion environments)
    - the position pkl is missing from the manifest
    """
    return _v3_scorer.score(position, features)
