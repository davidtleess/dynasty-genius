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


# ── round 2, item 4: one explicit selection policy, chosen on closed inner folds ──

from src.dynasty_genius.eval.annual_forecasts import (  # noqa: E402
    POLICY_SPACE,
    compose_policy,
    evaluate_horizon_policy,
    fit_policy,
)


def test_policy_space_is_baseline_candidate_and_a_bounded_blend():
    assert POLICY_SPACE == ("baseline", "candidate", "blend_0.25", "blend_0.5", "blend_0.75")


def test_compose_policy_is_the_named_convex_combination():
    c = np.array([10.0, 20.0])
    b = np.array([0.0, 40.0])
    np.testing.assert_allclose(compose_policy(c, b, "baseline"), b)
    np.testing.assert_allclose(compose_policy(c, b, "candidate"), c)
    np.testing.assert_allclose(compose_policy(c, b, "blend_0.25"), 0.25 * c + 0.75 * b)
    np.testing.assert_allclose(compose_policy(c, b, "blend_0.75"), 0.75 * c + 0.25 * b)
    with pytest.raises(ValueError):
        compose_policy(c, b, "blend_0.9")


class TestFitPolicy:
    def test_selection_happens_on_closed_inner_folds_and_names_a_policy_per_quantity(self):
        df = _panel()
        train = df[df.feature_season <= 2021]
        test = df[df.feature_season == 2023].reset_index(drop=True)
        pred, meta = fit_policy(train, test, FEATURES, horizon=1, test_season=2023)
        assert set(meta["policy_by_quantity"]) == {"p_appear", "points_given_appear", "games_given_appear"}
        assert all(v in POLICY_SPACE for v in meta["policy_by_quantity"].values())
        assert meta["inner_folds"], "no inner fold means no selection happened"
        for fold in meta["inner_folds"]:
            assert max(fold["train_seasons"]) + 1 <= fold["validation_season"]
        assert meta["selection_criterion"] == {"p_appear": "brier", "points_given_appear": "mse",
                                               "games_given_appear": "mse"}
        for q in QUANTITIES(1):
            assert np.isfinite(pred[q]).all()
        np.testing.assert_allclose(pred["e_points_year1"], pred["p_appear_year1"] * pred["e_points_year1_given_appear"])
        assert meta["final_fit_parity"] == "fit_policy is the function final scoring calls"

    def test_the_selected_policy_reproduces_its_composition_on_the_test_rows(self):
        df = _panel()
        train = df[df.feature_season <= 2021]
        test = df[df.feature_season == 2023].reset_index(drop=True)
        pred, meta = fit_policy(train, test, FEATURES, horizon=1)
        cand, _ = fit_horizon(train, test, FEATURES, horizon=1)
        base = persistence_baselines(train, test, horizon=1)
        chosen = meta["policy_by_quantity"]["points_given_appear"]
        np.testing.assert_allclose(
            pred["e_points_year1_given_appear"],
            compose_policy(cand["e_points_year1_given_appear"], base["e_points_year1_given_appear"], chosen),
        )

    def test_test_labels_cannot_influence_the_selection(self):
        df = _panel()
        train = df[df.feature_season <= 2021]
        test = df[df.feature_season == 2023].reset_index(drop=True)
        _, meta = fit_policy(train, test, FEATURES, horizon=1)
        poisoned = test.copy()
        poisoned["points_year1"] = 1e6
        poisoned["appeared_year1"] = True
        _, meta2 = fit_policy(train, poisoned, FEATURES, horizon=1)
        assert meta["policy_by_quantity"] == meta2["policy_by_quantity"]
        assert meta["inner_scores"] == meta2["inner_scores"]

    def test_it_refuses_when_no_inner_fold_can_be_built(self):
        df = _panel()
        train = df[df.feature_season <= 2019]           # 2018-2019: no closed inner fold with a fittable candidate
        test = df[df.feature_season == 2021].reset_index(drop=True)
        from src.dynasty_genius.eval.veteran_candidate import RecipeCannotFit
        with pytest.raises(RecipeCannotFit):
            fit_policy(train, test, FEATURES, horizon=1)


class TestEvaluateHorizonPolicy:
    def test_policy_evidence_is_separate_from_exploratory_arm_comparisons(self):
        df = _panel()
        out, preds = evaluate_horizon_policy(
            df, FEATURES, horizon=1, test_seasons=[2020, 2021, 2022, 2023], k=10, draws=20, seed=0,
            min_train_rows=10,
        )
        assert [f["test_season"] for f in out["folds"]] == [2020, 2021, 2022, 2023]
        evaluated = [f for f in out["folds"] if f["skipped_reason"] is None]
        assert evaluated
        f = evaluated[0]
        assert set(f["policy"]["policy_by_quantity"]) == {"p_appear", "points_given_appear", "games_given_appear"}
        assert set(f["policy"]) >= {"probability", "points_given_appear", "games_given_appear", "points_unconditional"}
        assert set(f["exploratory_candidate"]) >= {"probability", "points_given_appear", "points_unconditional"}
        assert out["pooled"]["policy"]["points_unconditional"]["delta_vs_baseline"]["topk_aggregation"] == "mean_over_forecast_seasons"
        assert out["evidence"] == "policy"      # the policy's outer score is the evidence; arms are exploratory
        assert set(preds.columns) >= {"player_id", "forecast_season", "policy_e_points_year1", "candidate_e_points_year1",
                                      "baseline_e_points_year1"}
