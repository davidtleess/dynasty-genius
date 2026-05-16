from __future__ import annotations

import pandas as pd

from src.dynasty_genius.eval.te_regularization_bakeoff import (
    ALPHA_GRID,
    evaluate_te_regularization_bakeoff,
)


def _synthetic_frame() -> pd.DataFrame:
    rows = []
    for season in [2019, 2020, 2021, 2022, 2023]:
        rows.extend(
            [
                {
                    "player_id": f"safe_{season}",
                    "feature_season": season,
                    "training_eligible": True,
                    "position": "TE",
                    "ppg_t": 6.0,
                    "games_t": 12,
                    "age": 25,
                    "route_participation": 0.65,
                    "target_share_nfl": 0.13,
                    "yprr": 1.4,
                    "tprr": 0.18,
                    "weighted_opportunity": 0.30,
                    "snap_share": 0.60,
                    "avg_ppg_t1_t2": 8.0,
                    "te_role_role_risk": 0,
                    "te_role_blocking_specialist": 0,
                },
                {
                    "player_id": f"risk_{season}",
                    "feature_season": season,
                    "training_eligible": True,
                    "position": "TE",
                    "ppg_t": 6.0,
                    "games_t": 12,
                    "age": 25,
                    "route_participation": 0.65,
                    "target_share_nfl": 0.13,
                    "yprr": 1.4,
                    "tprr": 0.18,
                    "weighted_opportunity": 0.30,
                    "snap_share": 0.60,
                    "avg_ppg_t1_t2": 3.0,
                    "te_role_role_risk": 1,
                    "te_role_blocking_specialist": 0,
                },
            ]
        )
    return pd.DataFrame(rows)


def test_evaluate_te_regularization_bakeoff_is_validation_only():
    result = evaluate_te_regularization_bakeoff(
        _synthetic_frame(),
        test_years=[2021, 2022, 2023],
    )

    assert result["experiment_name"] == "te_regularization_bakeoff"
    assert result["alpha_grid"] == list(ALPHA_GRID)
    assert "baseline_only" in result["results_by_alpha"]["1.0"]
    assert "unified_penalty" in result["results_by_alpha"]["100.0"]
    assert result["governance"]["model_features_changed"] is False
    assert result["governance"]["te_promotion_changed"] is False


def test_bakeoff_reports_deltas_vs_baseline_alpha_1():
    result = evaluate_te_regularization_bakeoff(
        _synthetic_frame(),
        test_years=[2021, 2022, 2023],
    )
    
    # Check a specific alpha result
    res_100 = result["results_by_alpha"]["100.0"]["unified_penalty"]
    assert "rmse_delta_vs_baseline_a1" in res_100["summary"]
    assert "mae_delta_vs_baseline_a1" in res_100["summary"]


import json
from pathlib import Path

from scripts.run_te_regularization_bakeoff import build_regularization_report


def test_real_bakeoff_report_is_aggregate_redacted_and_governed(tmp_path: Path):
    out = tmp_path / "regularization_bakeoff.json"

    report = build_regularization_report(
        training_path=Path("app/data/training/engine_b_features_v2.csv"),
        archetype_path=Path("app/data/identity/te_archetype_rubric_20260516.json"),
        eligible_path=Path("app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json"),
        out_path=out,
        run_id="te_reg_bakeoff_test",
        generated_at="2026-05-16T16:30:00Z",
    )

    assert out.exists()
    assert report["metadata"]["position"] == "TE"
    assert "100.0" in report["result"]["results_by_alpha"]
    assert report["governance"]["model_features_changed"] is False
    assert report["governance"]["te_promotion_changed"] is False
    rendered = out.read_text(encoding="utf-8").lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered
    assert "overall_grade" not in rendered
    assert "grades_offense" not in rendered
    assert "grades_pass_route" not in rendered
