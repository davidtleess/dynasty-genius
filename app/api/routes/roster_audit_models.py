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

from app.api.routes.players import (
    CounterArgumentField,
    EvidenceListField,
    _counter_argument_field,
    _evidence_list_field,
)
from src.dynasty_genius.eval.backtest_artifact import BacktestResult
from src.dynasty_genius.eval.served_model_alignment import check_served_alignment

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
    manifest but the artifact model_version differs (trust_status_stale) — OR, since
    DG-142, the deployed bundle's bytes do not match the model the published figures
    were measured on. The version strings are the generic "engine_b_v2" everywhere, so
    the string comparison alone was unreachable and the badge could not see a retrain.
    Positions are
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
            elif not (
                alignment := check_served_alignment(pos, result.model_artifact_hash)
            ).aligned:
                # DG-142: the version strings above are the generic "engine_b_v2" on
                # every position, so that comparison can never notice a retrain. Ask
                # the served BYTES instead — the same guard the trust surface uses.
                # Every not-aligned answer refuses, without exception. The two hashes
                # only choose WHICH caveat: both present = we compared and they differ
                # (stale); either absent = we could not read enough to compare
                # (unavailable). On a ticket about a badge asserting what it had not
                # checked, saying "different build" when nothing could be read would
                # repeat the defect one level down.
                status[pos] = "EXPERIMENTAL"
                if alignment.published_hash and alignment.served_hash:
                    caveats.add("trust_status_stale")
                else:
                    caveats.add("trust_status_unavailable")
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
    # DG-128 (2026-09-01): the band ships with the number (DVS units, null when the
    # score is null); dvs_engine is its basis — measured (B), prior (A), or blend.
    dvs_band_low: float | None = None
    dvs_band_high: float | None = None
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


class ReplacementReasoningView(BaseModel):
    """DG-160: how one position's replacement level was derived, in David's own terms.

    His 2026-08-31 ruling 5: "let the derived number stand and show the reasoning … Replacement
    TE = the 12th-best TE, because your league starts 12." Read from the LIVE league snapshot
    rather than from the comment above the constant, because that comment is what was wrong.
    """

    position: str
    rank: int
    points_per_game: float | None = None
    reason: str
    dedicated_starters: int
    shared_places_assumed: int
    shared_places_available: int
    flex_is_assumed: bool = False
    assumption: str = ""


class ReplacementBudgetView(BaseModel):
    """Whether all four replacement ranks can be true at once in this league.

    The detector. It asks no behavioural question — only whether the ranks jointly demand more
    flex and superflex places than the league has, which is arithmetic.
    """

    demanded: int
    available: int
    over_subscribed_by: int
    status: Literal["agrees", "disagrees"]
    largest_demand: str | None = None
    explanation: str


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
    replacement_reasoning: list[ReplacementReasoningView] = Field(default_factory=list)
    replacement_budget: ReplacementBudgetView | None = None
    decision_supported: Literal[False] = False


# ── Task 3: allowlist mapper (market-safe, token-enforced, applicability) ──────

# Explicit scalar allowlist. Anything not named here (market_overlay, market_value,
# future_*, etc.) is excluded from the David-facing player by construction — this is
# the leak fix: no raw pvo.dict() pass-through.
_SCALARS = (
    "player_id", "full_name", "position", "nfl_team", "age", "sleeper_id",
    "is_prospect", "draft_class", "nfl_draft_pick", "nfl_draft_round", "engine_used",
    "model_version", "model_grade", "dvs_engine", "dynasty_value_score",
    "dvs_band_low", "dvs_band_high",
    "projection_1y", "projection_2y", "projection_3y", "xvar", "dvs_pct",
    "signal_completeness", "inputs_present", "inputs_missing",
)


def _map_signals(raw: dict | None) -> RosterAuditSignalsView | None:
    """Curate the nested signals view: list + scalar token-only fields validated through
    SAFE_TOKENS; decision_supported is Literal[False] so a nested true cannot survive."""
    if not raw:
        return None
    drivers, dc1 = validate_tokens(raw.get("signal_drivers"))
    cav, dc2 = validate_tokens(raw.get("caveats"))
    signal, sc1 = validate_token(raw.get("signal"))           # R3-1: scalar token-only
    avc, sc2 = validate_token(raw.get("age_value_context"))   # R3-1
    liq, sc3 = validate_token(raw.get("liquidity_risk"))      # R3-1
    return RosterAuditSignalsView(
        cliff_age=raw.get("cliff_age"),
        years_to_cliff=raw.get("years_to_cliff"),
        age_cliff_risk=raw.get("age_cliff_risk"),
        biological_debt_score=raw.get("biological_debt_score"),  # R2-3 retained
        liquidity_risk=liq,
        signal=signal,
        signal_drivers=drivers,
        age_value_context=avc,
        caveats=cav + dc1 + dc2 + sc1 + sc2 + sc3,
    )


def map_player(raw: dict) -> RosterAuditPlayer:
    """Explicit ALLOWLIST mapping (no raw pvo.dict()); market/value/future fields are
    excluded by construction; David-facing text is validated/suppressed.

    Top-level PVO caveats are free-text uncertainty/provenance evidence, so they use
    banned-language filtering. Nested roster-audit/QB caveats remain token-only.
    """
    data: dict = {k: raw.get(k) for k in _SCALARS}
    caveats = _evidence_list_field(raw.get("caveats"))
    data["caveats"] = caveats.items + caveats.caveats
    data["counter_argument"] = _counter_argument_field(raw.get("counter_argument"))
    data["top_drivers"] = _evidence_list_field(raw.get("top_drivers"))
    data["risk_flags"] = _evidence_list_field(raw.get("risk_flags"))
    data["roster_audit"] = _map_signals(raw.get("roster_audit"))
    # R2-6: scoped to run_audit_pvo output (which emits engine_a / engine_b). Repo-wide,
    # engine_used can carry engine_a_*_ridge via pvo_assembler; this mapper consumes
    # run_audit_pvo output, so exact "engine_b" equality is correct here.
    data["model_status_applies"] = raw.get("engine_used") == "engine_b"
    return RosterAuditPlayer(**{k: v for k, v in data.items() if v is not None})


# ── Task 4: envelope assembler (QB token validation, isolated-drop / systemic-503) ──


class RosterDependencyError(RuntimeError):
    """Systemic roster-audit failure (e.g. every row unmappable) -> caller returns 503."""


def _map_qb(raw: dict) -> QBContextCard:
    """Map a raw QB-context card through the allowlist + token validation. The source
    label is token-only (R2-2): an unsafe source raises, so the caller drops the card."""
    ann, dc1 = validate_tokens(raw.get("qb_context_annotations"))
    cav, dc2 = validate_tokens(raw.get("qb_context_caveats"))
    src = raw.get("source_qb_context_annotations")
    if src not in SAFE_TOKENS:
        raise ValueError(f"unsafe source token {src!r}")
    allow = {
        "player_id", "full_name", "identity_coverage",
        "epa_per_dropback", "cpoe", "dakota", "dropback_count", "pass_attempts",
    }
    base = {k: raw.get(k) for k in allow if raw.get(k) is not None}
    return QBContextCard(
        **base,
        source_qb_context_annotations=src,
        qb_context_annotations=ann,
        qb_context_caveats=cav + dc1 + dc2,
    )


def _build_replacement_reasoning(
    audit: dict,
) -> tuple[list[ReplacementReasoningView], ReplacementBudgetView | None]:
    """Derive the on-screen reasoning from the league structure the audit carries.

    Returns empty when the audit does not carry a lineup — an explanation invented without the
    league's own slots would be the exact failure this exists to catch.
    """
    from src.dynasty_genius.features.replacement_reasoning import (
        audit_shared_slot_budget,
        explain_replacement,
        load_league_structure,
    )

    # An injected league wins (tests), otherwise read the captured snapshot. If neither is
    # available, show NOTHING: a derivation stated without the league's own slots is a
    # confident sentence resting on a structure nobody checked.
    league = audit.get("league") or load_league_structure() or {}
    roster_positions = league.get("roster_positions")
    teams = league.get("teams")
    if not roster_positions or not teams:
        return [], None
    # DG-159: read the points a game directly. This used to back-derive them as
    # `replacement_DVS / 100 * P90`, which was only ever right while the score's
    # denominator WAS the position P90 — and the moment those parted the sentence would
    # have gone on reading confidently while quoting a number no player is measured
    # against (receiver replacement would have shown as 6.53 rather than 9.05).
    from src.dynasty_genius.models.engine_b_contract import (
        ENGINE_B_VAR_THRESHOLDS,
        REPLACEMENT_PPG,
    )

    views: list[ReplacementReasoningView] = []
    for position, rank in ENGINE_B_VAR_THRESHOLDS.items():
        ppg = REPLACEMENT_PPG.get(position)
        out = explain_replacement(
            position=position,
            shipped_rank=rank,
            roster_positions=roster_positions,
            teams=int(teams),
            replacement_ppg=ppg,
            thresholds=dict(ENGINE_B_VAR_THRESHOLDS),
        )
        views.append(
            ReplacementReasoningView(
                position=out["position"],
                rank=out["rank"],
                points_per_game=out["points_per_game"],
                reason=out["reason"],
                dedicated_starters=out["dedicated"],
                shared_places_assumed=out["shared_places_demanded"],
                shared_places_available=out["shared_places_available"],
                flex_is_assumed=out["flex_is_assumed"],
                assumption=out["assumption"],
            )
        )
    b = audit_shared_slot_budget(
        thresholds=dict(ENGINE_B_VAR_THRESHOLDS),
        roster_positions=roster_positions,
        teams=int(teams),
    )
    budget = ReplacementBudgetView(
        demanded=b["demanded"],
        available=b["available"],
        over_subscribed_by=b["over_subscribed_by"],
        status=b["status"].value,
        largest_demand=b["largest_demand"],
        explanation=b["explanation"],
    )
    return views, budget


def assemble_response(audit: dict) -> RosterAuditResponse:
    """Map run_audit_pvo output into the typed RosterAuditResponse. Isolated unmappable
    rows are dropped, counted, named (player_row_dropped_corrupt), and degrade the status;
    ALL rows failing is systemic -> RosterDependencyError (caller 503), not a silent empty
    success. QB cards with an unsafe source label are dropped + named
    (qb_context_card_dropped_corrupt, R2-5). Any trust caveat forces degraded."""
    raw_players = audit.get("players", [])
    mapped: list[RosterAuditPlayer] = []
    dropped = 0
    for raw in raw_players:
        try:
            mapped.append(map_player(raw))
        except Exception:
            dropped += 1
    if raw_players and not mapped:
        raise RosterDependencyError("all roster rows failed to map")
    qb_cards: list[QBContextCard] = []
    qb_dropped = 0
    for raw in audit.get("qb_context_cards", []):
        try:
            qb_cards.append(_map_qb(raw))
        except Exception:
            qb_dropped += 1
    status_map, trust_caveats = load_model_status_by_position(
        [p.position for p in mapped]
    )
    # DG-160: the derivation goes on screen beside the number it produced. Built from the
    # league snapshot the audit was run against, so a rank his lineup cannot support is
    # visible rather than buried in a constant's comment.
    reasoning, budget = _build_replacement_reasoning(audit)
    caveats = list(audit.get("caveats", [])) + trust_caveats
    status = "active"
    if dropped:
        caveats.append("player_row_dropped_corrupt")
        status = "degraded"
    if qb_dropped:  # R2-5: QB-card drop is degraded + named, never silent
        caveats.append("qb_context_card_dropped_corrupt")
        status = "degraded"
    if trust_caveats:
        status = "degraded"
    return RosterAuditResponse(
        replacement_reasoning=reasoning,
        replacement_budget=budget,
        status=status,
        engine=audit.get("engine", "pvo_assembler_v1"),
        reason=audit.get("reason", ""),
        model_status_by_position=status_map,
        caveats=caveats,
        players=mapped,
        qb_context_cards=qb_cards,
        dropped_player_count=dropped + qb_dropped,
    )
