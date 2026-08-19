"""The model card must state what the deployed model actually saw.

DG-015. Measured on 2026-08-19 against the shipped artifacts:

    all four cards in app/data/backtest/model_cards/ declare
        "training_window": "2018–2022 (expanding; 4 folds)"
    while scripts/train_engine_b.py:66,187 fits on rows EXCLUDING
        HOLDOUT_SEASONS = [2022, 2023]
    and app/data/training/engine_b_features_v2.csv carries feature seasons
        2018, 2019, 2020, 2021, 2022, 2023, 2025

So the deployed fit actually saw 2018-2021 and 2025. The card's claim is wrong three
ways at once: it claims 2022, which was held out; it omits 2025, which was used; and
the dash asserts a contiguous span that does not exist.

The cause is structural, not a typo. `training_window` was rendered from the union of
the walk-forward folds' train_years — a true statement about the EVALUATION, published
under a name every reader takes to mean the deployed fit. And HOLDOUT_SEASONS lived in
exactly one file, invisible to the generator, so nothing could notice the disagreement.

These tests bind the two together so the drift cannot silently recur.
"""

from __future__ import annotations

import pytest

from src.dynasty_genius.eval.training_provenance import (
    HOLDOUT_SEASONS,
    deployed_fit_seasons,
    describe_seasons,
    evaluation_window,
    seasons_from_training_data,
    training_window_statement,
)

# --------------------------------------------------------------- season rendering

def test_a_gap_is_never_rendered_as_a_span() -> None:
    """"2018–2025" would assert six continuous seasons; only five exist, and 2022,
    2023 and 2024 are not among them. A range is legal only when it is unbroken."""
    assert describe_seasons([2018, 2019, 2020, 2021, 2025]) == "2018–2021, 2025"


def test_an_unbroken_run_is_allowed_to_compress() -> None:
    assert describe_seasons([2018, 2019, 2020, 2021]) == "2018–2021"


def test_isolated_seasons_are_listed_individually() -> None:
    assert describe_seasons([2019, 2021, 2025]) == "2019, 2021, 2025"


def test_a_two_season_run_is_listed_not_dashed() -> None:
    """A dash between adjacent years buys no brevity and invites a range reading."""
    assert describe_seasons([2018, 2019]) == "2018, 2019"


def test_rendering_is_order_and_duplicate_insensitive() -> None:
    assert describe_seasons([2025, 2018, 2019, 2018, 2021, 2020]) == "2018–2021, 2025"


def test_empty_is_stated_explicitly_never_as_an_empty_string() -> None:
    """An empty window must be unmissable; a blank field reads as "not applicable"."""
    assert describe_seasons([]) == "none"


# --------------------------------------------------------------- deployed fit

def test_holdout_seasons_are_excluded_from_the_deployed_fit() -> None:
    trainable = [2018, 2019, 2020, 2021, 2022, 2023]
    assert deployed_fit_seasons(trainable) == [2018, 2019, 2020, 2021]


def test_a_season_with_no_outcome_can_never_be_claimed_as_fitted() -> None:
    """The correction that this module's FIRST version got wrong.

    Measured 2026-08-19 in engine_b_features_v2.csv: 2025 has 505 rows, **zero**
    outcomes, and training_eligible=0 throughout — its t+1/t+2 result has not happened
    yet. An earlier version of this module derived the fit from every season present in
    the matrix and so published "2018–2021, 2025 (deployed fit; ...)" — repeating, in
    the fix, the exact overstatement the fix existed to remove.
    """
    trainable = [2018, 2019, 2020, 2021, 2022, 2023]   # seasons carrying an outcome
    fit = deployed_fit_seasons(trainable)
    assert fit == [2018, 2019, 2020, 2021]
    assert 2025 not in fit, "a season with no outcome is not a season the model saw"
    assert 2022 not in fit


def test_deployed_fit_never_silently_keeps_a_holdout_season() -> None:
    for season in HOLDOUT_SEASONS:
        assert season not in deployed_fit_seasons([season, 2018])


# --------------------------------------------------------------- the statement

def test_the_statement_names_the_excluded_seasons_rather_than_hiding_them() -> None:
    """A reader must be able to see what was withheld without opening the trainer."""
    stmt = training_window_statement([2018, 2019, 2020, 2021, 2022, 2023], [2025])
    assert "2018–2021" in stmt
    assert "2022, 2023" in stmt, "the held-out seasons must be stated, not omitted"
    assert "held out" in stmt.lower()


def test_the_statement_discloses_a_present_but_ungradable_season() -> None:
    """2025 is in the matrix and a reader will notice its absence from the fit. Silence
    invites the reading that it was lost; the card says why it could not be used."""
    stmt = training_window_statement([2018, 2019, 2020, 2021, 2022, 2023], [2025])
    assert "2025" in stmt
    assert "not yet gradable" in stmt
    assert stmt.startswith("2018–2021 ("), stmt


def test_the_real_training_matrix_splits_as_measured() -> None:
    """Pinned to engine_b_features_v2.csv as measured 2026-08-19."""
    trainable, ungradable = seasons_from_training_data()
    if not trainable:
        pytest.skip("training matrix not present in this worktree")
    assert trainable == [2018, 2019, 2020, 2021, 2022, 2023]
    assert ungradable == [2025]
    assert deployed_fit_seasons(trainable) == [2018, 2019, 2020, 2021]


def test_the_statement_never_reproduces_the_false_claim() -> None:
    """The exact string the shipped cards carry today must not be producible."""
    stmt = training_window_statement([2018, 2019, 2020, 2021, 2022, 2023], [2025])
    assert "2018–2022 (expanding; 4 folds)" not in stmt


def test_the_statement_is_about_the_fit_not_the_folds() -> None:
    """Fold count describes the evaluation and must not appear in the fit statement,
    which is the confusion that produced this defect."""
    stmt = training_window_statement([2018, 2019, 2020, 2021], [2025])
    assert "fold" not in stmt.lower()


# --------------------------------------------------------------- evaluation window

def test_the_evaluation_window_is_labelled_as_evaluation() -> None:
    """The fold information is true and worth keeping — it just is not the fit."""
    window = evaluation_window([[2018, 2019], [2018, 2019, 2020], [2018, 2019, 2020, 2021]])
    assert "walk-forward" in window.lower() or "evaluation" in window.lower()
    assert "3 folds" in window


def test_evaluation_window_survives_zero_folds_without_crashing() -> None:
    assert evaluation_window([]) == "none"


# --------------------------------------------------------------- the binding

def test_the_trainer_and_the_card_read_the_same_holdout_constant() -> None:
    """The defect's real cause: HOLDOUT_SEASONS lived only in train_engine_b.py, so
    the card generator could not have known what the trainer withheld. If this test
    fails, the two have been allowed to drift apart again."""
    from pathlib import Path

    path = Path("scripts/train_engine_b.py")
    if not path.exists():
        pytest.skip("train_engine_b.py not present in this worktree")

    source = path.read_text(encoding="utf-8")
    assert "HOLDOUT_SEASONS = [2022, 2023]" not in source, (
        "train_engine_b.py still defines HOLDOUT_SEASONS as a literal. It must import "
        "the shared constant from src.dynasty_genius.eval.training_provenance, or the "
        "card and the trainer can disagree again without anything noticing."
    )
    assert "training_provenance" in source, (
        "train_engine_b.py must source its holdout seasons from the shared module"
    )
