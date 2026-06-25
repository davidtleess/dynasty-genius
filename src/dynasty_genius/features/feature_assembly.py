"""F-feature-refresh T1 — inference-partition-aware feature assembly (C1).

The legacy `assemble_engine_b_dataset` set `training_eligible = feature_season < 2024`
(hardcoded) and then dropped EVERY row with a null outcome — so the latest completed
season (no T+1/T+2 outcome yet) was dropped before it could be scored as an inference
partition, which is the root cause of flat model vintages.

This module derives the outcome + training-eligibility from a computed
inference-season rule and **preserves the intended inference-season rows**
(`training_eligible=False`, null outcome allowed), while training rows still require a
complete outcome. It derives features ONLY — it never touches model weights.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

OUTCOME_COLUMN = "avg_ppg_t1_t2"


def inference_season_rule(seasons_window: list[int]) -> int:
    """The intended inference season — the latest (max) season in the window.

    Computed, never hardcoded: with a window ending in 2025 the inference season is
    2025 (the freshest completed season, predicting 2026–2027). Training-eligibility
    derives from this (a season needs a complete 2-year outcome window to train).
    """
    return int(max(seasons_window))


def assemble_feature_candidate(
    *, seasons_window: list[int], read_fns: dict[str, Any]
) -> pd.DataFrame:
    """Derive the per-player-season feature candidate from source frames.

    Preserves intended-inference-season rows with `training_eligible=False` and a null
    outcome; drops ONLY training-eligible rows that lack a complete outcome.
    """
    stats = read_fns["player_stats"].copy()
    grp = stats.groupby(["player_id", "season"], as_index=False).agg(
        ppg_t=("fantasy_points_ppr", "mean"),
        games_t=("week", "nunique"),
        position=("position", "first"),
        team=("team", "first"),
    )
    grp = grp.rename(columns={"season": "feature_season"})

    # T1 SEAM: outcome + honest inference partition only; feature *values* that need the
    # full nflreadpy engineering (snap share, routes, QB efficiency, aging, …) stay null
    # until T1b. The result is conformed to the exact Engine-B schema (shape, not values).
    partitioned = apply_inference_partition(grp, seasons_window=seasons_window)
    return _conform_to_engine_b_schema(partitioned)


def apply_inference_partition(
    df: pd.DataFrame, *, seasons_window: list[int]
) -> pd.DataFrame:
    """Compute the 2-year outcome + training-eligibility and select the honest partition.

    Shared by `assemble_feature_candidate` (the refresh seam) and
    `scripts/assemble_engine_b_dataset.py`. Training rows need a COMPLETE 2-year outcome
    window; the single latest (inference) season is preserved with a null outcome; an
    in-between season lacking a complete window is dropped. Replaces the legacy hardcoded
    `feature_season < 2024` + unconditional outcome drop. Operates on a frame carrying
    `player_id`/`feature_season`/`ppg_t`/`games_t` (plus any feature columns, untouched).
    """
    inference_season = inference_season_rule(seasons_window)
    outcomes = df[["player_id", "feature_season", "ppg_t", "games_t"]]
    o_t1 = outcomes.rename(
        columns={"feature_season": "join_season", "ppg_t": "ppg_t1", "games_t": "games_t1"}
    )
    o_t1 = o_t1.assign(join_season=o_t1["join_season"] - 1)
    o_t2 = outcomes.rename(
        columns={"feature_season": "join_season", "ppg_t": "ppg_t2", "games_t": "games_t2"}
    )
    o_t2 = o_t2.assign(join_season=o_t2["join_season"] - 2)
    merged = df.merge(
        o_t1, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left"
    ).drop(columns="join_season")
    merged = merged.merge(
        o_t2, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left"
    ).drop(columns="join_season")

    def _calc_avg(row: pd.Series) -> float:
        pts: list[float] = []
        if pd.notna(row.get("games_t1")) and row["games_t1"] > 0:
            pts.append(row["ppg_t1"])
        if pd.notna(row.get("games_t2")) and row["games_t2"] > 0:
            pts.append(row["ppg_t2"])
        return float(np.mean(pts)) if pts else np.nan

    merged[OUTCOME_COLUMN] = merged.apply(_calc_avg, axis=1)
    merged = merged.drop(
        columns=[c for c in ("ppg_t1", "ppg_t2", "games_t1", "games_t2") if c in merged.columns]
    )

    # Training-eligible = complete 2-year window (feature_season + 2 <= latest season).
    merged["training_eligible"] = merged["feature_season"] < (inference_season - 1)
    keep = (merged["training_eligible"] & merged[OUTCOME_COLUMN].notna()) | (
        merged["feature_season"] == inference_season
    )
    return merged[keep].reset_index(drop=True)


def _conform_to_engine_b_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Select EXACTLY the Engine-B output columns in order (NaN for any not computed).

    Drops every helper/intermediate column and fixes column order. Lazily imports the
    canonical column list to avoid an import cycle with the assembler script.
    """
    from scripts.assemble_engine_b_dataset import (  # noqa: E402  (lazy: avoid import cycle)
        ENGINE_B_OUTPUT_COLUMNS,
    )

    out = df.copy()
    for col in ENGINE_B_OUTPUT_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan
    return out[list(ENGINE_B_OUTPUT_COLUMNS)].reset_index(drop=True)
