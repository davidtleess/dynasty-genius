#!/usr/bin/env python3
"""Build a deterministic QB identity bridge to nflreadpy GSIS ids."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.identity import generate_dg_id, normalize_player_name

TRAINING_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
OUTPUT_PATH = ROOT / "resources" / "nflreadpy_qb_id_map.json"
DEFAULT_SEASONS = [2024, 2025, 2026]


def _to_pandas(frame: Any) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    if isinstance(frame, pd.DataFrame):
        return frame.copy()
    if hasattr(frame, "to_pandas"):
        return frame.to_pandas()
    return pd.DataFrame(frame)


def load_rosters(seasons: list[int]):
    import nflreadpy as nfl

    return nfl.load_rosters(seasons)


def _first_existing(row: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _canonical_player_id(row: dict[str, Any]) -> str:
    explicit = _first_existing(row, ["player_id", "dg_id"])
    if explicit:
        return str(explicit)
    name = _first_existing(row, ["pfr_player_name", "full_name", "player_name"])
    return generate_dg_id(str(name), "QB")


def _canonical_qbs_from_training(path: Path = TRAINING_CSV) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    df = df[df["position"] == "QB"].copy()
    rows = []
    for _, row in df.iterrows():
        name = row["pfr_player_name"]
        rows.append(
            {
                "player_id": generate_dg_id(name, "QB"),
                "pfr_player_name": name,
                "position": "QB",
                "season": int(row["season"]),
                "existing_gsis_id": row.get("gsis_id"),
            }
        )
    return rows


def _roster_lookup(rosters: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    if rosters.empty:
        return {}

    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for _, row in rosters.iterrows():
        record = row.to_dict()
        position = str(record.get("position", "")).upper()
        if position != "QB":
            continue
        name = _first_existing(record, ["player_name", "full_name", "pfr_player_name", "display_name"])
        gsis_id = _first_existing(record, ["gsis_id", "player_id"])
        if not name or not gsis_id:
            continue
        key = (normalize_player_name(str(name)), "QB")
        season = _first_existing(record, ["season", "recent_team_season"])
        candidate = {
            "pfr_player_name": str(name),
            "gsis_id": str(gsis_id),
            "season": int(season) if season not in (None, "") else None,
        }
        current = lookup.get(key)
        if current is None or (candidate["season"] or 0) > (current.get("season") or 0):
            lookup[key] = candidate
    return lookup


def build_bridge(
    canonical_qbs: list[dict[str, Any]],
    rosters: Any,
    coverage_threshold: float = 0.80,
    generated_at: str | None = None,
) -> dict[str, Any]:
    roster_df = _to_pandas(rosters)
    lookup = _roster_lookup(roster_df)
    players: dict[str, dict[str, Any]] = {}

    for raw_row in canonical_qbs:
        row = dict(raw_row)
        if str(row.get("position", "")).upper() != "QB":
            continue

        name = _first_existing(row, ["pfr_player_name", "full_name", "player_name"])
        if not name:
            continue
        player_id = _canonical_player_id(row)
        normalized_name = normalize_player_name(str(name))
        match = lookup.get((normalized_name, "QB"))

        existing_gsis_id = _first_existing(row, ["existing_gsis_id", "gsis_id"])
        if match:
            gsis_id = match["gsis_id"]
            season = match.get("season") or row.get("season")
            coverage = "FULL"
            unresolved_reason = None
        elif existing_gsis_id:
            gsis_id = str(existing_gsis_id)
            season = row.get("season")
            coverage = "FULL"
            unresolved_reason = None
        else:
            gsis_id = None
            season = row.get("season")
            coverage = "NONE"
            unresolved_reason = "no_nflreadpy_roster_match"

        players[player_id] = {
            "pfr_player_name": str(name),
            "normalized_name": normalized_name,
            "gsis_id": gsis_id,
            "season": int(season) if season not in (None, "") else None,
            "coverage": coverage,
            "unresolved_reason": unresolved_reason,
        }

    ordered_players = {key: players[key] for key in sorted(players)}
    total = len(ordered_players)
    resolved = sum(1 for player in ordered_players.values() if player["coverage"] != "NONE")
    unresolved = total - resolved
    coverage_pct = round(resolved / total, 4) if total else 0.0

    return {
        "metadata": {
            "source": "nflreadpy_rosters",
            "generated_at": generated_at,
            "coverage_threshold": coverage_threshold,
        },
        "coverage": {
            "total": total,
            "resolved": resolved,
            "unresolved": unresolved,
            "coverage_pct": coverage_pct,
            "threshold_met": coverage_pct >= coverage_threshold,
        },
        "players": ordered_players,
    }


def write_bridge_artifact(bridge: dict[str, Any], output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bridge, indent=2, sort_keys=True) + "\n")


def main() -> None:
    canonical_qbs = _canonical_qbs_from_training()
    rosters = load_rosters(DEFAULT_SEASONS)
    bridge = build_bridge(canonical_qbs, rosters, generated_at=datetime.now(timezone.utc).isoformat())
    write_bridge_artifact(bridge)
    coverage = bridge["coverage"]
    print(
        "Wrote "
        f"{OUTPUT_PATH} with {coverage['resolved']}/{coverage['total']} resolved "
        f"({coverage['coverage_pct']:.1%})."
    )


if __name__ == "__main__":
    main()
