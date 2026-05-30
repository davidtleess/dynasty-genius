#!/usr/bin/env python3
"""Subsystem 4 — Backtest-A runner CLI (spec §5.9).

Usage:
    .venv/bin/python3.14 scripts/run_backtest_a.py \\
        --snapshots-dir app/data/backtest/mock_draft/snapshots \\
        --identity-dir app/data/identity \\
        --draft-year 2025 \\
        --run-id backtest_a_<run_timestamp>

Synthetic / fixture runs require BOTH --override-draft-date and --override-reason
(loud, auditable override; §5.6) and are recorded as data_mode="synthetic".

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md §5.9
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_project_interpreter() -> None:
    """Re-exec under the project venv if the current interpreter lacks deps.

    The CLI may be invoked directly (shebang -> some system python3). If that
    interpreter has no project dependencies, re-exec under the repo-relative
    ``.venv`` python (portable; no hardcoded absolute path). NOTE: the venv python
    is often a SYMLINK to the system python, so we must NOT compare resolved paths
    (they would look equal) — venv site-packages come from launching the unresolved
    ``.venv/bin/python3.14`` path. An env-var sentinel prevents a re-exec loop.
    """
    try:
        import pydantic  # noqa: F401  (probe only)

        return
    except ModuleNotFoundError:
        pass
    if os.environ.get("_S4_RUNNER_REEXEC") == "1":
        return  # already re-exec'd once — let the real ImportError surface
    venv_python = _REPO_ROOT / ".venv" / "bin" / "python3.14"
    if venv_python.exists():
        os.execve(
            str(venv_python),
            [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]],
            {**os.environ, "_S4_RUNNER_REEXEC": "1"},
        )


_ensure_project_interpreter()
sys.path.insert(0, str(_REPO_ROOT))

from src.dynasty_genius.eval.backtest_mock_draft import (  # noqa: E402
    BacktestAInputError,
    run_backtest_a,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run Backtest A (mock-draft consensus vs realized NFL draft capital)."
        )
    )
    parser.add_argument("--snapshots-dir", required=True, type=Path)
    parser.add_argument("--identity-dir", required=True, type=Path)
    parser.add_argument("--draft-year", required=True, type=int)
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
    args = parser.parse_args(argv)

    try:
        result = run_backtest_a(
            snapshots_dir=args.snapshots_dir,
            identity_dir=args.identity_dir,
            draft_year=args.draft_year,
            run_id=args.run_id,
            output_root=args.output_root,
            override_draft_date=args.override_draft_date,
            override_reason=args.override_reason,
            include_untrusted=args.include_untrusted,
            dispersion_threshold=args.dispersion_threshold,
        )
    except BacktestAInputError as exc:
        print(f"schema/ingestion error: {exc}", file=sys.stderr)
        return 1

    print(
        f"backtest_a run {result.metadata['run_id']} complete "
        f"(data_mode={result.metadata['data_mode']})",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
