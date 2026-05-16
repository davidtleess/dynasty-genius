"""Validation-only TE taxonomy features for Phase 13.3.2."""
from __future__ import annotations

from typing import Any

TAXONOMY_VERSION = "0.1.0"

DETACHED_ALIGNMENT_MIN = 0.40
INLINE_ALIGNMENT_MIN = 0.70
BALANCED_INLINE_MIN = 0.55
BALANCED_INLINE_MAX = 0.70
RECEIVING_YPRR_MIN = 1.80
RECEIVING_TPRR_MIN = 0.18
ROLE_RISK_YPRR_MAX = 1.40
ROLE_RISK_TPRR_MAX = 0.16


def _num(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def _has_receiving_utility(row: dict[str, Any]) -> bool:
    yprr = _num(row.get("yprr_computed"))
    tprr = _num(row.get("tprr_computed"))
    return (
        yprr is not None
        and tprr is not None
        and yprr >= RECEIVING_YPRR_MIN
        and tprr >= RECEIVING_TPRR_MIN
    )


def _has_low_receiving_utility(row: dict[str, Any]) -> bool:
    yprr = _num(row.get("yprr_computed"))
    tprr = _num(row.get("tprr_computed"))
    return (
        yprr is not None
        and tprr is not None
        and yprr <= ROLE_RISK_YPRR_MAX
        and tprr <= ROLE_RISK_TPRR_MAX
    )


def classify_alignment_archetype(row: dict[str, Any]) -> str | None:
    detached = _num(row.get("detached_rate_from_snaps"))
    inline = _num(row.get("inline_rate_from_snaps"))
    if detached is None or inline is None:
        return None
    if detached >= DETACHED_ALIGNMENT_MIN and inline < BALANCED_INLINE_MIN:
        return "detached"
    if inline >= INLINE_ALIGNMENT_MIN:
        return "inline"
    return "balanced"


def classify_fantasy_role_archetype(row: dict[str, Any]) -> str | None:
    if row.get("labeling_status") != "labeled":
        return None
    alignment = classify_alignment_archetype(row)
    has_receiving_utility = _has_receiving_utility(row)
    has_low_receiving_utility = _has_low_receiving_utility(row)
    if alignment == "detached" and has_receiving_utility:
        return "receiving_specialist"
    if alignment == "detached" and has_low_receiving_utility:
        return "role_risk"
    if alignment == "balanced" and has_receiving_utility:
        return "complete_te"
    if alignment in {"balanced", "inline"} and has_low_receiving_utility:
        return "blocking_specialist"
    if alignment == "inline":
        return "blocking_specialist"
    return "unclear_role"


def derive_te_taxonomy_features(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("labeling_status") != "labeled":
        return {
            "alignment_archetype": None,
            "fantasy_role_archetype": None,
            "taxonomy_status": "unavailable",
            "taxonomy_version": TAXONOMY_VERSION,
        }
    return {
        "alignment_archetype": classify_alignment_archetype(row),
        "fantasy_role_archetype": classify_fantasy_role_archetype(row),
        "taxonomy_status": "labeled",
        "taxonomy_version": TAXONOMY_VERSION,
    }
