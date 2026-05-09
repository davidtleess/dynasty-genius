"""Step 2.1: Identity Resolution Pipeline."""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


MARKET_DERIVED_COLUMNS = {
    "ktc_id",
    "ktc_slug",
    "ktc_value",
    "ktc_market_value",
    "adp",
    "fantasypros_id",
    "dynastynerds_id",
    "market_value",
    "market_rank",
}


def _require_no_market_identity_columns(columns: list[str]) -> None:
    present = MARKET_DERIVED_COLUMNS.intersection({column.lower() for column in columns})
    if present:
        blocked = ", ".join(sorted(present))
        raise ValueError(f"Market-derived columns are not allowed in canonical identity: {blocked}")


def _optional_column(columns: list[str], name: str):
    return F.col(name) if name in columns else F.lit(None).alias(name)


def _normalized_name_expr(column_name: str):
    without_suffix = F.regexp_replace(
        F.lower(F.trim(F.col(column_name))),
        r"\b(jr|sr|ii|iii|iv|v)\b\.?",
        "",
    )
    without_punctuation = F.regexp_replace(without_suffix, r"[\\.']", "")
    normalized = F.regexp_replace(without_punctuation, r"[^a-z0-9]+", "_")
    normalized = F.regexp_replace(normalized, r"_+", "_")
    normalized = F.regexp_replace(normalized, r"^_|_$", "")

    first_token = F.substring_index(normalized, "_", 1)
    remainder = F.regexp_replace(normalized, r"^[^_]+_?", "")
    canonical_first = (
        F.when(first_token == "josh", "joshua")
        .when(first_token == "mike", "michael")
        .when(first_token == "mikey", "michael")
        .when(first_token == "chris", "christopher")
        .when(first_token == "matt", "matthew")
        .when(first_token == "tom", "thomas")
        .otherwise(first_token)
    )
    return F.when(remainder == "", canonical_first).otherwise(
        F.concat_ws("_", canonical_first, remainder)
    )

def build_identity_table(spark: SparkSession, catalog: str, bronze_schema: str, silver_schema: str):
    """
    Consolidates player IDs from multiple bronze sources into a canonical silver mapping.
    """
    bronze = f"{catalog}.{bronze_schema}"
    silver = f"{catalog}.{silver_schema}"
    
    # 1. Start with Sleeper as the primary anchor for active players
    # (Assuming sleeper_roster_snapshot exists in Bronze from Step 0.7)
    source_df = spark.table(f"{bronze}.sleeper_roster_snapshot")
    _require_no_market_identity_columns(source_df.columns)

    birth_date_col = _optional_column(source_df.columns, "birth_date")
    birth_year_col = _optional_column(source_df.columns, "birth_year")
    nfl_team_col = _optional_column(source_df.columns, "nfl_team")
    jersey_number_col = _optional_column(source_df.columns, "jersey_number")
    sleeper_df = source_df \
        .select(
            "player_id",
            "player_name",
            "position",
            birth_date_col,
            birth_year_col,
            nfl_team_col,
            jersey_number_col,
        ) \
        .distinct()
        
    # 2. Generate initial dg_id. Birth year is required for VERIFIED canonical rows.
    identity_df = sleeper_df.withColumn(
        "resolved_birth_year",
        F.coalesce(
            F.col("birth_year").cast("int"),
            F.year(F.to_date(F.col("birth_date"))),
        )
    ).withColumn(
        "base_dg_id",
        F.when(
            F.col("resolved_birth_year").isNotNull(),
            F.concat_ws(
                "_",
                _normalized_name_expr("player_name"),
                F.lower(F.col("position")),
                F.col("resolved_birth_year").cast("string"),
            ),
        ).otherwise(
            F.concat_ws("_", _normalized_name_expr("player_name"), F.lower(F.col("position")))
        )
    ).withColumn(
        "duplicate_number",
        F.row_number().over(
            Window.partitionBy("base_dg_id").orderBy(F.col("player_id").cast("string"))
        ),
    ).withColumn(
        "dg_id",
        F.when(
            F.col("duplicate_number") == 1,
            F.col("base_dg_id"),
        ).otherwise(F.concat_ws("_", F.col("base_dg_id"), F.col("duplicate_number").cast("string"))),
    ).select(
        F.col("dg_id"),
        F.col("player_name").alias("full_name"),
        F.col("position"),
        F.to_date(F.col("birth_date")).alias("birth_date"),
        F.col("nfl_team"),
        F.col("jersey_number"),
        F.col("player_id").alias("sleeper_id"),
        F.lit(None).cast("string").alias("pff_id"),
        F.lit(None).cast("string").alias("pfr_id"),
        F.lit(None).cast("string").alias("playerprofiler_id"),
        F.when(F.col("resolved_birth_year").isNull(), "CONFLICT")
        .otherwise("PENDING")
        .alias("verification_status"),
        F.current_timestamp().alias("last_updated_ts"),
        F.current_timestamp().alias("effective_from"),
        F.lit(None).cast("timestamp").alias("effective_to"),
        F.lit(True).alias("is_current")
    )
    
    # 3. Write to Silver
    # Using overwrite for the initial draft; in production this would be a MERGE
    identity_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        f"{silver}.player_identity"
    )

def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--bronze-schema", required=True)
    parser.add_argument("--silver-schema", required=True)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    spark = SparkSession.builder.getOrCreate()
    build_identity_table(spark, args.catalog, args.bronze_schema, args.silver_schema)
