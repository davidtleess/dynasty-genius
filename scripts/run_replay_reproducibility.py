"""Replay-reproducibility run — DG-050 (Master Proposal 3 §6.2).

Replays one sampled snapshot per capture stream through its pinned parser
version and byte-compares the result against the normalized content the store
holds, then writes a dated receipt (embedded UTC timestamp):

    app/data/ops/replay_reproducibility_latest.json
    app/data/ops/replay_reproducibility/runs/replay-<UTC>.json

READ-ONLY against every store: SQLite opens are ``mode=ro``, raw snapshots and
league artifacts are plain file reads, and no producer is invoked. Safe to run
beside the live fleet; the only writes are its own receipts under ops/.

Exit codes: 0 reproduced · 1 not_reproduced (a mismatch or error — the §6.2
guarantee failed somewhere and the receipt names where) · 2 nothing_replayed.

Callable, never self-scheduling (house rule): wiring this into launchd is a
separate decision and a separate ticket step. The CLI is launchd-shaped —
no environment assumptions, absolute default paths, named exit codes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.dynasty_genius.replay.replay_harness import (  # noqa: E402
    run_replay,
    write_receipt,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="DG-050 replay-reproducibility harness (read-only)"
    )
    parser.add_argument("--repo-root", type=Path, default=_ROOT)
    parser.add_argument(
        "--streams", nargs="*", default=None,
        help="limit to these streams (nflverse stream names, "
             "'fc_forward_capture', 'league_snapshot'); default: all",
    )
    parser.add_argument(
        "--max-raw-bytes", type=int, default=None,
        help="skip (and say so) any raw snapshot larger than this",
    )
    parser.add_argument(
        "--league-root", type=Path, default=None,
        help="league runtime root override (default <repo>/app/data/league_runtime)",
    )
    parser.add_argument(
        "--ops-root", type=Path, default=None,
        help="receipt directory override (default <repo>/app/data/ops)",
    )
    args = parser.parse_args(argv)

    receipt = run_replay(
        repo_root=args.repo_root,
        streams=set(args.streams) if args.streams else None,
        max_raw_bytes=args.max_raw_bytes,
        league_root=args.league_root,
    )
    for check in receipt["checks"]:
        keys = ("stream_season", "snapshot_id", "snapshot_date", "run_id")
        ref = next(
            (str(check["evidence"][k]) for k in keys if check["evidence"].get(k)),
            "",
        )
        print(f"REPLAY {check['stream']}/{check['check']}: "
              f"{check['status']}" + (f" ({ref})" if ref else ""))

    ops_root = args.ops_root or (args.repo_root / "app" / "data" / "ops")
    try:
        latest, dated = write_receipt(receipt, ops_root=ops_root)
    except FileExistsError as exc:
        # A same-second duplicate run collides on the 1s-granular run_id.
        # That is an environment condition, never a §6.2 verdict — exit 1 is
        # reserved for not_reproduced (pre-land review, 2026-08-28).
        print(f"RECEIPT NOT WRITTEN — {exc}", file=sys.stderr)
        print(f"verdict (unrecorded): {receipt['verdict']}  ({receipt['totals']})")
        return 2
    print(f"verdict: {receipt['verdict']}  ({receipt['totals']})")
    print(f"receipt: {latest}")
    print(f"receipt: {dated}")
    return {"reproduced": 0, "not_reproduced": 1}.get(receipt["verdict"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
