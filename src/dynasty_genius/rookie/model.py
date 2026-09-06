"""The estimator: draft capital → coherent per-season and cumulative forecasts.

Why this shape and nothing richer:

* The preserved study measured draft capital alone at AUC 0.813 (leave-one-class-out) and
  the college columns we hold at +0.004 on top of it, interval spanning zero. DG-162 and
  DG-163 found the same pattern on the veteran side. The candidate is the simple thing
  built honestly, not a wider thing built quickly.
* Pooled across positions with position main effects and a position × log(pick)
  interaction; log(pick) because the value curve is convex in pick number.

THE CONSTRUCTION — a three-state chain per NFL season (round-2 review, item 2). Round 1's
hazard construction made cumulative probabilities monotone but still let P(qualifies in j)
exceed P(appears in j) on four historical rows and P(qualified by h) exceed P(appeared by h)
on seven, because qualification and appearance were modelled side by side. Now each season
is a step of a chain whose history state is

    s = 0  never appeared before this season
    s = 1  appeared before, never qualified
    s = 2  qualified before

with two transition families per (season j, state s), each a logistic on the design matrix
fitted to exactly that conditioning population:

    a_j|s = P(appears in j | s)
    q_j|s = P(qualifies in j | appears in j, s)      fitted on the appearers in state s

so a qualifying season can only happen inside an appearance. With π_j the state
distribution before season j (π_1 = (1, 0, 0)):

    P(A_j)   = Σ_s π_s a_j|s
    P(Qy_j)  = Σ_s π_s a_j|s q_j|s                    ≤ P(A_j)
    π'_0 = π_0 (1 − a|0)
    π'_1 = π_0 a|0 (1 − q|0) + π_1 (1 − a|1 q|1)
    π'_2 = π_2 + π_0 a|0 q|0 + π_1 a|1 q|1
    P(appeared by j) = 1 − π'_0     P(qualified by j) = π'_2   ≤ 1 − π'_0
    E[N_h] = Σ_{j≤h} P(Qy_j)                             ≥ P(qualified by h)

Every bound the review asked for holds by arithmetic, for any input. A population too thin
to fit falls back to a recorded constant (``constant_fits``), never silently.

LEVELS, each conditional on an exactly matched event and unconditional on history:

    E[points_j | A_j], E[games_j | A_j], E[ppg_j | A_j]    ridge on the appearers
    E[ppg_j | Qy_j]                                          ridge on the qualifiers

and the unconditional pair, valid because points and games are exactly zero without an
appearance:  E[points_j] = P(A_j) · E[points_j | A_j],  E[games_j] = P(A_j) · E[games_j | A_j].

VARIANTS (the bounded menu the inner-window policy chooses from, evaluate.py):
    plain         the design above
    trend         + a linear class-year term, centred on the last training class
    trend_qb_r1   + the class-year term + a first-round-quarterback indicator (the one
                  cell the round-2 calibration assessment singles out; no blanket offset)

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

__all__ = ["FEATURE_COLUMNS", "MODEL_VERSION", "VARIANTS", "RookieCapitalModel", "design_matrix"]

MODEL_VERSION = "dg165_rookie_capital_v3_chain"
VARIANTS: tuple[str, ...] = ("plain", "trend", "trend_qb_r1")

# The ONLY columns the model reads. Draft capital and the draft-day age, nothing else.
FEATURE_COLUMNS: tuple[str, ...] = ("pick", "round", "age_at_draft", "position")

# L2 strength on standardised features, explicit so a change is a visible decision.
L2_C = 1.0
RIDGE_ALPHA = 1.0
# Below this many rows, or with a single class, a family falls back to a recorded constant.
MIN_ROWS_PER_FIT = 15
MAX_GAMES = 17.0
STATES = (0, 1, 2)


def _design_names(positions: tuple[str, ...], variant: str = "plain") -> list[str]:
    names = ["log_pick", "round", "age_at_draft"]
    names += [f"pos_{p}" for p in positions]
    names += [f"log_pick_x_{p}" for p in positions]
    if variant in ("trend", "trend_qb_r1"):
        names.append("class_year")
    if variant == "trend_qb_r1":
        names.append("qb_first_round")
    return names


def design_matrix(
    frame: pd.DataFrame,
    *,
    age_median_by_position: Mapping[str, float],
    positions: tuple[str, ...] = SKILL_POSITIONS,
    variant: str = "plain",
    trend_reference_year: int | None = None,
) -> np.ndarray:
    """Numeric design from the four feature columns. Age is imputed by position median.

    Deliberately NO missing-age indicator: the id-less prospects all lack a birth date, so
    an indicator would learn "missing age ⇒ no record", a data-collection artifact, and
    penalise a 2026 rookie whose birth date is merely not yet on file. Imputation alone
    keeps a missing age invisible to the fit (pinned by a test).
    """
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; choose from {VARIANTS}")
    unknown = set(frame["position"]) - set(positions)
    if unknown:
        raise ValueError(f"positions outside the model: {sorted(unknown)}")
    log_pick = np.log(frame["pick"].astype(float).to_numpy())
    round_ = frame["round"].astype(float).to_numpy()
    age = pd.to_numeric(frame["age_at_draft"], errors="coerce").to_numpy(dtype=float)
    fill = frame["position"].map(age_median_by_position).to_numpy(dtype=float)
    age = np.where(np.isnan(age), fill, age)
    pos = frame["position"].to_numpy()
    columns = [log_pick, round_, age]
    for p in positions:
        columns.append((pos == p).astype(float))
    for p in positions:
        columns.append(log_pick * (pos == p).astype(float))
    if variant in ("trend", "trend_qb_r1"):
        if trend_reference_year is None:
            raise ValueError("a trend variant needs its reference year")
        # A linear class-year term, centred on the last training class so that scoring a
        # later class extrapolates by whole years. Selected only inside training windows.
        columns.append(frame["draft_season"].astype(float).to_numpy() - float(trend_reference_year))
    if variant == "trend_qb_r1":
        columns.append(((pos == "QB") & (round_ == 1)).astype(float))
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
    variant: str = "plain"
    policy: str = "direct"
    policy_selection: dict | None = None
    trend_reference_year: int | None = None
    age_median_by_position: dict[str, float] = field(default_factory=dict)
    n_train: dict[str, int] = field(default_factory=dict)
    constant_fits: dict[str, float] = field(default_factory=dict)
    _fits: dict[str, object] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.horizons = tuple(sorted(set(int(h) for h in self.horizons)))
        self.max_season = self.horizons[-1]
        if self.variant not in VARIANTS:
            raise ValueError(f"unknown variant {self.variant!r}; choose from {VARIANTS}")

    @property
    def trend(self) -> bool:
        return self.variant in ("trend", "trend_qb_r1")

    @property
    def arm_id(self) -> str:
        return f"{MODEL_VERSION}:{self.policy}:{self.variant}"

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
        # A qualifying season without a stat row is impossible by the panel's construction;
        # assert it rather than let the chain absorb a broken label.
        broken = np.nansum((qual == 1) & (appear == 0))
        if broken:
            raise ValueError(f"{int(broken)} labelled qualifications without an appearance; the labels are broken")
        for j in range(1, J + 1):
            season_known = ~np.isnan(appear[:, j - 1]) & ~np.isnan(qual[:, j - 1])
            if j == 1:
                history_known = np.ones(len(train), dtype=bool)
                state = np.zeros(len(train), dtype=int)
            else:
                history_known = ~np.isnan(appear[:, : j - 1]).any(axis=1) & ~np.isnan(qual[:, : j - 1]).any(axis=1)
                appeared_before = np.nan_to_num(appear[:, : j - 1]).max(axis=1) == 1
                qualified_before = np.nan_to_num(qual[:, : j - 1]).max(axis=1) == 1
                state = np.where(qualified_before, 2, np.where(appeared_before, 1, 0))
            rows_known = season_known & history_known
            for s in (STATES if j > 1 else (0,)):
                in_state = rows_known & (state == s)
                self._fit_binary(f"a_{j}|s{s}", train, in_state, appear[:, j - 1])
                self._fit_binary(f"q_{j}|s{s}", train, in_state & (appear[:, j - 1] == 1), qual[:, j - 1])
            appeared = season_known & (appear[:, j - 1] == 1)
            self._fit_level(f"points_{j}|A", train, appeared, train[f"points_{j}"].to_numpy(dtype=float))
            self._fit_level(f"games_{j}|A", train, appeared, train[f"games_{j}"].to_numpy(dtype=float))
            self._fit_level(f"ppg_{j}|A", train, appeared, train[f"ppg_{j}"].to_numpy(dtype=float))
            qualified = season_known & (qual[:, j - 1] == 1)
            self._fit_level(f"ppg_{j}|Q", train, qualified, train[f"ppg_{j}"].to_numpy(dtype=float))
        return self

    def _design(self, frame: pd.DataFrame) -> np.ndarray:
        return design_matrix(frame, age_median_by_position=self.age_median_by_position, positions=self.positions,
                             variant=self.variant, trend_reference_year=self.trend_reference_year)

    def _fit_binary(self, name: str, train: pd.DataFrame, mask: np.ndarray, y_all: np.ndarray) -> None:
        rows = train.loc[mask]
        y = y_all[mask].astype(int)
        self.n_train[name] = int(len(rows))
        if len(rows) < MIN_ROWS_PER_FIT or y.min() == y.max():
            value = float(y.mean()) if len(rows) else 0.5
            self.constant_fits[name] = value
            self._fits[name] = _Constant(value)
            return
        self._fits[name] = _logistic().fit(self._design(rows), y)

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
        self._fits[name] = _ridge().fit(self._design(rows), y)

    # ------------------------------------------------------------------ prediction
    def _p(self, name: str, X: np.ndarray) -> np.ndarray:
        return self._fits[name].predict_proba(X)[:, 1]

    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        """One row per input row; every column is derived from the chain."""
        if not self._fits:
            raise RuntimeError("model is not fitted")
        X = self._design(frame)
        n = len(frame)
        out = {"gsis_id": frame["gsis_id"].to_numpy()}
        pi = [np.ones(n), np.zeros(n), np.zeros(n)]
        expected_qual_seasons = np.zeros(n)
        for j in range(1, self.max_season + 1):
            states = STATES if j > 1 else (0,)
            a = {s: self._p(f"a_{j}|s{s}", X) for s in states}
            q = {s: self._p(f"q_{j}|s{s}", X) for s in states}
            p_appear = sum(pi[s] * a[s] for s in states)
            p_qual = sum(pi[s] * a[s] * q[s] for s in states)
            new0 = pi[0] * (1 - a[0])
            first_qual = pi[0] * a[0] * q[0]
            if j > 1:
                first_qual = first_qual + pi[1] * a[1] * q[1]
                new1 = pi[0] * a[0] * (1 - q[0]) + pi[1] * (1 - a[1] * q[1])
            else:
                new1 = pi[0] * a[0] * (1 - q[0])
            new2 = pi[2] + first_qual
            pi = [new0, new1, new2]
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
                out[f"p_appear_by_h{j}"] = 1.0 - pi[0]
                out[f"p_qual_h{j}"] = pi[2]
                out[f"e_qual_seasons_h{j}"] = np.clip(expected_qual_seasons, 0.0, float(j))
        return pd.DataFrame(out, index=frame.index)

    def describe(self) -> dict:
        return {
            "model_version": MODEL_VERSION,
            "arm_id": self.arm_id,
            "variant": self.variant,
            "policy": self.policy,
            "policy_selection": self.policy_selection,
            "trend": self.trend,
            "trend_reference_year": self.trend_reference_year,
            "estimator": f"three-state chain per season: LogisticRegression (L2, C={L2_C}) per (season, state); levels: Ridge (alpha={RIDGE_ALPHA}); StandardScaler",
            "design_columns": _design_names(self.positions, self.variant),
            "feature_columns": list(FEATURE_COLUMNS),
            "horizons": list(self.horizons),
            "construction": (
                "states s0 never appeared / s1 appeared never qualified / s2 qualified before; a_j|s = P(appear | s), "
                "q_j|s = P(qualify | appear, s); P(A_j) = sum_s pi_s a; P(Qy_j) = sum_s pi_s a q <= P(A_j); "
                "P(qualified by j) = pi_2 <= 1 - pi_0 = P(appeared by j); E[N_h] = sum_j P(Qy_j); "
                "E[points_j] = P(A_j) * E[points_j | A_j] (points are exactly 0 without an appearance)"
            ),
            "age_median_by_position": self.age_median_by_position,
            "n_train_by_family": dict(self.n_train),
            "constant_fits": dict(self.constant_fits),
        }
