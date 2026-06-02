"""Backtest-A input-readiness preflight CLI (spec §11.2b).

DESCRIPTIVE / DIAGNOSTIC ONLY — reports whether real-mode Backtest-A inputs are
present / valid / aligned / free of the statically-determinable §11.2 selection-bias
hard-blocks, naming exactly what is missing. It does NOT validate model predictions,
market divergence, or represent decision-grade clearance. ``ready`` is input-readiness
only (the live nflreadpy truth fetch is not probed) — never a guarantee a live run
will succeed.

Usage:
    .venv/bin/python3.14 scripts/preflight_backtest_a.py \\
        --snapshots-dir <dir> --identity-dir <dir> --draft-year 2025 \\
        [--override-draft-date 2025-04-24] [--include-untrusted] \\
        [--run-id <id> --output-root <dir>]

Exit code 0 when ready, non-zero when any check is blocked.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.dynasty_genius.eval.backtest_mock_draft import preflight_backtest_a_inputs

_DIAGNOSTIC_HEADER = "DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim."
_READINESS_DISCLAIMER = (
    "Preflight checks INPUT READINESS only (file presence, schema validation, "
    "and selection-bias gate prerequisites). It does NOT validate model "
    "predictions, market divergence, or represent decision-grade clearance."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backtest-A input-readiness preflight (diagnostic-only, read-only)."
    )
    parser.add_argument("--snapshots-dir", type=Path, required=True)
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--draft-year", type=int, required=True)
    parser.add_argument("--override-draft-date", type=str, default=None)
    parser.add_argument("--include-untrusted", action="store_true")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args(argv)

    report = preflight_backtest_a_inputs(
        args.snapshots_dir,
        args.identity_dir,
        args.draft_year,
        override_draft_date=args.override_draft_date,
        include_untrusted=args.include_untrusted,
        run_id=args.run_id,
        output_root=args.output_root,
    )

    print(_DIAGNOSTIC_HEADER)
    print(_READINESS_DISCLAIMER)
    print(json.dumps(report.model_dump(), indent=2, sort_keys=True))
    return 0 if report.ready else 1


if __name__ == "__main__":
    sys.exit(main())
