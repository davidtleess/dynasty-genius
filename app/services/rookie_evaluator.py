from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np

from app.models.valuation import DynastyValuation, ValuationEngine

MODELS_DIR = Path(__file__).resolve().parents[2] / "app" / "data" / "models"
LATEST_POINTER = MODELS_DIR / "latest.json"
POSITIONS = ["WR", "RB", "TE", "QB"]

TIER_THRESHOLDS = [
    (14.0, "Elite"),
    (10.0, "Starter"),
    (6.0,  "Depth"),
    (0.0,  "Bust"),
]

DEFAULT_MODEL_VERSION = "unversioned"
DISPLAY_PRECISION = 1
HORIZON_YEARS = 3
SIGNAL_COMPLETENESS = "draft_capital_only"
PROVISIONAL_DYNASTY_VALUE_NOTE = (
    "dynasty_value_score is provisional pre-normalization Engine A output"
)
PROVISIONAL_DRIVERS_NOTE = (
    "top_drivers and per-prospect risk_flags are provisional this iteration"
)
DRIVER_ATTRIBUTION_NOTE = (
    "top_drivers are provisional Ridge coefficient attributions."
)
DRIVER_CENTERING_NOTE = (
    "top_drivers use coef x (feature - position_mean); positive direction means "
    "the prospect feature is better than the position training-set average."
)
DRAFT_CAPITAL_DRIVER_NOTE = (
    "pick and round are combined as draft_capital because they are collinear."
)
CLASS_RANK_NOTE = (
    "class_overall_rank does not yet account for positional scarcity."
)


def _latest_model_dir() -> Path | None:
    if not LATEST_POINTER.exists():
        return None

    pointer = json.loads(LATEST_POINTER.read_text())
    run_dir = pointer.get("run_dir")
    if not run_dir:
        return None

    return Path(__file__).resolve().parents[2] / run_dir


def _latest_pointer() -> dict:
    if not LATEST_POINTER.exists():
        return {}
    return json.loads(LATEST_POINTER.read_text())


def _load_validation_report(pointer: dict) -> dict:
    report_path = pointer.get("validation_report")
    if not report_path:
        return {}

    path = Path(__file__).resolve().parents[2] / report_path
    if not path.exists():
        return {}

    report = json.loads(path.read_text())
    per_position = report.get("per_position")
    if isinstance(per_position, dict):
        return per_position
    return {
        item["position"]: item
        for item in report.get("positions", [])
        if "position" in item
    }


def _load_models() -> tuple[dict, dict]:
    models = {}
    metadata = {}
    model_dir = _latest_model_dir() or MODELS_DIR

    for pos in POSITIONS:
        path = model_dir / f"{pos}_model.pkl"
        if not path.exists():
            raise FileNotFoundError(
                f"Model file not found: {path}. Run train_models.py first."
            )
        with open(path, "rb") as f:
            models[pos] = pickle.load(f)

        metadata_path = model_dir / f"{pos}_metadata.json"
        if metadata_path.exists():
            metadata[pos] = json.loads(metadata_path.read_text())
    return models, metadata


_MODELS, _MODEL_METADATA = _load_models()
_LATEST_POINTER = _latest_pointer()
_VALIDATION_BY_POSITION = _load_validation_report(_LATEST_POINTER)


def _dynasty_tier(ppg: float) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if ppg >= threshold:
            return tier
    return "Bust"


def _model_version(position: str) -> str:
    return (
        _LATEST_POINTER.get("model_version")
        or _MODEL_METADATA.get(position, {}).get("model_version")
        or DEFAULT_MODEL_VERSION
    )


def _validation_metadata(position: str) -> dict:
    report_metrics = _VALIDATION_BY_POSITION.get(position, {})
    metadata_metrics = _MODEL_METADATA.get(position, {}).get("metrics", {})
    rmse = report_metrics.get("rmse", metadata_metrics.get("rmse"))
    r2 = report_metrics.get("r2", metadata_metrics.get("r2"))
    spearman = report_metrics.get("spearman_rank_correlation")
    top_12_hit_rate = report_metrics.get("top_12_hit_rate")
    bust_avoidance_rate = report_metrics.get("bust_avoidance_rate")
    holdout_rows = report_metrics.get(
        "holdout_rows", _MODEL_METADATA.get(position, {}).get("holdout_rows")
    )
    model_grade = report_metrics.get("model_grade", "unvalidated")
    caveats = report_metrics.get("caveats", [])

    return {
        "model_grade": model_grade,
        "rmse_position_holdout": rmse,
        "r2_position_holdout": r2,
        "spearman_rank_correlation": spearman,
        "top_12_hit_rate": top_12_hit_rate,
        "bust_avoidance_rate": bust_avoidance_rate,
        "holdout_rows": holdout_rows,
        "position_ceiling": report_metrics.get("position_ceiling"),
        "coverage_80": report_metrics.get("coverage_80"),
        "caveats": caveats,
        "validation_source": _LATEST_POINTER.get("validation_report"),
    }


def _threshold_flags(position: str, pick: int, age: float) -> dict:
    age_line = {"RB": 23.0, "WR": 23.0, "TE": 24.0, "QB": 24.0}.get(position)
    return {
        "draft_capital_top_32": pick <= 32,
        "draft_capital_top_64": pick <= 64,
        "age_below_position_line": None if age_line is None else age <= age_line,
        "dominator_above_position_line": None,
        "ras_above_8": None,
        "yprr_above_position_line": None,
    }


def _counter_argument() -> str:
    return (
        "Score is driven by draft capital and age only; RAS, college production, "
        "and market overlays are not ingested yet."
    )


def _direction(contribution: float) -> str:
    if contribution > 0:
        return "positive"
    if contribution < 0:
        return "negative"
    return "neutral"


def _display_contribution(contribution: float) -> float:
    rounded = round(contribution, DISPLAY_PRECISION)
    return 0.0 if rounded == 0 else rounded


def _top_drivers(position: str, pick: int, round_num: int, age: float) -> list[dict]:
    metadata = _MODEL_METADATA.get(position, {})
    coefficients = metadata.get("coefficients", {})
    feature_means = metadata.get("feature_means", {})

    draft_capital = (
        float(coefficients.get("pick", 0.0))
        * (pick - float(feature_means.get("pick", pick)))
        + float(coefficients.get("round", 0.0))
        * (round_num - float(feature_means.get("round", round_num)))
    )
    age_term = float(coefficients.get("age", 0.0)) * (
        age - float(feature_means.get("age", age))
    )

    draft_capital_display = _display_contribution(draft_capital)
    age_display = _display_contribution(age_term)

    drivers = [
        {
            "feature": "draft_capital",
            "contribution": draft_capital_display,
            "direction": _direction(draft_capital_display),
        },
        {
            "feature": "age_at_entry",
            "contribution": age_display,
            "direction": _direction(age_display),
        },
    ]
    return sorted(drivers, key=lambda item: abs(item["contribution"]), reverse=True)


def _dynasty_valuation(
    *,
    position: str,
    name: str | None,
    ppg: float,
    model_version: str,
) -> dict:
    projected = round(ppg, DISPLAY_PRECISION)
    valuation = DynastyValuation(
        name=name,
        position=position,
        engine=ValuationEngine.ROOKIE_FORECAST,
        model_version=model_version,
        dynasty_value_score=projected,
        confidence_band=None,
        projection_1y=projected,
        projection_2y=projected,
        projection_3y=projected,
        source_projection={"predicted_y24_ppg": ppg},
        notes=[
            PROVISIONAL_DYNASTY_VALUE_NOTE,
            "Current rookie model predicts aggregate Y2-Y4 PPG, not calibrated year-specific projections.",
            "Confidence band is deferred until holdout error calibration is implemented.",
            PROVISIONAL_DRIVERS_NOTE,
            DRIVER_ATTRIBUTION_NOTE,
            DRIVER_CENTERING_NOTE,
            DRAFT_CAPITAL_DRIVER_NOTE,
            CLASS_RANK_NOTE,
        ],
    )
    return valuation.model_dump(mode="json")


def score_prospect(
    position: str,
    pick: int,
    round_num: int,
    age: float,
    name: str | None = None,
) -> dict:
    if position not in _MODELS:
        raise ValueError(f"Unsupported position: {position}. Must be one of {POSITIONS}.")

    model = _MODELS[position]
    X = np.array([[pick, round_num, age]])
    predicted = max(float(model.predict(X)[0]), 0.0)
    ppg = round(predicted, 2)
    model_version = _model_version(position)
    validation = _validation_metadata(position)
    valuation = _dynasty_valuation(
        position=position,
        name=name,
        ppg=ppg,
        model_version=model_version,
    )

    notes = [
        *valuation["notes"],
        "Legacy confidence was pick-bucket logic and is intentionally not emitted.",
    ]
    top_drivers = _top_drivers(position, pick, round_num, age)

    result = {
        "engine":            ValuationEngine.ROOKIE_FORECAST.value,
        "model_version":     model_version,
        "model_grade":       validation["model_grade"],
        "signal_completeness": SIGNAL_COMPLETENESS,
        "horizon_years":     HORIZON_YEARS,
        "dynasty_value_score": valuation["dynasty_value_score"],
        "projection_1y":     valuation["projection_1y"],
        "projection_2y":     valuation["projection_2y"],
        "projection_3y":     valuation["projection_3y"],
        "confidence_band":   None,
        "display_precision": DISPLAY_PRECISION,
        "rmse_position_holdout": validation["rmse_position_holdout"],
        "r2_position_holdout": validation["r2_position_holdout"],
        "validation":        validation,
        "model_caveats":     validation.get("caveats", []),
        "valuation":         {**valuation, "notes": notes},
        "notes":             notes,
        "position":          position,
        "pick":              pick,
        "round":             round_num,
        "age":               age,
        "age_at_entry":      age,
        "predicted_y24_ppg": ppg,
        "threshold_flags":   _threshold_flags(position, pick, age),
        "roster_fit_signal": "unknown",
        "top_drivers":       top_drivers,
        "risk_flags":        ["draft_capital_age_only"],
        "counter_argument":  _counter_argument(),
        "market_overlay":    None,
    }

    if validation["model_grade"] not in {"D", "unvalidated"}:
        result["projected_outcome_band"] = _dynasty_tier(ppg)

    return result


def score_draft_class(prospects: list[dict]) -> list[dict]:
    results = []
    for p in prospects:
        result = score_prospect(
            position=p["position"],
            pick=p["pick"],
            round_num=p["round"],
            age=p["age"],
            name=p.get("name"),
        )
        result["name"] = p["name"]
        result["valuation"]["name"] = p["name"]
        results.append(result)

    results.sort(key=lambda r: r["dynasty_value_score"], reverse=True)
    position_counts = {}
    for overall_rank, result in enumerate(results, start=1):
        position = result["position"]
        position_counts[position] = position_counts.get(position, 0) + 1
        result["class_overall_rank"] = overall_rank
        result["position_class_rank"] = position_counts[position]

    return results
