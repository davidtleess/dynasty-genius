"""The one label-closure rule every walk-forward in this repo must share (DG-177 round 1).

A label that spans W seasons after feature season t is final only after season t+W.
A forecast made after season s may therefore train on rows with t + W <= s. Three
inherited paths (backtest harness, availability walk-forward, the trainer's inner
alpha selection) each carried their own split and each was open; one shared rule,
asserted by tests, is how they stop drifting.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.dynasty_genius.models.label_closure import (
    LABEL_WINDOW_SEASONS,
    FutureLabelError,
    admissible_train_seasons,
    assert_labels_known,
    closed_train_mask,
)


def test_default_window_is_the_two_season_outcome():
    assert LABEL_WINDOW_SEASONS == 2


def test_two_season_label_admits_t_plus_2_equal_to_test_season():
    assert admissible_train_seasons([2018, 2019, 2020, 2021], 2021) == [2018, 2019]


def test_one_season_label_admits_one_more_season():
    assert admissible_train_seasons([2018, 2019, 2020, 2021], 2021, window=1) == [2018, 2019, 2020]


def test_strict_rule_is_one_season_tighter():
    assert admissible_train_seasons(
        [2018, 2019, 2020, 2021], 2021, rule="window_closed_before_test"
    ) == [2018]


def test_unknown_rule_is_refused():
    with pytest.raises(ValueError):
        admissible_train_seasons([2018], 2021, rule="nope")


def test_closed_train_mask_selects_only_closed_rows():
    seasons = pd.Series([2018, 2019, 2020, 2021, 2022])
    assert closed_train_mask(seasons, test_season=2021).tolist() == [True, True, False, False, False]
    assert closed_train_mask(seasons, test_season=2021, window=1).tolist() == [True, True, True, False, False]


def test_an_open_window_in_training_rows_is_refused():
    train = pd.DataFrame({"feature_season": [2018, 2020]})
    with pytest.raises(FutureLabelError):
        assert_labels_known(train, test_season=2021)
    assert_labels_known(train, test_season=2022)  # closed now; no raise


def test_the_veteran_evaluator_reexports_the_shared_rule():
    from src.dynasty_genius.eval import veteran_candidate as vc

    assert vc.admissible_train_seasons is admissible_train_seasons
    assert vc.FutureLabelError is FutureLabelError
