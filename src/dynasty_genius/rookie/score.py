"""Score a draft class with a fitted model; every prospect gets a row and a status.

``coverage_status`` says how the number was produced, never silently:

* ``scored``              — pick, round, position and age all present;
* ``scored_age_imputed``  — age at draft missing, imputed by the model's position median
                            (the flag is also a model input, so the imputation is visible
                            to the fit, not hidden from it).

Undrafted rookies are not in the frame this function receives; the runner reports them
as ``undrafted_not_modelled`` from a separate roster read so the gap is named, not filled.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.dynasty_genius.rookie.model import MODEL_VERSION, RookieCapitalModel

__all__ = ["bootstrap_intervals", "score_class"]

IDENTITY_COLUMNS = ("gsis_id", "name", "position", "team", "draft_season", "pick", "round", "age_at_draft")


def score_class(model: RookieCapitalModel, rookies: pd.DataFrame) -> pd.DataFrame:
    if rookies["gsis_id"].duplicated().any():
        raise ValueError("duplicate gsis_id in the class to score")
    pred = model.predict(rookies)
    identity = [c for c in IDENTITY_COLUMNS if c in rookies.columns]
    out = rookies[identity].copy().reset_index(drop=True)
    age_missing = pd.to_numeric(rookies["age_at_draft"], errors="coerce").isna().to_numpy()
    out["coverage_status"] = np.where(age_missing, "scored_age_imputed", "scored")
    pred = pred.reset_index(drop=True).drop(columns=["gsis_id"])
    out = pd.concat([out, pred], axis=1)
    out["model_version"] = MODEL_VERSION
    assert len(out) == len(rookies), "a prospect went missing between input and output"
    return out


def bootstrap_intervals(
    train: pd.DataFrame,
    rookies: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    n_boot: int,
    seed: int = 20260906,
) -> pd.DataFrame:
    """90% intervals from refitting on player-resampled training sets.

    This is parameter uncertainty of the fit, not the outcome spread of one rookie: a
    first-round pick with P(Q_3)=0.8 still fails a fifth of the time, and that is in the
    probability itself, not in these bounds.
    """
    rng = np.random.default_rng(seed)
    draws: dict[str, list[np.ndarray]] = {}
    for _ in range(n_boot):
        sample = train.iloc[rng.integers(0, len(train), len(train))]
        try:
            m = RookieCapitalModel(horizons=horizons).fit(sample)
        except ValueError:
            continue  # a resample lost a class for one label; skip it, count below
        p = m.predict(rookies)
        for col in p.columns:
            if col == "gsis_id":
                continue
            draws.setdefault(col, []).append(p[col].to_numpy())
    out = pd.DataFrame({"gsis_id": rookies["gsis_id"].to_numpy()})
    for col, arrays in draws.items():
        stack = np.vstack(arrays)
        out[f"{col}_lo90"] = np.nanpercentile(stack, 5, axis=0)
        out[f"{col}_hi90"] = np.nanpercentile(stack, 95, axis=0)
    out.attrs["n_boot_effective"] = len(next(iter(draws.values()))) if draws else 0
    return out
