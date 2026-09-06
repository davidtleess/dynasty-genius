"""DG-177 — the measured-opportunity feature family, built point-in-time.

The family is RAW realized opportunity per game (targets, air yards, carries, pass
attempts): counts of what happened in the feature season, with no fitted weights, so
nothing retrospective can hide inside a historical row. The expected-points columns the
same table carries are a THIRD-PARTY fitted model and are exposed separately, named as
exploratory, so a caller cannot confuse the two.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval.opportunity_features import (
    EXPLORATORY_XFP_FEATURES,
    RAW_OPPORTUNITY_FEATURES,
    attach_opportunity_rates,
    join_coverage,
    load_opportunity_season_features,
)

COLS = ["season", "week", "player_id", "position", "pass_attempt", "rec_attempt",
        "rush_attempt", "rec_air_yards", "total_fantasy_points", "total_fantasy_points_exp"]


def _db(rows):
    conn = sqlite3.connect(":memory:")
    conn.execute("create table ff_opportunity (%s)" % ", ".join(f"{c} TEXT" for c in COLS))
    conn.executemany(
        "insert into ff_opportunity values (%s)" % ",".join("?" * len(COLS)),
        [tuple(None if v is None else str(v) for v in r) for r in rows],
    )
    return conn


def test_family_names_are_fixed_and_disjoint():
    assert RAW_OPPORTUNITY_FEATURES == [
        "opp_targets_pg", "opp_air_yards_pg", "opp_carries_pg", "opp_pass_attempts_pg"
    ]
    assert EXPLORATORY_XFP_FEATURES == ["xfp_exp_ppg", "xfp_ppg_over_exp"]
    assert not set(RAW_OPPORTUNITY_FEATURES) & set(EXPLORATORY_XFP_FEATURES)


def test_loader_returns_season_sums_and_the_source_week_count_under_its_true_name():
    conn = _db([
        (2019, 1, "00-0001", "WR", 0, 8, 0, 90, 12.0, 10.0),
        (2019, 2, "00-0001", "WR", 0, 4, 1, 30, 6.0, 8.0),
        (2019, 1, "00-0002", "RB", 0, 2, 15, 5, 14.0, 13.0),
    ])
    out = load_opportunity_season_features(conn, seasons=[2019]).set_index("player_id")
    wr = out.loc["00-0001"]
    assert wr["feature_season"] == 2019
    assert wr["opp_weeks_in_source"] == 2          # weeks the SOURCE has a row for — not games played
    assert wr["opp_targets"] == 12 and wr["opp_air_yards"] == 120
    assert wr["opp_carries"] == 1 and wr["opp_pass_attempts"] == 0
    assert wr["xfp_points"] == 18.0 and wr["xfp_expected_points"] == 18.0
    assert "opp_games" not in out.columns             # the old misnamed denominator is gone
    for name in RAW_OPPORTUNITY_FEATURES + EXPLORATORY_XFP_FEATURES:
        assert name not in out.columns               # rates are attached against the product's games


def test_rates_are_per_product_game_with_missing_source_weeks_as_zero_opportunity():
    """The product's games_t counts every game with a stat line (all games, DG-024).
    The source has rows only for weeks with an opportunity; a stat-line game with no
    source row is an OBSERVED zero-opportunity appearance and divides the total."""
    training = pd.DataFrame({
        "player_id": ["00-0001"], "position": ["WR"], "feature_season": [2019], "games_t": [12],
    })
    opp = pd.DataFrame({
        "player_id": ["00-0001"], "feature_season": [2019], "opp_weeks_in_source": [10],
        "opp_targets": [60.0], "opp_air_yards": [900.0], "opp_carries": [0.0], "opp_pass_attempts": [0.0],
        "xfp_points": [120.0], "xfp_expected_points": [96.0],
    })
    out = attach_opportunity_rates(training, opp).iloc[0]
    assert out["opp_source_available"] is True or out["opp_source_available"] == True  # noqa: E712
    assert out["opp_weeks_in_source"] == 10
    assert out["opp_zero_opportunity_games"] == 2
    assert out["opp_targets_pg"] == pytest.approx(5.0)         # 60 / 12, not 60 / 10
    assert out["opp_air_yards_pg"] == pytest.approx(75.0)
    assert out["xfp_exp_ppg"] == pytest.approx(8.0)            # 96 / 12
    assert out["xfp_ppg_over_exp"] == pytest.approx(2.0)       # (120 - 96) / 12


def test_a_season_absent_from_the_source_is_unavailable_not_zero():
    training = pd.DataFrame({
        "player_id": ["00-0001", "00-0009"], "position": ["WR", "RB"],
        "feature_season": [2019, 2019], "games_t": [12, 8],
    })
    opp = pd.DataFrame({
        "player_id": ["00-0001"], "feature_season": [2019], "opp_weeks_in_source": [12],
        "opp_targets": [60.0], "opp_air_yards": [900.0], "opp_carries": [0.0], "opp_pass_attempts": [0.0],
        "xfp_points": [120.0], "xfp_expected_points": [96.0],
    })
    out = attach_opportunity_rates(training, opp).set_index("player_id")
    missing = out.loc["00-0009"]
    assert bool(missing["opp_source_available"]) is False
    assert np.isnan(missing["opp_targets_pg"]) and np.isnan(missing["xfp_exp_ppg"])
    assert np.isnan(missing["opp_zero_opportunity_games"])
    assert len(out) == 2                                        # no row is dropped


def test_more_source_weeks_than_product_games_is_refused_not_hidden():
    training = pd.DataFrame({"player_id": ["00-0001"], "position": ["WR"], "feature_season": [2019], "games_t": [5]})
    opp = pd.DataFrame({
        "player_id": ["00-0001"], "feature_season": [2019], "opp_weeks_in_source": [7],
        "opp_targets": [1.0], "opp_air_yards": [1.0], "opp_carries": [0.0], "opp_pass_attempts": [0.0],
        "xfp_points": [1.0], "xfp_expected_points": [1.0],
    })
    with pytest.raises(ValueError):
        attach_opportunity_rates(training, opp)


def test_a_feature_season_never_reads_a_later_season():
    base = [(2019, 1, "00-0001", "WR", 0, 8, 0, 90, 12.0, 10.0)]
    later = base + [(2020, 1, "00-0001", "WR", 0, 20, 0, 300, 40.0, 30.0)]
    a = load_opportunity_season_features(_db(base), seasons=[2019])
    b = load_opportunity_season_features(_db(later), seasons=[2019])
    pd.testing.assert_frame_equal(a, b)


def test_rows_without_an_identity_are_dropped_not_aggregated_as_a_phantom():
    conn = _db([
        (2019, 1, None, "WR", 0, 8, 0, 90, 12.0, 10.0),
        (2019, 1, "", "WR", 0, 8, 0, 90, 12.0, 10.0),
        (2019, 1, "00-0001", "WR", 0, 8, 0, 90, 12.0, 10.0),
    ])
    out = load_opportunity_season_features(conn, seasons=[2019])
    assert list(out["player_id"]) == ["00-0001"]


def test_text_columns_are_coerced_and_a_missing_value_does_not_poison_the_sum():
    conn = _db([
        (2019, 1, "00-0001", "WR", 0, 8, 0, None, 12.0, 10.0),
        (2019, 2, "00-0001", "WR", 0, 4, 0, 30, 6.0, 8.0),
    ])
    out = load_opportunity_season_features(conn, seasons=[2019]).set_index("player_id")
    assert out.loc["00-0001", "opp_air_yards"] == pytest.approx(30.0)
    assert out.loc["00-0001", "opp_targets"] == pytest.approx(12.0)


def test_join_coverage_counts_by_position_and_season():
    training = pd.DataFrame({
        "player_id": ["00-0001", "00-0002", "00-0003"],
        "position": ["WR", "WR", "RB"],
        "feature_season": [2019, 2019, 2019],
    })
    opp = pd.DataFrame({"player_id": ["00-0001"], "feature_season": [2019], "opp_weeks_in_source": [10]})
    cov = join_coverage(training, opp)
    assert cov == {
        "WR": {"2019": {"rows": 2, "joined": 1}},
        "RB": {"2019": {"rows": 1, "joined": 0}},
    }
