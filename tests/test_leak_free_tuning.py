"""Inner tuning that cannot learn from the answer (DG-177 round 1, review item 1).

The trainer's alpha selection validated on one season and trained on strictly earlier
seasons — but a training row one season earlier is LABELLED from the validation season
and the one after it, so its label was not closed at the inner validation date. And the
imputer was fitted on the whole training window before the inner split, so the
validation rows shaped the medians used to score them. Both are corrected here, and
the two tests that matter are the ones that watch a leak fail to move the result.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.dynasty_genius.models.leak_free_tuning import select_alpha_leak_free

ALPHAS = [0.1, 1.0, 10.0, 100.0, 1000.0]


def _panel(n_players=60, seasons=(2016, 2017, 2018, 2019, 2020, 2021), seed=0):
    """Staggered careers: a player is active for a contiguous 2-4 season stretch, so every
    validation season has players absent from its training side and vice versa — the
    real panel's shape, and the only shape a player-held-out fold can be built from."""
    rng = np.random.default_rng(seed)
    pid, season, X, y = [], [], [], []
    for p in range(n_players):
        skill = rng.normal(10, 3)
        start = int(rng.integers(0, len(seasons) - 1))
        career = seasons[start:start + int(rng.integers(2, 5))]
        for s in career:
            x1 = skill + rng.normal()
            x2 = rng.normal()
            pid.append(f"p{p}")
            season.append(s)
            X.append([x1, x2])
            y.append(0.8 * x1 + 0.4 * x2 + rng.normal())
    return np.array(X), np.array(y), np.array(season), np.array(pid, dtype=object)


def test_inner_training_rows_have_closed_labels_and_no_shared_player():
    X, y, seasons, pid = _panel()
    alpha, meta = select_alpha_leak_free(X, y, seasons, pid, ALPHAS, window=2)
    assert alpha in ALPHAS
    assert meta["folds"] >= 1
    assert meta["label_window_seasons"] == 2
    for train_idx, val_idx in meta["fold_indices"]:
        v = int(seasons[val_idx].min())
        assert seasons[val_idx].max() == v, "a validation fold is one season"
        assert (seasons[train_idx] + 2 <= v).all(), "an inner training label was not closed"
        assert not (set(pid[val_idx]) & set(pid[train_idx])), "a player crossed"


def test_a_label_not_closed_at_the_inner_validation_date_cannot_change_that_fold():
    """Rows one season before the last validation season are labelled from that season
    and the one after it; under the old selector they TRAINED the last fold. Rewriting
    their labels must leave the last fold's error alone at every alpha (they are not in
    it), while the fold that validates on them moves (they are its truths)."""
    X, y, seasons, pid = _panel()
    last = int(seasons.max())
    _, before = select_alpha_leak_free(X, y, seasons, pid, ALPHAS, window=2)
    y2 = y.copy()
    y2[seasons == last - 1] += 1000.0
    _, after = select_alpha_leak_free(X, y2, seasons, pid, ALPHAS, window=2)
    assert before["validation_seasons"] == after["validation_seasons"]
    i_last = before["validation_seasons"].index(last)
    i_prev = before["validation_seasons"].index(last - 1)
    for alpha in ALPHAS:
        assert before["fold_mse_by_alpha"][alpha][i_last] == after["fold_mse_by_alpha"][alpha][i_last]
        assert before["fold_mse_by_alpha"][alpha][i_prev] != after["fold_mse_by_alpha"][alpha][i_prev]


def test_the_imputer_is_fitted_inside_each_inner_fold():
    """A NaN in a validation row must be filled with the inner-TRAINING median. If the
    imputer were fitted on the whole window, moving the validation rows' values would
    move the medians used to score them; here it cannot."""
    X, y, seasons, pid = _panel()
    X = X.astype(float)
    val_rows = seasons == seasons.max()
    X[val_rows, 1] = np.nan          # every validation-season row is missing x2
    base = select_alpha_leak_free(X, y, seasons, pid, [1.0], window=2)
    X_moved = X.copy()
    earlier = seasons == seasons.max() - 3   # rows that DO train the last fold
    X_moved[earlier, 1] = X_moved[earlier, 1] + 50.0
    moved = select_alpha_leak_free(X_moved, y, seasons, pid, [1.0], window=2)
    # moving inner-training rows changes the fold error (the imputer saw them) ...
    assert base[1]["mean_cv_mse"] != moved[1]["mean_cv_mse"]
    # ... while the record says where preprocessing was fitted
    assert base[1]["preprocessing"] == "median_imputer_fit_inside_each_inner_fold"


def test_it_refuses_when_no_fold_survives_the_closure():
    X, y, seasons, pid = _panel(n_players=20, seasons=(2018, 2019))
    with pytest.raises(ValueError, match="cannot be selected without leakage"):
        select_alpha_leak_free(X, y, seasons, pid, ALPHAS, window=2)


def test_it_refuses_a_missing_or_incomplete_player_column():
    X, y, seasons, pid = _panel()
    with pytest.raises(ValueError, match="player"):
        select_alpha_leak_free(X, y, seasons, None, ALPHAS)
    with pytest.raises(ValueError, match="player"):
        select_alpha_leak_free(X, y, seasons, np.array([None] * len(y)), ALPHAS)


def test_the_trainer_uses_the_shared_selector():
    from scripts import train_engine_b

    assert train_engine_b.select_alpha_leak_free is select_alpha_leak_free
