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
``ci_p_disagreement``) is IMPLEMENTED here per registration §9.2 and the frozen
TW14-QB1-1 execution RED: ``_evaluate_h5_status`` is the total-ordered H5
decision function, with impossible or internally contradictory evidence (excess
folds, non-probability p values, reversed CIs, delta/CI sign contradictions)
refusing named BEFORE any label (green-review G6). *(An earlier version of this
paragraph said the H5 lane was a later unimplemented slice that refuses — that
was true when written and became stale when the execution RED landed; corrected
per round-2 finding R2-G7.)*
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
        # the two registered lanes; an unknown or non-string lane refuses
        # named — nothing falls open into model support. An omitted lane keeps
        # the authored model default.
        normalized = lane.strip().lower() if isinstance(lane, str) else None
        if normalized == "h5":
            return _evaluate_h5_status(payload)
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


# ── H5 lane (registration §9.2, TW14-QB1-1 execution RED) ──────────────────────

# Registered H5 constants — registration-pinned policy, never payload knobs.
H5_LANE_FOLD_FLOOR = 3  # fold_floors.h5_lane (≥3 of 4)
H5_LANE_FOLD_TOTAL = 4  # fold_floors.h5_lane_total — the registered 4-fold lane
H5_MARGIN_M = 0.05  # h5.margin_m (positive magnitude)
H5_BOUNDARY_DELTA0 = -H5_MARGIN_M  # h5.boundary_delta0 (signed)
H5_FDR_Q = 0.10  # inference.fdr_q


def _evaluate_h5_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The H5 total-ordered ``support_status`` (registration §9.2, first match wins).

    1. ``unsupported_power`` — the H5 fold floor (≥3 of 4) unmet; power precedes
       every substantive label.
    2. ``model_superior`` — two-sided CI95 excludes zero in the model's favour
       (δ < 0) AND |δ| ≥ m.
    3. ``market_superior`` — CI95 excludes zero in the market's favour (δ > 0)
       AND |δ| ≥ m.
    4. ``market_noninferior`` — one-sided 95% lower bound of δ STRICTLY > δ₀
       AND BH-adjusted p_ni ≤ q. If the CI and p criteria disagree in EITHER
       direction the status is ``inconclusive`` with the named
       ``ci_p_disagreement`` flag — a registered rule, no discretion.
    5. ``inconclusive`` — everything else.

    ``ni_met`` and ``p_ni`` survive every status (NI retention, §9.2)."""
    for knob in ("fold_floor", "margin", "fdr_q"):
        if knob in payload:
            raise QBValidationFailure(
                "registration_override_refused",
                f"{knob} is pinned by the registration and may not be supplied",
            )
    folds = payload.get("folds")
    if isinstance(folds, bool) or not isinstance(folds, int) or folds < 0:
        raise QBValidationFailure(
            "status_payload_malformed", f"folds must be a non-negative int, got {folds!r}"
        )
    if folds > H5_LANE_FOLD_TOTAL:
        # Green-review G6: the registered H5 lane has exactly 4 folds
        # (fold_floors.h5_lane_total); a higher evaluable count is impossible
        # evidence, never a stronger result — refused before any label.
        raise QBValidationFailure(
            "status_payload_malformed",
            f"folds {folds} exceeds the registered {H5_LANE_FOLD_TOTAL}-fold h5 lane",
        )
    pooled_delta = payload.get("pooled_delta")
    ci95 = payload.get("ci95")
    lower_one_sided = payload.get("one_sided_lower_95")
    p_ni = payload.get("p_ni")
    adjusted_p_ni = payload.get("adjusted_p_ni")
    for name, value in (
        ("pooled_delta", pooled_delta),
        ("one_sided_lower_95", lower_one_sided),
        ("p_ni", p_ni),
        ("adjusted_p_ni", adjusted_p_ni),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise QBValidationFailure(
                "status_payload_malformed", f"{name} must be numeric, got {value!r}"
            )
        if not math.isfinite(value):
            raise QBValidationFailure(
                "status_payload_malformed", f"{name} must be finite, got {value!r}"
            )
    if (
        not isinstance(ci95, (list, tuple))
        or len(ci95) != 2
        or any(
            isinstance(bound, bool) or not isinstance(bound, (int, float))
            for bound in ci95
        )
        or any(not math.isfinite(bound) for bound in ci95)
    ):
        raise QBValidationFailure(
            "status_payload_malformed", f"ci95 must be two finite bounds, got {ci95!r}"
        )
    ci_low, ci_high = float(ci95[0]), float(ci95[1])

    # Green-review G6: impossible or internally contradictory evidence refuses
    # NAMED, before the ordered status function assigns any substantive label.
    for name, value in (("p_ni", p_ni), ("adjusted_p_ni", adjusted_p_ni)):
        if not 0.0 <= float(value) <= 1.0:
            raise QBValidationFailure(
                "status_payload_malformed",
                f"{name} {value!r} is outside [0, 1] — not a probability",
            )
    if ci_low > ci_high:
        raise QBValidationFailure(
            "status_payload_malformed",
            f"ci95 bounds reversed: low {ci_low} > high {ci_high}",
        )
    if not ci_low <= float(pooled_delta) <= ci_high:
        raise QBValidationFailure(
            "status_payload_malformed",
            f"pooled_delta {pooled_delta!r} lies outside its own ci95 "
            f"[{ci_low}, {ci_high}] — sign-contradictory evidence",
        )

    ci_pass = lower_one_sided > H5_BOUNDARY_DELTA0  # strictly greater than δ₀
    p_pass = adjusted_p_ni <= H5_FDR_Q
    result: dict[str, Any] = {
        "decision_supported": False,
        "p_ni": p_ni,
        "ni_met": bool(folds >= H5_LANE_FOLD_FLOOR and ci_pass and p_pass),
        "flags": [],
    }
    if folds < H5_LANE_FOLD_FLOOR:
        result["support_status"] = "unsupported_power"
        return result
    if ci_high < 0 and abs(pooled_delta) >= H5_MARGIN_M:
        result["support_status"] = "model_superior"
        return result
    if ci_low > 0 and abs(pooled_delta) >= H5_MARGIN_M:
        result["support_status"] = "market_superior"
        return result
    if ci_pass and p_pass:
        result["support_status"] = "market_noninferior"
        return result
    if ci_pass != p_pass:
        result["support_status"] = "inconclusive"
        result["flags"].append("ci_p_disagreement")
        return result
    result["support_status"] = "inconclusive"
    return result
