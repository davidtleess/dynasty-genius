#!/usr/bin/env python3.14
"""DG-020 — backfill point-in-time FantasyCalc market history into the snapshot store.

What the FC API actually serves (measured 2026-08-28, this ticket's first step):
``GET /trades/historical/{fcId}?isDynasty=true&numQbs=2`` returns a per-player
DAILY value series — gap-free, with a GLOBAL window start of 2025-07-01. Nothing
earlier is served on any endpoint (the 2021–2024 annual dates in the store came
from the DynastyProcess archive loader, not from FantasyCalc). So this loader
backfills the API's full servable window; history before it belongs to
``scripts/load_dynastyprocess_archive.py``.

Provenance and safety, per the store's existing shape:
  * rows are tagged ``source='fc_history_api'`` — never ``fc_native``, which is
    reserved for the forward W2a daily capture (same rule the W1.4 adapter
    enforces for backfill sources);
  * ranks/trend are left NULL like the dp_archive backfill rows — the history
    endpoint serves values only, and ranks computed over today's player universe
    would be survivor-biased fabrication;
  * a date the store already holds is SKIPPED whole — fc_native and dp_archive
    rows stay exactly as recorded, and re-runs are idempotent by the same rule;
  * the current UTC day is excluded by default: the forward capture owns it, and
    pre-writing it would turn that capture's append into an immutability
    conflict.

Known limitation (disclosed, not hidden): the player universe comes from
``/values/current``, so players who left FantasyCalc's rankings before today are
not queried — their 2025-07→exit history is not captured. The DynastyProcess
path has no such bias; this loader adds fine-grained recent FC-market truth on
top of that backbone.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

sys.path.append(str(Path(__file__).parent.parent))

from scripts.snapshot_fantasycalc import FC_URL, LEAGUE_SETTINGS_HASH  # noqa: E402
from src.dynasty_genius.eval.market_snapshot_store import (  # noqa: E402
    MarketSnapshotStore,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

FC_HISTORY_URL_TMPL = (
    "https://api.fantasycalc.com/trades/historical/{fc_id}?isDynasty=true&numQbs=2"
)
SOURCE_TAG = "fc_history_api"
DEFAULT_DB_PATH = Path("app/data/fc_snapshots.db")
_GRIDS = ("daily", "weekly", "monthly")


def _normalize_universe(payload) -> list[dict]:
    """Current-values payload → [{fc_id, sleeper_id, position}], skipping
    entries without a sleeperId (same rule as the forward capture)."""
    if isinstance(payload, dict) and "players" in payload:
        payload = payload["players"]
    if not isinstance(payload, list):
        logger.error("Unexpected FantasyCalc API response format.")
        return []
    players: list[dict] = []
    for entry in payload:
        player = entry.get("player", {})
        fc_id, sleeper_id = player.get("id"), player.get("sleeperId")
        if fc_id is None or not sleeper_id:
            continue
        players.append(
            {
                "fc_id": int(fc_id),
                "sleeper_id": str(sleeper_id),
                "position": player.get("position"),
            }
        )
    return players


def _normalize_series(payload) -> dict[str, int]:
    """History payload ([{date: 'MM/DD/YYYY', value: int}]) → {iso_date: value}.

    External data — malformed items are skipped (fail closed), never crash.
    """
    series: dict[str, int] = {}
    if not isinstance(payload, list):
        return series
    for item in payload:
        try:
            iso = datetime.strptime(item["date"], "%m/%d/%Y").date().isoformat()
            series[iso] = int(item["value"])
        except (KeyError, TypeError, ValueError):
            continue
    return series


def _fetch_universe() -> list[dict]:
    """Network seam — tests monkeypatch httpx.get. Universe failure is fatal."""
    logger.info("Fetching FantasyCalc player universe: %s", FC_URL)
    try:
        response = httpx.get(FC_URL, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching FantasyCalc universe: %s", e)
        sys.exit(1)
    return _normalize_universe(response.json())


def _fetch_history(fc_id: int) -> dict[str, int] | None:
    """One player's daily series, or None on HTTP failure (player skipped)."""
    try:
        response = httpx.get(FC_HISTORY_URL_TMPL.format(fc_id=fc_id), timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("No history for fc_id=%s: %s", fc_id, e)
        return None
    return _normalize_series(response.json())


def _grid_dates(dates, grid: str) -> list[str]:
    """Filter ISO dates to the requested grid: daily=all, weekly=Mondays,
    monthly=first-of-month."""
    if grid not in _GRIDS:
        raise ValueError(f"grid must be one of {_GRIDS}, got {grid!r}")
    keep = sorted(set(dates))
    if grid == "weekly":
        return [d for d in keep if date.fromisoformat(d).isoweekday() == 1]
    if grid == "monthly":
        return [d for d in keep if d.endswith("-01")]
    return keep


def backfill_fc_history(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    grid: str = "daily",
    end_exclusive: str | None = None,
    throttle: float = 0.0,
) -> dict:
    """Backfill the FC history window into the store. Returns a run summary.

    Idempotent and collision-free by construction: every target date already
    present in the store (any source) is skipped whole. Each written date is one
    immutable append batch, so a failure leaves no partial date.
    """
    if end_exclusive is None:
        end_exclusive = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = MarketSnapshotStore(db_path=db_path)
    inserted_at = datetime.now(timezone.utc).isoformat()

    universe = _fetch_universe()
    values_by_date: dict[str, list[dict]] = {}
    players_no_history = 0
    for i, player in enumerate(universe):
        if throttle and i:
            time.sleep(throttle)
        series = _fetch_history(player["fc_id"])
        if not series:
            players_no_history += 1
            continue
        for iso, value in series.items():
            values_by_date.setdefault(iso, []).append(
                {
                    "snapshot_date": iso,
                    "league_settings_hash": LEAGUE_SETTINGS_HASH,
                    "sleeper_id": player["sleeper_id"],
                    "value": value,
                    "overall_rank": None,
                    "position_rank": None,
                    "position": player["position"],
                    "trend_30day": None,
                    "source": SOURCE_TAG,
                    "inserted_at": inserted_at,
                }
            )

    targets = [
        d for d in _grid_dates(values_by_date, grid) if d < end_exclusive
    ]
    dates_written: list[str] = []
    dates_skipped_existing: list[str] = []
    rows_written = 0
    for target in targets:
        if store.has_snapshot(target):
            dates_skipped_existing.append(target)
            continue
        rows = sorted(values_by_date[target], key=lambda r: r["sleeper_id"])
        store.append_snapshots(rows)
        dates_written.append(target)
        rows_written += len(rows)

    summary = {
        "grid": grid,
        "end_exclusive": end_exclusive,
        "players_total": len(universe),
        "players_no_history": players_no_history,
        "dates_targeted": len(targets),
        "dates_written": dates_written,
        "dates_skipped_existing": dates_skipped_existing,
        "rows_written": rows_written,
    }
    logger.info(
        "fc_history backfill: %d rows across %d dates (%d dates already present)",
        rows_written,
        len(dates_written),
        len(dates_skipped_existing),
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill FantasyCalc point-in-time history (2025-07-01→) "
        "into the market snapshot store."
    )
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--grid", choices=_GRIDS, default="daily")
    parser.add_argument(
        "--end-exclusive",
        default=None,
        help="ISO date; only dates strictly before it are written "
        "(default: today UTC — the forward capture owns the current day).",
    )
    parser.add_argument(
        "--throttle",
        type=float,
        default=0.15,
        help="Seconds between per-player history requests.",
    )
    args = parser.parse_args(argv)
    summary = backfill_fc_history(
        db_path=args.db_path,
        grid=args.grid,
        end_exclusive=args.end_exclusive,
        throttle=args.throttle,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
