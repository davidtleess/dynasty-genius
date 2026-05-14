"""Prospect identity resolver — three-stage sleeper_id join for pre-draft prospects.

Stage 1: explicit sleeper_id on the API request (caller override).
Stage 2: alias bridge lookup (human-curated JSON, keyed on normalized_name + position + draft_class).
Stage 3: unresolved — append to review log, return None.

No fuzzy matching. Wrong joins corrupt market overlay data silently, which is
worse than a null overlay. The review log is the correct fallback.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_BRIDGE_FILE = Path("app/data/prospect_alias_bridge.json")
_REVIEW_LOG = Path("app/data/prospect_identity_review.jsonl")

_bridge_cache: dict | None = None
_bridge_lock = threading.Lock()


def normalize_name(name: str) -> str:
    """Lowercase, strip all non-alphanumeric-non-space chars, collapse spaces."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def load_alias_bridge() -> dict:
    """Load and index the alias bridge. Cached after first successful load."""
    global _bridge_cache
    with _bridge_lock:
        if _bridge_cache is None:
            try:
                raw = json.loads(_BRIDGE_FILE.read_text())
                index: dict[tuple[str, str, int], str] = {}
                for entry in raw.get("entries", []):
                    key = (
                        entry["normalized_name"],
                        entry["position"].upper(),
                        int(entry["draft_class"]),
                    )
                    index[key] = entry["sleeper_id"]
                _bridge_cache = index
            except Exception:
                _bridge_cache = {}
    return _bridge_cache


def resolve_prospect_sleeper_id(
    name: str,
    position: str,
    draft_class: int,
    explicit_sleeper_id: Optional[str] = None,
) -> tuple[Optional[str], str]:
    """Return (sleeper_id | None, resolution_method).

    resolution_method:
      "explicit"           — caller supplied sleeper_id directly
      "alias_bridge"       — matched in prospect_alias_bridge.json
      "unresolved_logged"  — no match; review entry written
    """
    # Stage 1: explicit override
    if explicit_sleeper_id:
        return explicit_sleeper_id, "explicit"

    # Stage 2: alias bridge
    norm = normalize_name(name)
    bridge = load_alias_bridge()
    key = (norm, position.upper(), int(draft_class))
    sid = bridge.get(key)
    if sid:
        return sid, "alias_bridge"

    # Stage 3: unresolved — log for human review
    _log_unresolved(name, norm, position, draft_class)
    return None, "unresolved_logged"


def _log_unresolved(
    name: str,
    normalized_name: str,
    position: str,
    draft_class: int,
) -> None:
    try:
        _REVIEW_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "name": name,
            "normalized_name": normalized_name,
            "position": position.upper(),
            "draft_class": int(draft_class),
            "stage_reached": "alias_bridge_miss",
            "sleeper_id_resolved": None,
            "reviewer": None,
        }
        with open(_REVIEW_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # review log failure is non-fatal; overlay stays None
