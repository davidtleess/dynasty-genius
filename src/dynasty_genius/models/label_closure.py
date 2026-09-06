"""The one label-closure rule every walk-forward shares (DG-177, round 1).

A label that spans ``window`` seasons after feature season ``t`` is final only once
season ``t + window`` has been played. A forecast made after season ``s`` may therefore
train on rows with ``t + window <= s`` and on nothing later. That is the whole rule,
and it lives in one place so the backtest harness, the availability walk-forward, the
trainer's inner alpha selection and the veteran evaluator cannot drift apart again —
three of them were open when this was written, each in its own way.

Rules:
``labels_known_at_cutoff``   t + window <= s   (honest; equals the trainer's DG-026
                              ``no_shared_outcome_season`` for a single test season)
``window_closed_before_test`` t + window <  s   (one season tighter; DG-162's rule,
                              kept so that table can be reproduced)
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd

#: The served Engine B outcome spans the two seasons after the feature season.
LABEL_WINDOW_SEASONS = 2

CUTOFF_RULES = ("labels_known_at_cutoff", "window_closed_before_test")


class FutureLabelError(ValueError):
    """A training row's label was not known at the forecast cutoff."""


def admissible_train_seasons(
    seasons: Iterable[int],
    test_season: int,
    rule: str = "labels_known_at_cutoff",
    window: int = LABEL_WINDOW_SEASONS,
) -> list[int]:
    """Feature seasons whose labels were fully known when forecasting ``test_season``."""
    if rule == "labels_known_at_cutoff":
        keep = lambda t: t + window <= test_season  # noqa: E731
    elif rule == "window_closed_before_test":
        keep = lambda t: t + window < test_season  # noqa: E731
    else:
        raise ValueError(f"unknown cutoff rule {rule!r}; expected one of {CUTOFF_RULES}")
    return sorted(int(t) for t in set(int(s) for s in seasons) if keep(int(t)))


def closed_train_mask(
    feature_seasons: pd.Series,
    test_season: int,
    rule: str = "labels_known_at_cutoff",
    window: int = LABEL_WINDOW_SEASONS,
) -> pd.Series:
    """Boolean mask over ``feature_seasons`` selecting rows whose labels were closed."""
    allowed = admissible_train_seasons(feature_seasons.unique(), test_season, rule=rule, window=window)
    return feature_seasons.astype(int).isin(allowed)


def assert_labels_known(
    train: pd.DataFrame,
    test_season: int,
    rule: str = "labels_known_at_cutoff",
    window: int = LABEL_WINDOW_SEASONS,
) -> None:
    """Refuse a training frame carrying any row whose label was open at the cutoff."""
    present = sorted(int(s) for s in train["feature_season"].unique())
    allowed = set(admissible_train_seasons(present, test_season, rule=rule, window=window))
    open_windows = [s for s in present if s not in allowed]
    if open_windows:
        raise FutureLabelError(
            f"training rows from feature seasons {open_windows} are labelled from seasons "
            f"up to {max(open_windows) + window}, which were not known when forecasting "
            f"{test_season} (rule {rule!r}, window {window})"
        )
