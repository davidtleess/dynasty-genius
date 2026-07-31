"""Capture David's league transaction history into the durable store.

Callable by hand or by a scheduler that does not yet exist. This script installs nothing,
schedules nothing, and touches no other producer — adding a LaunchAgent is a separate
decision and a separate word.

    .venv/bin/python3.14 scripts/run_league_transaction_capture.py
    .venv/bin/python3.14 scripts/run_league_transaction_capture.py --summary
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.data.sleeper import _get, get_nfl_state  # noqa: E402
from src.dynasty_genius.league_capture import load_production_league_set  # noqa: E402
from src.dynasty_genius.league_transactions import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_LEGS,
    IdentityResolver,
    TransactionStore,
    load_governed_crosswalk,
    run_transaction_capture,
)

# Same environment convention the existing Sleeper producers already use.
DEFAULT_LEAGUE_ID = "1314363401744416768"


def _league_id() -> str:
    return os.environ.get("DYNASTY_SLEEPER_LEAGUE_ID", DEFAULT_LEAGUE_ID)


def _fetch_leg(league_id: str):
    def fetch(leg: int):
        return asyncio.run(_get(f"/league/{league_id}/transactions/{leg}")) or []

    return fetch


def _season() -> str:
    state = asyncio.run(get_nfl_state())
    return str(state.get("league_season") or state.get("season"))


def _resolver() -> IdentityResolver:
    """Canonical identity comes from the governed crosswalk; the snapshot supplies
    display attributes only. Presence in Sleeper's player map is not resolution."""
    league_set = load_production_league_set()
    snapshot = json.loads(league_set.paths["snapshot.json"].read_text(encoding="utf-8"))
    return IdentityResolver.from_snapshot(
        snapshot, crosswalk_by_sleeper=load_governed_crosswalk()
    )


def _print_summary(db_path: Path) -> None:
    store = TransactionStore(db_path)
    activity = store.manager_activity()
    print(f"\nWhat every manager has actually done ({store.transaction_count()} transactions):\n")
    for bucket in sorted(activity.values(), key=lambda b: -len(b["movements"])):
        moves = bucket["movements"]
        name = bucket["display_name"] or bucket["manager_key"]
        adds = sum(1 for m in moves if m["action"] == "add")
        drops = sum(1 for m in moves if m["action"] == "drop")
        got = sum(1 for m in moves if m["action"] == "pick_acquire")
        sent = sum(1 for m in moves if m["action"] == "pick_send")
        print(
            f"  {name:<20} {len(moves):>3} moves   adds {adds:>3}  drops {drops:>3}"
            f"  picks +{got}/-{sent}"
        )
        for m in moves[:3]:
            when = (m["created_at"] or "")[:10]
            if m["asset_type"] == "pick":
                label = f"{m['pick_season']} round {m['pick_round']} pick"
            else:
                label = f"{m['player_name'] or m['player_key']} ({m['position'] or '?'})"
            print(f"      {when}  {m['action']:<13} {label}   [{m['transaction_type']}]")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-id", default=None)
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--summary", action="store_true", help="print manager activity after capture")
    args = parser.parse_args()

    league_id = args.league_id or _league_id()
    season = _season()
    status = run_transaction_capture(
        league_id=league_id,
        season=season,
        fetch_leg=_fetch_leg(league_id),
        resolver=_resolver(),
        legs=DEFAULT_LEGS,
        db_path=Path(args.db_path),
    )
    print(json.dumps(status, indent=1, sort_keys=True))
    if args.summary:
        _print_summary(Path(args.db_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
