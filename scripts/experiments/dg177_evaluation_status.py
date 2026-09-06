#!/usr/bin/env python3
"""Write a machine-readable per-horizon evaluation status BESIDE an immutable run directory.

    .venv/bin/python scripts/experiments/dg177_evaluation_status.py runs/<ts>/dg177_annual_forecasts --arm recent_production_3col
    .venv/bin/python scripts/experiments/dg177_evaluation_status.py runs/<ts>/dg177_basic_horizons

Reads results.json and historical_predictions.csv from the run, computes the status
(``eval/evaluation_status``) and writes ``<parent>/<dirname>.evaluation_status.json``. The
run directory itself is never touched; the record names the run's results sha so the pair
cannot be mismatched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval.evaluation_status import evaluation_status  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--arm", default=None, help="arm key whose rows/blocks carry the policy (annual runs)")
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve()
    results = json.loads((run_dir / "results.json").read_text())
    predictions = pd.read_csv(run_dir / "historical_predictions.csv", low_memory=False)
    historical = results["historical"]
    if args.arm is not None:
        historical = {p: {h: (arms[args.arm] if isinstance(arms, dict) and args.arm in arms else arms)
                          for h, arms in per.items()} for p, per in historical.items()}
    status = evaluation_status({"historical": historical}, predictions, arm_key=args.arm)
    record = {
        "run_dir": str(run_dir.relative_to(ROOT)) if run_dir.is_relative_to(ROOT) else str(run_dir),
        "run_id": results.get("run_id"),
        "results_sha256": hashlib.sha256((run_dir / "results.json").read_bytes()).hexdigest(),
        "historical_predictions_sha256": hashlib.sha256((run_dir / "historical_predictions.csv").read_bytes()).hexdigest(),
        "arm": args.arm,
        "written_utc": datetime.now(timezone.utc).isoformat(),
        "companion_of_immutable_run": True,
        **status,
    }
    out = run_dir.parent / f"{run_dir.name}.evaluation_status.json"
    if out.exists():
        raise FileExistsError(f"{out} exists and is never overwritten")
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"wrote {out}")
    for position, per in status["positions"].items():
        for year, rec in per.items():
            print(f"  {position} {year}: {rec['status']} · folds {rec.get('evaluated_folds', 0)} · {rec.get('baseline_improvement', '')}"
                  + (f" · ECE {rec['calibration']['ece']:.3f} slope {rec['calibration']['reliability_slope']:.2f}" if rec.get("calibration", {}).get("status") == "ok" else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
