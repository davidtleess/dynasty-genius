"""DG-177 — the measured-opportunity feature family, built point-in-time.

Production is opportunity times efficiency, and opportunity is the stickier half. The
family this module builds is RAW realized opportunity per game in the feature season —
targets, air yards, carries, pass attempts — read from the ``ff_opportunity`` table in
the nflverse warehouse. They are counts of what happened, with no fitted weights, so a
historical row cannot carry a coefficient that saw later seasons.

**The denominator is the product's, not the source's.** ``games_t`` counts every game
with a stat line (ALL games, regular season and postseason, per DG-024). The source has
a row only for weeks in which the player had an opportunity, so it holds FEWER weeks
than ``games_t`` on about a third of rows and never more (measured 2026-09-06: 1,061 of
3,337 joined rows). A stat-line game with no source row is an OBSERVED zero-opportunity
appearance and divides the total like any other game. A player-season with no source
row at all is UNAVAILABLE — carried as NaN with ``opp_source_available = False`` — and is
never written as zero. (Review round 1, item 2.)

The same table also carries ``total_fantasy_points_exp``: expected points given each
play's context, from a THIRD-PARTY fitted model (nflverse's ffopportunity, documented as
trained on 2006-2020). Those columns are exposed separately under an ``xfp_`` prefix and
named exploratory: a description of past opportunity, not a projection or a price, but
not point-in-time either, and a caller must be able to tell the two apart by name.
"""
from __future__ import annotations

import sqlite3
from typing import Iterable

import numpy as np
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

#: warehouse column -> season total it becomes -> per-product-game rate it becomes
_RAW_SOURCE: dict[str, tuple[str, str]] = {
    "rec_attempt": ("opp_targets", "opp_targets_pg"),
    "rec_air_yards": ("opp_air_yards", "opp_air_yards_pg"),
    "rush_attempt": ("opp_carries", "opp_carries_pg"),
    "pass_attempt": ("opp_pass_attempts", "opp_pass_attempts_pg"),
}
_XFP_SOURCE: dict[str, str] = {
    "total_fantasy_points": "xfp_points",
    "total_fantasy_points_exp": "xfp_expected_points",
}
SEASON_TOTAL_COLUMNS: list[str] = [t for t, _ in _RAW_SOURCE.values()] + list(_XFP_SOURCE.values())
LOADER_COLUMNS: list[str] = ["player_id", "feature_season", "opp_weeks_in_source", *SEASON_TOTAL_COLUMNS]
ATTACHED_COLUMNS: list[str] = [
    "opp_source_available", "opp_weeks_in_source", "opp_zero_opportunity_games",
    *RAW_OPPORTUNITY_FEATURES, *EXPLORATORY_XFP_FEATURES,
]

SOURCE_TABLE = "ff_opportunity"
PRODUCT_GAMES_COLUMN = "games_t"


def load_opportunity_season_features(
    conn: sqlite3.Connection, seasons: Iterable[int]
) -> pd.DataFrame:
    """Season TOTALS per (player_id, feature_season), plus the number of weeks the source
    holds a row for — under that name, because it is not games played.

    Only rows whose ``season`` is in ``seasons`` are read, so a feature season can never
    see a later one. Rows without a player identity are dropped rather than pooled into a
    phantom player. The warehouse stores every column as TEXT; they are coerced here and
    a missing value contributes nothing to a sum.
    """
    seasons = sorted(int(s) for s in seasons)
    if not seasons:
        return pd.DataFrame(columns=LOADER_COLUMNS)
    source_cols = [*_RAW_SOURCE, *_XFP_SOURCE]
    placeholders = ",".join("?" * len(seasons))
    query = (
        f"SELECT season, week, player_id, {', '.join(source_cols)} FROM {SOURCE_TABLE} "
        f"WHERE player_id IS NOT NULL AND player_id != '' AND season IN ({placeholders})"
    )
    raw = pd.read_sql_query(query, conn, params=[str(s) for s in seasons])
    if raw.empty:
        return pd.DataFrame(columns=LOADER_COLUMNS)
    for col in ["season", "week", *source_cols]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw["season"] = raw["season"].astype(int)

    grouped = raw.groupby(["player_id", "season"], sort=True)
    weeks = grouped["week"].nunique().rename("opp_weeks_in_source")
    sums = grouped[source_cols].sum()
    out = pd.concat([weeks, sums], axis=1).reset_index().rename(columns={"season": "feature_season"})
    out = out.rename(columns={src: total for src, (total, _) in _RAW_SOURCE.items()})
    out = out.rename(columns=_XFP_SOURCE)
    out = out[LOADER_COLUMNS].sort_values(["player_id", "feature_season"]).reset_index(drop=True)
    out["feature_season"] = out["feature_season"].astype(int)
    out["opp_weeks_in_source"] = out["opp_weeks_in_source"].astype(int)
    return out


def attach_opportunity_rates(training: pd.DataFrame, opportunity: pd.DataFrame) -> pd.DataFrame:
    """Join the season totals onto training rows and express them per PRODUCT game.

    Rates divide by ``games_t`` (all games with a stat line). Source weeks missing from
    a joined season are observed zero-opportunity games and are counted in the
    denominator, never dropped. A season absent from the source is unavailable: rates
    are NaN and ``opp_source_available`` is False. No training row is dropped. A source
    holding MORE weeks than the product's game count would mean the two disagree about
    what a game is, and is refused rather than silently divided.
    """
    if PRODUCT_GAMES_COLUMN not in training.columns:
        raise ValueError(f"training frame lacks {PRODUCT_GAMES_COLUMN!r}; rates need the product's game count")
    merged = training.merge(
        opportunity[LOADER_COLUMNS], on=["player_id", "feature_season"], how="left", validate="m:1"
    )
    if len(merged) != len(training):
        raise ValueError(f"opportunity join changed the row count: {len(training)} -> {len(merged)}")

    available = merged["opp_weeks_in_source"].notna()
    games = merged[PRODUCT_GAMES_COLUMN].astype(float)
    over = available & (merged["opp_weeks_in_source"] > games)
    if over.any():
        bad = merged.loc[over, ["player_id", "feature_season", "opp_weeks_in_source", PRODUCT_GAMES_COLUMN]]
        raise ValueError(
            "the opportunity source holds more weeks than the product's game count for "
            f"{int(over.sum())} rows; the two disagree about what a game is:\n{bad.head(10)}"
        )
    denominator = games.where(available & (games > 0))
    merged["opp_source_available"] = available.astype(bool)
    merged["opp_zero_opportunity_games"] = (games - merged["opp_weeks_in_source"]).where(available)
    for _, (total, rate) in _RAW_SOURCE.items():
        merged[rate] = merged[total] / denominator
    merged["xfp_exp_ppg"] = merged["xfp_expected_points"] / denominator
    merged["xfp_ppg_over_exp"] = (merged["xfp_points"] - merged["xfp_expected_points"]) / denominator
    for col in ATTACHED_COLUMNS[2:]:
        merged[col] = merged[col].astype(float).replace([np.inf, -np.inf], np.nan)
    return merged.drop(columns=SEASON_TOTAL_COLUMNS)


def denominator_facts(attached: pd.DataFrame) -> dict[str, int]:
    """What the denominator did, for the artifact: how many rows joined, how many had
    fewer source weeks than product games, and how many zero-opportunity games were
    counted rather than dropped."""
    joined = attached["opp_source_available"].astype(bool)
    zero_games = attached.loc[joined, "opp_zero_opportunity_games"]
    return {
        "rows": int(len(attached)),
        "rows_joined": int(joined.sum()),
        "rows_unavailable": int((~joined).sum()),
        "rows_with_zero_opportunity_games": int((zero_games > 0).sum()),
        "zero_opportunity_games_counted": int(zero_games.sum()),
        "denominator": f"{PRODUCT_GAMES_COLUMN} (all games with a stat line, DG-024)",
    }


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
