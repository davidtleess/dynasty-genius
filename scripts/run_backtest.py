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
import csv
import subprocess
import sys
from pathlib import Path
from typing import Sequence

sys.path.append(str(Path(__file__).parent.parent))

from src.dynasty_genius.eval.backtest_harness import (
    IdMapUnavailableError,
    WalkForwardDriver,
)
from src.dynasty_genius.eval.backtest_report import (
    MarketComparisonEntry,
    write_market_comparison_json,
    write_prediction_log_csv,
)
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


def _load_id_map_csv(path: Path) -> dict[str, str]:
    """Load a deterministic GSIS → Sleeper id map from a DynastyProcess-style CSV.

    Requires gsis_id and sleeper_id columns (fails loud on missing columns).
    Sleeper ids are normalized to clean integer strings (e.g. "13269.0" →
    "13269"); NA/blank rows are skipped.
    """
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        missing = {"gsis_id", "sleeper_id"} - fields
        if missing:
            raise ValueError(
                "id map CSV missing required columns: " + ", ".join(sorted(missing))
            )
        id_map: dict[str, str] = {}
        for row in reader:
            gsis_id = (row.get("gsis_id") or "").strip()
            sleeper_id = (row.get("sleeper_id") or "").strip()
            if not gsis_id or gsis_id == "NA" or not sleeper_id or sleeper_id == "NA":
                continue
            try:
                sleeper_id = str(int(float(sleeper_id)))
            except ValueError:
                pass
            id_map[gsis_id] = sleeper_id
    return id_map


def _run_position(
    position: str,
    model_version: str,
    output_dir: Path,
    market_store: MarketSnapshotStore | None,
    id_map: dict[str, str] | None = None,
) -> tuple[str, str, Path]:
    driver = WalkForwardDriver(position=position, model_version=model_version)
    result = driver.run(
        market_store=market_store,
        id_map=id_map,
        emit_prediction_log=True,
        emit_market_comparison=True,
    )
    result.git_sha = _current_git_sha()
    run_dir = output_dir / str(result.run_id)
    artifact_path = result.save(run_dir)
    write_prediction_log_csv(
        getattr(driver, "prediction_rows", []),
        run_dir / f"predictions_{position}.csv",
    )
    market_entries = [
        MarketComparisonEntry.model_validate(row)
        for row in getattr(driver, "market_comparison_rows", [])
    ]
    write_market_comparison_json(
        market_entries,
        run_dir / f"market_comparison_{position}.json",
    )
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
    parser.add_argument(
        "--id-map-csv",
        type=Path,
        default=None,
        help=(
            "CSV with gsis_id and sleeper_id columns for a deterministic, "
            "network-independent market-comparison join (e.g. the verified "
            "DynastyProcess db_playerids.csv)."
        ),
    )
    args = parser.parse_args(argv)

    market_store = None
    if args.market_store is not None:
        if not args.market_store.exists():
            print(f"Error: market store not found at {args.market_store}", file=sys.stderr)
            return 1
        market_store = MarketSnapshotStore(db_path=args.market_store)

    id_map = None
    if args.id_map_csv is not None:
        if not args.id_map_csv.exists():
            print(f"Error: id map CSV not found at {args.id_map_csv}", file=sys.stderr)
            return 1
        try:
            id_map = _load_id_map_csv(args.id_map_csv)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    positions = ACTIVE_POSITIONS if args.all else (args.position,)

    print("position  overall_grade       artifact", flush=True)
    print("--------  ------------------  --------", flush=True)
    for position in positions:
        print(f"Running backtest for {position}...", flush=True)
        try:
            pos, grade, artifact_path = _run_position(
                position=position,
                model_version=args.model,
                output_dir=args.output_dir,
                market_store=market_store,
                id_map=id_map,
            )
        except IdMapUnavailableError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"{pos:<8}  {grade:<18}  {artifact_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
