"""DEBT-6 Slice 1b — T4: the read-only capture-health route.

``GET /api/system/capture-health`` answers the daily-login question: is the
PIT capture timeline complete enough to trust trend calculations, or are
there silent holes? Per store it reports timeline completeness (missing
dates, max contiguous gap), staleness with a grace window, and density
anomalies — descriptive facts only, ``decision_supported=false`` throughout.

Freshness never blocks (``ok | degraded`` only). Fail-closed is reserved for
the endpoint's OWN configuration: an absent/malformed/unsafe cadence config
returns a sanitized fixed 503 that never echoes paths, config content, or
tracebacks. Absent gitignored stores are a first-class 200-degraded state
(the CI/fresh-clone reality), never an error.

Spec: docs/superpowers/specs/2026-07-02-debt6-capture-health-slice1b-design.md
Plan: docs/superpowers/plans/2026-07-02-debt6-capture-health-slice1b-plan.md
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.routes.system_capture_health_models import (
    CaptureHealthConfigError,
    CaptureHealthErrorResponse,
    CaptureHealthResponse,
    inspect_capture_store,
    load_capture_cadence,
)


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


# Module-level so tests monkeypatch these; the handler reads them at request
# time. _CLOCK is injectable for deterministic staleness assertions.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_PATH = _REPO_ROOT / "app" / "config" / "capture_cadence.json"
_CLOCK: Callable[[], datetime] = _now_utc

_SANITIZED_MESSAGE = "capture health configuration unavailable"

router = APIRouter(prefix="/system", tags=["system"])


def _config_unavailable_503() -> JSONResponse:
    """One fixed 503 body for every config failure — no internal detail leaks."""

    body = CaptureHealthErrorResponse(
        error="capture_health_unavailable",
        message=_SANITIZED_MESSAGE,
        decision_supported=False,
    )
    return JSONResponse(status_code=503, content=body.model_dump())


@router.get(
    "/capture-health",
    response_model=CaptureHealthResponse,
    responses={503: {"model": CaptureHealthErrorResponse}},
)
def get_capture_health():
    try:
        config = load_capture_cadence(config_path=_CONFIG_PATH)
    except CaptureHealthConfigError:
        return _config_unavailable_503()

    now = _CLOCK()
    stores = [
        inspect_capture_store(
            store_config=store_config,
            repo_root=_REPO_ROOT,
            now=now,
            timezone=config.timezone,
            season_windows=config.season_windows,
        )
        for store_config in config.stores
    ]
    overall = (
        "degraded"
        if any(store.store_status == "degraded" for store in stores)
        else "ok"
    )
    return CaptureHealthResponse(
        overall_status=overall,  # type: ignore[arg-type]
        config_version=config.config_version,
        checked_at=now.isoformat(),
        stores=stores,
        decision_supported=False,
    )
