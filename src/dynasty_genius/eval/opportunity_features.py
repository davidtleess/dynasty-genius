"""DG-177 — the measured-opportunity feature family, built point-in-time.

Production is opportunity times efficiency, and opportunity is the stickier half. The
family this module builds is RAW realized opportunity per game in the feature season —
targets, air yards, carries, pass attempts — read from the ``ff_opportunity`` table in
the nflverse warehouse. They are counts of what happened, with no fitted weights, so a
historical row cannot carry a coefficient that saw later seasons.

The same table also carries ``total_fantasy_points_exp``: expected points given each
play's context, from a THIRD-PARTY fitted model (nflverse's ffopportunity). Its fit
window is not verifiable from the warehouse, so those columns are exposed separately
under an ``xfp_`` prefix and named exploratory. They are a description of past
opportunity, not a forward projection or a price, but they are not point-in-time
either, and a caller must be able to tell the two apart by name.
"""
from __future__ import annotations

import sqlite3
from typing import Iterable

import pandas as pd

RAW_OPPORTUNITY_FEATURES: list[str] = [
    "opp_targets_pg",
    "opp_air_yards_pg",
    "opp_carries_pg",
    "opp_pass_attempts_pg",
]

EXPLORATORY_XFP_FEATURES: list[str] = [
    "xfp_exp_ppg",
    "xfp_ppg_over_exp",
]

#: warehouse column -> per-game feature it becomes
_RAW_SOURCE: dict[str, str] = {
    "rec_attempt": "opp_targets_pg",
    "rec_air_yards": "opp_air_yards_pg",
    "rush_attempt": "opp_carries_pg",
    "pass_attempt": "opp_pass_attempts_pg",
}
_XFP_SOURCE: tuple[str, str] = ("total_fantasy_points", "total_fantasy_points_exp")

SOURCE_TABLE = "ff_opportunity"


def load_opportunity_season_features(
    conn: sqlite3.Connection, seasons: Iterable[int]
) -> pd.DataFrame:
    """One row per (player_id, feature_season) aggregated over the weeks the player appeared.

    Only rows whose ``season`` is in ``seasons`` are read, so a feature season can never
    see a later one. Rows without a player identity are dropped rather than pooled into a
    phantom player. The warehouse stores every column as TEXT; they are coerced here and
    a missing value contributes nothing to a sum.
    """
    seasons = sorted(int(s) for s in seasons)
    if not seasons:
        return _empty()
    cols = ["season", "week", "player_id", *_RAW_SOURCE, *_XFP_SOURCE]
    placeholders = ",".join("?" * len(seasons))
    query = (
        f"SELECT {', '.join(cols)} FROM {SOURCE_TABLE} "
        f"WHERE player_id IS NOT NULL AND player_id != '' AND season IN ({placeholders})"
    )
    raw = pd.read_sql_query(query, conn, params=[str(s) for s in seasons])
    if raw.empty:
        return _empty()
    for col in ["season", "week", *_RAW_SOURCE, *_XFP_SOURCE]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw["season"] = raw["season"].astype(int)

    grouped = raw.groupby(["player_id", "season"], sort=True)
    games = grouped["week"].nunique().rename("opp_games")
    sums = grouped[[*_RAW_SOURCE, *_XFP_SOURCE]].sum()
    out = pd.concat([games, sums], axis=1).reset_index()
    out = out.rename(columns={"season": "feature_season"})

    for source, feature in _RAW_SOURCE.items():
        out[feature] = out[source] / out["opp_games"]
    actual, expected = _XFP_SOURCE
    out["xfp_exp_ppg"] = out[expected] / out["opp_games"]
    out["xfp_ppg_over_exp"] = (out[actual] - out[expected]) / out["opp_games"]

    keep = ["player_id", "feature_season", "opp_games", *RAW_OPPORTUNITY_FEATURES, *EXPLORATORY_XFP_FEATURES]
    out = out[keep].sort_values(["player_id", "feature_season"]).reset_index(drop=True)
    out["feature_season"] = out["feature_season"].astype(int)
    out["opp_games"] = out["opp_games"].astype(int)
    return out


def join_coverage(training: pd.DataFrame, opportunity: pd.DataFrame) -> dict[str, dict[str, dict[str, int]]]:
    """How many training rows, per position and feature season, found an opportunity row."""
    merged = training[["player_id", "position", "feature_season"]].merge(
        opportunity[["player_id", "feature_season"]].drop_duplicates(),
        on=["player_id", "feature_season"],
        how="left",
        indicator=True,
    )
    merged["joined"] = merged["_merge"] == "both"
    out: dict[str, dict[str, dict[str, int]]] = {}
    for (position, season), part in merged.groupby(["position", "feature_season"], sort=True):
        out.setdefault(str(position), {})[str(int(season))] = {
            "rows": int(len(part)),
            "joined": int(part["joined"].sum()),
        }
    return out


def _empty() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["player_id", "feature_season", "opp_games", *RAW_OPPORTUNITY_FEATURES, *EXPLORATORY_XFP_FEATURES]
    )
