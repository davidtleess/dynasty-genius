"""Phase 23 W5b — cross-lane manual-review producer (pure, model+market aware).

This is the only place that emits ``market_package_requires_manual_review``. It
compares the MODEL's and the MARKET's directional read of a trade package and,
under the Q3=B policy, flags **opposite-directional disagreement** for manual
review. The comparison is scale-blind: each lane is reduced to a direction label
on its *own* scale via ``TRADE_PARITY_BAND`` — model and market magnitudes are
never subtracted from each other.

Pure module: no I/O. The route (`app/api/routes/trade_market.py`) hydrates model
xVAR, runs the model reconcile, derives coverage, and calls this producer. The
market-blind ``market_reconciler`` is untouched.

Design spec: docs/superpowers/specs/2026-06-22-w5b-cross-lane-manual-review-producer-design.md
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from src.dynasty_genius.models.engine_b_contract import TRADE_PARITY_BAND
from src.dynasty_genius.trade_lab.market_reconciler import MarketRealismWarning

# Normalizes the two `adjusted_favors` vocabularies (reconciler.py:120 no-overflow
# {side_a,side_b,neutral}; reconciler.py:180-184 overflow {david,counterparty,
# neutral}) to a single canonical direction. side_b == received-favored == david.
_MODEL_FAVOR_NORMALIZATION = {
    "side_b": "david",
    "david": "david",
    "side_a": "counterparty",
    "counterparty": "counterparty",
    "neutral": "neutral",
}

_DIRECTION_CODE = {"david": 1.0, "neutral": 0.0, "counterparty": -1.0}

# Locked message template (G3): fixed substitution set {David, Counterparty}; no
# dynamic per-asset prose. Symmetric naming — never asserts the model is correct.
_LABEL_DISPLAY = {"david": "David", "counterparty": "Counterparty"}
_MESSAGE_TEMPLATE = (
    "Model favors {model_label} but Market favors {market_label}. "
    "Manual review of the asset package is recommended."
)

_WARNING_CAVEATS = [
    "market_realism_warning_only",
    "market_overlay_display_only",
    "model_market_scales_not_comparable",
    "decision_supported_false",
]

# Q3=B (David-locked): emit ONLY on opposite directional labels.
_OPPOSITE_DIRECTIONAL = {("david", "counterparty"), ("counterparty", "david")}


@dataclass(frozen=True)
class CrossLaneReviewResult:
    """Outcome of the cross-lane review.

    ``warning`` is the emitted advisory (or ``None``). ``suppressed_reason`` is a
    per-lane set naming why the warning was fail-closed-suppressed on incomplete
    coverage (``model_coverage_incomplete`` / ``market_coverage_incomplete``); it
    is ``None`` for an emit and for an honest no-emit (agreement / neutral).
    """

    warning: Optional[MarketRealismWarning]
    suppressed_reason: Optional[frozenset[str]] = None


def _normalize_model_label(model_favors_raw: object) -> str:
    """Normalize a raw `adjusted_favors` token; fail loud on unknown/wrong-type."""
    if (
        not isinstance(model_favors_raw, str)
        or model_favors_raw not in _MODEL_FAVOR_NORMALIZATION
    ):
        raise ValueError(
            f"Unrecognized model_favors_raw token: {model_favors_raw!r}"
        )
    return _MODEL_FAVOR_NORMALIZATION[model_favors_raw]


def _all_finite(*values: float) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def _relative_delta(signed_delta: float, sent: float, received: float) -> float:
    max_side = max(sent, received)
    if max_side <= 0:
        return 0.0
    return abs(signed_delta) / max_side


def _market_label(
    market_delta_for_david: float,
    adjusted_market_sent: float,
    adjusted_market_received: float,
    parity_band: float,
) -> str:
    """Direction label on the market's own scale (within-band → neutral)."""
    relative = _relative_delta(
        market_delta_for_david, adjusted_market_sent, adjusted_market_received
    )
    if relative <= parity_band:
        return "neutral"
    return "david" if market_delta_for_david > 0 else "counterparty"


def evaluate_cross_lane_manual_review(
    *,
    model_favors_raw: object,
    model_coverage_complete: bool,
    model_delta_signed: float,
    adjusted_model_sent: float,
    adjusted_model_received: float,
    market_delta_for_david: float,
    adjusted_market_sent: float,
    adjusted_market_received: float,
    market_coverage_complete: bool,
    parity_band: float = TRADE_PARITY_BAND,
) -> CrossLaneReviewResult:
    """Emit ``market_package_requires_manual_review`` iff the lanes oppose (Q3=B).

    Fail-closed: a lane with incomplete coverage OR any non-finite numeric is
    ``unavailable`` and suppresses the warning with a per-lane reason. The model
    token is validated first (fail loud) so misuse never masquerades as a
    no-emit.
    """
    model_label = _normalize_model_label(model_favors_raw)

    # Fail-closed availability: coverage flags AND finiteness of each lane's
    # numerics. Never infer zero for missing/corrupt values.
    model_available = model_coverage_complete and _all_finite(
        model_delta_signed, adjusted_model_sent, adjusted_model_received
    )
    market_available = market_coverage_complete and _all_finite(
        market_delta_for_david, adjusted_market_sent, adjusted_market_received
    )

    if not model_available or not market_available:
        reasons: set[str] = set()
        if not model_available:
            reasons.add("model_coverage_incomplete")
        if not market_available:
            reasons.add("market_coverage_incomplete")
        return CrossLaneReviewResult(warning=None, suppressed_reason=frozenset(reasons))

    market_label = _market_label(
        market_delta_for_david,
        adjusted_market_sent,
        adjusted_market_received,
        parity_band,
    )

    if (model_label, market_label) not in _OPPOSITE_DIRECTIONAL:
        return CrossLaneReviewResult(warning=None, suppressed_reason=None)

    metrics = {
        "model_delta_signed": float(model_delta_signed),
        "adjusted_model_sent": float(adjusted_model_sent),
        "adjusted_model_received": float(adjusted_model_received),
        "model_relative_delta": _relative_delta(
            model_delta_signed, adjusted_model_sent, adjusted_model_received
        ),
        "model_direction_code": _DIRECTION_CODE[model_label],
        "market_delta_for_david": float(market_delta_for_david),
        "adjusted_market_sent": float(adjusted_market_sent),
        "adjusted_market_received": float(adjusted_market_received),
        "market_relative_delta": _relative_delta(
            market_delta_for_david, adjusted_market_sent, adjusted_market_received
        ),
        "market_direction_code": _DIRECTION_CODE[market_label],
        "parity_band": float(parity_band),
    }

    warning = MarketRealismWarning(
        warning_type="market_package_requires_manual_review",
        severity="advisory",
        message=_MESSAGE_TEMPLATE.format(
            model_label=_LABEL_DISPLAY[model_label],
            market_label=_LABEL_DISPLAY[market_label],
        ),
        metrics=metrics,
        caveats=list(_WARNING_CAVEATS),
    )
    return CrossLaneReviewResult(warning=warning, suppressed_reason=None)
