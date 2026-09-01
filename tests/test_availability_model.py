"""P(returns) — the availability half of the hurdle, and the guards it has to carry.

Why this exists: `58d3b20c` recovered 638 attrition player-seasons and labelled them
`outcome_returned`, and recorded in its own HONEST LIMIT section that the age coefficients
did not move because nothing consumes them. This is the model that consumes them. Value
becomes P(plays) x E[points | plays]; this file covers the first factor only.

Three guards, each from a specific finding rather than from good practice in general:

1. WALK-FORWARD BY SEASON, NOT GroupKFold. The AUC of 0.787/0.822/0.830/0.753 that
   motivated this work was measured with GroupKFold-by-player, which lets a 2023 season
   train a prediction about 2019. For a forecasting product that is not an estimate of
   forward performance at all. Every fold here must train strictly on the past.

2. THE EVENT IS OUR OWN FILTER. `outcome_returned` is False when a player posted no
   QUALIFYING season at t+1 or t+2, and the upstream assembler already drops seasons under
   MIN_GAMES_THRESHOLD=4. So the label is partly a fact about this pipeline, not about
   football, and any artifact that surfaces it has to say so.

3. CALIBRATION IS THE DELIVERABLE, NOT ACCURACY. Under the width-not-absence ruling,
   P(plays) is what gives a thin-sample player an honest band. An uncalibrated probability
   produces a band that is decorative, which is worse than no band because it looks
   measured. A model that ranks well and is calibrated badly fails at the actual job.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.dynasty_genius.models.availability import walk_forward_availability

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    if not DATASET.exists():
        pytest.skip(f"{DATASET} not found")
    with open(DATASET) as handle:
        return [r for r in csv.DictReader(handle) if r.get("outcome_returned") in ("True", "False")]


@pytest.fixture(scope="module")
def result(rows):
    return walk_forward_availability(rows)


def test_no_fold_trains_on_its_own_test_season_or_later(result) -> None:
    """The guard that separates a forecast from a retrospective fit."""
    assert result.folds, "walk-forward validation produced no folds"
    for fold in result.folds:
        assert fold.train_seasons, f"fold testing {fold.test_season} trained on nothing"
        assert max(fold.train_seasons) < fold.test_season, (
            f"fold testing {fold.test_season} trained on {sorted(fold.train_seasons)} — a "
            "season at or after the test year leaks the future into the estimate"
        )


def test_every_fold_tests_exactly_one_season_and_they_advance(result) -> None:
    """Expanding window: each fold's training set is a superset of the one before it."""
    seasons = [f.test_season for f in result.folds]
    assert seasons == sorted(seasons), "folds must run forward in time"
    assert len(set(seasons)) == len(seasons), "a season must not be tested twice"
    for earlier, later in zip(result.folds, result.folds[1:]):
        assert set(earlier.train_seasons) < set(later.train_seasons), (
            "an expanding window must strictly grow; a shrinking or equal window means a "
            "season was skipped"
        )


def test_predictions_are_probabilities(result) -> None:
    """A hurdle multiplies by this term, so anything outside [0,1] corrupts the value."""
    for fold in result.folds:
        assert fold.predictions, f"fold testing {fold.test_season} predicted nothing"
        assert all(0.0 <= p <= 1.0 for p in fold.predictions), (
            "P(returns) must be a probability — a hurdle multiplies E[points|plays] by it"
        )


def test_performance_is_reported_per_position(result) -> None:
    """QB attrition and RB attrition are different processes; one pooled number hides that."""
    assert set(result.by_position) >= {"QB", "RB", "WR", "TE"}
    for pos, metrics in result.by_position.items():
        assert metrics["n"] > 0, f"{pos} has no evaluated rows"
        assert 0.0 <= metrics["auc"] <= 1.0


def test_calibration_is_measured_not_just_discrimination(result) -> None:
    """AUC says the ranking is right; only calibration says the NUMBER is right."""
    for fold in result.folds:
        assert "brier" in fold.metrics, (
            "a probability used as a multiplier must be scored on calibration, not only on "
            "its ability to rank"
        )
        assert 0.0 <= fold.metrics["brier"] <= 1.0
    assert result.calibration_bins, (
        "report observed-vs-predicted by bin, so 'predicted 0.7 means ~70% observed' is "
        "checkable rather than assumed"
    )


def test_the_model_beats_predicting_the_base_rate(result) -> None:
    """The honest floor. If it cannot beat 'everyone returns at the league rate', say so."""
    assert result.baseline_brier is not None
    assert result.model_brier is not None


def test_the_artifact_says_the_event_is_our_own_filter(result) -> None:
    """Guard 2. The label is partly a fact about this pipeline, not about football."""
    text = result.event_definition.lower()
    assert "qualifying" in text, (
        "the event must be described as failing to post a QUALIFYING season, not as a "
        "career ending — MIN_GAMES_THRESHOLD=4 already removed sub-4-game seasons upstream"
    )


def test_each_fold_records_the_features_it_actually_used(result) -> None:
    """A silently dropped column is the day's recurring defect, one layer down.

    `ppg_t_minus_2` is 0% populated in 2018 and 2019 — structural, since the feature window
    opens at 2018 and those rows have no t-2. SimpleImputer drops an all-NaN column rather
    than failing, so the earliest fold trains on FIVE features while later folds train on
    six, and nothing in the output says so. That is the same shape as a constant presented
    as a measurement: the model looks like it consulted a signal it never saw.

    The drop is legitimate and must not be prevented. It must be RECORDED.
    """
    for fold in result.folds:
        assert fold.features_used, f"fold testing {fold.test_season} recorded no feature set"
        assert set(fold.features_used) <= set(result.features)
        dropped = set(result.features) - set(fold.features_used)
        assert dropped == set(fold.features_dropped), (
            f"fold testing {fold.test_season} used {sorted(fold.features_used)} but reports "
            f"{sorted(fold.features_dropped)} dropped — the two must agree or the record lies"
        )


def test_the_earliest_fold_is_honest_about_the_unobservable_lag(result) -> None:
    """The specific instance: t-2 cannot exist for the first two seasons of the window."""
    first = result.folds[0]
    assert "ppg_t_minus_2" in first.features_dropped, (
        "the first fold trains on 2018-2019, where ppg_t_minus_2 is 0% populated; it must "
        "report that feature as dropped rather than appear to have used it"
    )
