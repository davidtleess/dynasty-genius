"""Phase 23 W5b pure cross-lane manual-review producer contract tests.

RED  -> src/dynasty_genius/trade_lab/cross_lane_review.py does not exist yet.
GREEN -> pure producer emits only opposite-directional model/market warnings,
         fails closed on incomplete coverage, and keeps warnings advisory-only.
"""
from __future__ import annotations

import math
import re
from collections.abc import Iterable

import pytest

BANNED_WARNING_TERMS = {
    "accept",
    "reject",
    "approve",
    "block",
    "buy",
    "recommended",
    "fade",
    "sell",
    "target",
}


def _evaluate(**overrides):
    from src.dynasty_genius.trade_lab.cross_lane_review import (
        evaluate_cross_lane_manual_review,
    )

    kwargs = {
        "model_favors_raw": "david",
        "model_coverage_complete": True,
        "model_delta_signed": 20.0,
        "adjusted_model_sent": 80.0,
        "adjusted_model_received": 100.0,
        "market_delta_for_david": -20.0,
        "adjusted_market_sent": 110.0,
        "adjusted_market_received": 90.0,
        "market_coverage_complete": True,
        "parity_band": 0.10,
    }
    kwargs.update(overrides)
    return evaluate_cross_lane_manual_review(**kwargs)


def _suppressed_reasons(result) -> set[str]:
    reason = result.suppressed_reason
    if reason is None:
        return set()
    if isinstance(reason, str):
        return {reason}
    if isinstance(reason, Iterable):
        return set(reason)
    raise AssertionError(f"Unexpected suppressed_reason shape: {reason!r}")


def _assert_no_warning(result) -> None:
    assert result.warning is None


@pytest.mark.parametrize(
    ("model_favors_raw", "market_delta_for_david", "expected_message"),
    [
        (
            "david",
            -20.0,
            "Model favors David but Market favors Counterparty. The asset package "
            "is flagged for manual review.",
        ),
        (
            "side_b",
            -20.0,
            "Model favors David but Market favors Counterparty. The asset package "
            "is flagged for manual review.",
        ),
        (
            "counterparty",
            20.0,
            "Model favors Counterparty but Market favors David. The asset package "
            "is flagged for manual review.",
        ),
        (
            "side_a",
            20.0,
            "Model favors Counterparty but Market favors David. The asset package "
            "is flagged for manual review.",
        ),
    ],
)
def test_opposite_directional_labels_emit_manual_review_warning(
    model_favors_raw: str,
    market_delta_for_david: float,
    expected_message: str,
):
    result = _evaluate(
        model_favors_raw=model_favors_raw,
        market_delta_for_david=market_delta_for_david,
    )

    warning = result.warning
    assert warning is not None
    assert result.suppressed_reason is None
    assert warning.warning_type == "market_package_requires_manual_review"
    assert warning.severity == "advisory"
    assert warning.decision_supported is False
    assert warning.message == expected_message
    assert warning.caveats == [
        "market_realism_warning_only",
        "market_overlay_display_only",
        "model_market_scales_not_comparable",
        "decision_supported_false",
    ]


@pytest.mark.parametrize(
    ("model_favors_raw", "market_delta_for_david"),
    [
        ("david", 20.0),
        ("side_b", 20.0),
        ("counterparty", -20.0),
        ("side_a", -20.0),
        ("david", 0.0),
        ("neutral", -20.0),
    ],
)
def test_agreement_and_neutral_combinations_do_not_emit_under_q3_b(
    model_favors_raw: str,
    market_delta_for_david: float,
):
    result = _evaluate(
        model_favors_raw=model_favors_raw,
        market_delta_for_david=market_delta_for_david,
    )

    _assert_no_warning(result)
    assert result.suppressed_reason is None


def test_uncertain_model_range_token_is_neutral_canonical_and_suppresses_warning():
    from src.dynasty_genius.trade_lab.cross_lane_review import (
        _DIRECTION_CODE,
        _normalize_model_label,
    )

    assert _normalize_model_label("uncertain_range_crosses_parity") == "uncertain"
    assert _DIRECTION_CODE["uncertain"] == 0.0

    result = _evaluate(
        model_favors_raw="uncertain_range_crosses_parity",
        market_delta_for_david=-20.0,
    )

    _assert_no_warning(result)
    assert result.suppressed_reason is None


@pytest.mark.parametrize("bad_token", ["unknown", None, 1])
def test_unknown_or_wrong_type_model_favors_token_fails_loud(bad_token: object):
    with pytest.raises(ValueError):
        _evaluate(model_favors_raw=bad_token)


def test_market_band_boundary_is_neutral_at_band_and_directional_above_band():
    at_band = _evaluate(
        model_favors_raw="david",
        market_delta_for_david=-10.0,
        adjusted_market_sent=100.0,
        adjusted_market_received=90.0,
        parity_band=0.10,
    )
    _assert_no_warning(at_band)

    above_band = _evaluate(
        model_favors_raw="david",
        market_delta_for_david=-10.01,
        adjusted_market_sent=100.0,
        adjusted_market_received=89.99,
        parity_band=0.10,
    )

    assert above_band.warning is not None
    assert above_band.warning.metrics["market_direction_code"] == -1.0


def test_both_zero_market_sides_are_neutral_and_do_not_emit():
    result = _evaluate(
        model_favors_raw="david",
        market_delta_for_david=0.0,
        adjusted_market_sent=0.0,
        adjusted_market_received=0.0,
    )

    _assert_no_warning(result)
    assert result.suppressed_reason is None


@pytest.mark.parametrize(
    ("coverage_overrides", "expected_reasons"),
    [
        (
            {"model_coverage_complete": False},
            {"model_coverage_incomplete"},
        ),
        (
            {"market_coverage_complete": False},
            {"market_coverage_incomplete"},
        ),
        (
            {"model_coverage_complete": False, "market_coverage_complete": False},
            {"model_coverage_incomplete", "market_coverage_incomplete"},
        ),
    ],
)
def test_incomplete_coverage_suppresses_warning_with_per_lane_reason(
    coverage_overrides: dict[str, bool],
    expected_reasons: set[str],
):
    result = _evaluate(**coverage_overrides)

    _assert_no_warning(result)
    assert _suppressed_reasons(result) == expected_reasons


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_delta_signed", math.nan),
        ("adjusted_model_sent", math.inf),
        ("adjusted_model_received", -math.inf),
        ("market_delta_for_david", math.nan),
        ("adjusted_market_sent", math.inf),
        ("adjusted_market_received", -math.inf),
    ],
)
def test_non_finite_numeric_inputs_never_emit_warning(field: str, value: float):
    try:
        result = _evaluate(**{field: value})
    except ValueError:
        return

    _assert_no_warning(result)


def test_warning_metrics_are_float_only_and_reconstruct_decision():
    result = _evaluate(
        model_favors_raw="david",
        model_delta_signed=20.0,
        adjusted_model_sent=80.0,
        adjusted_model_received=100.0,
        market_delta_for_david=-20.0,
        adjusted_market_sent=110.0,
        adjusted_market_received=90.0,
        parity_band=0.10,
    )

    warning = result.warning
    assert warning is not None
    assert warning.metrics == {
        "model_delta_signed": 20.0,
        "adjusted_model_sent": 80.0,
        "adjusted_model_received": 100.0,
        "model_relative_delta": 0.2,
        "model_direction_code": 1.0,
        "market_delta_for_david": -20.0,
        "adjusted_market_sent": 110.0,
        "adjusted_market_received": 90.0,
        "market_relative_delta": pytest.approx(20.0 / 110.0),
        "market_direction_code": -1.0,
        "parity_band": 0.10,
    }
    assert all(isinstance(value, float) for value in warning.metrics.values())


def test_warning_message_and_caveats_exclude_banned_verdict_terms():
    result = _evaluate(model_favors_raw="david", market_delta_for_david=-20.0)

    warning = result.warning
    assert warning is not None
    serialized = f"{warning.message} {' '.join(warning.caveats)}".lower()
    for banned in BANNED_WARNING_TERMS:
        assert re.search(rf"\b{re.escape(banned)}\b", serialized) is None
