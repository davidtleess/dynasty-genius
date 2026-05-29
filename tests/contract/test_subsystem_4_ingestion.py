"""Subsystem 4 mock snapshot schema + content hash contract tests (§4.1)."""
from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from src.dynasty_genius.eval.backtest_mock_draft import (
    MockSnapshot,
    MockSnapshotMetadata,
    MockSnapshotPick,
    compute_canonical_content_hash,
    derive_snapshot_id,
)


def _pick(
    pick_no: int = 1,
    prospect_uuid: str = "cpr_00000000-0000-4000-8000-000000000001",
    note: str | None = None,
) -> dict:
    return {
        "pick_no": pick_no,
        "prospect_uuid": prospect_uuid,
        "note": note,
    }


def _metadata(content_hash: str = "abc123") -> dict:
    return {
        "source_url": "manual://synthetic/source-a/2025-v1",
        "source_label": "synthetic_source_a",
        "analyst": "davidleess",
        "mock_version": "v1",
        "published_date": "2025-04-01",
        "fetched_at": "2026-05-28T12:00:00Z",
        "content_hash": content_hash,
        "parser_version": "manual_json_v1",
        "parse_status": "complete",
        "draft_year": 2025,
    }


def _snapshot_payload(content_hash: str = "abc123") -> dict:
    return {
        "metadata": _metadata(content_hash=content_hash),
        "picks": [
            _pick(pick_no=1),
            _pick(
                pick_no=2,
                prospect_uuid="cpr_00000000-0000-4000-8000-000000000002",
                note="manual projection note",
            ),
        ],
    }


def test_mock_snapshot_schema_round_trip_from_json(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(_snapshot_payload()), encoding="utf-8")

    snapshot = MockSnapshot.model_validate_json(snapshot_path.read_text())

    assert isinstance(snapshot.metadata, MockSnapshotMetadata)
    assert isinstance(snapshot.picks[0], MockSnapshotPick)
    assert snapshot.metadata.source_url == "manual://synthetic/source-a/2025-v1"
    assert snapshot.metadata.source_label == "synthetic_source_a"
    assert snapshot.metadata.analyst == "davidleess"
    assert snapshot.metadata.mock_version == "v1"
    assert snapshot.metadata.published_date == "2025-04-01"
    assert snapshot.metadata.fetched_at == "2026-05-28T12:00:00Z"
    assert snapshot.metadata.content_hash == "abc123"
    assert snapshot.metadata.parser_version == "manual_json_v1"
    assert snapshot.metadata.parse_status == "complete"
    assert snapshot.metadata.draft_year == 2025
    assert snapshot.picks[0].pick_no == 1
    assert snapshot.picks[0].prospect_uuid == (
        "cpr_00000000-0000-4000-8000-000000000001"
    )
    assert snapshot.picks[0].note is None
    assert snapshot.picks[1].note == "manual projection note"


def test_snapshot_models_forbid_unknown_fields():
    bad = _snapshot_payload()
    bad["metadata"]["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        MockSnapshot.model_validate(bad)

    bad = _snapshot_payload()
    bad["picks"][0]["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        MockSnapshot.model_validate(bad)

    bad = _snapshot_payload()
    bad["unexpected"] = "not allowed"

    with pytest.raises(ValidationError):
        MockSnapshot.model_validate(bad)


def test_parse_status_literal_rejects_unknown_values():
    bad = _snapshot_payload()
    bad["metadata"]["parse_status"] = "trusted"

    with pytest.raises(ValidationError):
        MockSnapshot.model_validate(bad)


def test_compute_canonical_content_hash_is_deterministic_across_pick_order():
    picks_a = [
        MockSnapshotPick.model_validate(
            _pick(
                pick_no=2,
                prospect_uuid="cpr_00000000-0000-4000-8000-000000000002",
            )
        ),
        MockSnapshotPick.model_validate(_pick(pick_no=1)),
    ]
    picks_b = list(reversed(picks_a))

    content_hash_a = compute_canonical_content_hash(picks_a)
    content_hash_b = compute_canonical_content_hash(picks_b)

    canonical = "".join(
        json.dumps(
            pick.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        for pick in sorted(picks_a, key=lambda item: item.pick_no)
    )
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert content_hash_a == expected
    assert content_hash_b == expected


def test_derive_snapshot_id_is_deterministic_and_path_independent():
    metadata = MockSnapshotMetadata.model_validate(_metadata(content_hash="def456"))
    same_metadata_from_other_path = MockSnapshotMetadata.model_validate(
        _metadata(content_hash="def456")
    )

    expected = hashlib.sha256(
        "synthetic_source_a|davidleess|2025-04-01|v1|def456".encode("utf-8")
    ).hexdigest()
    assert derive_snapshot_id(metadata) == expected
    assert derive_snapshot_id(same_metadata_from_other_path) == expected
