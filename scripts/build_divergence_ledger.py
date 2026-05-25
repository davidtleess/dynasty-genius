#!/usr/bin/env python3.14
"""Build the divergence ledger for one or all positions.

Joins the latest BacktestResult with its market_comparison_{POSITION}.json
artifact to produce a passive rank-disagreement ledger. No model calls,
no new predictions — read-only relative to all training artifacts.

Output: app/data/backtest/divergence_ledger_{POSITION}.json

Usage:
    .venv/bin/python3.14 scripts/build_divergence_ledger.py --position WR
    .venv/bin/python3.14 scripts/build_divergence_ledger.py --all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))

from src.dynasty_genius.eval.backtest_report import DivergenceLedgerEntry

RUNS_DIR = Path("app/data/backtest/runs")
OUTPUT_DIR = Path("app/data/backtest")
VALID_POSITIONS = ("QB", "RB", "WR", "TE")


def _find_latest(position: str, runs_dir: Path) -> Optional[Path]:
    candidates = list(runs_dir.glob(f"*/backtest_result_{position}.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _flagged_direction(rank_delta: int) -> Optional[str]:
    if rank_delta > 0:
        return "model_higher"
    if rank_delta < 0:
        return "model_lower"
    return None


def build_divergence_ledger(
    position: str,
    runs_dir: Path = RUNS_DIR,
    output_dir: Path = OUTPUT_DIR,
) -> list[DivergenceLedgerEntry]:
    """Build and write the divergence ledger for one position.

    Reads the latest BacktestResult to confirm the run exists, then loads
    market_comparison_{POSITION}.json from the same run directory. For each
    entry where both model_rank and fc_rank are present, computes rank_delta
    and flagged_direction.

    rank_delta = fc_rank - engine_b_rank
      positive → model ranks player higher (model is more bullish than market)
      negative → model ranks player lower
      zero     → exact agreement (flagged_direction = None)

    Raises:
        FileNotFoundError: if no backtest_result_{position}.json exists under runs_dir.

    Returns:
        List of DivergenceLedgerEntry objects (may be empty if no market data).
    """
    result_path = _find_latest(position, runs_dir)
    if result_path is None:
        raise FileNotFoundError(
            f"No backtest_result_{position}.json found under {runs_dir}. "
            "Run scripts/run_backtest.py first."
        )

    run_dir = result_path.parent
    market_path = run_dir / f"market_comparison_{position}.json"

    if not market_path.exists():
        entries: list[DivergenceLedgerEntry] = []
    else:
        raw = json.loads(market_path.read_text(encoding="utf-8"))
        entries = []
        for row in raw:
            model_rank = row.get("model_rank")
            fc_rank = row.get("fc_rank")
            if model_rank is None or fc_rank is None:
                continue
            rank_delta = fc_rank - model_rank
            entries.append(DivergenceLedgerEntry(
                player_id=str(row["player_id"]),
                sleeper_id=row.get("sleeper_id"),
                position=position,
                feature_season=int(row["feature_season"]),
                engine_b_pred_ppg=float(row["predicted_ppg"]),
                engine_b_rank=int(model_rank),
                fc_value=int(row["fc_value"]) if row.get("fc_value") is not None else None,
                fc_rank=int(fc_rank),
                snapshot_date=row.get("snapshot_date"),
                realized_avg_ppg_t1_t2=(
                    float(row["realized_ppg"]) if row.get("realized_ppg") is not None else None
                ),
                realized_rank=(
                    int(row["realized_rank"]) if row.get("realized_rank") is not None else None
                ),
                rank_delta=rank_delta,
                flagged_direction=_flagged_direction(rank_delta),
            ))

    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / f"divergence_ledger_{position}.json"
    payload = [
        e.model_dump(mode="json") if hasattr(e, "model_dump") else json.loads(e.json())
        for e in entries
    ]
    ledger_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    return entries


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build divergence ledger artifact.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--position", choices=list(VALID_POSITIONS))
    target.add_argument("--all", action="store_true")
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    positions = VALID_POSITIONS if args.all else (args.position,)
    for pos in positions:
        print(f"Building divergence ledger for {pos}...", flush=True)
        try:
            entries = build_divergence_ledger(
                pos, runs_dir=args.runs_dir, output_dir=args.output_dir
            )
            n_higher = sum(1 for e in entries if e.flagged_direction == "model_higher")
            n_lower = sum(1 for e in entries if e.flagged_direction == "model_lower")
            n_unmatched = sum(1 for e in entries if e.fc_rank is None)
            print(
                f"  {pos}: n_entries={len(entries)}, "
                f"model_higher={n_higher}, model_lower={n_lower}, "
                f"unmatched={n_unmatched}"
            )
        except FileNotFoundError as e:
            print(f"  {pos}: SKIPPED — {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
