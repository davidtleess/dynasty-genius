"""Subsystem 4 ProspectConsensus aggregation contract tests (§5.2, §5.3)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.dynasty_genius.eval.backtest_mock_draft import (
    NormalizedPick,
    ProspectConsensus,
    aggregate_per_prospect,
)


def _pick(
    prospect_uuid: str = "cpr_aaaaaaaa-0000-4000-8000-000000000001",
    *,
    pick_no: int = 12,
    source_label: str = "source_a",
    analyst: str = "analyst_a",
    published_date: str = "2025-04-01",
    snapshot_id: str | None = None,
) -> NormalizedPick:
    snapshot_id = snapshot_id or f"snapshot_{source_label}_{analyst}_{pick_no}"
    return NormalizedPick(
        pick_no=pick_no,
        original_prospect_uuid=prospect_uuid,
        resolved_prospect_uuid=prospect_uuid,
        redirect_applied=False,
        snapshot_id=snapshot_id,
        metadata_tuple_key=f"{source_label}|{analyst}|{published_date}|v1",
        published_date=published_date,
        source_label=source_label,
    )


def test_prospect_consensus_schema_accepts_spec_shape_and_forbids_extra():
    consensus = ProspectConsensus.model_validate(
        {
            "prospect_uuid": "cpr_aaaaaaaa-0000-4000-8000-000000000001",
            "projected_pick_median": 12,
            "projected_pick_iqr": 4.0,
            "projected_pick_min": 10,
            "projected_pick_max": 18,
            "n_sources": 5,
            "n_unique_analysts": 5,
            "snapshot_ids_used": ["snapshot_a", "snapshot_b"],
            "staleness_days": 4.0,
            "abstention_tier": "exact_pick",
            "abstention_reason": None,
        }
    )

    assert consensus.prospect_uuid == "cpr_aaaaaaaa-0000-4000-8000-000000000001"
    assert consensus.projected_pick_median == 12
    assert consensus.projected_pick_iqr == 4.0
    assert consensus.n_sources == 5
    assert consensus.n_unique_analysts == 5
    assert consensus.abstention_tier == "exact_pick"

    bad = consensus.model_dump()
    bad["unexpected"] = "reject"
    with pytest.raises(ValidationError):
        ProspectConsensus.model_validate(bad)


def test_aggregate_counts_distinct_sources_and_analysts():
    uuid = "cpr_bbbbbbbb-0000-4000-8000-000000000001"
    picks = [
        _pick(uuid, pick_no=10, source_label="source_a", analyst="same"),
        _pick(uuid, pick_no=12, source_label="source_a", analyst="same"),
        _pick(uuid, pick_no=14, source_label="source_b", analyst="same"),
        _pick(uuid, pick_no=16, source_label="source_c", analyst="other"),
    ]

    consensus = aggregate_per_prospect(picks, draft_date="2025-04-24")[uuid]

    assert consensus.n_sources == 3
    assert consensus.n_unique_analysts == 2
    assert consensus.abstention_tier == "round_tier_only"


def test_abstention_gate_under_three_sources_abstains_with_reason():
    uuid = "cpr_cccccccc-0000-4000-8000-000000000001"
    picks = [
        _pick(uuid, pick_no=10, source_label="source_a", analyst="analyst_a"),
        _pick(uuid, pick_no=18, source_label="source_b", analyst="analyst_b"),
    ]

    consensus = aggregate_per_prospect(picks, draft_date="2025-04-24")[uuid]

    assert consensus.abstention_tier == "abstain"
    assert consensus.projected_pick_median is None
    assert consensus.abstention_reason
    assert "n_sources" in consensus.abstention_reason


def test_abstention_gate_three_to_four_sources_round_tier_only_with_reason():
    uuid = "cpr_dddddddd-0000-4000-8000-000000000001"
    picks = [
        _pick(uuid, pick_no=10, source_label="source_a", analyst="analyst_a"),
        _pick(uuid, pick_no=12, source_label="source_b", analyst="analyst_b"),
        _pick(uuid, pick_no=14, source_label="source_c", analyst="analyst_c"),
        _pick(uuid, pick_no=16, source_label="source_d", analyst="analyst_d"),
    ]

    consensus = aggregate_per_prospect(picks, draft_date="2025-04-24")[uuid]

    assert consensus.abstention_tier == "round_tier_only"
    assert consensus.projected_pick_median == 13
    assert consensus.abstention_reason
    assert "round_tier_only" in consensus.abstention_reason


def test_abstention_gate_five_sources_low_iqr_exact_pick():
    uuid = "cpr_eeeeeeee-0000-4000-8000-000000000001"
    picks = [
        _pick(uuid, pick_no=10, source_label="source_a", analyst="analyst_a"),
        _pick(uuid, pick_no=12, source_label="source_b", analyst="analyst_b"),
        _pick(uuid, pick_no=13, source_label="source_c", analyst="analyst_c"),
        _pick(uuid, pick_no=14, source_label="source_d", analyst="analyst_d"),
        _pick(uuid, pick_no=16, source_label="source_e", analyst="analyst_e"),
    ]

    consensus = aggregate_per_prospect(picks, draft_date="2025-04-24")[uuid]

    assert consensus.abstention_tier == "exact_pick"
    assert consensus.projected_pick_median == 13
    assert consensus.projected_pick_min == 10
    assert consensus.projected_pick_max == 16
    assert consensus.projected_pick_iqr <= 6
    assert consensus.abstention_reason is None


def test_abstention_gate_five_sources_high_iqr_falls_back_to_round_tier_only():
    uuid = "cpr_ffffffff-0000-4000-8000-000000000001"
    picks = [
        _pick(uuid, pick_no=1, source_label="source_a", analyst="analyst_a"),
        _pick(uuid, pick_no=20, source_label="source_b", analyst="analyst_b"),
        _pick(uuid, pick_no=40, source_label="source_c", analyst="analyst_c"),
        _pick(uuid, pick_no=80, source_label="source_d", analyst="analyst_d"),
        _pick(uuid, pick_no=120, source_label="source_e", analyst="analyst_e"),
    ]

    consensus = aggregate_per_prospect(picks, draft_date="2025-04-24")[uuid]

    assert consensus.abstention_tier == "round_tier_only"
    assert consensus.projected_pick_iqr > 6
    assert consensus.abstention_reason
    assert "iqr" in consensus.abstention_reason.lower()


def test_dispersion_threshold_is_configurable():
    uuid = "cpr_11111111-0000-4000-8000-000000000001"
    picks = [
        _pick(uuid, pick_no=10, source_label="source_a", analyst="analyst_a"),
        _pick(uuid, pick_no=12, source_label="source_b", analyst="analyst_b"),
        _pick(uuid, pick_no=13, source_label="source_c", analyst="analyst_c"),
        _pick(uuid, pick_no=14, source_label="source_d", analyst="analyst_d"),
        _pick(uuid, pick_no=16, source_label="source_e", analyst="analyst_e"),
    ]

    strict = aggregate_per_prospect(
        picks,
        draft_date="2025-04-24",
        dispersion_threshold=1,
    )[uuid]
    default = aggregate_per_prospect(picks, draft_date="2025-04-24")[uuid]

    assert strict.abstention_tier == "round_tier_only"
    assert strict.abstention_reason
    assert "dispersion_threshold=1" in strict.abstention_reason
    assert default.abstention_tier == "exact_pick"


def test_staleness_days_uses_most_recent_snapshot_whole_calendar_days():
    uuid = "cpr_22222222-0000-4000-8000-000000000001"
    picks = [
        _pick(
            uuid,
            pick_no=10,
            source_label="source_a",
            analyst="analyst_a",
            published_date="2025-04-01",
        ),
        _pick(
            uuid,
            pick_no=12,
            source_label="source_b",
            analyst="analyst_b",
            published_date="2025-04-20",
        ),
        _pick(
            uuid,
            pick_no=14,
            source_label="source_c",
            analyst="analyst_c",
            published_date="2025-04-18",
        ),
    ]

    consensus = aggregate_per_prospect(picks, draft_date="2025-04-24")[uuid]

    assert consensus.staleness_days == 4.0


def test_empty_normalized_picks_returns_empty_consensus_map():
    assert aggregate_per_prospect([], draft_date="2025-04-24") == {}
