"""A trained Engine B bundle must have exactly as many model inputs as it advertises.

Why this file exists: every `SimpleImputer` in `scripts/train_engine_b.py` is built with
sklearn's default `keep_empty_features=False`. When a feature column is all-NaN in the FIT
rows, that default silently drops the column at `fit_transform` — the imputer's output is
one column narrower than its input, the ridge is fit on the narrow matrix, and the bundle
then pickles `"features"` as the FULL list it was handed. The artifact says "I consult N
inputs"; the model has coefficients for N-1. Anything that zips `bundle["features"]` with
`model.coef_` misattributes every coefficient after the dropped slot, and a live value for
that feature at inference is discarded without a trace.

`src/dynasty_genius/eval/backtest_harness.py:489` already fits its imputer with
`keep_empty_features=True` (impute to 0.0, keep the column). Training and backtest therefore
disagree about the input set by construction the first time a column is empty in a fit
slice. Today no served bundle is affected (all four 2026-08-31 bundles are width-aligned);
DG-128 arms it by consuming `games_t_minus_*`, which is NaN for every rookie and every
left-censored (<4 game) season.

This is a SHAPE-HONESTY fix, not a model change: a column kept as constant 0.0 receives a
ridge coefficient of ~0, so predictions are numerically identical either way. What changes
is that the artifact stops lying about its inputs.
"""
from __future__ import annotations

import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import scripts.train_engine_b as train_engine_b
from scripts.train_engine_b import (
    HOLDOUT_SEASONS,
    _train_position,
    train_te_deployment_model,
)
from src.dynasty_genius.features.feature_assembly import OUTCOME_COLUMN
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_FEATURES_BY_POSITION

# A feature every position's contract carries and that is genuinely empty for a rookie
# class or a left-censored season — the shape DG-128 will feed the trainer.
EMPTY_IN_FIT = "ppg_t_minus_2"


def _frame(pos: str, n_per_season: int = 30) -> pd.DataFrame:
    """Rows for one position spanning the training seasons and both holdout seasons,
    with `EMPTY_IN_FIT` all-NaN in the FIT seasons only. The holdout rows keep real
    values so the drop is a fact about the fit slice, not about column existence."""
    rng = np.random.default_rng(20260901)
    seasons = [2018, 2019, 2020, 2021, *HOLDOUT_SEASONS]
    rows = []
    for season in seasons:
        for i in range(n_per_season):
            ppg = float(rng.uniform(2.0, 14.0))
            row = {
                "player_id": f"{pos}{season}{i}",
                "position": pos,
                "feature_season": season,
                "training_eligible": True,
                "ppg_t": ppg,
                OUTCOME_COLUMN: ppg * 0.9 + float(rng.normal(0, 1.5)),
            }
            for feature in ENGINE_B_FEATURES_BY_POSITION[pos]:
                row.setdefault(feature, float(rng.uniform(0.1, 0.9)))
            row["ppg_t"] = ppg
            if season not in HOLDOUT_SEASONS:
                row[EMPTY_IN_FIT] = np.nan
            rows.append(row)
    df = pd.DataFrame(rows)
    assert df.loc[~df["feature_season"].isin(HOLDOUT_SEASONS), EMPTY_IN_FIT].isna().all()
    return df


def _assert_bundle_width_is_honest(bundle: dict, df: pd.DataFrame) -> None:
    features = bundle["features"]
    imputer = bundle["imputer"]
    model = bundle["model"]
    assert EMPTY_IN_FIT in features, "the test frame must exercise the empty column"

    transformed = imputer.transform(df[features].head(5))
    assert transformed.shape[1] == len(features), (
        f"the imputer emits {transformed.shape[1]} columns for {len(features)} advertised "
        f"features — `{EMPTY_IN_FIT}` was dropped at fit because it was all-NaN in the fit "
        "slice; the bundle advertises an input the model never saw"
    )
    assert model.n_features_in_ == len(features), (
        "the ridge was fit on a narrower matrix than the bundle's feature list"
    )
    assert list(imputer.get_feature_names_out()) == list(features), (
        "the imputer's surviving feature names must be exactly the advertised list, in order"
    )
    assert not np.isnan(imputer.statistics_).any(), (
        "an all-NaN fit column must be imputed to a real constant (0.0), not left as NaN"
    )


def test_served_v2_path_keeps_an_empty_fit_column(tmp_path: Path, monkeypatch) -> None:
    """`_train_position` produced every bundle in v2_manifest.json; it must not narrow."""
    monkeypatch.setattr(train_engine_b, "ROOT", tmp_path)
    df = _frame("WR")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = _train_position("WR", df, run_dir, {}, {})

    assert not result.get("skipped"), result
    with open(run_dir / "wr_v2.pkl", "rb") as f:
        bundle = pickle.load(f)
    _assert_bundle_width_is_honest(bundle, df)


def test_te_v3_path_keeps_an_empty_fit_column(tmp_path: Path) -> None:
    """`train_te_deployment_model` writes te_v3.pkl through `_fit_position_ridge`."""
    df = _frame("TE")

    result = train_te_deployment_model(df, tmp_path / "run")

    assert not result.get("skipped"), result
    with open(tmp_path / "run" / "te_v3.pkl", "rb") as f:
        bundle = pickle.load(f)
    _assert_bundle_width_is_honest(bundle, df)


def test_training_on_an_empty_fit_column_is_not_a_warning(tmp_path: Path, monkeypatch) -> None:
    """sklearn marks the drop only with `UserWarning: Skipping features without any
    observed values`. With the column kept, nothing is skipped and nothing warns — the
    fix must be visible at fit time, not only in the artifact."""
    monkeypatch.setattr(train_engine_b, "ROOT", tmp_path)
    df = _frame("RB")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _train_position("RB", df, run_dir, {}, {})

    skipped = [w for w in caught if "Skipping features without any observed values" in str(w.message)]
    assert not skipped, [str(w.message) for w in skipped]


def test_v1_1_control_keeps_an_empty_fit_column(tmp_path: Path, monkeypatch) -> None:
    """The unified v1.1 control is validation-only and never promoted, but it is the
    third imputer in the file and the flag must not drift between the three sites."""
    from scripts.train_engine_b import FEATURES_UNIFIED, train_v1_1_control

    monkeypatch.setattr(train_engine_b, "ROOT", tmp_path)

    df = pd.concat([_frame("WR"), _frame("RB")], ignore_index=True)
    for feature in FEATURES_UNIFIED:
        if feature not in df.columns:
            df[feature] = 0.5
    fit = ~df["feature_season"].isin(HOLDOUT_SEASONS)
    df.loc[fit, EMPTY_IN_FIT] = np.nan
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    train_v1_1_control(df, run_dir)

    pkls = list(run_dir.glob("*.pkl"))
    assert len(pkls) == 1, pkls
    with open(pkls[0], "rb") as f:
        bundle = pickle.load(f)
    _assert_bundle_width_is_honest(bundle, df)
