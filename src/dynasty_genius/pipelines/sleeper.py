"""Step 0.7: Sleeper live roster ingestion for roster-state features."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any

import requests
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BASE_URL = "https://api.sleeper.app/v1"

USERNAME_ENV = "DYNASTY_SLEEPER_USERNAME"
SEASON_ENV = "DYNASTY_SEASON"
LEAGUE_ID_ENV = "DYNASTY_SLEEPER_LEAGUE_ID"
LEAGUE_NAME_ENV = "DYNASTY_SLEEPER_LEAGUE_NAME"

SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Anti-Speed Protocol failure: missing required environment variable {name}")
    return value


def _has_live_sleeper_config() -> bool:
    return bool(os.getenv(USERNAME_ENV) and os.getenv(SEASON_ENV) and (os.getenv(LEAGUE_ID_ENV) or os.getenv(LEAGUE_NAME_ENV)))


def _get(path: str) -> Any:
    response = requests.get(f"{BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    data = response.json()
    if data is None:
        raise ValueError(f"Sleeper returned no data for path {path}")
    return data


def _resolve_league_id(username: str, season: str, league_id: str | None, league_name: str | None) -> tuple[str, dict[str, Any]]:
    user = _get(f"/user/{username}")
    if not user:
        raise ValueError(f"Anti-Speed Protocol failure: Sleeper user not found for {username!r}")

    user_id = user["user_id"]
    if league_id:
        return league_id, user

    if not league_name:
        raise ValueError(
            f"Anti-Speed Protocol failure: set either {LEAGUE_ID_ENV} or {LEAGUE_NAME_ENV}; refusing to guess a league."
        )

    leagues = _get(f"/user/{user_id}/leagues/nfl/{season}")
    league = next((item for item in leagues if item.get("name") == league_name), None)
    if league is None:
        raise ValueError(
            f"Anti-Speed Protocol failure: league {league_name!r} not found for season {season}."
        )
    return league["league_id"], user


def fetch_roster_snapshot() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    username = _required_env(USERNAME_ENV)
    season = _required_env(SEASON_ENV)
    configured_league_id = os.getenv(LEAGUE_ID_ENV) or None
    configured_league_name = os.getenv(LEAGUE_NAME_ENV) or None

    league_id, user = _resolve_league_id(username, season, configured_league_id, configured_league_name)
    user_id = user["user_id"]

    rosters = _get(f"/league/{league_id}/rosters")
    users = _get(f"/league/{league_id}/users")
    all_players = _get("/players/nfl")
    league = _get(f"/league/{league_id}")

    my_roster = next((roster for roster in rosters if roster.get("owner_id") == user_id), None)
    if my_roster is None:
        raise ValueError(
            f"Anti-Speed Protocol failure: no roster found for user {username!r} in league {league_id}."
        )

    ingested_at = datetime.now(timezone.utc).isoformat()
    players = []
    for player_id in my_roster.get("players") or []:
        raw = all_players.get(player_id)
        if not raw:
            continue
        position = raw.get("position") or "OTHER"
        players.append(
            {
                "ingested_at": ingested_at,
                "source": "sleeper_api",
                "season": season,
                "league_id": league_id,
                "league_name": league.get("name"),
                "owner_user_id": user_id,
                "owner_username": username,
                "roster_id": my_roster.get("roster_id"),
                "player_id": player_id,
                "player_name": f"{raw.get('first_name', '')} {raw.get('last_name', '')}".strip(),
                "position": position if position in SKILL_POSITIONS else "OTHER",
                "nfl_team": raw.get("team") or "FA",
                "age_years": float(raw["age"]) if raw.get("age") is not None else None,
                "status": raw.get("status"),
                "fantasy_positions": raw.get("fantasy_positions") or [],
                "source_payload_json": json.dumps(raw, sort_keys=True),
            }
        )

    metadata = [
        {
            "ingested_at": ingested_at,
            "source": "sleeper_api",
            "season": season,
            "league_id": league_id,
            "league_name": league.get("name"),
            "owner_user_id": user_id,
            "owner_username": username,
            "roster_id": my_roster.get("roster_id"),
            "league_user_count": len(users),
            "roster_player_count": len(players),
        }
    ]
    return players, metadata


def fetch_mock_roster_snapshot() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ingested_at = datetime.now(timezone.utc).isoformat()
    season = os.getenv(SEASON_ENV) or "2026"
    mock_players = [
        {
            "player_id": "mock-jonathan-taylor",
            "player_name": "Jonathan Taylor",
            "position": "RB",
            "nfl_team": "IND",
            "age_years": 26.0,
            "status": "Active",
            "fantasy_positions": ["RB"],
        },
        {
            "player_id": "mock-davante-adams",
            "player_name": "Davante Adams",
            "position": "WR",
            "nfl_team": "LAR",
            "age_years": 33.0,
            "status": "Active",
            "fantasy_positions": ["WR"],
        },
        {
            "player_id": "mock-tyreek-hill",
            "player_name": "Tyreek Hill",
            "position": "WR",
            "nfl_team": "FA",
            "age_years": 32.0,
            "status": "Free Agent",
            "fantasy_positions": ["WR"],
        },
        {
            "player_id": "mock-wait-and-see-rookie",
            "player_name": "Wait-and-See Rookie",
            "position": "WR",
            "nfl_team": "FA",
            "age_years": 22.0,
            "status": "Watchlist",
            "fantasy_positions": ["WR"],
        },
    ]

    players = [
        {
            "ingested_at": ingested_at,
            "source": "mock_sleeper_ground_truth",
            "season": season,
            "league_id": "mock-productive-struggle-league",
            "league_name": "Mock Productive Struggle",
            "owner_user_id": "mock-david",
            "owner_username": "mock_pm_roster",
            "roster_id": 1,
            "source_payload_json": json.dumps(player, sort_keys=True),
            **player,
        }
        for player in mock_players
    ]
    metadata = [
        {
            "ingested_at": ingested_at,
            "source": "mock_sleeper_ground_truth",
            "season": season,
            "league_id": "mock-productive-struggle-league",
            "league_name": "Mock Productive Struggle",
            "owner_user_id": "mock-david",
            "owner_username": "mock_pm_roster",
            "roster_id": 1,
            "league_user_count": 12,
            "roster_player_count": len(players),
        }
    ]
    return players, metadata


def ingest_sleeper(spark: SparkSession, catalog: str, bronze_schema: str, silver_schema: str) -> None:
    bronze = f"{catalog}.{bronze_schema}"
    silver = f"{catalog}.{silver_schema}"

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {bronze}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {silver}")

    if _has_live_sleeper_config():
        roster_rows, metadata_rows = fetch_roster_snapshot()
    else:
        roster_rows, metadata_rows = fetch_mock_roster_snapshot()
    if not roster_rows:
        raise ValueError("Anti-Speed Protocol failure: Sleeper roster snapshot returned zero player rows.")

    roster_df = spark.createDataFrame(roster_rows).withColumn("ingested_at", F.to_timestamp("ingested_at"))
    metadata_df = spark.createDataFrame(metadata_rows).withColumn("ingested_at", F.to_timestamp("ingested_at"))

    roster_df.write.mode("append").saveAsTable(f"{bronze}.sleeper_roster_snapshot")
    metadata_df.write.mode("append").saveAsTable(f"{bronze}.sleeper_ingestion_audit")

    current_roster = (
        roster_df.select(
            "ingested_at",
            "season",
            "league_id",
            "league_name",
            "owner_user_id",
            "owner_username",
            "roster_id",
            "player_id",
            "player_name",
            "position",
            "nfl_team",
            "age_years",
            "status",
            "fantasy_positions",
        )
        .withColumn(
            "feature_quality_status",
            F.when(F.col("age_years").isNull(), "INCOMPLETE_REQUIRED_FEATURES").otherwise("READY_FOR_MODELING"),
        )
        .withColumn(
            "framework_flags",
            F.array_remove(
                F.array(
                    F.when(F.col("age_years").isNull(), "missing_verified_age"),
                    F.when(F.col("nfl_team") == "FA", "nfl_free_agent"),
                ),
                None,
            ),
        )
    )

    current_roster.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        f"{silver}.current_roster_state"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="gen_alpha")
    parser.add_argument("--bronze-schema", default="bronze")
    parser.add_argument("--silver-schema", default="silver")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    ingest_sleeper(SparkSession.builder.getOrCreate(), args.catalog, args.bronze_schema, args.silver_schema)
