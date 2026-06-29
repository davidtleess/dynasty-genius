"""Output models for the Roster Capacity Scenario Simulator.

All models are descriptive. `decision_supported` is locked False everywhere:
the simulator reports capacity and value-at-risk; it never recommends a move.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Per-field value-provenance keys carried on every candidate. Stable set so
# consumers can rely on the same keys regardless of join outcome.
VALUE_FIELD_KEYS: tuple[str, ...] = ("xvar", "dvs", "projection_2y", "position", "model")


class CapacityHealth(BaseModel):
    """League-shape capacity summary for David's roster.

    `total_capacity_cuts_required` and `active_slot_overflow` are DISTINCT:
    the former is roster-wide (players over total capacity, incl. reserve/taxi),
    the latter is active-slot pressure (non-reserve, non-taxi players over the
    active starter slots). A roster can be active-slot heavy while total-capacity
    compliant (stash slots absorb the excess).
    """

    total_players: int
    total_capacity: int
    total_capacity_cuts_required: int
    active_slot_overflow: int
    by_slot_class: dict[str, int]
    reserve_unrestricted: bool


class CapacityCandidate(BaseModel):
    """One roster player surfaced in the capacity-ordered review list.

    Raw value fields are re-joined from the universe PVO (the cut engine exposes
    only percentile/dvs). Each field carries a provenance status so a consumer
    can tell an "ok" join from an "unavailable"/"pre_model"/"unknown_position"
    one without guessing from a null.
    """

    sleeper_player_id: str
    full_name: str
    position: str
    cut_priority: int
    candidate_source: Literal["forced_review", "capacity_ordered"]
    raw_xvar: float | None
    dvs: float | None
    xvar_pct: float | None
    median_projection_2y: float | None
    value_field_status: dict[str, str]


class PoolRange(BaseModel):
    """The unrostered (waiver) replacement range for one position.

    Deliberately WIDE, not a confidence interval: `low`/`high` are the min/max of
    the position's display top-K unrostered values — an honest band over a
    volatile wire, never a tightened point estimate. `top_k_values` carries the
    ordered (descending) raw values themselves, retained out to the largest
    requested scenario so T3's depletion math has every per-member value it
    needs (it may be LONGER than the K that low/high are computed over).

    `status == "waiver_range_unavailable"` fails closed (stale snapshot,
    incomplete roster coverage, pool below `min_pool`, valuation coverage below
    floor); a genuinely barren-but-valid pool stays `ok` with a loud caveat.
    """

    status: Literal["ok", "waiver_range_unavailable"]
    low: float | None
    high: float | None
    top_k_values: list[float] = Field(default_factory=list)
    pool_size: int | None
    caveats: list[str] = Field(default_factory=list)


class ScenarioRequest(BaseModel):
    """A David-proposed cut hypothesis: clear N capacity, or specific cuts.

    Exactly one mode is used per request; `proposed_cuts` takes precedence when
    both are present. An empty/neither request falls back to the default
    `clear_n = total_capacity_cuts_required`.
    """

    clear_n: int | None = None
    proposed_cuts: list[str] | None = None


class ScenarioResult(BaseModel):
    """The descriptive consequences of one cut hypothesis — no verdict.

    `cumulative_value_at_risk` is depletion-aware (NOT N x a single-player gap):
    the wire depletes as you claim players, so the bound is summed per position
    from N-deep pool slices. Orientation is pinned `(best_case, worst_case)` and
    cannot invert; negatives are left UNCLAMPED (a cut that is a net upgrade
    reads negative). `pool_deficits` records, per position, how many cut spots
    have NO replacement candidate — a fact, never a do-not-cut verdict.
    `marginal_next_candidate_cost` is the value-at-risk RANGE of the next
    capacity-ordered candidate not in the cut set; it carries NO player
    identifier (it nominates no target).
    """

    cut_set: list[str] = Field(default_factory=list)
    cumulative_value_at_risk: tuple[float, float]
    marginal_next_candidate_cost: tuple[float, float] | None
    per_position_depth_impact: dict[str, dict[str, int]] = Field(default_factory=dict)
    pool_deficits: dict[str, int] = Field(default_factory=dict)
    caveats: list[str] = Field(default_factory=list)


class CapacityAuditResult(BaseModel):
    """Top-level descriptive result.

    `status == "blocked"` on data corruption (malformed snapshot/PVO content) —
    the simulator returns a blocked result rather than raising, so a producer can
    record the failure. API misuse (wrong argument TYPES) still raises.
    """

    status: Literal["ok", "blocked"]
    capacity_health: CapacityHealth | None
    candidates: list[CapacityCandidate] = Field(default_factory=list)
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    unrostered_pool_range: dict[str, PoolRange] = Field(default_factory=dict)
    excluded_counts: dict[str, int] = Field(default_factory=dict)
    caveats: list[str] = Field(default_factory=list)
    decision_supported: Literal[False] = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, _v: object) -> bool:
        return False


class ProducerReport(BaseModel):
    """The read-only producer's own exit/report envelope.

    `producer_status` is DISTINCT from the core `CapacityAuditResult.status`
    (`ok`/`blocked`): it adds `preflight_ready`, which never produces a
    scorecard. A blocked or preflight run carries `scorecard=None` or a blocked
    scorecard and writes no artifact; only an `ok` run writes one.
    """

    producer_status: Literal["ok", "blocked", "preflight_ready"]
    scorecard: CapacityAuditResult | None
    decision_supported: Literal[False] = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, _v: object) -> bool:
        return False
