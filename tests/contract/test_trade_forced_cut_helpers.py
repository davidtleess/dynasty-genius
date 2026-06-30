"""Trade Lab forced-cut penalty range helpers and additive model fields.

Task 1 RED only: these tests pin pure math and response-shape contracts before
the reconciler is rewired to RC v1.
"""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import TRADE_PARITY_BAND
from src.dynasty_genius.trade_lab import reconciler
from src.dynasty_genius.trade_lab.evaluator import (
    TradeAsset,
    TradeEvaluation,
    TradeSide,
)
from src.dynasty_genius.trade_lab.reconciler import (
    RosterPenaltySummary,
    TradeRosterReconciliation,
)


def _side(value: float) -> TradeSide:
    return TradeSide(
        assets=[TradeAsset(player_id=f"p{value}", xvar=value, position="WR")],
        xvar_sum=value,
        consolidation_factor=1.0,
        side_value=value,
    )


def _base_evaluation(*, sent: float = 100.0, received: float = 105.0) -> TradeEvaluation:
    return TradeEvaluation(
        side_a=_side(sent),
        side_b=_side(received),
        fairness_delta=abs(sent - received),
        within_parity_band=True,
        favors="neutral",
        favors_xvar_margin=None,
        caveats=[],
    )


@pytest.mark.parametrize(
    ("received_range", "expected"),
    [
        ((95.0, 105.0), "neutral"),
        ((111.0, 111.0), "neutral"),
        ((112.0, 130.0), "david"),
        ((70.0, 85.0), "counterparty"),
        ((85.0, 130.0), "uncertain_range_crosses_parity"),
    ],
)
def test_favors_status_uses_relative_parity_band_for_all_four_states(
    received_range: tuple[float, float],
    expected: str,
) -> None:
    """Parity threshold is delta <= band * max(sent, received), not sent*band."""
    assert hasattr(reconciler, "_favors_status")

    status = reconciler._favors_status(
        received_range,
        sent_value=100.0,
        parity_band=TRADE_PARITY_BAND,
    )

    assert status == expected


@pytest.mark.parametrize(
    ("received_range", "expected"),
    [
        ((120.0, 140.0), (20.0, 40.0)),
        ((90.0, 120.0), (0.0, 20.0)),
        ((50.0, 80.0), (20.0, 50.0)),
    ],
)
def test_fairness_delta_range_is_non_monotonic_around_sent_value(
    received_range: tuple[float, float],
    expected: tuple[float, float],
) -> None:
    """If sent is inside the received interval, the minimum delta is zero."""
    assert hasattr(reconciler, "_fairness_delta_range")

    assert reconciler._fairness_delta_range(100.0, received_range) == expected


def test_recovery_range_is_gross_minus_net_bounds() -> None:
    assert hasattr(reconciler, "_recovery_range")

    assert reconciler._recovery_range(20.0, (4.0, 16.0)) == (4.0, 16.0)


def test_roster_penalty_summary_has_additive_range_fields_with_safe_defaults() -> None:
    summary = RosterPenaltySummary(
        post_trade_total_players=21,
        post_trade_overflow=1,
        forced_cut_candidates=[],
        forced_cut_penalty_xvar=10.0,
        penalty_caveats=[],
        decision_supported=True,
    )

    assert summary.decision_supported is False
    assert summary.forced_cut_value_at_risk_range is None
    assert summary.forced_cut_recovery_range is None
    assert summary.pool_deficits == {}
    assert summary.penalty_status == "ok"


def test_trade_roster_reconciliation_has_additive_range_fields_with_safe_defaults() -> None:
    result = TradeRosterReconciliation(
        base_evaluation=_base_evaluation(),
        roster_penalty=RosterPenaltySummary(
            post_trade_total_players=20,
            post_trade_overflow=0,
            forced_cut_candidates=[],
            forced_cut_penalty_xvar=0.0,
            penalty_caveats=[],
            decision_supported=True,
        ),
        adjusted_david_received_value=105.0,
        adjusted_fairness_delta=5.0,
        adjusted_within_parity_band=True,
        adjusted_favors="neutral",
        decision_supported=True,
        caveats=[],
    )

    assert result.decision_supported is False
    assert result.roster_penalty.decision_supported is False
    assert result.adjusted_received_value_range is None
    assert result.adjusted_fairness_delta_range is None
    assert result.adjusted_favors_status == "neutral"


def test_blocked_penalty_status_allows_null_ranges_without_fabricated_zero() -> None:
    summary = RosterPenaltySummary(
        post_trade_total_players=0,
        post_trade_overflow=0,
        forced_cut_candidates=[],
        forced_cut_penalty_xvar=0.0,
        penalty_caveats=["capacity_audit_blocked"],
        penalty_status="blocked",
    )

    assert summary.forced_cut_value_at_risk_range is None
    assert summary.forced_cut_recovery_range is None
