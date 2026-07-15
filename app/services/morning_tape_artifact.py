"""Morning Tape model-population artifact builder (Phase 1, G4-2 identity join).

The artifact OWNS the model population. Building it joins Engine-B scores to the
GSIS→Sleeper crosswalk, but an unresolved or ambiguous identity is a *visible
evidence state* — never a reason to drop an Engine-B row or to arbitrarily pick
one of several conflicting crosswalk candidates. The HTTP surface only reads the
completed artifact (see ``app/api/routes/morning_tape.py``); it never calls this
builder on the request path.

Scope note (G4-2 = identity joining only): conflicting *model* predictions for a
single player are a separate concern and are not adjudicated here. Repeated rows
for one GSIS id are collapsed to the first occurrence so the population carries
each player exactly once, preserving input order.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

SCHEMA_VERSION = "morning_tape_model_population.v1"
_CROSSWALK_STALE_AFTER = timedelta(hours=24)


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _dedupe_scores_preserving_order(
    engine_scores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep each player once, in the order first seen; do not reorder the population."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for score in engine_scores:
        gsis_id = score["player_id"]
        if gsis_id in seen:
            continue
        seen.add(gsis_id)
        unique.append(score)
    return unique


def _crosswalk_index(
    crosswalk_entries: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for entry in crosswalk_entries:
        index.setdefault(entry["gsis_id"], []).append(entry)
    return index


def build_model_population_artifact(
    *,
    engine_scores: list[dict[str, Any]],
    crosswalk_entries: list[dict[str, Any]],
    engine_scores_as_of: str,
    crosswalk_as_of: str,
    now: str,
) -> dict[str, Any]:
    """Join Engine-B scores to the identity crosswalk into the serving artifact.

    Every supplied player survives to the artifact. Identity resolution is
    disclosed per row (``resolved`` / ``unresolved_crosswalk`` / ``ambiguous_crosswalk``);
    an unresolved or ambiguous join carries a null ``sleeper_id`` and a caveat rather
    than a guessed identity. A crosswalk older than 24h degrades the whole artifact
    with receipt evidence but retains its rows.
    """
    unique_scores = _dedupe_scores_preserving_order(engine_scores)
    crosswalk = _crosswalk_index(crosswalk_entries)

    players: list[dict[str, Any]] = []
    resolved_count = 0
    unresolved_count = 0
    ambiguous_count = 0

    for score in unique_scores:
        gsis_id = score["player_id"]
        matches = crosswalk.get(gsis_id, [])
        # Resolution turns on how many *distinct, non-null* sleeper targets exist
        # for this GSIS, not on the raw row count:
        #   - Duplicate-IDENTICAL rows collapse (one distinct target resolves cleanly).
        #   - A bridge row carrying a null sleeper_id is NOT a resolution — it never
        #     counts as a resolved asset, so it classifies as unresolved (keeps the
        #     cohort denominator honest).
        #   - Two or more distinct non-null targets are a genuine ambiguity.
        resolved_sleeper_ids = {
            entry["sleeper_id"]
            for entry in matches
            if entry.get("sleeper_id") is not None
        }
        position = score.get("position")
        score_caveats = list(score.get("caveats", []))

        if len(resolved_sleeper_ids) == 1:
            entry = next(e for e in matches if e.get("sleeper_id") is not None)
            identity = {
                "gsis_id": gsis_id,
                "sleeper_id": entry["sleeper_id"],
                "identity_resolved": True,
                "identity_status": "resolved",
                "player_name": entry.get("name"),
                "position": position,
            }
            resolved_count += 1
            caveats = score_caveats
        elif not resolved_sleeper_ids:
            identity = {
                "gsis_id": gsis_id,
                "sleeper_id": None,
                "identity_resolved": False,
                "identity_status": "unresolved_crosswalk",
                "player_name": None,
                "position": position,
            }
            unresolved_count += 1
            caveats = score_caveats + ["unresolved_crosswalk"]
        else:
            # Multiple crosswalk candidates: keep the row once, resolve nothing.
            identity = {
                "gsis_id": gsis_id,
                "sleeper_id": None,
                "identity_resolved": False,
                "identity_status": "ambiguous_crosswalk",
                "player_name": None,
                "position": position,
            }
            ambiguous_count += 1
            caveats = score_caveats + ["ambiguous_crosswalk"]

        players.append(
            {
                "identity": identity,
                # Per-row No-Verdict disclosure: every player row carries an explicit
                # False so any single-card component renders the disclaimer without
                # having to reach into the model bundle.
                "decision_supported": False,
                "model": {
                    "predicted_avg_ppg_t1_t2": score.get("predicted_avg_ppg_t1_t2"),
                    "engine": score.get("engine"),
                    "feature_season": score.get("feature_season"),
                    "experimental": score.get("experimental", False),
                    "decision_supported": False,
                },
                "caveats": caveats,
            }
        )

    stale = (_parse(now) - _parse(crosswalk_as_of)) > _CROSSWALK_STALE_AFTER
    crosswalk_receipt = {
        "as_of": crosswalk_as_of,
        "status": "stale" if stale else "fresh",
        "caveats": ["crosswalk_stale_over_24h"] if stale else [],
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "degraded" if stale else "ok",
        "decision_supported": False,
        "coverage": {
            "engine_score_count": len(unique_scores),
            "resolved_identity_count": resolved_count,
            "unresolved_identity_count": unresolved_count,
            "ambiguous_identity_count": ambiguous_count,
        },
        "players": players,
        "receipts": {
            "engine_scores": {"as_of": engine_scores_as_of},
            "crosswalk": crosswalk_receipt,
        },
    }
