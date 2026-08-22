"""Capture David's league transaction history into the durable store.

Callable by hand or by a scheduler that does not yet exist. This script installs nothing,
schedules nothing, and touches no other producer — adding a LaunchAgent is a separate
decision and a separate word.

**Every season by default.** One season of transactions cannot describe a manager, so the
capture walks Sleeper's ``previous_league_id`` chain back to the league's first season.
``--current-season-only`` restricts it to the live league.

    .venv/bin/python3.14 scripts/run_league_transaction_capture.py
    .venv/bin/python3.14 scripts/run_league_transaction_capture.py --summary
    .venv/bin/python3.14 scripts/run_league_transaction_capture.py --current-season-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.data.sleeper import _get, get_nfl_state  # noqa: E402
from src.dynasty_genius.league_capture import load_production_league_set  # noqa: E402
from src.dynasty_genius.league_transactions import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_LEGS,
    DEFAULT_RAW_ROOT,
    IdentityResolver,
    LeagueChainLink,
    TransactionStore,
    load_governed_crosswalk,
    run_chain_transaction_capture,
    run_transaction_capture,
)


def _manager_counts(status: Mapping[str, Any]) -> list[int]:
    """Every league this run actually contacted, by how many managers it reported.

    Two status shapes, because there are two capture modes: the chain nests one coverage
    block per season under `chain_coverage.by_season`, while `--current-season-only`
    reports a single league at the top level.
    """
    by_season = (status.get("chain_coverage") or {}).get("by_season")
    if by_season is not None:
        return [int(block.get("managers_total") or 0) for block in by_season.values()]
    if "managers_total" in status:
        return [int(status.get("managers_total") or 0)]
    return []


def capture_is_healthy(status: Mapping[str, Any]) -> bool:
    """0 = healthy, 1 = anything else. SR-09's dependency edges read this as a boolean.

    `status == "ok"` is NECESSARY BUT NOT SUFFICIENT, and that is the whole point of this
    function. Measured live 2026-08-22: pointing the runner at `--league-id 0` — a league that
    does not exist — returns `status: "ok"` with `managers_total: 0`, zero transactions and all
    eighteen legs empty. The house one-liner
    (`return 0 if report.get("status") == "ok" else 1`) would still exit 0 there, so SR-07's own
    verification block could never pass. The capture's self-assessment reports that the MECHANICS
    ran, not that it reached anything.

    **The discriminator is managers, never transaction count.** A real league always has managers
    even in a week with no moves — David's reports 12/12/12/11 across the four chain seasons — so
    zero managers means we did not reach a league. Transaction count would have flagged the
    entirely legitimate 2026-08-05..08-21 quiet stretch as a failure, and an alert that cries wolf
    every off-season is one nobody reads by September.
    """
    if status.get("status") != "ok":
        return False
    # A chain that walked only part of its seasons is a PARTIAL, and a partial must never
    # exit 0 silently (SR-07 step 3). Absent on the single-season path, which walks no chain.
    if status.get("chain_complete") is False:
        return False
    counts = _manager_counts(status)
    return bool(counts) and all(count > 0 for count in counts)


def resolve_raw_root(db_path: Path | str, raw_root: Path | str | None) -> Path:
    """Where the status marker and raw snapshots go — beside the database they describe.

    `raw_root` carries BOTH `transaction_capture_status_latest.json` and the `raw/` snapshot
    directory, and the runner never used to pass it, so `--db-path` redirected the store while
    the paperwork kept landing in production. On 2026-08-22 running SR-07's own verification
    command overwrote the real morning marker with a league-0 result and left two junk raw files
    in `app/data/league_transactions/raw/`. Any agent following the ticket verbatim does the same.

    A redirected database takes its paperwork with it: point `--db-path` somewhere and the whole
    run is sandboxed. The default path is unchanged, so the 06:30 job — which passes no flags —
    still writes exactly where it always has.
    """
    if raw_root is not None:
        return Path(raw_root)
    if Path(db_path) == Path(DEFAULT_DB_PATH):
        return Path(DEFAULT_RAW_ROOT)
    return Path(db_path).parent

# Same environment convention the existing Sleeper producers already use.
DEFAULT_LEAGUE_ID = "1314363401744416768"


def _league_id() -> str:
    return os.environ.get("DYNASTY_SLEEPER_LEAGUE_ID", DEFAULT_LEAGUE_ID)


def _fetch_leg(league_id: str):
    def fetch(leg: int):
        return asyncio.run(_get(f"/league/{league_id}/transactions/{leg}")) or []

    return fetch


def _fetch_chain_leg(league_id: str, leg: int):
    return asyncio.run(_get(f"/league/{league_id}/transactions/{leg}")) or []


def _fetch_league(league_id: str):
    return asyncio.run(_get(f"/league/{league_id}"))


def _season() -> str:
    state = asyncio.run(get_nfl_state())
    return str(state.get("league_season") or state.get("season"))


def _base_resolver() -> IdentityResolver:
    """Canonical identity comes from the governed crosswalk; the snapshot supplies
    display attributes only. Presence in Sleeper's player map is not resolution.

    The player universe and the crosswalk are season-independent, so this is built once
    and re-pointed per season at that season's own manager map.
    """
    league_set = load_production_league_set()
    snapshot = json.loads(league_set.paths["snapshot.json"].read_text(encoding="utf-8"))
    return IdentityResolver.from_snapshot(
        snapshot, crosswalk_by_sleeper=load_governed_crosswalk()
    )


def _resolver() -> IdentityResolver:
    return _base_resolver()


def _season_resolver_factory(base: IdentityResolver):
    """A resolver per league-season, built from THAT season's rosters and users.

    Sleeper reissues ``roster_id`` 1..12 every season and the slot changes hands: on
    David's own chain, rosters 2, 3 and 11 have different owners in earlier seasons than
    they do in 2026. Reusing one season's manager map would file a departed manager's moves
    under whoever later held their slot — silently, and with a confident name attached.
    """

    def build(link: LeagueChainLink) -> IdentityResolver:
        rosters = asyncio.run(_get(f"/league/{link.league_id}/rosters")) or []
        users = asyncio.run(_get(f"/league/{link.league_id}/users")) or []
        return base.with_managers(rosters=rosters, users=users)

    return build


def _print_summary(db_path: Path) -> None:
    store = TransactionStore(db_path)
    seasons = store.seasons()
    if seasons:
        print("\nSeasons in the store:\n")
        for row in seasons:
            coverage = row.get("coverage") or {}
            unresolved = coverage.get("players_not_canonically_identified")
            print(
                f"  {row['season']}  league {row['league_id']}  {row['status']:<6} "
                f"{row['transactions_total'] or 0:>4} txns  "
                f"{row['movements_total'] or 0:>4} movements  "
                f"players not canonically identified: {unresolved}"
            )
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
    parser.add_argument(
        "--raw-root",
        default=None,
        help="where the status marker and raw snapshots go. Defaults to production for the "
             "default --db-path, and BESIDE the database otherwise, so redirecting the store "
             "sandboxes the whole run rather than half of it.",
    )
    parser.add_argument("--summary", action="store_true", help="print manager activity after capture")
    parser.add_argument(
        "--current-season-only",
        action="store_true",
        help="capture only the live league, skipping the previous_league_id chain",
    )
    args = parser.parse_args()

    league_id = args.league_id or _league_id()
    raw_root = resolve_raw_root(args.db_path, args.raw_root)
    if args.current_season_only:
        status = run_transaction_capture(
            league_id=league_id,
            season=_season(),
            fetch_leg=_fetch_leg(league_id),
            resolver=_resolver(),
            legs=DEFAULT_LEGS,
            db_path=Path(args.db_path),
            raw_root=raw_root,
        )
    else:
        status = run_chain_transaction_capture(
            league_id=league_id,
            fetch_league=_fetch_league,
            fetch_leg=_fetch_chain_leg,
            build_resolver=_season_resolver_factory(_base_resolver()),
            legs=DEFAULT_LEGS,
            db_path=Path(args.db_path),
            raw_root=raw_root,
        )
    print(json.dumps(status, indent=1, sort_keys=True))
    if args.summary:
        _print_summary(Path(args.db_path))
    return 0 if capture_is_healthy(status) else 1


if __name__ == "__main__":
    raise SystemExit(main())
