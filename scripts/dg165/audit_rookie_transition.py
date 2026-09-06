#!/usr/bin/env python
"""Audit the rookie -> veteran forecast transition on the same realized target (DG-165, 2026-09-06).

Reads two FROZEN runs (every consumed byte verified against its producer's manifest) and writes a
NEW immutable run directory under --runs-root. Changes no player value; proposes no correction.
Exit code is non-zero on any refusal.

    PYTHONPATH=. .venv/bin/python scripts/dg165/audit_rookie_transition.py \\
        --rookie-run runs/20260906T195904Z/dg165_rookie_capital \\
        --veteran-run /Users/davidleess/dg-wt/DG-177/runs/20260906T195728Z/dg177_basic_horizons \\
        --experience 1 2 3 --seed 20260906 --draws 2000
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402
from src.dynasty_genius.rookie.transition_audit import (  # noqa: E402
    load_rookie_run,
    load_veteran_run,
    run_audit,
    write_audit,
)


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"  # provenance is recorded as unknown, never invented


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rookie-run", required=True, help="frozen DG-165 rookie run directory")
    ap.add_argument("--veteran-run", required=True, help="frozen DG-177 veteran run directory (read-only)")
    ap.add_argument("--experience", type=int, nargs="+", default=[1, 2, 3], help="seasons of NFL information on the veteran side")
    ap.add_argument("--seed", type=int, default=20260906)
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--runs-root", default="runs")
    args = ap.parse_args(argv)
    try:
        rookie = load_rookie_run(args.rookie_run)
        veteran = load_veteran_run(args.veteran_run)
        result = run_audit(rookie, veteran, experiences=tuple(args.experience), seed=args.seed, draws=args.draws)
    except ValueError as exc:  # a refusal: say why, write nothing
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    run_dir = create_run_dir(args.runs_root, name="dg165_transition_audit")
    write_audit(run_dir, result, rookie=rookie, veteran=veteran, seed=args.seed, draws=args.draws,
                experiences=tuple(args.experience), git_sha=git_sha())
    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
