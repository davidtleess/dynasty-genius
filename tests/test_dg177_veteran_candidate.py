"""DG-177 — honest historical candidate evaluation for veteran forecasts.

These tests pin the behaviours the ticket names as non-negotiable:
  * a training row's outcome window must be fully known before the test forecast
    (a future label is REFUSED, not silently dropped);
  * candidate feature lists that carry future-season data or third-party
    projections/rankings are refused before any fit;
  * every transform is fitted inside the training window only;
  * uncertainty on a comparison is the bootstrapped DIFFERENCE, resampling players;
  * a skipped fold is written as skipped, never dropped;
  * a run directory is never overwritten.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval.veteran_candidate import (
    LABEL_WINDOW_SEASONS,
    FutureLabelError,
    admissible_train_seasons,
    assert_labels_known,
    build_folds,
    fit_predict_arm,
    paired_cluster_bootstrap,
    run_candidate_evaluation,
    score_predictions,
    validate_candidate_features,
    write_run_artifact,
)

SEASONS = [2018, 2019, 2020, 2021, 2022, 2023]


# ── the cutoff rule ───────────────────────────────────────────────────────────

class TestAdmissibleTrainSeasons:
    def test_label_window_is_two_seasons(self):
        assert LABEL_WINDOW_SEASONS == 2

    def test_labels_known_at_cutoff_admits_t_plus_2_equal_to_test(self):
        # Row 2019 is labelled from 2020-2021; forecasting after 2021 knows both.
        assert admissible_train_seasons(SEASONS, 2021) == [2018, 2019]

    def test_strict_rule_reproduces_dg162(self):
        # DG-162's earn.py used feature_season <= s-3.
        assert admissible_train_seasons(
            SEASONS, 2021, rule="window_closed_before_test"
        ) == [2018]

    def test_unknown_rule_is_refused(self):
        with pytest.raises(ValueError):
            admissible_train_seasons(SEASONS, 2021, rule="whatever")

    def test_agrees_with_the_deployed_trainer_for_a_single_test_season(self):
        # The deployed trainer already encodes DG-026; the two definitions must not drift.
        from scripts.train_engine_b import admissible_training_seasons

        for s in (2020, 2021, 2022, 2023):
            assert admissible_train_seasons(SEASONS, s) == admissible_training_seasons(
                SEASONS, [s], rule="no_shared_outcome_season"
            )
            assert admissible_train_seasons(
                SEASONS, s, rule="window_closed_before_test"
            ) == admissible_training_seasons(SEASONS, [s], rule="window_closed_before_test")


class TestFutureLabelsAreRefused:
    def test_a_training_row_whose_window_is_open_raises(self):
        train = pd.DataFrame({"feature_season": [2018, 2020], "y": [1.0, 2.0]})
        with pytest.raises(FutureLabelError):
            assert_labels_known(train, test_season=2021)

    def test_a_closed_window_passes(self):
        train = pd.DataFrame({"feature_season": [2018, 2019], "y": [1.0, 2.0]})
        assert_labels_known(train, test_season=2021)  # no raise


# ── the feature gate ──────────────────────────────────────────────────────────

class TestCandidateFeatureGate:
    @pytest.mark.parametrize(
        "bad",
        ["ppg_t1", "games_t2", "ppg_next", "future_ppg", "snap_share_future"],
    )
    def test_future_season_columns_are_refused(self, bad):
        with pytest.raises(ValueError):
            validate_candidate_features(["ppg_t", "age", bad])

    @pytest.mark.parametrize(
        "bad",
        ["sleeper_projection", "consensus_rank", "fantasypros_ecr", "ktc_value", "adp",
         "projected_points", "dynastynerds_rank"],
    )
    def test_third_party_projections_and_rankings_are_refused(self, bad):
        with pytest.raises(ValueError):
            validate_candidate_features(["ppg_t", "age", bad])

    def test_the_baseline_and_the_opportunity_family_pass(self):
        validate_candidate_features(["ppg_t", "games_t", "age"])
        validate_candidate_features(
            ["ppg_t", "games_t", "age", "opp_targets_pg", "opp_air_yards_pg",
             "opp_carries_pg", "opp_pass_attempts_pg"]
        )


# ── fitting inside the window ─────────────────────────────────────────────────

def _panel(n_players=40, seasons=SEASONS, seed=0, positions=("WR",)):
    rng = np.random.default_rng(seed)
    rows = []
    for pos in positions:
        for p in range(n_players):
            skill = rng.normal(10, 3)
            for s in seasons:
                x1 = skill + rng.normal(0, 1)
                x2 = rng.normal(0, 1)
                y = 0.8 * x1 + 0.5 * x2 + rng.normal(0, 1)
                rows.append({
                    "player_id": f"{pos}-{p:03d}", "position": pos, "feature_season": s,
                    "x1": x1, "x2": x2, "avg_ppg_t1_t2": y, "training_eligible": True,
                })
    return pd.DataFrame(rows)


class TestFitPredictArm:
    def test_changing_one_test_row_cannot_move_another_prediction(self):
        df = _panel()
        train = df[df.feature_season <= 2020]
        test = df[df.feature_season == 2022].reset_index(drop=True)
        base = fit_predict_arm(train, test, ["x1", "x2"])
        mutated = test.copy()
        mutated.loc[0, "x1"] += 50.0
        mutated.loc[0, "x2"] = np.nan
        again = fit_predict_arm(train, mutated, ["x1", "x2"])
        # row 0 moved; every other row is bit-identical -> nothing was fitted on test
        assert again[0] != base[0]
        np.testing.assert_array_equal(again[1:], base[1:])

    def test_a_nan_in_test_is_imputed_from_train_not_dropped(self):
        df = _panel()
        train = df[df.feature_season <= 2020]
        test = df[df.feature_season == 2022].reset_index(drop=True)
        test.loc[3, "x1"] = np.nan
        pred = fit_predict_arm(train, test, ["x1", "x2"])
        assert len(pred) == len(test)
        assert np.isfinite(pred).all()

    def test_an_all_nan_feature_in_train_does_not_crash(self):
        df = _panel()
        train = df[df.feature_season <= 2020].copy()
        train["x2"] = np.nan
        test = df[df.feature_season == 2022]
        pred = fit_predict_arm(train, test, ["x1", "x2"])
        assert np.isfinite(pred).all()


# ── folds ─────────────────────────────────────────────────────────────────────

class TestBuildFolds:
    def test_thin_fold_is_reported_as_skipped_not_dropped(self):
        df = _panel(n_players=40)  # 40 rows per season
        folds = build_folds(df, test_seasons=[2020, 2021, 2022], min_train_rows=60)
        by_season = {f.test_season: f for f in folds}
        assert set(by_season) == {2020, 2021, 2022}
        assert by_season[2020].skipped_reason is not None      # only 2018 -> 40 rows
        assert by_season[2020].n_train == 40
        assert by_season[2021].skipped_reason is None
        assert by_season[2021].train_seasons == [2018, 2019]
        assert by_season[2022].train_seasons == [2018, 2019, 2020]

    def test_folds_count_players_as_well_as_rows(self):
        df = _panel(n_players=40)
        (fold,) = build_folds(df, test_seasons=[2022], min_train_rows=60)
        assert fold.n_train_players == 40
        assert fold.n_test_players == 40
        assert fold.n_test == 40


# ── metrics and the paired bootstrap ──────────────────────────────────────────

class TestScoreAndBootstrap:
    def test_perfect_prediction_scores_perfectly(self):
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        m = score_predictions(y, y, k=3)
        assert m["n"] == 6
        assert m["rmse"] == pytest.approx(0.0)
        assert m["r2"] == pytest.approx(1.0)
        assert m["spearman"] == pytest.approx(1.0)
        assert m["topk_overlap"] == pytest.approx(1.0)

    def test_identical_arms_have_a_zero_difference_with_a_zero_width_interval(self):
        rng = np.random.default_rng(0)
        y = rng.normal(size=200)
        a = y + rng.normal(scale=0.5, size=200)
        groups = np.repeat(np.arange(50), 4)
        out = paired_cluster_bootstrap(y, a, a, groups, draws=200, seed=0, k=20)
        assert out["delta_rmse"]["point"] == 0.0
        assert out["delta_rmse"]["ci90"] == [0.0, 0.0]

    def test_a_clearly_worse_arm_has_an_interval_that_excludes_zero(self):
        rng = np.random.default_rng(1)
        y = rng.normal(size=400)
        a = y + rng.normal(scale=0.3, size=400)
        b = y + rng.normal(scale=1.5, size=400)
        groups = np.repeat(np.arange(100), 4)
        out = paired_cluster_bootstrap(y, a, b, groups, draws=300, seed=0, k=40)
        lo, hi = out["delta_rmse"]["ci90"]
        assert lo > 0.0  # b - a in RMSE is positive: b is worse
        assert out["delta_r2"]["ci90"][1] < 0.0

    def test_bootstrap_is_deterministic_for_a_seed(self):
        rng = np.random.default_rng(2)
        y = rng.normal(size=100)
        a = y + rng.normal(scale=0.5, size=100)
        b = y + rng.normal(scale=0.7, size=100)
        groups = np.repeat(np.arange(25), 4)
        one = paired_cluster_bootstrap(y, a, b, groups, draws=100, seed=7, k=10)
        two = paired_cluster_bootstrap(y, a, b, groups, draws=100, seed=7, k=10)
        assert one == two


# ── the whole evaluation ──────────────────────────────────────────────────────

class TestRunCandidateEvaluation:
    def test_every_arm_is_retained_and_every_fold_is_accounted_for(self):
        df = _panel(n_players=40, positions=("WR",))
        arms = {"x1_only": ["x1"], "x1_and_x2": ["x1", "x2"], "noise": ["x2"]}
        result, predictions = run_candidate_evaluation(
            df, arms=arms, test_seasons=[2020, 2021, 2022, 2023],
            reference_arms=["x1_only", "x1_and_x2"], min_train_rows=60, draws=50, seed=0,
            k_by_position={"WR": 10},
        )
        wr = result["positions"]["WR"]
        assert [f["test_season"] for f in wr["folds"]] == [2020, 2021, 2022, 2023]
        assert wr["folds"][0]["skipped_reason"] is not None
        assert set(wr["pooled"]) == set(arms)             # the losing arm is retained
        # one block of paired differences per reference arm, against every OTHER arm
        assert set(wr["deltas"]) == {"x1_only", "x1_and_x2"}
        assert set(wr["deltas"]["x1_only"]) == {"x1_and_x2", "noise"}
        assert set(wr["deltas"]["x1_and_x2"]) == {"x1_only", "noise"}
        assert set(wr["folds"][1]["deltas"]) == {"x1_only", "x1_and_x2"}
        # a reference compared with itself would be a tautology; it is not emitted
        assert "x1_only" not in wr["deltas"]["x1_only"]
        # the informative arm beats the reference, the noise arm loses
        assert wr["pooled"]["x1_and_x2"]["rmse"] < wr["pooled"]["x1_only"]["rmse"]
        assert wr["pooled"]["noise"]["rmse"] > wr["pooled"]["x1_only"]["rmse"]
        # predictions are row-level, one per (row, arm), over the evaluated folds only
        n_test_rows = len(df[df.feature_season.isin([2021, 2022, 2023])])
        assert len(predictions) == n_test_rows * len(arms)
        assert set(predictions.columns) >= {
            "player_id", "position", "feature_season", "arm", "y_true", "y_pred"
        }

    def test_an_unknown_reference_arm_is_refused(self):
        df = _panel()
        with pytest.raises(ValueError):
            run_candidate_evaluation(
                df, arms={"a": ["x1"]}, test_seasons=[2022],
                reference_arms=["a", "nope"], k_by_position={"WR": 10},
            )

    def test_a_prohibited_arm_is_refused_before_anything_is_fitted(self):
        df = _panel()
        df["sleeper_projection"] = 1.0
        with pytest.raises(ValueError):
            run_candidate_evaluation(
                df, arms={"leak": ["x1", "sleeper_projection"]}, test_seasons=[2022],
                reference_arms=["leak"], k_by_position={"WR": 10},
            )


class TestWriteRunArtifact:
    def test_writes_results_report_and_predictions(self, tmp_path):
        out = tmp_path / "20260906T120000Z" / "dg177_veteran_candidate"
        results = {"positions": {}, "config": {"rule": "labels_known_at_cutoff"}}
        preds = pd.DataFrame({"player_id": ["a"], "position": ["WR"], "feature_season": [2022],
                              "arm": ["x"], "y_true": [1.0], "y_pred": [1.1]})
        written = write_run_artifact(out, results, preds, provenance={"git_head": "abc"},
                                     report_md="# report\n")
        assert (out / "results.json").exists()
        assert (out / "predictions.csv").exists()
        assert (out / "report.md").exists()
        blob = json.loads((out / "results.json").read_text())
        assert blob["provenance"] == {"git_head": "abc"}
        assert blob["config"]["rule"] == "labels_known_at_cutoff"
        assert set(written) == {"results.json", "predictions.csv", "report.md"}

    def test_never_overwrites_an_existing_run_directory(self, tmp_path):
        out = tmp_path / "run"
        out.mkdir()
        (out / "results.json").write_text("{}")
        with pytest.raises(FileExistsError):
            write_run_artifact(out, {"positions": {}}, pd.DataFrame(), provenance={},
                               report_md="")
