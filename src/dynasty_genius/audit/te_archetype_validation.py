"""Diagnostic validation for Phase 13 TE archetype labels.

This module intentionally emits aggregate metrics only. It is a trust artifact
over an existing backtest prediction log, not a model feature materializer.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Any


ARCHETYPE_ORDER = ("receiving_leaning", "ambiguous", "blocking_leaning")
VALIDATION_VERSION = "0.1.0"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    parsed = float(text)
    if math.isnan(parsed):
        return None
    return parsed


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(median(values))


def _canonical_by_source_id(eligible_rows: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in eligible_rows:
        canonical = str(row.get("player_id") or "").strip()
        source_id = str(row.get("gsis_id") or "").strip()
        if canonical and source_id:
            mapping[source_id] = canonical
    return mapping


def _safe_prediction_source(source: str) -> str:
    """Preserve repo-relative provenance without leaking local filesystem paths."""
    return source.replace("\\", "/").split("/Users/")[-1] if "/Users/" in source else source


def _group_metrics(rows: list[dict[str, Any]], min_unique_players: int) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {archetype: [] for archetype in ARCHETYPE_ORDER}
    for row in rows:
        archetype = row["archetype"]
        if archetype in grouped:
            grouped[archetype].append(row)

    metrics: dict[str, dict[str, Any]] = {}
    for archetype in ARCHETYPE_ORDER:
        values = grouped[archetype]
        unique_players = {row["canonical_player_id"] for row in values}
        realized = [row["realized_ppg"] for row in values]
        predicted = [row["predicted_ppg"] for row in values]
        residuals = [row["residual"] for row in values]
        abs_errors = [abs(row["residual"]) for row in values]
        positive_residual = [row for row in values if row["residual"] > 0]
        metrics[archetype] = {
            "prediction_rows": len(values),
            "unique_players": len(unique_players),
            "sample_status": (
                "usable_for_diagnostic"
                if len(unique_players) >= min_unique_players
                else "small_n"
            ),
            "realized_ppg_mean": _round(_mean(realized)),
            "realized_ppg_median": _round(_median(realized)),
            "predicted_ppg_mean": _round(_mean(predicted)),
            "predicted_ppg_median": _round(_median(predicted)),
            "residual_mean": _round(_mean(residuals)),
            "residual_median": _round(_median(residuals)),
            "absolute_error_mean": _round(_mean(abs_errors)),
            "positive_residual_rate": _round(len(positive_residual) / len(values)) if values else None,
        }
    return metrics


def _comparison(
    metrics: dict[str, dict[str, Any]],
    left: str,
    right: str,
) -> dict[str, float | None]:
    left_metrics = metrics[left]
    right_metrics = metrics[right]
    fields = (
        "realized_ppg_mean",
        "predicted_ppg_mean",
        "residual_mean",
        "absolute_error_mean",
        "positive_residual_rate",
    )
    out: dict[str, float | None] = {}
    for field in fields:
        left_value = left_metrics[field]
        right_value = right_metrics[field]
        out[f"{field}_diff"] = (
            None if left_value is None or right_value is None else _round(left_value - right_value)
        )
    return out


def build_te_archetype_validation_artifact(
    archetype_artifact: dict[str, Any],
    *,
    eligible_rows: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
    run_id: str,
    prediction_source: str,
    generated_at: str,
    min_unique_players: int = 8,
) -> dict[str, Any]:
    """Join TE archetype labels to existing TE backtest predictions and aggregate metrics."""

    players = archetype_artifact["players"]
    canonical_by_gsis = _canonical_by_source_id(eligible_rows)
    matched_rows: list[dict[str, Any]] = []
    matched_labeled_rows: list[dict[str, Any]] = []

    for row in prediction_rows:
        canonical_player_id = canonical_by_gsis.get(str(row.get("player_id") or ""))
        if not canonical_player_id:
            continue
        label = players.get(canonical_player_id)
        if label is None:
            continue
        matched_rows.append(row)
        archetype = label.get("archetype")
        if archetype is None:
            continue
        predicted = _to_float(row.get("predicted_ppg"))
        realized = _to_float(row.get("realized_ppg"))
        residual = _to_float(row.get("residual"))
        if predicted is None or realized is None:
            continue
        if residual is None:
            residual = realized - predicted
        matched_labeled_rows.append(
            {
                "canonical_player_id": canonical_player_id,
                "archetype": archetype,
                "predicted_ppg": predicted,
                "realized_ppg": realized,
                "residual": residual,
            }
        )

    group_metrics = _group_metrics(matched_labeled_rows, min_unique_players=min_unique_players)
    return {
        "metadata": {
            "schema_version": VALIDATION_VERSION,
            "run_id": run_id,
            "generated_at": generated_at,
            "validation_type": "te_archetype_backtest_residual_lens",
            "position": "TE",
            "rubric_run_id": archetype_artifact.get("metadata", {}).get("run_id"),
            "rubric_version": archetype_artifact.get("metadata", {}).get("rubric_version"),
            "prediction_source": _safe_prediction_source(prediction_source),
            "eligible_count": len(eligible_rows),
            "prediction_rows": len(prediction_rows),
            "matched_prediction_rows": len(matched_rows),
            "matched_labeled_prediction_rows": len(matched_labeled_rows),
            "matched_labeled_unique_players": len(
                {row["canonical_player_id"] for row in matched_labeled_rows}
            ),
            "min_unique_players_per_group": min_unique_players,
        },
        "group_metrics": group_metrics,
        "comparisons": {
            "receiving_leaning_minus_blocking_leaning": _comparison(
                group_metrics,
                "receiving_leaning",
                "blocking_leaning",
            ),
            "receiving_leaning_minus_ambiguous": _comparison(
                group_metrics,
                "receiving_leaning",
                "ambiguous",
            ),
        },
        "governance": {
            "diagnostic_only": True,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
            "pff_grades_used": False,
            "player_level_rows_emitted": False,
        },
        "interpretation": {
            "primary_question": "Do snap-based collegiate TE archetype labels explain future TE outcome or model residual patterns?",
            "answer_policy": "Treat group deltas as evidence for future feature bake-off design, not as production model lift.",
            "current_status": "exploratory_validation",
        },
        "limitations": [
            "Prediction rows are repeated player-seasons from the existing TE backtest log, not independent prospect observations.",
            "The rubric uses snap-alignment fallback, not route-alignment.",
            "The artifact does not retrain Engine A or Engine B, so it cannot prove incremental model lift by itself.",
            "TE remains EXPERIMENTAL regardless of this diagnostic result.",
        ],
    }
