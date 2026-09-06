"""DG-165 — weekly source capture: coverage is measured BEFORE any filter, on the raw frame.

Synthetic frames only. What each test would catch: a coverage report that silently
drops a missing week or a null scoring component, or that filters to a position set.
"""
from __future__ import annotations

import pandas as pd

from src.dynasty_genius.rookie.weekly_source import coverage_report, schema_report


def _weekly():
    # Two placeholder rows without a player id: one with zero points (the source's one-per-
    # season-week placeholder) and one unattributed stat line WITH points (seen live, e.g.
    # 2005 week 1 team row 6.0). Both must be counted, never dropped or filled.
    return pd.DataFrame({
        "player_id": ["a", "a", "b", "c", "d", None, None], "player_display_name": ["A", "A", "B", "C", "D", None, "D.Bryant"],
        "position": ["WR", "WR", "RB", "K", "DB", None, None], "team": ["X", "X", "Y", "Z", "Z", None, "Q"],
        "season": [2020, 2020, 2020, 2020, 2021, 2020, 2020], "week": [1, 2, 1, 17, 18, 3, 6],
        "season_type": ["REG", "REG", "REG", "REG", "POST", "REG", "REG"],
        "fantasy_points_ppr": [10.0, None, 5.0, 3.0, 1.0, 0.0, 3.1], "receptions": [3, 4, 0, 0, 0, 0, 1],
        "fumbles_lost": [0, None, 1, 0, 0, 0, 0],
    })


def test_coverage_counts_rows_and_reg_weeks_per_season_before_any_position_filter():
    cov = coverage_report(_weekly())
    row = cov.set_index(["season", "season_type"]).loc[(2020, "REG")]
    assert row["rows"] == 6 and row["players"] == 3
    assert row["weeks_present"] == "1|2|3|6|17" and row["week_min"] == 1 and row["week_max"] == 17 and row["n_weeks"] == 5
    assert row["positions"] == "K|RB|WR"           # K and DB are still here: no filter at capture
    assert row["rows_missing_player_id"] == 2 and row["rows_missing_player_id_with_points"] == 1
    post = cov.set_index(["season", "season_type"]).loc[(2021, "POST")]
    assert post["rows"] == 1 and post["positions"] == "DB"


def test_schema_report_keeps_every_column_and_counts_nulls_instead_of_filling():
    schema = schema_report(_weekly()).set_index("column")
    assert set(schema.index) == set(_weekly().columns)
    assert schema.loc["fantasy_points_ppr", "nulls"] == 1 and schema.loc["fumbles_lost", "nulls"] == 1
    assert schema.loc["week", "dtype"] != "" and schema.loc["fantasy_points_ppr", "non_null"] == 6
