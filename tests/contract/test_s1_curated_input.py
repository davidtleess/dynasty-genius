"""S1 curated-input loader contract tests (spec v4 §3, §3b, §4)."""
from __future__ import annotations

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    NormalizedCollegeProspectRow,
)
from src.dynasty_genius.mock_consensus.curated_input import (
    DRAFT_PICK_MAX,
    CuratedInputSchemaError,
    adapt_curated_row_to_s3,
    load_curated_json_payload,
)


def _row(**overrides) -> dict:
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


def _payload(*rows: dict) -> dict:
    return {"schema_version": "s1_curated_mock_consensus_v1", "rows": list(rows)}


def _drop_reasons(result) -> list[str]:
    return [drop.reason for drop in result.dropped_rows]


def test_structural_schema_gate_rejects_malformed_payloads_before_row_semantics():
    for payload in (
        None,
        [],
        {},
        {"schema_version": "s1_curated_mock_consensus_v1"},
        {"schema_version": "s1_curated_mock_consensus_v1", "rows": "not-a-list"},
    ):
        with pytest.raises(CuratedInputSchemaError):
            load_curated_json_payload(payload)


def test_semantic_validation_drops_invalid_records_with_reasons_never_silent():
    rows = [
        _row(raw_row_hash="hash_valid"),
        _row(raw_row_hash="hash_missing_class", draft_class=None),
        _row(raw_row_hash="hash_blank_analyst", analyst="  "),
        _row(raw_row_hash="hash_malformed_analyst", analyst="daniel_jeremiah"),
        _row(raw_row_hash="hash_source_type", source_type="ranking"),
        _row(raw_row_hash="hash_exact_null", projected_pick=None),
        _row(raw_row_hash="hash_exact_too_high", projected_pick=DRAFT_PICK_MAX + 1),
        _row(
            raw_row_hash="hash_bad_round",
            projection_status="round_only",
            projected_pick=None,
            projected_round=8,
        ),
        _row(
            raw_row_hash="hash_udfa_with_pick",
            projection_status="udfa",
            projected_pick=250,
            projected_round=None,
        ),
        _row(raw_row_hash="hash_bad_date", published_date="04/01/2026"),
        _row(raw_row_hash="hash_valid", prospect_name_raw="Duplicate Hash"),
    ]

    result = load_curated_json_payload(_payload(*rows))

    assert [row.raw_row_hash for row in result.rows] == ["hash_valid"]
    assert len(result.dropped_rows) == len(rows) - 1
    reasons = " | ".join(_drop_reasons(result)).lower()
    for expected in (
        "draft_class",
        "analyst",
        "source_type",
        "exact_pick",
        "projected_pick",
        "round_only",
        "projected_round",
        "udfa",
        "published_date",
        "duplicate raw_row_hash",
    ):
        assert expected in reasons


def test_missing_required_row_fields_are_dropped_not_crashed():
    """Fail-closed: a curated row missing a directly-indexed required field must
    be dropped with an explicit reason, never crash the loader (KeyError)."""
    for missing in (
        "source_id",
        "source_snapshot_id",
        "raw_row_hash",
        "prospect_name_raw",
        "position_raw",
        "school_raw",
    ):
        row = _row(raw_row_hash=f"hash_missing_{missing}")
        del row[missing]

        result = load_curated_json_payload(_payload(row))

        assert result.rows == []
        assert len(result.dropped_rows) == 1
        assert missing in result.dropped_rows[0].reason


def test_big_board_rows_are_excluded_with_explicit_reason():
    result = load_curated_json_payload(
        _payload(
            _row(
                raw_row_hash="hash_big_board",
                source_type="big_board",
                projected_pick=5,
                projected_round=1,
            )
        )
    )

    assert result.rows == []
    assert len(result.dropped_rows) == 1
    assert result.dropped_rows[0].raw_row_hash == "hash_big_board"
    assert "big_board" in result.dropped_rows[0].reason
    assert "excluded" in result.dropped_rows[0].reason.lower()


def test_adapter_builds_read_only_normalized_college_prospect_row():
    result = load_curated_json_payload(
        _payload(
            _row(
                raw_row_hash="hash_adapter",
                prospect_name_raw="Carnell Tate",
                position_raw="WR",
                school_raw="Ohio State",
                draft_class=2027,
                source_id="the_athletic",
                source_snapshot_id="the_athletic:2026-04-01:v1",
            )
        )
    )
    curated = result.rows[0]

    s3_row = adapt_curated_row_to_s3(curated)

    assert isinstance(s3_row, NormalizedCollegeProspectRow)
    assert s3_row.raw_name == "Carnell Tate"
    assert s3_row.full_name == "Carnell Tate"
    assert s3_row.normalized_name == "carnell tate"
    assert s3_row.position == "WR"
    assert s3_row.position_group == "WR"
    assert s3_row.current_school == "Ohio State"
    assert s3_row.draft_class == 2027
    assert s3_row.source == "s1_mock_consensus:the_athletic"
    assert s3_row.source_record_id == "the_athletic:hash_adapter"
    assert s3_row.source_snapshot_id == "the_athletic:2026-04-01:v1"
    assert s3_row.id_provenance.model_dump() == {
        "cfbd_athlete_id": None,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
    }
