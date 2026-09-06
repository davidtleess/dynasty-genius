"""Round 2, item 5 — years 1-5 on the basic cohort: unsupported cells are reported, never filled."""
from __future__ import annotations

from scripts.experiments.dg177_basic_horizons import (
    HORIZONS,
    evaluable_horizons,
    horizon_support,
)


def test_horizons_are_one_to_five():
    assert HORIZONS == (1, 2, 3, 4, 5)


def test_support_counts_closed_training_seasons_per_horizon():
    seasons = list(range(2010, 2026))
    support = horizon_support(seasons, last_complete_season=2025, min_training_seasons=6)
    # a year-5 label closes at t+5 <= 2025 -> feature seasons 2010..2020: 11 closed seasons
    assert support[5]["closed_feature_seasons"] == list(range(2010, 2021))
    assert support[5]["supported"] is True
    assert support[1]["closed_feature_seasons"] == list(range(2010, 2025))


def test_a_horizon_with_too_few_closed_seasons_is_unsupported_not_filled():
    seasons = list(range(2018, 2026))
    support = horizon_support(seasons, last_complete_season=2025, min_training_seasons=6)
    assert support[5]["supported"] is False and "2018" in support[5]["reason"]
    assert evaluable_horizons(support) == [1, 2]      # 2018-2025 supports only 1-2 at that floor
