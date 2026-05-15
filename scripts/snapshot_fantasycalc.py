#!/usr/bin/env python3.14
"""
Capture today's FantasyCalc dynasty values and write to fc_snapshots.db.

Usage:
    .venv/bin/python3.14 scripts/snapshot_fantasycalc.py
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FC_URL = "https://api.fantasycalc.com/values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1"
LEAGUE_SETTINGS_HASH = hashlib.sha256(
    "isDynasty=true&numQbs=2&numTeams=12&ppr=1".encode()
).hexdigest()[:16]

DEFAULT_DB_PATH = Path("app/data/fc_snapshots.db")


def snapshot_fantasycalc(db_path: Path = DEFAULT_DB_PATH) -> int:
    """Fetch current values from FantasyCalc and store in SQLite. Returns row count."""
    logger.info("Fetching FantasyCalc values from: %s", FC_URL)

    try:
        response = httpx.get(FC_URL, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        # Handle list vs dict with 'players' key
        players = []
        if isinstance(data, list):
            players = data
        elif isinstance(data, dict) and "players" in data:
            players = data["players"]
        else:
            logger.error("Unexpected FantasyCalc API response format.")
            return 0

        if not players:
            logger.warning("FantasyCalc API returned no player data.")
            return 0

        snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        inserted_at = datetime.now(timezone.utc).isoformat()
        store = MarketSnapshotStore(db_path=db_path)

        rows = []
        for entry in players:
            player = entry.get("player", {})
            sleeper_id = player.get("sleeperId")

            if not sleeper_id:
                # Log this at debug level as it's common for some historical/defunct entries
                logger.debug("Skipping player with no sleeperId: %s", player.get("name"))
                continue

            rows.append({
                "snapshot_date": snapshot_date,
                "league_settings_hash": LEAGUE_SETTINGS_HASH,
                "sleeper_id": str(sleeper_id),
                "value": int(entry.get("value", 0)),
                "overall_rank": entry.get("overallRank"),
                "position_rank": entry.get("positionRank"),
                "position": player.get("position"),
                "trend_30day": entry.get("trend30Day"),
                "source": "fc_native",
                "inserted_at": inserted_at,
            })

        if not rows:
            logger.warning("No valid rows with sleeperId found in API response.")
            return 0

        count = store.upsert_snapshots(rows)
        logger.info("Successfully wrote %d snapshots for %s", count, snapshot_date)
        return count

    except httpx.HTTPError as e:
        logger.error("HTTP error fetching FantasyCalc data: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Error processing FantasyCalc data or writing to DB: %s", e)
        sys.exit(2)


if __name__ == "__main__":
    snapshot_fantasycalc()
