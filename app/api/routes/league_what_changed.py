"""War Room #2 T3 — read-only What-Changed API over the pre-built T2 report.

``GET /api/league/what-changed`` serves the latest overwrite-latest report written
by the T2 emitter — it does NOT rebuild the report or rerun the diff engine. The T2
producer is imported only to document that lineage (and is asserted never-called in
the contract test); the request path reads ``_REPORT_PATH`` and nothing else.

Fail-closed (mirrors the League Pulse Inc1 route): a missing / malformed / wrong-root
/ wrong-schema report → 503. A report that loads and conforms is served as 200 with
its own honest ``overall_status`` (``degraded``/``unavailable`` are valid loaded
state, not errors), so the descriptive caveats reach the client intact.

Frontend HOLD: backend route only, no UI in this increment.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.api.routes.league_what_changed_models import (
    SCHEMA_VERSION,
    WhatChangedResponse,
)

# Imported to document the producer lineage; the API serves the pre-built report and
# never invokes the emitter (enforced by the contract test). Intentionally unused here.
from src.dynasty_genius.what_changed.report import (  # noqa: F401
    emit_daily_what_changed_report,
)

_ROOT = Path(__file__).resolve().parents[3]
_REPORT_PATH = _ROOT / "app" / "data" / "what_changed" / "what_changed_latest_report.json"

router = APIRouter(prefix="/league", tags=["league-what-changed"])


def _unavailable_503(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"error": "what_changed_report_unavailable", "message": message},
    )


@router.get(
    "/what-changed",
    response_model=WhatChangedResponse,
    response_model_exclude_none=True,
)
def what_changed_surface() -> WhatChangedResponse:
    """Read-only serve of the latest pre-built What-Changed report (artifact-state)."""
    try:
        raw = _REPORT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise _unavailable_503(f"report file missing: {_REPORT_PATH}") from exc
    except OSError as exc:
        raise _unavailable_503(f"report file unreadable: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _unavailable_503(f"malformed report JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise _unavailable_503("report root is not a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise _unavailable_503(
            f"unexpected schema_version: {data.get('schema_version')!r}"
        )

    try:
        return WhatChangedResponse.model_validate(data)
    except ValidationError as exc:
        raise _unavailable_503(f"malformed report (schema contract): {exc}") from exc
