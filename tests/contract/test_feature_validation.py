from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


def _clean_candidate() -> pd.DataFrame:
    engine_b_script = importlib.import_module("scripts.assemble_engine_b_dataset")
    rows: list[dict] = []
    for season, training_eligible, outcome in (
        (2024, True, 11.0),
        (2025, False, np.nan),
    ):
        for pos in ("QB", "RB", "WR", "TE"):
            player_id = f"{pos.lower()}-{season}"
            row = {
                "snap_share_t_minus_1": 0.72,
                "cpoe": 4.0 if pos == "QB" else np.nan,
                "player_id": player_id,
                "route_participation": 0.81 if pos in {"WR", "TE"} else np.nan,
                "aging_curve_position": "QB_dual_threat" if pos == "QB" else pos,
                "ppg_t": 12.0,
                "depth_chart_position": f"{pos}1",
                "tprr": 0.22 if pos in {"WR", "TE"} else np.nan,
                "total_points_t": 144.0,
                "ppg_t_minus_2": 9.0,
                "dakota": 0.11 if pos == "QB" else np.nan,
                "air_yards_share": 0.28 if pos in {"WR", "TE"} else np.nan,
                "aging_curve_value": 0.98,
                "target_share_nfl": 0.24 if pos in {"WR", "TE"} else np.nan,
                "yprr": 1.8 if pos in {"WR", "TE"} else np.nan,
                "epa_per_dropback": 0.14 if pos == "QB" else np.nan,
                "dropback_count": 220 if pos == "QB" else np.nan,
                "team": "MIN",
                "feature_season": season,
                "weighted_opportunity": 0.42 if pos in {"WR", "TE"} else np.nan,
                "age": 25.0,
                "is_dual_threat": pos == "QB",
                "ppg_t_minus_1": 10.0,
                "pass_attempts": 210 if pos == "QB" else np.nan,
                "snap_share": 0.76,
                "games_t": 12,
                "position": pos,
                engine_b_script.OUTCOME_COLUMN: outcome,
                "training_eligible": training_eligible,
                "ppg_t_minus_1_available": True,
                "ppg_t_minus_2_available": True,
                "snap_share_t_minus_1_available": True,
                "te_role_is_risk_profile": 1.0 if pos == "TE" else np.nan,
            }
            rows.append(row)

    return pd.DataFrame(rows, columns=list(engine_b_script.ENGINE_B_OUTPUT_COLUMNS))


def _validate(df: pd.DataFrame, **kwargs):
    validation = importlib.import_module("src.dynasty_genius.features.feature_validation")
    return validation.validate_feature_candidate(
        df,
        inference_season=2025,
        min_total_rows=4,
        min_position_rows={"QB": 1, "RB": 1, "WR": 1, "TE": 1},
        critical_features=("snap_share", "games_t", "ppg_t", "age"),
        max_null_rate_by_column={"snap_share": 0.0, "games_t": 0.0, "ppg_t": 0.0},
        prior_runtime=kwargs.get("prior_runtime"),
    )


def test_clean_feature_candidate_passes_and_reports_drift_without_blocking() -> None:
    candidate = _clean_candidate()
    prior = candidate.copy()
    prior.loc[prior["feature_season"] == 2025, "snap_share"] = 0.50

    result = _validate(candidate, prior_runtime=prior)

    assert result.ok is True
    assert result.failures == []
    assert result.decision_supported is False
    assert result.drift["row_count"]["candidate"] == len(candidate)
    assert result.drift["row_count"]["prior_runtime"] == len(prior)
    assert "snap_share" in result.drift["numeric_mean_delta"]


@pytest.mark.parametrize(
    ("mutate", "expected_reason"),
    [
        (lambda df: df.assign(ktc_value=123), "prohibited"),
        (lambda df: df.drop(columns=["snap_share"]), "schema"),
        (lambda df: df.assign(feature_season="not-a-season"), "dtype"),
        (lambda df: df.assign(player_id=[""] + df["player_id"].tolist()[1:]), "blank"),
        (
            lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True),
            "duplicate",
        ),
        (
            lambda df: df[df["feature_season"] != 2025].reset_index(drop=True),
            "inference",
        ),
        (lambda df: df.assign(snap_share=1.25), "range"),
        (lambda df: df.assign(snap_share=np.nan), "nan"),
    ],
)
def test_feature_validation_gates_fail_closed_independently(
    mutate,
    expected_reason: str,
) -> None:
    result = _validate(mutate(_clean_candidate()))

    assert result.ok is False
    assert result.decision_supported is False
    assert any(expected_reason in failure.lower() for failure in result.failures)


def test_validation_rejects_missing_position_coverage() -> None:
    candidate = _clean_candidate()
    candidate = candidate[candidate["position"] != "TE"].reset_index(drop=True)

    result = _validate(candidate)

    assert result.ok is False
    assert any("coverage" in failure.lower() and "TE" in failure for failure in result.failures)
