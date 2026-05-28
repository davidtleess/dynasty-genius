"""Subsystem 4 bridge schema + validation contract tests (§3.1, §3.2)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
)
from src.dynasty_genius.identity.prospect_nfl_bridge import (
    ProspectNflBridgeEntry,
    validate_against_s3,
    validate_bridge_entry,
)


def _provenance() -> dict:
    return {
        "nflreadr_source": "nflreadpy.draft_picks",
        "nflreadr_season": 2025,
        "draft_truth_content_hash": "abc123",
        "nflreadr_fetched_at": "2026-05-28T12:00:00Z",
    }


def _drafted_entry_kwargs() -> dict:
    return {
        "prospect_uuid": "cpr_00000000-0000-4000-8000-000000000001",
        "gsis_id": "00-0034987",
        "pfr_id": "ManningArch01",
        "draft_year": 2025,
        "draft_pick_no": 1,
        "draft_round": 1,
        "nfl_team": "CAR",
        "udfa": False,
        "evidence_snapshot": {
            "full_name": "Arch Manning",
            "position": "QB",
            "college": "Texas",
            "fetched_at": "2026-05-28T12:00:00Z",
        },
        "event_id": "ev_1",
        "decided_at": "2026-05-28T12:00:00Z",
        "reviewer_id": "davidleess",
        "decision": "confirm",
        **_provenance(),
    }


def _udfa_entry_kwargs() -> dict:
    return {
        "prospect_uuid": "cpr_00000000-0000-4000-8000-000000000002",
        "gsis_id": None,
        "pfr_id": None,
        "draft_year": 2025,
        "draft_pick_no": None,
        "draft_round": None,
        "nfl_team": None,
        "udfa": True,
        "evidence_snapshot": None,
        "event_id": "ev_2",
        "decided_at": "2026-05-28T12:00:01Z",
        "reviewer_id": "davidleess",
        "decision": "udfa",
        "note": "verified absent from nflreadr 2025 7-day post-draft window",
        **_provenance(),
    }


def _s3_row_for(
    uuid: str,
    status: str = "confirmed",
    draft_class: int = 2025,
) -> RegistryEntry:
    base = NormalizedCollegeProspectRow.model_validate(
        {
            "raw_name": "Arch Manning",
            "normalized_name": "arch manning",
            "full_name": "Arch Manning",
            "position": "QB",
            "position_group": "QB",
            "draft_class": draft_class,
            "current_school": "Texas",
            "prior_schools": [],
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
            "source": "manual_fixture",
            "source_record_id": f"src_{uuid[:8]}",
            "source_snapshot_id": "fixture_2025_v1",
            "id_provenance": {
                "cfbd_athlete_id": None,
                "cfb_player_id": None,
                "pfr_id": None,
                "gsis_id": None,
                "sleeper_id": None,
            },
            "notes": None,
        }
    )
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,
        match_key=compute_match_key(
            normalized_name=base.normalized_name,
            position_group="QB",
            draft_class=draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status=status,
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **base.model_dump(),
    )


def test_drafted_entry_accepts_minimal_shape():
    entry = ProspectNflBridgeEntry.model_validate(_drafted_entry_kwargs())
    assert entry.gsis_id == "00-0034987"
    assert entry.udfa is False
    assert entry.decision == "confirm"
    assert validate_bridge_entry(entry) == []


def test_udfa_entry_accepts_strict_null_shape():
    entry = ProspectNflBridgeEntry.model_validate(_udfa_entry_kwargs())
    assert entry.gsis_id is None
    assert entry.udfa is True
    assert entry.decision == "udfa"
    assert validate_bridge_entry(entry) == []


def test_drafted_with_null_gsis_id_fails_validation():
    bad = _drafted_entry_kwargs()
    bad["gsis_id"] = None
    entry = ProspectNflBridgeEntry.model_validate(bad)
    errors = validate_bridge_entry(entry)
    assert any("gsis_id" in error for error in errors)


def test_drafted_with_null_pick_no_fails_validation():
    bad = _drafted_entry_kwargs()
    bad["draft_pick_no"] = None
    entry = ProspectNflBridgeEntry.model_validate(bad)
    errors = validate_bridge_entry(entry)
    assert any("draft_pick_no" in error for error in errors)


def test_udfa_with_populated_gsis_id_fails_validation():
    bad = _udfa_entry_kwargs()
    bad["gsis_id"] = "00-0034987"
    entry = ProspectNflBridgeEntry.model_validate(bad)
    errors = validate_bridge_entry(entry)
    assert any("udfa" in error.lower() for error in errors)


def test_udfa_with_populated_pfr_id_fails_validation():
    bad = _udfa_entry_kwargs()
    bad["pfr_id"] = "ManningArch01"
    entry = ProspectNflBridgeEntry.model_validate(bad)
    errors = validate_bridge_entry(entry)
    assert any("pfr_id" in error.lower() or "udfa" in error.lower() for error in errors)


def test_drafted_with_null_pfr_id_is_valid():
    ok = _drafted_entry_kwargs()
    ok["pfr_id"] = None
    entry = ProspectNflBridgeEntry.model_validate(ok)
    assert validate_bridge_entry(entry) == []


def test_missing_provenance_field_fails_validation():
    bad = _drafted_entry_kwargs()
    bad.pop("nflreadr_source")
    with pytest.raises(ValidationError):
        ProspectNflBridgeEntry.model_validate(bad)


def test_decision_literal_rejects_other_strings():
    bad = _drafted_entry_kwargs()
    bad["decision"] = "merge_into"
    with pytest.raises(ValidationError):
        ProspectNflBridgeEntry.model_validate(bad)


def test_evidence_snapshot_none_for_udfa_is_valid():
    ok = _udfa_entry_kwargs()
    ok["evidence_snapshot"] = None
    entry = ProspectNflBridgeEntry.model_validate(ok)
    assert validate_bridge_entry(entry) == []


def test_confirm_rejected_when_prospect_uuid_not_in_s3():
    s3 = CollegeProspectRegistry()
    entry = ProspectNflBridgeEntry.model_validate(_drafted_entry_kwargs())
    errors = validate_against_s3(entry, s3_registry=s3)
    assert any("not in S3" in error or "unknown" in error.lower() for error in errors)


def test_confirm_rejected_when_prospect_uuid_not_confirmed():
    uuid = "cpr_00000000-0000-4000-8000-000000000001"
    s3 = CollegeProspectRegistry(
        entries={uuid: _s3_row_for(uuid, status="provisional")}
    )
    entry = ProspectNflBridgeEntry.model_validate(
        {**_drafted_entry_kwargs(), "prospect_uuid": uuid}
    )
    errors = validate_against_s3(entry, s3_registry=s3)
    assert any(
        "provisional" in error.lower() or "not confirmed" in error.lower()
        for error in errors
    )


def test_confirm_rejected_when_draft_year_mismatches_s3():
    uuid = "cpr_00000000-0000-4000-8000-000000000001"
    s3 = CollegeProspectRegistry(entries={uuid: _s3_row_for(uuid, draft_class=2024)})
    entry = ProspectNflBridgeEntry.model_validate(
        {**_drafted_entry_kwargs(), "prospect_uuid": uuid}
    )
    errors = validate_against_s3(entry, s3_registry=s3)
    assert any("draft_year" in error and "draft_class" in error for error in errors)


def test_confirm_accepted_when_s3_confirmed_and_draft_year_matches():
    uuid = "cpr_00000000-0000-4000-8000-000000000001"
    s3 = CollegeProspectRegistry(
        entries={uuid: _s3_row_for(uuid, status="confirmed", draft_class=2025)}
    )
    entry = ProspectNflBridgeEntry.model_validate(
        {**_drafted_entry_kwargs(), "prospect_uuid": uuid}
    )
    assert validate_against_s3(entry, s3_registry=s3) == []
