"""Slice A — read-only Roster Capacity API over the gitignored artifact.

``GET /api/roster/capacity`` serves the latest scorecard written by
``scripts/run_roster_capacity_audit.py`` — it does NOT rebuild the audit or read
anything but ``_ARTIFACT_PATH``. Fail-closed (mirrors the What-Changed / League
Pulse routes): a missing / malformed / wrong-root / wrong-schema / non-finite /
verdict-shaped artifact → structured 503. A parseable artifact whose freshness
timestamps cannot be verified (null or unparseable — both real producer outputs,
since ``sleeper_snapshot_captured_at`` comes from ``snapshot.get("captured_at")``)
is served 200 with ``artifact_status=degraded`` and a ``freshness_unverifiable``
caveat, so the descriptive state reaches the client without fabricating
confidence.

Read-only, descriptive: ``decision_supported`` stays False; ranges pass through
unclamped and signed; no cut target is nominated.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.api.routes.roster_capacity_models import (
    RosterCapacityErrorResponse,
    RosterCapacityResponse,
)
from src.dynasty_genius.roster_capacity.models import CapacityAuditResult

_ROOT = Path(__file__).resolve().parents[3]
_ARTIFACT_PATH = (
    _ROOT / "app" / "data" / "roster_capacity" / "roster_capacity_latest.json"
)

# The exact top-level envelope the producer writes: CapacityAuditResult.model_dump()
# enriched with the two producer-added fields (run_roster_capacity_audit.py:112-116).
# Missing OR extra keys fail closed — a stray `recommendation` verdict field must
# never reach the client, and a dropped `decision_supported` is an incomplete
# envelope, not a silent model default.
_EXPECTED_KEYS = frozenset(
    {
        "status",
        "capacity_health",
        "candidates",
        "scenarios",
        "unrostered_pool_range",
        "excluded_counts",
        "caveats",
        "decision_supported",
        "created_at",
        "sleeper_snapshot_captured_at",
    }
)

router = APIRouter(prefix="/roster", tags=["roster-capacity"])


def _unavailable_503(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error": "roster_capacity_artifact_unavailable",
            "message": message,
            "decision_supported": False,
        },
    )


def _has_non_finite(value: Any) -> bool:
    """Recursively detect NaN/±Infinity in the parsed scorecard.

    Pydantic accepts ``"NaN"``/``"Infinity"`` strings by coercion, so the sweep
    runs on the validated dump — a fabricated non-finite value fails closed
    rather than reaching the client as a tidy-looking number.
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


def _unexpected_key_path(raw: Any, dump: Any, path: str = "") -> str | None:
    """Return the path of the first raw key the schema does not declare, else None.

    Pydantic silently ignores extra keys at every level, so a nested verdict
    field (a ``recommendation`` on a scenario/candidate/pool) would be dropped
    and the route would serve 200. Walking ``raw`` against the validated
    ``dump`` in parallel flags any key present in the artifact but absent from
    the schema's re-serialization — at any depth. Dynamic-value maps
    (``excluded_counts``, ``by_slot_class``, …) never false-positive because the
    model preserves their keys, so raw keys stay a subset of the dump's.
    """
    if isinstance(raw, dict) and isinstance(dump, dict):
        for key in raw:
            here = f"{path}.{key}" if path else key
            if key not in dump:
                return here
            found = _unexpected_key_path(raw[key], dump[key], here)
            if found is not None:
                return found
    elif isinstance(raw, (list, tuple)) and isinstance(dump, (list, tuple)):
        for index, item in enumerate(raw):
            if index < len(dump):
                found = _unexpected_key_path(item, dump[index], f"{path}[{index}]")
                if found is not None:
                    return found
    return None


def _freshness_verifiable(*timestamps: object) -> bool:
    """True only when every timestamp is a parseable ISO-8601 string.

    Null (a real producer output) and unparseable strings both read as
    unverifiable → the caller degrades rather than implying confident freshness.
    """
    for ts in timestamps:
        if not isinstance(ts, str):
            return False
        try:
            datetime.fromisoformat(ts)
        except ValueError:
            return False
    return True


@router.get(
    "/capacity",
    response_model=RosterCapacityResponse,
    responses={503: {"model": RosterCapacityErrorResponse}},
)
def roster_capacity_surface() -> RosterCapacityResponse:
    """Read-only serve of the latest enriched capacity scorecard artifact."""
    try:
        raw = _ARTIFACT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise _unavailable_503(f"artifact file missing: {_ARTIFACT_PATH}") from exc
    except OSError as exc:
        raise _unavailable_503(f"artifact file unreadable: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _unavailable_503(f"malformed artifact JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise _unavailable_503("artifact root is not a JSON object")

    missing = _EXPECTED_KEYS - set(data)
    if missing:
        raise _unavailable_503(
            f"incomplete artifact (schema contract): missing {sorted(missing)}"
        )

    try:
        core = CapacityAuditResult.model_validate(data)
    except ValidationError as exc:
        raise _unavailable_503(f"malformed artifact (schema contract): {exc}") from exc

    dump = core.model_dump()

    # Fail closed on ANY field the schema does not declare, at ANY depth — a
    # nested verdict field (a `recommendation` on a scenario/candidate/pool)
    # must never reach the client. Top-level strictness alone is incomplete
    # because Pydantic drops nested extras silently. The two producer-enrichment
    # fields are not part of the core model, so add them to the comparison shape
    # (their presence is already guaranteed by the missing-key check above).
    comparison = {
        **dump,
        "created_at": data["created_at"],
        "sleeper_snapshot_captured_at": data["sleeper_snapshot_captured_at"],
    }
    unexpected = _unexpected_key_path(data, comparison)
    if unexpected is not None:
        raise _unavailable_503(
            f"unexpected artifact field (schema contract): {unexpected}"
        )

    if _has_non_finite(dump):
        raise _unavailable_503("artifact contains non-finite numeric values")

    created_at = data["created_at"]
    snapshot_captured_at = data["sleeper_snapshot_captured_at"]
    caveats = list(core.caveats)

    if core.status == "blocked":
        artifact_status = "blocked"
    elif not _freshness_verifiable(created_at, snapshot_captured_at):
        artifact_status = "degraded"
        caveats = [*caveats, "freshness_unverifiable"]
    else:
        artifact_status = "ok"

    return RosterCapacityResponse(
        status=core.status,
        artifact_status=artifact_status,
        capacity_health=core.capacity_health,
        candidates=core.candidates,
        scenarios=core.scenarios,
        unrostered_pool_range=core.unrostered_pool_range,
        excluded_counts=core.excluded_counts,
        caveats=caveats,
        created_at=created_at,
        sleeper_snapshot_captured_at=snapshot_captured_at,
    )
