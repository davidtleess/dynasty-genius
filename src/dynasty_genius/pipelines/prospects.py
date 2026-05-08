"""Pipeline A: quantitative college prospect feature store."""

from __future__ import annotations

import argparse

from pyspark.sql import SparkSession, Window
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

    identity_df = _read_json_feed(spark, f"{raw_base_path}/identity", "mock_playerprofiler_identity")
    production_df = _read_json_feed(
        spark, f"{raw_base_path}/college_production", "mock_cfb_reference_production"
    )
    team_df = _read_json_feed(
        spark, f"{raw_base_path}/team_production", "mock_cfb_reference_team"
    )
    ras_df = _read_json_feed(spark, f"{raw_base_path}/ras", "mock_ras_feed")

    _require_columns(
        identity_df,
        ["player_id", "player_name", "position", "school", "draft_class", "date_of_birth"],
        "prospect identity feed",
    )
    _require_columns(
        production_df,
        [
            "player_id",
            "player_name",
            "position",
            "school",
            "season",
            "rushing_yards",
            "receiving_yards",
            "passing_yards",
            "rushing_tds",
            "receiving_tds",
            "passing_tds",
        ],
        "college production feed",
    )
    _require_columns(
        team_df,
        ["school", "season", "team_total_yards", "team_total_tds"],
        "team production feed",
    )

    identity_df.write.mode("append").saveAsTable(f"{bronze}.prospect_identity")
    production_df.write.mode("append").saveAsTable(f"{bronze}.college_production")
    team_df.write.mode("append").saveAsTable(f"{bronze}.team_production")
    ras_df.write.mode("append").saveAsTable(f"{bronze}.athletic_testing")

    identity = (
        spark.table(f"{bronze}.prospect_identity")
        .where(F.col("draft_class").isin(2026, 2027))
        .where(F.col("player_id").isNotNull())
        .where(F.col("date_of_birth").isNotNull())
    )
    production = spark.table(f"{bronze}.college_production").where(F.col("player_id").isNotNull())
    team = (
        spark.table(f"{bronze}.team_production")
        .where(F.col("team_total_yards").isNotNull())
        .where(F.col("team_total_tds").isNotNull())
    )
    ras = spark.table(f"{bronze}.athletic_testing").where(F.col("draft_class").isin(2026, 2027))

    latest_season_window = Window.partitionBy("player_id").orderBy(F.col("season").desc())
    latest_production = (
        production.withColumn("season_rank", F.row_number().over(latest_season_window))
        .where(F.col("season_rank") == 1)
        .drop("season_rank")
    )

    production_with_team = (
        latest_production.join(team, ["school", "season"], "left")
        .withColumn(
            "player_total_yards",
            F.coalesce(F.col("rushing_yards"), F.lit(0.0))
            + F.coalesce(F.col("receiving_yards"), F.lit(0.0))
            + F.coalesce(F.col("passing_yards"), F.lit(0.0)),
        )
        .withColumn(
            "player_total_tds",
            F.coalesce(F.col("rushing_tds"), F.lit(0.0))
            + F.coalesce(F.col("receiving_tds"), F.lit(0.0))
            + F.coalesce(F.col("passing_tds"), F.lit(0.0)),
        )
        .withColumn(
            "yard_share",
            F.when(F.col("team_total_yards") > 0, F.col("player_total_yards") / F.col("team_total_yards")),
        )
        .withColumn(
            "td_share",
            F.when(F.col("team_total_tds") > 0, F.col("player_total_tds") / F.col("team_total_tds")),
        )
        .withColumn(
            "college_dominator_rating",
            F.when(
                F.col("yard_share").isNotNull() & F.col("td_share").isNotNull(),
                (F.col("yard_share") + F.col("td_share")) / F.lit(2.0),
            ),
        )
    )

    age_thresholds = spark.createDataFrame(
        [("RB", 22.0), ("WR", 23.0), ("QB", 24.0), ("TE", 24.0)],
        ["position", "age_threshold"],
    )
    dominator_thresholds = spark.createDataFrame(
        [("WR", 0.25), ("RB", 0.30), ("TE", 0.15), ("QB", None)],
        ["position", "dominator_threshold"],
    )

    ras_latest = (
        ras.select(
            "player_id",
            F.col("relative_athletic_score").cast("double").alias("relative_athletic_score"),
            F.coalesce(F.col("ras_status"), F.lit("UNAVAILABLE")).alias("ras_status"),
        )
        .dropDuplicates(["player_id"])
    )

    features = (
        identity.join(production_with_team, ["player_id", "player_name", "position", "school"], "left")
        .withColumn(
            "nfl_entry_date",
            F.to_date(F.concat_ws("-", F.col("draft_class"), F.lit("04"), F.lit("24"))),
        )
        .withColumn(
            "age_at_nfl_entry",
            F.round(F.months_between(F.col("nfl_entry_date"), F.col("date_of_birth")) / 12, 2),
        )
        .join(ras_latest, "player_id", "left")
        .withColumn("ras_status", F.coalesce(F.col("ras_status"), F.lit("UNAVAILABLE")))
        .join(age_thresholds, "position", "left")
        .join(dominator_thresholds, "position", "left")
        .withColumn(
            "age_flag",
            F.when(F.col("age_threshold").isNotNull(), F.col("age_at_nfl_entry") >= F.col("age_threshold")).otherwise(False),
        )
        .withColumn(
            "dominator_flag",
            F.when(F.col("dominator_threshold").isNull(), F.lit(None).cast("boolean"))
            .when(F.col("college_dominator_rating").isNull(), F.lit(None).cast("boolean"))
            .otherwise(F.col("college_dominator_rating") < F.col("dominator_threshold")),
        )
        .withColumn(
            "ras_above_8",
            F.when(F.col("relative_athletic_score").isNull(), F.lit(None).cast("boolean")).otherwise(
                F.col("relative_athletic_score") >= 8.0
            ),
        )
        .withColumn(
            "feature_warnings",
            F.array_remove(
                F.array(
                    F.when(F.col("age_at_nfl_entry").isNull(), "missing_verified_age"),
                    F.when(F.col("college_dominator_rating").isNull(), "missing_dominator_inputs"),
                    F.when(F.col("relative_athletic_score").isNull(), "missing_or_unavailable_ras"),
                    F.when(F.col("age_flag"), "age_above_framework_threshold"),
                    F.when(F.col("dominator_flag"), "dominator_below_position_threshold"),
                    F.when(F.col("ras_above_8") == False, "ras_below_8"),
                ),
                None,
            ),
        )
        .withColumn(
            "feature_quality_status",
            F.when(
                F.array_contains(F.col("feature_warnings"), "missing_verified_age")
                | F.array_contains(F.col("feature_warnings"), "missing_dominator_inputs"),
                "INCOMPLETE_REQUIRED_FEATURES",
            ).otherwise("READY_FOR_MODELING"),
        )
        .withColumn("calculated_at", F.current_timestamp())
        .select(
            F.col("player_name").alias("Player_Name"),
            F.col("draft_class").alias("Draft_Class"),
            F.col("age_at_nfl_entry").alias("Age_At_NFL_Entry"),
            F.col("college_dominator_rating").alias("College_Dominator_Rating"),
            F.col("relative_athletic_score").alias("Relative_Athletic_Score"),
            "player_id",
            "position",
            "school",
            "ras_status",
            "age_flag",
            "dominator_flag",
            "ras_above_8",
            "feature_quality_status",
            "feature_warnings",
            "calculated_at",
        )
    )

    features.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        f"{silver}.prospect_features_silver"
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
