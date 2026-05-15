#!/usr/bin/env python3.14
"""Market-leakage guard for Engine A/B training CSVs.

Checks that no training CSV contains columns that are market signals,
analyst opinions, or prohibited fields. Column patterns are derived from
the source registry (market_overlay sources) and the engine_a_contract
(PROHIBITED_COLUMNS + LEAKAGE_REGEX), so the guard stays in sync with
the taxonomy automatically.

Usage:
    # Check specific files (called by pre-commit):
    .venv/bin/python3.14 scripts/validate_training_csv.py app/data/training/foo.csv

    # Check all training CSVs:
    .venv/bin/python3.14 scripts/validate_training_csv.py --all

Exit 0 = clean. Exit 1 = violation found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dynasty_genius.models.engine_a_contract import LEAKAGE_REGEX, PROHIBITED_COLUMNS
from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

_TRAINING_DIR = Path("app/data/training")

# Derive column prefixes from market_overlay source names in the registry.
# E.g. "fantasycalc" → check for "fantasycalc_" prefix.
_MARKET_OVERLAY_PREFIXES: tuple[str, ...] = tuple(
    f"{name}_"
    for name, defn in SOURCE_REGISTRY.items()
    if "market_overlay" in defn.roles
)

_LEAKAGE_RE = re.compile(LEAKAGE_REGEX, re.IGNORECASE)


def _violations_in_header(columns: list[str]) -> list[str]:
    """Return list of offending column names found in the CSV header."""
    bad: list[str] = []
    for col in columns:
        col_lower = col.lower()
        if col in PROHIBITED_COLUMNS:
            bad.append(f"{col!r} (in PROHIBITED_COLUMNS)")
        elif _LEAKAGE_RE.search(col):
            bad.append(f"{col!r} (matches LEAKAGE_REGEX)")
        elif any(col_lower.startswith(p) for p in _MARKET_OVERLAY_PREFIXES):
            bad.append(f"{col!r} (market_overlay source prefix)")
    return bad


def validate_csv(path: Path) -> list[str]:
    """Return list of violation strings for a single CSV. Empty = clean."""
    try:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
    except (IndexError, OSError) as exc:
        return [f"Cannot read {path}: {exc}"]
    columns = [c.strip() for c in first_line.split(",")]
    return _violations_in_header(columns)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Training CSV market-leakage guard.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("files", nargs="*", type=Path, metavar="CSV",
                       help="CSV file(s) to validate (pre-commit usage).")
    group.add_argument("--all", action="store_true",
                       help=f"Validate all CSVs in {_TRAINING_DIR}.")
    args = parser.parse_args(argv)

    paths: list[Path] = (
        list(_TRAINING_DIR.glob("*.csv")) if args.all else args.files
    )
    if not paths:
        return 0

    found_any = False
    for p in paths:
        violations = validate_csv(p)
        if violations:
            found_any = True
            print(f"FAIL {p}:", file=sys.stderr)
            for v in violations:
                print(f"  {v}", file=sys.stderr)

    if found_any:
        print(
            "\nMarket-signal columns detected in training CSV. "
            "Market data must live in the presentation/overlay layer only. "
            "See docs/governance/01-north-star-architecture.md.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
