#!/usr/bin/env python3
"""Subsystem 4 — Backtest-B v1 always-abstain stub CLI (spec §6.1).

Backtest B is deliberately excluded in v1 (gated on Backtest A clearance by
round/position bucket). This CLI mirrors run_backtest_a's flags for symmetric UX,
plus --upstream-run, and writes a single abstain report at
<output_root>/<run_id>/backtest_b_abstain.json. It always exits 0 and never runs
ingestion. A future agent implementing real Backtest B must explicitly flip the
contract lock test.

Usage:
    .venv/bin/python3.14 scripts/run_backtest_b.py --run-id b_<ts> \\
        --upstream-run backtest_a_<ts>

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md §6.1
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_project_interpreter() -> None:
    """Re-exec under the project venv if the current interpreter lacks deps.

    The venv python is often a SYMLINK to the system python, so we must NOT compare
    resolved paths — venv site-packages come from launching the unresolved
    ``.venv/bin/python3.14`` path. An env-var sentinel prevents a re-exec loop.
    """
    try:
        import pydantic  # noqa: F401  (probe only)

        return
    except ModuleNotFoundError:
        pass
    if os.environ.get("_S4_RUNNER_B_REEXEC") == "1":
        return  # already re-exec'd once — let the real ImportError surface
    venv_python = _REPO_ROOT / ".venv" / "bin" / "python3.14"
    if venv_python.exists():
        os.execve(
            str(venv_python),
            [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
            {**os.environ, "_S4_RUNNER_B_REEXEC": "1"},
        )


_ensure_project_interpreter()
sys.path.insert(0, str(_REPO_ROOT))

from src.dynasty_genius.eval.backtest_mock_draft import (  # noqa: E402
    write_backtest_b_abstain_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Backtest B (v1 always-abstain stub; gated on Backtest A)."
    )
    # Backtest-A flags, accepted for symmetric UX (the stub does not ingest).
    parser.add_argument("--snapshots-dir", type=Path)
    parser.add_argument("--identity-dir", type=Path)
    parser.add_argument("--draft-year", type=int)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("app/data/backtest/mock_draft/runs"),
    )
    parser.add_argument("--override-draft-date", default=None)
    parser.add_argument("--override-reason", default=None)
    parser.add_argument("--include-untrusted", action="store_true")
    parser.add_argument("--dispersion-threshold", type=float, default=6)
    # Backtest-B specific: reference an upstream Backtest-A run.
    parser.add_argument("--upstream-run", default=None)
    args = parser.parse_args(argv)

    payload = write_backtest_b_abstain_report(
        run_id=args.run_id,
        output_root=args.output_root,
        upstream_run_id=args.upstream_run,
    )
    print(
        f"backtest_b abstain: {payload['status']} (run {args.run_id})",
        file=sys.stdout,
    )
    return payload["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
