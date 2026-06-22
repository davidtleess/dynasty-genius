"""League Pulse Increment 1 — typed read-only DTOs + token discipline.

Backend contract for the League Pulse decision surface (read-only over the
Phase 17/18 `*_latest` artifacts). All DTOs are `extra="forbid"` allowlist
shapes with `decision_supported` locked `Literal[False]` recursively. Market
content is surfaced ONLY via `LeaguePulseMarketCard` + the market-influenced
`LeaguePulsePartnerRanking` (Q3=B labeled overlay); the model-native
`LeaguePulseCard` rejects market evidence/score keys by construction.

Design spec: docs/superpowers/specs/2026-06-22-league-pulse-increment-1-contract-design.md
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# ── Token discipline ─────────────────────────────────────────────────────────

# Caveat/rationale tokens permitted on a David-facing surface. validate_tokens
# keeps only these; anything else is dropped with `evidence_suppressed_banned_term`.
SAFE_TOKENS: frozenset[str] = frozenset(
    {
        "phase17_non_decision_grade",
        "future_pick_values_deferred",
        "posture_unclassified",
        "phase18_heuristic_posture",
        "market_overlay_unvalidated_divergence",
        "market_overlay_context_only",
        "waiver_status_from_sleeper_snapshot",
        "partner_score_market_influenced",
        "taxi_activation_cost_requires_manual_review",
        "evidence_suppressed_banned_term",
    }
)


def validate_tokens(raw: list[str] | None) -> tuple[list[str], list[str]]:
    """Keep only SAFE_TOKENS; drop the rest with a single suppression caveat."""
    items = list(raw or [])
    clean = [t for t in items if t in SAFE_TOKENS]
    caveats = ["evidence_suppressed_banned_term"] if len(clean) != len(items) else []
    return clean, caveats


# Closed token→neutral-label map. A raw producer rationale token is NEVER passed
# through to the client: a token not in the map maps to the safe generic fallback.
_TOKEN_LABELS: dict[str, str] = {
    "UNROSTERED_MODEL_MARKET_ASYMMETRY": "market_divergence_context",
    "MODEL_MARKET_ASYMMETRY": "market_divergence_context",
    "FANTASYCALC_PERCENTILE_DIVERGENCE": "market_divergence_context",
    "TAXI_LONG_TERM_VALUE_PRESENT": "taxi_long_term_value_present",
    "ACTIVATION_COST_REPRESENTED": "activation_cost_represented",
}
_FALLBACK_LABEL = "opportunity_signal"


def neutral_label_for_token(token: str) -> str:
    """Map a raw rationale token to a neutral label; unknown → safe fallback."""
    return _TOKEN_LABELS.get(token, _FALLBACK_LABEL)


# Per-card-type allowlists (evidence + score_components).
_MODEL_NATIVE_EVIDENCE = frozenset(
    {
        "position",
        "perspective_position_z",
        "counterparty_position_z",
        "perspective_surplus_label",
        "counterparty_surplus_label",
    }
)
_MODEL_NATIVE_SCORE = frozenset({"fit_score", "feasibility_score"})
_OVERLAY_EVIDENCE = frozenset(
    {
        "market_percentile",
        "model_minus_market_delta",
        "model_percentile",
        "signal",
        "signal_status",
        "xvar",
        "asset_roster_id",
        "raw_xvar",
        "lineup_role",
    }
)
_OVERLAY_SCORE = frozenset({"fit_score", "divergence_score", "feasibility_score"})


# ── Base: extra=forbid + decision_supported locked False ─────────────────────


class _DSBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_supported: Literal[False] = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _force_false(cls, v: object) -> bool:
        return False


# ── Nested DTOs ──────────────────────────────────────────────────────────────


class LeaguePulseSources(_DSBase):
    team_posture: dict[str, Any]
    team_value_matrix: dict[str, Any]
    league_opportunity: dict[str, Any]


class LeaguePulseTeamPosture(_DSBase):
    roster_id: int
    team_name: str | None
    posture_label: Literal[
        "CONTENDER", "REBUILDING", "ASCENDING", "BALANCED", "TRANSITIONAL"
    ]
    score: float
    components: dict[str, float]
    caveats: list[str] = []


class LeaguePulseValueViews(_DSBase):
    # NO market_overlay_total field — extra=forbid is the backstop; the mapper
    # suppresses it by not selecting it (so a valid team is NOT dropped).
    starter_weighted_xvar: float
    lineup_xvar: float
    depth_credit_xvar: float
    total_xvar_capped: float
    top_n_xvar: float


class LeaguePulseTeamValue(_DSBase):
    roster_id: int
    team_name: str | None
    value_views: LeaguePulseValueViews
    age_profile: dict[str, float]
    positional_summary: dict[str, Any]
    future_picks: dict[str, Any]


class LeaguePulsePartnerRanking(_DSBase):
    counterparty_roster_id: int
    counterparty_team_name: str | None
    partner_score: float
    matched_positions: list[str]
    score_components: dict[str, float]
    evidence: dict[str, Any]
    market_influenced: Literal[True] = True
    caveats: list[str] = []

    @field_validator("market_influenced", mode="before")
    @classmethod
    def _force_market_influenced(cls, v: object) -> bool:
        return True

    @model_validator(mode="after")
    def _ensure_market_caveat(self) -> "LeaguePulsePartnerRanking":
        # divergence_density_score is market-derived → the section is always
        # flagged market-influenced (Codex's catch).
        if "partner_score_market_influenced" not in self.caveats:
            self.caveats = [*self.caveats, "partner_score_market_influenced"]
        return self


class LeaguePulseCard(_DSBase):
    """Model-native opportunity card. Rejects market evidence/score keys."""

    card_id: str
    card_type: Literal["ROSTER_SURPLUS_DEFICIT_MATCH"]
    opportunity_score: float
    rationale_primary: str
    rationale_secondary: list[str] = []
    evidence: dict[str, Any]
    score_components: dict[str, float]
    caveats: list[str] = []

    @field_validator("evidence")
    @classmethod
    def _evidence_model_native(cls, v: dict[str, Any]) -> dict[str, Any]:
        extra = set(v) - _MODEL_NATIVE_EVIDENCE
        if extra:
            raise ValueError(
                f"model-native card evidence has non-allowlisted keys: {sorted(extra)}"
            )
        return v

    @field_validator("score_components")
    @classmethod
    def _score_model_native(cls, v: dict[str, float]) -> dict[str, float]:
        extra = set(v) - _MODEL_NATIVE_SCORE
        if extra:
            raise ValueError(
                "model-native card score_components has non-allowlisted keys: "
                f"{sorted(extra)}"
            )
        return v


class LeaguePulseRecommendedDrop(_DSBase):
    sleeper_player_id: str
    full_name: str
    position: str
    cut_priority: int
    ir_compliance_status: str
    cut_rationale: list[str] = []

    @field_validator("cut_rationale")
    @classmethod
    def _filter_rationale(cls, v: list[str]) -> list[str]:
        clean, _ = validate_tokens(v)
        return clean


class LeaguePulseMarketCard(_DSBase):
    """Labeled market-overlay card (Q3=B). Admits market evidence/score keys."""

    card_id: str
    card_type: Literal[
        "WAIVER_CANDIDATE",
        "DIVERGENCE_MODEL_HIGH",
        "DIVERGENCE_MARKET_HIGH",
        "TAXI_ACTIVATION_CANDIDATE",
    ]
    opportunity_score: float
    rationale_primary: str
    rationale_secondary: list[str] = []
    evidence: dict[str, Any]
    score_components: dict[str, float]
    caveats: list[str] = []
    recommended_drop: Optional[LeaguePulseRecommendedDrop] = None

    @model_validator(mode="after")
    def _ensure_overlay_caveat(self) -> "LeaguePulseMarketCard":
        # DTO is the impenetrable label: every overlay card carries the
        # unvalidated-divergence caveat even if a caller omits it (matches
        # PartnerRanking.market_influenced). decision_supported stays False.
        if "market_overlay_unvalidated_divergence" not in self.caveats:
            self.caveats = [*self.caveats, "market_overlay_unvalidated_divergence"]
        return self

    @field_validator("evidence")
    @classmethod
    def _evidence_overlay(cls, v: dict[str, Any]) -> dict[str, Any]:
        extra = set(v) - _OVERLAY_EVIDENCE
        if extra:
            raise ValueError(
                f"overlay card evidence has non-allowlisted keys: {sorted(extra)}"
            )
        return v

    @field_validator("score_components")
    @classmethod
    def _score_overlay(cls, v: dict[str, float]) -> dict[str, float]:
        extra = set(v) - _OVERLAY_SCORE
        if extra:
            raise ValueError(
                f"overlay card score_components has non-allowlisted keys: {sorted(extra)}"
            )
        return v


class LeaguePulseDropCounts(_DSBase):
    team_postures: int = 0
    team_values: int = 0
    partner_rankings: int = 0
    model_native_cards: int = 0
    market_overlay_cards: int = 0
    recommended_drops: int = 0


# ── Envelope ─────────────────────────────────────────────────────────────────


class LeaguePulseResponse(_DSBase):
    status: Literal["active", "degraded"]
    perspective_roster_id: int
    source_artifacts: LeaguePulseSources
    captured_at: str
    caveats: list[str] = []
    team_postures: list[LeaguePulseTeamPosture] = []
    team_values: list[LeaguePulseTeamValue] = []
    partner_rankings: list[LeaguePulsePartnerRanking] = []
    model_native_cards: list[LeaguePulseCard] = []
    market_overlay_cards: list[LeaguePulseMarketCard] = []
    dropped: LeaguePulseDropCounts
