"""Pipeline B: PFF active NFL feature store."""

from __future__ import annotations

import argparse

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def _require_columns(df, required_cols: list[str], feed_name: str) -> None:
    missing = [column for column in required_cols if column not in df.columns]
    if missing:
        raise ValueError(
            f"Anti-Speed Protocol failure: {feed_name} missing required columns: {missing}"
        )


def _read_json_feed(spark: SparkSession, path: str, source_name: str):
    return (
        spark.read.format("json")
        .load(path)
        .withColumn("source", F.lit(source_name))
        .withColumn("source_verified_at", F.current_timestamp())
    )


def build_features(
    spark: SparkSession,
    catalog: str,
    bronze_schema: str,
    silver_schema: str,
    raw_base_path: str,
) -> None:
    bronze = f"{catalog}.{bronze_schema}"
    silver = f"{catalog}.{silver_schema}"

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {bronze}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {silver}")

    receiving_raw = _read_json_feed(spark, f"{raw_base_path}/receiving", "mock_pff_receiving")
    rushing_raw = _read_json_feed(spark, f"{raw_base_path}/rushing", "mock_pff_rushing")
    snaps_raw = _read_json_feed(spark, f"{raw_base_path}/snaps", "mock_pff_snaps")
    blocking_raw = _read_json_feed(spark, f"{raw_base_path}/team_blocking", "mock_pff_team_blocking")
    college_raw = _read_json_feed(spark, f"{raw_base_path}/college_final_season", "mock_pff_college")

    _require_columns(
        receiving_raw,
        ["season", "week", "player_id", "player_name", "position", "team", "routes_run", "receiving_yards"],
        "PFF receiving feed",
    )
    _require_columns(
        rushing_raw,
        ["season", "week", "player_id", "player_name", "position", "team", "rush_attempts", "breakaway_runs"],
        "PFF rushing feed",
    )
    _require_columns(
        snaps_raw,
        [
            "season",
            "week",
            "player_id",
            "player_name",
            "position",
            "team",
            "offensive_snaps",
            "team_offensive_snaps",
            "rookie_season",
        ],
        "PFF snap feed",
    )
    _require_columns(blocking_raw, ["season", "week", "team", "run_blocking_grade"], "PFF team blocking feed")
    _require_columns(
        college_raw,
        ["player_id", "player_name", "position", "draft_class", "final_college_season", "final_season_yprr"],
        "PFF college final-season feed",
    )

    receiving_raw.write.mode("append").saveAsTable(f"{bronze}.pff_receiving")
    rushing_raw.write.mode("append").saveAsTable(f"{bronze}.pff_rushing")
    snaps_raw.write.mode("append").saveAsTable(f"{bronze}.pff_snap")
    blocking_raw.write.mode("append").saveAsTable(f"{bronze}.pff_team_blocking")
    college_raw.write.mode("append").saveAsTable(f"{bronze}.pff_college_final_season")

    receiving = spark.table(f"{bronze}.pff_receiving")
    rushing = spark.table(f"{bronze}.pff_rushing")
    snaps = spark.table(f"{bronze}.pff_snap")
    blocking = spark.table(f"{bronze}.pff_team_blocking")
    college = spark.table(f"{bronze}.pff_college_final_season")

    receiving_features = (
        receiving.where(F.col("position").isin("WR", "TE"))
        .groupBy("season", "player_id", "player_name", "position", "team")
        .agg(F.sum("routes_run").alias("season_routes_run"), F.sum("receiving_yards").alias("season_receiving_yards"))
        .withColumn(
            "yards_per_route_run",
            F.when(F.col("season_routes_run") > 0, F.col("season_receiving_yards") / F.col("season_routes_run")),
        )
    )

    rushing_features = (
        rushing.where(F.col("position") == "RB")
        .groupBy("season", "player_id", "player_name", "position", "team")
        .agg(
            F.sum("rush_attempts").alias("season_rush_attempts"),
            F.sum("breakaway_runs").alias("season_breakaway_runs"),
        )
        .withColumn(
            "breakaway_run_percentage",
            F.when(F.col("season_rush_attempts") > 0, F.col("season_breakaway_runs") / F.col("season_rush_attempts")),
        )
    )

    team_blocking_features = (
        blocking.groupBy("season", "team").agg(F.avg("run_blocking_grade").alias("run_blocking_grade"))
    )
    rb_with_blocking = rushing_features.join(team_blocking_features, ["season", "team"], "left")

    year_1_snap_features = (
        snaps.where(F.col("season") == F.col("rookie_season"))
        .groupBy("season", "player_id", "player_name", "position", "team")
        .agg(
            F.sum("offensive_snaps").alias("year_1_offensive_snaps"),
            F.sum("team_offensive_snaps").alias("year_1_team_offensive_snaps"),
            F.sum("routes_run").alias("year_1_routes_run"),
            F.sum("team_dropbacks").alias("year_1_team_dropbacks"),
        )
        .withColumn(
            "year_1_snap_percentage",
            F.when(
                F.col("year_1_team_offensive_snaps") > 0,
                F.col("year_1_offensive_snaps") / F.col("year_1_team_offensive_snaps"),
            ),
        )
        .withColumn(
            "year_1_route_participation",
            F.when(F.col("year_1_team_dropbacks") > 0, F.col("year_1_routes_run") / F.col("year_1_team_dropbacks")),
        )
        .withColumn(
            "year_1_snap_signal",
            F.when(F.col("year_1_snap_percentage") >= 0.70, "ELITE_YEAR_1_USAGE")
            .when(F.col("year_1_snap_percentage") < 0.40, "POOR_YEAR_1_USAGE")
            .when(F.col("year_1_snap_percentage").isNull(), "UNKNOWN")
            .otherwise("NEUTRAL"),
        )
    )

    college_yprr_features = (
        college.select("player_id", F.col("final_season_yprr").alias("final_college_yprr")).dropDuplicates(["player_id"])
    )
    yprr_thresholds = spark.createDataFrame(
        [("WR", 2.5), ("TE", 1.8)], ["position", "final_college_yprr_threshold"]
    )

    active_player_base = (
        receiving_features.select("season", "player_id", "player_name", "position", "team")
        .unionByName(rb_with_blocking.select("season", "player_id", "player_name", "position", "team"), allowMissingColumns=True)
        .dropDuplicates(["season", "player_id"])
    )

    features = (
        active_player_base.join(
            receiving_features.select("season", "player_id", "yards_per_route_run"),
            ["season", "player_id"],
            "left",
        )
        .join(
            rb_with_blocking.select("season", "player_id", "run_blocking_grade", "breakaway_run_percentage"),
            ["season", "player_id"],
            "left",
        )
        .join(
            year_1_snap_features.select(
                "season",
                "player_id",
                "year_1_snap_percentage",
                "year_1_route_participation",
                "year_1_snap_signal",
            ),
            ["season", "player_id"],
            "left",
        )
        .join(college_yprr_features, "player_id", "left")
        .join(yprr_thresholds, "position", "left")
        .withColumn(
            "yprr_threshold_flag",
            F.when(F.col("final_college_yprr_threshold").isNull(), F.lit(None).cast("boolean"))
            .when(F.col("final_college_yprr").isNull(), F.lit(None).cast("boolean"))
            .otherwise(F.col("final_college_yprr") < F.col("final_college_yprr_threshold")),
        )
        .withColumn(
            "feature_warnings",
            F.array_remove(
                F.array(
                    F.when(F.col("position").isin("WR", "TE") & F.col("yards_per_route_run").isNull(), "missing_yprr_inputs"),
                    F.when(F.col("position") == "RB" & F.col("breakaway_run_percentage").isNull(), "missing_breakaway_run_inputs"),
                    F.when(F.col("position") == "RB" & F.col("run_blocking_grade").isNull(), "missing_team_run_blocking_grade"),
                    F.when(F.col("year_1_snap_percentage").isNull(), "missing_or_not_year_1_snap_data"),
                    F.when(F.col("yprr_threshold_flag"), "final_college_yprr_below_framework_threshold"),
                    F.when(F.col("year_1_snap_signal") == "POOR_YEAR_1_USAGE", "year_1_snap_pct_below_40"),
                    F.when(F.col("year_1_snap_signal") == "ELITE_YEAR_1_USAGE", "year_1_snap_pct_above_70"),
                ),
                None,
            ),
        )
        .withColumn(
            "feature_quality_status",
            F.when(
                F.col("position").isin("WR", "TE") & F.col("yards_per_route_run").isNull(),
                "INCOMPLETE_REQUIRED_FEATURES",
            )
            .when(
                (F.col("position") == "RB")
                & (F.col("breakaway_run_percentage").isNull() | F.col("run_blocking_grade").isNull()),
                "INCOMPLETE_REQUIRED_FEATURES",
            )
            .otherwise("READY_FOR_MODELING"),
        )
        .withColumn("calculated_at", F.current_timestamp())
        .select(
            "player_id",
            "player_name",
            "position",
            "team",
            "season",
            "yards_per_route_run",
            "run_blocking_grade",
            "breakaway_run_percentage",
            "year_1_snap_percentage",
            "year_1_route_participation",
            "final_college_yprr",
            "yprr_threshold_flag",
            "year_1_snap_signal",
            "feature_quality_status",
            "feature_warnings",
            "calculated_at",
        )
    )

    features.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        f"{silver}.active_player_pff_features_silver"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="gen_alpha")
    parser.add_argument("--bronze-schema", default="bronze")
    parser.add_argument("--silver-schema", default="silver")
    parser.add_argument("--raw-base-path", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_features(
        SparkSession.builder.getOrCreate(),
        args.catalog,
        args.bronze_schema,
        args.silver_schema,
        args.raw_base_path,
    )
