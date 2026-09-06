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
#: Regular-season weeks the NFL played; a source season with fewer REG weeks is incomplete.
REG_WEEKS_EXPECTED = {season: (18 if season >= 2021 else 17) for season in range(1999, 2101)}
MIN_PLAYERS_PER_SEASON = 1000


class SourceIncompleteError(ValueError):
    """The weekly source cannot support "no row means no game": a season, week, scoring
    value or identity is missing, or rows are duplicated. Refuse; never treat as zero."""


def validate_weekly_source(
    weekly: pd.DataFrame,
    *,
    seasons: Iterable[int],
    min_players_per_season: int = MIN_PLAYERS_PER_SEASON,
) -> dict:
    """Prove the properties that make a MISSING player-season an OBSERVED absence.

    1. every requested season is present with its full regular-season week range and a
       credible number of players (a partial pull is not a season);
    2. (player_id, season, week, season_type) is unique (a duplicated week would double a
       season's games and points);
    3. no scoring value and no identity is missing (a missing value is unknown, not 0).
    Returns the facts that were checked, for the manifest.
    """
    seasons = sorted(int(s) for s in seasons)
    required = ["player_id", "season", "week", "season_type", SCORING_COLUMN]
    missing_cols = [c for c in required if c not in weekly.columns]
    if missing_cols:
        raise SourceIncompleteError(f"weekly source lacks columns {missing_cols}")
    problems: list[str] = []
    facts: dict = {"seasons": {}, "scope_checked": "REG"}
    missing_id = int(weekly["player_id"].isna().sum() + (weekly["player_id"].astype(str).str.strip() == "").sum())
    if missing_id:
        problems.append(f"{missing_id} rows have a missing player_id")
    points = pd.to_numeric(weekly[SCORING_COLUMN], errors="coerce")
    missing_points = int(points.isna().sum())
    if missing_points:
        problems.append(f"{missing_points} rows have a missing {SCORING_COLUMN} value")
    dup = int(weekly.duplicated(subset=["player_id", "season", "week", "season_type"]).sum())
    if dup:
        problems.append(f"{dup} duplicate (player, season, week, season_type) rows")
    reg = weekly[weekly["season_type"] == "REG"]
    for season in seasons:
        rows = reg[reg["season"].astype(int) == season]
        expected_weeks = REG_WEEKS_EXPECTED.get(season, 18)
        weeks = int(rows["week"].nunique()) if len(rows) else 0
        players = int(rows["player_id"].nunique()) if len(rows) else 0
        facts["seasons"][str(season)] = {"rows": int(len(rows)), "reg_weeks": weeks,
                                         "reg_weeks_expected": expected_weeks, "players": players}
        if len(rows) == 0:
            problems.append(f"season {season} is absent from the source")
            continue
        if weeks < expected_weeks:
            problems.append(f"season {season} has {weeks} regular-season weeks, expected {expected_weeks}")
        if players < min_players_per_season:
            problems.append(f"season {season} has {players} players, below the floor of {min_players_per_season}")
    facts.update({"duplicate_rows": dup, "missing_points": missing_points, "missing_player_id": missing_id,
                  "min_players_per_season": int(min_players_per_season), "validated": not problems})
    if problems:
        raise SourceIncompleteError("weekly source cannot support observed absence: " + "; ".join(problems))
    return facts


def season_outcomes(
    weekly: pd.DataFrame, scope: str = "REG", *, validation: dict | None = None
) -> pd.DataFrame:
    """One row per (player_id, season): stat-row games and PPR points in ``scope``.

    Requires the facts from ``validate_weekly_source``: without them a missing
    player-season cannot be read as an observed absence, so this refuses to proceed.
    """
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}; expected one of {sorted(SCOPES)}")
    if not validation or not validation.get("validated"):
        raise SourceIncompleteError(
            "season_outcomes needs a validated source: call validate_weekly_source first"
        )
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
                      "exposure": EXPOSURE, "source_validation": dict(validation)})
    return out


def annual_targets(
    training: pd.DataFrame,
    outcomes: pd.DataFrame,
    *,
    horizons: Iterable[int] = (1, 2),
    last_complete_season: int,
) -> pd.DataFrame:
    """Attach per-season labels for each horizon to every training row (none dropped)."""
    validation = outcomes.attrs.get("source_validation")
    if not validation or not validation.get("validated"):
        raise SourceIncompleteError(
            "annual_targets needs outcomes built from a validated source; a missing row is "
            "an observed absence only when the source is known to be complete"
        )
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
        "source_validation": dict(validation),
    })
    return out
