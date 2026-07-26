"""Read-only reproduction for Studio 009 relay addendum.

This analysis depends on three frozen inputs that are intentionally not stored in
this repository: Studio's board fixture and two gitignored league-runtime
artifacts. Paths are overridable so another machine can supply exact copies.
Each input is hash-checked before analysis.
"""

import argparse
import hashlib
import json
from pathlib import Path

from scipy.stats import pearsonr, rankdata

DG_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STUDIO_BOARD = (
    DG_ROOT.parent
    / "frontend-studio/proposals/009-who-holds-what/board-data.js"
)
DEFAULT_MATRIX = (
    DG_ROOT
    / "app/data/league_runtime/runs/league-20260724T132000Z/team_value_matrix.json"
)
DEFAULT_SNAPSHOT = (
    DG_ROOT
    / "app/data/league_runtime/runs/league-20260724T132000Z/snapshot.json"
)
EXPECTED_SHA256 = {
    "studio_board": "ce81294d0795676b846caeae57ec7584327135a4032d2217a110111199a36392",
    "matrix": "76e79f875848c223b103cba4990bc1637f603b9670ce10b7e35225bd77bd5986",
    "snapshot": "41dc8d50d2539ebd342605739ba7aebc9eb8d11961b8f820c08fc45edac7119b",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studio-board", type=Path, default=DEFAULT_STUDIO_BOARD)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    return parser.parse_args()


def verify_input(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(
            f"{label} input is not in this clone; supply its path explicitly: {path}"
        )
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = EXPECTED_SHA256[label]
    if actual != expected:
        raise SystemExit(
            f"{label} SHA-256 mismatch: expected {expected}, received {actual}"
        )
    return path


def load_js_object(path: Path) -> dict:
    text = path.read_text()
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def rank_gap_correlation(rows: list[dict], model_field: str) -> float:
    ages: list[float] = []
    gaps: list[float] = []
    for position in ("QB", "RB", "WR", "TE"):
        cohort = [row for row in rows if row["position"] == position]
        market_rank = rankdata([-row["market_value"] for row in cohort])
        model_rank = rankdata([-row[model_field] for row in cohort])
        for row, market, model in zip(
            cohort, market_rank, model_rank, strict=True
        ):
            ages.append(row["age"])
            gaps.append(float(market - model))
    return float(pearsonr(ages, gaps).statistic)


args = parse_args()
studio_board = verify_input(args.studio_board, "studio_board")
matrix_path = verify_input(args.matrix, "matrix")
snapshot_path = verify_input(args.snapshot, "snapshot")

board = load_js_object(studio_board)
matrix = json.loads(matrix_path.read_text())
snapshot = json.loads(snapshot_path.read_text())

matrix_by_name = {
    player["full_name"]: player
    for team in matrix["teams"]
    for player in team["players"]
    if player.get("full_name")
}
snapshot_by_name = {
    row["player"]["full_name"]: row
    for row in snapshot["players"]
    if row.get("player", {}).get("full_name")
}

market_rows: list[dict] = []
dvs_rows: list[dict] = []
for position, position_board in board["boards"].items():
    for team in position_board["teams"]:
        for item in team["items"]:
            row = {
                "name": item["nm"],
                "position": position,
                "age": float(item["age"]),
                "market_value": float(item["v"]),
                "xvar": float(matrix_by_name[item["nm"]]["raw_xvar"]),
                "dvs": float(item["dvs"]),
                "state": "valued",
            }
            market_rows.append(row)
            dvs_rows.append(row)
        for item in team["off"]:
            if item["v"] is None:
                continue
            market_rows.append(
                {
                    "name": item["nm"],
                    "position": position,
                    "age": float(
                        snapshot_by_name[item["nm"]]["player"]["age"]
                    ),
                    "market_value": float(item["v"]),
                    "xvar": float(matrix_by_name[item["nm"]]["raw_xvar"]),
                    "state": item["state"],
                }
            )

active_null = [row for row in market_rows if row["state"] == "nullvalue"]
pre_model_null = [row for row in market_rows if row["state"] == "nomodel"]
without_active = [
    row for row in market_rows if row["state"] != "nullvalue"
]
without_any_null = [row for row in market_rows if row["state"] == "valued"]

# DVS ranks are already frozen in board-data.js as mr/dr. Reconstruct directly
# so this check does not depend on a later model or market file.
dvs_ages: list[float] = []
dvs_gaps: list[float] = []
for position_board in board["boards"].values():
    for team in position_board["teams"]:
        for item in team["items"]:
            dvs_ages.append(float(item["age"]))
            dvs_gaps.append(float(item["mr"] - item["dr"]))

print(
    json.dumps(
        {
            "market_priced_n": len(market_rows),
            "dvs_n": len(dvs_rows),
            "active_b_null_n": len(active_null),
            "pre_model_null_n": len(pre_model_null),
            "xvar_zero_included_r": rank_gap_correlation(
                market_rows, "xvar"
            ),
            "xvar_drop_active_b_only_r": rank_gap_correlation(
                without_active, "xvar"
            ),
            "xvar_drop_all_null_r": rank_gap_correlation(
                without_any_null, "xvar"
            ),
            "dvs_frozen_rank_gap_r": float(
                pearsonr(dvs_ages, dvs_gaps).statistic
            ),
            "active_b_names": [row["name"] for row in active_null],
            "pre_model_names": [row["name"] for row in pre_model_null],
        },
        indent=2,
    )
)
