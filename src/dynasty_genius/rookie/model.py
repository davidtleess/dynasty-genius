"""The estimator: pooled logistic regressions on draft capital, position as a term.

Why this shape and nothing richer:

* The preserved study measured draft capital alone at AUC 0.813 (leave-one-class-out) and
  the college columns we hold at +0.004 on top of it, interval spanning zero. DG-162 and
  DG-163 found the same pattern on the veteran side. The candidate is therefore the simple
  thing, built honestly, not a wider thing built quickly.
* Pooled across positions with position main effects and a position × log(pick)
  interaction, because per-position samples (68-194 in the 2015-2020 study) do not support
  separate models, while the slope of the pick curve plainly differs by position.
* log(pick) rather than pick: the value curve is convex in pick number (pick 1 to 10 is a
  bigger step than 200 to 210), and a single log term captures that without a spline.

Three families are fitted per horizon, each on the rows whose label is observable:

    P(Q_h)        logistic on the design matrix, label ``q_h``
    P(played_h)   logistic, label ``played_h``
    P(qy_j)       logistic per NFL season j = 1..h, label ``qy_j``

and E[N_h] = Σ_{j<=h} P(qy_j) — bounded by h by construction, monotone in h, and it says
WHEN the qualifying seasons are expected, which is the delayed-breakout structure the review
asked for. No product of P and a conditional mean is formed here.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.rookie.cohort import SKILL_POSITIONS

__all__ = ["FEATURE_COLUMNS", "MODEL_VERSION", "RookieCapitalModel", "design_matrix"]

MODEL_VERSION = "dg165_rookie_capital_v1"

# The ONLY columns the model reads. Draft capital and the draft-day age, nothing else.
FEATURE_COLUMNS: tuple[str, ...] = ("pick", "round", "age_at_draft", "position")

# L2 strength. The design has 11 columns on ~2,200 rows; the default C=1 on standardised
# features is mild shrinkage, kept explicit so a change is a visible decision.
L2_C = 1.0


def _design_names(positions: tuple[str, ...]) -> list[str]:
    names = ["log_pick", "round", "age_at_draft"]
    names += [f"pos_{p}" for p in positions]
    names += [f"log_pick_x_{p}" for p in positions]
    return names


def design_matrix(
    frame: pd.DataFrame,
    *,
    age_median_by_position: Mapping[str, float],
    positions: tuple[str, ...] = SKILL_POSITIONS,
) -> np.ndarray:
    """Numeric design from the four feature columns. Age is imputed by position median.

    Deliberately NO missing-age indicator. Measured 2026-09-06: every one of the 107
    id-less washouts kept in the cohort lacks a birth date (PFR never recorded one for a
    player who never played), so an indicator would learn "missing age ⇒ washout" — a
    data-collection artifact — and penalise a 2026 rookie whose birth date is merely not
    yet on file. Imputation alone keeps a missing age invisible to the fit.
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
    return np.column_stack(columns)


def _logistic() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(C=L2_C, max_iter=5000)),
        ]
    )


@dataclass
class RookieCapitalModel:
    """Fit once per forecast date on rows whose labels were observable at that date."""

    horizons: tuple[int, ...] = (1, 2, 3, 4, 5)
    positions: tuple[str, ...] = SKILL_POSITIONS
    age_median_by_position: dict[str, float] = field(default_factory=dict)
    _qual: dict[int, Pipeline] = field(default_factory=dict, repr=False)
    _played: dict[int, Pipeline] = field(default_factory=dict, repr=False)
    _year: dict[int, Pipeline] = field(default_factory=dict, repr=False)
    n_train: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.horizons = tuple(sorted(set(int(h) for h in self.horizons)))

    # ------------------------------------------------------------------ fitting
    def fit(self, train: pd.DataFrame) -> "RookieCapitalModel":
        missing = [c for c in FEATURE_COLUMNS if c not in train.columns]
        if missing:
            raise ValueError(f"training frame lacks feature columns {missing}")
        ages = pd.to_numeric(train["age_at_draft"], errors="coerce")
        overall = float(np.nanmedian(ages)) if ages.notna().any() else 22.0
        self.age_median_by_position = {
            p: float(np.nanmedian(ages[train["position"] == p])) if (train["position"] == p).any()
            and ages[train["position"] == p].notna().any() else overall
            for p in self.positions
        }
        for h in self.horizons:
            self._qual[h] = self._fit_one(train, f"q_{h}")
            self._played[h] = self._fit_one(train, f"played_{h}")
        for j in range(1, self.horizons[-1] + 1):
            self._year[j] = self._fit_one(train, f"qy_{j}")
        return self

    def _fit_one(self, train: pd.DataFrame, label: str) -> Pipeline:
        rows = train.loc[train[label].notna()]
        y = rows[label].astype(int).to_numpy()
        if len(rows) == 0 or y.min() == y.max():
            raise ValueError(
                f"label {label}: {len(rows)} observable rows with classes {sorted(set(y))}; "
                "cannot fit a probability from a single class"
            )
        X = design_matrix(rows, age_median_by_position=self.age_median_by_position, positions=self.positions)
        self.n_train[label] = int(len(rows))
        return _logistic().fit(X, y)

    # ------------------------------------------------------------------ prediction
    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        """One row per input row: p_played_h, p_qual_h, e_qual_seasons_h, p_qual_year_j."""
        if not self._qual:
            raise RuntimeError("model is not fitted")
        X = design_matrix(frame, age_median_by_position=self.age_median_by_position, positions=self.positions)
        out = pd.DataFrame({"gsis_id": frame["gsis_id"].to_numpy()}, index=frame.index)
        year_p = {}
        for j, model in self._year.items():
            year_p[j] = model.predict_proba(X)[:, 1]
            out[f"p_qual_year{j}"] = year_p[j]
        for h in self.horizons:
            out[f"p_played_h{h}"] = self._played[h].predict_proba(X)[:, 1]
            out[f"p_qual_h{h}"] = self._qual[h].predict_proba(X)[:, 1]
            expected = np.sum([year_p[j] for j in range(1, h + 1)], axis=0)
            out[f"e_qual_seasons_h{h}"] = np.clip(expected, 0.0, float(h))
            with np.errstate(divide="ignore", invalid="ignore"):
                given = np.where(out[f"p_qual_h{h}"] > 1e-9, out[f"e_qual_seasons_h{h}"] / out[f"p_qual_h{h}"], np.nan)
            # E[N_h | Q_h] cannot exceed h and cannot be below 1 (a qualifier has >= 1).
            out[f"e_qual_seasons_given_qual_h{h}"] = np.clip(given, 1.0, float(h))
        return out

    def describe(self) -> dict:
        return {
            "model_version": MODEL_VERSION,
            "estimator": "sklearn LogisticRegression (L2, C=%s) on StandardScaler" % L2_C,
            "design_columns": _design_names(self.positions),
            "feature_columns": list(FEATURE_COLUMNS),
            "horizons": list(self.horizons),
            "age_median_by_position": self.age_median_by_position,
            "n_train_by_label": dict(self.n_train),
            "expected_seasons": "E[N_h] = sum_{j<=h} P(qualifies in NFL season j); bounded by h",
        }
