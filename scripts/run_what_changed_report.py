"""War Room #2 — operational refresh CLI for the Daily What-Changed report.

A thin, scheduler-safe wrapper over the shipped T2 emitter
(:func:`emit_daily_what_changed_report`). It resolves the production input paths,
injects a tz-aware clock, and writes the overwrite-latest report so the read-only
API (``GET /api/league/what-changed``) serves real data instead of 503.

Read-only over every input (capture stores, structural artifacts, PVO); the ONLY
write is the gitignored report. It never mutates a model/feature/PVO path and never
auto-commits. ``--preflight`` is a readiness check only: it never calls the emitter
and never writes.

Honest exit codes: a written report — INCLUDING a degraded/unavailable one — exits 0
(degraded is honest, not a failure); only a real failure (emitter exception, unusable
report path) exits 1, leaving no partial report.

Run via the project interpreter; the LaunchAgent (T2) runs it daily after the WR#1
captures land:

    .venv/bin/python3.14 scripts/run_what_changed_report.py
    .venv/bin/python3.14 scripts/run_what_changed_report.py --preflight
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# cwd-independent: resolve the repo root from THIS file (scripts/ is one level down)
# and put it on sys.path BEFORE importing the package, so a launchd run from outside
# the repo does not crash with ModuleNotFoundError (the WR#1 standalone lesson).
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.what_changed.report import (  # noqa: E402  (after sys.path bootstrap)
    emit_daily_what_changed_report,
)

# Input keys mirror the emitter's kwargs; paths are resolved against ROOT at call time
# (ROOT is monkeypatchable in tests).
_INPUT_RELATIVES = {
    "fc_db_path": "app/data/fc_forward_capture.db",
    "model_db_path": "app/data/model_forward_capture.db",
    "sleeper_snapshot_path": "app/data/league_snapshots/sleeper_universe_snapshot_latest.json",
    "team_posture_path": "app/data/valuation/team_posture_latest.json",
    "team_value_matrix_path": "app/data/valuation/team_value_matrix_latest.json",
    "league_opportunity_path": "app/data/valuation/league_opportunity_latest.json",
    "roster_cut_report_path": "app/data/valuation/roster_cut_report_latest.json",
}
_REPORT_RELATIVE = "app/data/what_changed/what_changed_latest_report.json"
_TOP_N = 25


def _resolve_inputs() -> dict[str, Path]:
    return {key: ROOT / rel for key, rel in _INPUT_RELATIVES.items()}


def _resolve_report_path() -> Path:
    return ROOT / _REPORT_RELATIVE


def _nearest_existing_ancestor(path: Path) -> Path:
    for ancestor in (path, *path.parents):
        if ancestor.exists():
            return ancestor
    return path


def _report_parent_usable(report_path: Path) -> bool:
    """True if the report parent is (or can become) a writable directory."""
    parent = report_path.parent
    if parent.exists():
        return parent.is_dir()
    ancestor = _nearest_existing_ancestor(parent)
    return ancestor.is_dir() and os.access(ancestor, os.W_OK)


def _preflight(inputs: dict[str, Path], report_path: Path) -> dict:
    """Readiness check ONLY — no emitter call, no write."""
    input_status = {
        key: {"exists": path.exists(), "path": str(path)}
        for key, path in inputs.items()
    }
    failures: list[str] = []
    if not any(status["exists"] for status in input_status.values()):
        failures.append("no_usable_inputs")
    if not _report_parent_usable(report_path):
        failures.append("report_parent_unusable")
    return {
        "preflight": True,
        "ready": not failures,
        "report_path": str(report_path),
        "inputs": input_status,
        "readiness_failures": failures,
    }


def _run(inputs: dict[str, Path], report_path: Path) -> int:
    try:
        report = emit_daily_what_changed_report(
            fc_db_path=inputs["fc_db_path"],
            model_db_path=inputs["model_db_path"],
            sleeper_snapshot_path=inputs["sleeper_snapshot_path"],
            team_posture_path=inputs["team_posture_path"],
            team_value_matrix_path=inputs["team_value_matrix_path"],
            league_opportunity_path=inputs["league_opportunity_path"],
            roster_cut_report_path=inputs["roster_cut_report_path"],
            report_path=report_path,
            now_fn=lambda: datetime.now(timezone.utc),
            top_n=_TOP_N,
        )
    except Exception as exc:  # real failure -> nonzero, emitter leaves no partial report
        print(f"what-changed report failed: {exc}", file=sys.stderr)
        return 1

    daily_diff = report.get("daily_diff", {})
    summary = {
        "overall_status": report.get("overall_status"),
        "market_status": daily_diff.get("market", {}).get("status"),
        "model_status": daily_diff.get("model", {}).get("status"),
        "structural_status": report.get("structural_context", {}).get("status"),
        "report_path": str(report_path),
    }
    print(json.dumps(summary))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the Daily What-Changed report (read-only over inputs)."
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="readiness check only; never calls the emitter and never writes",
    )
    args = parser.parse_args(argv)

    inputs = _resolve_inputs()
    report_path = _resolve_report_path()

    if args.preflight:
        result = _preflight(inputs, report_path)
        print(json.dumps(result))
        return 0 if result["ready"] else 1

    return _run(inputs, report_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
