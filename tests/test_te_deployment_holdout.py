"""The TE deployment model must take the same test every other position takes.

Why this file exists: `train_te_deployment_model` fits on `train_df`, then calls
`model.predict(X)` on the very X it was just fit on, and scores THAT. The reported R²
and Spearman are therefore in-sample — a measure of how well a ridge can memorise 492
rows, not of how it will rank a tight end next season. It then writes
`"promotion_warranted": None` as a literal, so the >=2/3 composite gate that governs
every other position is never invoked for TE.

The consequence is not academic. TE is the ONE position that has ever taken a fair test
and lost: run 20260513T012309Z scored it 0 improvements of 3 against a naive prior-season
PPG baseline and correctly recorded promotion_warranted False, while QB, RB and WR each
went 3 of 3. The model now serving TE was trained by this path afterwards, with no
holdout, and the product displays it as validated.

QB/RB/WR already do this correctly a hundred lines below (`_train_position`): split on
HOLDOUT_SEASONS, fit on train, predict on test, score out-of-sample against a baseline
computed on the same held-out rows, then `_gate`. These tests require TE to do the same.

They deliberately do NOT assert that TE passes. If an honest holdout says TE cannot beat
last season's points, that is the correct answer and the product should say so.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.train_engine_b import HOLDOUT_SEASONS, train_te_deployment_model
from src.dynasty_genius.features.feature_assembly import OUTCOME_COLUMN
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_FEATURES_BY_POSITION


def _te_frame(n_per_season: int = 30) -> pd.DataFrame:
    """TE rows spanning training seasons and both holdout seasons."""
    rng = np.random.default_rng(20260831)
    seasons = [2018, 2019, 2020, 2021, *HOLDOUT_SEASONS]
    rows = []
    for season in seasons:
        for i in range(n_per_season):
            ppg = float(rng.uniform(2.0, 14.0))
            row = {
                "player_id": f"TE{season}{i}",
                "position": "TE",
                "feature_season": season,
                "training_eligible": True,
                "ppg_t": ppg,
                OUTCOME_COLUMN: ppg * 0.9 + float(rng.normal(0, 1.5)),
            }
            for feature in ENGINE_B_FEATURES_BY_POSITION["TE"]:
                row.setdefault(feature, float(rng.uniform(0.1, 0.9)))
            row["ppg_t"] = ppg
            rows.append(row)
    return pd.DataFrame(rows)


def test_te_reports_a_holdout_it_did_not_train_on(tmp_path: Path) -> None:
    """train_rows + test_rows must PARTITION the TE rows; scoring on X proves it did not."""
    df = _te_frame()
    result = train_te_deployment_model(df, tmp_path / "run")

    assert not result.get("skipped"), result
    assert result.get("test_rows"), (
        "TE must report a held-out row count like every other position; its absence is "
        "what let in-sample metrics ship as validation"
    )
    assert result["train_rows"] + result["test_rows"] == len(df), (
        "train and holdout must be a partition of the TE rows — if the model were scored "
        "on the rows it was fit on, these would overlap instead of summing"
    )


def test_te_actually_runs_the_promotion_gate(tmp_path: Path) -> None:
    """`promotion_warranted: None` meant the gate was never called, not that it tied."""
    df = _te_frame()
    result = train_te_deployment_model(df, tmp_path / "run")

    assert isinstance(result.get("promotion_warranted"), bool), (
        "promotion_warranted must be a real verdict from _gate, not a hardcoded None"
    )
    assert isinstance(result.get("improvements"), int), (
        "the composite gate reports how many of the three metrics beat the baseline"
    )
    assert 0 <= result["improvements"] <= 3


def test_te_baseline_is_measured_on_the_held_out_rows(tmp_path: Path) -> None:
    """A baseline computed on training rows would flatter the model on the test set."""
    df = _te_frame()
    result = train_te_deployment_model(df, tmp_path / "run")

    holdout = df[df["feature_season"].isin(HOLDOUT_SEASONS)]
    expected = float(
        np.sqrt(np.mean((holdout[OUTCOME_COLUMN].values - holdout["ppg_t"].values) ** 2))
    )
    assert result["metrics_baseline"]["rmse"] == pytest.approx(expected, rel=1e-6), (
        "the naive last-season-PPG baseline must be scored on the SAME held-out rows the "
        "model is scored on, or the comparison is between two different populations"
    )
