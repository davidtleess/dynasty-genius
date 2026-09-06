"""DG-165 — the draft-capital rookie candidate: labels, cutoffs, conditioning, coverage.

Every test here is written against SYNTHETIC frames (no network, no shared data). Each
test names the production change that would make it fail:

* nth-largest bar → a `rank == N` lookup would skip a tied bar and drop a season silently
  (the DG-164 WR-2024 defect, 284 rows gone with no error).
* zero-game prospect labelled 0 → applying `censored_incomplete_arc` or an inner join to
  the panel would delete him and return P ≈ 1 (DG-165 feasibility gate landmine).
* NaN beyond the cutoff → training on labels observed through 2025 while forecasting 2019
  (the preserved study's split) is exactly what this refuses.
* walk-forward bound `max(train class) <= T - h` → the leak the review named.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.models.leakage import find_leaking_columns
from src.dynasty_genius.rookie.cohort import draft_cohort_from_picks
from src.dynasty_genius.rookie.evaluate import walk_forward_splits
from src.dynasty_genius.rookie.labels import (
    horizon_labels,
    played_season_keys,
    qualifying_season_keys,
)
from src.dynasty_genius.rookie.model import FEATURE_COLUMNS, RookieCapitalModel
from src.dynasty_genius.rookie.run_dir import create_run_dir
from src.dynasty_genius.rookie.score import score_class


# ----------------------------------------------------------------------------- fixtures
def _panel(rows):
    """rows: (player_id, position, season, points, games)."""
    return pd.DataFrame(rows, columns=["player_id", "position", "season", "points", "games"])


def _cohort(rows):
    """rows: (gsis_id, draft_season, position, pick, round, age_at_draft)."""
    return pd.DataFrame(
        rows,
        columns=["gsis_id", "draft_season", "position", "pick", "round", "age_at_draft"],
    )


# ----------------------------------------------------------------------------- labels
def test_qualifying_keys_use_the_nth_largest_so_a_tie_at_the_bar_admits_both_players():
    # Bar N=2 at WR: points 10, 9, 9, 8. rank(method="min") gives 1,2,2,4 — a rank==2
    # lookup exists here, but with 10, 9, 9, 9, 8 and N=3 the rank==3 lookup returns
    # nothing. N-th largest always exists. Both tied players must qualify.
    panel = _panel(
        [
            ("a", "WR", 2020, 10.0, 17),
            ("b", "WR", 2020, 9.0, 17),
            ("c", "WR", 2020, 9.0, 17),
            ("d", "WR", 2020, 8.0, 17),
        ]
    )
    keys = qualifying_season_keys(panel, bar={"WR": 2})
    assert keys == {("a", 2020), ("b", 2020), ("c", 2020)}


def test_qualifying_keys_raise_when_a_season_has_fewer_players_than_the_bar():
    # A (season, position) group smaller than the bar means the panel is broken, not that
    # nobody qualified. Fail loud rather than return an empty set that reads as a result.
    panel = _panel([("a", "TE", 2020, 10.0, 17)])
    with pytest.raises(ValueError, match="TE 2020"):
        qualifying_season_keys(panel, bar={"TE": 21})


def test_played_keys_are_seasons_with_at_least_one_game():
    panel = _panel([("a", "RB", 2020, 0.0, 1), ("b", "RB", 2020, 0.0, 0)])
    assert played_season_keys(panel) == {("a", 2020)}


def test_horizon_labels_zero_game_prospect_is_labelled_zero_not_dropped():
    cohort = _cohort([("washout", 2015, "WR", 200, 6, 22.0)])
    labels = horizon_labels(
        cohort, qualifying=set(), played=set(), horizons=(1, 2, 3), last_completed_season=2020
    )
    row = labels.set_index("gsis_id").loc["washout"]
    assert len(labels) == 1
    assert (row["q_1"], row["q_2"], row["q_3"]) == (0, 0, 0)
    assert (row["n_1"], row["n_2"], row["n_3"]) == (0, 0, 0)
    assert (row["played_1"], row["played_2"], row["played_3"]) == (0, 0, 0)


def test_horizon_labels_count_only_seasons_inside_the_window():
    # Qualifies in rookie season and in season 4; h=2 window is seasons 2015-2016.
    cohort = _cohort([("p", 2015, "RB", 10, 1, 21.0)])
    qual = {("p", 2015), ("p", 2018)}
    labels = horizon_labels(
        cohort, qualifying=qual, played=qual, horizons=(1, 2, 4), last_completed_season=2025
    )
    row = labels.iloc[0]
    assert (row["q_1"], row["n_1"]) == (1, 1)
    assert (row["q_2"], row["n_2"]) == (1, 1)
    assert (row["q_4"], row["n_4"]) == (1, 2)


def test_horizon_labels_are_missing_when_the_window_is_not_complete_at_the_cutoff():
    # Class 2019 at cutoff 2020 (last completed season): h=1 (2019) and h=2 (2019-20) are
    # observable, h=3 (2019-21) is NOT — it must be NaN, never 0.
    cohort = _cohort([("p", 2019, "QB", 1, 1, 22.0)])
    labels = horizon_labels(
        cohort, qualifying=set(), played=set(), horizons=(1, 2, 3), last_completed_season=2020
    )
    row = labels.iloc[0]
    assert row["q_1"] == 0 and row["q_2"] == 0
    assert np.isnan(row["q_3"]) and np.isnan(row["n_3"]) and np.isnan(row["played_3"])


# ----------------------------------------------------------------------------- cohort
def test_cohort_from_picks_keeps_a_no_id_pick_who_never_played_as_a_washout():
    # Measured 2026-09-06: 107 of the 108 skill picks without a gsis_id have ZERO career
    # games in PFR. Dropping them deletes washouts — the survivorship landmine again. A
    # no-id pick with zero games stays, under a synthetic id, and labels to 0. A no-id
    # pick who DID play cannot be labelled (no join key) and is dropped — and counted.
    picks = pd.DataFrame(
        {
            "season": [2020, 2020, 2020, 2020, 2020],
            "round": [1, 1, 2, 7, 7],
            "pick": [1, 2, 40, 250, 251],
            "position": ["QB", "OT", "WR", "RB", "TE"],
            "gsis_id": ["00-1", "00-2", None, "00-4", None],
            "age": [22.0, 21.0, 22.0, np.nan, 23.0],
            "team": ["CIN", "WAS", "DET", "SEA", "KAN"],
            "pfr_player_name": ["A", "B", "C", "D", "E"],
            "games": [40, 40, 0, 12, 30],
        }
    )
    cohort, report = draft_cohort_from_picks(picks, seasons=range(2020, 2021))
    assert list(cohort["gsis_id"]) == ["00-1", "nogsis:2020:40", "00-4"]
    assert list(cohort["id_status"]) == ["gsis", "no_gsis_never_played", "gsis"]
    assert list(cohort.columns[:6]) == [
        "gsis_id", "draft_season", "position", "pick", "round", "age_at_draft",
    ]
    assert report["skill_rows"] == 4
    assert report["no_gsis_kept_as_washout"] == 1
    assert report["no_gsis_played_dropped_unlabelable"] == 1
    assert report["missing_age"] == 1


# ----------------------------------------------------------------------------- cutoff
def test_walk_forward_training_classes_never_need_a_season_at_or_after_the_forecast_year():
    # Forecast T=2020, pre-season. A class c contributes at horizon h only if the whole
    # window c..c+h-1 ended by 2019, i.e. c <= T - h. Class T is the test set.
    cohort = _cohort([(f"p{c}", c, "WR", 50, 2, 22.0) for c in range(2010, 2023)])
    splits = walk_forward_splits(
        cohort, qualifying=set(), played=set(), horizons=(1, 3, 5),
        forecast_years=(2020,), last_completed_season_today=2025, min_train_rows=1,
    )
    by_h = {(s.forecast_year, s.horizon): s for s in splits}
    assert by_h[(2020, 1)].train["draft_season"].max() == 2019
    assert by_h[(2020, 3)].train["draft_season"].max() == 2017
    assert by_h[(2020, 5)].train["draft_season"].max() == 2015
    for s in splits:
        assert set(s.test["draft_season"]) == {2020}
        assert s.train[f"q_{s.horizon}"].notna().all()


def test_walk_forward_leak_canary_a_breakout_in_season_T_is_invisible_to_training_at_T():
    # Class 2019 player qualifies ONLY in 2020. Forecasting 2020 with h=2 his window is
    # 2019-2020, incomplete at cutoff 2019 → he must be absent from training. With h=1
    # his window is 2019 alone → present, labelled 0.
    cohort = _cohort(
        [("canary", 2019, "RB", 30, 1, 21.0)]
        + [(f"f{c}", c, "RB", 30, 1, 21.0) for c in range(2010, 2019)]
        + [("t", 2020, "RB", 30, 1, 21.0)]
    )
    qual = {("canary", 2020)}
    splits = walk_forward_splits(
        cohort, qualifying=qual, played=qual, horizons=(1, 2),
        forecast_years=(2020,), last_completed_season_today=2021, min_train_rows=1,
    )
    by_h = {s.horizon: s for s in splits}
    assert "canary" not in set(by_h[2].train["gsis_id"])
    canary_h1 = by_h[1].train.set_index("gsis_id").loc["canary"]
    assert canary_h1["q_1"] == 0


def test_walk_forward_test_labels_are_only_those_observable_today():
    # Today's last completed season is 2021. Forecast T=2020: h=1 (2020) and h=2 (2020-21)
    # are gradable, h=3 (2020-22) is not → no split is produced for it.
    cohort = _cohort([(f"p{c}", c, "TE", 100, 4, 23.0) for c in range(2010, 2021)])
    splits = walk_forward_splits(
        cohort, qualifying=set(), played=set(), horizons=(1, 2, 3),
        forecast_years=(2020,), last_completed_season_today=2021, min_train_rows=1,
    )
    assert sorted(s.horizon for s in splits) == [1, 2]


# ----------------------------------------------------------------------------- model
def _training_frame(seed=0, n=400):
    rng = np.random.default_rng(seed)
    pick = rng.integers(1, 260, n)
    pos = rng.choice(["QB", "RB", "WR", "TE"], n)
    age = rng.normal(22.5, 0.9, n).round(1)
    frame = _cohort(
        [(f"p{i}", 2010 + (i % 8), pos[i], int(pick[i]), int(np.ceil(pick[i] / 32)), age[i])
         for i in range(n)]
    )
    p = 1 / (1 + np.exp((np.log(pick) - 4.0)))  # higher picks (small numbers) qualify more
    # Per-season qualification first (what horizon_labels emits as qy_j), then the
    # window labels derived from it, so the fixture has the same internal consistency
    # as a real label frame: q_h = any(qy_1..h), n_h = sum(qy_1..h).
    by_year = np.column_stack([(rng.random(n) < p).astype(int) for _ in range(3)])
    for j in range(1, 4):
        frame[f"qy_{j}"] = by_year[:, j - 1]
    for h in (1, 2, 3):
        frame[f"q_{h}"] = by_year[:, :h].max(axis=1)
        frame[f"n_{h}"] = by_year[:, :h].sum(axis=1)
        frame[f"played_{h}"] = np.maximum(frame[f"q_{h}"], (rng.random(n) < 0.7).astype(int))
    return frame


def test_feature_columns_are_draft_capital_only_and_carry_no_market_column():
    assert set(FEATURE_COLUMNS) <= {"pick", "round", "age_at_draft", "position"}
    assert find_leaking_columns(_training_frame()[list(FEATURE_COLUMNS)]) == []


def test_model_predictions_are_probabilities_and_expected_seasons_bounded_by_horizon():
    train = _training_frame()
    model = RookieCapitalModel(horizons=(1, 2, 3)).fit(train)
    pred = model.predict(train.head(50))
    for h in (1, 2, 3):
        assert pred[f"p_qual_h{h}"].between(0, 1).all()
        assert pred[f"p_played_h{h}"].between(0, 1).all()
        assert pred[f"e_qual_seasons_h{h}"].between(0, h).all()


def test_model_ranks_the_first_pick_above_the_last_pick():
    train = _training_frame()
    model = RookieCapitalModel(horizons=(1,)).fit(train)
    probe = _cohort([("first", 2026, "WR", 1, 1, 22.0), ("last", 2026, "WR", 255, 7, 22.0)])
    pred = model.predict(probe).set_index("gsis_id")
    assert pred.loc["first", "p_qual_h1"] > pred.loc["last", "p_qual_h1"]


# ----------------------------------------------------------------------------- scoring
def test_score_class_gives_every_prospect_a_row_and_names_an_imputed_age():
    train = _training_frame()
    model = RookieCapitalModel(horizons=(1, 2)).fit(train)
    rookies = _cohort(
        [("a", 2026, "QB", 1, 1, 22.0), ("b", 2026, "TE", 16, 1, np.nan), ("c", 2026, "RB", 250, 7, 23.0)]
    )
    scored = score_class(model, rookies)
    assert len(scored) == 3
    assert set(scored["gsis_id"]) == {"a", "b", "c"}
    status = scored.set_index("gsis_id")["coverage_status"]
    assert status["a"] == "scored"
    assert status["b"] == "scored_age_imputed"
    assert scored["p_qual_h1"].notna().all()


# ----------------------------------------------------------------------------- run dir
def test_create_run_dir_refuses_to_overwrite_an_existing_run(tmp_path):
    first = create_run_dir(tmp_path, run_id="20260906T120000Z")
    assert first.is_dir()
    with pytest.raises(FileExistsError):
        create_run_dir(tmp_path, run_id="20260906T120000Z")


# ----------------------------------------------------------------------------- report
def test_evaluation_markdown_names_every_horizon_and_every_absent_pair():
    from src.dynasty_genius.rookie.report import render_evaluation_markdown

    evaluation = {
        "pooled_by_horizon": {
            1: {"forecast_years": [2010, 2011], "n": 160,
                "qual": {"n": 160, "prevalence": 0.3, "auc": 0.81, "brier": 0.17, "log_loss": 0.5,
                         "brier_base_rate": 0.21, "log_loss_base_rate": 0.61},
                "qual_auc_ci90": [0.77, 0.85], "qual_brier_ci90": [0.15, 0.19],
                "played": {"n": 160, "prevalence": 0.8, "auc": 0.7, "brier": 0.15, "log_loss": 0.45,
                           "brier_base_rate": 0.16, "log_loss_base_rate": 0.5},
                "seasons": {"n": 160, "mean_actual": 0.3, "mean_predicted": 0.31, "rmse": 0.4,
                            "rmse_base_rate": 0.46, "bias": 0.01},
                "calibration_qual": [{"bin": "0.00-0.10", "n": 40, "predicted": 0.05, "actual": 0.05}],
                "by_position": {"QB": {"n": 20, "prevalence": 0.4, "auc": 0.9, "brier": 0.1, "log_loss": 0.3,
                                       "brier_base_rate": 0.24, "log_loss_base_rate": 0.67,
                                       "seasons": {"n": 20, "mean_actual": 0.4, "mean_predicted": 0.4,
                                                   "rmse": 0.3, "rmse_base_rate": 0.5, "bias": 0.0}}},
                "by_round": {1: {"n": 30, "actual_qual_rate": 0.7, "predicted_qual_rate": 0.68,
                                 "actual_seasons": 0.7, "predicted_seasons": 0.7}}},
        },
        "per_split": [],
        "absent_pairs": [{"forecast_year": 2024, "horizon": 5, "reason": "window 2024-2028 not complete by 2025"}],
    }
    text = render_evaluation_markdown(evaluation)
    assert "h = 1" in text
    assert "2024" in text and "h = 5" in text and "not complete" in text


def test_a_missing_age_scores_exactly_like_the_position_median_age():
    # Measured 2026-09-06: the 107 id-less washouts retained in the cohort ALL lack a birth
    # date, because PFR never recorded one for a player who never played. An "age missing"
    # indicator would therefore learn "missing age ⇒ washout" — a data-collection artifact —
    # and penalise a 2026 rookie whose birth date is merely not yet on file. Missing age
    # must be imputed and otherwise invisible to the fit.
    train = _training_frame()
    train.loc[train.index[:40], "age_at_draft"] = np.nan  # some training rows lack age too
    model = RookieCapitalModel(horizons=(1, 2)).fit(train)
    median = model.age_median_by_position["QB"]
    probe = _cohort([("nan_age", 2026, "QB", 249, 7, np.nan), ("median_age", 2026, "QB", 249, 7, median)])
    pred = model.predict(probe).set_index("gsis_id")
    for col in ("p_qual_h1", "p_qual_h2", "e_qual_seasons_h2", "p_played_h1"):
        assert pred.loc["nan_age", col] == pytest.approx(pred.loc["median_age", col], abs=1e-12)
