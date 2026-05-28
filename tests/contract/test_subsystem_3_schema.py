"""Subsystem 3 - schema & registry contract tests (section 10.1)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.dynasty_genius.identity.college_prospect_identity import (
    MATCHER_ALGORITHM_VERSION,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryAppendOnlyError,
    StatusHistoryEntry,
    load_registry,
)


def _fixture_row_minimal() -> dict:
    return {
        "raw_name": "Arch Manning",
        "normalized_name": "arch manning",
        "full_name": "Arch Manning",
        "position": "QB",
        "position_group": "QB",
        "draft_class": 2027,
        "current_school": "Texas",
        "prior_schools": [],
        "cfbd_athlete_id": None,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "manual_fixture",
        "source_record_id": "fixture_2027_001",
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    }


def test_normalized_row_required_and_nullable_fields_accept_minimal_shape():
    row = NormalizedCollegeProspectRow.model_validate(_fixture_row_minimal())
    assert row.raw_name == "Arch Manning"
    assert row.draft_class == 2027
    assert row.cfbd_athlete_id is None
    assert row.id_provenance.cfbd_athlete_id is None


def test_normalized_row_rejects_missing_required_field():
    bad = _fixture_row_minimal()
    bad.pop("source_record_id")
    with pytest.raises(ValidationError):
        NormalizedCollegeProspectRow.model_validate(bad)


def test_normalized_row_id_provenance_round_trip_preserves_nested_nulls():
    row = NormalizedCollegeProspectRow.model_validate(_fixture_row_minimal())
    dumped = row.model_dump()
    reloaded = NormalizedCollegeProspectRow.model_validate(dumped)
    assert reloaded == row


def test_status_history_append_only_invariant_blocks_destructive_rewrite():
    history = [
        StatusHistoryEntry(
            event_id="ev_1",
            decision="confirm",
            after_status="confirmed",
            decided_at="2026-05-28T12:00:00Z",
            reviewer_id="davidleess",
        )
    ]
    entry = RegistryEntry(
        prospect_uuid="cpr_00000000-0000-4000-8000-000000000001",
        verification_status="confirmed",
        match_key="abc123",
        status_history=history,
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **_fixture_row_minimal(),
    )
    new_history = [
        StatusHistoryEntry(
            event_id="ev_2",
            decision="confirm",
            after_status="confirmed",
            decided_at="2026-05-28T12:00:01Z",
            reviewer_id="davidleess",
        )
    ]
    with pytest.raises(StatusHistoryAppendOnlyError):
        entry.replace_status_history(new_history)  # destructive rewrite forbidden


def test_empty_or_missing_registry_file_loads_as_no_op(tmp_path: Path):
    missing = tmp_path / "absent.json"
    registry = load_registry(missing)
    assert registry.entries == {}

    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"metadata": {}, "entries": []}))
    assert load_registry(empty).entries == {}


def test_cfbd_shape_forward_compat_validates_against_documented_response_fields():
    cfbd_like = {
        "raw_name": "Quinn Ewers",
        "normalized_name": "quinn ewers",
        "full_name": "Quinn Ewers",
        "position": "QB",
        "position_group": "QB",
        "draft_class": 2027,
        "current_school": "Texas",
        "prior_schools": ["Ohio State"],
        "cfbd_athlete_id": "cfbd_4567890",
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "cfbd",
        "source_record_id": "cfbd_athlete_4567890",
        "source_snapshot_id": "cfbd_2027_snapshot_001",
        "id_provenance": {
            "cfbd_athlete_id": {
                "method": "cfbd_api_get_athletes",
                "fetched_at": "2026-05-28T12:00:00Z",
            },
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    }
    row = NormalizedCollegeProspectRow.model_validate(cfbd_like)
    assert row.source == "cfbd"
    assert row.id_provenance.cfbd_athlete_id is not None


def test_module_pins_matcher_algorithm_version_string():
    assert MATCHER_ALGORITHM_VERSION == "cpr_matcher_v1.0.0"
