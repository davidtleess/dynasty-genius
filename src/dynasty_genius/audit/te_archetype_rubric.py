"""Phase 13.3.1 Step 0 TE archetype rubric.

The rubric is diagnostic only. It classifies already-parsed PFF alignment rows
for review artifacts and must not be used as an Engine A/B training feature in
Phase 13.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RUBRIC_VERSION = "0.1.0"
DEFAULT_RECEIVING_THRESHOLD = 0.40
SENSITIVITY_RECEIVING_THRESHOLD = 0.45
BLOCKING_INLINE_THRESHOLD = 0.70
MIN_ALIGNMENT_SNAPS = 100.0
ELITE_YPRR_ANCHOR = 1.80


@dataclass(frozen=True)
class TEArchetypeInput:
    player_id: str
    draft_year: int
    selected_season: int | None
    source_row_hash: str | None
    inline_snaps: float | None
    slot_snaps: float | None
    wide_snaps: float | None
    routes: float | None
    targets: float | None
    receptions: float | None
    yards: float | None


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _safe_float(value: float | None) -> float:
    return float(value or 0.0)


def classify_te_archetype(
    row: TEArchetypeInput,
    *,
    receiving_threshold: float = DEFAULT_RECEIVING_THRESHOLD,
) -> dict[str, Any]:
    """Classify one TE row from snap-alignment fields."""

    inline = _safe_float(row.inline_snaps)
    slot = _safe_float(row.slot_snaps)
    wide = _safe_float(row.wide_snaps)
    total = inline + slot + wide

    base = {
        "player_id": row.player_id,
        "draft_year": row.draft_year,
        "selected_season": row.selected_season,
        "coverage_status": "pff_alignment_available",
        "source_row_hash": row.source_row_hash,
        "alignment_snap_total": _round(total),
        "routes": _round(row.routes),
        "targets": _round(row.targets),
        "receptions": _round(row.receptions),
        "yards": _round(row.yards),
        "alignment_source": "snaps_fallback",
        "threshold_basis": "snap_counts",
    }

    if total <= 0:
        return {
            **base,
            "labeling_status": "invalid_alignment",
            "archetype": None,
            "detached_rate_from_snaps": None,
            "inline_rate_from_snaps": None,
            "yprr_computed": None,
            "tprr_computed": None,
            "elite_efficiency_prior": False,
            "near_volume_threshold": False,
        }

    detached_rate = (slot + wide) / total
    inline_rate = inline / total
    routes = _safe_float(row.routes)
    targets = _safe_float(row.targets)
    yards = _safe_float(row.yards)
    yprr = yards / routes if routes > 0 else None
    tprr = targets / routes if routes > 0 else None

    if total < MIN_ALIGNMENT_SNAPS:
        status = "low_volume"
        archetype = None
    elif detached_rate >= receiving_threshold:
        status = "labeled"
        archetype = "receiving_leaning"
    elif inline_rate >= BLOCKING_INLINE_THRESHOLD:
        status = "labeled"
        archetype = "blocking_leaning"
    else:
        status = "labeled"
        archetype = "ambiguous"

    return {
        **base,
        "labeling_status": status,
        "archetype": archetype,
        "detached_rate_from_snaps": _round(detached_rate),
        "inline_rate_from_snaps": _round(inline_rate),
        "yprr_computed": _round(yprr),
        "tprr_computed": _round(tprr),
        "elite_efficiency_prior": bool(yprr is not None and yprr >= ELITE_YPRR_ANCHOR),
        "near_volume_threshold": 80.0 <= total <= 120.0,
    }
