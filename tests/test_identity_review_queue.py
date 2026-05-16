"""Task 13.1.2 tests: identity review queue JSONL writer."""
from __future__ import annotations

import json

import pytest

from src.dynasty_genius.audit.identity_review_queue import (
    FuzzyCandidate,
    ReviewQueueEntry,
    ReviewQueueValidationError,
    append_review_entry,
    write_review_queue,
)


def test_review_queue_writer_appends_jsonl_entries(tmp_path):
    path = tmp_path / "identity_review_queue_test_run.jsonl"
    entry = ReviewQueueEntry(
        candidate_id="pff_te_001",
        source="pff",
        source_row_id="pff_export_2025_te.csv:42",
        name="Mason Taylor",
        position="TE",
        draft_year=2025,
        college="LSU",
        stage_reached="review_queue",
        status="PENDING",
        fuzzy_candidates=[
            FuzzyCandidate(
                player_id="mason_taylor_te_2025",
                score=0.91,
                reason="name+position candidate only; review required",
            )
        ],
    )

    append_review_entry(path, entry)
    append_review_entry(
        path,
        ReviewQueueEntry(
            candidate_id="pff_te_002",
            source="pff",
            source_row_id="pff_export_2025_te.csv:43",
            name="Unknown Tight End",
            position="TE",
            draft_year=2025,
            stage_reached="review_queue",
            status="INSUFFICIENT_DATA",
        ),
    )

    lines = path.read_text().splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["candidate_id"] == "pff_te_001"
    assert first["status"] == "PENDING"
    assert first["resolved_player_id"] is None
    assert first["fuzzy_candidates"][0]["player_id"] == "mason_taylor_te_2025"
    assert first["fuzzy_candidates"][0]["score"] == 0.91


def test_fuzzy_candidates_are_review_only_not_manual_resolution(tmp_path):
    path = tmp_path / "identity_review_queue_test_run.jsonl"
    entry = ReviewQueueEntry(
        candidate_id="pff_te_003",
        source="pff",
        source_row_id="pff_export_2025_te.csv:44",
        name="Collision Player",
        position="TE",
        draft_year=2025,
        stage_reached="review_queue",
        status="RESOLVED_MANUAL",
        resolved_player_id="collision_te_2025",
        fuzzy_candidates=[
            FuzzyCandidate(
                player_id="collision_te_2025",
                score=0.96,
                reason="high fuzzy score but still review-only",
            )
        ],
    )

    with pytest.raises(ReviewQueueValidationError, match="fuzzy candidates cannot resolve"):
        append_review_entry(path, entry)

    assert not path.exists()


def test_write_review_queue_replaces_file_with_valid_entries(tmp_path):
    path = tmp_path / "identity_review_queue_test_run.jsonl"
    path.write_text("old\n")

    entries = [
        ReviewQueueEntry(
            candidate_id="cfbd_qb_001",
            source="cfbd",
            source_row_id="cfbd_export.csv:7",
            name="Prospect One",
            position="QB",
            draft_year=2026,
            stage_reached="review_queue",
            status="PENDING",
        )
    ]

    write_review_queue(path, entries)

    lines = path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["candidate_id"] == "cfbd_qb_001"
