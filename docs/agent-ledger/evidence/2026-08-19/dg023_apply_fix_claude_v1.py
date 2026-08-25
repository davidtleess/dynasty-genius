"""DG-023 — apply the stream-provenance status fix to the ticket worktree.

Anchored, idempotent-checked patch: each anchor must match exactly once or the
script refuses. Recorded as evidence so the change is reproducible rather than
hand-applied.
"""

from __future__ import annotations

import sys
from pathlib import Path

TARGET = Path("/Users/davidleess/dg-wt/DG-023/scripts/run_feature_refresh.py")

OLD_1 = '''        status = "loaded" if seasons_present is not None else "loaded_empty"
        return frame, {
            "status": status,
            "effective_season": seasons_present,
            "fallback_used": attempts_made > 1,'''

NEW_1 = '''        # DG-023: `status` is a fact about ROWS; `effective_season` is a fact about
        # the SEASON COLUMN. Deriving the first from the second fused two independent
        # questions, so `participation` -- which loads tens of thousands of rows and
        # carries no `season` column at all -- was reported `loaded_empty`, and
        # /api/health rendered that as "EMPTY: participation" over good data.
        # Measured 2026-08-19: the features participation feeds
        # (route_participation / tprr / yprr) are each populated 498/505 in the
        # inference season. A health signal that cries wolf on good data is worse
        # than none, because a real failure looks identical.
        row_count = int(len(frame))
        status = "loaded" if row_count else "loaded_empty"
        return frame, {
            "status": status,
            "effective_season": seasons_present,
            # Recorded so a reader can tell an UNOBSERVABLE season from a genuinely
            # empty load. Without it the artifact cannot distinguish the two, which
            # is precisely why the false label stood unexamined for eleven days.
            "row_count": row_count,
            "fallback_used": attempts_made > 1,'''

OLD_2 = '''    return pd.DataFrame(), {
        "status": "unavailable",
        "effective_season": None,
        "fallback_used": attempts_made > 1,
        "error_type": error_type,
    }'''

NEW_2 = '''    return pd.DataFrame(), {
        "status": "unavailable",
        "effective_season": None,
        # A stream that never loaded has NO row count. Zero would assert a
        # successful empty read, which is a different fact.
        "row_count": None,
        "fallback_used": attempts_made > 1,
        "error_type": error_type,
    }'''


def main() -> int:
    source = TARGET.read_text()
    for label, anchor in (("status-derivation", OLD_1), ("unavailable-branch", OLD_2)):
        hits = source.count(anchor)
        if hits != 1:
            print(f"REFUSED: anchor {label!r} matched {hits} times, expected 1")
            return 1
    patched = source.replace(OLD_1, NEW_1).replace(OLD_2, NEW_2)
    TARGET.write_text(patched)
    print(f"patched {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
