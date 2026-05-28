"""Subsystem 3 - ConfirmedProspectUuid contract tests (section 10.4)."""
from __future__ import annotations

import inspect

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    ConfirmedProspectUuid,
    ProspectUuidDeprecatedMerged,
    ProspectUuidNotConfirmed,
    RegistryEntry,
    StatusHistoryEntry,
    UnknownProspectUuid,
    compute_match_key,
    normalize_name,
    resolve_prospect_cfbd_athlete_id,
)


def _entry(uuid: str, status: str = "confirmed", merged_into: str | None = None):
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,
        match_key=compute_match_key(
            normalized_name="sample name",
            position_group="WR",
            draft_class=2027,
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
        merged_into_prospect_uuid=merged_into,
        reviewer_id="davidleess",
        reviewer_metadata={},
        raw_name="Sample Name",
        normalized_name=normalize_name("Sample Name"),
        full_name="Sample Name",
        position="WR",
        position_group="WR",
        draft_class=2027,
        current_school="Texas",
        prior_schools=[],
        cfbd_athlete_id=None,
        cfb_player_id=None,
        pfr_id=None,
        gsis_id=None,
        sleeper_id=None,
        source="manual_fixture",
        source_record_id=f"fixture_2027_{uuid}",
        source_snapshot_id="fixture_2027_v1",
        id_provenance={
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        notes=None,
    )


def test_confirmed_uuid_constructs_only_on_confirmed_row():
    uuid = "cpr_11111111-1111-4111-8111-111111111111"
    registry = CollegeProspectRegistry(entries={uuid: _entry(uuid, status="confirmed")})
    confirmed = ConfirmedProspectUuid(uuid, registry=registry)
    assert str(confirmed) == uuid


def test_confirmed_uuid_raises_unknown_uuid_for_missing_row():
    registry = CollegeProspectRegistry()
    with pytest.raises(UnknownProspectUuid):
        ConfirmedProspectUuid("cpr_does_not_exist", registry=registry)


def test_confirmed_uuid_raises_not_confirmed_on_provisional_row():
    uuid = "cpr_22222222-2222-4222-8222-222222222222"
    registry = CollegeProspectRegistry(entries={uuid: _entry(uuid, status="provisional")})
    with pytest.raises(ProspectUuidNotConfirmed):
        ConfirmedProspectUuid(uuid, registry=registry)


def test_confirmed_uuid_raises_deprecated_merged_on_redirect_without_allow_flag():
    survivor = "cpr_33333333-3333-4333-8333-333333333333"
    deprecated = "cpr_44444444-4444-4444-8444-444444444444"
    registry = CollegeProspectRegistry(
        entries={
            survivor: _entry(survivor, status="confirmed"),
            deprecated: _entry(
                deprecated, status="deprecated", merged_into=survivor
            ),
        }
    )
    with pytest.raises(ProspectUuidDeprecatedMerged):
        ConfirmedProspectUuid(deprecated, registry=registry)


def test_confirmed_uuid_follows_redirect_when_explicitly_allowed():
    survivor = "cpr_55555555-5555-4555-8555-555555555555"
    deprecated = "cpr_66666666-6666-4666-8666-666666666666"
    registry = CollegeProspectRegistry(
        entries={
            survivor: _entry(survivor, status="confirmed"),
            deprecated: _entry(
                deprecated, status="deprecated", merged_into=survivor
            ),
        }
    )
    confirmed = ConfirmedProspectUuid(deprecated, registry=registry, follow_redirect=True)
    assert str(confirmed) == survivor


def test_runtime_consumer_signature_requires_confirmed_prospect_uuid_type():
    """Spec section 4.4: runtime signature contract; no mypy/pyright gate in v1."""
    sig = inspect.signature(resolve_prospect_cfbd_athlete_id)
    rendered = repr(sig.return_annotation)
    assert "ConfirmedProspectUuid" in rendered, (
        f"resolve_prospect_cfbd_athlete_id return type must mention "
        f"ConfirmedProspectUuid, got {rendered}"
    )
