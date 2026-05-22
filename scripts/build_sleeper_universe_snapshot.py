"""Build Phase 17.1 Sleeper universe snapshot and coverage artifacts."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app.data.sleeper import (  # noqa: E402
    get_all_players,
    get_draft,
    get_draft_picks,
    get_league,
    get_league_drafts,
    get_nfl_state,
    get_rosters,
    get_traded_picks,
    get_users,
)
from src.dynasty_genius.sleeper_universe import (  # noqa: E402
    build_universe_snapshot,
    write_snapshot_artifacts,
)

DEFAULT_OUTPUT_DIR = ROOT / "app" / "data" / "league_snapshots"
LEAGUE_CONTEXT_PATH = ROOT / "resources" / "david_league_context.json"


def _load_david_roster_id() -> int | None:
    if not LEAGUE_CONTEXT_PATH.exists():
        return None
    data = json.loads(LEAGUE_CONTEXT_PATH.read_text())
    roster_id = data.get("david_roster_id")
    return int(roster_id) if roster_id is not None else None


async def _latest_draft_id(league_id: str) -> str | None:
    draft_id = os.environ.get("DYNASTY_SLEEPER_DRAFT_ID")
    if draft_id:
        return draft_id
    drafts = await get_league_drafts(league_id)
    if not drafts:
        return None
    drafts.sort(key=lambda item: item.get("created", 0), reverse=True)
    return str(drafts[0]["draft_id"])


async def build_snapshot() -> dict:
    league_id = os.environ.get("DYNASTY_SLEEPER_LEAGUE_ID", "1314363401744416768")
    draft_id = await _latest_draft_id(league_id)
    league, rosters, users, traded_picks, players, nfl_state = await asyncio.gather(
        get_league(league_id),
        get_rosters(league_id),
        get_users(league_id),
        get_traded_picks(league_id),
        get_all_players(),
        get_nfl_state(),
    )
    draft_state = {"draft_id": draft_id}
    draft_picks = []
    if draft_id:
        draft_state, draft_picks = await asyncio.gather(
            get_draft(draft_id),
            get_draft_picks(draft_id),
        )

    captured_at = datetime.now(timezone.utc).isoformat()
    snapshot = build_universe_snapshot(
        league_id=league_id,
        league=league,
        players=players,
        rosters=rosters,
        users=users,
        traded_picks=traded_picks,
        draft_state={**draft_state, "nfl_state": nfl_state},
        draft_picks=draft_picks,
        captured_at=captured_at,
        david_roster_id=_load_david_roster_id(),
    )
    return snapshot


async def main() -> None:
    snapshot = await build_snapshot()
    run_id = datetime.now(timezone.utc).strftime("phase17-%Y%m%dT%H%M%SZ")
    paths = write_snapshot_artifacts(snapshot, output_dir=DEFAULT_OUTPUT_DIR, run_id=run_id)
    print(f"Wrote Phase 17.1 Sleeper universe snapshot: {paths['snapshot']}")
    print(f"Wrote Phase 17.1 coverage report: {paths['coverage']}")


if __name__ == "__main__":
    asyncio.run(main())
