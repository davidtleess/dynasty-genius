"""DG-177 — the measured-opportunity feature family, built point-in-time.

The family is RAW realized opportunity per game (targets, air yards, carries, pass
attempts): counts of what happened in the feature season, with no fitted weights, so
nothing retrospective can hide inside a historical row. The expected-points columns the
same table carries are a THIRD-PARTY fitted model and are exposed separately, named as
exploratory, so a caller cannot confuse the two.
"""
from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from src.dynasty_genius.eval.opportunity_features import (
    EXPLORATORY_XFP_FEATURES,
    RAW_OPPORTUNITY_FEATURES,
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


def test_per_game_aggregation_over_the_weeks_a_player_appeared():
    conn = _db([
        (2019, 1, "00-0001", "WR", 0, 8, 0, 90, 12.0, 10.0),
        (2019, 2, "00-0001", "WR", 0, 4, 1, 30, 6.0, 8.0),
        (2019, 1, "00-0002", "RB", 0, 2, 15, 5, 14.0, 13.0),
    ])
    out = load_opportunity_season_features(conn, seasons=[2019]).set_index("player_id")
    wr = out.loc["00-0001"]
    assert wr["feature_season"] == 2019
    assert wr["opp_games"] == 2
    assert wr["opp_targets_pg"] == pytest.approx(6.0)
    assert wr["opp_air_yards_pg"] == pytest.approx(60.0)
    assert wr["opp_carries_pg"] == pytest.approx(0.5)
    assert wr["opp_pass_attempts_pg"] == pytest.approx(0.0)
    assert wr["xfp_exp_ppg"] == pytest.approx(9.0)
    assert wr["xfp_ppg_over_exp"] == pytest.approx(0.0)   # (18 - 18) / 2
    rb = out.loc["00-0002"]
    assert rb["opp_carries_pg"] == pytest.approx(15.0)
    assert rb["xfp_ppg_over_exp"] == pytest.approx(1.0)


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
    assert out.loc["00-0001", "opp_air_yards_pg"] == pytest.approx(15.0)
    assert out.loc["00-0001", "opp_targets_pg"] == pytest.approx(6.0)


def test_join_coverage_counts_by_position_and_season():
    training = pd.DataFrame({
        "player_id": ["00-0001", "00-0002", "00-0003"],
        "position": ["WR", "WR", "RB"],
        "feature_season": [2019, 2019, 2019],
    })
    opp = pd.DataFrame({"player_id": ["00-0001"], "feature_season": [2019], "opp_games": [10]})
    cov = join_coverage(training, opp)
    assert cov == {
        "WR": {"2019": {"rows": 2, "joined": 1}},
        "RB": {"2019": {"rows": 1, "joined": 0}},
    }
