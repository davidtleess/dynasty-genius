from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.assemble_engine_b_dataset import (
    ENGINE_B_OUTPUT_COLUMNS,
    add_te_role_risk_feature,
)
from scripts.train_engine_b import train_te_deployment_model
from src.dynasty_genius.eval.backtest_harness import WalkForwardDriver
from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_FEATURES_QB,
    ENGINE_B_FEATURES_RB,
    ENGINE_B_FEATURES_TE,
    ENGINE_B_FEATURES_WR,
)


def test_te_role_risk_feature_is_te_only_contract_feature():
    assert "te_role_is_risk_profile" in ENGINE_B_FEATURES_TE
    assert "te_role_is_risk_profile" not in ENGINE_B_FEATURES_QB
    assert "te_role_is_risk_profile" not in ENGINE_B_FEATURES_RB
    assert "te_role_is_risk_profile" not in ENGINE_B_FEATURES_WR


def test_add_te_role_risk_feature_defaults_missing_labels_to_zero():
    df = pd.DataFrame(
        [
            {"player_id": "gsis-risk", "position": "TE"},
            {"player_id": "gsis-block", "position": "TE"},
            {"player_id": "gsis-receive", "position": "TE"},
            {"player_id": "gsis-missing", "position": "TE"},
            {"player_id": "gsis-qb", "position": "QB"},
        ]
    )
    eligible = {
        "eligible": [
            {"gsis_id": "gsis-risk", "player_id": "risk_te"},
            {"gsis_id": "gsis-block", "player_id": "block_te"},
            {"gsis_id": "gsis-receive", "player_id": "receive_te"},
            {"gsis_id": "gsis-missing", "player_id": "missing_te"},
        ]
    }
    labeled_base = {
        "labeling_status": "labeled",
        "detached_rate_from_snaps": 0.10,
        "inline_rate_from_snaps": 0.90,
        "yprr_computed": 1.0,
        "tprr_computed": 0.10,
    }
    rubric = {
        "players": {
            "risk_te": {
                **labeled_base,
                "detached_rate_from_snaps": 0.70,
                "inline_rate_from_snaps": 0.20,
            },
            "block_te": labeled_base,
            "receive_te": {
                **labeled_base,
                "detached_rate_from_snaps": 0.70,
                "inline_rate_from_snaps": 0.20,
                "yprr_computed": 2.1,
                "tprr_computed": 0.21,
            },
        }
    }

    result = add_te_role_risk_feature(df, rubric, eligible)

    values = dict(zip(result["player_id"], result["te_role_is_risk_profile"]))
    assert values["gsis-risk"] == 1
    assert values["gsis-block"] == 1
    assert values["gsis-receive"] == 0
    assert values["gsis-missing"] == 0
    assert np.isnan(values["gsis-qb"])


def test_engine_b_output_columns_preserve_existing_dataset_gate_columns():
    required_existing = {
        "dropback_count",
        "pass_attempts",
        "route_participation",
        "total_points_t",
        "target_share_nfl",
        "air_yards_share",
    }
    assert required_existing <= set(ENGINE_B_OUTPUT_COLUMNS)
    assert "te_role_is_risk_profile" in ENGINE_B_OUTPUT_COLUMNS


def test_walkforward_te_alpha_is_100_for_model_change_validation():
    assert WalkForwardDriver.FIXED_ALPHA["TE"] == 100.0


@pytest.mark.xfail(
    strict=True,
    reason=(
        "te_role_is_risk_profile all-negative invariant was a Tyler-Conklin contamination "
        "artifact: 128x duplicated NON-risk rows inflated the non-risk baseline. After the T2 "
        "dedup the coef flips to 3/4 positive (see "
        "docs/validation/2026-06-26-te-role-risk-contamination-finding.md). xfail until the "
        "deferred feature-validity review resolves the invariant; strict=True forces a revisit "
        "if it passes again. Do NOT flip the assertion to green."
    ),
)
def test_te_run_records_negative_role_risk_coefficients():
    driver = WalkForwardDriver(position="TE")
    result = driver.run()
    assert result.ridge_alpha == 100.0
    assert result.folds
    coefficients = [
        fold.feature_coefficients["te_role_is_risk_profile"]
        for fold in result.folds
    ]
    assert len(coefficients) == 4
    assert all(coef < 0.0 for coef in coefficients)


def test_train_te_deployment_model_writes_only_te_artifact(tmp_path: Path):
    rows = []
    for season in range(2018, 2024):
        for idx, risk in enumerate([0, 1, 0, 1]):
            rows.append(
                {
                    "player_id": f"te-{season}-{idx}",
                    "position": "TE",
                    "feature_season": season,
                    "training_eligible": True,
                    "avg_ppg_t1_t2": 12.0 - (risk * 3.0) + idx,
                    "age": 23 + idx,
                    "ppg_t": 9.0 + idx,
                    "games_t": 10,
                    "snap_share": 0.5 + idx * 0.05,
                    "aging_curve_value": 1.0,
                    "ppg_t_minus_1": 8.0 + idx,
                    "ppg_t_minus_2": 7.5 + idx,
                    "snap_share_t_minus_1": 0.45 + idx * 0.03,
                    "ppg_t_minus_1_available": True,
                    "ppg_t_minus_2_available": True,
                    "snap_share_t_minus_1_available": True,
                    "weighted_opportunity": 0.25 + idx * 0.01,
                    "yprr": 1.4 + idx * 0.1,
                    "tprr": 0.12 + idx * 0.01,
                    "te_role_is_risk_profile": risk,
                }
            )
    df = pd.DataFrame(rows)

    report = train_te_deployment_model(df, tmp_path)

    assert report["position"] == "TE"
    assert report["alpha_selected"] == 100.0
    assert report["artifact_path"].endswith("te_v3.pkl")
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "te_v3.pkl",
        "validation_report_te.json",
    ]
    with open(tmp_path / "te_v3.pkl", "rb") as f:
        bundle = pickle.load(f)
    feature_index = bundle["features"].index("te_role_is_risk_profile")
    assert bundle["model"].coef_[feature_index] < 0.0
