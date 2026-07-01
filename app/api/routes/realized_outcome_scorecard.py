"""Scaffolding — read-only Realized-Outcome scorecard API.

``GET /api/realized-outcome/scorecard`` serves the latest scorecard written by
``scripts/run_realized_outcome_scoring.py`` (gitignored, weekly, no-op off-season).
It does NOT run scoring or read anything but ``_SCORECARD_PATH``.

Semantics differ deliberately from the other read-only routes: an ABSENT artifact
is the healthy off-season state (the loop is a no-op until the first finalized 2026
week), so it returns **200 ``inactive``**, not a fail-closed 503. 503 is reserved
for a PRESENT-but-broken artifact (malformed JSON, wrong root, wrong schema,
non-finite numbers, or a verdict-shaped field).

Descriptive-only diagnostic surface: ``decision_supported`` stays ``False``; this is
a fidelity/accuracy audit of a FROZEN model vs realized NFL outcomes, never a player
verdict. Market data is excluded from scoring upstream.

SCAFFOLDING (real-shape verification deferred to ~Sept 2026): no artifact exists yet.
Known divergence handled here: ``score()`` emits ``maturity_pct`` per tracking row but
NOT at the root, so the root value is derived from the tracking rows when the artifact
omits it — the UI's prominent maturity indicator still lights up on the first real
scorecard without a scorer change.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.api.routes.realized_outcome_scorecard_models import (
    RealizedOutcomeScorecardErrorResponse,
    RealizedOutcomeScorecardResponse,
)

_ROOT = Path(__file__).resolve().parents[3]
_SCORECARD_PATH = (
    _ROOT / "app" / "data" / "realized_outcome" / "scorecard_latest.json"
)

router = APIRouter(prefix="/realized-outcome", tags=["realized-outcome"])


def _unavailable_503(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error": "realized_outcome_scorecard_unavailable",
            "message": message,
            "decision_supported": False,
        },
    )


def _has_non_finite(value: Any) -> bool:
    """Recursively detect NaN/±Infinity in the validated dump.

    Pydantic coerces ``"NaN"``/``"Infinity"`` strings to floats, so a fabricated
    non-finite value fails closed rather than reaching the client as a tidy number.
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_has_non_finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_non_finite(item) for item in value)
    return False


def _inactive_response() -> RealizedOutcomeScorecardResponse:
    """The healthy off-season state: no artifact yet, so nothing has accrued."""
    return RealizedOutcomeScorecardResponse(
        status="inactive",
        status_reason="awaiting_first_finalized_week",
        as_of_week=None,
        settlement_status="unsettled",
        maturity_pct=None,
        cohort_metrics={},
        tracking_rows=[],
        excluded_counts={},
        decision_supported=False,
    )


@router.get(
    "/scorecard",
    response_model=RealizedOutcomeScorecardResponse,
    responses={503: {"model": RealizedOutcomeScorecardErrorResponse}},
)
def realized_outcome_scorecard() -> RealizedOutcomeScorecardResponse:
    """Read-only serve of the latest realized-outcome scorecard artifact."""
    try:
        raw = _SCORECARD_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Absent artifact = healthy off-season no-op, not an error.
        return _inactive_response()
    except OSError as exc:
        raise _unavailable_503(f"scorecard file unreadable: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _unavailable_503(f"malformed scorecard JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise _unavailable_503("scorecard root is not a JSON object")

    try:
        scorecard = RealizedOutcomeScorecardResponse.model_validate(data)
    except ValidationError as exc:
        raise _unavailable_503(
            f"malformed scorecard (schema contract): {exc}"
        ) from exc

    if _has_non_finite(scorecard.model_dump()):
        raise _unavailable_503("scorecard contains non-finite numeric values")

    # score() emits maturity_pct per tracking row but not at the root; derive the
    # root value from the rows (all share it — it is a function of as_of_week) when
    # the artifact omits it, so the empty-state UI's maturity indicator lights up on
    # the first real scorecard. A root value present in the artifact wins.
    if scorecard.maturity_pct is None and scorecard.tracking_rows:
        derived = scorecard.tracking_rows[0].maturity_pct
        if derived is not None:
            scorecard = scorecard.model_copy(update={"maturity_pct": derived})

    return scorecard
