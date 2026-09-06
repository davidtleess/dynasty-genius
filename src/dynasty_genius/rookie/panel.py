"""The player-season panel the labels are cut on: regular season, PPR, 1999 onward.

Same construction as the canonical DG-164 cells (preserved ``panel.py``): weekly nflverse
player stats, ``season_type == "REG"``, QB/RB/WR/TE, summed to player-season points with a
game count. Regular season only because fantasy leagues play the regular season; this is a
different quantity from Engine B's ``ppg_t`` (all games, DG-024), and deliberately so.

``games`` counts weekly stat rows, i.e. weeks the player recorded a stat line. A player
who dressed without touching the ball is absent from that count; "played" here means
"appears in the weekly stats", and the manifest says so.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from src.dynasty_genius.rookie.cohort import SKILL_POSITIONS

__all__ = ["PANEL_COLUMNS", "build_panel", "load_panel"]

PANEL_COLUMNS: tuple[str, ...] = ("player_id", "position", "season", "points", "games")


def build_panel(seasons: Iterable[int]) -> pd.DataFrame:
    """Network read of nflverse weekly stats, reduced to the panel columns."""
    import nflreadpy as nfl  # lazy: tests never touch the network

    seasons = sorted(set(int(s) for s in seasons))
    weekly = nfl.load_player_stats(seasons).to_pandas()
    reg = weekly.loc[(weekly["season_type"] == "REG") & weekly["position"].isin(SKILL_POSITIONS)]
    panel = (
        reg.groupby(["player_id", "position", "season"], as_index=False)
        .agg(points=("fantasy_points_ppr", "sum"), games=("fantasy_points_ppr", "size"))
    )
    panel["player_id"] = panel["player_id"].astype(str)
    panel["season"] = panel["season"].astype(int)
    return panel[list(PANEL_COLUMNS)]


def load_panel(path: Path | str) -> pd.DataFrame:
    """Read a saved panel (parquet); accepts the DG-164 panel's wider column set."""
    frame = pd.read_parquet(path)
    missing = [c for c in PANEL_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"panel at {path} lacks columns {missing}")
    frame = frame[list(PANEL_COLUMNS)].copy()
    frame["player_id"] = frame["player_id"].astype(str)
    frame["season"] = frame["season"].astype(int)
    return frame
