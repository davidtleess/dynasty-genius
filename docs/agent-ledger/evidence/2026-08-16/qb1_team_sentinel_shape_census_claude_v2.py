"""R13 census v2: the EXACT name-field shapes of missing-id rows, REG only.

The v1 census sampled 2015 rows (player_name="Team") and the real-surface
probe then measured that only 10 of 192 REG missing-id rows match that name —
so the provider shape is heterogeneous across seasons. This measures every
(player_name, player_display_name, position) shape, by season. Read-only.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
WEEKLY = REPO_ROOT / "app/data/backtest/qb_validation/raw/weekly"


def _norm(value: object) -> object:
    if value is None:
        return "<None>"
    if isinstance(value, float) and value != value:
        return "<NaN>"
    return repr(value)


def main() -> int:
    frame = pd.read_parquet(sorted(WEEKLY.rglob("*.parquet"))[0])
    reg = frame[frame["season_type"] == "REG"]
    bad = reg[reg["player_id"].isna()]
    print(f"REG rows: {len(reg)}; REG missing-id rows: {len(bad)}")
    name_columns = [
        column
        for column in ("player_name", "player_display_name", "position", "team")
        if column in bad.columns
    ]
    shapes: dict[tuple, int] = {}
    seasons: dict[tuple, set[int]] = {}
    for _, row in bad.iterrows():
        key = tuple(_norm(row[column]) for column in name_columns[:3])
        shapes[key] = shapes.get(key, 0) + 1
        seasons.setdefault(key, set()).add(int(row["season"]))
    print(f"shape key = ({', '.join(name_columns[:3])})")
    for key, count in sorted(shapes.items(), key=lambda item: -item[1]):
        span = seasons[key]
        print(f"  {key}: n={count} seasons={min(span)}-{max(span)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
