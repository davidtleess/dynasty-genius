"""War Room #2 T3 — typed, leak-proof DTOs for the What-Changed API.

Backend contract for ``GET /api/league/what-changed`` (read-only over the
pre-built T2 report). Every DTO is an ``extra="forbid"`` allowlist shape with
``decision_supported`` locked ``Literal[False]`` at each section root, mirroring
the six report roots the T2 emitter stamps. The model section DTO has NO market
fields by construction, so a market key leaking into the model section fails
validation rather than reaching the client.

Section-specific fields are optional so one strict shape serves both the populated
(``ok``) and degraded (``insufficient_history`` / ``unavailable``) variants without
admitting unknown keys; the route serves with ``response_model_exclude_none`` so the
absent ones never appear in the payload.

Design spec: docs/superpowers/specs/2026-06-24-war-room-2-daily-what-changed-diff-design.md
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

SCHEMA_VERSION = "war_room_2_what_changed_v1"


class _Strict(BaseModel):
    """Allowlist base: reject any field not explicitly declared."""

    model_config = ConfigDict(extra="forbid")


# ── market section ───────────────────────────────────────────────────────────
class WhatChangedMarketDelta(_Strict):
    sleeper_id: str
    player_key: str
    player_name: Optional[str] = None
    position: Optional[str] = None
    value_delta: int
    value_delta_direction: str
    overall_rank_delta: int
    overall_rank_delta_direction: str
    position_rank_delta: int
    position_rank_delta_direction: str


class WhatChangedEnteredExited(_Strict):
    sleeper_id: str
    player_key: str


class WhatChangedMarketSection(_Strict):
    status: str
    decision_supported: Literal[False]
    market_source: str
    comparison_window: Optional[dict[str, Any]] = None
    roster_deltas: Optional[list[WhatChangedMarketDelta]] = None
    top_movers: Optional[list[WhatChangedMarketDelta]] = None
    total_movers_count: Optional[int] = None
    entered: Optional[list[WhatChangedEnteredExited]] = None
    exited: Optional[list[WhatChangedEnteredExited]] = None
    aborted_reason: Optional[str] = None


# ── model section (NO market fields by construction) ──────────────────────────
class WhatChangedModelDelta(_Strict):
    sleeper_id: Optional[str] = None
    player_key: str
    player_name: Optional[str] = None
    position: Optional[str] = None
    dynasty_value_score_delta: float
    dynasty_value_score_delta_direction: str
    dvs_pct_delta: float
    xvar_delta: float


class WhatChangedVintage(_Strict):
    """A complete model vintage — both hashes required and non-blank.

    A vintage is the identity of a model output; a partial/empty vintage is never an
    honest shape, so both fields are required (not Optional) and rejected if blank.
    """

    semantic_output_hash: str
    provenance_hash: str

    @field_validator("semantic_output_hash", "provenance_hash")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("vintage hash must be non-blank")
        return value


class WhatChangedModelComparisonWindow(_Strict):
    """Allowlisted, shape-closed model window — no market key can hide on it.

    Admits ONLY the three honest model window shapes:
    1. ``{status: insufficient_history}`` — status alone.
    2. ``{status: model_multi_vintage_ambiguous, from_date, to_date, ambiguous_dates}``.
    3. ``{from_date, to_date, from_vintage, to_vintage}`` — clean two-date window, no status.

    ``extra="forbid"`` (via ``_Strict``) rejects unknown keys (incl. a nested
    ``market_overlay``); the ``Literal`` status rejects unknown states; and the
    post-validator rejects mixed/partial combinations so the window is fully closed.
    """

    status: Optional[Literal["insufficient_history", "model_multi_vintage_ambiguous"]] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    ambiguous_dates: Optional[list[str]] = None
    from_vintage: Optional[WhatChangedVintage] = None
    to_vintage: Optional[WhatChangedVintage] = None

    @model_validator(mode="after")
    def _exactly_one_known_shape(self) -> "WhatChangedModelComparisonWindow":
        if self.status == "insufficient_history":
            if any(
                f is not None
                for f in (
                    self.from_date,
                    self.to_date,
                    self.ambiguous_dates,
                    self.from_vintage,
                    self.to_vintage,
                )
            ):
                raise ValueError("insufficient_history window admits no other fields")
        elif self.status == "model_multi_vintage_ambiguous":
            if self.from_date is None or self.to_date is None or not self.ambiguous_dates:
                raise ValueError(
                    "model_multi_vintage_ambiguous window requires from_date, "
                    "to_date, and a non-empty ambiguous_dates"
                )
            if self.from_vintage is not None or self.to_vintage is not None:
                raise ValueError("ambiguous window admits no vintages")
        else:  # status is None -> clean two-date window
            if None in (
                self.from_date,
                self.to_date,
                self.from_vintage,
                self.to_vintage,
            ):
                raise ValueError(
                    "clean window requires from_date, to_date, from_vintage, to_vintage"
                )
            if self.ambiguous_dates is not None:
                raise ValueError("clean window admits no ambiguous_dates")
        return self


class WhatChangedModelFeatureFreshness(_Strict):
    """Descriptive engine_b feature-source freshness for the model section.

    Discloses which feature CSV backed the model vintage (a published runtime vs the
    committed seed) and its hashes/as-of label, so the daily digest can show that captured
    vintages are genuinely moving. Carries NO market field and certifies no decision.
    """

    decision_supported: Literal[False]
    feature_source_kind: Literal["runtime", "seed"] | None = None
    feature_csv_sha256: Optional[str] = None
    source_as_of: Optional[str] = None
    feature_csv_path: Optional[str] = None
    published_seed_sha256: Optional[str] = None
    # Honest-disclosure shape: a present-but-unverified runtime surfaces as not_ready rather
    # than being hidden (feature_source_kind is then None and aborted_reason explains why).
    # Closed vocabularies so the API cannot report a phantom source kind/status.
    feature_source_status: Literal["not_ready"] | None = None
    aborted_reason: Optional[str] = None


class WhatChangedModelPvoSeedStaleness(_Strict):
    """Descriptive seed-vs-runtime drift summary — the §3.6 manual-promotion tripwire.

    Surfaced ONLY when ``promote_recommended`` is True (silent on quiet drift). The count
    of model-supported players drifted >5% and the coverage-count change are the stable
    triggers; ``mean_abs_value_delta`` / ``p95_abs_value_delta`` are DISCLOSURE-only (never
    promotion triggers — market-noise-sensitive). Carries no market field; certifies no
    decision.
    """

    decision_supported: Literal[False]
    promote_recommended: bool
    count_players_drifted_gt_5pct: int
    count_model_supported_players_drifted_gt_5pct: int
    mean_abs_value_delta: float  # disclosure-only — NOT a promotion trigger
    p95_abs_value_delta: float  # disclosure-only — NOT a promotion trigger
    coverage_count_deltas: dict[str, int]
    seed_as_of: Optional[str] = None
    seed_age_days: Optional[float] = None


class WhatChangedModelPvoStaleness(_Strict):
    """Descriptive PVO source provenance for the model section + passive seed-staleness.

    Provenance (source kind / hashes / as-of / paths) is ALWAYS disclosed so the digest can
    show which artifact backed the vintage. The ``seed_staleness`` block appears only on the
    promotion tripwire. A present-but-unverified runtime surfaces as ``not_ready`` (kind None
    + ``aborted_reason``), never hidden. Closed vocabularies so the API cannot report a
    phantom source kind/status. Carries NO market field and certifies no decision.
    """

    decision_supported: Literal[False]
    pvo_source_kind: Literal["runtime", "seed"] | None = None
    pvo_sha256: Optional[str] = None
    coverage_sha256: Optional[str] = None
    source_as_of: Optional[str] = None
    pvo_path: Optional[str] = None
    coverage_path: Optional[str] = None
    seed_staleness: WhatChangedModelPvoSeedStaleness | None = None
    # Honest-disclosure shape: a present-but-unverified runtime surfaces as not_ready rather
    # than being hidden (pvo_source_kind is then None and aborted_reason explains why).
    pvo_source_status: Literal["not_ready"] | None = None
    aborted_reason: Optional[str] = None


class WhatChangedModelSection(_Strict):
    status: str
    decision_supported: Literal[False]
    comparison_window: Optional[WhatChangedModelComparisonWindow] = None
    deltas: Optional[list[WhatChangedModelDelta]] = None
    vintage_changed: Optional[bool] = None
    feature_freshness: WhatChangedModelFeatureFreshness | None = None
    pvo_staleness: WhatChangedModelPvoStaleness | None = None


class WhatChangedDailyDiff(_Strict):
    decision_supported: Literal[False]
    overall_status: str
    market: WhatChangedMarketSection
    model: WhatChangedModelSection


# ── structural current-context section ────────────────────────────────────────
class WhatChangedStalenessCaveat(_Strict):
    basis: str
    report_generated_at: str
    age_hours: float
    is_stale: bool


class WhatChangedTeamValueSummary(_Strict):
    roster_id: Optional[int] = None
    team_name: Optional[str] = None
    posture_label: Optional[str] = None
    # Real team_value_views keys (market_overlay_total is excluded upstream — market
    # stays overlay-only and never enters this summary).
    depth_credit_xvar: Optional[float] = None
    lineup_xvar: Optional[float] = None
    starter_weighted_xvar: Optional[float] = None
    top_n_xvar: Optional[float] = None
    total_xvar_capped: Optional[float] = None


class WhatChangedPartnerRanking(_Strict):
    counterparty_roster_id: Optional[int] = None
    counterparty_team_name: Optional[str] = None
    partner_score: Optional[float] = None
    matched_positions: Optional[list[str]] = None


class WhatChangedCard(_Strict):
    card_id: Optional[str] = None
    card_type: Optional[str] = None
    asset_name: Optional[str] = None
    opportunity_score: Optional[float] = None
    recommended_drop_name: Optional[str] = None


class WhatChangedDropSummary(_Strict):
    roster_id: Optional[int] = None
    total_players: Optional[int] = None
    total_capacity: Optional[int] = None
    cuts_required: Optional[int] = None


class WhatChangedCutCandidate(_Strict):
    sleeper_player_id: Optional[str] = None
    player_name: Optional[str] = None
    position: Optional[str] = None
    cut_priority: Optional[int] = None
    dvs: Optional[float] = None
    xvar_pct: Optional[float] = None


class WhatChangedStructuralSection(_Strict):
    status: str
    decision_supported: Literal[False]
    current_not_delta: bool
    source_path: Optional[str] = None
    captured_at: Optional[str] = None
    staleness_caveat: Optional[WhatChangedStalenessCaveat] = None
    aborted_reason: Optional[str] = None
    # team_posture
    david_roster_id: Optional[int] = None
    david_team_name: Optional[str] = None
    david_posture: Optional[str] = None
    team_count: Optional[int] = None
    # team_value
    david_value_summary: Optional[WhatChangedTeamValueSummary] = None
    # league_opportunity
    top_partner_rankings: Optional[list[WhatChangedPartnerRanking]] = None
    top_cards: Optional[list[WhatChangedCard]] = None
    # drop_pressure
    summary: Optional[WhatChangedDropSummary] = None
    top_candidates: Optional[list[WhatChangedCutCandidate]] = None
    # sleeper_snapshot
    david_roster_player_count: Optional[int] = None
    league_roster_count: Optional[int] = None


class WhatChangedStructuralSections(_Strict):
    team_posture: WhatChangedStructuralSection
    team_value: WhatChangedStructuralSection
    league_opportunity: WhatChangedStructuralSection
    drop_pressure: WhatChangedStructuralSection
    sleeper_snapshot: WhatChangedStructuralSection


class WhatChangedStructuralContext(_Strict):
    status: str
    decision_supported: Literal[False]
    current_not_delta: bool
    sections: WhatChangedStructuralSections


# ── top-level response ───────────────────────────────────────────────────────
class WhatChangedResponse(_Strict):
    schema_version: str
    generated_at: str
    decision_supported: Literal[False]
    overall_status: str
    daily_diff: WhatChangedDailyDiff
    structural_context: WhatChangedStructuralContext
