"""The estimator: draft capital → coherent per-season and cumulative forecasts.

Why this shape and nothing richer:

* The preserved study measured draft capital alone at AUC 0.813 (leave-one-class-out) and
  the college columns we hold at +0.004 on top of it, interval spanning zero. DG-162 and
  DG-163 found the same pattern on the veteran side. The candidate is the simple thing
  built honestly, not a wider thing built quickly.
* Pooled across positions with position main effects and a position × log(pick)
  interaction; log(pick) because the value curve is convex in pick number.

THE CONSTRUCTION (round-1 review, item 3). Separate logistic fits per horizon produced
cumulative probabilities that DECREASED with h for 80 of 80 rookies. Nested events are now
built from per-season hazards, so coherence holds by arithmetic rather than by hope:

    a_j  = P(appears in season j | no appearance before j)     first-appearance hazard
    ρ_j  = P(appears in season j | appeared before j)          re-appearance rate
    q_j  = P(qualifies in season j | not qualified before j)   first-qualification hazard
    r_j  = P(qualifies in season j | qualified before j)       re-qualification rate

    P(appear by h) = 1 − Π_{j≤h} (1 − a_j)                      monotone in h
    P(A_j)         = a_j (1 − P(appear by j−1)) + ρ_j P(appear by j−1)   ≤ P(appear by j)
    P(Q_h), P(Qy_j) likewise from q_j and r_j
    E[N_h]         = Σ_{j≤h} P(Qy_j)                              ≥ P(Q_h), ≤ h

Each hazard/rate is a logistic on the design matrix fitted to exactly its conditioning
population (the at-risk rows, or the previously-qualified rows), with a recorded constant
fallback when that population is too thin to fit — visible in ``n_train`` and
``constant_fits``, never silent.

LEVELS, each conditional on an exactly matched event:

    E[points_j | A_j], E[games_j | A_j], E[ppg_j | A_j]    ridge on the appearers
    E[ppg_j | Qy_j]                                          ridge on the qualifiers

and the unconditional pair, valid because points and games are exactly zero when he does
not appear:  E[points_j] = P(A_j) · E[points_j | A_j],  E[games_j] = P(A_j) · E[games_j | A_j].

No other product is formed here. Replacement, lineup policy and value are the consumer's.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.rookie.cohort import SKILL_POSITIONS

__all__ = ["FEATURE_COLUMNS", "MODEL_VERSION", "RookieCapitalModel", "design_matrix"]

MODEL_VERSION = "dg165_rookie_capital_v2_hazard"

# The ONLY columns the model reads. Draft capital and the draft-day age, nothing else.
FEATURE_COLUMNS: tuple[str, ...] = ("pick", "round", "age_at_draft", "position")

# L2 strength on standardised features, explicit so a change is a visible decision.
L2_C = 1.0
RIDGE_ALPHA = 1.0
# Below this many rows, or with a single class, a family falls back to a recorded constant.
MIN_ROWS_PER_FIT = 15
MAX_GAMES = 17.0


def _design_names(positions: tuple[str, ...], trend: bool = False) -> list[str]:
    names = ["log_pick", "round", "age_at_draft"]
    names += [f"pos_{p}" for p in positions]
    names += [f"log_pick_x_{p}" for p in positions]
    if trend:
        names.append("class_year")
    return names


def design_matrix(
    frame: pd.DataFrame,
    *,
    age_median_by_position: Mapping[str, float],
    positions: tuple[str, ...] = SKILL_POSITIONS,
    trend_reference_year: int | None = None,
) -> np.ndarray:
    """Numeric design from the four feature columns. Age is imputed by position median.

    Deliberately NO missing-age indicator: the id-less prospects all lack a birth date, so
    an indicator would learn "missing age ⇒ no record", a data-collection artifact, and
    penalise a 2026 rookie whose birth date is merely not yet on file. Imputation alone
    keeps a missing age invisible to the fit (pinned by a test).
    """
    unknown = set(frame["position"]) - set(positions)
    if unknown:
        raise ValueError(f"positions outside the model: {sorted(unknown)}")
    log_pick = np.log(frame["pick"].astype(float).to_numpy())
    round_ = frame["round"].astype(float).to_numpy()
    age = pd.to_numeric(frame["age_at_draft"], errors="coerce").to_numpy(dtype=float)
    fill = frame["position"].map(age_median_by_position).to_numpy(dtype=float)
    age = np.where(np.isnan(age), fill, age)
    columns = [log_pick, round_, age]
    for p in positions:
        columns.append((frame["position"].to_numpy() == p).astype(float))
    for p in positions:
        columns.append(log_pick * (frame["position"].to_numpy() == p).astype(float))
    if trend_reference_year is not None:
        # A linear class-year term, centred on the last training class so that scoring a
        # later class extrapolates by whole years. The bounded experiment the round-1
        # review asked for; selected only inside training windows (evaluate.py).
        columns.append(frame["draft_season"].astype(float).to_numpy() - float(trend_reference_year))
    return np.column_stack(columns)


class _Constant:
    """A recorded constant estimator for a population too thin to fit."""

    def __init__(self, value: float):
        self.value = float(value)

    def predict_proba(self, X):
        p = np.full(len(X), np.clip(self.value, 0.01, 0.99))
        return np.column_stack([1 - p, p])

    def predict(self, X):
        return np.full(len(X), self.value)


def _logistic() -> Pipeline:
    return Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(C=L2_C, max_iter=5000))])


def _ridge() -> Pipeline:
    return Pipeline([("scale", StandardScaler()), ("reg", Ridge(alpha=RIDGE_ALPHA))])


@dataclass
class RookieCapitalModel:
    """Fit once per forecast date on rows whose labels were observable at that date."""

    horizons: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    positions: tuple[str, ...] = SKILL_POSITIONS
    trend: bool = False
    trend_reference_year: int | None = None
    trend_selection: dict | None = None
    age_median_by_position: dict[str, float] = field(default_factory=dict)
    n_train: dict[str, int] = field(default_factory=dict)
    constant_fits: dict[str, float] = field(default_factory=dict)
    _fits: dict[str, object] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.horizons = tuple(sorted(set(int(h) for h in self.horizons)))
        self.max_season = self.horizons[-1]

    # ------------------------------------------------------------------ fitting
    def fit(self, train: pd.DataFrame) -> "RookieCapitalModel":
        missing = [c for c in FEATURE_COLUMNS if c not in train.columns]
        if missing:
            raise ValueError(f"training frame lacks feature columns {missing}")
        if self.trend:
            self.trend_reference_year = int(train["draft_season"].max())
        ages = pd.to_numeric(train["age_at_draft"], errors="coerce")
        overall = float(np.nanmedian(ages)) if ages.notna().any() else 22.0
        self.age_median_by_position = {
            p: float(np.nanmedian(ages[train["position"] == p]))
            if (train["position"] == p).any() and ages[train["position"] == p].notna().any() else overall
            for p in self.positions
        }
        J = self.max_season
        appear = np.column_stack([train[f"appear_{j}"].to_numpy(dtype=float) for j in range(1, J + 1)])
        qual = np.column_stack([train[f"qy_{j}"].to_numpy(dtype=float) for j in range(1, J + 1)])
        for j in range(1, J + 1):
            season_known = ~np.isnan(appear[:, j - 1]) & ~np.isnan(qual[:, j - 1])
            if j == 1:
                appeared_before = np.zeros(len(train), dtype=bool)
                qualified_before = np.zeros(len(train), dtype=bool)
                history_known = np.ones(len(train), dtype=bool)
            else:
                history_known = ~np.isnan(appear[:, : j - 1]).any(axis=1) & ~np.isnan(qual[:, : j - 1]).any(axis=1)
                appeared_before = np.nan_to_num(appear[:, : j - 1]).max(axis=1) == 1
                qualified_before = np.nan_to_num(qual[:, : j - 1]).max(axis=1) == 1
            rows_known = season_known & history_known
            self._fit_binary(f"a_{j}", train, rows_known & ~appeared_before, appear[:, j - 1])
            self._fit_binary(f"q_{j}", train, rows_known & ~qualified_before, qual[:, j - 1])
            if j > 1:
                self._fit_binary(f"rho_{j}", train, rows_known & appeared_before, appear[:, j - 1])
                self._fit_binary(f"r_{j}", train, rows_known & qualified_before, qual[:, j - 1])
            appeared = season_known & (appear[:, j - 1] == 1)
            self._fit_level(f"points_{j}|A", train, appeared, train[f"points_{j}"].to_numpy(dtype=float))
            self._fit_level(f"games_{j}|A", train, appeared, train[f"games_{j}"].to_numpy(dtype=float))
            self._fit_level(f"ppg_{j}|A", train, appeared, train[f"ppg_{j}"].to_numpy(dtype=float))
            qualified = season_known & (qual[:, j - 1] == 1)
            self._fit_level(f"ppg_{j}|Q", train, qualified, train[f"ppg_{j}"].to_numpy(dtype=float))
        return self

    def _fit_binary(self, name: str, train: pd.DataFrame, mask: np.ndarray, y_all: np.ndarray) -> None:
        rows = train.loc[mask]
        y = y_all[mask].astype(int)
        self.n_train[name] = int(len(rows))
        if len(rows) < MIN_ROWS_PER_FIT or y.min() == y.max():
            value = float(y.mean()) if len(rows) else 0.5
            self.constant_fits[name] = value
            self._fits[name] = _Constant(value)
            return
        X = self._design(rows)
        self._fits[name] = _logistic().fit(X, y)

    def _fit_level(self, name: str, train: pd.DataFrame, mask: np.ndarray, y_all: np.ndarray) -> None:
        mask = mask & ~np.isnan(y_all)
        rows = train.loc[mask]
        y = y_all[mask]
        self.n_train[name] = int(len(rows))
        if len(rows) < MIN_ROWS_PER_FIT:
            value = float(y.mean()) if len(rows) else 0.0
            self.constant_fits[name] = value
            self._fits[name] = _Constant(value)
            return
        X = self._design(rows)
        self._fits[name] = _ridge().fit(X, y)

    def _design(self, frame: pd.DataFrame) -> np.ndarray:
        return design_matrix(frame, age_median_by_position=self.age_median_by_position, positions=self.positions,
                             trend_reference_year=self.trend_reference_year if self.trend else None)

    # ------------------------------------------------------------------ prediction
    def _p(self, name: str, X: np.ndarray) -> np.ndarray:
        return self._fits[name].predict_proba(X)[:, 1]

    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        """One row per input row; every column is derived from the hazard construction."""
        if not self._fits:
            raise RuntimeError("model is not fitted")
        X = self._design(frame)
        out = pd.DataFrame({"gsis_id": frame["gsis_id"].to_numpy()}, index=frame.index)
        n = len(frame)
        appear_by = np.zeros(n)
        qual_by = np.zeros(n)
        expected_qual_seasons = np.zeros(n)
        for j in range(1, self.max_season + 1):
            a = self._p(f"a_{j}", X)
            q = self._p(f"q_{j}", X)
            if j == 1:
                p_appear = a
                p_qual = q
                appear_by = a
                qual_by = q
            else:
                rho = self._p(f"rho_{j}", X)
                r = self._p(f"r_{j}", X)
                p_appear = a * (1 - appear_by) + rho * appear_by
                p_qual = q * (1 - qual_by) + r * qual_by
                appear_by = appear_by + a * (1 - appear_by)
                qual_by = qual_by + q * (1 - qual_by)
            expected_qual_seasons = expected_qual_seasons + p_qual
            points_given = np.clip(self._fits[f"points_{j}|A"].predict(X), 0.0, None)
            games_given = np.clip(self._fits[f"games_{j}|A"].predict(X), 1.0, MAX_GAMES)
            ppg_given = np.clip(self._fits[f"ppg_{j}|A"].predict(X), 0.0, None)
            ppg_given_qual = np.clip(self._fits[f"ppg_{j}|Q"].predict(X), 0.0, None)
            out[f"p_appear_year{j}"] = p_appear
            out[f"p_qual_year{j}"] = p_qual
            out[f"e_points_year{j}_given_appear"] = points_given
            out[f"e_games_year{j}_given_appear"] = games_given
            out[f"e_ppg_year{j}_given_appear"] = ppg_given
            out[f"e_points_year{j}"] = p_appear * points_given
            out[f"e_games_year{j}"] = p_appear * games_given
            out[f"e_ppg_given_qual_year{j}"] = ppg_given_qual
            if j in self.horizons:
                out[f"p_appear_by_h{j}"] = appear_by
                out[f"p_qual_h{j}"] = qual_by
                out[f"e_qual_seasons_h{j}"] = np.clip(expected_qual_seasons, 0.0, float(j))
        return out

    def describe(self) -> dict:
        return {
            "model_version": MODEL_VERSION,
            "estimator": f"per-season hazards and rates: sklearn LogisticRegression (L2, C={L2_C}); levels: Ridge (alpha={RIDGE_ALPHA}); all on StandardScaler",
            "design_columns": _design_names(self.positions, self.trend),
            "trend": bool(self.trend),
            "trend_reference_year": self.trend_reference_year,
            "trend_selection": self.trend_selection,
            "feature_columns": list(FEATURE_COLUMNS),
            "horizons": list(self.horizons),
            "construction": (
                "P(appear by h) = 1 - prod(1 - a_j); P(A_j) = a_j(1 - P(appear by j-1)) + rho_j P(appear by j-1); "
                "same for qualification with q_j, r_j; E[N_h] = sum_j P(Qy_j); "
                "E[points_j] = P(A_j) * E[points_j | A_j] (points are exactly 0 without an appearance)"
            ),
            "age_median_by_position": self.age_median_by_position,
            "n_train_by_family": dict(self.n_train),
            "constant_fits": dict(self.constant_fits),
        }
