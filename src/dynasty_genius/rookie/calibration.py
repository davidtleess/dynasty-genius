"""The bounded recent-era QB / first-round calibration assessment (round-2 review, item 3).

Separates, per position × draft band × era × season, the APPEARANCE error (mean predicted
probability minus realised rate) from the CONDITIONAL POINTS error among appearers (mean
E[points | appears] minus realised points) and the unconditional points error, each with a
row-resampled 90% bootstrap interval and its sample size. This is an assessment, not a
correction: no offset is applied anywhere. Whether any recalibration enters the forecast is
decided only by the inner-window policy in evaluate.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["calibration_assessment", "render_assessment_markdown"]

ERAS = {"2005-15": (2005, 2015), "2016-25": (2016, 2025)}


def _ci(values: np.ndarray, n_boot: int, rng: np.random.Generator) -> list[float]:
    values = values[~np.isnan(values)]
    if len(values) < 2:
        return [float("nan"), float("nan")]
    means = [float(np.mean(values[rng.integers(0, len(values), len(values))])) for _ in range(n_boot)]
    lo, hi = np.percentile(means, [5, 95])
    return [float(lo), float(hi)]


def _cell(g: pd.DataFrame, j: int, n_boot: int, rng: np.random.Generator) -> dict | None:
    g = g.loc[g[f"appear_{j}"].notna()]
    if g.empty:
        return None
    appear_err = (g[f"p_appear_year{j}"] - g[f"appear_{j}"]).to_numpy(dtype=float)
    uncond_err = (g[f"e_points_year{j}"] - g[f"points_{j}"]).to_numpy(dtype=float)
    a = g.loc[g[f"appear_{j}"] == 1]
    cond_err = (a[f"e_points_year{j}_given_appear"] - a[f"points_{j}"]).to_numpy(dtype=float)
    out = {
        "n": int(len(g)),
        "appearance_rate": float(g[f"appear_{j}"].mean()),
        "appearance_bias": float(np.mean(appear_err)),
        "appearance_bias_ci90": _ci(appear_err, n_boot, rng),
        "n_appearers": int(len(a)),
        "conditional_points_bias": float(np.mean(cond_err)) if len(a) else float("nan"),
        "conditional_points_bias_ci90": _ci(cond_err, n_boot, rng),
        "unconditional_points_bias": float(np.mean(uncond_err)),
        "unconditional_points_bias_ci90": _ci(uncond_err, n_boot, rng),
    }
    if f"qy_{j}" in g and f"p_qual_year{j}" in g:
        qual_err = (g[f"p_qual_year{j}"] - g[f"qy_{j}"]).to_numpy(dtype=float)
        out["qualification_bias"] = float(np.nanmean(qual_err))
        out["qualification_bias_ci90"] = _ci(qual_err, n_boot, rng)
    return out


def calibration_assessment(predictions: pd.DataFrame, *, seasons=(1, 2), n_boot: int = 1000, seed: int = 20260906) -> dict:
    rng = np.random.default_rng(seed)
    frame = predictions.copy()
    frame["_band"] = np.where(frame["round"].astype(int) == 1, "R1", "R2+")
    frame["_era"] = None
    for name, (lo, hi) in ERAS.items():
        frame.loc[frame["forecast_year"].between(lo, hi), "_era"] = name
    frame = frame.loc[frame["_era"].notna()]
    cells: dict = {}
    for pos, gp in frame.groupby("position"):
        cells[pos] = {}
        for band in ("R1", "R2+", "all"):
            gb = gp if band == "all" else gp.loc[gp["_band"] == band]
            cells[pos][band] = {}
            for era in ERAS:
                ge = gb.loc[gb["_era"] == era]
                cells[pos][band][era] = {}
                for j in seasons:
                    cell = _cell(ge, j, n_boot, rng)
                    if cell is not None:
                        cells[pos][band][era][str(j)] = cell
    return {"eras": {k: list(v) for k, v in ERAS.items()}, "seasons": list(seasons), "n_boot": n_boot,
            "reading": ("bias = predicted − realised; appearance error and conditional-points error are separate quantities "
                        "with separate intervals; nothing here is applied as a correction"),
            "cells": cells}


def _f(x, nd=1):
    try:
        if x != x:
            return "—"
    except TypeError:
        return "—"
    if isinstance(x, (list, tuple)):
        return "(" + ", ".join(_f(v, nd) for v in x) + ")"
    return f"{x:.{nd}f}"


def render_assessment_markdown(assessment: dict) -> str:
    lines = ["# Recent-era QB / first-round calibration assessment", "",
             "bias = predicted − realised. Appearance error (probability points) and conditional points error",
             "(season points among appearers) are separate; intervals are row-resampled 90% bootstraps. Nothing",
             "here is applied as a correction.", ""]
    for pos, bands in assessment["cells"].items():
        lines += [f"## {pos}", "",
                  "| band | era | season | n | appear rate | appearance bias (90%) | n appearers | conditional points bias (90%) | unconditional points bias (90%) |",
                  "|---|---|---|---:|---:|---|---:|---|---|"]
        for band, eras in bands.items():
            for era, js in eras.items():
                for j, c in js.items():
                    lines.append(f"| {band} | {era} | {j} | {c['n']} | {_f(c['appearance_rate'], 2)} | {_f(c['appearance_bias'], 3)} {_f(c['appearance_bias_ci90'], 3)} | "
                                 f"{c['n_appearers']} | {_f(c['conditional_points_bias'])} {_f(c['conditional_points_bias_ci90'])} | "
                                 f"{_f(c['unconditional_points_bias'])} {_f(c['unconditional_points_bias_ci90'])} |")
        lines.append("")
    return "\n".join(lines) + "\n"
