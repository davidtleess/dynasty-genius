"""League Pulse Increment 1 — allowlist mappers + fail-closed assembler.

Maps the three read-only Phase 17/18 artifacts into the typed League Pulse DTOs
(`league_pulse_models`). Allowlist-FIRST: each mapper selects known keys so
market fields (`market_overlay_total`, raw `players`, market evidence on
model-native cards) are suppressed without dropping a valid record; the DTO
`extra="forbid"` is the backstop. Fail-closed: isolated unmappable records are
dropped + counted (degraded-200); a missing/schema-wrong/all-unmappable required
section, or a total cross-artifact join failure, raises
`LeaguePulseDependencyError` (the route translates it to 503).

Design spec: docs/superpowers/specs/2026-06-22-league-pulse-increment-1-contract-design.md
"""
from __future__ import annotations

from typing import Any, Optional

from app.api.routes import league_pulse_v1_compat
from app.api.routes.league_pulse_models import (
    _MODEL_NATIVE_SCORE,
    LeaguePulseCapacityCandidate,
    LeaguePulseCapacityCandidatePool,
    LeaguePulseCard,
    LeaguePulseDropCounts,
    LeaguePulseMarketCard,
    LeaguePulsePartnerRanking,
    LeaguePulseResponse,
    LeaguePulseSources,
    LeaguePulseTeamPosture,
    LeaguePulseTeamValue,
    LeaguePulseValueViews,
    neutral_label_for_token,
    validate_tokens,
)


def _safe_caveats(raw: list[str] | None) -> list[str]:
    """SAFE_TOKEN-filter an emitted caveat list (drop banned/unknown + mark)."""
    clean, suppression = validate_tokens(raw)
    return clean + suppression

_EXPECTED_SCHEMAS = {
    "team_posture": "team_posture.v1",
    "team_value_matrix": "team_value_matrix.v1",
}

# League Pulse tolerates both league_opportunity schema versions during the
# Phase 1 T2/T3 migration: v2 cards carry the descriptive capacity pool natively;
# stale v1 cards are migrated via league_pulse_v1_compat. T4 drops v1 acceptance.
ACCEPTED_LEAGUE_OPPORTUNITY_SCHEMAS = frozenset(
    {"league_opportunity.v1", "league_opportunity.v2"}
)

_VALUE_VIEW_KEYS = (
    "starter_weighted_xvar",
    "lineup_xvar",
    "depth_credit_xvar",
    "total_xvar_capped",
    "top_n_xvar",
)
_CAPACITY_ITEM_KEYS = (
    "sleeper_player_id",
    "full_name",
    "position",
    "value_status",
    "xvar_pct",
    "dvs",
    "capacity_conflict_status",
    "rule_conflict_label",
    "caveats",
    "decision_supported",
)
_CAPACITY_POOL_KEYS = (
    "pool_status",
    "selection_rule",
    "narrowing_rule",
    "sort_key",
    "caveats",
    "decision_supported",
)
_MODEL_NATIVE_CARD_TYPES = frozenset({"ROSTER_SURPLUS_DEFICIT_MATCH"})
_OVERLAY_CARD_TYPES = frozenset(
    {
        "UNROSTERED_MODEL_MARKET_DIVERGENCE",
        "DIVERGENCE_MODEL_HIGH",
        "DIVERGENCE_MARKET_HIGH",
        "TAXI_LONG_TERM_VALUE_PRESENT",
    }
)


class LeaguePulseDependencyError(Exception):
    """Systemic failure: a required artifact is missing/schema-wrong/all-unmappable
    or the cross-artifact roster join is empty. The route maps this to 503."""


# ── Per-section mappers ──────────────────────────────────────────────────────


def map_team_posture(raw: dict[str, Any]) -> LeaguePulseTeamPosture:
    posture = raw.get("posture") or {}
    return LeaguePulseTeamPosture(
        roster_id=raw["roster_id"],
        team_name=(raw.get("owner") or {}).get("team_name"),
        posture_label=posture["label"],
        score=posture["score"],
        components=posture.get("components") or {},
        caveats=_safe_caveats(posture.get("caveats")),
    )


def map_team_value(raw: dict[str, Any]) -> LeaguePulseTeamValue:
    views = raw["team_value_views"]  # KeyError → unmappable (caught by assembler)
    value_views = LeaguePulseValueViews(
        **{k: views[k] for k in _VALUE_VIEW_KEYS}
    )
    return LeaguePulseTeamValue(
        roster_id=raw["roster_id"],
        team_name=(raw.get("owner") or {}).get("team_name"),
        value_views=value_views,
        age_profile=raw.get("age_profile") or {},
        positional_summary=raw.get("positional_summary") or {},
        future_picks=raw.get("future_picks") or {},
    )


def map_partner_ranking(raw: dict[str, Any]) -> LeaguePulsePartnerRanking:
    return LeaguePulsePartnerRanking(
        counterparty_roster_id=raw["counterparty_roster_id"],
        counterparty_team_name=raw.get("counterparty_team_name"),
        partner_score=raw["partner_score"],
        matched_positions=list(raw.get("matched_positions") or []),
        score_components=raw.get("score_components") or {},
        evidence=raw.get("evidence") or {},
    )


def _map_capacity_item(raw: dict[str, Any]) -> LeaguePulseCapacityCandidate:
    """Allowlist-select one capacity candidate row into its typed DTO."""
    return LeaguePulseCapacityCandidate(
        **{k: raw[k] for k in _CAPACITY_ITEM_KEYS if k in raw}
    )


def _map_capacity_pool(raw_card: dict[str, Any]) -> Optional[LeaguePulseCapacityCandidatePool]:
    """Map the descriptive capacity pool; drop the block (not the card) if malformed.

    Prefers the native v2 ``roster_capacity_candidates`` pool. Falls back to the
    transitional v1-compat shim, which migrates a stale ``league_opportunity.v1``
    card's legacy single-drop field into the same pool shape.
    """
    pool = raw_card.get("roster_capacity_candidates")
    if pool is None:
        pool = league_pulse_v1_compat.extract_legacy_capacity_pool(raw_card)
    if pool is None:
        return None
    try:
        fields = {k: pool[k] for k in _CAPACITY_POOL_KEYS if k in pool}
        fields["items"] = [_map_capacity_item(it) for it in pool.get("items") or []]
        return LeaguePulseCapacityCandidatePool(**fields)
    except Exception:
        return None


def map_card(raw: dict[str, Any]) -> Optional[tuple[str, Any]]:
    """Route + sanitize one opportunity card. Returns (lane, dto) or None (drop)."""
    # Stale league_opportunity.v1 cards (old action-shaped card types, the
    # removed composite score, and the legacy signal field) are normalized into
    # the v2 contract by the compat shim, which is the sole home for the
    # cordoned legacy tokens.
    raw = league_pulse_v1_compat.normalize_legacy_card(raw)
    card_type = raw.get("card_type")
    rationale = raw.get("rationale") or {}
    common = {
        "card_id": raw.get("card_id"),
        "card_type": card_type,
        "evidence_status": raw.get("evidence_status"),
        "sort_key": raw.get("sort_key"),
        "sort_value": raw.get("sort_value"),
        "rationale_primary": neutral_label_for_token(rationale.get("primary") or ""),
        "rationale_secondary": [
            neutral_label_for_token(t) for t in (rationale.get("secondary") or [])
        ],
        "evidence": dict(rationale.get("evidence") or {}),
        "caveats": _safe_caveats(raw.get("caveats")),
    }
    score = dict(raw.get("score_components") or {})

    if card_type in _MODEL_NATIVE_CARD_TYPES:
        # Model-native purity: divergence_score must be a real zero; strip it.
        # A nonzero divergence_score, an unexpected score key, or a market
        # evidence key (rejected by the DTO) drops the card fail-closed.
        divergence = score.get("divergence_score", 0.0)
        if divergence not in (0, 0.0):
            return None
        if set(score) - _MODEL_NATIVE_SCORE - {"divergence_score"}:
            return None
        score_out = {k: v for k, v in score.items() if k in _MODEL_NATIVE_SCORE}
        try:
            card = LeaguePulseCard(score_components=score_out, **common)
        except Exception:
            return None
        return ("model_native_cards", card)

    if card_type in _OVERLAY_CARD_TYPES:
        try:
            card = LeaguePulseMarketCard(
                score_components=score,
                roster_capacity_candidates=_map_capacity_pool(raw),
                **common,
            )
        except Exception:
            return None
        return ("market_overlay_cards", card)

    return None


# ── Assembler ────────────────────────────────────────────────────────────────


def _require_schema(artifact: dict[str, Any], key: str) -> None:
    if (artifact or {}).get("schema_version") != _EXPECTED_SCHEMAS[key]:
        raise LeaguePulseDependencyError(
            f"{key} schema_version mismatch: expected {_EXPECTED_SCHEMAS[key]}, "
            f"got {(artifact or {}).get('schema_version')!r}"
        )


def _require_league_opportunity_schema(artifact: dict[str, Any]) -> None:
    schema_version = (artifact or {}).get("schema_version")
    if schema_version not in ACCEPTED_LEAGUE_OPPORTUNITY_SCHEMAS:
        raise LeaguePulseDependencyError(
            "league_opportunity schema_version mismatch: expected one of "
            f"{sorted(ACCEPTED_LEAGUE_OPPORTUNITY_SCHEMAS)}, got {schema_version!r}"
        )


def assemble_league_pulse(
    posture_artifact: dict[str, Any],
    value_artifact: dict[str, Any],
    opportunity_artifact: dict[str, Any],
) -> LeaguePulseResponse:
    """Assemble the read-only League Pulse response, fail-closed."""
    _require_schema(posture_artifact, "team_posture")
    _require_schema(value_artifact, "team_value_matrix")
    _require_league_opportunity_schema(opportunity_artifact)

    posture_teams = posture_artifact.get("teams") or []
    value_teams = value_artifact.get("teams") or []
    posture_rosters = {t.get("roster_id") for t in posture_teams}
    value_rosters = {t.get("roster_id") for t in value_teams}
    known_rosters = posture_rosters | value_rosters
    # Total cross-artifact join failure: posture and value share no rosters.
    if not (posture_rosters & value_rosters):
        raise LeaguePulseDependencyError("cross-artifact roster join is empty")

    dropped = {
        "team_postures": 0,
        "team_values": 0,
        "partner_rankings": 0,
        "model_native_cards": 0,
        "market_overlay_cards": 0,
        "roster_capacity_candidate_pools": 0,
    }

    team_postures: list[LeaguePulseTeamPosture] = []
    for t in posture_teams:
        try:
            team_postures.append(map_team_posture(t))
        except Exception:
            dropped["team_postures"] += 1
    if posture_teams and not team_postures:
        raise LeaguePulseDependencyError("all team_postures unmappable")

    team_values: list[LeaguePulseTeamValue] = []
    for t in value_teams:
        try:
            team_values.append(map_team_value(t))
        except Exception:
            dropped["team_values"] += 1
    if value_teams and not team_values:
        raise LeaguePulseDependencyError("all team_values unmappable")

    partner_rankings: list[LeaguePulsePartnerRanking] = []
    for raw_pr in opportunity_artifact.get("partner_rankings") or []:
        if raw_pr.get("counterparty_roster_id") not in known_rosters:
            dropped["partner_rankings"] += 1
            continue
        try:
            partner_rankings.append(map_partner_ranking(raw_pr))
        except Exception:
            dropped["partner_rankings"] += 1

    model_native_cards: list[LeaguePulseCard] = []
    market_overlay_cards: list[LeaguePulseMarketCard] = []
    for raw_card in opportunity_artifact.get("cards") or []:
        # Normalize stale v1 cards once so the drop-count + pool-source checks
        # below see v2 card types (map_card normalizes again, idempotently).
        raw_card = league_pulse_v1_compat.normalize_legacy_card(raw_card)
        result = map_card(raw_card)
        if result is None:
            if raw_card.get("card_type") in _OVERLAY_CARD_TYPES:
                dropped["market_overlay_cards"] += 1
            else:
                dropped["model_native_cards"] += 1
            continue
        lane, card = result
        if lane == "model_native_cards":
            model_native_cards.append(card)
        else:
            market_overlay_cards.append(card)
            # dropped-count semantics (matches every sibling in `dropped`): a
            # capacity pool PRESENT in the source artifact that failed to map
            # (malformed) is a DROP. An absent pool is not a drop.
            pool_source_present = (
                raw_card.get("roster_capacity_candidates") is not None
                or league_pulse_v1_compat.extract_legacy_capacity_pool(raw_card) is not None
            )
            if pool_source_present and card.roster_capacity_candidates is None:
                dropped["roster_capacity_candidate_pools"] += 1

    captured_at = max(
        a.get("captured_at") or ""
        for a in (posture_artifact, value_artifact, opportunity_artifact)
    )
    # League Pulse is inherently artifact-state (never live) → always degraded
    # with a descriptive artifact-state caveat (graceful-degrade, not 503).
    artifact_state_caveat = f"league_pulse_artifact_state_{captured_at[:10]}"

    sources = LeaguePulseSources(
        team_posture={
            "schema_version": posture_artifact.get("schema_version"),
            "captured_at": posture_artifact.get("captured_at"),
        },
        team_value_matrix={
            "schema_version": value_artifact.get("schema_version"),
            "captured_at": value_artifact.get("captured_at"),
        },
        league_opportunity={
            "schema_version": opportunity_artifact.get("schema_version"),
            "captured_at": opportunity_artifact.get("captured_at"),
        },
    )

    return LeaguePulseResponse(
        status="degraded",
        perspective_roster_id=opportunity_artifact.get("perspective_roster_id"),
        source_artifacts=sources,
        captured_at=captured_at,
        caveats=[artifact_state_caveat],
        team_postures=team_postures,
        team_values=team_values,
        partner_rankings=partner_rankings,
        model_native_cards=model_native_cards,
        market_overlay_cards=market_overlay_cards,
        dropped=LeaguePulseDropCounts(**dropped),
    )
