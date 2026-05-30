#!/usr/bin/env python3.14
"""
Capture today's FantasyCalc dynasty values and write to fc_snapshots.db.

Usage:
    .venv/bin/python3.14 scripts/snapshot_fantasycalc.py
"""
from __future__ import annotations

import hashlib
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


def _fetch_fc_rows() -> list[dict]:
    """Fetch current FantasyCalc values and normalize to fc_native store rows.

    The network seam — tests monkeypatch this to supply a fixed payload. Returns
    [] when the API returns no usable data; an HTTP failure exits(1).
    """
    logger.info("Fetching FantasyCalc values from: %s", FC_URL)
    try:
        response = httpx.get(FC_URL, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching FantasyCalc data: %s", e)
        sys.exit(1)

    # Handle list vs dict with 'players' key
    if isinstance(data, list):
        players = data
    elif isinstance(data, dict) and "players" in data:
        players = data["players"]
    else:
        logger.error("Unexpected FantasyCalc API response format.")
        return []

    if not players:
        logger.warning("FantasyCalc API returned no player data.")
        return []

    snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    inserted_at = datetime.now(timezone.utc).isoformat()

    rows: list[dict] = []
    for entry in players:
        player = entry.get("player", {})
        sleeper_id = player.get("sleeperId")
        if not sleeper_id:
            # Common for some historical/defunct entries
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
    return rows


def snapshot_fantasycalc(db_path: Path = DEFAULT_DB_PATH) -> int:
    """Capture today's FantasyCalc values via the IMMUTABLE append path. Returns row count.

    Same-day re-runs are idempotent (identical rows → no-op); a changed value for
    an already-recorded (snapshot_date, league_settings_hash, sleeper_id) raises
    MarketSnapshotImmutabilityError and is NOT swallowed (fail loud — no silent
    overwrite). The HTTP fetch is isolated in _fetch_fc_rows.
    """
    rows = _fetch_fc_rows()
    if not rows:
        return 0
    store = MarketSnapshotStore(db_path=db_path)
    count = store.append_snapshots(rows)
    logger.info(
        "Successfully wrote %d snapshots for %s", count, rows[0]["snapshot_date"]
    )
    return count


if __name__ == "__main__":
    snapshot_fantasycalc()
