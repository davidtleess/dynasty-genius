"""P(returns) — the availability factor of the dynasty hurdle.

The product estimates points CONDITIONAL ON PLAYING and calls the result dynasty value.
That is one of two factors. This module estimates the other: given what a player did in
season t, what is the probability he posts a qualifying season in t+1 or t+2 at all.

Value composes as ``P(plays) x E[points | plays]``. Composing it is deliberately NOT done
here — estimating a term and changing every published number are separate acts with
different blast radii (DG-125).

WHAT THE EVENT ACTUALLY IS. ``outcome_returned`` is False when no qualifying season was
observed at t+1 or t+2. The upstream assembler already drops seasons under
``MIN_GAMES_THRESHOLD=4``, so the label means "did not post a QUALIFYING season", which is
weaker and narrower than "his career ended". A model fit to it is partly modelling this
pipeline's own filter. ``EVENT_DEFINITION`` carries that sentence so anything surfacing a
number from here has no excuse for overstating it.

WHY WALK-FORWARD. The AUC that motivated this work (0.787/0.822/0.830/0.753) was measured
under GroupKFold-by-player, which is not a temporal split: it lets a 2023 season train a
prediction about 2019. Expanding-window validation by season is the only design that
estimates what this model would actually have done. Expect lower numbers, and prefer them.

WHY STANDARDISED. L2-penalised coefficients are penalised by RAW magnitude, so without
scaling a feature on a small numeric range (snap_share, 0-1) needs a large coefficient to
matter and is shrunk hardest, while one on a large range (ppg_t, 0-30) needs almost none.
That is measurably what suppressed the efficiency features in Engine B; the scaler is here
so this model does not inherit it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

EVENT_DEFINITION = (
    "outcome_returned=False means the player posted no QUALIFYING season (>= "
    "MIN_GAMES_THRESHOLD games) at t+1 or t+2. It is this pipeline's qualification event, "
    "not a football fact: it does not establish that a career ended, that the player "
    "retired, or that he took zero snaps."
)

# Populated for every complete-window row at every position, so a fold is never thinned by
# a feature that only exists for one position. Deliberately small: 2,879 rows across four
# positions does not support a wide model, and the ticket's floor is beating the base rate.
FEATURES: tuple[str, ...] = (
    "age",
    "games_t",
    "ppg_t",
    "snap_share",
    "ppg_t_minus_1",
    "ppg_t_minus_2",
)

MIN_TRAIN_SEASONS = 2


@dataclass(frozen=True)
class Fold:
    test_season: int
    train_seasons: tuple[int, ...]
    n_train: int
    n_test: int
    predictions: tuple[float, ...]
    truths: tuple[int, ...]
    metrics: Mapping[str, float]
    # A feature with no observed value anywhere in THIS fold's training window cannot be
    # fit, and SimpleImputer drops such a column silently. The drop is legitimate — you
    # cannot learn from a column you never saw — but an unrecorded one makes the model
    # appear to have consulted a signal it never had. Both lists are published so the two
    # can be checked against each other.
    features_used: tuple[str, ...] = ()
    features_dropped: tuple[str, ...] = ()


@dataclass(frozen=True)
class AvailabilityResult:
    folds: tuple[Fold, ...]
    by_position: Mapping[str, Mapping[str, float]]
    calibration_bins: tuple[Mapping[str, float], ...]
    model_brier: float | None
    baseline_brier: float | None
    base_rate: float | None
    event_definition: str = EVENT_DEFINITION
    features: tuple[str, ...] = field(default=FEATURES)


def _num(value: Any) -> float:
    if value in ("True", "true"):
        return 1.0
    if value in ("False", "false"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _matrix(rows: Sequence[Mapping[str, Any]], features: Sequence[str] = FEATURES) -> np.ndarray:
    return np.array([[_num(r.get(f, "")) for f in features] for r in rows], dtype=float)


def _observable(train_rows: Sequence[Mapping[str, Any]]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split FEATURES into those with at least one observed value in this window, and the rest.

    `ppg_t_minus_2` is the live instance: it is 0% populated in 2018 and 2019 because the
    feature window opens at 2018 and those rows have no t-2 to look back to. Structural,
    not a data defect — but the earliest fold therefore fits five features while later
    folds fit six, and that difference has to appear in the record rather than in a
    warning nobody reads.
    """
    full = _matrix(train_rows)
    observed = ~np.all(np.isnan(full), axis=0)
    used = tuple(f for f, keep in zip(FEATURES, observed) if keep)
    dropped = tuple(f for f, keep in zip(FEATURES, observed) if not keep)
    return used, dropped


def _labels(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.array([1 if r["outcome_returned"] == "True" else 0 for r in rows], dtype=int)


def auc(truths: Sequence[int], scores: Sequence[float]) -> float:
    """Rank-based AUC (Mann-Whitney), tie-aware. Returns 0.5 when one class is absent."""
    y = np.asarray(truths)
    s = np.asarray(scores, dtype=float)
    pos, neg = int((y == 1).sum()), int((y == 0).sum())
    if pos == 0 or neg == 0:
        return 0.5
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), dtype=float)
    ranks[order] = np.arange(1, len(s) + 1, dtype=float)
    # average ranks within ties, so a constant predictor scores exactly 0.5
    _, inverse, counts = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts), dtype=float)
    np.add.at(sums, inverse, ranks)
    ranks = (sums / counts)[inverse]
    return float((ranks[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def brier(truths: Sequence[int], probs: Sequence[float]) -> float:
    return float(np.mean((np.asarray(probs, dtype=float) - np.asarray(truths, dtype=float)) ** 2))


def _calibration(truths: Sequence[int], probs: Sequence[float], bins: int = 10) -> tuple[dict, ...]:
    """Observed rate vs mean predicted, by bin — the check a bare AUC cannot make."""
    y = np.asarray(truths, dtype=float)
    p = np.asarray(probs, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    out: list[dict] = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi) if hi < 1.0 else (p >= lo) & (p <= hi)
        if not mask.any():
            continue
        out.append({
            "bin_low": float(lo),
            "bin_high": float(hi),
            "n": int(mask.sum()),
            "mean_predicted": float(p[mask].mean()),
            "observed_rate": float(y[mask].mean()),
        })
    return tuple(out)


def _fit(train_rows: Sequence[Mapping[str, Any]], features: Sequence[str]) -> Pipeline:
    pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000)),
    ])
    pipe.fit(_matrix(train_rows, features), _labels(train_rows))
    return pipe


def walk_forward_availability(
    rows: Iterable[Mapping[str, Any]],
    *,
    min_train_seasons: int = MIN_TRAIN_SEASONS,
) -> AvailabilityResult:
    """Expanding-window validation of P(returns), one fold per testable season.

    Only rows with a resolved ``outcome_returned`` participate: outside a complete outcome
    window the return is UNOBSERVED rather than negative, and training on it as a negative
    would teach the model that every currently-active player washed out.
    """
    usable = [r for r in rows if r.get("outcome_returned") in ("True", "False")]
    seasons = sorted({int(r["feature_season"]) for r in usable})

    folds: list[Fold] = []
    for index, test_season in enumerate(seasons):
        train_seasons = tuple(s for s in seasons[:index])
        if len(train_seasons) < min_train_seasons:
            continue
        train_rows = [r for r in usable if int(r["feature_season"]) in train_seasons]
        test_rows = [r for r in usable if int(r["feature_season"]) == test_season]
        if not train_rows or not test_rows:
            continue

        used, dropped = _observable(train_rows)
        model = _fit(train_rows, used)
        probs = model.predict_proba(_matrix(test_rows, used))[:, 1]
        truths = _labels(test_rows)
        folds.append(Fold(
            test_season=test_season,
            train_seasons=train_seasons,
            n_train=len(train_rows),
            n_test=len(test_rows),
            features_used=used,
            features_dropped=dropped,
            predictions=tuple(float(p) for p in probs),
            truths=tuple(int(t) for t in truths),
            metrics={
                "auc": auc(truths, probs),
                "brier": brier(truths, probs),
                # the honest floor: predict the TRAINING base rate for everyone
                "baseline_brier": brier(truths, np.full(len(truths), _labels(train_rows).mean())),
                "base_rate": float(truths.mean()),
            },
        ))

    all_truth = [t for f in folds for t in f.truths]
    all_prob = [p for f in folds for p in f.predictions]
    all_rows = [r for f in folds for r in
                [x for x in usable if int(x["feature_season"]) == f.test_season]]

    by_position: dict[str, dict[str, float]] = {}
    for pos in ("QB", "RB", "WR", "TE"):
        idx = [i for i, r in enumerate(all_rows) if r.get("position") == pos]
        if not idx:
            continue
        t = [all_truth[i] for i in idx]
        p = [all_prob[i] for i in idx]
        by_position[pos] = {
            "n": len(idx),
            "auc": auc(t, p),
            "brier": brier(t, p),
            "base_rate": float(np.mean(t)),
        }

    base_rate = float(np.mean(all_truth)) if all_truth else None
    return AvailabilityResult(
        folds=tuple(folds),
        by_position=by_position,
        calibration_bins=_calibration(all_truth, all_prob) if all_truth else (),
        model_brier=brier(all_truth, all_prob) if all_truth else None,
        baseline_brier=(
            float(np.mean([f.metrics["baseline_brier"] * f.n_test for f in folds]) /
                  np.mean([f.n_test for f in folds]))
            if folds else None
        ),
        base_rate=base_rate,
    )
