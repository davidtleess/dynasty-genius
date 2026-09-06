"""Score a draft class with a fitted model; every prospect gets a row and a status.

``identity_status`` says whether the NFL identity behind the row is resolved; an unresolved
prospect keeps NaN in every forecast column (the assembler says "no forecast: identity
unresolved", never "value 0"). ``coverage_status`` says how the number was produced:

* ``scored``              — pick, round, position and age all present;
* ``scored_age_imputed``  — age at draft missing, imputed by the model's position median.

Undrafted rookies are not in the frame this function receives; the runner reports them as
a named gap from the integration lane's roster audit, never filled here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.dynasty_genius.rookie.labels import LABEL_BASIS_UNRESOLVED
from src.dynasty_genius.rookie.model import MODEL_VERSION, RookieCapitalModel

__all__ = ["bootstrap_intervals", "score_class"]

IDENTITY_COLUMNS = ("gsis_id", "name", "position", "team", "draft_season", "pick", "round", "age_at_draft")


def score_class(model: RookieCapitalModel, rookies: pd.DataFrame) -> pd.DataFrame:
    if rookies["gsis_id"].duplicated().any():
        raise ValueError("duplicate gsis_id in the class to score")
    pred = model.predict(rookies)
    identity = [c for c in IDENTITY_COLUMNS if c in rookies.columns]
    out = rookies[identity].copy().reset_index(drop=True)
    unresolved = (
        rookies["label_basis"].astype(str).eq(LABEL_BASIS_UNRESOLVED).to_numpy()
        if "label_basis" in rookies.columns else np.zeros(len(rookies), dtype=bool)
    )
    out["identity_status"] = np.where(unresolved, "unresolved", "resolved")
    age_missing = pd.to_numeric(rookies["age_at_draft"], errors="coerce").isna().to_numpy()
    out["coverage_status"] = np.where(age_missing, "scored_age_imputed", "scored")
    pred = pred.reset_index(drop=True).drop(columns=["gsis_id"])
    pred.loc[unresolved, :] = np.nan
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
    trend: bool = False,
) -> pd.DataFrame:
    """90% intervals from refitting on player-resampled training sets.

    Parameter uncertainty of the fit conditional on this model form (including whether the
    class-year trend term is in it) and this training window — not outcome spread, and not
    model or season uncertainty.
    """
    rng = np.random.default_rng(seed)
    draws: dict[str, list[np.ndarray]] = {}
    for _ in range(n_boot):
        sample = train.iloc[rng.integers(0, len(train), len(train))]
        m = RookieCapitalModel(horizons=horizons, trend=trend).fit(sample)
        p = m.predict(rookies)
        for col in p.columns:
            if col != "gsis_id":
                draws.setdefault(col, []).append(p[col].to_numpy())
    columns = {"gsis_id": rookies["gsis_id"].to_numpy()}
    for col, arrays in draws.items():
        stack = np.vstack(arrays)
        columns[f"{col}_lo90"] = np.nanpercentile(stack, 5, axis=0)
        columns[f"{col}_hi90"] = np.nanpercentile(stack, 95, axis=0)
    out = pd.DataFrame(columns)
    out.attrs["n_boot_effective"] = len(next(iter(draws.values()))) if draws else 0
    return out
