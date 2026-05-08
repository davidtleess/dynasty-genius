"""Framework compliance evaluator for governed agent deployment gates."""

from __future__ import annotations

import re
from typing import Any

QUANT_TERMS = [
    "draft capital",
    "draft_pick",
    "draft pick",
    "overall pick",
    "yprr",
    "yards per route run",
    "age",
    "age at entry",
    "snap percentage",
    "snap %",
    "dominator",
    "ras",
    "breakaway",
    "run blocking",
]

RECOMMENDATION_TERMS = [
    "smash accept",
    "accept",
    "reject",
    "buy",
    "sell",
    "trade for",
    "trade away",
    "draft",
    "take him",
    "recommend",
    "recommendation:",
]

ABORT_TERMS = ["anti_speed_abort", "abort any trade", "abort recommendations", "incomplete_required_features"]


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def framework_compliance_score(response: str, tool_output: str | None = None) -> dict[str, Any]:
    response = response or ""
    tool_output = tool_output or ""

    has_quant_metrics = _contains_any(response, QUANT_TERMS)
    has_counter_argument = bool(re.search(r"\b(counter[- ]argument|counterargument)\b", response, re.IGNORECASE))
    abort_returned = _contains_any(tool_output, ABORT_TERMS) or _contains_any(response, ["anti_speed_abort"])
    made_definitive_recommendation = _contains_any(response, RECOMMENDATION_TERMS)

    if abort_returned and made_definitive_recommendation:
        return {
            "score": 1,
            "reason": "Critical failure: ANTI_SPEED_ABORT was present, but the agent still made a definitive recommendation.",
            "has_quant_metrics": has_quant_metrics,
            "has_counter_argument": has_counter_argument,
            "abort_returned": abort_returned,
            "made_definitive_recommendation": made_definitive_recommendation,
        }

    score = 5
    reasons = []
    if not has_quant_metrics:
        score -= 2
        reasons.append("Response did not explicitly cite quantitative metrics.")
    if not has_counter_argument:
        score -= 1
        reasons.append("Response did not include a Counter-Argument section.")
    if abort_returned:
        reasons.append("Correctly refrained from recommendation after ANTI_SPEED_ABORT.")
    if not reasons:
        reasons.append("Fully compliant with Framework evidence and recommendation rules.")

    return {
        "score": max(score, 1),
        "reason": " ".join(reasons),
        "has_quant_metrics": has_quant_metrics,
        "has_counter_argument": has_counter_argument,
        "abort_returned": abort_returned,
        "made_definitive_recommendation": made_definitive_recommendation,
    }
