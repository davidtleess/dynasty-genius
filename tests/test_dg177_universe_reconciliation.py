"""Round 2, item 6 — every eligible player gets a forecast or a precise reason, never 0."""
from __future__ import annotations

import pandas as pd

from src.dynasty_genius.eval.universe_reconciliation import REASONS, reconcile_universe


def _universe():
    return pd.DataFrame({
        "sleeper_id": ["1", "2", "3", "4", "5", "6"],
        "gsis_id": ["00-A", None, None, None, "00-E", None],
        "name": ["Has Row", "Maps To Cohort", "No Mapping", "Never Played", "Left Cohort", "Missed One Season"],
        "position": ["WR", "RB", "WR", "WR", "RB", "WR"],
        "rostered": [True, True, False, True, True, True],
    })


def _idmap():
    return pd.DataFrame({"sleeper_id": [1.0, 2.0, 4.0, 5.0, 6.0],
                         "gsis_id": ["00-A", "00-B", "00-D", "00-E", "00-F"]})


def _cohort_2025():
    # 00-A active 2025; 00-B active 2025; 00-F zero-games 2025 after an active 2024 (in cohort)
    return pd.DataFrame({"player_id": ["00-A", "00-B", "00-F"], "feature_season": [2025] * 3,
                         "games_t": [15, 10, 0]})


def _history():
    # last season each gsis appeared in the weekly source
    return pd.DataFrame({"player_id": ["00-A", "00-B", "00-E", "00-F"], "last_season_seen": [2025, 2025, 2022, 2024]})


def test_every_universe_row_gets_exactly_one_status_and_no_zero():
    out = reconcile_universe(_universe(), _idmap(), _cohort_2025(), _history(), inference_season=2025)
    assert len(out) == 6 and set(out["status"]) <= set(REASONS)
    by = out.set_index("sleeper_id")["status"].to_dict()
    assert by["1"] == "forecast"                         # gsis on the universe row, in the cohort
    assert by["2"] == "forecast"                         # gsis via the id map, in the cohort
    assert by["3"] == "no_gsis_mapping"                  # nothing maps this Sleeper id
    assert by["4"] == "no_nfl_history"                   # gsis known, never a stat line
    assert by["5"] == "left_cohort_two_absent_seasons"   # last seen 2022: absent 2023, 2024, 2025
    assert by["6"] == "forecast"                         # zero-games 2025 row exists (Tank Dell's shape)
    assert out.loc[out.sleeper_id == "5", "last_season_seen"].iloc[0] == 2022
    assert out.loc[out.sleeper_id == "6", "games_2025"].iloc[0] == 0


def test_a_universe_gsis_disagreeing_with_the_id_map_is_flagged_not_overwritten():
    universe = _universe().copy()
    universe.loc[universe.sleeper_id == "1", "gsis_id"] = "00-WRONG"
    out = reconcile_universe(universe, _idmap(), _cohort_2025(), _history(), inference_season=2025)
    row = out.set_index("sleeper_id").loc["1"]
    assert row["status"] == "identity_conflict"
    assert row["gsis_id_universe"] == "00-WRONG" and row["gsis_id_idmap"] == "00-A"


def test_a_player_whose_stat_line_position_is_outside_the_modelled_set_gets_that_reason():
    universe = pd.DataFrame({"sleeper_id": ["7"], "gsis_id": ["00-H"], "name": ["Two Way"], "position": ["DB"], "rostered": [True]})
    history = pd.DataFrame({"player_id": ["00-H"], "last_season_seen": [2025]})
    positions = pd.DataFrame({"player_id": ["00-H"], "feature_season": [2025], "position": ["DB"]})
    out = reconcile_universe(universe, _idmap(), _cohort_2025(), history, inference_season=2025,
                             cohort_positions=positions)
    row = out.iloc[0]
    assert row["status"] == "position_outside_modelled_set" and row["cohort_position"] == "DB"
