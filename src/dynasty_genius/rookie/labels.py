"""Outcome labels for a draft prospect at fixed horizons, with an information cutoff.

The two hazards this module exists to avoid, both found on 2026-09-05:

1. **A washout is an outcome, not missing data.** A prospect with zero NFL games has no row
   in any per-season table. An inner join, or the inherited ``censored_incomplete_arc``
   flag, deletes him — and a model fitted on the survivors returns P(qualifies) ≈ 1.
   Labels here are built FROM THE COHORT, looking the panel up by key, so a prospect with
   no panel row is labelled 0 at every observable horizon.

2. **A label that needs a season not yet played is missing, never zero.** "Ever qualifies"
   gave a 2015 pick eleven seasons to do it and a 2020 pick six. Here the window is fixed
   (seasons c .. c+h-1 for draft class c) and the label is NaN whenever the window ends
   after ``last_completed_season``. At forecast year T that argument is T-1.

The bar is the tie-robust N-th largest, not ``rank == N``: with method="min" a tie at N-1
skips rank N and the lookup silently returns nothing (the DG-164 WR-2024 defect, 284
rows gone with no error).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

__all__ = [
    "AVAILABILITY_BAR",
    "horizon_labels",
    "played_season_keys",
    "qualifying_season_keys",
    "season_ppg_map",
]

# David's 2026-09-05 availability ruling ("the next who is actually available"), the bar
# the canonical DG-164 cells are cut on (preserved publish_v3.py:4). Passed explicitly
# everywhere so a starter-bar variant (DG-171) is a parameter, not a code change.
AVAILABILITY_BAR: Mapping[str, int] = {"QB": 37, "RB": 45, "WR": 71, "TE": 21}

SeasonKey = tuple[str, int]


def qualifying_season_keys(panel: pd.DataFrame, bar: Mapping[str, int]) -> set[SeasonKey]:
    """(player_id, season) pairs that finished at or above the bar for their position.

    ``panel`` needs ``player_id, position, season, points``. A (season, position) group
    with fewer players than its bar is a broken panel, not an empty result, and raises.
    """
    keys: set[SeasonKey] = set()
    for (season, position), group in panel.groupby(["season", "position"], sort=True):
        if position not in bar:
            continue
        rank_n = bar[position]
        if len(group) < rank_n:
            raise ValueError(
                f"{position} {season}: {len(group)} player-seasons in the panel, "
                f"fewer than the bar rank {rank_n}; the panel is incomplete"
            )
        threshold = group["points"].nlargest(rank_n).iloc[-1]
        qualified = group.loc[group["points"] >= threshold, "player_id"]
        keys.update((str(player_id), int(season)) for player_id in qualified)
    return keys


def played_season_keys(panel: pd.DataFrame) -> set[SeasonKey]:
    """(player_id, season) pairs with at least one regular-season game."""
    played = panel.loc[panel["games"] >= 1, ["player_id", "season"]]
    return {(str(p), int(s)) for p, s in played.itertuples(index=False)}


def season_ppg_map(panel: pd.DataFrame) -> dict[SeasonKey, float]:
    """(player_id, season) -> regular-season PPR points per game with a stat row.

    The LEVEL a qualifier produces, in the same units the panel is cut on. Denominator is
    weeks with a weekly stat row — NOT the served all-games denominator (DG-024); the
    manifest names the difference so a consumer can reconcile rather than absorb it.
    """
    played = panel.loc[panel["games"] >= 1]
    return {
        (str(p), int(s)): float(pts) / float(g)
        for p, s, pts, g in played[["player_id", "season", "points", "games"]].itertuples(index=False)
    }


def horizon_labels(
    cohort: pd.DataFrame,
    *,
    qualifying: set[SeasonKey],
    played: set[SeasonKey],
    horizons: Iterable[int],
    last_completed_season: int,
    season_ppg: Mapping[SeasonKey, float] | None = None,
) -> pd.DataFrame:
    """Attach horizon labels to every cohort row; never drops a prospect.

    For each horizon h the window is draft_season .. draft_season+h-1. Columns added:

    * ``qy_j`` (j = 1..max h): qualified in NFL season j — NaN if season j is not complete.
    * ``ppg_year_j`` (when ``season_ppg`` is given): his rate in season j if he played it,
      NaN otherwise — a rate exists only for a season with games, never as a zero.
    * ``q_h``: any qualifying season in the window; ``n_h``: count of them;
      ``played_h``: any game in the window. All NaN when the window is not complete.

    Float dtype throughout so NaN can be carried; a fitted model reads only notna rows.
    """
    horizons = tuple(sorted(set(int(h) for h in horizons)))
    if not horizons or horizons[0] < 1:
        raise ValueError(f"horizons must be positive integers, got {horizons}")
    out = cohort.reset_index(drop=True).copy()
    ids = out["gsis_id"].astype(str).to_numpy()
    classes = out["draft_season"].astype(int).to_numpy()

    max_h = horizons[-1]
    qualified_by_year = np.full((len(out), max_h), np.nan)
    played_by_year = np.full((len(out), max_h), np.nan)
    for j in range(1, max_h + 1):
        season = classes + (j - 1)
        complete = season <= last_completed_season
        qual = np.array([(pid, int(s)) in qualifying for pid, s in zip(ids, season)], dtype=float)
        play = np.array([(pid, int(s)) in played for pid, s in zip(ids, season)], dtype=float)
        qualified_by_year[complete, j - 1] = qual[complete]
        played_by_year[complete, j - 1] = play[complete]
        out[f"qy_{j}"] = qualified_by_year[:, j - 1]
        if season_ppg is not None:
            rate = np.array([season_ppg.get((pid, int(s)), np.nan) for pid, s in zip(ids, season)], dtype=float)
            out[f"ppg_year_{j}"] = np.where(complete, rate, np.nan)

    for h in horizons:
        window_q = qualified_by_year[:, :h]
        window_p = played_by_year[:, :h]
        observable = ~np.isnan(window_q).any(axis=1)
        q_h = np.where(observable, np.nanmax(np.where(observable[:, None], window_q, 0.0), axis=1), np.nan)
        n_h = np.where(observable, np.nansum(window_q, axis=1), np.nan)
        played_h = np.where(observable, np.nanmax(np.where(observable[:, None], window_p, 0.0), axis=1), np.nan)
        out[f"q_{h}"] = q_h
        out[f"n_{h}"] = n_h
        out[f"played_{h}"] = played_h
    return out
