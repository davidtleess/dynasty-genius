"""DG-128: capture nflverse draft picks ONCE into the tracked draft-capital snapshot.

The serving batch reads `resources/draft_capital/nflverse_draft_picks.json` offline to hand a
veteran his pick, round and draft-season age — the Engine A prior's inputs. This script is the
only writer of that file. It is NOT a cadence job: draft capital is fixed the day a player is
drafted, so the snapshot changes once a year (the April draft) and lands through git like any
other resource, content-hashed by `src.dynasty_genius.draft_capital`.

Exit codes follow the house convention — 0 wrote a snapshot, 1 anything else. An empty upstream
writes nothing: a blank snapshot would silently un-prior every veteran.

    .venv/bin/python scripts/capture_draft_capital.py            # 2000..current season
    .venv/bin/python scripts/capture_draft_capital.py --seasons 2000 2026
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.draft_capital import (  # noqa: E402
    DRAFT_CAPITAL_SNAPSHOT_PATH,
    build_snapshot,
    write_snapshot,
)

SOURCE = "nflreadpy.load_draft_picks"
# Engine A trained on 2015+ drafts; the snapshot reaches back further so a long-tenured veteran
# (a 2007 pick still on a roster) is drafted, not silently undrafted.
DEFAULT_FIRST_SEASON = 2000


def _fetch_upstream(seasons: list[int]) -> list[dict[str, Any]]:
    """The real fetch: nflreadpy's governed loader, rows as plain dicts."""
    from nflreadpy import load_draft_picks

    return load_draft_picks(seasons=seasons).to_dicts()


def run_capture(
    *,
    output_path: Path,
    seasons: tuple[int, int],
    fetch_fn: Callable[[list[int]], list[dict[str, Any]]] | None = None,
) -> int:
    fetch_fn = fetch_fn or _fetch_upstream
    first, last = seasons
    snapshot = build_snapshot(
        fetch_fn(list(range(first, last + 1))),
        seasons=(first, last),
        pulled_at=datetime.now(UTC).isoformat(),
        source=SOURCE,
    )
    if not snapshot["rows"]:
        print(f"draft_capital: upstream returned no skill-position rows for {first}-{last}; nothing written")
        return 1
    write_snapshot(snapshot, output_path)
    print(
        f"draft_capital: wrote {output_path} rows={len(snapshot['rows'])} "
        f"seasons={first}-{last} sha256={snapshot['content_sha256']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--seasons",
        nargs=2,
        type=int,
        metavar=("FIRST", "LAST"),
        default=(DEFAULT_FIRST_SEASON, datetime.now(UTC).year),
    )
    parser.add_argument("--output", type=Path, default=DRAFT_CAPITAL_SNAPSHOT_PATH)
    args = parser.parse_args(argv)
    return run_capture(output_path=args.output, seasons=tuple(args.seasons))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
