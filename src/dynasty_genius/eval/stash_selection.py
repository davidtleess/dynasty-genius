"""DG-177 stash-selection evaluation: can the frozen future-production ordering find later contributors
among low-production developmental candidates? Frozen inputs only; definitions frozen before any result."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class StashSelectionError(ValueError):
    """A definitions, source or chronology condition under which the evaluator refuses."""


DEFINITIONS_VERSION = "stash_selection_definitions_v1"
REQUIRED_DEFINITION_KEYS = ("version", "frozen_before_first_result", "origins", "low_production", "developmental",
                            "outcome", "orderings", "metrics", "claims_not_made")


def load_definitions(path: Path) -> dict:
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    missing = [k for k in REQUIRED_DEFINITION_KEYS if k not in d]
    if missing:
        raise StashSelectionError(f"definitions file lacks {missing}")
    if d.get("version") != DEFINITIONS_VERSION or d.get("frozen_before_first_result") is not True:
        raise StashSelectionError("definitions must be the frozen v1 file")
    d["_file"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return d
