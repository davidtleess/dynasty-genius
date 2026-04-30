import pickle
from pathlib import Path

import numpy as np

MODELS_DIR = Path(__file__).resolve().parents[2] / "app" / "data" / "models"
POSITIONS = ["WR", "RB", "TE", "QB"]

TIER_THRESHOLDS = [
    (14.0, "Elite"),
    (10.0, "Starter"),
    (6.0,  "Depth"),
    (0.0,  "Bust"),
]

CONFIDENCE_THRESHOLDS = [
    (32,  "High"),
    (96,  "Medium"),
    (None, "Low"),
]


def _load_models() -> dict:
    models = {}
    for pos in POSITIONS:
        path = MODELS_DIR / f"{pos}_model.pkl"
        if not path.exists():
            raise FileNotFoundError(
                f"Model file not found: {path}. Run train_models.py first."
            )
        with open(path, "rb") as f:
            models[pos] = pickle.load(f)
    return models


_MODELS = _load_models()


def _dynasty_tier(ppg: float) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if ppg >= threshold:
            return tier
    return "Bust"


def _confidence(pick: int) -> str:
    for threshold, label in CONFIDENCE_THRESHOLDS:
        if threshold is None or pick <= threshold:
            return label
    return "Low"


def score_prospect(position: str, pick: int, round_num: int, age: float) -> dict:
    if position not in _MODELS:
        raise ValueError(f"Unsupported position: {position}. Must be one of {POSITIONS}.")

    model = _MODELS[position]
    X = np.array([[pick, round_num, age]])
    predicted = max(float(model.predict(X)[0]), 0.0)
    ppg = round(predicted, 2)

    return {
        "position":          position,
        "pick":              pick,
        "round":             round_num,
        "age":               age,
        "predicted_y24_ppg": ppg,
        "dynasty_tier":      _dynasty_tier(ppg),
        "confidence":        _confidence(pick),
    }


def score_draft_class(prospects: list[dict]) -> list[dict]:
    results = []
    for p in prospects:
        result = score_prospect(
            position=p["position"],
            pick=p["pick"],
            round_num=p["round"],
            age=p["age"],
        )
        result["name"] = p["name"]
        results.append(result)

    results.sort(key=lambda r: r["predicted_y24_ppg"], reverse=True)
    return results
