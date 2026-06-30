"""Transitional league_opportunity.v1 → capacity-pool compatibility shim.

The No-Verdict reconcile (Phase 1 T2) replaced the tool-selected single-drop
field on opportunity cards with the descriptive ``roster_capacity_candidates``
pool (``league_opportunity.v2``). Stale on-disk ``league_opportunity.v1``
artifacts still carry the legacy field, so this module reads that ONE legacy key
and migrates it into the v2 pool shape — keeping League Pulse live during the
T2/T3 migration window without re-introducing the legacy field into the
assembler itself (which the No-Verdict cordon scans).

The migrated pool is explicitly marked ``legacy_*`` so the surface never
presents it as a fresh, freely-chosen candidate set, and ``decision_supported``
stays ``False`` throughout.

REMOVE AT T4: once every artifact is regenerated at ``league_opportunity.v2``
and v1 acceptance is dropped from the assembler, delete this module, its import
in ``league_pulse_assembler``, and its scanner allowlist entry.
"""
from __future__ import annotations

from typing import Any, Optional

# The single legacy field name read off a stale league_opportunity.v1 card.
# Housed here (not in the assembler) so the assembler stays free of the cordoned
# legacy token; this module is the tracked, T4-removed home for it.
_LEGACY_DROP_FIELD = "recommended_drop"


def extract_legacy_capacity_pool(raw_card: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Migrate a stale v1 card's legacy single-drop block into a v2 pool dict.

    Returns a ``roster_capacity_candidates``-shaped dict (one legacy item) or
    ``None`` when the legacy field is absent. No nomination is implied: the pool
    is marked as a legacy single-candidate compatibility artifact.
    """
    legacy = raw_card.get(_LEGACY_DROP_FIELD)
    if not legacy:
        return None
    hard_conflict = legacy.get("cut_priority") == 0
    item = {
        "sleeper_player_id": legacy.get("sleeper_player_id"),
        "full_name": legacy.get("full_name"),
        "position": legacy.get("position"),
        "value_status": "unvalued",
        "xvar_pct": None,
        "dvs": None,
        "capacity_conflict_status": (
            "hard_roster_rules_conflict" if hard_conflict else "roster_capacity_pressure"
        ),
        "rule_conflict_label": "IR compliance violation" if hard_conflict else None,
        "caveats": ["valuation_unavailable", "legacy_v1_artifact_migrated"],
        "decision_supported": False,
    }
    return {
        "decision_supported": False,
        "pool_status": "legacy_single_candidate",
        "selection_rule": "legacy_v1_field_migrated_no_tool_selection",
        "narrowing_rule": "stale_v1_artifact_compatibility",
        "sort_key": "legacy_v1_single_candidate_no_sort",
        "items": [item],
        "caveats": ["legacy_v1_artifact_migrated"],
    }


# T3 No-Verdict reconcile: a stale league_opportunity.v1 card carries the old
# action-shaped card types, the hidden opportunity_score composite, and a
# signal_status field. This shim migrates such a card into the v2 contract
# (neutral card types, transparent sort_key/sort_value, mechanical
# evidence_status), so the assembler — which the cordon scans — never references
# these legacy tokens directly. REMOVE AT T4 with the rest of this module.
_LEGACY_CARD_TYPE_MAP = {
    "WAIVER_CANDIDATE": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
    "TAXI_ACTIVATION_CANDIDATE": "TAXI_LONG_TERM_VALUE_PRESENT",
}
_LEGACY_EVIDENCE_STATUS = {
    "gates_passed": "evidence_complete",
    "gates_blocked": "evidence_gated",
    "unavailable": "inputs_unavailable",
}
_MARKET_DELTA_SORT_KEY = "absolute_model_market_delta_desc"
_POSITIONAL_SORT_KEY = "positional_z_differential_desc"
_TAXI_SORT_KEY = "taxi_long_term_value_desc"


def _legacy_evidence_status(signal_status: Any) -> str:
    return _LEGACY_EVIDENCE_STATUS.get(str(signal_status or "unavailable"), "inputs_unavailable")


def normalize_legacy_card(raw_card: dict[str, Any]) -> dict[str, Any]:
    """Return a v2-contract card. v2 cards (which always carry ``sort_key``) pass
    through unchanged; stale v1 cards are migrated in place to the v2 shape."""
    if not isinstance(raw_card, dict) or "sort_key" in raw_card:
        return raw_card

    card = dict(raw_card)
    legacy_type = card.get("card_type")
    new_type = _LEGACY_CARD_TYPE_MAP.get(legacy_type, legacy_type)
    card["card_type"] = new_type

    rationale = dict(card.get("rationale") or {})
    evidence = dict(rationale.get("evidence") or {})
    legacy_signal_status = card.get("signal_status") or evidence.get("signal_status")
    evidence_status = _legacy_evidence_status(legacy_signal_status)

    # Migrate evidence keys to the v2 names.
    if "signal_status" in evidence:
        evidence.pop("signal_status")
        evidence["evidence_status"] = evidence_status
    if "xvar" in evidence:
        evidence["asset_xvar"] = evidence.pop("xvar")

    # Derive the transparent, per-category sort the v2 producer would emit.
    if new_type == _LEGACY_CARD_TYPE_MAP["TAXI_ACTIVATION_CANDIDATE"]:
        sort_key = _TAXI_SORT_KEY
        sort_value = float(evidence.get("raw_xvar") or 0.0)
    elif new_type == "ROSTER_SURPLUS_DEFICIT_MATCH":
        sort_key = _POSITIONAL_SORT_KEY
        z_diff = round(
            abs(float(evidence.get("perspective_position_z") or 0.0))
            + float(evidence.get("counterparty_position_z") or 0.0),
            3,
        )
        evidence["positional_z_differential"] = z_diff
        sort_value = z_diff
    else:
        sort_key = _MARKET_DELTA_SORT_KEY
        sort_value = abs(float(evidence.get("model_minus_market_delta") or 0.0))

    rationale["evidence"] = evidence
    card["rationale"] = rationale
    card["evidence_status"] = evidence_status
    card["sort_key"] = sort_key
    card["sort_value"] = round(float(sort_value), 3)
    # Drop the removed verdict-shaped fields.
    card.pop("opportunity_score", None)
    card.pop("signal_status", None)
    return card
