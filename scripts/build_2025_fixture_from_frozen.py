"""S3 Task 10A — Task 3 Step 2: build the provisional 2025 fixture from the frozen stack.

Consumes the committed T3 frozen payloads under ``<output_root>/_frozen_2025/`` and runs
the cleared cohort-truth-driven Task-2 builder (``build_2025_prospect_fixture``, committed
``43d6bc7``) to write ONLY:
- ``<output_root>/2025_fantasy_prospects.json`` (emit-ready identity rows), and
- ``<output_root>/2025_review_queue.json`` (missing/ambiguous/unresolved/malformed rows).

BUILD ONLY. This does NOT re-freeze sources, call live APIs, or mint registry/bridge
records — that is plan-Task-4 (``ingest_college_prospect_fixture.py``), a separate gated
step after David reviews the review/block queue (plan Task 3 Step 3).

Usage:
    .venv/bin/python3.14 scripts/build_2025_fixture_from_frozen.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

# Curated CFBD<->nflverse school-name normalization (lowercase keys). The builder applies
# these before matching; unmatched picks fall to the review queue for David's adjudication,
# so this map need not be exhaustive.
SCHOOL_ALIASES: dict[str, str] = {
    "ole miss": "mississippi",
    "nc state": "north carolina state",
    "usc": "southern california",
    "pitt": "pittsburgh",
    "cal": "california",
    "penn st.": "penn state",
    "ohio st.": "ohio state",
    "michigan st.": "michigan state",
    "mississippi st.": "mississippi state",
    "iowa st.": "iowa state",
    "kansas st.": "kansas state",
    "oklahoma st.": "oklahoma state",
    "washington st.": "washington state",
    "colorado st.": "colorado state",
    "oregon st.": "oregon state",
    "arizona st.": "arizona state",
    "florida st.": "florida state",
    "appalachian st.": "appalachian state",
    "boise st.": "boise state",
    "montana st.": "montana state",
    "north dakota st.": "north dakota state",
    "utah st.": "utah state",
    "miami (fl)": "miami",
    "central florida": "ucf",
}

# Frozen-file name <-> frozen_inputs dict key (the keys build_2025_prospect_fixture expects).
# `cfbd_roster` is NOT here: its artifact is roster_year-qualified (`cfbd_roster_{roster_year}.json`,
# e.g. cfbd_roster_2024.json per spec §2 year decoupling), so it is derived by glob, not a fixed name.
_FROZEN_FILES: dict[str, str] = {
    "nflverse_draft_picks": "nflverse_draft_picks_2025_pin.json",
    "ff_playerids": "ff_playerids_pin.json",
    "udfa_sources": "udfa_sources_manifest.json",
    "manifest": "manifest.json",
}


def _default_builder() -> Callable:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.dynasty_genius.identity.build_2025_prospect_fixture import (
        build_2025_prospect_fixture,
    )

    return build_2025_prospect_fixture


def build_2025_fixture_from_frozen(
    *,
    output_root: Path,
    builder: Callable | None = None,
    print_summary: bool = True,
) -> dict:
    """Load ``_frozen_2025/`` -> run the Task-2 builder -> write fixture + review queue.

    Returns a bounded summary dict. Fail-closed: a missing required frozen file raises
    ``FileNotFoundError`` (naming the file) BEFORE any output is written.
    """
    output_root = Path(output_root)
    frozen_dir = output_root / "_frozen_2025"

    # Load ALL frozen inputs first (a missing file raises here, before any write).
    frozen_inputs: dict[str, Any] = {}
    # cfbd_roster: roster_year-qualified artifact (cfbd_roster_{roster_year}.json) — derived by
    # glob, not a hardcoded year (spec §2 year decoupling; the registry/draft year stays 2025).
    roster_matches = sorted(frozen_dir.glob("cfbd_roster_*.json"))
    if not roster_matches:
        raise FileNotFoundError(
            f"required frozen input missing: {frozen_dir / 'cfbd_roster_*.json'}"
        )
    if len(roster_matches) > 1:
        raise ValueError(
            f"ambiguous CFBD roster artifacts in {frozen_dir}: "
            f"{[p.name for p in roster_matches]}"
        )
    frozen_inputs["cfbd_roster"] = json.loads(roster_matches[0].read_text(encoding="utf-8"))
    for key, filename in _FROZEN_FILES.items():
        path = frozen_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"required frozen input missing: {path}")
        frozen_inputs[key] = json.loads(path.read_text(encoding="utf-8"))

    build = builder or _default_builder()
    rows, review_queue = build(frozen_inputs, school_aliases=SCHOOL_ALIASES)

    (output_root / "2025_fantasy_prospects.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    (output_root / "2025_review_queue.json").write_text(
        json.dumps(review_queue, indent=2), encoding="utf-8"
    )

    review_reasons = dict(Counter(r.get("reason") for r in review_queue))
    summary = {
        "emitted_rows": len(rows),
        "review_queue_rows": len(review_queue),
        "review_reasons": review_reasons,
    }

    if print_summary:
        print(
            "T4 fixture build complete -> 2025_fantasy_prospects.json + 2025_review_queue.json"
        )
        print(
            f"  emitted_rows={summary['emitted_rows']} "
            f"review_queue_rows={summary['review_queue_rows']}"
        )
        for reason, count in review_reasons.items():
            print(f"  {reason}={count}")
    return summary


def main(argv: list[str] | None = None) -> int:
    build_2025_fixture_from_frozen(
        output_root=Path("resources/prospect_fixtures"),
        print_summary=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
