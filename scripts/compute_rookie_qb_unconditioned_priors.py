"""Rookie-QB unconditioned prior table producer (recalibration v2).

Computes TRUE unconditioned draft-class survival per the ratified spec
docs/superpowers/specs/2026-07-04-rookie-filter-prior-recalibration-design.md:
cohort = ALL rookie QB entrants in rosters (missing draft slot = undrafted);
outcome@H = the role-occupancy predicate evaluated DIRECTLY at season
entry_year+H from role rows — never a label-table join, which would
reintroduce the feature-floor conditioning this build removes (a
sit-then-start QB is H1-negative and later-horizon-positive on merit).
Never-appeared seasons are honest negatives, counted only in horizons whose
outcome window is observable. Gemini's pre-registered prediction ranges are
scored as a REPORT-ONLY diagnostic — misses are findings, never adjustments.

Run: .venv/bin/python3.14 scripts/compute_rookie_qb_unconditioned_priors.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = REPO_ROOT / "app" / "config" / "rookie_qb_prior_table_v2.json"

CAPITAL_BANDS = ("round_1_picks_1_32", "round_2_picks_33_64", "day3_picks_65_plus", "undrafted")
GAMES_THRESHOLD = 8
SNAP_SHARE_THRESHOLD = 0.50

# Spec §0 pre-registered prediction ranges (Gemini, recorded before any
# computation) — the DEFAULT scorecard carried by every artifact; misses are
# findings, never adjustments.
PRE_REGISTERED_PREDICTION_RANGES: dict[tuple[str, int], tuple[float, float]] = {
    ("round_1_picks_1_32", 1): (0.80, 0.88),
    ("round_2_picks_33_64", 1): (0.45, 0.50),
    ("day3_picks_65_plus", 2): (0.05, 0.08),
    ("undrafted", 1): (0.01, 0.02),
}


def _capital_band(draft_number: object) -> str:
    if pd.isna(draft_number):
        return "undrafted"
    slot = int(draft_number)
    if slot <= 32:
        return "round_1_picks_1_32"
    if slot <= 64:
        return "round_2_picks_33_64"
    return "day3_picks_65_plus"


def compute_rookie_qb_unconditioned_priors(
    *,
    rosters: pd.DataFrame,
    role_rows: pd.DataFrame,
    generated_at: str,
    generation_command: str,
    machinery_repo_sha: str,
    source_caveat: str,
    cohort_entry_years: tuple[int, ...],
    horizons: tuple[int, ...] = (1, 2, 3),
    prediction_ranges: dict[tuple[str, int], tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Build the v2 band-by-horizon unconditioned prior artifact (pure; no I/O)."""
    if prediction_ranges is None:
        prediction_ranges = PRE_REGISTERED_PREDICTION_RANGES
    qb_rosters = rosters[
        (rosters["position"] == "QB") & (rosters["entry_year"].isin(list(cohort_entry_years)))
    ]

    quarantined: list[dict[str, Any]] = []
    members: dict[str, dict[str, Any]] = {}
    for row in qb_rosters.itertuples(index=False):
        if row.player_id is None or pd.isna(row.player_id):
            quarantined.append({"player_id": None, "reason": "identity_unresolved"})
            continue
        draft_number = None if pd.isna(row.draft_number) else int(row.draft_number)
        existing = members.get(row.player_id)
        if existing is None:
            members[row.player_id] = {
                "entry_year": int(row.entry_year),
                "draft_number": draft_number,
            }
            continue
        # Real-source semantics (probe 2026-07-04: 8/138 QBs carry the slot in
        # one roster season and NA in another; ZERO distinct-number conflicts):
        # NA is sparsity and coalesces to the known number — only DISTINCT
        # non-NA numbers or entry_year mismatches are true conflicts.
        if existing["entry_year"] != int(row.entry_year) or (
            existing["draft_number"] is not None
            and draft_number is not None
            and existing["draft_number"] != draft_number
        ):
            raise ValueError(
                f"conflicting rookie draft metadata for {row.player_id!r}: "
                f"{existing} vs entry_year={int(row.entry_year)}, "
                f"draft_number={draft_number}"
            )
        if existing["draft_number"] is None and draft_number is not None:
            existing["draft_number"] = draft_number

    qb_roles = role_rows[role_rows["position"] == "QB"] if len(role_rows) else role_rows
    role_lookup = {
        (row.player_id, int(row.season)): row for row in qb_roles.itertuples(index=False)
    }
    seasons = [int(row.season) for row in qb_roles.itertuples(index=False)]
    if not seasons:
        # Fail closed: no role data means NO observable horizon — fabricating
        # a window from cohort years would count everyone negative (Codex T1
        # amendment): refuse instead.
        raise ValueError("role source is empty: no QB seasons — observability window unavailable")
    max_available_role_season = max(seasons)

    cells: dict[tuple[str, int], dict[str, Any]] = {
        (band, int(horizon)): {
            "n": 0,
            "positives": 0,
            "basis": {"games_and_snap": 0, "games_only": 0, "absent_role_row": 0},
        }
        for band in CAPITAL_BANDS
        for horizon in horizons
    }
    structural_exclusions: list[dict[str, Any]] = []

    for player_id, member in sorted(members.items()):
        band = _capital_band(member["draft_number"])
        for horizon in horizons:
            target_season = member["entry_year"] + int(horizon)
            if target_season > max_available_role_season:
                structural_exclusions.append(
                    {
                        "player_id": player_id,
                        "entry_year": member["entry_year"],
                        "horizon": int(horizon),
                        "target_season": target_season,
                        "reason": "target_season_unavailable",
                    }
                )
                continue
            cell = cells[(band, int(horizon))]
            cell["n"] += 1
            role = role_lookup.get((player_id, target_season))
            if role is None:
                cell["basis"]["absent_role_row"] += 1
            elif pd.isna(role.snap_share):
                cell["basis"]["games_only"] += 1
                if int(role.games) >= GAMES_THRESHOLD:
                    cell["positives"] += 1
            else:
                cell["basis"]["games_and_snap"] += 1
                if (
                    int(role.games) >= GAMES_THRESHOLD
                    and float(role.snap_share) >= SNAP_SHARE_THRESHOLD
                ):
                    cell["positives"] += 1

    rows = [
        {
            "capital_band": band,
            "horizon": int(horizon),
            "n": cell["n"],
            "positives": cell["positives"],
            "rate": (cell["positives"] / cell["n"]) if cell["n"] else None,
            "basis": cell["basis"],
        }
        for (band, horizon), cell in cells.items()
    ]

    checks: list[dict[str, Any]] = []
    for (band, horizon), (low, high) in prediction_ranges.items():
        match = next(
            (r for r in rows if r["capital_band"] == band and r["horizon"] == int(horizon)),
            None,
        )
        actual = match["rate"] if match else None
        if actual is None:
            status = "uncomputable_empty_cell"
        elif low <= actual <= high:
            status = "within_pre_registered_range"
        else:
            status = "outside_pre_registered_range"
        checks.append(
            {
                "capital_band": band,
                "horizon": int(horizon),
                "pre_registered_range": [low, high],
                "actual_rate": actual,
                "status": status,
            }
        )

    return {
        "metadata": {
            "config_version": 2,
            "generated_at": generated_at,
            "generation_command": generation_command,
            "machinery_repo_sha": machinery_repo_sha,
            "source_caveat": source_caveat,
            "cohort_entry_years": [int(year) for year in cohort_entry_years],
            "max_available_role_season": max_available_role_season,
            "decision_supported": False,
        },
        "rows": rows,
        "diagnostics": {
            "structural_exclusions": structural_exclusions,
            "quarantined_entries": quarantined,
        },
        # Report-only by construction (spec seed 7): never a gate, never an
        # input to the rates themselves.
        "prediction_check": {"status": "report_only", "gating": False, "checks": checks},
        "decision_supported": False,
    }


def validate_rookie_qb_prior_table(artifact: dict[str, Any]) -> None:
    """Fail-closed table contract (spec seeds 5/6 and the zero-denominator rule).

    The H1 rule guards the FILTER's consumption path: EVERY capital band's H1
    row must carry real data (n > 0) — the filter can be asked about any band,
    so a single empty H1 band means it would consume a null. Refused.
    """
    h1_rows = [row for row in artifact["rows"] if int(row["horizon"]) == 1]
    if h1_rows and any(row["n"] == 0 for row in h1_rows):
        empty = [row["capital_band"] for row in h1_rows if row["n"] == 0]
        raise ValueError(
            f"runtime-consumed H1 rows require n > 0 across all capital bands; empty: {empty}"
        )
    seen: set[tuple[str, int]] = set()
    for row in artifact["rows"]:
        key = (row["capital_band"], int(row["horizon"]))
        if key in seen:
            raise ValueError(f"duplicate (capital_band, horizon) cell: {key}")
        seen.add(key)
        if row["positives"] > row["n"]:
            raise ValueError(f"positives exceed n in cell {key}")
        if row["n"] == 0 and row["rate"] is not None:
            raise ValueError(f"empty cell {key} must carry rate null, never a number")



def write_rookie_qb_prior_table(artifact: dict[str, Any], path: Path = TABLE_PATH) -> None:
    """Explicit write step — computing never writes (no auto-regeneration)."""
    validate_rookie_qb_prior_table(artifact)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, default=str) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-out", type=Path, default=TABLE_PATH)
    args = parser.parse_args()

    import datetime
    import subprocess

    import nflreadpy  # local import: committed tests never require the network

    from scripts.generate_qb_role_occupancy_labels import (
        SOURCE_SEASONS,
        _load_source_frames,
        aggregate_qb_role_source,
    )

    rosters_raw = nflreadpy.load_rosters(list(SOURCE_SEASONS)).to_pandas()
    rosters = rosters_raw[["gsis_id", "season", "position", "entry_year", "draft_number"]].rename(
        columns={"gsis_id": "player_id"}
    )
    player_stats, snap_counts = _load_source_frames()
    role_rows = aggregate_qb_role_source(player_stats=player_stats, snap_counts=snap_counts)

    artifact = compute_rookie_qb_unconditioned_priors(
        rosters=rosters,
        role_rows=role_rows,
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        generation_command=".venv/bin/python3.14 scripts/compute_rookie_qb_unconditioned_priors.py",
        machinery_repo_sha=subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        source_caveat=(
            "nflreadpy rosters/stats/snaps snapshot as of generation date; cohort covers "
            "QBs who received a roster entry — a camp-cut draftee appears via the draft-year "
            "roster; 2025-season data may still shift."
        ),
        cohort_entry_years=(2018, 2019, 2020, 2021, 2022, 2023),
    )
    write_rookie_qb_prior_table(artifact, args.table_out)
    print(f"table -> {args.table_out}")
    for row in artifact["rows"]:
        if row["horizon"] == 1 or row["rate"] is not None:
            print(
                f"  {row['capital_band']} H{row['horizon']}: {row['positives']}/{row['n']}"
                f" = {row['rate'] if row['rate'] is None else round(row['rate'], 3)}"
            )
    for check in artifact["prediction_check"]["checks"]:
        print(f"  prediction {check['capital_band']} H{check['horizon']}: {check['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
