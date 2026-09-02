"""The 503 bodies that ``/api/engine-b/scores`` and ``/api/roster/audit`` actually send.

DG-133 made both routes answer a governed 503 when the Engine B inference partition
cannot be selected. They raise ``HTTPException(status_code=503, detail={...})`` and
FastAPI's default handler wraps that as ``{"detail": {"error": ..., "message": ...}}``
— so the contract must declare the ``detail`` envelope, not a flat body. (Three other
routes — roster capacity, model scoreboard, realized-outcome scorecard — raise the same
way but declare a FLAT model; that pre-existing mismatch is DG-138's, not repaired here.
The four ``JSONResponse`` routes are honest: flat body, flat model.)

``message`` is a bare token from ``inference_partition`` (DG-133) on the partition
path; the roster route's second 503 site (every row failed to map, raised by the audit
envelope assembler) sends a short sentence. Either way it is ``str``. (DG-135)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EngineBDependencyUnavailableDetail(BaseModel):
    error: Literal["engine_b_dependency_unavailable"]
    message: str


class EngineBDependencyUnavailableResponse(BaseModel):
    """503 from ``GET /api/engine-b/scores``."""

    detail: EngineBDependencyUnavailableDetail


class RosterDependencyUnavailableDetail(BaseModel):
    error: Literal["roster_dependency_unavailable"]
    message: str


class RosterDependencyUnavailableResponse(BaseModel):
    """503 from ``GET /api/roster/audit``."""

    detail: RosterDependencyUnavailableDetail
