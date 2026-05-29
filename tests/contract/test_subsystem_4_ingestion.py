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
    NormalizedPick,
    compute_canonical_content_hash,
    derive_snapshot_id,
    ingest_snapshots,
)
from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
    normalize_name,
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


def _registry_entry(
    uuid: str,
    *,
    status: str = "confirmed",
    draft_class: int = 2025,
    merged_into: str | None = None,
) -> RegistryEntry:
    normalized_name = normalize_name(f"Prospect {uuid[-4:]}")
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,
        match_key=compute_match_key(
            normalized_name=normalized_name,
            position_group="WR",
            draft_class=draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid[-12:]}",
                decision="confirm",
                after_status=status,
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=merged_into,
        reviewer_id="davidleess",
        reviewer_metadata={},
        raw_name=f"Prospect {uuid[-4:]}",
        normalized_name=normalized_name,
        full_name=f"Prospect {uuid[-4:]}",
        position="WR",
        position_group="WR",
        draft_class=draft_class,
        current_school="Texas",
        prior_schools=[],
        cfbd_athlete_id=None,
        cfb_player_id=None,
        pfr_id=None,
        gsis_id=None,
        sleeper_id=None,
        source="manual_fixture",
        source_record_id=f"fixture_{uuid[-12:]}",
        source_snapshot_id="fixture_2025_v1",
        id_provenance={
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        notes=None,
    )


def _registry(*entries: RegistryEntry) -> CollegeProspectRegistry:
    return CollegeProspectRegistry(
        entries={entry.prospect_uuid: entry for entry in entries}
    )


def _snapshot_payload_for(
    picks: list[dict],
    *,
    source_label: str = "synthetic_source_a",
    analyst: str | None = "davidleess",
    mock_version: str = "v1",
    published_date: str = "2025-04-01",
    parse_status: str = "complete",
) -> dict:
    pick_models = [MockSnapshotPick.model_validate(pick) for pick in picks]
    content_hash = compute_canonical_content_hash(pick_models)
    return {
        "metadata": {
            **_metadata(content_hash=content_hash),
            "source_label": source_label,
            "analyst": analyst,
            "mock_version": mock_version,
            "published_date": published_date,
            "parse_status": parse_status,
        },
        "picks": picks,
    }


def _write_snapshot(
    snapshots_dir,
    filename: str,
    picks: list[dict],
    **metadata_overrides,
) -> dict:
    payload = _snapshot_payload_for(picks, **metadata_overrides)
    path = snapshots_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return payload


def _coverage_keys() -> set[str]:
    return {
        "snapshot_ids_used",
        "metadata_tuple_keys_used",
        "total_snapshots_found",
        "leakage_excluded_snapshots",
        "untrusted_excluded_snapshots",
        "partial_snapshot_warnings",
        "duplicate_pick_no_rejections",
        "duplicate_prospect_uuid_rejections",
        "content_hash_collisions",
        "snapshots_used",
        "total_picks",
        "redirect_applied",
        "high_redirect_rate_warning",
        "unresolved_picks",
        "unresolved_picks_ratio",
        "draft_date_used",
        "draft_date_source",
    }


def test_ingest_snapshots_schema_validation_rejects_unknown_nested_fields(tmp_path):
    uuid = "cpr_10000000-0000-4000-8000-000000000001"
    payload = _snapshot_payload_for([_pick(prospect_uuid=uuid)])
    payload["picks"][0]["unexpected_nested_field"] = "reject me"
    (tmp_path / "bad.json").write_text(json.dumps(payload), encoding="utf-8")

    normalized_picks, coverage = ingest_snapshots(
        tmp_path,
        s3_registry=_registry(_registry_entry(uuid)),
        draft_date="2025-04-24",
    )

    assert normalized_picks == []
    assert coverage["snapshots_used"] == 0
    assert coverage["total_snapshots_found"] == 1


def test_ingest_snapshots_applies_strict_published_date_leakage_gate(tmp_path):
    before_uuid = "cpr_20000000-0000-4000-8000-000000000001"
    equal_uuid = "cpr_20000000-0000-4000-8000-000000000002"
    after_uuid = "cpr_20000000-0000-4000-8000-000000000003"
    _write_snapshot(
        tmp_path,
        "before.json",
        [_pick(prospect_uuid=before_uuid)],
        source_label="source_before",
        published_date="2025-04-23",
    )
    _write_snapshot(
        tmp_path,
        "equal.json",
        [_pick(prospect_uuid=equal_uuid)],
        source_label="source_equal",
        published_date="2025-04-24",
    )
    _write_snapshot(
        tmp_path,
        "after.json",
        [_pick(prospect_uuid=after_uuid)],
        source_label="source_after",
        published_date="2025-04-25",
    )

    normalized_picks, coverage = ingest_snapshots(
        tmp_path,
        s3_registry=_registry(
            _registry_entry(before_uuid),
            _registry_entry(equal_uuid),
            _registry_entry(after_uuid),
        ),
        draft_date="2025-04-24",
    )

    assert [pick.resolved_prospect_uuid for pick in normalized_picks] == [before_uuid]
    assert coverage["total_snapshots_found"] == 3
    assert coverage["leakage_excluded_snapshots"] == 2
    assert coverage["snapshots_used"] == 1


def test_ingest_snapshots_validates_confirmed_identity_and_redirects(tmp_path):
    confirmed = "cpr_30000000-0000-4000-8000-000000000001"
    survivor = "cpr_30000000-0000-4000-8000-000000000002"
    deprecated = "cpr_30000000-0000-4000-8000-000000000003"
    bad_survivor = "cpr_30000000-0000-4000-8000-000000000004"
    deprecated_to_bad = "cpr_30000000-0000-4000-8000-000000000005"
    unknown = "cpr_30000000-0000-4000-8000-000000000006"
    _write_snapshot(
        tmp_path,
        "identity.json",
        [
            _pick(pick_no=1, prospect_uuid=confirmed),
            _pick(pick_no=2, prospect_uuid=deprecated),
            _pick(pick_no=3, prospect_uuid=deprecated_to_bad),
            _pick(pick_no=4, prospect_uuid=unknown),
        ],
    )

    normalized_picks, coverage = ingest_snapshots(
        tmp_path,
        s3_registry=_registry(
            _registry_entry(confirmed),
            _registry_entry(survivor),
            _registry_entry(deprecated, status="deprecated", merged_into=survivor),
            _registry_entry(bad_survivor, status="provisional"),
            _registry_entry(
                deprecated_to_bad,
                status="deprecated",
                merged_into=bad_survivor,
            ),
        ),
        draft_date="2025-04-24",
    )

    assert all(isinstance(pick, NormalizedPick) for pick in normalized_picks)
    assert [
        (pick.original_prospect_uuid, pick.resolved_prospect_uuid, pick.redirect_applied)
        for pick in normalized_picks
    ] == [
        (confirmed, confirmed, False),
        (deprecated, survivor, True),
    ]
    assert coverage["redirect_applied"] == 1
    assert coverage["unresolved_picks"] == 2
    assert coverage["unresolved_picks_ratio"] == 0.5


def test_ingest_snapshots_same_tuple_same_hash_is_idempotent(tmp_path):
    uuid = "cpr_40000000-0000-4000-8000-000000000001"
    picks = [_pick(prospect_uuid=uuid)]
    _write_snapshot(tmp_path, "source_a/first.json", picks)
    _write_snapshot(tmp_path, "source_a/duplicate_same_hash.json", picks)

    normalized_picks, coverage = ingest_snapshots(
        tmp_path,
        s3_registry=_registry(_registry_entry(uuid)),
        draft_date="2025-04-24",
    )

    assert [pick.resolved_prospect_uuid for pick in normalized_picks] == [uuid]
    assert coverage["total_snapshots_found"] == 2
    assert coverage["snapshots_used"] == 1
    assert coverage["content_hash_collisions"] == 0


def test_ingest_snapshots_same_tuple_different_hash_rejects_collision(tmp_path):
    first_uuid = "cpr_50000000-0000-4000-8000-000000000001"
    second_uuid = "cpr_50000000-0000-4000-8000-000000000002"
    _write_snapshot(tmp_path, "source_a/first.json", [_pick(prospect_uuid=first_uuid)])
    _write_snapshot(
        tmp_path,
        "source_a/collision.json",
        [_pick(prospect_uuid=second_uuid)],
    )

    normalized_picks, coverage = ingest_snapshots(
        tmp_path,
        s3_registry=_registry(_registry_entry(first_uuid), _registry_entry(second_uuid)),
        draft_date="2025-04-24",
    )

    assert [pick.resolved_prospect_uuid for pick in normalized_picks] == [first_uuid]
    assert coverage["snapshots_used"] == 1
    assert coverage["content_hash_collisions"] == 1
    assert any(
        "content_hash_collision_warning" in warning
        for warning in coverage.get("warnings", [])
    )


def test_ingest_snapshots_rejects_duplicate_pick_no_snapshot(tmp_path):
    first_uuid = "cpr_60000000-0000-4000-8000-000000000001"
    second_uuid = "cpr_60000000-0000-4000-8000-000000000002"
    _write_snapshot(
        tmp_path,
        "duplicate_pick_no.json",
        [
            _pick(pick_no=1, prospect_uuid=first_uuid),
            _pick(pick_no=1, prospect_uuid=second_uuid),
        ],
    )

    normalized_picks, coverage = ingest_snapshots(
        tmp_path,
        s3_registry=_registry(_registry_entry(first_uuid), _registry_entry(second_uuid)),
        draft_date="2025-04-24",
    )

    assert normalized_picks == []
    assert coverage["snapshots_used"] == 0
    assert coverage["duplicate_pick_no_rejections"] == 1


def test_ingest_snapshots_rejects_duplicate_prospect_uuid_snapshot(tmp_path):
    uuid = "cpr_70000000-0000-4000-8000-000000000001"
    _write_snapshot(
        tmp_path,
        "duplicate_prospect_uuid.json",
        [
            _pick(pick_no=1, prospect_uuid=uuid),
            _pick(pick_no=2, prospect_uuid=uuid),
        ],
    )

    normalized_picks, coverage = ingest_snapshots(
        tmp_path,
        s3_registry=_registry(_registry_entry(uuid)),
        draft_date="2025-04-24",
    )

    assert normalized_picks == []
    assert coverage["snapshots_used"] == 0
    assert coverage["duplicate_prospect_uuid_rejections"] == 1


def test_ingest_snapshots_coverage_matrix_populates_section_4_5_fields(tmp_path):
    uuid = "cpr_80000000-0000-4000-8000-000000000001"
    _write_snapshot(tmp_path, "coverage.json", [_pick(prospect_uuid=uuid)])

    normalized_picks, coverage = ingest_snapshots(
        tmp_path,
        s3_registry=_registry(_registry_entry(uuid)),
        draft_date="2025-04-24",
    )

    assert len(normalized_picks) == 1
    assert set(coverage) >= _coverage_keys()
    assert coverage["snapshot_ids_used"]
    assert coverage["metadata_tuple_keys_used"] == [
        "synthetic_source_a|davidleess|2025-04-01|v1"
    ]
    assert coverage["total_snapshots_found"] == 1
    assert coverage["snapshots_used"] == 1
    assert coverage["total_picks"] == 1
    assert coverage["draft_date_used"] == "2025-04-24"
    assert coverage["draft_date_source"] == "explicit"
