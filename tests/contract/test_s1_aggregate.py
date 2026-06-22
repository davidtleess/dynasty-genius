"""S1 aggregation + abstention policy contract tests (spec v4 T4)."""
from __future__ import annotations

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    ConfirmedProspectUuid,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
    normalize_name,
)
from src.dynasty_genius.mock_consensus.aggregate import (
    aggregate_mock_consensus,
    round_tier_for_pick,
)
from src.dynasty_genius.mock_consensus.curated_input import load_curated_json_payload
from src.dynasty_genius.mock_consensus.identity_join import IdentityResolution


def _payload_row(**overrides) -> dict:
    row = {
        "source_id": "source_a",
        "source_name": "Source A",
        "analyst": "Analyst A",
        "mock_version": "v1",
        "published_date": "2026-04-01",
        "source_snapshot_id": "snap_a",
        "raw_row_hash": "hash_a",
        "parse_status": "complete",
        "source_type": "mock",
        "prospect_name_raw": "Arch Manning",
        "position_raw": "QB",
        "school_raw": "Texas",
        "draft_class": 2027,
        "projected_pick": 10,
        "projected_round": 1,
        "nfl_team": "TEN",
        "projection_status": "exact_pick",
        "source_rank": None,
    }
    row.update(overrides)
    return row


def _analyst_name(index: int) -> str:
    return f"Analyst {chr(ord('A') + index - 1)}"


def _rows(*payload_rows: dict):
    result = load_curated_json_payload(
        {"schema_version": "s1_curated_mock_consensus_v1", "rows": list(payload_rows)}
    )
    assert result.dropped_rows == []
    return result.rows


def _registry_entry(uuid: str) -> RegistryEntry:
    normalized = normalize_name("Arch Manning")
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status="confirmed",
        match_key=compute_match_key(
            normalized_name=normalized,
            position_group="QB",
            draft_class=2027,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status="confirmed",
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        raw_name="Arch Manning",
        normalized_name=normalized,
        full_name="Arch Manning",
        position="QB",
        position_group="QB",
        draft_class=2027,
        current_school="Texas",
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


def _confirmed(uuid: str = "cpr_20000000-0000-4000-8000-000000000001"):
    registry = CollegeProspectRegistry(entries={uuid: _registry_entry(uuid)})
    return ConfirmedProspectUuid(uuid, registry=registry)


def _identity_map(rows, *, unresolved_hashes=()):
    unresolved = set(unresolved_hashes)
    confirmed = _confirmed()
    return {
        row.raw_row_hash: IdentityResolution(
            confirmed_uuid=None if row.raw_row_hash in unresolved else confirmed,
            feeds_aggregation=row.raw_row_hash not in unresolved,
        )
        for row in rows
    }


def test_latest_eligible_per_analyst_dedups_with_deterministic_tiebreak():
    rows = _rows(
        _payload_row(
            analyst="Analyst A",
            raw_row_hash="hash_a_old",
            published_date="2026-03-01",
            source_snapshot_id="snap_a_old",
            projected_pick=250,
        ),
        _payload_row(
            analyst="Analyst A",
            raw_row_hash="hash_a_mid",
            published_date="2026-04-01",
            source_snapshot_id="snap_a",
            projected_pick=99,
        ),
        _payload_row(
            analyst="Analyst A",
            raw_row_hash="hash_a_latest",
            published_date="2026-04-01",
            source_snapshot_id="snap_z",
            projected_pick=10,
        ),
        _payload_row(analyst="Analyst B", raw_row_hash="hash_b", projected_pick=12),
        _payload_row(analyst="Analyst C", raw_row_hash="hash_c", projected_pick=13),
        _payload_row(analyst="Analyst D", raw_row_hash="hash_d", projected_pick=14),
        _payload_row(analyst="Analyst E", raw_row_hash="hash_e", projected_pick=16),
    )

    result = aggregate_mock_consensus(rows, _identity_map(rows), as_of="2026-04-24")
    record = result.records[0]

    assert result.should_abstain is False
    assert record.n_unique_analysts == 5
    assert record.projected_pick_median == 13.0
    assert "hash_a_latest" in record.raw_row_hashes_used
    assert "hash_a_mid" not in record.raw_row_hashes_used
    assert "hash_a_old" not in record.raw_row_hashes_used


def test_round_tier_boundaries_and_half_pick_rounding():
    assert round_tier_for_pick(1) == "R1.early"
    assert round_tier_for_pick(4) == "R1.early"
    assert round_tier_for_pick(4.5) == "R1.mid"
    assert round_tier_for_pick(8) == "R1.mid"
    assert round_tier_for_pick(8.5) == "R1.late"
    assert round_tier_for_pick(12) == "R1.late"
    assert round_tier_for_pick(13) == "R1.late"
    assert round_tier_for_pick(32) == "R1.late"
    assert round_tier_for_pick(33) == "R2"
    assert round_tier_for_pick(80) == "R3"
    assert round_tier_for_pick(150) == "Day3"
    assert round_tier_for_pick(None) == "UDFA"


def test_disagreement_flag_and_iqr_hard_block_live_in_s1_policy():
    tight_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"tight_{idx}",
                projected_pick=pick,
            )
            for idx, pick in enumerate([10, 12, 14, 15, 17], start=1)
        ]
    )
    wide_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"wide_{idx}",
                projected_pick=pick,
            )
            for idx, pick in enumerate([10, 12, 14, 16, 20], start=1)
        ]
    )

    tight = aggregate_mock_consensus(
        tight_rows,
        _identity_map(tight_rows),
        as_of="2026-04-24",
    ).records[0]
    wide = aggregate_mock_consensus(
        wide_rows,
        _identity_map(wide_rows),
        as_of="2026-04-24",
    ).records[0]

    assert tight.projected_pick_iqr == 5.0
    assert tight.disagreement_flag is False
    assert tight.projected_pick_median == 14.0
    assert tight.internal_diagnostic is True

    assert wide.projected_pick_iqr == 7.0
    assert wide.disagreement_flag is True
    assert wide.projected_pick_median is None
    assert wide.internal_diagnostic is False
    assert wide.abstention_tier == "round_tier_only"


def test_analyst_count_and_staleness_boundaries_control_exact_pick_emission():
    two_rows = _rows(
        _payload_row(analyst="Analyst A", raw_row_hash="a", projected_pick=10),
        _payload_row(analyst="Analyst B", raw_row_hash="b", projected_pick=12),
    )
    four_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"four_{idx}",
                projected_pick=pick,
            )
            for idx, pick in enumerate([10, 12, 14, 16], start=1)
        ]
    )
    fresh_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"fresh_{idx}",
                projected_pick=pick,
                published_date="2026-03-25",
            )
            for idx, pick in enumerate([10, 12, 13, 14, 16], start=1)
        ]
    )
    stale_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"stale_{idx}",
                projected_pick=pick,
                published_date="2026-03-24",
            )
            for idx, pick in enumerate([10, 12, 13, 14, 16], start=1)
        ]
    )

    under = aggregate_mock_consensus(
        two_rows,
        _identity_map(two_rows),
        as_of="2026-04-24",
    )
    four = aggregate_mock_consensus(
        four_rows,
        _identity_map(four_rows),
        as_of="2026-04-24",
    ).records[0]
    fresh = aggregate_mock_consensus(
        fresh_rows,
        _identity_map(fresh_rows),
        as_of="2026-04-24",
    ).records[0]
    stale = aggregate_mock_consensus(
        stale_rows,
        _identity_map(stale_rows),
        as_of="2026-04-24",
    ).records[0]

    assert under.should_abstain is True
    assert any("n_unique_analysts" in reason for reason in under.abstention_reasons)
    assert four.abstention_tier == "round_tier_only"
    assert four.projected_pick_median == 13.0
    assert fresh.staleness_days == 30
    assert fresh.projected_pick_median == 13.0
    assert fresh.internal_diagnostic is True
    assert stale.staleness_days == 31
    assert stale.projected_pick_median is None
    assert stale.internal_diagnostic is False


def test_round_only_and_udfa_paths_emit_round_tiers_without_exact_pick():
    round_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"round_{idx}",
                projection_status="round_only",
                projected_pick=None,
                projected_round=round_no,
            )
            for idx, round_no in enumerate([1, 1, 2, 2, 3], start=1)
        ]
    )
    udfa_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"udfa_{idx}",
                projection_status="udfa",
                projected_pick=None,
                projected_round=None,
            )
            for idx in range(1, 6)
        ]
    )

    round_record = aggregate_mock_consensus(
        round_rows,
        _identity_map(round_rows),
        as_of="2026-04-24",
    ).records[0]
    udfa_record = aggregate_mock_consensus(
        udfa_rows,
        _identity_map(udfa_rows),
        as_of="2026-04-24",
    ).records[0]

    assert round_record.round_tier == "R2"
    assert round_record.projected_pick_median is None
    assert round_record.internal_diagnostic is False
    assert udfa_record.round_tier == "UDFA"
    assert udfa_record.projected_pick_median is None
    assert udfa_record.internal_diagnostic is False


def test_raw_pre_join_match_rate_gate_abstains_for_top_12_and_rate_failures():
    top_12_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"top_{idx}",
                projected_pick=idx,
            )
            for idx in range(1, 25)
        ]
    )
    rate_rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"rate_{idx}",
                projected_pick=idx,
            )
            for idx in range(1, 25)
        ]
    )

    top_result = aggregate_mock_consensus(
        top_12_rows,
        _identity_map(top_12_rows, unresolved_hashes={"top_3"}),
        as_of="2026-04-24",
    )
    rate_result = aggregate_mock_consensus(
        rate_rows,
        _identity_map(
            rate_rows,
            unresolved_hashes={f"rate_{idx}" for idx in range(13, 19)},
        ),
        as_of="2026-04-24",
    )

    assert top_result.should_abstain is True
    assert any("top_12" in reason for reason in top_result.abstention_reasons)
    assert rate_result.should_abstain is True
    assert any("unresolved_rate" in reason for reason in rate_result.abstention_reasons)


def test_aggregate_fails_closed_on_empty_payload_and_missing_identity_entries():
    """Robustness boundary (Claude proactive): empty input and rows with no
    identity_map entry must fail closed (abstain), never crash."""
    empty = aggregate_mock_consensus([], {}, as_of="2026-04-24")
    assert empty.should_abstain is True

    rows = _rows(
        *[
            _payload_row(
                analyst=_analyst_name(idx),
                raw_row_hash=f"miss_{idx}",
                projected_pick=pick,
            )
            for idx, pick in enumerate([10, 12, 13, 14, 16], start=1)
        ]
    )
    # Empty identity_map: every row is treated as unresolved (fail-closed), so the
    # raw pre-join gate abstains rather than raising KeyError.
    result = aggregate_mock_consensus(rows, {}, as_of="2026-04-24")
    assert result.should_abstain is True
