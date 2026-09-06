"""The FULL nflverse weekly player-stats source, captured once and measured before any filter.

Source: the nflverse-data GitHub release ``stats_player`` — one parquet per season,
``stats_player_week_<season>.parquet`` — the same files ``nflreadpy.load_player_stats``
reads (its memory cache is not touched; nothing is written under the shared cache). Every
column is retained, including every scoring component, so a later common outcome artifact
(DG-179) can attribute points fully instead of trusting a saved total.

Coverage is measured on the raw frame: rows, distinct players, weeks present, positions —
and rows WITHOUT a player id (the source carries one placeholder row per season-week and,
in some seasons, unattributed stat lines with points). Those rows are counted and kept; a
consumer decides them explicitly. Missing values stay missing.
"""
from __future__ import annotations

import pandas as pd

__all__ = ["RELEASE", "coverage_report", "release_url", "schema_report"]

RELEASE = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/"


def release_url(season: int) -> str:
    return f"{RELEASE}stats_player_week_{int(season)}.parquet"


def coverage_report(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per (season, season_type), measured on the raw rows."""
    rows = []
    for (season, stype), g in frame.groupby(["season", "season_type"], dropna=False, sort=True):
        weeks = sorted(int(w) for w in g["week"].dropna().unique())
        missing = g["player_id"].isna() | (g["player_id"].astype(str).str.strip() == "")
        pts = pd.to_numeric(g.get("fantasy_points_ppr"), errors="coerce") if "fantasy_points_ppr" in g else pd.Series(0.0, index=g.index)
        rows.append({
            "season": int(season), "season_type": stype, "rows": int(len(g)),
            "players": int(g.loc[~missing, "player_id"].nunique()),
            "weeks_present": "|".join(str(w) for w in weeks), "week_min": weeks[0] if weeks else None,
            "week_max": weeks[-1] if weeks else None, "n_weeks": len(weeks),
            "positions": "|".join(sorted(str(p) for p in g["position"].dropna().unique())),
            "rows_missing_player_id": int(missing.sum()),
            "rows_missing_player_id_with_points": int((missing & (pts.fillna(0) != 0)).sum()),
            "rows_missing_fantasy_points_ppr": int(pts.isna().sum()) if "fantasy_points_ppr" in g else None,
        })
    return pd.DataFrame(rows)


def schema_report(frame: pd.DataFrame) -> pd.DataFrame:
    """Every column with its dtype, non-null and null counts — nothing filled."""
    return pd.DataFrame({
        "column": list(frame.columns),
        "dtype": [str(frame[c].dtype) for c in frame.columns],
        "non_null": [int(frame[c].notna().sum()) for c in frame.columns],
        "nulls": [int(frame[c].isna().sum()) for c in frame.columns],
    })
