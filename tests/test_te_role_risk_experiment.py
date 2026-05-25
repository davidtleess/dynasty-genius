from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.run_te_role_risk_experiment import build_role_risk_report
from src.dynasty_genius.eval.te_role_risk_experiment import (
    PRIMARY_ALPHA,
    RANK_DEGRADATION_THRESHOLD,
    ROLE_RISK_CANDIDATE_COLUMNS,
    UNIFIED_PENALTY_COLUMN,
    evaluate_te_role_risk_experiment,
)


def _player_row(
    season: int,
    player_id: str,
    *,
    is_risk: bool,
    outcome: float,
    ppg_variation: float = 0.0,
) -> dict:
    return {
        "player_id": player_id,
        "feature_season": season,
        "training_eligible": True,
        "position": "TE",
        "ppg_t": 5.0 + ppg_variation,
        "games_t": 12,
        "age": 25,
        "route_participation": 0.65,
        "target_share_nfl": 0.13,
        "yprr": 1.4,
        "tprr": 0.18,
        "weighted_opportunity": 0.30,
        "snap_share": 0.60,
        "avg_ppg_t1_t2": outcome,
        "te_role_role_risk": 1 if is_risk else 0,
        "te_role_blocking_specialist": 0,
    }


def _synthetic_frame() -> pd.DataFrame:
    rows = []
    for season in range(2018, 2024):
        rows.append(_player_row(season, f"safe_{season}", is_risk=False, outcome=8.0))
        rows.append(_player_row(season, f"risk_{season}", is_risk=True, outcome=3.0))
    return pd.DataFrame(rows)


def test_evaluate_te_role_risk_experiment_is_validation_only():
    result = evaluate_te_role_risk_experiment(
        _synthetic_frame(),
        test_years=[2020, 2021, 2022, 2023],
    )

    assert result["experiment_name"] == "te_role_risk_detector"
    assert result["primary_alpha"] == PRIMARY_ALPHA
    assert set(result["candidates"]) == {"sparse_duo", "unified_penalty"}
    assert result["candidates"]["sparse_duo"]["candidate_columns"] == list(ROLE_RISK_CANDIDATE_COLUMNS)
    assert result["candidates"]["unified_penalty"]["candidate_columns"] == [UNIFIED_PENALTY_COLUMN]
    assert result["governance"]["model_features_changed"] is False
    assert result["governance"]["te_promotion_changed"] is False
    assert result["governance"]["market_data_used"] is False
    assert result["governance"]["pff_grades_used"] is False
    assert result["candidates"]["unified_penalty"]["summary"]["rmse_delta_mean"] < 0
    assert result["candidates"]["unified_penalty"]["summary"]["mae_delta_mean"] < 0


def test_acceptance_requires_error_improvement_rank_preservation_and_negative_coefficients():
    result = evaluate_te_role_risk_experiment(
        _synthetic_frame(),
        test_years=[2020, 2021, 2022, 2023],
    )
    unified = result["candidates"]["unified_penalty"]

    assert unified["summary"]["rmse_win_folds"] >= 3
    assert unified["summary"]["passes_acceptance"] is True
    assert unified["acceptance"]["rmse_win_gate"] is True
    assert unified["acceptance"]["mean_rmse_gate"] is True
    assert unified["acceptance"]["mean_mae_gate"] is True
    assert unified["acceptance"]["rank_degradation_gate"] is True
    assert unified["acceptance"]["rank_degradation_threshold"] == RANK_DEGRADATION_THRESHOLD
    assert unified["acceptance"]["negative_coefficient_gate"] is True
    assert max(unified["summary"]["candidate_coefficients"].values()) < 0.0


def test_all_zero_candidate_columns_match_baseline_predictions():
    frame = _synthetic_frame()
    frame["te_role_role_risk"] = 0
    frame["te_role_blocking_specialist"] = 0

    result = evaluate_te_role_risk_experiment(frame, test_years=[2020, 2021, 2022, 2023])

    for fold in result["candidates"]["unified_penalty"]["folds"]:
        assert fold["rmse_delta"] == 0.0
        assert fold["mae_delta"] == 0.0


def test_risk_features_are_not_perfectly_collinear_with_existing_features():
    frame = _synthetic_frame()
    numeric_columns = [
        "ppg_t",
        "route_participation",
        "target_share_nfl",
        "yprr",
        "tprr",
        "weighted_opportunity",
        "snap_share",
    ]
    for column in numeric_columns:
        corr = frame[column].corr(frame["te_role_role_risk"])
        assert pd.isna(corr) or abs(corr) < 0.98


def test_rank_degradation_gate_rejects_rank_inverted_fold():
    rows = []
    for season in [2019, 2020]:
        for i in range(15):
            rows.append(
                _player_row(
                    season,
                    f"risk_{i}_{season}",
                    is_risk=True,
                    outcome=9.0,
                    ppg_variation=i * 0.05,
                )
            )
            rows.append(
                _player_row(
                    season,
                    f"safe_{i}_{season}",
                    is_risk=False,
                    outcome=1.0,
                    ppg_variation=i * 0.05,
                )
            )

    for i in range(15):
        rows.append(
            _player_row(
                2021,
                f"risk_{i}_2021",
                is_risk=True,
                outcome=1.0,
                ppg_variation=i * 0.05,
            )
        )
        rows.append(
            _player_row(
                2021,
                f"safe_{i}_2021",
                is_risk=False,
                outcome=9.0,
                ppg_variation=i * 0.05,
            )
        )

    result = evaluate_te_role_risk_experiment(pd.DataFrame(rows), test_years=[2021])
    unified = result["candidates"]["unified_penalty"]

    assert unified["acceptance"]["rank_degradation_gate"] is False
    assert unified["summary"]["passes_acceptance"] is False


def test_real_role_risk_report_is_aggregate_redacted_and_governed(tmp_path: Path):
    out = tmp_path / "role_risk.json"

    report = build_role_risk_report(
        training_path=Path("app/data/training/engine_b_features_v2.csv"),
        archetype_path=Path("app/data/identity/te_archetype_rubric_20260516.json"),
        eligible_path=Path("app/data/identity/pff_te_eligible_te_2018_2025_20260516_canonical.json"),
        out_path=out,
        run_id="te_role_risk_experiment_test",
        generated_at="2026-05-16T15:30:00Z",
    )

    assert out.exists()
    assert report["metadata"]["position"] == "TE"
    assert report["metadata"]["source_eligible_manifest"].endswith("pff_te_eligible_te_2018_2025_20260516_canonical.json")
    assert "weighted_opportunity" in report["metadata"]["baseline_features"]
    assert report["metadata"]["ridge_alpha"] == 1.0
    assert report["result"]["experiment_name"] == "te_role_risk_detector"
    assert set(report["result"]["candidates"]) == {"sparse_duo", "unified_penalty"}
    assert "alpha_sensitivity" in report["result"]
    assert report["governance"]["model_features_changed"] is False
    assert report["governance"]["te_promotion_changed"] is False
    assert report["governance"]["market_data_used"] is False
    assert report["governance"]["pff_grades_used"] is False
    assert report["decision"]["production_change_approved"] is False

    rendered = out.read_text(encoding="utf-8").lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered
    assert "overall_grade" not in rendered
    assert "grades_offense" not in rendered
    assert "grades_pass_route" not in rendered
