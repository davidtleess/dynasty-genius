"""R13 probe v3: WHAT the three missing-id shapes actually contain (REG only).

Read-only. For each shape (anonymous / "Team" / "R.Rodgers"): stat magnitudes
vs the per-team-week sums of identified player rows, to evidence whether a
shape is a team-level aggregate (out-of-cohort by registration §3/§4) or an
unresolvable PLAYER row (fail-closed territory).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[4]
WEEKLY = REPO_ROOT / "app/data/backtest/qb_validation/raw/weekly"

STATS = [
    "attempts",
    "passing_yards",
    "passing_tds",
    "carries",
    "rushing_yards",
    "rushing_tds",
    "receptions",
    "receiving_yards",
    "sack_fumbles_lost",
    "rushing_fumbles_lost",
    "receiving_fumbles_lost",
]


def main() -> int:
    frame = pd.read_parquet(sorted(WEEKLY.rglob("*.parquet"))[0])
    reg = frame[frame["season_type"] == "REG"]
    bad = reg[reg["player_id"].isna()]
    named = reg[reg["player_id"].notna()]

    anon = bad[bad["player_name"].isna()]
    team_named = bad[bad["player_name"] == "Team"]
    other = bad[bad["player_name"].notna() & (bad["player_name"] != "Team")]

    present = [stat for stat in STATS if stat in frame.columns]
    for label, subset in (
        ("anonymous", anon),
        ("Team-named", team_named),
        ("other-named", other),
    ):
        print(f"== {label}: n={len(subset)}")
        if len(subset) == 0:
            continue
        sums = subset[present].sum(numeric_only=True)
        nonzero = {k: round(float(v), 1) for k, v in sums.items() if v != 0}
        print(f"   nonzero stat totals: {nonzero}")
        sample = subset.head(2)
        for _, row in sample.iterrows():
            row_nonzero = {
                stat: row[stat]
                for stat in present
                if pd.notna(row[stat]) and row[stat] != 0
            }
            print(
                f"   sample: season={row['season']} week={row['week']} "
                f"team={row.get('team')} name={row.get('player_name')!r} "
                f"stats={row_nonzero}"
            )
        # Aggregate check on the first sample: does this row equal the sum of
        # identified player rows for the same team-week?
        first = sample.iloc[0]
        peers = named[
            (named["season"] == first["season"])
            & (named["week"] == first["week"])
            & (named["team"] == first["team"])
        ]
        if len(peers):
            peer_sums = peers[present].sum(numeric_only=True)
            compare = {
                stat: (
                    round(float(first[stat]), 1) if pd.notna(first[stat]) else None,
                    round(float(peer_sums[stat]), 1),
                )
                for stat in ("passing_yards", "rushing_yards", "receiving_yards")
                if stat in present
            }
            print(f"   row-vs-peer-sum (row, sum-of-players): {compare}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
