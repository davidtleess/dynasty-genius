"""DG-165 — source preparation for DG-179 (Codex's contract, 2026-09-06).

Synthetic frames only. What each test would catch:
* game coverage judged from week labels instead of exact schedule game ids, or a cancelled
  game silently counted as missing / an unexpected weekly game silently accepted;
* a null-id row dropped without a quarantine record carrying its source row index and file
  hash, or an excluded season leaking into the identified file;
* a nonzero unidentified row that is NOT one of the exactly reviewed six being tolerated,
  or a reviewed one being absent — either must fail, never a numeric tolerance;
* a manifest missing a required key.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.dynasty_genius.rookie.source_preparation import (
    REQUIRED_MANIFEST_KEYS,
    game_coverage,
    preparation_manifest,
    split_identified,
    verify_quarantine,
)


def _schedule():
    return pd.DataFrame({
        "game_id": ["2001_01_A_B", "2001_02_C_D", "2022_17_BUF_CIN", "2022_01_E_F", "2022_20_G_H"],
        "season": [2001, 2001, 2022, 2022, 2022], "game_type": ["REG", "REG", "REG", "REG", "POST"], "week": [1, 2, 17, 1, 20],
        "away_team": ["A", "C", "BUF", "E", "G"], "home_team": ["B", "D", "CIN", "F", "H"],
        "result": [3, -7, None, 10, 1],
    })


def _weekly():
    rows = [
        # (season, week, season_type, game_id, team, opp, player_id, player_name, ppr, file, row_index)
        (2001, 1, "REG", "2001_01_A_B", "A", "B", "p1", "P One", 12.0, "f2001", 0),
        (2001, 2, "REG", "2001_02_C_D", "C", "D", "p2", "P Two", -1.0, "f2001", 1),
        (2001, 2, "REG", "2001_02_C_D", "C", "D", None, None, 0.0, "f2001", 2),      # zero placeholder
        (2001, 11, "REG", "2001_11_GB_DET", "GB", "DET", None, "Team", 1.68, "f2001", 3),  # reviewed nonzero
        (2022, 1, "REG", "2022_01_E_F", "E", "F", "p3", "P Three", 20.0, "f2022", 0),
        (2022, 1, "REG", "2022_01_E_F", "E", "F", None, None, 0.0, "f2022", 1),
        (2000, 3, "REG", "2000_03_X_Y", "X", "Y", "p9", "Old", 5.0, "f2000", 0),       # excluded season
    ]
    return pd.DataFrame(rows, columns=["season", "week", "season_type", "game_id", "team", "opponent_team", "player_id",
                                       "player_name", "fantasy_points_ppr", "source_file", "source_row_index"])


def test_game_coverage_compares_exact_reg_game_ids_and_honours_the_declared_cancellation():
    weekly = _weekly()
    cov = game_coverage(_schedule(), weekly, admitted_seasons=range(2001, 2023), cancelled_game_ids={"2022_17_BUF_CIN"})
    assert cov["verified"] is False                   # 2001_11_GB_DET is in weekly but not on the schedule
    assert cov["unexpected_game_ids"] == ["2001_11_GB_DET"]
    assert cov["missing_game_ids"] == []              # the cancelled game is excluded explicitly, not "missing"
    per = {p["season"]: p for p in cov["per_season"]}
    assert per[2022]["schedule_reg_games"] == 2 and per[2022]["cancelled"] == ["2022_17_BUF_CIN"] and per[2022]["weekly_reg_games"] == 1
    assert per[2022]["completed_games"] == 1
    weekly2 = weekly.loc[weekly["game_id"] != "2001_11_GB_DET"]
    assert game_coverage(_schedule(), weekly2, admitted_seasons=range(2001, 2023), cancelled_game_ids={"2022_17_BUF_CIN"})["verified"] is True


def test_split_keeps_only_admitted_identified_rows_and_quarantines_every_null_id_row_with_provenance():
    weekly = _weekly()
    identified, quarantine = split_identified(weekly, admitted_seasons=range(2001, 2023), file_hashes={"f2001": "h1", "f2022": "h2", "f2000": "h0"})
    assert set(identified["player_id"]) == {"p1", "p2", "p3"} and 2000 not in set(identified["season"])
    assert list(identified.columns) == [c for c in weekly.columns if c not in ("source_file", "source_row_index")] + ["source_file", "source_row_index"] or "source_row_index" in identified.columns
    assert len(quarantine) == 3 and quarantine["player_id"].isna().all()
    assert set(quarantine["source_file_sha256"]) == {"h1", "h2"} and set(quarantine["source_row_index"]) == {2, 3, 1}
    assert 2000 not in set(quarantine["season"])        # excluded seasons are not admitted at all, not quarantined


def test_verify_quarantine_accepts_exactly_the_reviewed_nonzero_rows_and_fails_on_any_other():
    weekly = _weekly()
    _, quarantine = split_identified(weekly, admitted_seasons=range(2001, 2023), file_hashes={"f2001": "h1", "f2022": "h2", "f2000": "h0"})
    reviewed = [{"season": 2001, "week": 11, "team": "GB", "opponent_team": "DET", "player_name": "Team", "fantasy_points_ppr": 1.68}]
    report = verify_quarantine(quarantine, reviewed_nonzero=reviewed)
    assert report["row_count"] == 3 and report["zero_placeholder_rows"] == 2 and len(report["nonzero_rows"]) == 1
    assert report["point_totals_by_season"]["2001"] == {"rows": 2, "signed_points": pytest.approx(1.68), "absolute_points": pytest.approx(1.68), "nonzero_rows": 1}
    assert report["policy"].startswith("exact reviewed unidentified records")
    with pytest.raises(ValueError, match="not among the reviewed"):
        verify_quarantine(quarantine, reviewed_nonzero=[])
    with pytest.raises(ValueError, match="reviewed record .* absent"):
        verify_quarantine(quarantine, reviewed_nonzero=reviewed + [{"season": 2003, "week": 4, "team": "PHI", "opponent_team": "BUF", "player_name": "Team", "fantasy_points_ppr": -0.1}])
    mismatched = [{**reviewed[0], "fantasy_points_ppr": 1.7}]
    with pytest.raises(ValueError, match="not among the reviewed"):
        verify_quarantine(quarantine, reviewed_nonzero=mismatched)


def test_preparation_manifest_carries_every_required_key_and_the_honest_flags():
    manifest = preparation_manifest(
        admitted_seasons=range(2001, 2026),
        excluded_seasons={1999: ["1999_01_BAL_STL"], 2000: ["2000_03_SD_KC", "2000_06_BUF_MIA"]},
        identified_weekly_sha256="a" * 64, identified_rows=10, identified_columns=150,
        game_coverage={"verified": True, "missing_game_ids": [], "unexpected_game_ids": [], "per_season": []},
        quarantine={"path": "quarantine.parquet", "sha256": "b" * 64, "row_count": 3, "nonzero_rows": [], "point_totals_by_season": {},
                    "policy": "exact reviewed unidentified records; not a tolerance"},
        inputs=[{"path": "raw/games.csv", "sha256": "c" * 64, "bytes": 1, "url": "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"}],
    )
    assert REQUIRED_MANIFEST_KEYS <= set(manifest)
    assert manifest["schema_version"] == "dg179_source_preparation_v1"
    assert manifest["research_qualified"] is True and manifest["individual_stat_completeness_proven"] is False
    assert manifest["admitted_seasons"] == list(range(2001, 2026)) and manifest["excluded_seasons"]["2000"] == ["2000_03_SD_KC", "2000_06_BUF_MIA"]
    assert "stat-record weeks" in manifest["exposure_definition"] and "not" in manifest["exact_league_claim"].lower()
