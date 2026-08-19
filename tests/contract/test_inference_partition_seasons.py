"""DG-029 — pin the three-way season partition, and prove it is parameterized.

Why this file exists: the Engine-B training table has zero 2024 rows while 2025 is
present. That shape reads like a data gap, and one wrong guess about it already cost
most of an evening. It is not a gap. `apply_inference_partition` sorts every season
into exactly one of three buckets, and 2024 lands in the one that is dropped:

  * training     — feature_season < inference_season - 1, complete 2-year outcome
                   window, kept WITH an outcome and training_eligible=True
  * in-between   — no complete outcome window, not the inference season: DROPPED
  * inference    — the latest season in the window, kept WITHOUT an outcome and
                   training_eligible=False

With a 2018..2025 window that makes 2024 the in-between season. Nothing about 2024 is
special; it is the arithmetic of a 2-year outcome horizon against a window ending in
2025. These tests pin the RULE, not the year, so the drop moves on its own when 2026
data lands.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.dynasty_genius.features.feature_assembly import (
    OUTCOME_COLUMN,
    apply_inference_partition,
    inference_season_rule,
)


def _frame(seasons: list[int], *, players: int = 2) -> pd.DataFrame:
    """One row per player per season, with the columns the partition needs."""
    return pd.DataFrame(
        [
            {
                "player_id": f"P{p}",
                "feature_season": s,
                "ppg_t": 10.0 + p,
                "games_t": 17,
            }
            for s in seasons
            for p in range(players)
        ]
    )


WINDOW = list(range(2018, 2026))  # the production window: 2018..2025


def test_inference_season_is_the_window_max_not_a_literal() -> None:
    assert inference_season_rule(WINDOW) == 2025
    assert inference_season_rule([2019, 2020, 2021]) == 2021


def test_the_in_between_season_is_dropped_entirely() -> None:
    """The DG-029 answer: 2024 is absent BY DESIGN, not by gap."""
    out = apply_inference_partition(_frame(WINDOW), seasons_window=WINDOW)
    assert 2024 not in set(out["feature_season"]), (
        "2024 must be dropped: it has no complete 2-year outcome window "
        "(2024+2=2026 > 2025) and it is not the inference season"
    )


def test_training_seasons_keep_an_outcome_and_are_eligible() -> None:
    out = apply_inference_partition(_frame(WINDOW), seasons_window=WINDOW)
    train = out[out["feature_season"] <= 2023]
    assert not train.empty
    assert train["training_eligible"].all()
    assert train[OUTCOME_COLUMN].notna().all()


def test_inference_season_is_kept_but_never_trained_on() -> None:
    out = apply_inference_partition(_frame(WINDOW), seasons_window=WINDOW)
    inf = out[out["feature_season"] == 2025]
    assert not inf.empty, "the inference season must survive the partition"
    assert not inf["training_eligible"].any()
    assert inf[OUTCOME_COLUMN].isna().all(), (
        "the inference season has no future to grade against; its outcome must be null"
    )


def test_partition_is_exhaustive_and_disjoint() -> None:
    """Every surviving row is training XOR inference — no third state."""
    out = apply_inference_partition(_frame(WINDOW), seasons_window=WINDOW)
    is_train = out["training_eligible"]
    has_outcome = out[OUTCOME_COLUMN].notna()
    assert (is_train == has_outcome).all(), (
        "training_eligible and outcome-presence must agree row for row"
    )


@pytest.mark.parametrize(
    ("window_end", "expected_seasons"),
    [
        (2025, {2018, 2019, 2020, 2021, 2022, 2023, 2025}),
        (2024, {2018, 2019, 2020, 2021, 2022, 2024}),
        (2026, {2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026}),
    ],
)
def test_the_partition_follows_the_window_not_the_calendar(
    window_end: int, expected_seasons: set[int]
) -> None:
    """The guard that matters: shift the window, the whole partition moves with it.

    Asserts the EXACT surviving set, not merely that one season is missing. An
    earlier draft of this test only checked that the expected in-between season was
    absent, and a mutation reintroducing the legacy hardcoded `feature_season < 2024`
    slipped past two of its three cases by dropping an EXTRA season the test never
    looked at. Pinning the full set is what makes this guard honest.
    """
    window = list(range(2018, window_end + 1))
    out = apply_inference_partition(_frame(window), seasons_window=window)
    assert set(out["feature_season"]) == expected_seasons

    inference = window_end
    assert out[out["feature_season"] == inference][OUTCOME_COLUMN].isna().all()
    assert not out[out["feature_season"] == inference]["training_eligible"].any()
    trained = out[out["feature_season"] != inference]
    assert trained["training_eligible"].all()
    assert trained[OUTCOME_COLUMN].notna().all()
