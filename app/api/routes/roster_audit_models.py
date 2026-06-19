"""Roster Audit Increment 1 — typed, allowlist-mapped, leakage-safe contract models.

Task 1: live, fail-closed Engine-B trust loader (``load_model_status_by_position``).
Task 2: typed response models (no ``extra="allow"``), curated signals view, and the
SAFE_TOKENS allowlist + token validators. Subsequent tasks add the allowlist mapper
and the envelope assembler.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.api.routes.players import CounterArgumentField, EvidenceListField
from src.dynasty_genius.eval.backtest_artifact import BacktestResult

TRUST_DIR = Path("app/data/backtest/trust_surface/latest")
_VALID = {"VALIDATED", "PROVISIONAL", "EXPERIMENTAL"}


def _manifest_versions() -> dict[str, str]:
    """Live manifest model_version per position (upper-cased). Fail-closed: any read or
    parse failure yields an empty map, which disables the stale check rather than crashing."""
    try:
        manifest = json.loads((TRUST_DIR / "manifest.json").read_text(encoding="utf-8"))
        return {
            k.upper(): v.get("model_version")
            for k, v in manifest.get("positions", {}).items()
        }
    except Exception:
        return {}


def load_model_status_by_position(
    positions: list[str],
) -> tuple[dict[str, str], list[str]]:
    """LIVE per-position Engine-B model_status via BacktestResult.load. Fail-closed:
    missing / malformed / out-of-domain / unverifiable-freshness / STALE -> EXPERIMENTAL
    + caveat; keys are NEVER omitted (no fail-open). Freshness can only be trusted when
    the live manifest carries this position's model_version: if the manifest is missing,
    malformed, or lacks the position key, the artifact is treated as unverified
    (trust_status_unavailable) rather than trusted. Stale (R2-4) = the position IS in the
    manifest but the artifact model_version differs (trust_status_stale). Positions are
    upper-cased and de-duplicated; an empty list yields an empty status map and no
    caveats."""
    manifest = _manifest_versions()
    status: dict[str, str] = {}
    caveats: set[str] = set()
    for pos in sorted({p.upper() for p in positions}):
        path = TRUST_DIR / f"backtest_result_{pos}.json"
        try:
            result = BacktestResult.load(path)
            value = result.promotion_gate.model_status
            if value not in _VALID:
                status[pos] = "EXPERIMENTAL"
                caveats.add("trust_status_unavailable")
            elif pos not in manifest:
                # Cannot verify freshness without a manifest version -> fail closed.
                status[pos] = "EXPERIMENTAL"
                caveats.add("trust_status_unavailable")
            elif result.model_version != manifest[pos]:
                status[pos] = "EXPERIMENTAL"
                caveats.add("trust_status_stale")
            else:
                status[pos] = value
        except Exception:
            status[pos] = "EXPERIMENTAL"
            caveats.add("trust_status_unavailable")
    return status, sorted(caveats)


# ── Task 2: token allowlist + validators ──────────────────────────────────────

# Single source of truth (Codex centralization note); seeded from roster_auditor
# producers (T7 completeness test enforces parity with what the producers emit).
SAFE_TOKENS: frozenset[str] = frozenset({
    # trust / model
    "trust_status_unavailable", "trust_status_stale", "negative_r2_lower_bound",
    "low_sample_holdout",
    # caveats (verified producers, roster_auditor.py)
    "no_market_overlay", "no_market_derived_inputs", "no_internal_value_signal",
    "no_usage_signal", "age_curve_only", "engine_b_experimental_v1_fallback",
    # signal (verified)
    "past_cliff", "at_cliff", "approaching_cliff", "no_age_signal",
    # signal_drivers (verified)
    "age_past_position_cliff", "age_at_position_cliff",
    "age_within_two_years_of_position_cliff", "age_not_near_position_cliff",
    # age_value_context (verified)
    "past_cliff_depreciation_risk", "no_engine_b_projection",
    "approaching_cliff_high_projection", "approaching_cliff_low_projection",
    "prime_window_high_projection", "stable_age_low_projection",
    # liquidity_risk (verified)
    "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH", "MEDIUM_LIMITED_ESCAPE_HATCH", "LOW",
    # QB context (verified): annotations / caveats / source label
    "low_td_int_ratio_bust_context", "all_purpose_yards_mobility_context",
    "missing_qb_college_context", "p2s_context_unavailable",
    "cfbd_qb_context_annotations",
    # drop reasons
    "player_row_dropped_corrupt", "qb_context_card_dropped_corrupt",
})


def validate_tokens(raw: list[str] | None) -> tuple[list[str], list[str]]:
    """Keep only SAFE_TOKENS; drop banned/unknown with a caveat (AC-5 token-only, list)."""
    items = list(raw or [])
    clean = [t for t in items if t in SAFE_TOKENS]
    caveats = ["evidence_suppressed_banned_term"] if len(clean) != len(items) else []
    return clean, caveats


def validate_token(value: str | None) -> tuple[str | None, list[str]]:
    """Scalar token-only (R3-1): pass None or a SAFE_TOKEN; else -> None + caveat."""
    if value is None or value in SAFE_TOKENS:
        return value, []
    return None, ["evidence_suppressed_banned_term"]


class RosterAuditSignalsView(BaseModel):
    """F3: curated signals view; nested decision_supported can never leak true."""

    cliff_age: int | None = None
    years_to_cliff: int | None = None
    age_cliff_risk: float | None = None
    biological_debt_score: float | None = None  # R2-3: retained (populated + decision-relevant)
    liquidity_risk: str | None = None
    signal: str | None = None
    signal_drivers: list[str] = Field(default_factory=list)
    age_value_context: str | None = None
    caveats: list[str] = Field(default_factory=list)
    decision_supported: Literal[False] = False


class QBContextCard(BaseModel):
    """F2: explicitly typed; extra fields forbidden (no provenance/market backdoor)."""

    model_config = {"extra": "forbid"}
    player_id: str
    full_name: str
    identity_coverage: Literal["FULL", "PARTIAL", "NONE"]
    context_role: Literal["context_signal"] = "context_signal"
    epa_per_dropback: float | None = None
    cpoe: float | None = None
    dakota: float | None = None
    dropback_count: float | None = None
    pass_attempts: float | None = None
    qb_context_annotations: list[str] = Field(default_factory=list)
    qb_context_caveats: list[str] = Field(default_factory=list)
    source_qb_context_annotations: str
    decision_supported: Literal[False] = False


class RosterAuditPlayer(BaseModel):
    player_id: str
    full_name: str
    position: str
    nfl_team: str | None = None
    age: float | None = None
    sleeper_id: str | None = None
    is_prospect: bool = False
    draft_class: int | None = None
    nfl_draft_pick: int | None = None
    nfl_draft_round: int | None = None
    engine_used: str | None = None
    model_version: str | None = None
    model_grade: str
    dvs_engine: Literal["A", "B", "blend"] | None = None
    model_status_applies: bool = False
    dynasty_value_score: float | None = None
    projection_1y: float | None = None
    projection_2y: float | None = None
    projection_3y: float | None = None
    xvar: float | None = None
    dvs_pct: float | None = None
    signal_completeness: float = 0.0
    inputs_present: list[str] = Field(default_factory=list)
    inputs_missing: list[str] = Field(default_factory=list)
    counter_argument: CounterArgumentField
    top_drivers: EvidenceListField
    risk_flags: EvidenceListField
    caveats: list[str] = Field(default_factory=list)
    roster_audit: RosterAuditSignalsView | None = None
    decision_supported: Literal[False] = False


ROSTER_AUDIT_PLAYER_FIELDS: frozenset[str] = frozenset(RosterAuditPlayer.model_fields)


class RosterAuditResponse(BaseModel):
    status: Literal["active", "degraded"]
    engine: str
    reason: str
    model_status_by_position: dict[
        str, Literal["VALIDATED", "PROVISIONAL", "EXPERIMENTAL"]
    ]
    caveats: list[str] = Field(default_factory=list)
    players: list[RosterAuditPlayer] = Field(default_factory=list)
    qb_context_cards: list[QBContextCard] = Field(default_factory=list)
    dropped_player_count: int = 0
    decision_supported: Literal[False] = False
