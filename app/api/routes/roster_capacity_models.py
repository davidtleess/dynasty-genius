"""Response models for the read-only Roster Capacity API (Slice A).

Descriptive-only: `decision_supported` is locked False. The response mirrors the
producer's enriched scorecard artifact and adds `artifact_status` (the route's
read of freshness / blocked state) without ever collapsing a range to a scalar
or nominating a cut target.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.dynasty_genius.roster_capacity.models import (
    CapacityCandidate,
    CapacityHealth,
    PoolRange,
    ScenarioResult,
)


class RosterCapacityErrorResponse(BaseModel):
    """Structured 503 body: the artifact could not be served.

    Even the failure is descriptive — `decision_supported` stays False so a
    consumer never reads an error as a directive.
    """

    error: str
    message: str
    decision_supported: Literal[False] = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, _v: object) -> bool:
        return False


class RosterCapacityResponse(BaseModel):
    """Read-only serve of the enriched capacity scorecard artifact.

    `artifact_status` is the route's own read of the served state
    (`ok` / `degraded` / `blocked`), DISTINCT from the core `status`. No field
    averages, tightens, or nominates: ranges pass through unclamped and signed,
    and `marginal_next_candidate_cost` stays a range with no player identifier.
    """

    status: Literal["ok", "blocked"]
    artifact_status: Literal["ok", "degraded", "blocked"]
    capacity_health: CapacityHealth | None
    candidates: list[CapacityCandidate] = Field(default_factory=list)
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    unrostered_pool_range: dict[str, PoolRange] = Field(default_factory=dict)
    excluded_counts: dict[str, int] = Field(default_factory=dict)
    caveats: list[str] = Field(default_factory=list)
    created_at: str | None
    sleeper_snapshot_captured_at: str | None
    decision_supported: Literal[False] = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, _v: object) -> bool:
        return False
