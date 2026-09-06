"""DG-165 — the draft-capital rookie candidate: labels, cutoffs, coherence, grading, coverage.

Every test runs on SYNTHETIC frames (no network, no shared data) and names the production
change that would make it fail:

* nth-largest bar → a `rank == N` lookup skips a tied bar and drops a season silently
  (the DG-164 WR-2024 defect).
* measured zero vs unknown → mapping a missing career record to "zero games" asserted a
  negative from missing data (round-1 review); an unresolved identity must be NaN, kept,
  and counted, with the zero treatment available only as an explicit sensitivity arm.
* NaN beyond the cutoff → training on labels observed through 2025 while forecasting 2019
  (the preserved study's split) is exactly what this refuses.
* coherence by construction → separate per-horizon fits gave decreasing cumulative
  probabilities for 80 of 80 rookies (round-1 review).
* one procedure → the historical fit for T and the final fit are the same function.
* training baselines → the comparator is each forecast year's training prevalence, never
  pooled test prevalence (round-1 review).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.models.leakage import find_leaking_columns
from src.dynasty_genius.rookie.cohort import draft_cohort_from_picks
from src.dynasty_genius.rookie.evaluate import (
    evaluate_forecast_years,
    fit_at_forecast_year,
    training_frame_at,
)
from src.dynasty_genius.rookie.labels import (
    horizon_labels,
    qualifying_season_keys,
    season_stats_map,
)
from src.dynasty_genius.rookie.model import FEATURE_COLUMNS, RookieCapitalModel
from src.dynasty_genius.rookie.report import render_evaluation_markdown
from src.dynasty_genius.rookie.run_dir import create_run_dir
from src.dynasty_genius.rookie.score import score_class

SMALL_BAR = {"QB": 5, "RB": 5, "WR": 5, "TE": 5}


# ----------------------------------------------------------------------------- fixtures
def _panel(rows):
    """rows: (player_id, position, season, points, games)."""
    return pd.DataFrame(rows, columns=["player_id", "position", "season", "points", "games"])


def _cohort(rows, basis="nflverse_gsis"):
    """rows: (gsis_id, draft_season, position, pick, round, age_at_draft)."""
    frame = pd.DataFrame(rows, columns=["gsis_id", "draft_season", "position", "pick", "round", "age_at_draft"])
    frame["label_basis"] = basis
    return frame


def _cohort_with_outcomes(seed=5, n=900, classes=range(2005, 2020)):
    """A synthetic cohort + panel where appearance and qualification depend on capital and
    persist across seasons, so hazards and re-qualification rates are all identifiable."""
    rng = np.random.default_rng(seed)
    classes = list(classes)
    rows, panel_rows = [], []
    for i in range(n):
        c = classes[i % len(classes)]
        pick = int(rng.integers(1, 250))
        pos = ["QB", "RB", "WR", "TE"][i % 4]
        pid = f"{c}-{i}"
        rows.append((pid, c, pos, pick, int(np.ceil(pick / 32)), 22.0))
        base = 1 / (1 + np.exp(np.log(pick) - 4.2))
        alive = rng.random() < 0.85
        for j in range(6):
            if not alive:
                break
            games = int(rng.integers(1, 18))
            level = max(1.0, 16.0 - 2.2 * np.log(pick) + rng.normal(0, 2.0))
            panel_rows.append((pid, pos, c + j, games * level, games))
            alive = rng.random() < 0.55 + 0.4 * base
    # Filler veterans so every (season, position) group holds at least the bar rank, as
    # the real panel does; they are not in the cohort and never get a label.
    for season in range(min(classes), max(classes) + 6):
        for pos in ("QB", "RB", "WR", "TE"):
            for k in range(6):
                panel_rows.append((f"filler-{pos}-{k}", pos, season, 80.0 + 10 * k, 16))
    return _cohort(rows), _panel(panel_rows)


# ----------------------------------------------------------------------------- labels
def test_qualifying_keys_use_the_nth_largest_so_a_tie_at_the_bar_admits_both_players():
    panel = _panel([("a", "WR", 2020, 10.0, 17), ("b", "WR", 2020, 9.0, 17),
                    ("c", "WR", 2020, 9.0, 17), ("d", "WR", 2020, 8.0, 17)])
    assert qualifying_season_keys(panel, bar={"WR": 2}) == {("a", 2020), ("b", 2020), ("c", 2020)}


def test_qualifying_keys_raise_when_a_season_has_fewer_players_than_the_bar():
    panel = _panel([("a", "TE", 2020, 10.0, 17)])
    with pytest.raises(ValueError, match="TE 2020"):
        qualifying_season_keys(panel, bar={"TE": 21})


def test_season_labels_points_are_measured_zero_without_appearance_and_nan_when_unresolved():
    panel = _panel([("p", "WR", 2015, 170.0, 17)])
    cohort = _cohort([("p", 2015, "WR", 10, 1, 21.0), ("u", 2015, "WR", 200, 6, 22.0)])
    cohort["label_basis"] = ["nflverse_gsis", "unresolved"]
    labels = horizon_labels(cohort, qualifying={("p", 2015)}, season_stats=season_stats_map(panel),
                            horizons=(1, 2), last_completed_season=2025).set_index("gsis_id")
    p, u = labels.loc["p"], labels.loc["u"]
    assert (p["appear_1"], p["points_1"], p["games_1"], p["ppg_1"]) == (1, 170.0, 17, 10.0)
    assert (p["appear_2"], p["points_2"], p["games_2"]) == (0, 0.0, 0) and np.isnan(p["ppg_2"])
    for col in ("appear_1", "points_1", "qy_1", "q_2", "n_2", "appear_by_2"):
        assert np.isnan(u[col]), f"unresolved prospect must carry NaN in {col}, not a zero"


def test_unresolved_prospects_can_be_labelled_zero_only_as_an_explicit_sensitivity_arm():
    panel = _panel([("p", "WR", 2015, 170.0, 17)])
    cohort = _cohort([("u", 2015, "WR", 200, 6, 22.0)], basis="unresolved")
    labels = horizon_labels(cohort, qualifying=set(), season_stats=season_stats_map(panel), horizons=(1,),
                            last_completed_season=2025, unresolved_as_zero=True).iloc[0]
    assert (labels["appear_1"], labels["points_1"], labels["qy_1"], labels["q_1"]) == (0, 0.0, 0, 0)


def test_horizon_labels_count_only_seasons_inside_the_window():
    # Qualifies in the rookie season and in season 4; h=2 window is seasons 2015-2016.
    panel = _panel([("p", "RB", 2015, 300.0, 17), ("p", "RB", 2018, 300.0, 17)])
    cohort = _cohort([("p", 2015, "RB", 10, 1, 21.0)])
    labels = horizon_labels(cohort, qualifying={("p", 2015), ("p", 2018)}, season_stats=season_stats_map(panel),
                            horizons=(1, 2, 4), last_completed_season=2025).iloc[0]
    assert (labels["q_1"], labels["n_1"]) == (1, 1)
    assert (labels["q_2"], labels["n_2"], labels["appear_by_2"]) == (1, 1, 1)
    assert (labels["q_4"], labels["n_4"]) == (1, 2)


def test_horizon_labels_are_missing_when_the_window_is_not_complete_at_the_cutoff():
    # Class 2019 at cutoff 2020: seasons 1-2 are complete, season 3 (2021) is not.
    cohort = _cohort([("p", 2019, "QB", 1, 1, 22.0)])
    row = horizon_labels(cohort, qualifying=set(), season_stats={}, horizons=(1, 2, 3),
                         last_completed_season=2020).iloc[0]
    assert row["q_1"] == 0 and row["q_2"] == 0 and row["appear_2"] == 0 and row["points_2"] == 0.0
    for col in ("q_3", "n_3", "appear_3", "points_3", "games_3", "qy_3", "appear_by_3"):
        assert np.isnan(row[col]), col


# ----------------------------------------------------------------------------- cohort
def _picks(rows):
    return pd.DataFrame(rows, columns=["season", "round", "pick", "position", "gsis_id", "age", "team",
                                       "pfr_player_name", "games"])


def test_cohort_resolves_missing_ids_through_players_then_rosters_and_keeps_the_rest_unresolved():
    picks = _picks([
        (2020, 1, 1, "QB", "00-1", 22.0, "CIN", "A Quarterback", 40),
        (2020, 1, 2, "OT", "00-2", 21.0, "WAS", "A Tackle", 40),
        (2020, 2, 40, "WR", None, 22.0, "DET", "Draft Keyed", np.nan),
        (2020, 5, 150, "TE", None, 23.0, "KAN", "Roster Named", np.nan),
        (2020, 7, 250, "RB", None, np.nan, "SEA", "Nobody Found", np.nan),
    ])
    players = pd.DataFrame({"gsis_id": ["00-40", "00-99"], "display_name": ["Draft Keyed", "Roster Named"],
                            "draft_year": [2020, 1999], "draft_pick": [40, 150], "rookie_season": [2020, 1999]})
    rosters = pd.DataFrame({"gsis_id": ["00-150"], "full_name": ["Roster Named"], "entry_year": [2020],
                            "rookie_year": [2020], "draft_number": [np.nan]})
    cohort, report = draft_cohort_from_picks(picks, seasons=range(2020, 2021), players=players, rosters=rosters)
    got = cohort.set_index("pick")
    assert got.loc[40, "gsis_id"] == "00-40" and got.loc[40, "label_basis"] == "players:draft_year+pick"
    assert got.loc[150, "gsis_id"] == "00-150" and got.loc[150, "label_basis"] == "rosters:name+year"
    assert got.loc[250, "gsis_id"] == "unresolved:2020:250" and got.loc[250, "label_basis"] == "unresolved"
    assert got.loc[1, "label_basis"] == "nflverse_gsis"
    assert len(cohort) == 4 and report["skill_rows"] == 4
    assert report["without_gsis_id"] == 3 and report["unresolved_kept_with_nan_labels"] == 1
    assert report["resolution_of_missing_ids"] == {"players:draft_year+pick": 1, "rosters:name+year": 1, "unresolved": 1}


# ----------------------------------------------------------------------------- cutoff
def test_training_frame_at_T_never_labels_a_season_at_or_after_T():
    cohort = _cohort([(f"p{c}", c, "WR", 50, 2, 22.0) for c in range(2010, 2023)])
    train = training_frame_at(cohort, qualifying=set(), season_stats={}, horizons=(1, 3, 5), forecast_year=2020)
    assert train["draft_season"].max() == 2019
    for h in (1, 3, 5):
        assert train.loc[train[f"q_{h}"].notna(), "draft_season"].max() == 2020 - h
        assert train.loc[train[f"appear_{h}"].notna(), "draft_season"].max() == 2020 - h


def test_leak_canary_a_breakout_in_season_T_is_invisible_to_the_fit_at_T():
    # Class 2019 player qualifies ONLY in 2020. At forecast 2020 his season-2 label is NaN
    # (unknown), and his season-1 label is 0 — the fit at T cannot see the breakout.
    cohort = _cohort([("canary", 2019, "RB", 30, 1, 21.0)] + [(f"f{c}", c, "RB", 30, 1, 21.0) for c in range(2010, 2019)])
    panel = _panel([("canary", "RB", 2020, 300.0, 17)])
    train = training_frame_at(cohort, qualifying={("canary", 2020)}, season_stats=season_stats_map(panel),
                              horizons=(1, 2), forecast_year=2020).set_index("gsis_id")
    assert np.isnan(train.loc["canary", "qy_2"]) and np.isnan(train.loc["canary", "q_2"])
    assert train.loc["canary", "qy_1"] == 0 and train.loc["canary", "appear_1"] == 0


def test_test_labels_are_only_those_observable_today():
    # Today's last completed season is 2021: class 2020's seasons 1-2 are gradable, 3 is not.
    cohort = _cohort([("p", 2020, "TE", 100, 4, 23.0)])
    row = horizon_labels(cohort, qualifying=set(), season_stats={}, horizons=(1, 2, 3), last_completed_season=2021).iloc[0]
    assert row["q_2"] == 0 and np.isnan(row["q_3"]) and np.isnan(row["qy_3"])


# ----------------------------------------------------------------------------- model
def test_feature_columns_are_draft_capital_only_and_carry_no_market_column():
    cohort, _ = _cohort_with_outcomes()
    assert set(FEATURE_COLUMNS) <= {"pick", "round", "age_at_draft", "position"}
    assert find_leaking_columns(cohort[list(FEATURE_COLUMNS)]) == []


def _fitted(horizons=(1, 2, 3)):
    cohort, panel = _cohort_with_outcomes()
    stats = season_stats_map(panel)
    qual = qualifying_season_keys(panel, bar=SMALL_BAR)
    train = horizon_labels(cohort, qualifying=qual, season_stats=stats, horizons=horizons, last_completed_season=2025)
    return RookieCapitalModel(horizons=horizons).fit(train), train, cohort


def test_model_predictions_are_probabilities_and_expected_seasons_bounded_by_horizon():
    model, _, cohort = _fitted()
    pred = model.predict(cohort.head(60))
    for j in (1, 2, 3):
        assert pred[f"p_qual_year{j}"].between(0, 1).all() and pred[f"p_appear_year{j}"].between(0, 1).all()
        assert pred[f"p_qual_h{j}"].between(0, 1).all() and pred[f"p_appear_by_h{j}"].between(0, 1).all()
        assert pred[f"e_qual_seasons_h{j}"].between(0, j).all()
        assert (pred[f"e_points_year{j}"] >= 0).all() and pred[f"e_games_year{j}_given_appear"].between(1, 17).all()


def test_model_ranks_the_first_pick_above_the_last_pick():
    model, _, _ = _fitted(horizons=(1,))
    probe = _cohort([("first", 2026, "WR", 1, 1, 22.0), ("last", 2026, "WR", 255, 7, 22.0)])
    pred = model.predict(probe).set_index("gsis_id")
    assert pred.loc["first", "p_qual_year1"] > pred.loc["last", "p_qual_year1"]
    assert pred.loc["first", "e_points_year1"] > pred.loc["last", "e_points_year1"]


def test_a_missing_age_scores_exactly_like_the_position_median_age():
    # The id-less prospects all lack a birth date; an age-missing indicator would learn
    # "missing age ⇒ no record" and penalise a rookie whose birth date is not yet on file.
    model, train, _ = _fitted(horizons=(1, 2))
    median = model.age_median_by_position["QB"]
    probe = _cohort([("nan_age", 2026, "QB", 249, 7, np.nan), ("median_age", 2026, "QB", 249, 7, median)])
    pred = model.predict(probe).set_index("gsis_id")
    for col in ("p_qual_year1", "p_qual_h2", "e_qual_seasons_h2", "p_appear_year1", "e_points_year2"):
        assert pred.loc["nan_age", col] == pytest.approx(pred.loc["median_age", col], abs=1e-12)


def test_level_given_qualification_reads_only_qualifying_seasons_and_rises_with_capital():
    cohort, panel = _cohort_with_outcomes()
    stats = season_stats_map(panel)
    qual = qualifying_season_keys(panel, bar=SMALL_BAR)
    train = horizon_labels(cohort, qualifying=qual, season_stats=stats, horizons=(1, 2), last_completed_season=2025)
    # Plant an absurd rate on every NON-qualifying appearance: the qualification level
    # must never read those rows.
    for j in (1, 2):
        mask = (train[f"appear_{j}"] == 1) & (train[f"qy_{j}"] == 0)
        train.loc[mask, f"ppg_{j}"] = 150.0
    model = RookieCapitalModel(horizons=(1, 2)).fit(train)
    probe = _cohort([("first", 2026, "WR", 1, 1, 22.0), ("last", 2026, "WR", 255, 7, 22.0)])
    pred = model.predict(probe).set_index("gsis_id")
    for j in (1, 2):
        col = f"e_ppg_given_qual_year{j}"
        assert 0 < pred.loc["first", col] < 30 and 0 < pred.loc["last", col] < 30
        assert pred.loc["first", col] > pred.loc["last", col]


def test_cumulative_and_annual_probabilities_are_coherent_by_construction():
    model, _, cohort = _fitted(horizons=(1, 2, 3, 4))
    pred = model.predict(cohort.head(120))
    tol = 1e-9
    for h in (2, 3, 4):
        assert (pred[f"p_appear_by_h{h}"] + tol >= pred[f"p_appear_by_h{h - 1}"]).all()
        assert (pred[f"p_qual_h{h}"] + tol >= pred[f"p_qual_h{h - 1}"]).all()
    for j in (1, 2, 3, 4):
        assert (pred[f"p_qual_year{j}"] <= pred[f"p_qual_h{j}"] + tol).all()
        assert (pred[f"p_appear_year{j}"] <= pred[f"p_appear_by_h{j}"] + tol).all()
        assert np.allclose(pred[f"e_points_year{j}"], pred[f"p_appear_year{j}"] * pred[f"e_points_year{j}_given_appear"])
        assert np.allclose(pred[f"e_games_year{j}"], pred[f"p_appear_year{j}"] * pred[f"e_games_year{j}_given_appear"])
    for h in (1, 2, 3, 4):
        assert (pred[f"e_qual_seasons_h{h}"] + tol >= pred[f"p_qual_h{h}"]).all()
        assert (pred[f"e_qual_seasons_h{h}"] <= h + tol).all()
    assert pred["p_qual_year1"].equals(pred["p_qual_h1"])


# ----------------------------------------------------------------------------- evaluation
def test_historical_and_final_fits_share_one_procedure_and_every_annual_quantity_is_graded():
    cohort, panel = _cohort_with_outcomes()
    stats = season_stats_map(panel)
    qual = qualifying_season_keys(panel, bar=SMALL_BAR)
    report, predictions = evaluate_forecast_years(
        cohort, qualifying=qual, season_stats=stats, horizons=(1, 2, 3),
        forecast_years=(2015, 2016), last_completed_season_today=2025, n_boot=10,
    )
    model_2016 = fit_at_forecast_year(cohort, qualifying=qual, season_stats=stats, horizons=(1, 2, 3), forecast_year=2016)
    fresh = model_2016.predict(cohort.loc[cohort["draft_season"] == 2016]).set_index("gsis_id")
    got = predictions.loc[predictions["forecast_year"] == 2016].set_index("gsis_id")
    assert np.allclose(fresh.loc[got.index, "p_qual_year2"], got["p_qual_year2"])
    annual = report["annual"]
    for j in (1, 2, 3):
        for q in ("p_qual_year", "p_appear_year", "e_points_year", "e_games_year",
                  "e_ppg_year_given_appear", "e_ppg_given_qual_year"):
            assert q in annual[j], (j, q)
    assert "auc" in annual[1]["p_qual_year"] and "brier_training_baseline" in annual[1]["p_qual_year"]
    assert "rmse" in annual[1]["e_points_year"] and "rmse_training_baseline" in annual[1]["e_points_year"]
    assert annual[1]["e_ppg_given_qual_year"]["rmse"] < annual[1]["e_ppg_given_qual_year"]["rmse_training_baseline"]


def test_comparator_is_the_training_baseline_of_each_forecast_year_not_pooled_test_prevalence():
    # Classes before 2015 qualify often; the 2015 test class almost never does. A comparator
    # built from pooled TEST prevalence would flatter the model; the report must carry the
    # training one and expose it per forecast year.
    rows, panel_rows = [], []
    rng = np.random.default_rng(11)
    for c in range(2008, 2016):
        for i in range(80):
            pick = int(rng.integers(1, 250))
            pos = ["QB", "RB", "WR", "TE"][i % 4]
            pid = f"{c}-{i}"
            rows.append((pid, c, pos, pick, int(np.ceil(pick / 32)), 22.0))
            good = rng.random() < (0.6 if c < 2015 else 0.05)
            panel_rows.append((pid, pos, c, 300.0 if good else float(rng.uniform(1, 4)), 16))
    cohort = _cohort(rows)
    panel = _panel(panel_rows)
    # Bar rank 1 per position: before 2015 the many 300-point ties all qualify (~60%);
    # in 2015 only the single best per position does (~5%).
    top_one = {"QB": 1, "RB": 1, "WR": 1, "TE": 1}
    report, predictions = evaluate_forecast_years(
        cohort, qualifying=qualifying_season_keys(panel, bar=top_one), season_stats=season_stats_map(panel),
        horizons=(1,), forecast_years=(2015,), last_completed_season_today=2025, n_boot=10,
    )
    entry = report["annual"][1]["p_qual_year"]
    train_prev = float(predictions["baseline_p_qual_year1"].mean())
    assert entry["baseline_by_forecast_year"]["2015"] == pytest.approx(train_prev)
    assert train_prev > 0.4 and entry["prevalence"] < 0.15


# ----------------------------------------------------------------------------- scoring
def test_score_class_gives_every_prospect_a_row_and_unresolved_identities_carry_no_number():
    model, _, _ = _fitted(horizons=(1, 2))
    rookies = _cohort([("a", 2026, "QB", 1, 1, 22.0), ("b", 2026, "TE", 16, 1, np.nan), ("c", 2026, "RB", 250, 7, 23.0)])
    rookies["label_basis"] = ["nflverse_gsis", "nflverse_gsis", "unresolved"]
    scored = score_class(model, rookies).set_index("gsis_id")
    assert len(scored) == 3
    assert scored.loc["a", "coverage_status"] == "scored" and scored.loc["b", "coverage_status"] == "scored_age_imputed"
    assert scored.loc["a", "identity_status"] == "resolved" and scored.loc["c", "identity_status"] == "unresolved"
    assert scored.loc[["a", "b"], "p_qual_year1"].notna().all()
    assert np.isnan(scored.loc["c", "p_qual_year1"]) and np.isnan(scored.loc["c", "e_points_year1"])


# ----------------------------------------------------------------------------- run dir, report
def test_create_run_dir_refuses_to_overwrite_an_existing_run(tmp_path):
    first = create_run_dir(tmp_path, run_id="20260906T120000Z")
    assert first.is_dir()
    with pytest.raises(FileExistsError):
        create_run_dir(tmp_path, run_id="20260906T120000Z")


def test_evaluation_markdown_names_every_season_horizon_and_absent_pair():
    binary = {"n": 100, "prevalence": 0.3, "auc": 0.8, "auc_ci90": [0.7, 0.9], "brier": 0.17,
              "brier_training_baseline": 0.21, "log_loss": 0.5, "log_loss_training_baseline": 0.6,
              "mean_predicted": 0.31, "forecast_years": [2010], "baseline_by_forecast_year": {"2010": 0.3},
              "calibration": [{"bin": "0.00-0.10", "n": 40, "predicted": 0.05, "actual": 0.05}],
              "by_position": {}, "by_round": {}}
    level = {"n": 50, "mean_actual": 100.0, "mean_predicted": 95.0, "rmse": 40.0, "rmse_training_baseline": 50.0,
             "bias": -5.0, "forecast_years": [2010], "baseline_by_forecast_year": {"2010": 90.0},
             "by_position": {}, "by_round": {}}
    evaluation = {
        "annual": {1: {"p_qual_year": binary, "p_appear_year": binary, "e_points_year": level, "e_games_year": level,
                       "e_points_year_given_appear": level, "e_games_year_given_appear": level,
                       "e_ppg_year_given_appear": level, "e_ppg_given_qual_year": level}},
        "horizon": {1: {"p_qual_h": binary, "p_appear_by_h": binary, "e_qual_seasons_h": level}},
        "per_forecast_year": [], "skipped_forecast_years": [],
        "absent": [{"forecast_year": 2024, "season": 5, "reason": "NFL season 2028 not complete by 2025; cannot be graded yet"}],
    }
    text = render_evaluation_markdown(evaluation)
    assert "season 1" in text and "h = 1" in text
    assert "2024" in text and "not complete" in text


# ----------------------------------------------------------------------------- trend experiment
def _cohort_with_rising_outcomes(seed=7, n=1400, classes=range(2000, 2020)):
    """Appearance and qualification odds rise with the draft class year, so a model without
    a class-year term under-predicts recent classes out of time."""
    rng = np.random.default_rng(seed)
    classes = list(classes)
    rows, panel_rows = [], []
    for i in range(n):
        c = classes[i % len(classes)]
        pick = int(rng.integers(1, 250))
        pos = ["QB", "RB", "WR", "TE"][i % 4]
        pid = f"{c}-{i}"
        rows.append((pid, c, pos, pick, int(np.ceil(pick / 32)), 22.0))
        logit = 4.2 - np.log(pick) + 0.12 * (c - 2010)
        base = 1 / (1 + np.exp(-logit))
        alive = rng.random() < min(0.95, 0.5 + base)
        for j in range(4):
            if not alive:
                break
            games = int(rng.integers(6, 18))
            level = max(1.0, 12.0 - 1.5 * np.log(pick) + 0.25 * (c - 2010) + rng.normal(0, 2.0))
            panel_rows.append((pid, pos, c + j, games * level, games))
            alive = rng.random() < 0.6 + 0.35 * base
    for season in range(min(classes), max(classes) + 4):
        for pos in ("QB", "RB", "WR", "TE"):
            for k in range(6):
                panel_rows.append((f"filler-{pos}-{k}", pos, season, 60.0 + 10 * k, 16))
    return _cohort(rows), _panel(panel_rows)


def test_class_year_trend_is_an_explicit_model_option_recorded_in_describe():
    cohort, panel = _cohort_with_rising_outcomes()
    stats = season_stats_map(panel)
    qual = qualifying_season_keys(panel, bar=SMALL_BAR)
    train = horizon_labels(cohort, qualifying=qual, season_stats=stats, horizons=(1, 2), last_completed_season=2025)
    plain = RookieCapitalModel(horizons=(1, 2)).fit(train)
    trend = RookieCapitalModel(horizons=(1, 2), variant="trend").fit(train)
    assert plain.describe()["variant"] == "plain" and trend.describe()["variant"] == "trend"
    assert "class_year" in trend.describe()["design_columns"] and "class_year" not in plain.describe()["design_columns"]
    probe = _cohort([("late", 2026, "WR", 40, 2, 22.0)])
    # The trend model extrapolates the rising odds; the plain model cannot.
    assert trend.predict(probe)["p_qual_year1"].iloc[0] > plain.predict(probe)["p_qual_year1"].iloc[0]


def test_inner_menu_policy_selects_a_variant_using_only_labels_known_at_the_forecast_year():
    from src.dynasty_genius.rookie.evaluate import MENU, fit_at_forecast_year

    cohort, panel = _cohort_with_rising_outcomes()
    stats = season_stats_map(panel)
    qual = qualifying_season_keys(panel, bar=SMALL_BAR)
    model = fit_at_forecast_year(cohort, qualifying=qual, season_stats=stats, horizons=(1, 2),
                                 forecast_year=2016, policy="inner_menu")
    sel = model.describe()["policy_selection"]
    assert sel["chosen"] in MENU and set(sel["scores"]) == set(MENU)
    # inner validation classes all lie strictly before the forecast year and their
    # season-1 labels were complete at the cutoff
    assert max(sel["validation_classes"]) <= 2015
    assert sel["scores"]["trend"]["log_loss_p_qual_year1"] != sel["scores"]["plain"]["log_loss_p_qual_year1"]
    # a breakout in season T cannot change the selection: relabel with T's season and refit
    later = fit_at_forecast_year(cohort, qualifying=qual | {(pid, 2016) for pid in cohort["gsis_id"]},
                                 season_stats=stats, horizons=(1, 2), forecast_year=2016, policy="inner_menu")
    assert later.describe()["policy_selection"]["scores"] == sel["scores"]


def test_policy_experiment_declares_the_policy_ex_ante_and_never_picks_a_winner_on_outer_years():
    from src.dynasty_genius.rookie.evaluate import policy_experiment

    cohort, panel = _cohort_with_rising_outcomes()
    stats = season_stats_map(panel)
    qual = qualifying_season_keys(panel, bar=SMALL_BAR)
    result = policy_experiment(cohort, policy="inner_menu", exploratory=("plain",), qualifying=qual,
                               season_stats=stats, horizons=(1, 2), forecast_years=range(2012, 2020),
                               last_completed_season_today=2025, n_boot=10)
    # the declared policy is the canonical arm; the others are exploratory; no decision field
    assert result["policy"] == "inner_menu" and set(result["arms"]) == {"inner_menu", "plain"}
    assert "decision" not in result and "auto_trend_wins" not in result
    assert result["evidence_status"]["inner_menu"].startswith("independent")
    assert result["evidence_status"]["plain"].startswith("exploratory")
    assert set(result["predictions"]) == {"inner_menu", "plain"}
    # the comparison bounds the DIFFERENCE with a paired bootstrap, it does not crown a winner
    cmp = result["comparison"]["plain"]["p_qual_year1"]["brier"]
    assert {"policy", "exploratory", "difference", "difference_ci90"} <= set(cmp)
    assert cmp["difference"] == pytest.approx(cmp["exploratory"] - cmp["policy"])
    assert len(cmp["difference_ci90"]) == 2
    # every forecast year of the policy arm carries the inner selection it made
    for year in result["arms"]["inner_menu"]["per_forecast_year"]:
        assert year["policy_selection"]["chosen"] in ("plain", "trend", "trend_qb_r1")
        assert max(year["policy_selection"]["validation_classes"]) < year["forecast_year"]



# ----------------------------------------------------------------------------- round-2 review
# The review's historical counterexamples (run 151705Z): P(qualifies) > P(appears) on four
# annual rows and seven cumulative rows, all at the extremes. Under the three-state chain
# the subset relation holds for ANY input by arithmetic; these rows document the shapes
# that broke the previous construction.
COUNTEREXAMPLE_ROWS = [
    ("qb1-2005", 2005, "QB", 1, 1, 21.0), ("rb4-2008", 2008, "RB", 4, 1, 21.0), ("qb250-2005", 2005, "QB", 250, 7, 22.0),
    ("rb13-2008", 2008, "RB", 13, 1, 21.0), ("rb22-2008", 2008, "RB", 22, 1, 21.0), ("rb23-2008", 2008, "RB", 23, 1, 21.0),
    ("rb24-2008", 2008, "RB", 24, 1, 22.0), ("rb55-2008", 2008, "RB", 55, 2, 21.0),
]


def test_qualification_is_a_subset_of_appearance_on_every_row_including_the_review_counterexamples():
    model, _, cohort = _fitted(horizons=(1, 2, 3, 4, 5, 6))
    probe = pd.concat([cohort.head(150), _cohort(COUNTEREXAMPLE_ROWS)], ignore_index=True)
    pred = model.predict(probe)
    tol = 1e-12
    for j in range(1, 7):
        assert (pred[f"p_qual_year{j}"] <= pred[f"p_appear_year{j}"] + tol).all(), j
        assert (pred[f"p_qual_h{j}"] <= pred[f"p_appear_by_h{j}"] + tol).all(), j
        assert (pred[f"p_qual_year{j}"] <= pred[f"p_qual_h{j}"] + tol).all(), j
        assert (pred[f"e_qual_seasons_h{j}"] + tol >= pred[f"p_qual_h{j}"]).all(), j
        if j > 1:
            assert (pred[f"p_qual_h{j}"] + tol >= pred[f"p_qual_h{j - 1}"]).all(), j
            assert (pred[f"p_appear_by_h{j}"] + tol >= pred[f"p_appear_by_h{j - 1}"]).all(), j


def test_chain_transition_families_are_fitted_on_their_own_history_states():
    model, _, _ = _fitted(horizons=(1, 2, 3))
    families = model.describe()["n_train_by_family"]
    # season 1: only the never-appeared state exists; later seasons: appearance and
    # qualification-given-appearance for each of the three history states
    assert "a_1|s0" in families and "q_1|s0" in families and "a_1|s1" not in families
    for name in ("a_2|s0", "a_2|s1", "a_2|s2", "q_2|s0", "q_2|s1", "q_2|s2"):
        assert name in families, name


def test_scored_rows_carry_affirmative_policy_and_arm_identifiers():
    model, _, _ = _fitted(horizons=(1, 2))
    rookies = _cohort([("a", 2026, "QB", 1, 1, 22.0)])
    scored = score_class(model, rookies, model_policy="inner_menu", evaluation_sha256="abc123")
    row = scored.iloc[0]
    assert row["model_policy"] == "inner_menu" and row["evaluation_sha256"] == "abc123"
    assert row["scoring_arm_id"] == model.describe()["arm_id"] and row["scoring_arm_id"].endswith(":plain")


def test_pairing_verification_raises_on_any_mismatch_and_reports_consistent_otherwise(tmp_path):
    from src.dynasty_genius.rookie.identifiers import verify_pairing

    manifest = {"model_policy": "inner_menu", "scoring_arm_id": "v3:trend:inner_menu"}
    evaluation = {"policy_id": "inner_menu", "arm_ids": ["v3:trend:inner_menu", "v3:plain:inner_menu"]}
    scores = pd.DataFrame({"model_policy": ["inner_menu"] * 2, "scoring_arm_id": ["v3:trend:inner_menu"] * 2,
                           "evaluation_sha256": ["h1"] * 2})
    block = verify_pairing(manifest=manifest, evaluation=evaluation, scores=scores, evaluation_sha256="h1")
    assert block["status"] == "consistent"
    with pytest.raises(ValueError, match="policy"):
        verify_pairing(manifest={**manifest, "model_policy": "plain"}, evaluation=evaluation, scores=scores, evaluation_sha256="h1")
    with pytest.raises(ValueError, match="sha256"):
        verify_pairing(manifest=manifest, evaluation=evaluation, scores=scores, evaluation_sha256="other")
    with pytest.raises(ValueError, match="arm"):
        verify_pairing(manifest=manifest, evaluation={**evaluation, "arm_ids": ["v3:plain:plain"]}, scores=scores, evaluation_sha256="h1")


def test_calibration_assessment_separates_appearance_and_conditional_points_by_era_band_and_season():
    from src.dynasty_genius.rookie.calibration import calibration_assessment

    rng = np.random.default_rng(2)
    n = 400
    frame = pd.DataFrame({
        "forecast_year": rng.choice([2010, 2020], n), "position": rng.choice(["QB", "WR"], n),
        "round": rng.choice([1, 3], n), "gsis_id": [f"p{i}" for i in range(n)],
    })
    for j in (1, 2):
        frame[f"appear_{j}"] = (rng.random(n) < 0.8).astype(float)
        frame[f"p_appear_year{j}"] = 0.75
        frame[f"points_{j}"] = np.where(frame[f"appear_{j}"] == 1, 100.0, 0.0)
        frame[f"e_points_year{j}_given_appear"] = 90.0
        frame[f"e_points_year{j}"] = 0.75 * 90.0
    out = calibration_assessment(frame, seasons=(1, 2), n_boot=20)
    cell = out["cells"]["QB"]["R1"]["2016-25"]["1"]
    assert {"n", "appearance_bias", "appearance_bias_ci90", "n_appearers", "conditional_points_bias",
            "conditional_points_bias_ci90", "unconditional_points_bias", "unconditional_points_bias_ci90"} <= set(cell)
    assert cell["conditional_points_bias"] == pytest.approx(-10.0)
    assert out["eras"] == {"2005-15": [2005, 2015], "2016-25": [2016, 2025]}


def test_report_renders_the_policy_comparison_and_assessment_from_json_shapes():
    from src.dynasty_genius.rookie.report import render_report_markdown

    binary = {"n": 10, "prevalence": 0.3, "auc": 0.8, "auc_ci90": [0.7, 0.9], "brier": 0.17, "brier_training_baseline": 0.21,
              "log_loss": 0.5, "log_loss_training_baseline": 0.6, "mean_predicted": 0.31, "forecast_years": [2010]}
    level = {"n": 5, "mean_actual": 100.0, "mean_predicted": 95.0, "rmse": 40.0, "rmse_training_baseline": 50.0, "bias": -5.0, "forecast_years": [2010]}
    evaluation = {"policy_id": "inner_menu", "arm_ids": ["v3:inner_menu:trend"],
                  "annual": {1: {"p_qual_year": binary, "p_appear_year": binary, "e_points_year": level, "e_games_year": level,
                                 "e_ppg_given_qual_year": level}},
                  "horizon": {1: {"p_qual_h": binary, "p_appear_by_h": binary, "e_qual_seasons_h": level}},
                  "per_forecast_year": [{"forecast_year": 2010, "variant": "trend", "policy_selection": {"chosen": "trend"}}]}
    manifest = {"run_dir": "runs/x", "git_sha": "abcdef0123", "model_version": "v3", "model_policy": "inner_menu",
                "scoring_arm_id": "v3:inner_menu:trend", "status": "RESEARCH", "definitions": {}, "units": {},
                "forecast_date": {"forecast_cutoff": "2026-09-01", "label_window": "through 2025", "forecast_year": 2026},
                "cohort": {"coverage": {"rows": 1}}, "model": {"horizons": [1]}}
    comparison = {"policy": "inner_menu",
                  "evidence_status": {"inner_menu": "independent of the policy choice", "plain": "exploratory comparison"},
                  "comparison": {"plain": {"p_qual_year1": {"brier": {"policy": 0.17, "exploratory": 0.18, "difference": 0.01,
                                                                       "difference_ci90": [0.0, 0.02], "reading": "positive favours the policy"}}}}}
    assessment = {"cells": {"QB": {"R1": {"2016-25": {"1": {"n": 3, "appearance_rate": 0.9, "appearance_bias": 0.01, "appearance_bias_ci90": [0, 0.02],
                                                              "n_appearers": 3, "conditional_points_bias": -20.0, "conditional_points_bias_ci90": [-30, -10],
                                                              "unconditional_points_bias": -18.0, "unconditional_points_bias_ci90": [-28, -8]}}}}}}
    text = render_report_markdown(manifest, evaluation, None, None, comparison, assessment)
    assert "Declared policy: **inner_menu**" in text and "exploratory comparison" in text
    assert "2010: trend" in text and "calibration assessment" in text


def test_scored_rows_carry_the_current_position_beside_the_draft_position_when_supplied():
    # Max Bredeson (2026 pick 159) is TE in the draft table and RB on the 2026 roster; the
    # join is on (draft_season, pick), position is an attribute, and both are exported.
    model, _, _ = _fitted(horizons=(1,))
    rookies = _cohort([("b", 2026, "TE", 159, 5, 23.0)])
    rookies["position_current"] = ["RB"]
    scored = score_class(model, rookies).iloc[0]
    assert scored["position"] == "TE" and scored["position_current"] == "RB"
