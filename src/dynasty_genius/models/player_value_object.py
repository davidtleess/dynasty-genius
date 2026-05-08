"""Player Value Object — the unified valuation row every decision surface reads from."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MarketOverlay(BaseModel):
    """KTC and market-signal data joined after model scoring.

    Market values never enter Engine A or Engine B as predictive features.
    This overlay is display-only context for David's decision surfaces.
    """

    source: str = "KTC"
    market_value: Optional[float] = None
    trend_delta: Optional[float] = None
    model_minus_market_delta: Optional[float] = None
    market_percentile: Optional[float] = None
    source_timestamp: Optional[str] = None
    caveats: list[str] = Field(default_factory=list)


class PlayerValueObject(BaseModel):
    """Unified dynasty valuation row.

    Every decision surface (Roster Audit, Trade Lab, Rookie Board) reads
    from this object. It does NOT invent its own scoring logic.

    Scores and projections are None until the relevant engine is validated.
    Decision surfaces must check model_grade before presenting scored fields.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    player_id: str = Field(..., description="Canonical dg_id")
    full_name: str
    position: str
    nfl_team: Optional[str] = None
    age: Optional[float] = None

    # ── Model metadata ────────────────────────────────────────────────────────
    engine_used: Optional[str] = None        # "engine_a" | "engine_b" | None
    model_version: Optional[str] = None
    model_grade: str = "PRE_MODEL"           # PRE_MODEL | EXPERIMENTAL | DECISION_GRADE

    # ── Scores — None until model_grade is DECISION_GRADE ────────────────────
    dynasty_value_score: Optional[float] = None
    projection_1y: Optional[float] = None
    projection_2y: Optional[float] = None
    projection_3y: Optional[float] = None

    # ── Signal completeness ───────────────────────────────────────────────────
    signal_completeness: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of required signals present"
    )
    inputs_present: list[str] = Field(default_factory=list)
    inputs_missing: list[str] = Field(default_factory=list)

    # ── Analysis ──────────────────────────────────────────────────────────────
    top_drivers: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    counter_argument: Optional[str] = None
    caveats: list[str] = Field(default_factory=list)

    # ── Market overlay — post-scoring only ───────────────────────────────────
    market_overlay: Optional[MarketOverlay] = None

    # ── Provenance ────────────────────────────────────────────────────────────
    assembled_at: Optional[str] = None
    source_versions: dict[str, str] = Field(default_factory=dict)
