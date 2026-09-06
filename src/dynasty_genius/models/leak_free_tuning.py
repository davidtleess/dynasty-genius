"""Ridge penalty selection that cannot learn from the answer (DG-027, corrected DG-177).

The inherited selector validated on one season and trained on strictly earlier
seasons with the validation season's players held out. Two things were still open:

1. A training row one season before the validation season is LABELLED from the
   validation season and the one after it — its label was not closed at the inner
   validation date. Inner training rows now obey the same closure rule as the outer
   split: ``t + window <= v``.
2. The imputer was fitted on the whole training window before the inner split, so the
   validation rows shaped the medians used to score them. It is now fitted inside each
   inner fold on that fold's training rows only.

It still RAISES rather than degrading: a grouped split that quietly reverts to random
when its group column is missing reports a clean number and changes nothing.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error

from src.dynasty_genius.models.label_closure import LABEL_WINDOW_SEASONS

PREPROCESSING = "median_imputer_fit_inside_each_inner_fold"


def make_imputer(strategy: str = "median") -> SimpleImputer:
    """The deployed trainer's imputer: keeps an all-missing column (as zeros) so a
    fold whose window predates a lag column still sees the same feature set."""
    return SimpleImputer(strategy=strategy, keep_empty_features=True)


def select_alpha_leak_free(
    X: np.ndarray,
    y: np.ndarray,
    seasons: np.ndarray,
    player_ids: Any,
    alphas: Iterable[float],
    *,
    window: int = LABEL_WINDOW_SEASONS,
    imputer_strategy: str = "median",
) -> tuple[float, dict[str, Any]]:
    """Choose the ridge penalty on expanding-time folds clustered on player, with every
    inner training label closed at the validation season and preprocessing fitted per fold.

    ``X`` may contain NaN; it is imputed inside each fold. Returns ``(alpha, meta)``.
    """
    if player_ids is None:
        raise ValueError(
            "alpha cannot be selected without leakage: no player column was supplied, "
            "and random folds on panel data put the same player on both sides"
        )
    player_ids = np.asarray(player_ids, dtype=object)
    if len(player_ids) != len(y) or any(p is None or p != p for p in player_ids):
        raise ValueError(
            "alpha cannot be selected without leakage: the player column is incomplete"
        )

    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    seasons = np.asarray(seasons).astype(int)
    ordered = sorted(np.unique(seasons))
    folds: list[tuple[np.ndarray, np.ndarray]] = []
    for season in ordered:
        val = np.flatnonzero(seasons == season)
        if val.size == 0:
            continue
        val_players = set(player_ids[val])
        closed = seasons + window <= season
        train = np.flatnonzero(closed & np.array([p not in val_players for p in player_ids]))
        if train.size == 0:
            continue
        folds.append((train, val))

    if not folds:
        raise ValueError(
            "alpha cannot be selected without leakage: no expanding-time fold survives "
            f"with the player held out and labels closed (window {window}; seasons present: "
            f"{ordered})"
        )

    alphas = [float(a) for a in alphas]
    errors_by_alpha: dict[float, list[float]] = {a: [] for a in alphas}
    for train, val in folds:
        imputer = make_imputer(imputer_strategy)
        x_tr = imputer.fit_transform(X[train])
        x_va = imputer.transform(X[val])
        for alpha in alphas:
            pred = Ridge(alpha=alpha).fit(x_tr, y[train]).predict(x_va)
            errors_by_alpha[alpha].append(float(mean_squared_error(y[val], pred)))

    mean_errors = {a: float(np.mean(e)) for a, e in errors_by_alpha.items()}
    best_alpha = min(alphas, key=lambda a: mean_errors[a])
    return best_alpha, {
        "method": "expanding_time_folds_clustered_on_player_with_closed_labels",
        "label_window_seasons": int(window),
        "preprocessing": PREPROCESSING,
        "folds": len(folds),
        "fold_indices": folds,
        "validation_seasons": [int(seasons[val].min()) for _, val in folds],
        "mean_cv_mse": mean_errors[best_alpha],
        "mean_cv_mse_by_alpha": mean_errors,
        "fold_mse_by_alpha": errors_by_alpha,
    }
