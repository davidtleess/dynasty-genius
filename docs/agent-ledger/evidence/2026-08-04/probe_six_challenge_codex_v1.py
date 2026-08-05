"""Read-only counter-probes for the six-loader framing challenge.

Prints concise JSON to stdout. It does not write source or product data.
"""

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


SEASONS = [2023, 2024, 2025]


def duplicate_summary(frame: pl.DataFrame, keys: list[str]) -> dict[str, object]:
    grouped = frame.group_by(keys).len()
    duplicates = grouped.filter(pl.col("len") > 1)
    return {
        "keys": keys,
        "rows": frame.height,
        "groups": grouped.height,
        "duplicate_groups": duplicates.height,
        "max_group": int(grouped["len"].max()) if grouped.height else 0,
        "nulls": {key: int(frame[key].null_count()) for key in keys},
    }


def exact_duplicate_summary(frame: pl.DataFrame) -> dict[str, int]:
    payloads = [
        json.dumps(row, sort_keys=True, default=str, separators=(",", ":"))
        for row in frame.to_dicts()
    ]
    counts = Counter(payloads)
    return {
        "rows": frame.height,
        "exact_unique_rows": len(counts),
        "exact_duplicate_groups": sum(1 for count in counts.values() if count > 1),
        "exact_duplicate_rows_beyond_first": sum(
            count - 1 for count in counts.values() if count > 1
        ),
        "max_exact_multiplicity": max(counts.values()),
    }


def identity_summary(
    frame: pl.DataFrame, column: str, kind: str, identity: IdentityIndex
) -> dict[str, int]:
    statuses = Counter(identity.resolve(value, kind=kind)[1] for value in frame[column])
    return dict(sorted(statuses.items()))


def main() -> None:
    identity = IdentityIndex.from_governed_crosswalk()
    opportunity = nr.load_ff_opportunity(seasons=SEASONS)
    opportunity_players = opportunity.filter(pl.col("player_id").is_not_null())
    opportunity_aggregates = opportunity.filter(pl.col("player_id").is_null())

    depth = nr.load_depth_charts(seasons=SEASONS)
    depth_old = depth.filter(pl.col("season").is_not_null())
    depth_new = depth.filter(pl.col("season").is_null())

    contracts = nr.load_contracts()
    contract_payloads = [
        json.dumps(row, sort_keys=True, default=str, separators=(",", ":"))
        for row in contracts.to_dicts()
    ]
    contract_counts = Counter(contract_payloads)

    pfr = {}
    for stat_type in ("pass", "rush", "rec", "def"):
        frame = nr.load_pfr_advstats(seasons=SEASONS, stat_type=stat_type)
        pfr[stat_type] = duplicate_summary(frame, ["game_id", "pfr_player_id"])
        pfr[stat_type]["identity"] = identity_summary(
            frame, "pfr_player_id", "pfr", identity
        )

    output = {
        "ff_opportunity": {
            "identity_all_rows": identity_summary(
                opportunity, "player_id", "gsis", identity
            ),
            "identity_player_rows": identity_summary(
                opportunity_players, "player_id", "gsis", identity
            ),
            "all_candidate": duplicate_summary(
                opportunity, ["season", "week", "player_id"]
            ),
            "nonnull_player_candidate": duplicate_summary(
                opportunity_players, ["season", "week", "player_id"]
            ),
            "nonnull_player_game_candidate": duplicate_summary(
                opportunity_players, ["game_id", "player_id"]
            ),
            "null_player_rows": opportunity_aggregates.height,
            "null_player_rows_with_name": int(
                opportunity_aggregates["full_name"].is_not_null().sum()
            ),
            "null_player_rows_with_position": int(
                opportunity_aggregates["position"].is_not_null().sum()
            ),
            "null_player_rows_by_season": opportunity_aggregates.group_by("season")
            .len()
            .sort("season")
            .to_dicts(),
        },
        "depth_charts": {
            "old_identity": identity_summary(depth_old, "gsis_id", "gsis", identity),
            "new_identity": identity_summary(depth_new, "gsis_id", "gsis", identity),
            "old_exact_duplicates": exact_duplicate_summary(depth_old),
            "new_exact_duplicates": exact_duplicate_summary(depth_new),
            "old_candidates": [
                duplicate_summary(
                    depth_old,
                    [
                        "season",
                        "week",
                        "club_code",
                        "gsis_id",
                        "formation",
                        "depth_position",
                    ],
                ),
                duplicate_summary(
                    depth_old,
                    ["season", "week", "club_code", "gsis_id", "formation", "depth_team"],
                ),
            ],
            "new_candidates": [
                duplicate_summary(
                    depth_new,
                    ["dt", "team", "espn_id", "pos_grp", "pos_slot", "pos_rank"],
                ),
                duplicate_summary(
                    depth_new,
                    ["dt", "team", "gsis_id", "pos_grp", "pos_slot", "pos_rank"],
                ),
            ],
            "new_rows_null_gsis": int(depth_new["gsis_id"].null_count()),
            "new_rows_null_espn": int(depth_new["espn_id"].null_count()),
        },
        "contracts": {
            "identity": identity_summary(contracts, "gsis_id", "gsis", identity),
            "rows": contracts.height,
            "exact_unique_rows": len(contract_counts),
            "exact_duplicate_groups": sum(1 for count in contract_counts.values() if count > 1),
            "exact_duplicate_rows_beyond_first": sum(
                count - 1 for count in contract_counts.values() if count > 1
            ),
            "max_exact_multiplicity": max(contract_counts.values()),
            "year_signed_min": int(contracts["year_signed"].min()),
            "year_signed_max": int(contracts["year_signed"].max()),
        },
        "pfr_advstats": pfr,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
