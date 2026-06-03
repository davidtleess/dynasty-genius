"""Subsystem 3 — review-candidate promotion CLI (the only blessed write path).

Usage:
    .venv/bin/python3.14 scripts/promote_review_candidate.py \\
        --identity-dir app/data/identity \\
        --target <prospect_uuid> \\
        --decision confirm \\
        [--target-kind self|existing] \\
        [--survivor <uuid>]         # for confirm-existing or merge_into
        [--new-full-name "..."]     # for split
        [--new-position WR]         # for split
        [--new-position-group WR]
        [--evidence "..."]          # required for merge_into and split
        [--note "..."]
        [--reviewer davidleess]
        [--review-id <id>]

Spec: docs/superpowers/specs/2026-05-28-subsystem-3-prospect-identity-substrate-design.md §6
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    PromotionDecision,
    promote_review_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a review candidate.")
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--target", type=str, required=True)
    parser.add_argument(
        "--decision",
        type=str,
        required=True,
        choices=["confirm", "reject", "defer", "merge_into", "split"],
    )
    parser.add_argument(
        "--target-kind",
        type=str,
        choices=["self", "existing"],
        default="self",
    )
    parser.add_argument("--review-id", type=str, default=None)
    parser.add_argument("--survivor", type=str, default=None)
    parser.add_argument("--new-full-name", type=str, default=None)
    parser.add_argument("--new-position", type=str, default=None)
    parser.add_argument("--new-position-group", type=str, default=None)
    parser.add_argument("--evidence", type=str, default=None)
    parser.add_argument("--note", type=str, default=None)
    parser.add_argument("--reviewer", type=str, default="davidleess")
    args = parser.parse_args(argv)

    decision = PromotionDecision(
        kind=args.decision,
        target_kind=args.target_kind,
        target=args.target,
        survivor=args.survivor,
        new_full_name=args.new_full_name,
        new_position=args.new_position,
        new_position_group=args.new_position_group,
    )
    result = promote_review_candidate(
        review_id=args.review_id,
        decision=decision,
        identity_dir=args.identity_dir,
        reviewer_id=args.reviewer,
        evidence=args.evidence,
        note=args.note,
    )
    print(f"exit_code={result.exit_code} event_id={result.event_id}", file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
