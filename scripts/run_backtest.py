#!/usr/bin/env python3.14
"""Run the Engine B walk-forward backtest for one position and persist the artifact.

Usage:
    .venv/bin/python3.14 scripts/run_backtest.py --position WR --model engine_b_v2
    .venv/bin/python3.14 scripts/run_backtest.py --all
    .venv/bin/python3.14 scripts/run_backtest.py --position QB --output-dir /custom/path
    .venv/bin/python3.14 scripts/run_backtest.py --position RB --market-store app/data/fc_snapshots.db

Output:
    Writes app/data/backtest/runs/{run_id}/backtest_result_{POSITION}.json
    Prints run_id and overall_grade to stdout.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

sys.path.append(str(Path(__file__).parent.parent))

from src.dynasty_genius.eval.backtest_harness import WalkForwardDriver
from src.dynasty_genius.eval.market_snapshot_store import MarketSnapshotStore

DEFAULT_OUTPUT_DIR = Path("app/data/backtest/runs")
VALID_POSITIONS = {"QB", "RB", "WR", "TE"}
ACTIVE_POSITIONS = ("QB", "RB", "WR")


def _current_git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    sha = result.stdout.strip()
    return sha if len(sha) == 40 else None


def _run_position(
    position: str,
    model_version: str,
    output_dir: Path,
    market_store: MarketSnapshotStore | None,
) -> tuple[str, str, Path]:
    driver = WalkForwardDriver(position=position, model_version=model_version)
    result = driver.run(market_store=market_store)
    result.git_sha = _current_git_sha()
    artifact_path = result.save(output_dir / str(result.run_id))
    return position, result.promotion_gate.overall_grade, artifact_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Engine B walk-forward backtest.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--position",
        choices=sorted(VALID_POSITIONS),
        help="Player position to backtest (QB, RB, WR, or TE).",
    )
    target.add_argument(
        "--all",
        action="store_true",
        help="Run all active promoted positions: QB, RB, WR.",
    )
    parser.add_argument(
        "--model",
        default="engine_b_v2",
        help="Model version label to record in the BacktestResult.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for run artifacts. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--market-store",
        type=Path,
        default=None,
        help="Path to fc_snapshots.db for market comparison (optional).",
    )
    args = parser.parse_args(argv)

    market_store = None
    if args.market_store is not None:
        if not args.market_store.exists():
            print(f"Error: market store not found at {args.market_store}", file=sys.stderr)
            return 1
        market_store = MarketSnapshotStore(db_path=args.market_store)

    positions = ACTIVE_POSITIONS if args.all else (args.position,)

    print("position  overall_grade       artifact", flush=True)
    print("--------  ------------------  --------", flush=True)
    for position in positions:
        print(f"Running backtest for {position}...", flush=True)
        pos, grade, artifact_path = _run_position(
            position=position,
            model_version=args.model,
            output_dir=args.output_dir,
            market_store=market_store,
        )
        print(f"{pos:<8}  {grade:<18}  {artifact_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
