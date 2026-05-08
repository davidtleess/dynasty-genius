"""Read-only Mosaic AI Agent tools for the gen_alpha feature stores."""

from __future__ import annotations

from typing import Any

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

spark = SparkSession.builder.getOrCreate()

PROSPECT_TABLE = "gen_alpha.silver.prospect_features_silver"
ACTIVE_PFF_TABLE = "gen_alpha.silver.active_player_pff_features_silver"

ABORT_WARNING = (
    "ANTI_SPEED_ABORT: feature_quality_status == INCOMPLETE_REQUIRED_FEATURES. "
    "Abort any trade, rookie-pick, buy/sell, or roster recommendation for this player "
    "until missing required source data is verified and the feature row is rebuilt."
)


def _latest_by_key(df, partition_cols: list[str]):
    window = Window.partitionBy(*partition_cols).orderBy(F.col("calculated_at").desc_nulls_last())
    return df.withColumn("_rn", F.row_number().over(window)).where(F.col("_rn") == 1).drop("_rn")


def get_prospect_metrics(player_name: str) -> dict[str, Any] | str:
    if not player_name or not player_name.strip():
        return "ANTI_SPEED_ABORT: player_name is required. Do not make recommendations."

    matches = (
        spark.table(PROSPECT_TABLE)
        .withColumn("_player_name_norm", F.lower(F.trim(F.col("Player_Name"))))
        .where(F.col("_player_name_norm") == player_name.strip().lower())
    )
    rows = _latest_by_key(matches, ["player_id"]).limit(2).collect()

    if not rows:
        return (
            f"ANTI_SPEED_ABORT: no verified prospect feature row found for '{player_name}'. "
            "Do not make recommendations until the player is present in gen_alpha.silver.prospect_features_silver."
        )
    if len(rows) > 1:
        candidates = [row["Player_Name"] for row in rows]
        return (
            f"ANTI_SPEED_ABORT: multiple prospect rows matched '{player_name}': {candidates}. "
            "Require player_id disambiguation before making recommendations."
        )

    row = rows[0].asDict(recursive=True)
    if row.get("feature_quality_status") == "INCOMPLETE_REQUIRED_FEATURES":
        return f"{ABORT_WARNING} Player={row.get('Player_Name')}; Warnings={row.get('feature_warnings')}"

    return {
        "player_id": row.get("player_id"),
        "player_name": row.get("Player_Name"),
        "draft_class": row.get("Draft_Class"),
        "position": row.get("position"),
        "school": row.get("school"),
        "age_at_nfl_entry": row.get("Age_At_NFL_Entry"),
        "college_dominator_rating": row.get("College_Dominator_Rating"),
        "relative_athletic_score": row.get("Relative_Athletic_Score"),
        "framework_flags": {
            "age_flag": row.get("age_flag"),
            "dominator_flag": row.get("dominator_flag"),
            "ras_above_8": row.get("ras_above_8"),
            "feature_warnings": row.get("feature_warnings"),
            "feature_quality_status": row.get("feature_quality_status"),
        },
    }


def get_active_nfl_metrics(player_id: str) -> dict[str, Any] | str:
    if not player_id or not player_id.strip():
        return "ANTI_SPEED_ABORT: player_id is required. Do not make recommendations."

    matches = spark.table(ACTIVE_PFF_TABLE).where(F.col("player_id") == player_id.strip())
    rows = _latest_by_key(matches, ["player_id"]).limit(1).collect()

    if not rows:
        return (
            f"ANTI_SPEED_ABORT: no verified active NFL feature row found for player_id='{player_id}'. "
            "Do not make recommendations until the player is present in gen_alpha.silver.active_player_pff_features_silver."
        )

    row = rows[0].asDict(recursive=True)
    if row.get("feature_quality_status") == "INCOMPLETE_REQUIRED_FEATURES":
        return (
            f"{ABORT_WARNING} Player_ID={row.get('player_id')}; "
            f"Player={row.get('player_name')}; Warnings={row.get('feature_warnings')}"
        )

    return {
        "player_id": row.get("player_id"),
        "player_name": row.get("player_name"),
        "position": row.get("position"),
        "team": row.get("team"),
        "season": row.get("season"),
        "yards_per_route_run": row.get("yards_per_route_run"),
        "year_1_snap_percentage": row.get("year_1_snap_percentage"),
        "year_1_route_participation": row.get("year_1_route_participation"),
        "run_blocking_grade": row.get("run_blocking_grade"),
        "breakaway_run_percentage": row.get("breakaway_run_percentage"),
        "final_college_yprr": row.get("final_college_yprr"),
        "framework_flags": {
            "yprr_threshold_flag": row.get("yprr_threshold_flag"),
            "year_1_snap_signal": row.get("year_1_snap_signal"),
            "feature_warnings": row.get("feature_warnings"),
            "feature_quality_status": row.get("feature_quality_status"),
        },
    }
