"""Read-only PFR advanced-stats grain and identity census for 2018-2025."""

# ruff: noqa: E402, I001 -- portable repo-root bootstrap precedes project imports.

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import nflreadpy as nr
import polars as pl

from src.dynasty_genius.nflverse_usage import IdentityIndex


def main() -> None:
    identity = IdentityIndex.from_governed_crosswalk()
    seasons = list(range(2018, 2026))
    output: dict[str, object] = {"seasons": seasons, "stat_types": {}}
    total_rows = 0
    total_statuses: Counter[str] = Counter()

    for stat_type in ("pass", "rush", "rec", "def"):
        frame = nr.load_pfr_advstats(seasons=seasons, stat_type=stat_type)
        grouped = frame.group_by(["game_id", "pfr_player_id"]).len()
        statuses = Counter(
            identity.resolve(value, kind="pfr")[1]
            for value in frame["pfr_player_id"]
        )
        total_rows += frame.height
        total_statuses.update(statuses)
        output["stat_types"][stat_type] = {
            "rows": frame.height,
            "duplicate_groups": grouped.filter(pl.col("len") > 1).height,
            "max_group": int(grouped["len"].max()) if grouped.height else 0,
            "null_game_id": int(frame["game_id"].null_count()),
            "null_pfr_player_id": int(frame["pfr_player_id"].null_count()),
            "identity": dict(sorted(statuses.items())),
        }

    output["rows_total"] = total_rows
    output["identity_total"] = dict(sorted(total_statuses.items()))
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
