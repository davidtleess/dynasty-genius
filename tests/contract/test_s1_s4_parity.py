"""S1/S4 parity RED for delegating raw consensus statistics."""
from __future__ import annotations

from collections.abc import Iterable

from src.dynasty_genius.eval import backtest_mock_draft as bmd
from src.dynasty_genius.mock_consensus import consensus_math


def _pick(
    prospect_uuid: str,
    *,
    pick_no: int,
    source_label: str,
    analyst: str,
    snapshot_id: str,
    published_date: str = "2025-04-01",
) -> bmd.NormalizedPick:
    return bmd.NormalizedPick(
        pick_no=pick_no,
        original_prospect_uuid=prospect_uuid,
        resolved_prospect_uuid=prospect_uuid,
        redirect_applied=False,
        snapshot_id=snapshot_id,
        metadata_tuple_key=f"{source_label}|{analyst}|{published_date}|v1",
        published_date=published_date,
        source_label=source_label,
    )


def _picks_for_policy_path(
    prospect_uuid: str,
    pick_numbers: Iterable[int],
    *,
    snapshot_prefix: str,
) -> list[bmd.NormalizedPick]:
    return [
        _pick(
            prospect_uuid,
            pick_no=pick_no,
            source_label=f"source_{idx}",
            analyst=f"analyst_{idx}",
            snapshot_id=f"{snapshot_prefix}_{idx}",
        )
        for idx, pick_no in enumerate(pick_numbers, start=1)
    ]


def test_aggregate_per_prospect_delegates_raw_stats_to_s1_math(monkeypatch):
    uuid = "cpr_delegate-0000-4000-8000-000000000001"
    calls: list[tuple[list[consensus_math.ConsensusObservation], str]] = []
    original = consensus_math.compute_consensus_stats

    def spy(
        observations: list[consensus_math.ConsensusObservation],
        *,
        as_of: str,
    ) -> consensus_math.ConsensusStats:
        calls.append((list(observations), as_of))
        return original(observations, as_of=as_of)

    monkeypatch.setattr(consensus_math, "compute_consensus_stats", spy)

    bmd.aggregate_per_prospect(
        _picks_for_policy_path(uuid, [10, 12, 13, 14, 16], snapshot_prefix="delegate"),
        draft_date="2025-04-24",
    )

    assert len(calls) == 1
    observations, as_of = calls[0]
    assert as_of == "2025-04-24"
    assert [obs.pick_no for obs in observations] == [10, 12, 13, 14, 16]
    assert {obs.source_id for obs in observations} == {
        "source_1",
        "source_2",
        "source_3",
        "source_4",
        "source_5",
    }


def test_s4_characterization_outputs_remain_stable_across_policy_paths():
    abstain_uuid = "cpr_abstain0-0000-4000-8000-000000000001"
    round_uuid = "cpr_round000-0000-4000-8000-000000000001"
    exact_uuid = "cpr_exact000-0000-4000-8000-000000000001"
    high_iqr_uuid = "cpr_highiqr0-0000-4000-8000-000000000001"
    picks = (
        _picks_for_policy_path(abstain_uuid, [10, 18], snapshot_prefix="abstain")
        + _picks_for_policy_path(round_uuid, [10, 12, 14, 16], snapshot_prefix="round00")
        + _picks_for_policy_path(
            exact_uuid,
            [10, 12, 13, 14, 16],
            snapshot_prefix="exact00",
        )
        + _picks_for_policy_path(
            high_iqr_uuid,
            [1, 20, 40, 80, 120],
            snapshot_prefix="highiqr",
        )
    )

    actual = {
        uuid: consensus.model_dump()
        for uuid, consensus in bmd.aggregate_per_prospect(
            picks,
            draft_date="2025-04-24",
        ).items()
    }

    assert actual == {
        abstain_uuid: {
            "prospect_uuid": abstain_uuid,
            "projected_pick_median": None,
            "projected_pick_iqr": None,
            "projected_pick_min": None,
            "projected_pick_max": None,
            "n_sources": 2,
            "n_unique_analysts": 2,
            "snapshot_ids_used": ["abstain_1", "abstain_2"],
            "staleness_days": 23.0,
            "abstention_tier": "abstain",
            "abstention_reason": "abstain: n_sources=2 below minimum (>=3 required)",
        },
        round_uuid: {
            "prospect_uuid": round_uuid,
            "projected_pick_median": 13.0,
            "projected_pick_iqr": 5.0,
            "projected_pick_min": 10,
            "projected_pick_max": 16,
            "n_sources": 4,
            "n_unique_analysts": 4,
            "snapshot_ids_used": ["round00_1", "round00_2", "round00_3", "round00_4"],
            "staleness_days": 23.0,
            "abstention_tier": "round_tier_only",
            "abstention_reason": (
                "round_tier_only: n_sources=4 in [3,4]; exact-pick claim not "
                "permitted per spec §5.3"
            ),
        },
        exact_uuid: {
            "prospect_uuid": exact_uuid,
            "projected_pick_median": 13.0,
            "projected_pick_iqr": 4.0,
            "projected_pick_min": 10,
            "projected_pick_max": 16,
            "n_sources": 5,
            "n_unique_analysts": 5,
            "snapshot_ids_used": [
                "exact00_1",
                "exact00_2",
                "exact00_3",
                "exact00_4",
                "exact00_5",
            ],
            "staleness_days": 23.0,
            "abstention_tier": "exact_pick",
            "abstention_reason": None,
        },
        high_iqr_uuid: {
            "prospect_uuid": high_iqr_uuid,
            "projected_pick_median": 40.0,
            "projected_pick_iqr": 89.5,
            "projected_pick_min": 1,
            "projected_pick_max": 120,
            "n_sources": 5,
            "n_unique_analysts": 5,
            "snapshot_ids_used": [
                "highiqr_1",
                "highiqr_2",
                "highiqr_3",
                "highiqr_4",
                "highiqr_5",
            ],
            "staleness_days": 23.0,
            "abstention_tier": "round_tier_only",
            "abstention_reason": (
                "round_tier_only: IQR=89.50 exceeds dispersion_threshold=6"
            ),
        },
    }
