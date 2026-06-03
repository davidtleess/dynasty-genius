"""S3 Task-10A Task-5 — deterministic reviewed batch confirmation of the clean 2025 cohort.

David authorized Option B: batch-confirm the clean provisional rows, and manually
adjudicate the 7 similar-named surfaced-candidate rows separately. This runner confirms
every provisional registry row whose ``prospect_uuid`` is NOT in the manually-adjudicated
flagged set, routing each through the blessed ``promote_review_candidate`` write path
(decision=confirm, target_kind=self) so every confirmation lands a real promotion-log
event (an audit trail, never a hand-rolled status edit).

Legitimacy guards (fail-closed BEFORE any write):
- the clean count must equal ``expected_count`` (refuse a surprise cohort size), and
- every clean target must carry a non-null ``cfbd_athlete_id`` (no identity-less confirm).

The 7 flagged rows are excluded and remain ``provisional`` for David's manual confirm.

CLI usage:
    .venv/bin/python3.14 scripts/batch_confirm_2025_clean_prospects.py \\
        --identity-dir app/data/identity \\
        --expected-count 79 \\
        --reviewer davidleess
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    PromotionDecision,
    load_registry,
    promote_review_candidate,
)

# The 7 surfaced-candidate rows adjudicated by David as DISTINCT similar-named players
# (confirm-both, no merges) — excluded from the batch and confirmed manually so their
# review-queue edges close. UUIDs paired with their originating review_id(s) for audit.
FLAGGED_2025_SURFACED_UUIDS: frozenset[str] = frozenset({
    "cpr_75165863-44c7-4999-9767-9996bd28e6f7",  # Jaylin Noel   (review_0001)
    "cpr_d3a5dcc7-e46a-49ae-badb-0ceb21935849",  # Savion Williams (review_0002)
    "cpr_0c3f2dec-f2a7-4d9f-abc2-6657d245e833",  # Trevor Etienne (review_0003)
    "cpr_4a90c532-9c61-44fb-b9c0-fcd1ceb3ee31",  # Jaylin Lane    (review_0004 + review_0005)
    "cpr_3ffc600c-88c6-4652-aaab-d4cbaea98914",  # Jalen Royals   (review_0006)
    "cpr_237e67ba-2aca-40fc-ab66-5a0011193143",  # Riley Leonard  (review_0007)
    "cpr_1f40c8b6-20f2-410b-a524-95a57c87681a",  # Cam Miller     (review_0008)
})


@dataclass(frozen=True)
class BatchConfirmResult:
    exit_code: int
    confirmed_count: int
    skipped_flagged_count: int


def batch_confirm_clean_prospects(
    *,
    identity_dir: Path,
    flagged_uuids: set[str] | frozenset[str],
    expected_count: int,
    reviewer_id: str,
) -> BatchConfirmResult:
    """Confirm the clean (non-flagged) cohort through the blessed promotion path.

    Fail-closed (raises ``ValueError``, NO writes) when the clean count != expected_count
    or any clean target lacks a ``cfbd_athlete_id``. Idempotent: rows already confirmed on
    a prior run are skipped, so a rerun appends no new events.
    """
    registry = load_registry(identity_dir / "college_prospect_registry.json")
    flagged = set(flagged_uuids)

    clean = [e for e in registry.entries.values() if e.prospect_uuid not in flagged]
    skipped_flagged_count = sum(
        1 for e in registry.entries.values() if e.prospect_uuid in flagged
    )

    if len(clean) != expected_count:
        raise ValueError(
            f"expected {expected_count} clean provisional rows, found {len(clean)} "
            f"(check the flagged set / fixture cohort before confirming)"
        )
    missing = [e.prospect_uuid for e in clean if not e.cfbd_athlete_id]
    if missing:
        raise ValueError(
            f"refusing batch confirm: {len(missing)} clean row(s) missing cfbd_athlete_id "
            f"(first: {missing[0]})"
        )
    # Fail closed on any clean row in an unexpected status. provisional -> confirm below;
    # confirmed -> idempotent skip. Anything else (e.g. deprecated) signals a corrupted
    # cohort that would otherwise satisfy expected_count while silently skipping rows.
    bad_status = [
        e.prospect_uuid
        for e in clean
        if e.verification_status not in {"provisional", "confirmed"}
    ]
    if bad_status:
        raise ValueError(
            f"refusing batch confirm: {len(bad_status)} clean row(s) in an unexpected "
            f"verification_status (expected provisional|confirmed; first: {bad_status[0]})"
        )

    confirmed_count = 0
    for entry in clean:
        if entry.verification_status != "provisional":
            continue  # idempotent rerun — already confirmed
        result = promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(
                kind="confirm", target_kind="self", target=entry.prospect_uuid
            ),
            identity_dir=identity_dir,
            reviewer_id=reviewer_id,
            evidence=None,
            note="Task-5 deterministic reviewed batch confirm (clean cohort; David-authorized Option B).",
        )
        if result.exit_code != 0:
            return BatchConfirmResult(
                exit_code=result.exit_code,
                confirmed_count=confirmed_count,
                skipped_flagged_count=skipped_flagged_count,
            )
        confirmed_count += 1

    return BatchConfirmResult(
        exit_code=0,
        confirmed_count=confirmed_count,
        skipped_flagged_count=skipped_flagged_count,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch-confirm the clean 2025 prospect cohort (S3 Task-5, Option B)."
    )
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--reviewer", type=str, default="davidleess")
    args = parser.parse_args(argv)

    result = batch_confirm_clean_prospects(
        identity_dir=args.identity_dir,
        flagged_uuids=FLAGGED_2025_SURFACED_UUIDS,
        expected_count=args.expected_count,
        reviewer_id=args.reviewer,
    )
    print(
        f"batch confirm complete -> exit_code={result.exit_code} "
        f"confirmed={result.confirmed_count} skipped_flagged={result.skipped_flagged_count}"
    )
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
