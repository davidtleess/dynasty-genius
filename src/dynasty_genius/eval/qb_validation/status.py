"""QB-1 comparison-status decision function, model lane (F30).

Spec rows implemented here (v8, SHA 8fa244c1…): the model-lane ``support_status``
vocabulary {supported, not_separable, contradicted, unsupported_power}, evaluated
as a total, ordered function — the power gate FIRST, then direction, then the
separability conjunction. ``supported`` requires ALL of: the fold floor, the
pooled delta in the registered direction ≥ 0.05 Spearman units, the CI95
excluding zero, and BH-FDR survival; any missing conjunct degrades to
``not_separable`` (conservative), never upgrades.

The H5 lane's disjoint vocabulary (market_noninferior / market_superior /
model_superior / inconclusive / unsupported_power, the NI margin machinery, and
``ci_p_disagreement``) is a LATER slice: its behavioral RED rows are not yet
authored, so this module refuses H5 payloads with a named reason rather than
shipping unpinned behavior. GREEN discipline: red-driven, never speculative.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure

# Model-lane fold floor: ≥5 of 8 evaluable folds (spec D3 inference contract).
MODEL_LANE_FOLD_FLOOR = 5

# The registered model lane has exactly 8 folds (t ∈ {2018..2025}); a higher
# evaluable count is impossible evidence, not a stronger result.
MODEL_LANE_FOLD_TOTAL = 8

# The registered materiality floor, Spearman units (spec D3).
MATERIALITY_FLOOR = 0.05


def evaluate_power_and_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Assign the single model-lane ``support_status`` for one comparison (F30).

    Ordered, total, no discretion:
    1. ``unsupported_power`` — evaluable folds below the lane floor (the power
       gate precedes every substantive label).
    2. ``contradicted`` — a zero-excluding CI in the WRONG registered direction;
       named, never folded into any other status.
    3. ``supported`` — fold floor AND registered direction AND pooled delta
       ≥ 0.05 AND CI95 excluding zero AND BH-FDR survival, all present.
    4. ``not_separable`` — everything else (CI spanning zero, failed BH-FDR, or
       a conjunct missing from the payload; conservative by construction).
    """
    lane = payload.get("lane")
    if lane is not None:
        # Closed lane vocabulary (round-3 B1): an explicit lane must be one of
        # the two registered lanes. H5 in ANY spelling refuses named; an
        # unknown or non-string lane refuses named — nothing falls open into
        # model support. An omitted lane keeps the authored model default.
        normalized = lane.strip().lower() if isinstance(lane, str) else None
        if normalized == "h5":
            raise QBValidationFailure(
                "h5_status_not_implemented",
                "the H5 status decision function lands with its own behavioral "
                "RED slice; refusing rather than emitting unpinned vocabulary",
            )
        if normalized != "model":
            raise QBValidationFailure(
                "status_payload_malformed",
                f"unknown lane {lane!r}; the registered lanes are 'model' and 'h5'",
            )
    if "fold_floor" in payload:
        # The floor is registered policy (5/8 model-lane), not a payload knob.
        raise QBValidationFailure(
            "registration_override_refused",
            "fold_floor is pinned by the registration and may not be supplied",
        )

    folds = payload.get("folds")
    if folds is None:
        raise QBValidationFailure(
            "status_payload_incomplete", "comparison payload lacks 'folds'"
        )
    if isinstance(folds, bool) or not isinstance(folds, int) or folds < 0:
        raise QBValidationFailure(
            "status_payload_malformed", f"folds must be a non-negative int, got {folds!r}"
        )
    if folds > MODEL_LANE_FOLD_TOTAL:
        raise QBValidationFailure(
            "status_payload_malformed",
            f"folds {folds} exceeds the registered {MODEL_LANE_FOLD_TOTAL}-fold lane",
        )
    for flag in ("ci_excludes_zero", "passes_fdr"):
        value = payload.get(flag)
        if value is not None and not isinstance(value, bool):
            # Truthy strings must never stand in for the CI/FDR conjuncts
            # (round-2 B2: "false" is truthy). None reads as conjunct-absent
            # and degrades conservatively like a missing key.
            raise QBValidationFailure(
                "status_payload_malformed",
                f"{flag} must be a bool, got {value!r}",
            )

    pooled_delta = payload.get("pooled_delta")
    if pooled_delta is not None:
        if isinstance(pooled_delta, bool) or not isinstance(pooled_delta, (int, float)):
            raise QBValidationFailure(
                "status_payload_malformed",
                f"pooled_delta must be numeric, got {pooled_delta!r}",
            )
        if math.isnan(pooled_delta) or math.isinf(pooled_delta):
            raise QBValidationFailure(
                "non_finite_evidence",
                f"pooled_delta {pooled_delta!r} is not finite; non-finite values "
                "are degenerate inputs, never support",
            )

    result: dict[str, Any] = {
        "decision_supported": False,
        "folds": folds,
        "fold_floor": MODEL_LANE_FOLD_FLOOR,
    }

    if folds < MODEL_LANE_FOLD_FLOOR:
        result["support_status"] = "unsupported_power"
        return result

    ci_excludes_zero = payload.get("ci_excludes_zero", False)
    direction = payload.get("direction")

    if ci_excludes_zero and direction == "wrong":
        result["support_status"] = "contradicted"
        return result

    passes_fdr = payload.get("passes_fdr", False)
    if (
        ci_excludes_zero
        and direction == "registered"
        and pooled_delta is not None
        and float(pooled_delta) >= MATERIALITY_FLOOR
        and passes_fdr is True
    ):
        result["support_status"] = "supported"
        return result

    result["support_status"] = "not_separable"
    return result
