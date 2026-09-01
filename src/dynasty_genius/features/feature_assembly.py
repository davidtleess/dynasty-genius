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
    """Build the genuinely scoreable Engine-B feature candidate from source frames.

    Delegates to `build_engine_b_features` (the full frame-injectable engineering, T1b):
    real feature values + the honest inference partition (intended-inference-season rows
    kept with `training_eligible=False`/null outcome; complete-window training rows;
    in-between seasons dropped), conformed to the exact Engine-B schema.
    """
    return build_engine_b_features(seasons_window=seasons_window, read_fns=read_fns)


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

    def _returned(row: pd.Series) -> bool:
        """Did a qualifying outcome season appear at t+1 or t+2?

        Narrow on purpose. The upstream assembler drops seasons under
        MIN_GAMES_THRESHOLD, so a missing outcome row means "did not post a QUALIFYING
        season", which is a weaker claim than "took zero snaps". Anything downstream that
        models attrition must read this as the pipeline's own qualification event, not as
        a football fact.
        """
        return bool(
            (pd.notna(row.get("games_t1")) and row["games_t1"] > 0)
            or (pd.notna(row.get("games_t2")) and row["games_t2"] > 0)
        )

    merged[OUTCOME_COLUMN] = merged.apply(_calc_avg, axis=1)
    merged["outcome_returned"] = merged.apply(_returned, axis=1).astype("boolean")
    merged = merged.drop(
        columns=[c for c in ("ppg_t1", "ppg_t2", "games_t1", "games_t2") if c in merged.columns]
    )

    # A complete 2-year outcome window (feature_season + 2 <= latest season). Outside it
    # the player's return is UNOBSERVED rather than negative, so the availability label is
    # nulled there; otherwise an availability model would read every currently-active
    # player as having washed out.
    window_complete = merged["feature_season"] < (inference_season - 1)
    merged.loc[~window_complete, "outcome_returned"] = pd.NA

    # `training_eligible` keeps the meaning every consumer already relies on: this row can
    # train the PRODUCTION regression. Consumers select on it and then read OUTCOME_COLUMN
    # straight into a Ridge fit (train_engine_b.py:212,294,351,371;
    # backtest_harness._build_fold_data), so a row with no observed production must not
    # qualify — admitting one feeds NaN targets into a points model, which is a different
    # bug from the one this fixes.
    merged["training_eligible"] = window_complete & merged[OUTCOME_COLUMN].notna()

    # ...but the row itself SURVIVES, which is the actual fix. A player who never returned
    # is an OBSERVATION, not a missing row. The pre-DG mask dropped him entirely, deleting
    # 638 of 2,880 complete-window player-seasons, 9.3x concentrated in the lowest
    # snap-share decile — which is what flattened the learned age curve and left the model
    # with almost no examples of the low-opportunity population it is asked to rank.
    # He is kept with outcome_returned=False and OUTCOME_COLUMN=NaN, because what was
    # observed is the absence of an opportunity, never a productive capacity of zero.
    # That is the hurdle split: P(plays) is estimable from every complete-window row,
    # E[points | plays] only from those who played.
    keep = window_complete | (merged["feature_season"] == inference_season)
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


def build_engine_b_features(
    *, read_fns: dict[str, Any], seasons_window: list[int]
) -> pd.DataFrame:
    """Full frame-injectable Engine-B feature engineering (T1b).

    Same logic as scripts/assemble_engine_b_dataset.py main() steps 1–12, reading inputs
    from ``read_fns`` instead of nflreadpy so it is testable and reusable by the
    F-feature-refresh runner. Derives features ONLY — no model fit, no model-artifact
    write. Returns the candidate conformed to ENGINE_B_OUTPUT_COLUMNS.

    read_fns keys: player_stats (required), rosters, snap_counts, pbp, participation,
    and optionally te_rubric/te_eligible (else the committed TE-rubric files are used).
    """
    from scripts.assemble_engine_b_dataset import (  # noqa: E402  (lazy: avoid import cycle)
        MIN_GAMES_THRESHOLD,
        _to_pandas,
        add_te_role_risk_feature,
        add_te_role_risk_feature_from_files,
        fetch_and_agg_stats,
    )
    from src.dynasty_genius.models.aging_curves import aging_curve_value
    from src.dynasty_genius.models.engine_b_contract import (
        DUAL_THREAT_RUSHING_THRESHOLD,
    )

    # 1. Base stats (injected weekly frame)
    df = fetch_and_agg_stats(seasons_window, weekly=read_fns["player_stats"])
    df = df.rename(columns={"season": "feature_season"})

    # 2. Minimum games filter
    df = df[df["games_t"] >= MIN_GAMES_THRESHOLD].copy()

    # 3. Roster info (age, depth chart)
    rosters_raw = _to_pandas(read_fns["rosters"])
    rosters_agg = rosters_raw.groupby(["gsis_id", "season"]).agg({
        "birth_date": "first",
        "depth_chart_position": lambda x: x.mode().iloc[0] if not x.mode().empty else None,
    }).reset_index()
    rosters_agg["birth_year"] = pd.to_datetime(rosters_agg["birth_date"], errors="coerce").dt.year
    rosters_agg["age"] = rosters_agg["season"] - rosters_agg["birth_year"]
    df = df.merge(
        rosters_agg[["gsis_id", "season", "age", "depth_chart_position"]],
        left_on=["player_id", "feature_season"], right_on=["gsis_id", "season"], how="left",
    ).drop(columns="season")

    # 4. Snap share (joined via the gsis_id ↔ pfr_id crosswalk)
    snaps_raw = _to_pandas(read_fns["snap_counts"])
    snaps_agg = snaps_raw.groupby(["pfr_player_id", "season"])["offense_pct"].mean().reset_index(
        name="snap_share"
    )
    # Season-aware crosswalk: include `season` in the key. A seasonless crosswalk maps a
    # single gsis_id to every pfr_id it was ever paired with (e.g. an upstream stale/wrong
    # pfr_id in one season), so a snap row under the *other* pfr_id is double-attributed and
    # fans out the join (and the later self-joins multiply it). Keying on season confines the
    # mapping to the correct (gsis_id, pfr_id) pair per season.
    crosswalk = (
        rosters_raw[["gsis_id", "pfr_id", "season"]]
        .dropna()
        .drop_duplicates()
        .rename(columns={"pfr_id": "pfr_player_id"})
    )
    snaps_agg = snaps_agg.merge(crosswalk, on=["pfr_player_id", "season"], how="inner")
    # Fail-closed guard: even season-aware, a within-season 1:N collision (one gsis_id mapped
    # to two pfr_ids in the SAME season, both carrying snaps) would still fan out. That is a
    # new upstream data anomaly — surface it loudly rather than silently dropping or averaging
    # conflicting rows.
    if snaps_agg.duplicated(["gsis_id", "season"]).any():
        n_dup = int(snaps_agg.duplicated(["gsis_id", "season"]).sum())
        raise ValueError(
            f"snap-share crosswalk produced {n_dup} duplicate (gsis_id, season) row(s): a "
            "within-season gsis_id->pfr_id 1:N collision. Refusing to fan out or average snaps."
        )
    df = df.merge(
        snaps_agg[["gsis_id", "season", "snap_share"]],
        left_on=["player_id", "feature_season"], right_on=["gsis_id", "season"], how="left",
    ).drop(columns="season")

    # 5. PBP-derived QB efficiency (EPA/CPOE/DAKOTA), masked to QBs
    pbp = _to_pandas(read_fns["pbp"])
    pbp_qbs = pbp[pbp["qb_dropback"] == 1].copy()
    qb_eff = pbp_qbs.groupby(["passer_player_id", "season"]).agg({
        "epa": "mean", "cpoe": "mean", "qb_dropback": "sum", "pass_attempt": "sum",
    }).reset_index()
    qb_eff.columns = [
        "player_id", "feature_season", "epa_per_dropback", "cpoe", "dropback_count", "pass_attempts"
    ]
    qb_eff["dakota"] = (qb_eff["epa_per_dropback"] * 0.7) + ((qb_eff["cpoe"] / 100.0) * 0.3)
    df = df.merge(qb_eff, on=["player_id", "feature_season"], how="left")
    qb_cols = ["epa_per_dropback", "cpoe", "dakota", "dropback_count", "pass_attempts"]
    df.loc[df["position"] != "QB", qb_cols] = np.nan
    qb_partial = (
        (df["position"] == "QB")
        & df["epa_per_dropback"].notna()
        & (df["cpoe"].isna() | df["dakota"].isna())
    )
    df = df[~qb_partial].copy()

    # 6. Route metrics (YPRR/TPRR/route participation) from PBP + participation
    part = _to_pandas(read_fns["participation"])
    pass_plays = pbp[(pbp["pass_attempt"] == 1) | (pbp["qb_dropback"] == 1)].copy()
    pass_plays = pass_plays.merge(
        part[["nflverse_game_id", "play_id", "offense_players"]],
        left_on=["game_id", "play_id"], right_on=["nflverse_game_id", "play_id"], how="inner",
    )
    team_pass_att = pass_plays.groupby(["posteam", "season"]).size().reset_index(
        name="team_pass_attempts_routes"
    )
    team_pass_att.rename(columns={"posteam": "team"}, inplace=True)
    pass_plays["offense_players"] = pass_plays["offense_players"].str.split(";")
    exploded = pass_plays.explode("offense_players")
    exploded = exploded.rename(columns={"offense_players": "player_id", "season": "feature_season"})
    routes = exploded.groupby(["player_id", "feature_season"]).size().reset_index(name="routes_run")
    df = df.merge(routes, on=["player_id", "feature_season"], how="left")
    df = df.merge(
        team_pass_att.rename(columns={"season": "feature_season"}),
        on=["team", "feature_season"], how="left",
    )
    df["route_participation"] = df["routes_run"] / df["team_pass_attempts_routes"].replace(0, np.nan)
    df["yprr"] = df["yards_t"] / df["routes_run"].replace(0, np.nan)
    df["tprr"] = df["targets_t"] / df["routes_run"].replace(0, np.nan)

    # 6b. NFL Next Gen Stats (public aggregates)
    ng_pass = _to_pandas(read_fns.get("nextgen_passing")) if read_fns.get("nextgen_passing") is not None else pd.DataFrame()
    ng_rec = _to_pandas(read_fns.get("nextgen_receiving")) if read_fns.get("nextgen_receiving") is not None else pd.DataFrame()
    ng_rush = _to_pandas(read_fns.get("nextgen_rushing")) if read_fns.get("nextgen_rushing") is not None else pd.DataFrame()

    if not ng_pass.empty:
        ng_pass = ng_pass[(ng_pass["week"] == 0) & (ng_pass["season_type"] == "REG")].copy()
        ng_pass = ng_pass.rename(columns={"player_gsis_id": "player_id", "season": "feature_season"})
        ng_pass = ng_pass.rename(columns={
            "avg_time_to_throw": "ngs_avg_time_to_throw",
            "completion_percentage_above_expectation": "ngs_completion_percentage_above_expectation"
        })
        keep_cols = ["player_id", "feature_season", "ngs_avg_time_to_throw", "ngs_completion_percentage_above_expectation"]
        ng_pass = ng_pass[[c for c in keep_cols if c in ng_pass.columns]]
        df = df.merge(ng_pass, on=["player_id", "feature_season"], how="left")

    if not ng_rec.empty:
        ng_rec = ng_rec[(ng_rec["week"] == 0) & (ng_rec["season_type"] == "REG")].copy()
        ng_rec = ng_rec.rename(columns={"player_gsis_id": "player_id", "season": "feature_season"})
        ng_rec = ng_rec.rename(columns={
            "avg_separation": "ngs_avg_separation",
            "avg_cushion": "ngs_avg_cushion"
        })
        keep_cols = ["player_id", "feature_season", "ngs_avg_separation", "ngs_avg_cushion"]
        ng_rec = ng_rec[[c for c in keep_cols if c in ng_rec.columns]]
        df = df.merge(ng_rec, on=["player_id", "feature_season"], how="left")

    if not ng_rush.empty:
        ng_rush = ng_rush[(ng_rush["week"] == 0) & (ng_rush["season_type"] == "REG")].copy()
        ng_rush = ng_rush.rename(columns={"player_gsis_id": "player_id", "season": "feature_season"})
        ng_rush = ng_rush.rename(columns={
            "rush_yards_over_expected_per_att": "ngs_rush_yards_over_expected_per_att",
            "percent_attempts_gte_eight_defenders": "ngs_percent_attempts_gte_eight_defenders"
        })
        keep_cols = ["player_id", "feature_season", "ngs_rush_yards_over_expected_per_att", "ngs_percent_attempts_gte_eight_defenders"]
        ng_rush = ng_rush[[c for c in keep_cols if c in ng_rush.columns]]
        df = df.merge(ng_rush, on=["player_id", "feature_season"], how="left")

    # 7. Multi-year trends + availability flags
    #
    # Renames here are BY NAME. The previous positional form (`df_t1.columns = [...]`)
    # relabels by ORDER, so a selection and a name list that disagree silently write one
    # feature's values into another column: adding `games_t` to `trend_base` without
    # matching the list puts a game count into `ppg_t_minus_1` and a PPG into
    # `snap_share_t_minus_1`. Both are REQUIRED Engine B features for all four positions
    # (engine_b_contract.py ENGINE_B_BASE_FEATURES), so every published value would move
    # while the name-only guards in scripts/assemble_engine_b_dataset.py:269-275 still
    # passed. `.rename` cannot express that mistake; the positional form invited it.
    #
    # ⚠ `games_t_minus_1` / `games_t_minus_2` are LEFT-CENSORED AT `MIN_GAMES_THRESHOLD`
    # (4). Step 2 above drops player-seasons below it BEFORE this join, so a player who
    # played 1-3 games last season is written NaN with `_available = False` — byte-identical
    # to a true rookie. These lags separate a FULL prior season from NO prior season; they
    # cannot separate a SHORT prior season from none. The same censoring already applies to
    # the ppg and snap_share lags. A consumer that reads absence as "no NFL history" will be
    # wrong about exactly the injured players it most needs to reason about.
    trend_base = df[
        ["player_id", "feature_season", "ppg_t", "snap_share", "games_t"]
    ].drop_duplicates(subset=["player_id", "feature_season"])
    df_t1 = trend_base.copy()
    df_t1["feature_season"] = df_t1["feature_season"] + 1
    df_t1 = df_t1.rename(columns={
        "ppg_t": "ppg_t_minus_1",
        "snap_share": "snap_share_t_minus_1",
        "games_t": "games_t_minus_1",
    })
    df_t2 = trend_base[["player_id", "feature_season", "ppg_t", "games_t"]].copy()
    df_t2["feature_season"] = df_t2["feature_season"] + 2
    df_t2 = df_t2.rename(columns={
        "ppg_t": "ppg_t_minus_2",
        "games_t": "games_t_minus_2",
    })
    df = df.merge(df_t1, on=["player_id", "feature_season"], how="left")
    df = df.merge(df_t2, on=["player_id", "feature_season"], how="left")
    df["ppg_t_minus_1_available"] = df["ppg_t_minus_1"].notna()
    df["ppg_t_minus_2_available"] = df["ppg_t_minus_2"].notna()
    df["snap_share_t_minus_1_available"] = df["snap_share_t_minus_1"].notna()
    df["games_t_minus_1_available"] = df["games_t_minus_1"].notna()
    df["games_t_minus_2_available"] = df["games_t_minus_2"].notna()

    # 8. QB archetype (dual-threat from multi-year rushing)
    rushing_hist = df[["player_id", "feature_season", "rushing_yards_t"]].copy()
    r_t1 = rushing_hist.rename(
        columns={"feature_season": "join_season", "rushing_yards_t": "rushing_t_minus_1"}
    )
    r_t1["join_season"] = r_t1["join_season"] + 1
    r_t2 = rushing_hist.rename(
        columns={"feature_season": "join_season", "rushing_yards_t": "rushing_t_minus_2"}
    )
    r_t2["join_season"] = r_t2["join_season"] + 2
    df = df.merge(
        r_t1, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left"
    ).drop(columns="join_season")
    df = df.merge(
        r_t2, left_on=["player_id", "feature_season"], right_on=["player_id", "join_season"], how="left"
    ).drop(columns="join_season")
    df["is_dual_threat"] = (
        (df["rushing_yards_t"] > DUAL_THREAT_RUSHING_THRESHOLD)
        | (df["rushing_t_minus_1"] > DUAL_THREAT_RUSHING_THRESHOLD)
        | (df["rushing_t_minus_2"] > DUAL_THREAT_RUSHING_THRESHOLD)
    ).fillna(False)

    # 9. Aging curves + logged position
    def _curve_details(row: pd.Series):
        pos = row["position"]
        if pos == "QB":
            pos = "QB_dual_threat" if row["is_dual_threat"] else "QB_pocket"
        try:
            return aging_curve_value(pos, row["age"]), pos
        except Exception:
            return 1.0, pos

    curve_results = df.apply(_curve_details, axis=1)
    df["aging_curve_value"] = [r[0] for r in curve_results]
    df["aging_curve_position"] = [r[1] for r in curve_results]

    # 10. Outcome + honest inference partition (shared rule)
    df = apply_inference_partition(df, seasons_window=seasons_window)

    # 11. TE role-risk (injected rubric/eligible when present; else committed files)
    if read_fns.get("te_rubric") is not None and read_fns.get("te_eligible") is not None:
        df = add_te_role_risk_feature(df, read_fns["te_rubric"], read_fns["te_eligible"])
    else:
        df = add_te_role_risk_feature_from_files(df)

    # 12. Conform to the exact Engine-B output schema
    return _conform_to_engine_b_schema(df)
