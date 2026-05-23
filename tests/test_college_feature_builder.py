"""Tests for Phase 16.3 college feature builder."""
import pytest
from scripts.build_college_features import (
    normalize_player_name,
    compute_ryptpa,
    find_pff_match,
    find_pff_name_mismatch,
    find_pff_match_any_season,
    build_college_season_year,
    MANIFEST_DRAFT_YEARS,
)


def test_normalize_player_name_strips_suffix():
    assert normalize_player_name("A.J. Brown Jr.") == "aj brown"
    assert normalize_player_name("Marvin Harrison II") == "marvin harrison"
    assert normalize_player_name("DeVonta Smith") == "devonta smith"


def test_normalize_player_name_removes_punctuation():
    assert normalize_player_name("Ja'Marr Chase") == "jamarr chase"
    assert normalize_player_name("D.J. Moore") == "dj moore"


def test_compute_ryptpa_basic():
    result = compute_ryptpa(receiving_yards=1000.0, team_pass_attempts=400.0)
    assert result == pytest.approx(2.5)


def test_compute_ryptpa_returns_none_on_zero_attempts():
    result = compute_ryptpa(receiving_yards=1000.0, team_pass_attempts=0.0)
    assert result is None


def test_compute_ryptpa_returns_none_when_yards_missing():
    result = compute_ryptpa(receiving_yards=None, team_pass_attempts=400.0)
    assert result is None


def test_compute_ryptpa_returns_none_when_attempts_missing():
    result = compute_ryptpa(receiving_yards=1000.0, team_pass_attempts=None)
    assert result is None


def test_find_pff_match_exact():
    pff_rows = [
        {"player_name": "AJ Brown", "college": "Mississippi", "yprr": 2.5, "yards": 1000.0},
    ]
    result = find_pff_match("A.J. Brown", "Mississippi", pff_rows)
    assert result is not None
    assert result["yards"] == 1000.0


def test_find_pff_match_college_abbrev():
    pff_rows = [
        {"player_name": "Courtland Sutton", "college": "SMU", "yprr": 2.1, "yards": 900.0},
    ]
    result = find_pff_match("Courtland Sutton", "SMU", pff_rows)
    assert result is not None


def test_find_pff_match_returns_none_for_no_match():
    pff_rows = [
        {"player_name": "Other Player", "college": "Alabama", "yprr": 2.0, "yards": 800.0},
    ]
    result = find_pff_match("AJ Brown", "Mississippi", pff_rows)
    assert result is None


def test_find_pff_match_college_mismatch_returns_none():
    # Name matches but college differs — must NOT auto-resolve (identity risk).
    pff_rows = [
        {"player_name": "John Smith", "college": "Alabama", "yprr": 2.0, "yards": 800.0},
    ]
    result = find_pff_match("John Smith", "Georgia", pff_rows)
    assert result is None


def test_find_pff_name_mismatch_detected():
    # Name matches but college differs — find_pff_name_mismatch returns the row
    # so the builder can route it to manual review.
    pff_rows = [
        {"player_name": "John Smith", "college": "Alabama", "yprr": 2.0, "yards": 800.0},
    ]
    result = find_pff_name_mismatch("John Smith", "Georgia", pff_rows)
    assert result is not None
    assert result["college"] == "Alabama"


def test_find_pff_name_mismatch_no_detection_on_exact_match():
    # If college also matches, find_pff_name_mismatch should return None.
    pff_rows = [
        {"player_name": "John Smith", "college": "Alabama", "yprr": 2.0, "yards": 800.0},
    ]
    result = find_pff_name_mismatch("John Smith", "Alabama", pff_rows)
    assert result is None


def test_find_pff_match_any_season_found():
    pff_by_season = {
        2019: [{"player_name": "Jamarr Chase", "college": "LSU", "yprr": 4.0, "yards": 1200.0}],
        2020: [],  # sat out — not present
    }
    result = find_pff_match_any_season("Ja'Marr Chase", "LSU", pff_by_season, exclude_season=2020)
    assert result is not None
    found_season, found_row = result
    assert found_season == 2019
    assert found_row["yards"] == 1200.0


def test_find_pff_match_any_season_not_found():
    pff_by_season = {
        2019: [{"player_name": "Other Player", "college": "Alabama", "yprr": 2.0, "yards": 800.0}],
    }
    result = find_pff_match_any_season("Ja'Marr Chase", "LSU", pff_by_season)
    assert result is None


def test_build_college_season_year_standard():
    assert build_college_season_year(draft_year=2019, position="WR") == 2018


def test_build_college_season_year_opt_out_returns_none():
    # Opt-outs / non-standard cases return None — caller must handle via fallback
    # e.g. Ja'Marr Chase (2021 draft) sat out 2020; his file is in 2019 season
    assert build_college_season_year(draft_year=2021, position="WR", opt_out=True) is None


def test_manifest_draft_years_range():
    assert 2018 in MANIFEST_DRAFT_YEARS
    assert 2024 in MANIFEST_DRAFT_YEARS
    assert 2017 not in MANIFEST_DRAFT_YEARS
    assert 2025 not in MANIFEST_DRAFT_YEARS
