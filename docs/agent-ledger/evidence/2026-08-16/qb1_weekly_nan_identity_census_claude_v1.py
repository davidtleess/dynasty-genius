"""Read-only census of unusable-identity rows in the ADMITTED weekly pool.

Measures how many rows of the pinned QB-1 weekly input carry a null/NaN
player_id, by season, plus what those rows contain. Mutates nothing.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
WEEKLY = REPO_ROOT / "app/data/backtest/qb_validation/raw/weekly"


def main() -> int:
    frames = sorted(WEEKLY.rglob("*.parquet"))
    print(f"weekly parquet files: {len(frames)}")
    total_rows = 0
    total_bad = 0
    for path in frames:
        frame = pd.read_parquet(path)
        bad = frame[frame["player_id"].isna()]
        total_rows += len(frame)
        total_bad += len(bad)
        if len(bad):
            by_season = bad.groupby("season").size().to_dict()
            print(f"{path.name}: rows={len(frame)} nan_player_id={len(bad)} by_season={by_season}")
            sample = bad.head(3)
            keep = [
                column
                for column in (
                    "player_id",
                    "player_name",
                    "player_display_name",
                    "season",
                    "week",
                    "position",
                    "team",
                    "recent_team",
                )
                if column in sample.columns
            ]
            print(sample[keep].to_string())
    print(f"TOTAL rows={total_rows} nan_player_id={total_bad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
