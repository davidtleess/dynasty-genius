"""Subsystem 4 metric + bridge-gate contract tests (§5.4, §11.2)."""
from __future__ import annotations

import pytest

from src.dynasty_genius.eval import backtest_mock_draft as bmd
from src.dynasty_genius.identity.prospect_nfl_bridge import (
    CollegeProspectBridge,
    ProspectNflBridgeEntry,
)

UUID_A = "cpr_10000000-0000-4000-8000-000000000001"
UUID_B = "cpr_10000000-0000-4000-8000-000000000002"
UUID_C = "cpr_10000000-0000-4000-8000-000000000003"
UUID_D = "cpr_10000000-0000-4000-8000-000000000004"
UUID_E = "cpr_10000000-0000-4000-8000-000000000005"
UUID_F = "cpr_10000000-0000-4000-8000-000000000006"


ROUND_BUCKETS = ["R1-early", "R1-mid", "R1-late", "R2", "R3", "Day3", "UDFA"]


def _coverage(**overrides) -> dict:
    coverage = {
        "consensus_unbridged_count": 0,
        "confirmed_class_unbridged_count": 0,
        "orphan_bridges_detected": [],
    }
    coverage.update(overrides)
    return coverage


def _evaluate_bridge_gates(coverage: dict):
    return bmd.evaluate_bridge_gates(coverage)


def _consensus(
    prospect_uuid: str,
    projected_pick_median: float | None,
    *,
    abstention_tier: str = "exact_pick",
) -> bmd.ProspectConsensus:
    return bmd.ProspectConsensus(
        prospect_uuid=prospect_uuid,
        projected_pick_median=projected_pick_median,
        projected_pick_iqr=4.0 if projected_pick_median is not None else None,
        projected_pick_min=(
            int(projected_pick_median) if projected_pick_median is not None else None
        ),
        projected_pick_max=(
            int(projected_pick_median) if projected_pick_median is not None else None
        ),
        n_sources=5 if abstention_tier != "abstain" else 2,
        n_unique_analysts=5 if abstention_tier != "abstain" else 2,
        snapshot_ids_used=[f"snapshot_{prospect_uuid[-4:]}"],
        staleness_days=2.0,
        abstention_tier=abstention_tier,
        abstention_reason=(
            None if abstention_tier != "abstain" else "abstain: insufficient sources"
        ),
    )


def _round_for_pick(pick_no: int | None) -> int | None:
    if pick_no is None:
        return None
    if pick_no <= 32:
        return 1
    if pick_no <= 64:
        return 2
    if pick_no <= 105:
        return 3
    return min(7, ((pick_no - 1) // 32) + 1)


def _outcome(
    prospect_uuid: str,
    *,
    pick_no: int | None,
    position: str = "WR",
    udfa: bool = False,
) -> bmd.RealizedOutcome:
    return bmd.RealizedOutcome(
        prospect_uuid=prospect_uuid,
        gsis_id=None if udfa else f"00-{prospect_uuid[-4:]}",
        pfr_id=None,
        draft_year=2025,
        draft_pick_no=pick_no,
        draft_round=_round_for_pick(pick_no),
        nfl_team=None if udfa else "TEN",
        udfa=udfa,
        unbridged_prospect=False,
        bridge_stale_warning=False,
        warnings=[],
        evidence_full_name=f"Prospect {prospect_uuid[-4:]}",
        evidence_position=position,
        evidence_college="Test U",
    )


def _bridge_entry(
    prospect_uuid: str,
    *,
    pick_no: int | None,
    position: str = "WR",
    udfa: bool = False,
) -> ProspectNflBridgeEntry:
    return ProspectNflBridgeEntry.model_validate(
        {
            "prospect_uuid": prospect_uuid,
            "gsis_id": None if udfa else f"00-{prospect_uuid[-4:]}",
            "pfr_id": None,
            "draft_year": 2025,
            "draft_pick_no": pick_no,
            "draft_round": _round_for_pick(pick_no),
            "nfl_team": None if udfa else "TEN",
            "udfa": udfa,
            "nflreadr_source": "nflreadpy.draft_picks",
            "nflreadr_season": 2025,
            "draft_truth_content_hash": "hash_2025_v1",
            "nflreadr_fetched_at": "2026-05-29T12:00:00Z",
            "evidence_snapshot": (
                None
                if udfa
                else {
                    "full_name": f"Prospect {prospect_uuid[-4:]}",
                    "position": position,
                    "college": "Test U",
                }
            ),
            "event_id": f"ev_{prospect_uuid[-4:]}",
            "decided_at": "2026-05-29T12:00:00Z",
            "reviewer_id": "davidleess",
            "decision": "udfa" if udfa else "confirm",
            "note": None,
        }
    )


def _bridge_for_outcomes(outcomes: list[bmd.RealizedOutcome]) -> CollegeProspectBridge:
    return CollegeProspectBridge(
        metadata={"draft_year": 2025, "schema_version": "prospect_nfl_bridge_v1.0.0"},
        entries=[
            _bridge_entry(
                outcome.prospect_uuid,
                pick_no=outcome.draft_pick_no,
                position=outcome.evidence_position or "WR",
                udfa=outcome.udfa,
            )
            for outcome in outcomes
        ],
    )


def _joined_rows() -> list[tuple[bmd.ProspectConsensus, bmd.RealizedOutcome]]:
    """Golden-answer fixture spanning all §5.4 metric universes."""
    return [
        (_consensus(UUID_A, 5.0), _outcome(UUID_A, pick_no=1, position="QB")),
        (
            _consensus(UUID_B, 20.0, abstention_tier="round_tier_only"),
            _outcome(UUID_B, pick_no=30, position="WR"),
        ),
        (_consensus(UUID_C, 32.5), _outcome(UUID_C, pick_no=40, position="RB")),
        (
            _consensus(UUID_D, None, abstention_tier="abstain"),
            _outcome(UUID_D, pick_no=80, position="TE"),
        ),
        (_consensus(UUID_E, 50.0), _outcome(UUID_E, pick_no=None, udfa=True)),
    ]


def _metrics(joined_rows=None, n_total=6):
    rows = _joined_rows() if joined_rows is None else joined_rows
    return bmd.compute_metrics(
        rows,
        n_prospects_total_in_class=n_total,
        bridge=_bridge_for_outcomes([outcome for _consensus, outcome in rows]),
    )


def test_evaluate_bridge_gates_passes_when_all_counts_zero():
    assert _evaluate_bridge_gates(_coverage()) is None


def test_evaluate_bridge_gates_blocks_on_consensus_unbridged():
    assert _evaluate_bridge_gates(_coverage(consensus_unbridged_count=1)) == [
        "consensus_unbridged"
    ]


def test_evaluate_bridge_gates_blocks_on_confirmed_class_unbridged():
    assert _evaluate_bridge_gates(_coverage(confirmed_class_unbridged_count=2)) == [
        "confirmed_class_unbridged"
    ]


def test_evaluate_bridge_gates_blocks_on_orphan_bridges():
    assert _evaluate_bridge_gates(_coverage(orphan_bridges_detected=[UUID_A])) == [
        "orphan_bridges_detected"
    ]


def test_evaluate_bridge_gates_combines_multiple_blockers():
    assert _evaluate_bridge_gates(
        _coverage(
            consensus_unbridged_count=1,
            confirmed_class_unbridged_count=2,
            orphan_bridges_detected=[UUID_A],
        )
    ) == [
        "consensus_unbridged",
        "confirmed_class_unbridged",
        "orphan_bridges_detected",
    ]


def test_compute_metrics_returns_shape_and_records_metric_version():
    result = _metrics()

    assert set(result) == {"metric_version", "metrics", "warnings"}
    assert result["metric_version"] == bmd.METRIC_VERSION
    assert set(result["metrics"]) == {
        "overall_pick_mae",
        "round_bucket_accuracy",
        "top_36_skill_recall",
        "udfa_false_positive_rate",
        "coverage_after_abstention",
        "early_pick_weighted_error",
        "per_bucket_breakdown",
    }


def test_overall_pick_mae_uses_drafted_and_projected_drafted_intersection():
    metrics = _metrics()["metrics"]

    assert metrics["overall_pick_mae"] == pytest.approx((4.0 + 10.0 + 7.5) / 3)


def test_round_bucket_accuracy_excludes_abstain_and_uses_round_half_up():
    metrics = _metrics()["metrics"]

    # A correct, B wrong, C correct because 32.5 -> round_half_up 33 -> R2,
    # E wrong because projected drafted but realized UDFA. D is abstain and excluded.
    assert metrics["round_bucket_accuracy"] == pytest.approx(2 / 4)


def test_top_36_skill_recall_uses_min_denominator_and_warns_on_incomplete_truth():
    result = _metrics()

    assert result["metrics"]["top_36_skill_recall"] == pytest.approx(1.0)
    assert "insufficient_truth_coverage" in result["warnings"]


def test_udfa_false_positive_rate_denominator_is_projected_drafted_only():
    metrics = _metrics()["metrics"]

    # A, B, C, and E are projected drafted by raw median in [1,257]; D abstains.
    # E is the lone realized-UDFA false positive.
    assert metrics["udfa_false_positive_rate"] == pytest.approx(1 / 4)


def test_coverage_after_abstention_uses_scored_over_confirmed_class_total():
    metrics = _metrics()["metrics"]

    # A, B, C, E are scored; D abstains; total confirmed class is supplied by caller.
    assert metrics["coverage_after_abstention"] == pytest.approx(4 / 6)


def test_early_pick_weighted_error_uses_inverse_realized_pick_weight():
    metrics = _metrics()["metrics"]
    numerator = (4.0 * 1.0) + (10.0 * (1 / 30)) + (7.5 * (1 / 40))
    denominator = 1.0 + (1 / 30) + (1 / 40)

    assert metrics["early_pick_weighted_error"] == pytest.approx(
        numerator / denominator
    )


def test_per_bucket_breakdown_populates_exact_bucket_set_and_counts():
    breakdown = _metrics()["metrics"]["per_bucket_breakdown"]

    assert list(breakdown) == ROUND_BUCKETS
    assert breakdown["R1-early"]["n_realized"] == 1
    assert breakdown["R1-late"]["n_realized"] == 1
    assert breakdown["R2"]["n_realized"] == 1
    assert breakdown["R3"]["n_realized"] == 1
    assert breakdown["UDFA"]["n_realized"] == 1
    assert breakdown["R1-early"]["n_scored"] == 1
    assert breakdown["R1-late"]["n_scored"] == 1
    assert breakdown["R2"]["n_scored"] == 1
    assert breakdown["UDFA"]["n_scored"] == 1
    assert breakdown["R3"]["n_scored"] == 0
