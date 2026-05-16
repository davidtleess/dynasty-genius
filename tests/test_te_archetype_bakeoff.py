from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.run_te_archetype_bakeoff import build_bakeoff_report
from src.dynasty_genius.eval.te_archetype_bakeoff import (
    build_te_bakeoff_frame,
    evaluate_te_taxonomy_candidate,
)


def _archetype_artifact():
    return {
        "players": {
            "te_a": {
                "player_id": "te_a",
                "labeling_status": "labeled",
                "archetype": "ambiguous",
                "coverage_status": "pff_alignment_available",
                "detached_rate_from_snaps": 0.33,
                "inline_rate_from_snaps": 0.67,
                "alignment_snap_total": 240.0,
                "routes": 210.0,
                "yprr_computed": 2.2,
                "tprr_computed": 0.21,
            },
            "te_b": {
                "player_id": "te_b",
                "labeling_status": "labeled",
                "archetype": "receiving_leaning",
                "coverage_status": "pff_alignment_available",
                "detached_rate_from_snaps": 0.54,
                "inline_rate_from_snaps": 0.46,
                "alignment_snap_total": 260.0,
                "routes": 220.0,
                "yprr_computed": 1.1,
                "tprr_computed": 0.11,
            },
        }
    }


def test_build_frame_joins_taxonomy_by_canonical_player_id_without_source_ids():
    training = pd.DataFrame(
        [
            {
                "player_id": "00-a",
                "position": "TE",
                "feature_season": 2021,
                "avg_ppg_t1_t2": 9.0,
                "training_eligible": True,
            },
            {
                "player_id": "00-b",
                "position": "TE",
                "feature_season": 2021,
                "avg_ppg_t1_t2": 4.0,
                "training_eligible": True,
            },
            {
                "player_id": "00-x",
                "position": "TE",
                "feature_season": 2021,
                "avg_ppg_t1_t2": 6.0,
                "training_eligible": True,
            },
        ]
    )
    eligible_rows = [
        {"player_id": "te_a", "gsis_id": "00-a"},
        {"player_id": "te_b", "gsis_id": "00-b"},
    ]

    frame = build_te_bakeoff_frame(training, _archetype_artifact(), eligible_rows=eligible_rows)

    assert frame.shape[0] == 3
    assert "gsis_id" not in frame.columns
    assert "pff_id" not in frame.columns
    assert "fantasy_role_archetype" in frame.columns
    assert frame.loc[frame["player_id"] == "00-a", "fantasy_role_archetype"].item() == "complete_te"
    assert frame.loc[frame["player_id"] == "00-b", "fantasy_role_archetype"].item() == "role_risk"
    assert (
        frame.loc[frame["player_id"] == "00-x", "fantasy_role_archetype"].item()
        == "taxonomy_missing"
    )


def test_build_frame_adds_one_hot_candidate_columns():
    training = pd.DataFrame(
        [
            {
                "player_id": "00-a",
                "position": "TE",
                "feature_season": 2021,
                "avg_ppg_t1_t2": 9.0,
                "training_eligible": True,
            }
        ]
    )
    eligible_rows = [{"player_id": "te_a", "gsis_id": "00-a"}]

    frame = build_te_bakeoff_frame(training, _archetype_artifact(), eligible_rows=eligible_rows)

    assert frame["te_role_complete_te"].item() == 1
    assert frame["te_role_blocking_specialist"].item() == 0
    assert frame["te_align_balanced"].item() == 1


def test_evaluate_candidate_reports_metric_deltas_without_model_promotion():
    rows = []
    for season in [2019, 2020, 2021, 2022]:
        rows.extend(
            [
                {
                    "player_id": f"rec_{season}",
                    "feature_season": season,
                    "training_eligible": True,
                    "position": "TE",
                    "ppg_t": 6.0,
                    "games_t": 12,
                    "age": 24,
                    "route_participation": 0.65,
                    "target_share_nfl": 0.12,
                    "yprr": 1.3,
                    "tprr": 0.18,
                    "weighted_opportunity": 0.3,
                    "snap_share": 0.6,
                    "avg_ppg_t1_t2": 9.0,
                    "te_role_complete_te": 1,
                    "te_role_blocking_specialist": 0,
                    "te_role_role_risk": 0,
                },
                {
                    "player_id": f"block_{season}",
                    "feature_season": season,
                    "training_eligible": True,
                    "position": "TE",
                    "ppg_t": 6.0,
                    "games_t": 12,
                    "age": 24,
                    "route_participation": 0.65,
                    "target_share_nfl": 0.12,
                    "yprr": 1.3,
                    "tprr": 0.18,
                    "weighted_opportunity": 0.3,
                    "snap_share": 0.6,
                    "avg_ppg_t1_t2": 3.0,
                    "te_role_complete_te": 0,
                    "te_role_blocking_specialist": 1,
                    "te_role_role_risk": 0,
                },
            ]
        )
    frame = pd.DataFrame(rows)

    result = evaluate_te_taxonomy_candidate(
        frame,
        candidate_name="fantasy_role_one_hot",
        candidate_columns=["te_role_complete_te", "te_role_blocking_specialist", "te_role_role_risk"],
        test_years=[2021, 2022],
    )

    assert result["candidate_name"] == "fantasy_role_one_hot"
    assert result["model_features_changed"] is False
    assert result["te_promotion_changed"] is False
    assert result["market_data_used"] is False
    assert result["folds"][0]["baseline_rmse"] > result["folds"][0]["candidate_rmse"]
    assert result["summary"]["rmse_delta_mean"] < 0
    assert result["summary"]["passes_acceptance"] is False


def test_bakeoff_report_is_aggregate_redacted_and_governed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    training_path = tmp_path / "training.csv"
    archetype_path = tmp_path / "archetype.json"
    eligible_path = tmp_path / "eligible.json"
    out_path = tmp_path / "te_bakeoff.json"

    pd.DataFrame(
        [
            {"player_id": "00-a", "position": "TE", "feature_season": 2021},
            {"player_id": "00-b", "position": "WR", "feature_season": 2021},
        ]
    ).to_csv(training_path, index=False)
    archetype_path.write_text(
        json.dumps({"metadata": {"eligible_count": 1}, "players": {"te_a": {}}}),
        encoding="utf-8",
    )
    eligible_path.write_text(
        json.dumps({"eligible": [{"player_id": "te_a", "gsis_id": "00-a", "pff_id": "123"}]}),
        encoding="utf-8",
    )

    def fake_build_frame(
        training: pd.DataFrame,
        archetype_artifact: dict[str, Any],
        *,
        eligible_rows: list[dict[str, Any]],
    ) -> pd.DataFrame:
        assert list(training["position"].unique()) == ["TE"]
        assert archetype_artifact["metadata"]["eligible_count"] == 1
        assert eligible_rows[0]["gsis_id"] == "00-a"
        frame = training.copy()
        frame["te_align_detached"] = 1
        frame["te_role_complete_te"] = 1
        frame["te_role_role_risk"] = 0
        return frame

    def fake_evaluate(
        frame: pd.DataFrame,
        *,
        candidate_name: str,
        candidate_columns: list[str],
        test_years: list[int],
    ) -> dict[str, Any]:
        return {
            "candidate_name": candidate_name,
            "candidate_columns": candidate_columns,
            "folds": [{"test_year": test_years[0], "rmse_delta": -0.1, "mae_delta": -0.1}],
            "summary": {
                "rmse_delta_mean": -0.1,
                "mae_delta_mean": -0.1,
                "passes_acceptance": True,
            },
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
        }

    monkeypatch.setattr(
        "scripts.run_te_archetype_bakeoff._load_evaluator_functions",
        lambda: (fake_build_frame, fake_evaluate),
    )

    report = build_bakeoff_report(
        training_path=training_path,
        archetype_path=archetype_path,
        eligible_path=eligible_path,
        out_path=out_path,
        run_id="te_archetype_bakeoff_test",
        generated_at="2026-05-16T14:30:00Z",
        test_years=[2021],
    )

    assert out_path.exists()
    assert report["metadata"]["position"] == "TE"
    assert report["metadata"]["te_training_rows"] == 1
    assert report["governance"]["diagnostic_only"] is True
    assert report["governance"]["model_features_changed"] is False
    assert report["governance"]["te_promotion_changed"] is False
    assert report["governance"]["market_data_used"] is False
    assert report["governance"]["pff_grades_used"] is False
    assert report["governance"]["player_level_rows_emitted"] is False
    assert set(report["candidates"]) == {
        "snap_alignment_one_hot",
        "fantasy_role_one_hot",
        "complete_te_detector",
        "role_risk_detector",
    }

    rendered = out_path.read_text(encoding="utf-8").lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered
    assert "overall_grade" not in rendered


def test_committed_bakeoff_artifact_is_aggregate_redacted_and_governed():
    path = Path("app/data/backtest/phase13/te_archetype_bakeoff_20260516.json")
    report = json.loads(path.read_text(encoding="utf-8"))

    assert report["metadata"]["position"] == "TE"
    assert report["metadata"]["te_training_rows"] > 0
    assert report["governance"]["diagnostic_only"] is True
    assert report["governance"]["model_features_changed"] is False
    assert report["governance"]["te_promotion_changed"] is False
    assert report["governance"]["market_data_used"] is False
    assert report["governance"]["pff_grades_used"] is False
    assert report["governance"]["player_level_rows_emitted"] is False
    assert set(report["candidates"]) == {
        "snap_alignment_one_hot",
        "fantasy_role_one_hot",
        "complete_te_detector",
        "role_risk_detector",
    }
    assert report["candidates"]["role_risk_detector"]["summary"]["passes_acceptance"] is True

    rendered = path.read_text(encoding="utf-8").lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered
    assert "overall_grade" not in rendered
