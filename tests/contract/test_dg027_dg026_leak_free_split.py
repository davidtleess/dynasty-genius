"""DG-027 + DG-026 — the penalty and the split stop learning from the answer.

DG-027: alpha was chosen by random 5-fold CV over pooled multi-season rows.
85-90% of the fitted training rows belong to a player who appears more than once,
so random folds put the same player on both sides by construction and the penalty
was tuned against a validation set that already knew the answer. Measured: the
selected alpha moves QB 1000 -> 1, RB 500 -> 50, WR 200 -> 1, TE 10 -> 0.1 under
an honest selector. QB's 1000 was the grid CEILING (DG-017) — that ceiling was
the leak talking.

DG-026: the split was clean on FEATURES and leaking on LABELS. The target is the
mean PPG of the two seasons AFTER the feature season, so a 2021 training row is
labelled from 2022-23 while the 2022-23 holdout is labelled from 2023-25 — 2023
outcomes on both sides.

Neither fix retrains or promotes anything: they change how the NEXT run chooses,
and a promotion is David's word through DG-058/059.
"""
from __future__ import annotations

import numpy as np
import pytest

from scripts.train_engine_b import (
    ALPHA_CANDIDATES,
    HOLDOUT_SEASONS,
    LABEL_WINDOW_RULE,
    LABEL_WINDOW_SEASONS,
    admissible_training_seasons,
    select_alpha_leak_free,
)


# ── DG-026: the label window, not just the feature season ───────────────────
def test_the_shipped_rule_drops_the_season_that_shares_an_outcome_with_the_test():
    """The leak the ticket names: holdout 2022-23 is labelled from 2023-25, and a
    2021 training row is labelled from 2022-23 — 2023 on both sides. 2020's
    window (2021-22) is clear of it, so 2020 stays."""
    seasons = admissible_training_seasons([2018, 2019, 2020, 2021], HOLDOUT_SEASONS)
    assert seasons == [2018, 2019, 2020]
    assert 2021 not in seasons
    assert LABEL_WINDOW_RULE == "no_shared_outcome_season"


def test_the_stricter_rule_is_available_and_costs_a_further_season():
    """Also forbids a training LABEL season from being a test FEATURE season.
    Measured cost on the real dataset: one alpha-selection fold per position and
    80 QB rows, so it is not the default — but it is one constant away."""
    strict = admissible_training_seasons(
        [2018, 2019, 2020, 2021], HOLDOUT_SEASONS, rule="window_closed_before_test"
    )
    assert strict == [2018, 2019]


def test_an_unknown_rule_is_refused_rather_than_silently_defaulted():
    with pytest.raises(ValueError, match="unknown label-window rule"):
        admissible_training_seasons([2018], HOLDOUT_SEASONS, rule="whatever")


def test_the_rule_follows_the_label_window_rather_than_a_hard_coded_year():
    assert LABEL_WINDOW_SEASONS == 2
    assert admissible_training_seasons([2015, 2016, 2017], [2019]) == [2015, 2016, 2017]
    assert admissible_training_seasons([2015, 2016, 2017], [2018]) == [2015, 2016]


def test_an_empty_admissible_set_is_returned_honestly_not_papered_over():
    assert admissible_training_seasons([2021], [2021]) == []


# ── DG-027: neither the season nor the player crosses a fold ────────────────
def _panel(n_players=60, seasons=(2016, 2017, 2018, 2019), churn=0.45):
    """A panel with real turnover. A perfectly balanced one — every player in
    every season — has NO honest fold at all, because holding out the validation
    season's players empties the training side. The real dataset does have
    turnover (3 usable folds per position, measured), and a fixture without it
    would test a situation the data never presents."""
    rng = np.random.default_rng(0)
    pid, season, X, y = [], [], [], []
    for p in range(n_players):
        skill = rng.normal()
        for i, s in enumerate(seasons):
            # each player enters and leaves; not everyone spans the panel
            if rng.random() < churn and i > 0:
                continue
            pid.append(f"p{p}")
            season.append(s)
            X.append([skill + rng.normal(0, 0.1), rng.normal()])
            y.append(3 * skill + rng.normal(0, 0.5))
    return np.array(X), np.array(y), np.array(season), np.array(pid)


def test_a_panel_with_no_turnover_has_no_honest_fold_and_says_so():
    """The degenerate case, pinned because it is the one that tempts a fallback:
    if every player appears in every season, holding the validation season's
    players out of the training side leaves nothing. Refusing is correct."""
    rng = np.random.default_rng(1)
    pid, season, X, y = [], [], [], []
    for p in range(20):
        for s in (2016, 2017, 2018):
            pid.append(f"p{p}")
            season.append(s)
            X.append([rng.normal(), rng.normal()])
            y.append(rng.normal())
    with pytest.raises(ValueError, match="cannot be selected without leakage"):
        select_alpha_leak_free(
            np.array(X), np.array(y), np.array(season), np.array(pid, dtype=object),
            ALPHA_CANDIDATES,
        )


def test_the_chosen_alpha_comes_from_folds_where_no_player_and_no_season_crosses():
    X, y, seasons, pid = _panel()
    alpha, meta = select_alpha_leak_free(X, y, seasons, pid, ALPHA_CANDIDATES)
    assert alpha in ALPHA_CANDIDATES
    assert meta["folds"] >= 1
    for train_idx, val_idx in meta["fold_indices"]:
        assert set(seasons[train_idx]).isdisjoint(set(seasons[val_idx])), "a season crossed"
        assert set(pid[train_idx]).isdisjoint(set(pid[val_idx])), "a player crossed"
        assert seasons[train_idx].max() < seasons[val_idx].min(), "the future taught the past"


def test_it_refuses_rather_than_falling_back_when_it_cannot_split_honestly():
    """The failure this guard exists for: a grouped split that silently reverts
    to random reports a clean number and changes nothing."""
    X, y, seasons, pid = _panel(n_players=4, seasons=(2018,))
    with pytest.raises(ValueError, match="cannot be selected without leakage"):
        select_alpha_leak_free(X, y, seasons, pid, ALPHA_CANDIDATES)


def test_it_refuses_when_the_player_column_is_missing_rather_than_ignoring_it():
    X, y, seasons, pid = _panel()
    with pytest.raises(ValueError, match="player"):
        select_alpha_leak_free(X, y, seasons, None, ALPHA_CANDIDATES)
    with pytest.raises(ValueError, match="player"):
        select_alpha_leak_free(X, y, seasons, np.array([None] * len(y)), ALPHA_CANDIDATES)


def test_every_player_in_a_validation_fold_is_held_out_of_its_training_side():
    """A returning player is dropped from the train side of the fold he is
    validated in — that is the price of "neither crosses", and it is the point."""
    X, y, seasons, pid = _panel(n_players=10, seasons=(2016, 2017, 2018))
    _, meta = select_alpha_leak_free(X, y, seasons, pid, ALPHA_CANDIDATES)
    for train_idx, val_idx in meta["fold_indices"]:
        assert len(train_idx) > 0 and len(val_idx) > 0
        assert not (set(pid[val_idx]) & set(pid[train_idx]))
