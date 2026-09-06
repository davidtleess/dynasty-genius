"""Source preparation for the common outcomes (DG-179), to Codex's 2026-09-06 contract.

From the immutable weekly capture this builds, in a NEW immutable run:

* ``identified_weekly.parquet`` — every row of the ADMITTED seasons (2001–2025) that carries a
  player id, all original columns retained, plus the source file hash and row index;
* ``quarantine.parquet`` / ``.csv`` — every admitted-season row WITHOUT a player id, in full,
  with its original season-file row index and raw file hash. Zero-point placeholders are
  counted; the nonzero ones must match, exactly and one-for-one, the records Codex reviewed
  (a research-only exception for those exact rows — NOT a numeric tolerance). Any other
  nonzero unidentified row, or a reviewed one that is absent, fails the preparation;
* a game-coverage check of exact REG game ids against the official nfldata schedule,
  season by season, BEFORE any filtering, with the cancelled 2022 BUF–CIN game excluded
  explicitly (271 completed games) rather than counted as missing or invented;
* ``preparation_manifest.json`` with the required keys, the honest flags
  (``research_qualified`` true, ``individual_stat_completeness_proven`` false), signed AND
  absolute point exclusions per season, the excluded seasons with their missing game ids,
  and the input hashes.

Excluded seasons (1999, 2000 — incomplete game coverage) are not admitted at all: never
zero-labelled, never quarantined here; their rows stay in the raw capture. Negative points
for identified players stay negative. Nothing is invented; nothing is filled.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd

__all__ = [
    "REQUIRED_MANIFEST_KEYS",
    "SCHEDULE_URL",
    "game_coverage",
    "preparation_manifest",
    "split_identified",
    "verify_quarantine",
]

SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
SCHEMA_VERSION = "dg179_source_preparation_v1"
QUARANTINE_POLICY = "exact reviewed unidentified records; not a tolerance"
REQUIRED_MANIFEST_KEYS = {
    "schema_version", "admitted_seasons", "excluded_seasons", "identified_weekly_sha256", "research_qualified",
    "individual_stat_completeness_proven", "game_coverage", "quarantine", "inputs", "limitations", "exposure_definition",
    "exact_league_claim",
}


def _null_id(frame: pd.DataFrame) -> pd.Series:
    return frame["player_id"].isna() | (frame["player_id"].astype(str).str.strip() == "")


def game_coverage(
    schedule: pd.DataFrame,
    weekly: pd.DataFrame,
    *,
    admitted_seasons: Iterable[int],
    cancelled_game_ids: set[str] = frozenset(),
) -> dict:
    """Exact REG game-id comparison per admitted season, measured before any filter."""
    admitted = sorted(set(int(s) for s in admitted_seasons))
    sched = schedule.loc[(schedule["game_type"] == "REG") & schedule["season"].isin(admitted)]
    week = weekly.loc[(weekly["season_type"] == "REG") & weekly["season"].isin(admitted)]
    per_season, missing_all, unexpected_all = [], [], []
    for season in admitted:
        s_ids = set(sched.loc[sched["season"] == season, "game_id"].astype(str))
        w_ids = set(week.loc[week["season"] == season, "game_id"].dropna().astype(str))
        cancelled = sorted(s_ids & set(cancelled_game_ids))
        missing = sorted(s_ids - w_ids - set(cancelled_game_ids))
        unexpected = sorted(w_ids - s_ids)
        # week labels must agree for the games both sides carry
        sw = sched.loc[sched["season"] == season, ["game_id", "week"]].drop_duplicates("game_id").set_index("game_id")["week"]
        ww = week.loc[week["season"] == season, ["game_id", "week"]].dropna().drop_duplicates("game_id").set_index("game_id")["week"]
        common = sw.index.intersection(ww.index)
        week_mismatch = sorted(g for g in common if int(sw[g]) != int(ww[g]))
        per_season.append({"season": season, "schedule_reg_games": len(s_ids), "cancelled": cancelled,
                           "completed_games": len(s_ids) - len(cancelled), "weekly_reg_games": len(w_ids),
                           "missing": missing, "unexpected": unexpected, "week_label_mismatches": week_mismatch})
        missing_all += missing
        unexpected_all += unexpected + [f"{g} (week {int(ww[g])} vs schedule {int(sw[g])})" for g in week_mismatch]
    return {"verified": not missing_all and not unexpected_all, "missing_game_ids": missing_all,
            "unexpected_game_ids": unexpected_all, "cancelled_game_ids": sorted(cancelled_game_ids), "per_season": per_season}


def split_identified(
    weekly: pd.DataFrame,
    *,
    admitted_seasons: Iterable[int],
    file_hashes: Mapping[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Admitted rows only: identified rows keep every column; null-id rows go to quarantine
    in full, each with ``source_file_sha256`` and ``source_row_index``."""
    admitted = set(int(s) for s in admitted_seasons)
    rows = weekly.loc[weekly["season"].isin(admitted)].copy()
    if "source_file" not in rows.columns or "source_row_index" not in rows.columns:
        raise ValueError("weekly rows must carry source_file and source_row_index provenance")
    rows["source_file_sha256"] = rows["source_file"].map(lambda f: file_hashes[f])
    null = _null_id(rows)
    identified = rows.loc[~null].reset_index(drop=True)
    quarantine = rows.loc[null].reset_index(drop=True)
    return identified, quarantine


def _shape(row) -> tuple:
    name = row.get("player_name")
    name = None if (name is None or (isinstance(name, float) and np.isnan(name))) else str(name)
    return (int(row["season"]), int(row["week"]), str(row["team"]), str(row["opponent_team"]), name,
            round(float(row["fantasy_points_ppr"]), 2))


def verify_quarantine(quarantine: pd.DataFrame, *, reviewed_nonzero: list[dict]) -> dict:
    """Zero placeholders are counted; nonzero rows must match the reviewed records exactly and
    one-for-one (season, week, team, opponent, name, points to 2 dp). No numeric tolerance."""
    pts = pd.to_numeric(quarantine["fantasy_points_ppr"], errors="coerce")
    nonzero = quarantine.loc[pts.fillna(0) != 0]
    reviewed_shapes = [_shape(r) for r in reviewed_nonzero]
    found = [_shape(r) for _, r in nonzero.iterrows()]
    for shape in found:
        if shape not in reviewed_shapes:
            raise ValueError(f"nonzero unidentified row {shape} is not among the reviewed records; preparation fails")
    for shape in reviewed_shapes:
        if shape not in found:
            raise ValueError(f"reviewed record {shape} is absent from the quarantine; preparation fails")
    totals = {}
    for season, g in quarantine.groupby("season"):
        p = pd.to_numeric(g["fantasy_points_ppr"], errors="coerce").fillna(0)
        totals[str(int(season))] = {"rows": int(len(g)), "signed_points": float(p.sum()), "absolute_points": float(p.abs().sum()),
                                    "nonzero_rows": int((p != 0).sum())}
    details = [{"season": s[0], "week": s[1], "team": s[2], "opponent_team": s[3], "player_name": s[4], "fantasy_points_ppr": s[5],
                "source_file_sha256": str(r["source_file_sha256"]), "source_row_index": int(r["source_row_index"])}
               for s, (_, r) in zip(found, nonzero.iterrows())]
    return {"row_count": int(len(quarantine)), "zero_placeholder_rows": int(len(quarantine) - len(nonzero)), "nonzero_rows": details,
            "point_totals_by_season": totals, "policy": QUARANTINE_POLICY}


def preparation_manifest(
    *,
    admitted_seasons: Iterable[int],
    excluded_seasons: Mapping[int, list[str]],
    identified_weekly_sha256: str,
    identified_rows: int,
    identified_columns: int,
    game_coverage: dict,
    quarantine: dict,
    inputs: list[dict],
    extra: Mapping | None = None,
) -> dict:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "admitted_seasons": sorted(set(int(s) for s in admitted_seasons)),
        "excluded_seasons": {str(int(s)): list(ids) for s, ids in excluded_seasons.items()},
        "excluded_seasons_policy": "incomplete schedule coverage in the source; never zero-labelled; rows remain only in the raw capture",
        "identified_weekly_sha256": identified_weekly_sha256,
        "identified_weekly": {"rows": int(identified_rows), "columns": int(identified_columns)},
        "research_qualified": True,
        "individual_stat_completeness_proven": False,
        "game_coverage": game_coverage,
        "quarantine": quarantine,
        "inputs": inputs,
        "exposure_definition": "stat-record weeks: a player-week exists when the source carries a stat record for that player in that game; "
                               "it is not a snap count and not a proof he dressed",
        "exact_league_claim": "NOT an exact reproduction of David's league scoring: saved default-PPR totals do not establish equivalence "
                              "for all-unit fumble losses, recovery touchdowns or individual special-teams forced-fumble/recovery bonuses; "
                              "the research preset must be named explicitly by the consumer",
        "limitations": [
            "identified-player research outcomes; individual-stat completeness is not proven",
            "1999 and 2000 excluded for missing schedule games; no history for those years is filled with zero",
            "the cancelled 2022 BUF-CIN game is excluded explicitly (271 completed games); no appearance is invented for it",
            "six nonzero unidentified records are quarantined by exact review, not by a tolerance; their points are excluded from every player",
            "negative points for identified players stay negative",
        ],
    }
    if extra:
        manifest.update(dict(extra))
    return manifest
