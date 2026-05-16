from __future__ import annotations

import json
from pathlib import Path

from scripts.build_te_archetype_validation import build_validation_from_files
from src.dynasty_genius.audit.te_archetype_validation import (
    build_te_archetype_validation_artifact,
)


def _synthetic_archetype_artifact() -> dict:
    return {
        "metadata": {
            "run_id": "rubric_test",
            "rubric_version": "0.1.0",
            "eligible_count": 4,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
        },
        "players": {
            "receiving_a": {"player_id": "receiving_a", "archetype": "receiving_leaning", "labeling_status": "labeled"},
            "receiving_b": {"player_id": "receiving_b", "archetype": "receiving_leaning", "labeling_status": "labeled"},
            "blocking_a": {"player_id": "blocking_a", "archetype": "blocking_leaning", "labeling_status": "labeled"},
            "missing_a": {"player_id": "missing_a", "archetype": None, "labeling_status": "excluded"},
        },
    }


def _synthetic_eligible_rows() -> list[dict]:
    return [
        {"player_id": "receiving_a", "gsis_id": "00-r-a"},
        {"player_id": "receiving_b", "gsis_id": "00-r-b"},
        {"player_id": "blocking_a", "gsis_id": "00-b-a"},
        {"player_id": "missing_a", "gsis_id": "00-m-a"},
    ]


def _synthetic_predictions() -> list[dict]:
    return [
        {
            "player_id": "00-r-a",
            "fold_index": "1",
            "feature_season": "2021",
            "predicted_ppg": "6.0",
            "realized_ppg": "9.0",
            "residual": "3.0",
        },
        {
            "player_id": "00-r-b",
            "fold_index": "1",
            "feature_season": "2021",
            "predicted_ppg": "8.0",
            "realized_ppg": "7.0",
            "residual": "-1.0",
        },
        {
            "player_id": "00-b-a",
            "fold_index": "1",
            "feature_season": "2021",
            "predicted_ppg": "5.0",
            "realized_ppg": "2.0",
            "residual": "-3.0",
        },
        {
            "player_id": "00-m-a",
            "fold_index": "1",
            "feature_season": "2021",
            "predicted_ppg": "4.0",
            "realized_ppg": "4.0",
            "residual": "0.0",
        },
        {
            "player_id": "00-active-veteran",
            "fold_index": "1",
            "feature_season": "2021",
            "predicted_ppg": "10.0",
            "realized_ppg": "10.0",
            "residual": "0.0",
        },
    ]


def test_validation_artifact_groups_prediction_residuals_by_archetype():
    artifact = build_te_archetype_validation_artifact(
        _synthetic_archetype_artifact(),
        eligible_rows=_synthetic_eligible_rows(),
        prediction_rows=_synthetic_predictions(),
        run_id="validation_test",
        prediction_source="synthetic_predictions.csv",
        generated_at="2026-05-16T13:30:00Z",
        min_unique_players=1,
    )

    assert artifact["metadata"]["matched_prediction_rows"] == 4
    assert artifact["metadata"]["matched_labeled_prediction_rows"] == 3
    assert artifact["metadata"]["matched_labeled_unique_players"] == 3
    assert artifact["group_metrics"]["receiving_leaning"]["prediction_rows"] == 2
    assert artifact["group_metrics"]["receiving_leaning"]["realized_ppg_mean"] == 8.0
    assert artifact["group_metrics"]["receiving_leaning"]["residual_mean"] == 1.0
    assert artifact["group_metrics"]["blocking_leaning"]["prediction_rows"] == 1
    assert artifact["group_metrics"]["blocking_leaning"]["realized_ppg_mean"] == 2.0
    assert artifact["comparisons"]["receiving_leaning_minus_blocking_leaning"]["realized_ppg_mean_diff"] == 6.0


def test_validation_artifact_is_diagnostic_only_and_redacted():
    artifact = build_te_archetype_validation_artifact(
        _synthetic_archetype_artifact(),
        eligible_rows=_synthetic_eligible_rows(),
        prediction_rows=_synthetic_predictions(),
        run_id="validation_test",
        prediction_source="synthetic_predictions.csv",
        generated_at="2026-05-16T13:30:00Z",
        min_unique_players=1,
    )

    assert artifact["governance"]["model_features_changed"] is False
    assert artifact["governance"]["te_promotion_changed"] is False
    assert artifact["governance"]["market_data_used"] is False
    assert artifact["governance"]["pff_grades_used"] is False
    assert "players" not in artifact
    rendered = json.dumps(artifact).lower()
    assert "00-r-a" not in rendered
    assert "receiving_a" not in rendered
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered


def test_small_unique_player_groups_are_marked_exploratory():
    artifact = build_te_archetype_validation_artifact(
        _synthetic_archetype_artifact(),
        eligible_rows=_synthetic_eligible_rows(),
        prediction_rows=_synthetic_predictions(),
        run_id="validation_test",
        prediction_source="synthetic_predictions.csv",
        generated_at="2026-05-16T13:30:00Z",
        min_unique_players=2,
    )

    assert artifact["group_metrics"]["blocking_leaning"]["unique_players"] == 1
    assert artifact["group_metrics"]["blocking_leaning"]["sample_status"] == "small_n"
    assert artifact["group_metrics"]["receiving_leaning"]["sample_status"] == "usable_for_diagnostic"


def test_build_validation_from_files_writes_committed_artifact_shape(tmp_path: Path):
    out = tmp_path / "validation.json"

    artifact = build_validation_from_files(
        archetype_path=Path("app/data/identity/te_archetype_rubric_20260516.json"),
        eligible_path=Path("app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json"),
        predictions_path=Path("app/data/backtest/runs/25f9697d-f155-49e2-a6c7-384b7cec51c1/predictions_TE.csv"),
        out_path=out,
        run_id="te_archetype_validation_test",
        generated_at="2026-05-16T13:30:00Z",
    )

    assert out.exists()
    assert artifact["metadata"]["matched_labeled_prediction_rows"] == 337
    assert artifact["metadata"]["matched_labeled_unique_players"] == 60
    assert artifact["group_metrics"]["blocking_leaning"]["unique_players"] >= 8
    assert artifact["comparisons"]["receiving_leaning_minus_blocking_leaning"]["realized_ppg_mean_diff"] > 3.0
    assert artifact["comparisons"]["receiving_leaning_minus_blocking_leaning"]["residual_mean_diff"] > 1.0
    rendered = out.read_text(encoding="utf-8").lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "/users/" not in rendered
