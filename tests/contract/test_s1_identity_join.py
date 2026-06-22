"""S1 read-only identity-join contract tests (spec v4 §6, U4)."""
from __future__ import annotations

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeAliasBridge,
    CollegeAliasBridgeEntry,
    CollegeProspectRegistry,
    ConfirmedProspectUuid,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
    normalize_name,
)
from src.dynasty_genius.mock_consensus.curated_input import (
    adapt_curated_row_to_s3,
    load_curated_json_payload,
)
from src.dynasty_genius.mock_consensus.identity_join import (
    apply_match_rate_gate,
    resolve_curated_row_identity,
)


def _curated_payload_row(**overrides) -> dict:
    row = {
        "source_id": "nfl_mock_database",
        "source_name": "NFL Mock Database",
        "analyst": "Daniel Jeremiah",
        "mock_version": "v1",
        "published_date": "2026-04-01",
        "source_snapshot_id": "nfl_mock_database:2026-04-01:v1",
        "raw_row_hash": "hash_arch_001",
        "parse_status": "complete",
        "source_type": "mock",
        "prospect_name_raw": "Arch Manning",
        "position_raw": "QB",
        "school_raw": "Texas",
        "draft_class": 2027,
        "projected_pick": 12,
        "projected_round": 1,
        "nfl_team": "TEN",
        "projection_status": "exact_pick",
        "source_rank": None,
    }
    row.update(overrides)
    return row


def _incoming(**overrides) -> NormalizedCollegeProspectRow:
    result = load_curated_json_payload(
        {"schema_version": "s1_curated_mock_consensus_v1", "rows": [_curated_payload_row(**overrides)]}
    )
    assert result.dropped_rows == []
    return adapt_curated_row_to_s3(result.rows[0])


def _entry(
    uuid: str,
    *,
    name: str = "Arch Manning",
    position: str = "QB",
    position_group: str = "QB",
    draft_class: int = 2027,
    school: str = "Texas",
    status: str = "confirmed",
) -> RegistryEntry:
    normalized = normalize_name(name)
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,  # type: ignore[arg-type]
        match_key=compute_match_key(
            normalized_name=normalized,
            position_group=position_group,
            draft_class=draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status=status,  # type: ignore[arg-type]
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        raw_name=name,
        normalized_name=normalized,
        full_name=name,
        position=position,
        position_group=position_group,
        draft_class=draft_class,
        current_school=school,
        prior_schools=[],
        cfbd_athlete_id=None,
        cfb_player_id=None,
        pfr_id=None,
        gsis_id=None,
        sleeper_id=None,
        source="manual_fixture",
        source_record_id=f"fixture_{uuid}",
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


def _registry(*entries: RegistryEntry) -> CollegeProspectRegistry:
    return CollegeProspectRegistry(
        metadata={"draft_class": 2027},
        entries={entry.prospect_uuid: entry for entry in entries},
    )


def test_exact_confirmed_match_returns_confirmed_uuid_and_feeds_aggregation():
    uuid = "cpr_10000000-0000-4000-8000-000000000001"
    result = resolve_curated_row_identity(
        _incoming(),
        registry=_registry(_entry(uuid)),
        alias_bridge=CollegeAliasBridge(),
    )

    assert isinstance(result.confirmed_uuid, ConfirmedProspectUuid)
    assert str(result.confirmed_uuid) == uuid
    assert result.review_candidates == []
    assert result.feeds_aggregation is True


def test_fuzzy_match_surfaces_review_queue_without_auto_match():
    uuid = "cpr_10000000-0000-4000-8000-000000000002"
    result = resolve_curated_row_identity(
        _incoming(prospect_name_raw="Carnell Tate Jr.", position_raw="WR", school_raw="Ohio State"),
        registry=_registry(
            _entry(
                uuid,
                name="Carnell Tate",
                position="WR",
                position_group="WR",
                school="Ohio State",
            )
        ),
        alias_bridge=CollegeAliasBridge(),
    )

    assert result.confirmed_uuid is None
    assert result.feeds_aggregation is False
    assert [candidate.target_prospect_uuid for candidate in result.review_candidates] == [uuid]


def test_common_name_collision_does_not_auto_match():
    incoming = _incoming(
        prospect_name_raw="Chris Smith",
        position_raw="WR",
        school_raw="Georgia",
    )
    result = resolve_curated_row_identity(
        incoming,
        registry=_registry(
            _entry(
                "cpr_10000000-0000-4000-8000-000000000003",
                name="Chris Smith",
                position="WR",
                position_group="WR",
                school="Georgia",
            ),
            _entry(
                "cpr_10000000-0000-4000-8000-000000000004",
                name="Chris Smith",
                position="WR",
                position_group="WR",
                school="Georgia",
            ),
        ),
        alias_bridge=CollegeAliasBridge(),
    )

    assert result.confirmed_uuid is None
    assert result.feeds_aggregation is False
    assert len(result.review_candidates) == 2


def test_direct_registry_row_must_be_confirmed_to_match():
    uuid = "cpr_10000000-0000-4000-8000-000000000005"
    for status in ("provisional", "deprecated"):
        result = resolve_curated_row_identity(
            _incoming(),
            registry=_registry(_entry(uuid, status=status)),
            alias_bridge=CollegeAliasBridge(),
        )

        assert result.confirmed_uuid is None
        assert result.feeds_aggregation is False


def test_alias_bridge_target_resolves_through_confirmed_registry_only():
    confirmed = "cpr_10000000-0000-4000-8000-000000000006"
    provisional = "cpr_10000000-0000-4000-8000-000000000007"
    incoming = _incoming(
        source_id="the_athletic",
        raw_row_hash="alias_hash",
        prospect_name_raw="Alias Prospect",
        position_raw="WR",
        school_raw="Alias U",
    )
    alias_entry = CollegeAliasBridgeEntry(
        match_key=compute_match_key(
            normalized_name=incoming.normalized_name,
            position_group=incoming.position_group,
            draft_class=incoming.draft_class,
        ),
        source_record_id=incoming.source_record_id,
        target_prospect_uuid=confirmed,
    )
    registry = _registry(
        _entry(confirmed, name="Different Name", position="WR", position_group="WR"),
        _entry(provisional, name="Alias Prospect", position="WR", position_group="WR", status="provisional"),
    )

    result = resolve_curated_row_identity(
        incoming,
        registry=registry,
        alias_bridge=CollegeAliasBridge(entries=[alias_entry]),
    )

    assert isinstance(result.confirmed_uuid, ConfirmedProspectUuid)
    assert str(result.confirmed_uuid) == confirmed
    assert result.feeds_aggregation is True

    bad_targets = (
        provisional,
        "cpr_10000000-0000-4000-8000-000000000099",
    )
    for target in bad_targets:
        bad_alias = alias_entry.model_copy(update={"target_prospect_uuid": target})
        bad_result = resolve_curated_row_identity(
            incoming,
            registry=registry,
            alias_bridge=CollegeAliasBridge(entries=[bad_alias]),
        )
        assert bad_result.confirmed_uuid is None
        assert bad_result.feeds_aggregation is False


def test_match_rate_gate_fails_closed_on_malformed_ranked_rows():
    """U4 is a fail-closed integrity gate: a malformed raw row must abstain with an
    explicit reason, never crash (KeyError/TypeError) and never silently bypass a
    wrong-type ``resolved`` value as resolved."""
    malformed_cases = [
        [{"raw_rank": 1}],  # missing resolved
        [{"resolved": False}],  # missing raw_rank
        [{"raw_rank": "1", "resolved": False}],  # raw_rank wrong type
        [{"raw_rank": 1, "resolved": "false"}],  # resolved wrong type (truthy str)
        [{"raw_rank": 0, "resolved": False}],  # raw_rank below 1
        ["not-a-dict"],  # row not a mapping
    ]
    for rows in malformed_cases:
        result = apply_match_rate_gate(rows, top_n=12, max_unresolved=0.20)
        assert result.should_abstain is True
        assert any("malformed" in reason for reason in result.reasons)


def test_match_rate_gate_trips_on_overall_unresolved_rate_and_raw_top_n_unresolved():
    over_twenty = [
        {"raw_rank": idx, "resolved": idx not in {13, 14, 15, 16, 17, 18}}
        for idx in range(1, 25)
    ]
    rate_result = apply_match_rate_gate(over_twenty, top_n=12, max_unresolved=0.20)

    assert rate_result.should_abstain is True
    assert any("unresolved_rate" in reason for reason in rate_result.reasons)

    top_n_unresolved = [
        {"raw_rank": idx, "resolved": idx != 3}
        for idx in range(1, 25)
    ]
    top_n_result = apply_match_rate_gate(
        top_n_unresolved,
        top_n=12,
        max_unresolved=0.20,
    )

    assert top_n_result.should_abstain is True
    assert any("top_12" in reason for reason in top_n_result.reasons)

    outside_top_n_unresolved = [
        {"raw_rank": idx, "resolved": idx != 20}
        for idx in range(1, 25)
    ]
    clean_result = apply_match_rate_gate(
        outside_top_n_unresolved,
        top_n=12,
        max_unresolved=0.20,
    )

    assert clean_result.should_abstain is False
    assert clean_result.reasons == []
