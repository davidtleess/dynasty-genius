"""Read-only membership in the declared frozen prediction cohort.

This is a historical evaluation fact, separate from a player's current model route.
The lookup mirrors the scorer's declared capture and five-column join key without
changing capture, scorer, or identity eligibility.
"""

from __future__ import annotations

import contextlib
import json
import math
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

MODEL_SUPPORTED_ENGINE_PATHS = frozenset({"ENGINE_A", "ENGINE_B", "BLEND_AB"})
KNOWN_NON_MODEL_ENGINE_PATHS = frozenset(
    {"PRE_MODEL", "MARKET_ONLY", "INACTIVE", "CONTEXT_ONLY", "UNRESOLVED_IDENTITY"}
)

_MEMBERSHIP_QUERY = """
    SELECT r.engine_path AS engine_path,
           j.player_key AS joinable_player_key,
           s.player_key AS snapshot_player_key,
           s.prediction_ppg_status AS prediction_ppg_status,
           s.projection_2y AS projection_2y
      FROM model_forward_capture_raw AS r
      LEFT JOIN model_forward_capture_joinable AS j
        ON j.capture_date = r.capture_date
       AND j.source = r.source
       AND j.semantic_output_hash = r.semantic_output_hash
       AND j.provenance_hash = r.provenance_hash
       AND j.player_key = r.player_key
      LEFT JOIN model_forward_prediction_snapshot AS s
        ON s.capture_date = r.capture_date
       AND s.source = r.source
       AND s.semantic_output_hash = r.semantic_output_hash
       AND s.provenance_hash = r.provenance_hash
       AND s.player_key = r.player_key
     WHERE r.capture_date = ?
       AND r.source = ?
       AND r.sleeper_id = ?
"""

_INCLUDED_ROSTER_QUERY = """
    SELECT j.sleeper_id AS sleeper_id,
           s.prediction_ppg_status AS prediction_ppg_status,
           s.projection_2y AS projection_2y
      FROM model_forward_capture_joinable AS j
      JOIN model_forward_prediction_snapshot AS s
        ON s.capture_date = j.capture_date
       AND s.source = j.source
       AND s.semantic_output_hash = j.semantic_output_hash
       AND s.provenance_hash = j.provenance_hash
       AND s.player_key = j.player_key
     WHERE s.capture_date = ?
       AND s.source = ?
"""


def _unavailable(*, season: int, capture_date: str | None) -> dict[str, Any]:
    return {
        "season": season,
        "frozen_capture_date": capture_date,
        "status": "unavailable",
        "basis": "store_unavailable_or_ambiguous",
        "message": "Frozen prediction membership is currently unavailable.",
        "coverage": None,
        "decision_supported": False,
    }


def _load_declaration(path: Path, season: int) -> tuple[str, str] | None:
    try:
        payload = json.loads(path.read_text(), object_pairs_hook=_reject_duplicate_keys)
        if not isinstance(payload, dict):
            return None
        seasons = payload.get("seasons")
        if not isinstance(seasons, dict):
            return None
        entry = seasons.get(str(season))
        if not isinstance(entry, dict):
            return None
        capture_date = entry["frozen_capture_date"]
        source = entry["source"]
        declared_by = entry["declared_by"]
        declared_at = entry["declared_at"]
        if not all(
            isinstance(value, str) and value.strip()
            for value in (capture_date, source, declared_by, declared_at)
        ):
            return None
        datetime.strptime(capture_date, "%Y-%m-%d")
        declared_at_value = datetime.fromisoformat(declared_at)
        if "T" not in declared_at or declared_at_value.tzinfo is None:
            return None
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return capture_date, source


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    for key, _value in pairs:
        if key in seen:
            raise ValueError("declaration_duplicate_json_key")
        seen.add(key)
    return dict(pairs)


def _finite_projection(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _classify_row(row: sqlite3.Row) -> tuple[str, str]:
    engine_path = row["engine_path"]
    joinable = row["joinable_player_key"] is not None
    snapshot = row["snapshot_player_key"] is not None

    if engine_path in KNOWN_NON_MODEL_ENGINE_PATHS:
        # The capture driver writes a companion row for every raw row, including
        # PRE_MODEL rows (with a null/incomplete prediction). Historical exclusion
        # is proven by the normal absence from joinable, not by companion absence.
        if joinable:
            return "unavailable", "store_unavailable_or_ambiguous"
        if snapshot and not (
            row["prediction_ppg_status"]
            in {"capture_incomplete", "missing_legacy_capture"}
            and row["projection_2y"] is None
        ):
            return "unavailable", "store_unavailable_or_ambiguous"
        return "not_in_frozen_prediction_cohort", "non_model_route_at_freeze"

    if engine_path not in MODEL_SUPPORTED_ENGINE_PATHS:
        return "unavailable", "store_unavailable_or_ambiguous"

    if not joinable:
        return "unavailable", "store_unavailable_or_ambiguous"
    if not snapshot:
        return "prediction_capture_incomplete", "prediction_capture_incomplete"

    status = row["prediction_ppg_status"]
    projection = row["projection_2y"]
    if status == "captured" and _finite_projection(projection):
        return "included", "model_supported_prediction_captured"
    if (
        status in {"capture_incomplete", "missing_legacy_capture"}
        and projection is None
    ) or (status == "captured" and projection is None):
        return "prediction_capture_incomplete", "prediction_capture_incomplete"
    return "unavailable", "store_unavailable_or_ambiguous"


def _message(status: str, season: int) -> str:
    if status == "included":
        return f"A model prediction was frozen for {season} outcome evaluation."
    if status == "not_in_frozen_prediction_cohort":
        return f"No model prediction was frozen for {season} outcome evaluation."
    if status == "prediction_capture_incomplete":
        return f"The {season} frozen model snapshot is incomplete for this player."
    return "Frozen prediction membership is currently unavailable."


def _roster_coverage(
    conn: sqlite3.Connection,
    *,
    capture_date: str,
    source: str,
    rostered_sleeper_ids: Iterable[str],
) -> dict[str, int]:
    rostered = {
        str(sleeper_id).strip()
        for sleeper_id in rostered_sleeper_ids
        if str(sleeper_id).strip()
    }
    included = {
        str(row["sleeper_id"])
        for row in conn.execute(_INCLUDED_ROSTER_QUERY, (capture_date, source))
        if row["prediction_ppg_status"] == "captured"
        and _finite_projection(row["projection_2y"])
        and row["sleeper_id"] is not None
    }
    included_count = len(rostered & included)
    return {
        "current_rostered_skill_player_count": len(rostered),
        "current_rostered_skill_in_frozen_prediction_cohort_count": included_count,
        "current_rostered_skill_not_in_frozen_prediction_cohort_count": (
            len(rostered) - included_count
        ),
    }


def resolve_frozen_prediction_membership(
    sleeper_id: str,
    *,
    season: int,
    declaration_path: Path,
    db_path: Path,
    current_rostered_skill_sleeper_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Resolve one player's declared frozen-prediction membership, fail closed."""
    declaration = _load_declaration(Path(declaration_path), season)
    if declaration is None:
        return _unavailable(season=season, capture_date=None)
    capture_date, source = declaration

    if not Path(db_path).is_file():
        return _unavailable(season=season, capture_date=capture_date)

    try:
        uri = f"file:{Path(db_path).resolve().as_posix()}?mode=ro"
        # closing(), not the bare connection context: `with conn` only ends the
        # transaction and leaks the handle until GC (same idiom as the scorer).
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                _MEMBERSHIP_QUERY, (capture_date, source, str(sleeper_id))
            ).fetchall()
            coverage = _roster_coverage(
                conn,
                capture_date=capture_date,
                source=source,
                rostered_sleeper_ids=current_rostered_skill_sleeper_ids,
            )
    except (OSError, sqlite3.DatabaseError):
        return _unavailable(season=season, capture_date=capture_date)

    if not rows:
        status, basis = (
            "not_in_frozen_prediction_cohort",
            "not_present_in_frozen_universe",
        )
    else:
        classifications = {_classify_row(row) for row in rows}
        if len(classifications) != 1:
            return _unavailable(season=season, capture_date=capture_date)
        status, basis = classifications.pop()

    return {
        "season": season,
        "frozen_capture_date": capture_date,
        "status": status,
        "basis": basis,
        "message": _message(status, season),
        "coverage": coverage,
        "decision_supported": False,
    }
