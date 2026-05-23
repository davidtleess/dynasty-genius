"""Tests for Phase 16.3 college feature builder."""
import pytest
from scripts.build_college_features import (
    normalize_player_name,
    compute_ryptpa,
    find_pff_match,
    build_college_season_year,
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


def test_build_college_season_year_standard():
    assert build_college_season_year(draft_year=2019, position="WR") == 2018


def test_build_college_season_year_opt_out_returns_none():
    # Opt-outs / non-standard cases return None — caller must handle via fallback
    # e.g. Ja'Marr Chase (2021 draft) sat out 2020; his file is in 2019 season
    assert build_college_season_year(draft_year=2021, position="WR", opt_out=True) is None
