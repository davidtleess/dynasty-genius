"""DG-177 round 1, item 3 — annual forecast candidates on the appearance event.

Per horizon j: P(appear_j | x_t), E[points_j | appear_j, x_t], E[games_j | appear_j, x_t],
and their products. Every model is fitted on training rows whose year-j label was
closed at the cutoff; the ridge penalty is chosen leak-free inside the window; the
probability model has no tuning to leak. Baselines are training-only. Censored rows
never train anything.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval.annual_forecasts import (
    QUANTITIES,
    evaluate_horizon,
    fit_horizon,
    persistence_baselines,
)

SEASONS = [2018, 2019, 2020, 2021, 2022, 2023]


def _panel(n_players=120, seed=0, last_complete=2024):
    """Staggered careers with a year-1 and year-2 appearance process and points."""
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_players):
        skill = rng.normal(12, 4)
        start = int(rng.integers(0, len(SEASONS) - 1))
        career = SEASONS[start:start + int(rng.integers(2, 5))]
        for s in career:
            ppg = max(0.5, skill + rng.normal(0, 2))
            row = {"player_id": f"p{p:03d}", "position": "WR", "feature_season": s,
                   "ppg_t": ppg, "games_t": int(rng.integers(8, 18)), "age": float(rng.integers(22, 33)),
                   "identity_status": "resolved"}
            row["total_points_t"] = ppg * row["games_t"]
            for j in (1, 2):
                season = s + j
                row[f"season_year{j}"] = season
                censored = season > last_complete
                row[f"censored_year{j}"] = censored
                if censored:
                    row[f"appeared_year{j}"] = pd.NA
                    row[f"games_year{j}"] = np.nan
                    row[f"points_year{j}"] = np.nan
                    continue
                appear = rng.random() < 1 / (1 + np.exp(-(skill - 10) / 3))
                games = int(rng.integers(4, 18)) if appear else 0
                points = games * max(0.0, skill * 0.9 + rng.normal(0, 3)) if appear else 0.0
                row[f"appeared_year{j}"] = bool(appear)
                row[f"games_year{j}"] = float(games)
                row[f"points_year{j}"] = float(points)
            rows.append(row)
    df = pd.DataFrame(rows)
    for j in (1, 2):
        df[f"appeared_year{j}"] = df[f"appeared_year{j}"].astype("boolean")
    return df


FEATURES = ["ppg_t", "games_t", "age"]


def test_quantity_names_follow_the_agreed_contract():
    assert QUANTITIES(1) == [
        "p_appear_year1", "e_points_year1_given_appear", "e_games_year1_given_appear",
        "e_points_year1", "e_games_year1",
    ]


class TestFitHorizon:
    def test_predictions_are_probabilities_and_products(self):
        df = _panel()
        train = df[df.feature_season <= 2020]
        test = df[df.feature_season == 2022].reset_index(drop=True)
        pred, meta = fit_horizon(train, test, FEATURES, horizon=1)
        p = pred["p_appear_year1"]
        assert ((p >= 0) & (p <= 1)).all()
        np.testing.assert_allclose(pred["e_points_year1"], p * pred["e_points_year1_given_appear"])
        np.testing.assert_allclose(pred["e_games_year1"], p * pred["e_games_year1_given_appear"])
        assert meta["event"] == "appeared: >= 1 stat-row game in the season"
        assert meta["points_model"]["recipe"] == "leak_free"
        assert meta["points_model"]["alpha_selection"]["label_window_seasons"] == 1
        assert meta["n_train_observed"] > meta["n_train_appeared"] > 0

    def test_censored_and_unresolved_rows_never_train(self):
        df = _panel()
        train = df[df.feature_season <= 2022].copy()       # 2022 rows: year2 = 2024 known, fine
        test = df[df.feature_season == 2023].reset_index(drop=True)
        # poison the censored rows' labels: they must not be read
        train.loc[train["censored_year2"], "points_year2"] = 1e9
        train.loc[train["censored_year2"], "appeared_year2"] = True
        pred, meta = fit_horizon(train, test, FEATURES, horizon=2)
        assert np.isfinite(pred["e_points_year2"]).all() and pred["e_points_year2"].max() < 1e6
        assert meta["n_train_observed"] == int((~train["censored_year2"]).sum())

    def test_a_test_row_cannot_move_another_test_row(self):
        df = _panel()
        train = df[df.feature_season <= 2020]
        test = df[df.feature_season == 2022].reset_index(drop=True)
        base, _ = fit_horizon(train, test, FEATURES, horizon=1)
        mutated = test.copy()
        mutated.loc[0, "ppg_t"] += 40
        again, _ = fit_horizon(train, mutated, FEATURES, horizon=1)
        for q in QUANTITIES(1):
            np.testing.assert_array_equal(again[q][1:], base[q][1:])

    def test_training_rows_must_have_closed_labels(self):
        df = _panel()
        train = df[df.feature_season <= 2022]              # 2022's year-2 label is 2024: open at a 2023 cutoff
        test = df[df.feature_season == 2023].reset_index(drop=True)
        with pytest.raises(ValueError):
            fit_horizon(train, test, FEATURES, horizon=2, test_season=2023)


class TestBaselines:
    def test_persistence_uses_training_rows_only(self):
        df = _panel()
        train = df[df.feature_season <= 2020]
        test = df[df.feature_season == 2022].reset_index(drop=True)
        base = persistence_baselines(train, test, horizon=1)
        obs = train[~train["censored_year1"]]
        rate = float(obs["appeared_year1"].astype(float).mean())
        np.testing.assert_allclose(base["p_appear_year1"], rate)
        app = obs[obs["appeared_year1"].astype(bool)]
        retention = app["points_year1"].sum() / app["total_points_t"].sum()
        np.testing.assert_allclose(base["e_points_year1_given_appear"], test["total_points_t"] * retention)
        np.testing.assert_allclose(base["e_games_year1_given_appear"], app["games_year1"].mean())
        np.testing.assert_allclose(base["e_points_year1"], rate * base["e_points_year1_given_appear"])


class TestEvaluateHorizon:
    def test_every_fold_is_accounted_for_and_metrics_are_per_forecast_season(self):
        df = _panel()
        out, preds = evaluate_horizon(
            df, FEATURES, horizon=1, test_seasons=[2019, 2020, 2021, 2022, 2023],
            k=10, draws=20, seed=0, min_train_rows=10,
        )
        seasons = [f["test_season"] for f in out["folds"]]
        assert seasons == [2019, 2020, 2021, 2022, 2023]
        assert out["folds"][0]["skipped_reason"] is not None     # one training season: no inner fold
        evaluated = [f for f in out["folds"] if f["skipped_reason"] is None]
        assert evaluated
        f = evaluated[0]
        assert set(f["probability"]) >= {"brier", "auc", "base_rate", "baseline_brier", "calibration"}
        assert set(f["points_given_appear"]) >= {"model", "baseline", "delta_vs_baseline"}
        assert set(f["points_unconditional"]) >= {"model", "baseline", "delta_vs_baseline"}
        assert f["points_given_appear"]["model"]["n"] == f["n_test_appeared"]
        assert f["points_unconditional"]["model"]["n"] == f["n_test_observed"]
        assert out["pooled"]["probability"]["brier"] <= 1.0
        assert out["pooled"]["points_unconditional"]["model"]["topk_aggregation"] == "mean_over_forecast_seasons"
        assert set(preds.columns) >= {"player_id", "feature_season", "forecast_season", *QUANTITIES(1),
                                      "appeared_year1", "points_year1", "games_year1"}
        assert (preds["forecast_season"] == preds["feature_season"] + 1).all()
