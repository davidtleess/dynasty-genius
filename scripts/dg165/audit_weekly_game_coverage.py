"""Game-level coverage of the captured weekly source — corroboration for Codex's DG-179 audit.

Distinct week labels are not game coverage: a season can carry 17 week labels and still be
missing games. This reads the immutable capture's raw files and counts distinct game_ids per
(season, season_type) and per week, against the expected regular-season game count for the
league size of the year (31 teams x 16 games / 2 = 248 for 1999-2001; 32 x 16 / 2 = 256 for
2002-2020; 32 x 17 / 2 = 272 from 2021). It writes a NEW run directory and asserts nothing
about completeness; shortfalls are listed for the contract owner to resolve.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402


def expected_reg_games(season: int) -> int:
    teams = 31 if season <= 2001 else 32
    games = 16 if season <= 2020 else 17
    return teams * games // 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", type=Path, required=True)
    ap.add_argument("--runs-root", type=Path, default=REPO / "runs")
    a = ap.parse_args(argv)
    manifest_sha = hashlib.sha256((a.capture / "manifest.json").read_bytes()).hexdigest()
    frames = [pd.read_parquet(p, columns=["season", "week", "season_type", "game_id", "team", "opponent_team"])
              for p in sorted((a.capture / "raw").glob("stats_player_week_*.parquet"))]
    weekly = pd.concat(frames, ignore_index=True)
    per_season = []
    for (season, stype), g in weekly.groupby(["season", "season_type"], sort=True):
        games = g["game_id"].nunique()
        per_week = g.groupby("week")["game_id"].nunique()
        entry = {"season": int(season), "season_type": stype, "distinct_game_ids": int(games),
                 "expected_reg_games": expected_reg_games(int(season)) if stype == "REG" else None,
                 "shortfall": (expected_reg_games(int(season)) - int(games)) if stype == "REG" else None,
                 "weeks": "|".join(f"{int(w)}:{int(n)}" for w, n in per_week.items()),
                 "teams_seen": int(g["team"].nunique())}
        per_season.append(entry)
    table = pd.DataFrame(per_season)
    run_dir = create_run_dir(a.runs_root, name="weekly_source_game_coverage")
    table.to_csv(run_dir / "game_coverage.csv", index=False)
    reg = table.loc[table["season_type"] == "REG"]
    short = reg.loc[reg["shortfall"] != 0, ["season", "distinct_game_ids", "expected_reg_games", "shortfall"]]
    lines = ["# Game-level coverage of the captured weekly source (corroboration, no completeness claim)", "",
             f"Capture: `{a.capture}` (manifest sha256 `{manifest_sha[:12]}…`). Expected REG games = teams × games / 2 for the year.", "",
             "| season | REG distinct game_ids | expected | shortfall | games per week |", "|---|---:|---:|---:|---|"]
    for _, r in reg.iterrows():
        lines.append(f"| {r['season']} | {r['distinct_game_ids']} | {r['expected_reg_games']} | {r['shortfall']} | {r['weeks']} |")
    lines += ["", f"Seasons with a REG shortfall: {len(short)} → " + ", ".join(f"{int(s)}: {int(d)} of {int(e)}" for s, d, e in zip(short['season'], short['distinct_game_ids'], short['expected_reg_games']))]
    (run_dir / "GAME_COVERAGE.md").write_text("\n".join(lines) + "\n")
    (run_dir / "manifest.json").write_text(json.dumps({
        "purpose": "game-level coverage of the weekly source capture; corroboration for the DG-179 source contract; asserts nothing about completeness",
        "capture": str(a.capture), "capture_manifest_sha256": manifest_sha, "computed_at": datetime.now(timezone.utc).isoformat(),
        "expected_rule": "31 teams x 16 games / 2 for 1999-2001; 32 x 16 / 2 for 2002-2020; 32 x 17 / 2 from 2021",
        "reg_shortfalls": short.to_dict("records"),
        "outputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(run_dir.iterdir()) if p.is_file()},
    }, indent=1, default=str))
    print(reg[["season", "distinct_game_ids", "expected_reg_games", "shortfall"]].to_string(index=False))
    print("2001 REG games per week:", reg.loc[reg["season"] == 2001, "weeks"].iloc[0])
    print(f"run dir: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
