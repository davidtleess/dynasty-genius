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
