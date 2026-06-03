"""Subsystem 3 — manual-fixture ingestion CLI.

Usage:
    .venv/bin/python3.14 scripts/ingest_college_prospect_fixture.py \\
        --fixture resources/college_prospect_fixture_2027.json \\
        --identity-dir app/data/identity \\
        --run-id manual_2027_<run_timestamp>

Spec: docs/superpowers/specs/2026-05-28-subsystem-3-prospect-identity-substrate-design.md §6.5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the repo root is importable when invoked directly from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.identity.college_prospect_identity import ingest_fixture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest the college prospect fixture (spec §6.5).")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    args = parser.parse_args(argv)

    result = ingest_fixture(
        fixture_path=args.fixture,
        identity_dir=args.identity_dir,
        run_id=args.run_id,
    )
    print(
        f"run_id={result.run_id} exit_code={result.exit_code} coverage={result.coverage}",
        file=sys.stderr,
    )
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
