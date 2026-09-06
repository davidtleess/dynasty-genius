"""DG-177 round 1, item 3 — season-by-season outcomes on explicit events.

The served Engine B target is a two-season average on the event "posted a qualifying
season in t+1 OR t+2". A ranking that discounts by year needs one season at a time,
each on one event, with exposure carried beside the points. This module builds that
label from nflverse weekly player stats:

  season j after feature season t  →  appeared_year{j}  (>= 1 regular-season stat-row week)
                                      games_year{j}     (stat-row weeks)
                                      points_year{j}    (sum of fantasy_points_ppr)
                                      ppg_year{j}       (points / games; undefined at 0 games)
                                      censored_year{j}  (season not yet complete)

Three things it refuses to confuse:
  * a ZERO-appearance season is an observation — 0 games, 0 points, appeared False;
  * an UNFINISHED season is censored — NaN with the flag set, never 0;
  * an identity the source never saw is unresolved — NaN with ``identity_status`` set.

Scope is explicit. ``REG`` is the ranking lane's typed target (agreed with DG-178 on
2026-09-06). ``ALL`` (regular + postseason) is the product's own basis for its served
feature ``ppg_t`` under DG-024 and is kept available under its own name; nothing here
changes that ruling or the served target.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

SCORING_COLUMN = "fantasy_points_ppr"
SCOPES: dict[str, tuple[str, ...]] = {"REG": ("REG",), "ALL": ("REG", "POST")}
EVENT = "appeared: >= 1 stat-row game in the season"
EXPOSURE = "games: weeks with a weekly stat row in scope"


def season_outcomes(weekly: pd.DataFrame, scope: str = "REG") -> pd.DataFrame:
    """One row per (player_id, season): stat-row games and PPR points in ``scope``."""
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}; expected one of {sorted(SCOPES)}")
    rows = weekly[weekly["season_type"].isin(SCOPES[scope])]
    if rows.empty:
        out = pd.DataFrame(columns=["player_id", "season", "games", "points"])
    else:
        grouped = rows.groupby(["player_id", "season"], sort=True)
        out = pd.concat(
            [grouped["week"].nunique().rename("games"),
             grouped[SCORING_COLUMN].sum().rename("points")],
            axis=1,
        ).reset_index()
        out["season"] = out["season"].astype(int)
        out["games"] = out["games"].astype(int)
        out["points"] = out["points"].astype(float)
    out.attrs.update({"scope": scope, "season_types": list(SCOPES[scope]), "scoring": SCORING_COLUMN,
                      "exposure": EXPOSURE})
    return out


def annual_targets(
    training: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    horizons: Iterable[int] = (1, 2),
    last_complete_season: int,
) -> pd.DataFrame:
    """Attach per-season labels for each horizon to every training row (none dropped)."""
    horizons = [int(h) for h in horizons]
    out = training[["player_id", "position", "feature_season"]].copy().reset_index(drop=True)
    seen = set(outcomes["player_id"].unique())
    resolved = out["player_id"].isin(seen)
    out["identity_status"] = np.where(resolved, "resolved", "unresolved_in_source")
    lookup = outcomes.set_index(["player_id", "season"])[["games", "points"]]

    for j in horizons:
        season = out["feature_season"].astype(int) + j
        keyed = pd.MultiIndex.from_arrays([out["player_id"], season])
        hit = lookup.reindex(keyed)
        games = hit["games"].to_numpy(dtype=float)
        points = hit["points"].to_numpy(dtype=float)
        censored = (season > int(last_complete_season)).to_numpy()
        observed = resolved.to_numpy() & ~censored
        absent = observed & np.isnan(games)
        games = np.where(absent, 0.0, games)
        points = np.where(absent, 0.0, points)
        games = np.where(observed, games, np.nan)
        points = np.where(observed, points, np.nan)
        appeared = pd.array([None] * len(out), dtype="boolean")
        appeared[observed] = games[observed] >= 1
        with np.errstate(divide="ignore", invalid="ignore"):
            ppg = np.where(games > 0, points / games, np.nan)
        out[f"season_year{j}"] = season.astype(int)
        out[f"appeared_year{j}"] = appeared
        out[f"games_year{j}"] = games
        out[f"points_year{j}"] = points
        out[f"ppg_year{j}"] = ppg
        out[f"censored_year{j}"] = censored

    out.attrs.update({
        "event": EVENT,
        "exposure": EXPOSURE,
        "scope": outcomes.attrs.get("scope"),
        "scoring": outcomes.attrs.get("scoring", SCORING_COLUMN),
        "label_window_seasons": {f"year{j}": j for j in horizons},
        "last_complete_season": int(last_complete_season),
    })
    return out
