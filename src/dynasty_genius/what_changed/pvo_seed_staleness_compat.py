"""Compatibility shim for stale PVO seed-staleness ready-markers.

The What-Changed §3.6 model-promotion tripwire renamed its directive-shaped marker fields to
descriptive threshold-crossing names (the marker states a FACT — a drift threshold was crossed
— not an action to take). The runtime ready-marker
(``app/data/valuation_runtime/universe_pvo_runtime.ready.json``) is gitignored, so an OLD marker
can persist across a deploy until the next ``run_pvo_refresh``. This module is the sole, tracked
home for the two legacy field-name literals — housed OUTSIDE the No-Verdict cordon's scanned
surfaces (mirroring ``league_pulse_v1_compat``) so the consumer (``what_changed/report.py``)
stays cordon-clean while still reading legacy marker state. Kept indefinitely: it is tiny and
prevents What-Changed from degrading on a legacy gitignored marker.
"""
from __future__ import annotations

from typing import Any

# The two legacy marker field names, renamed to the descriptive forms. Housed here (not in the
# scanned consumer) so the cordon never flags the consumer for reading legacy state.
_LEGACY_TO_DESCRIPTIVE = {
    "promote_recommended": "promotion_review_threshold_crossed",
    "recommendation_reasons": "review_triggers",
}


def normalize_seed_staleness(block: Any) -> Any:
    """Return ``block`` with any legacy marker field names renamed to their descriptive forms.

    All other fields pass through unchanged; a marker already on the new names is returned as-is
    (the new name wins if both are somehow present). Non-dict input passes through untouched.
    """
    if not isinstance(block, dict):
        return block
    normalized = dict(block)
    for legacy_name, descriptive_name in _LEGACY_TO_DESCRIPTIVE.items():
        if legacy_name in normalized:
            normalized.setdefault(descriptive_name, normalized.pop(legacy_name))
    return normalized
