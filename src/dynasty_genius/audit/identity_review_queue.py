"""Identity review queue artifacts for Phase 13.1.

Fuzzy candidates are evidence for human review only. They never mark a row as
resolved, and they never make a row eligible for training materialization.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REVIEW_QUEUE_STATUSES = {
    "PENDING",
    "INSUFFICIENT_DATA",
    "REJECTED_COLLISION",
    "RESOLVED_MANUAL",
}


class ReviewQueueValidationError(ValueError):
    """Raised when a review queue entry violates the Phase 13 contract."""


@dataclasses.dataclass(frozen=True)
class FuzzyCandidate:
    player_id: str
    score: float
    reason: str

    def as_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "score": self.score,
            "reason": self.reason,
        }


@dataclasses.dataclass(frozen=True)
class ReviewQueueEntry:
    candidate_id: str
    source: str
    source_row_id: str
    name: str
    position: str
    draft_year: int | None
    stage_reached: str
    status: str
    college: str | None = None
    fuzzy_candidates: list[FuzzyCandidate] = dataclasses.field(default_factory=list)
    resolved_player_id: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    created_at: str | None = None

    def validate(self) -> None:
        if self.status not in REVIEW_QUEUE_STATUSES:
            raise ReviewQueueValidationError(f"unknown review status: {self.status}")
        required = {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "source_row_id": self.source_row_id,
            "name": self.name,
            "position": self.position,
            "stage_reached": self.stage_reached,
        }
        missing = [field for field, value in required.items() if not value]
        if missing:
            raise ReviewQueueValidationError(f"missing required review fields: {missing}")
        if self.fuzzy_candidates and self.status == "RESOLVED_MANUAL":
            raise ReviewQueueValidationError(
                "fuzzy candidates cannot resolve production identity; write a manual override instead"
            )
        if self.resolved_player_id and self.status != "RESOLVED_MANUAL":
            raise ReviewQueueValidationError(
                "resolved_player_id is allowed only after manual override approval"
            )
        if self.status == "RESOLVED_MANUAL" and not self.resolved_player_id:
            raise ReviewQueueValidationError("RESOLVED_MANUAL requires resolved_player_id")

    def as_dict(self) -> dict:
        self.validate()
        created_at = self.created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "source_row_id": self.source_row_id,
            "name": self.name,
            "position": self.position.upper(),
            "draft_year": self.draft_year,
            "college": self.college,
            "stage_reached": self.stage_reached,
            "status": self.status,
            "resolved_player_id": self.resolved_player_id,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "created_at": created_at,
            "fuzzy_candidates": [candidate.as_dict() for candidate in self.fuzzy_candidates],
        }


def append_review_entry(path: Path | str, entry: ReviewQueueEntry) -> None:
    """Append one review queue entry as JSONL."""
    target = Path(path)
    payload = entry.as_dict()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def write_review_queue(path: Path | str, entries: Iterable[ReviewQueueEntry]) -> None:
    """Replace a review queue artifact with the supplied entries."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry.as_dict(), sort_keys=True) + "\n")
