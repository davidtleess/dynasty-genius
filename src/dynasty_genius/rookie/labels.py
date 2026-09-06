"""Outcome labels for a draft prospect, per NFL season and per horizon, with an information
cutoff — and with "unknown" kept distinct from "zero".

Three hazards this module exists to avoid:

1. **A measured absence is an outcome; a missing record is not.** A prospect whose NFL
   identity is resolved and who has no weekly stat row in season j scored zero fantasy
   points that season — a measured fact — and is labelled 0 / 0 points. A prospect whose
   identity could NOT be resolved (``label_basis == "unresolved"``) carries NaN in every
   label: he is kept in the cohort and counted, never dropped, and never asserted to have
   failed. The round-1 review found the previous build turning ``games = NaN`` into "zero
   games"; ``unresolved_as_zero`` exists only as an explicit sensitivity arm.

2. **A label that needs a season not yet played is missing, never zero.** Season j of
   draft class c is NFL season c + j − 1; it is complete only if ≤ ``last_completed_season``.
   At forecast year T that argument is T − 1.

3. **The bar is the tie-robust N-th largest**, not ``rank == N`` (the DG-164 WR-2024 defect).

"Appear" means at least one weekly stat row in nflverse regular-season player stats. It is
not "dressed" or "took a snap"; a player without a stat row scored zero fantasy points, which
is the fact the labels need. The manifest says so.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

__all__ = [
    "AVAILABILITY_BAR",
    "LABEL_BASIS_UNRESOLVED",
    "horizon_labels",
    "qualifying_season_keys",
    "season_stats_map",
]

# David's 2026-09-05 availability ruling ("the next who is actually available"), the bar
# the canonical DG-164 cells are cut on (preserved publish_v3.py:4). Passed explicitly
# everywhere so a starter-bar variant (DG-171) is a parameter, not a code change.
AVAILABILITY_BAR: Mapping[str, int] = {"QB": 37, "RB": 45, "WR": 71, "TE": 21}

LABEL_BASIS_UNRESOLVED = "unresolved"

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


def season_stats_map(panel: pd.DataFrame) -> dict[SeasonKey, tuple[float, int]]:
    """(player_id, season) -> (regular-season PPR points, games with a weekly stat row).

    Only seasons with at least one stat row are present; absence from the map for a
    resolved identity IS the zero-points, zero-games season.
    """
    played = panel.loc[panel["games"] >= 1]
    return {
        (str(p), int(s)): (float(pts), int(g))
        for p, s, pts, g in played[["player_id", "season", "points", "games"]].itertuples(index=False)
    }


def horizon_labels(
    cohort: pd.DataFrame,
    *,
    qualifying: set[SeasonKey],
    season_stats: Mapping[SeasonKey, tuple[float, int]],
    horizons: Iterable[int],
    last_completed_season: int,
    unresolved_as_zero: bool = False,
) -> pd.DataFrame:
    """Attach per-season and per-horizon labels to every cohort row; never drops a prospect.

    Per NFL season j = 1..max(h) (season c + j − 1 for class c), NaN when not complete:
      ``appear_j``  1 if he has a weekly stat row that season, else 0
      ``points_j``  regular-season PPR points, 0 when he did not appear
      ``games_j``   weeks with a stat row, 0 when he did not appear
      ``ppg_j``     points_j / games_j, NaN when he did not appear (a rate needs games)
      ``qy_j``      1 if he finished at or above the bar that season
    Per horizon h (window seasons 1..h), NaN when the window is not complete:
      ``appear_by_h``  any appearance in the window   ``q_h``  any qualifying season
      ``n_h``          number of qualifying seasons in the window

    Rows whose ``label_basis`` is "unresolved" carry NaN everywhere unless
    ``unresolved_as_zero`` (the sensitivity arm) is set. A cohort without a
    ``label_basis`` column is treated as fully resolved.
    """
    horizons = tuple(sorted(set(int(h) for h in horizons)))
    if not horizons or horizons[0] < 1:
        raise ValueError(f"horizons must be positive integers, got {horizons}")
    out = cohort.reset_index(drop=True).copy()
    ids = out["gsis_id"].astype(str).to_numpy()
    classes = out["draft_season"].astype(int).to_numpy()
    if "label_basis" in out.columns:
        unknown = (out["label_basis"].astype(str) == LABEL_BASIS_UNRESOLVED).to_numpy()
    else:
        unknown = np.zeros(len(out), dtype=bool)
    if unresolved_as_zero:
        unknown = np.zeros(len(out), dtype=bool)

    max_h = horizons[-1]
    appear = np.full((len(out), max_h), np.nan)
    qual = np.full((len(out), max_h), np.nan)
    for j in range(1, max_h + 1):
        season = classes + (j - 1)
        known = (season <= last_completed_season) & ~unknown
        stats = [season_stats.get((pid, int(s))) for pid, s in zip(ids, season)]
        appeared = np.array([st is not None for st in stats], dtype=float)
        points = np.array([st[0] if st is not None else 0.0 for st in stats], dtype=float)
        games = np.array([st[1] if st is not None else 0 for st in stats], dtype=float)
        qualified = np.array([(pid, int(s)) in qualifying for pid, s in zip(ids, season)], dtype=float)
        appear[known, j - 1] = appeared[known]
        qual[known, j - 1] = qualified[known]
        out[f"appear_{j}"] = appear[:, j - 1]
        out[f"points_{j}"] = np.where(known, points, np.nan)
        out[f"games_{j}"] = np.where(known, games, np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[f"ppg_{j}"] = np.where(known & (appeared == 1), points / np.where(games > 0, games, np.nan), np.nan)
        out[f"qy_{j}"] = qual[:, j - 1]

    for h in horizons:
        window_q = qual[:, :h]
        window_a = appear[:, :h]
        observable = ~np.isnan(window_q).any(axis=1)
        safe_q = np.where(observable[:, None], window_q, 0.0)
        safe_a = np.where(observable[:, None], window_a, 0.0)
        out[f"appear_by_{h}"] = np.where(observable, safe_a.max(axis=1), np.nan)
        out[f"q_{h}"] = np.where(observable, safe_q.max(axis=1), np.nan)
        out[f"n_{h}"] = np.where(observable, safe_q.sum(axis=1), np.nan)
    return out
