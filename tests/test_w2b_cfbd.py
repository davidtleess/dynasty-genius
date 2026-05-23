"""Tests for Phase 19 W2b CFBD player-level enrichment pipeline.

TDD suite covering:
  - pivot_receiving_stats: CFBD API record pivot (YDS, REC, TD, G)
  - pivot_rushing_stats: CFBD API record pivot (YDS, CAR, TD, G)
  - build_team_rec_lookup: sum player receiving yards by (school, year)
  - build_team_rush_lookup: sum player rushing yards by (school, year)
  - build_sp_lookup: SP+ rating keyed by (school, year)
  - compute_wr_cfbd_features: full WR feature set from pivot
  - compute_rb_cfbd_features: full RB feature set from pivot + SP lookup
  - compute_te_cfbd_features: TE RYPTPA + YPR career
  - compute_era_proxy_features: final_college_age, early_declare,
      wr_early_declare, covid_eligibility_flag from existing v3 columns
  - Leakage guard: no draft-capital columns emitted by W2b functions
"""
from __future__ import annotations

import pytest

from scripts.build_w2b_cfbd import (
    DOMINATOR_BREAKOUT_THRESHOLD,
    build_sp_lookup,
    build_team_rec_lookup,
    build_team_rush_lookup,
    compute_era_proxy_features,
    compute_rb_cfbd_features,
    compute_te_cfbd_features,
    compute_wr_cfbd_features,
    normalize_player_name,
    pivot_receiving_stats,
    pivot_rushing_stats,
)
from src.dynasty_genius.models.head_b_contract import HEAD_B_PROHIBITED_COLUMNS


# ── Synthetic CFBD API fixtures ───────────────────────────────────────────────

# Amari Cooper's 2014 (final year before 2015 draft) and 2013 seasons at Alabama
RECV_2014 = [
    {"player": "Amari Cooper", "team": "Alabama", "statType": "YDS", "stat": "1304"},
    {"player": "Amari Cooper", "team": "Alabama", "statType": "REC", "stat": "101"},
    {"player": "Amari Cooper", "team": "Alabama", "statType": "TD", "stat": "11"},
    {"player": "Amari Cooper", "team": "Alabama", "statType": "G", "stat": "13"},
    # Other Alabama receiver — makes team total > Cooper alone
    {"player": "ArDarius Stewart", "team": "Alabama", "statType": "YDS", "stat": "462"},
    {"player": "ArDarius Stewart", "team": "Alabama", "statType": "REC", "stat": "38"},
    {"player": "ArDarius Stewart", "team": "Alabama", "statType": "TD", "stat": "3"},
]
# Team total receiving yards 2014 Alabama = 1304 + 462 = 1766
# Cooper dominator 2014 = 1304 / 1766 ≈ 0.738 (above 0.20 threshold)

RECV_2013 = [
    # Cooper below breakout threshold in 2013
    {"player": "Amari Cooper", "team": "Alabama", "statType": "YDS", "stat": "300"},
    {"player": "Amari Cooper", "team": "Alabama", "statType": "REC", "stat": "45"},
    {"player": "Amari Cooper", "team": "Alabama", "statType": "TD", "stat": "4"},
    {"player": "Kevin Norwood", "team": "Alabama", "statType": "YDS", "stat": "1800"},
    {"player": "Kevin Norwood", "team": "Alabama", "statType": "REC", "stat": "120"},
    {"player": "Kevin Norwood", "team": "Alabama", "statType": "TD", "stat": "15"},
]
# Team total 2013 Alabama = 300 + 1800 = 2100
# Cooper dominator 2013 = 300 / 2100 ≈ 0.143 (below 0.20 threshold — no breakout yet)

RUSH_2015 = [
    {"player": "Derrick Henry", "team": "Alabama", "statType": "YDS", "stat": "895"},
    {"player": "Derrick Henry", "team": "Alabama", "statType": "CAR", "stat": "110"},
    {"player": "Derrick Henry", "team": "Alabama", "statType": "TD", "stat": "9"},
    {"player": "Derrick Henry", "team": "Alabama", "statType": "G", "stat": "14"},
    {"player": "Kenyan Drake", "team": "Alabama", "statType": "YDS", "stat": "408"},
    {"player": "Kenyan Drake", "team": "Alabama", "statType": "CAR", "stat": "72"},
    {"player": "Kenyan Drake", "team": "Alabama", "statType": "TD", "stat": "4"},
]
# Team rush total 2015 Alabama = 895 + 408 = 1303
# Henry dominator 2015 rush = 895/1303 ≈ 0.687

SP_2015 = [
    {"team": "Alabama", "rating": 38.4},
    {"team": "LSU", "rating": 18.2},
    {"team": "Ohio State", "rating": 32.1},
]


# ── normalize_player_name ─────────────────────────────────────────────────────

def test_normalize_removes_apostrophes():
    assert normalize_player_name("Ja'Marr Chase") == "jamarrchase"


def test_normalize_lowercases():
    assert normalize_player_name("Amari Cooper") == "amaricooper"


def test_normalize_removes_dots_and_hyphens():
    assert normalize_player_name("D.J. Moore") == "djmoore"


# ── pivot_receiving_stats ─────────────────────────────────────────────────────

def test_pivot_receiving_yds_rec_td():
    pivot = pivot_receiving_stats(RECV_2014, 2014)
    key = (normalize_player_name("Amari Cooper"), "alabama", 2014)
    assert key in pivot
    assert pivot[key]["rec_yds"] == pytest.approx(1304.0)
    assert pivot[key]["rec"] == pytest.approx(101.0)
    assert pivot[key]["rec_td"] == pytest.approx(11.0)


def test_pivot_receiving_games_captured():
    pivot = pivot_receiving_stats(RECV_2014, 2014)
    key = (normalize_player_name("Amari Cooper"), "alabama", 2014)
    assert pivot[key]["games"] == pytest.approx(13.0)


def test_pivot_receiving_multiple_players():
    pivot = pivot_receiving_stats(RECV_2014, 2014)
    assert len(pivot) == 2  # Cooper + Stewart


def test_pivot_receiving_no_games_field():
    """Records without G stat type should produce no 'games' key."""
    records_no_g = [r for r in RECV_2014 if r["statType"] != "G"]
    pivot = pivot_receiving_stats(records_no_g, 2014)
    key = (normalize_player_name("Amari Cooper"), "alabama", 2014)
    assert "games" not in pivot.get(key, {})


# ── pivot_rushing_stats ───────────────────────────────────────────────────────

def test_pivot_rushing_yds_car_td():
    pivot = pivot_rushing_stats(RUSH_2015, 2015)
    key = (normalize_player_name("Derrick Henry"), "alabama", 2015)
    assert key in pivot
    assert pivot[key]["rush_yds"] == pytest.approx(895.0)
    assert pivot[key]["rush_att"] == pytest.approx(110.0)
    assert pivot[key]["rush_td"] == pytest.approx(9.0)


def test_pivot_rushing_games_captured():
    pivot = pivot_rushing_stats(RUSH_2015, 2015)
    key = (normalize_player_name("Derrick Henry"), "alabama", 2015)
    assert pivot[key]["games"] == pytest.approx(14.0)


# ── build_team_rec_lookup ─────────────────────────────────────────────────────

def test_build_team_rec_lookup_sums_correctly():
    pivot = pivot_receiving_stats(RECV_2014, 2014)
    lookup = build_team_rec_lookup(pivot)
    assert ("alabama", 2014) in lookup
    # 1304 (Cooper) + 462 (Stewart) = 1766
    assert lookup[("alabama", 2014)] == pytest.approx(1766.0)


def test_build_team_rec_lookup_multiple_years():
    pivot_14 = pivot_receiving_stats(RECV_2014, 2014)
    pivot_13 = pivot_receiving_stats(RECV_2013, 2013)
    combined = {**pivot_14, **pivot_13}
    lookup = build_team_rec_lookup(combined)
    assert ("alabama", 2014) in lookup
    assert ("alabama", 2013) in lookup


# ── build_team_rush_lookup ────────────────────────────────────────────────────

def test_build_team_rush_lookup_sums_correctly():
    pivot = pivot_rushing_stats(RUSH_2015, 2015)
    lookup = build_team_rush_lookup(pivot)
    assert ("alabama", 2015) in lookup
    # 895 + 408 = 1303
    assert lookup[("alabama", 2015)] == pytest.approx(1303.0)


# ── build_sp_lookup ───────────────────────────────────────────────────────────

def test_build_sp_lookup_rating_keyed_by_school_year():
    lookup = build_sp_lookup(SP_2015, 2015)
    assert ("alabama", 2015) in lookup
    assert lookup[("alabama", 2015)] == pytest.approx(38.4)


def test_build_sp_lookup_multiple_schools():
    lookup = build_sp_lookup(SP_2015, 2015)
    assert len(lookup) == 3


# ── compute_wr_cfbd_features ──────────────────────────────────────────────────

def _make_wr_lookups():
    """Build rec_pivot and team_rec_lookup from synthetic 2013+2014 data."""
    pivot_14 = pivot_receiving_stats(RECV_2014, 2014)
    pivot_13 = pivot_receiving_stats(RECV_2013, 2013)
    pivot = {**pivot_14, **pivot_13}
    team_rec = build_team_rec_lookup(pivot)
    return pivot, team_rec


def test_wr_dominator_final_populated():
    """WR final-season dominator computed correctly from synthetic data."""
    pivot, team_rec = _make_wr_lookups()
    # Amari Cooper: draft_year=2015, college="Alabama", age_at_draft=21.0
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec)
    assert result["wr_dominator_final_missing"] == "0"
    val = float(result["wr_dominator_final"])
    # 1304 / 1766 ≈ 0.738
    assert 0.70 < val < 0.80


def test_wr_breakout_age_populated_final_season():
    """WR breakout_age set to first season ≥ 0.20 dominator.

    In 2013 Cooper's dominator ≈ 0.143 (below threshold).
    In 2014 Cooper's dominator ≈ 0.738 (above threshold).
    breakout_age should be his age in 2014 = 21.0 - 1 = 20.0.
    """
    pivot, team_rec = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec)
    assert result["wr_breakout_age_missing"] == "0"
    assert float(result["wr_breakout_age"]) == pytest.approx(20.0)


def test_wr_ypr_career_populated():
    """Career YPR = total_rec_yds / total_rec."""
    pivot, team_rec = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec)
    assert result["wr_yards_per_reception_career_missing"] == "0"
    ypr = float(result["wr_yards_per_reception_career"])
    # (1304 + 300) / (101 + 45) = 1604 / 146 ≈ 10.99
    assert 10.0 < ypr < 12.0


def test_wr_rec_tds_per_game_final_populated():
    """TDs per game in final season (requires G stat)."""
    pivot, team_rec = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec)
    assert result["wr_rec_tds_per_game_final_missing"] == "0"
    # 11 TD / 13 games ≈ 0.846
    val = float(result["wr_rec_tds_per_game_final"])
    assert 0.80 < val < 0.90


def test_wr_features_missing_when_no_match():
    """Player not in pivot → all WR features return _missing=1."""
    pivot, team_rec = _make_wr_lookups()
    row = {"pfr_player_name": "Unknown Player", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec)
    for col in ("wr_dominator_final", "wr_breakout_age", "wr_yards_per_reception_career"):
        assert result[f"{col}_missing"] == "1", f"{col}_missing should be 1 for unmatched player"


# ── compute_rb_cfbd_features ──────────────────────────────────────────────────

def _make_rb_lookups():
    rush_pivot = pivot_rushing_stats(RUSH_2015, 2015)
    team_rush = build_team_rush_lookup(rush_pivot)
    rec_pivot = {}  # no receiving for this test
    sp = build_sp_lookup(SP_2015, 2015)
    return rush_pivot, rec_pivot, team_rush, sp


def test_rb_final_dominator_populated():
    rush_pivot, rec_pivot, team_rush, sp = _make_rb_lookups()
    # Derrick Henry: draft_year=2016, college="Alabama"
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, sp)
    assert result["rb_final_dominator_missing"] == "0"
    val = float(result["rb_final_dominator"])
    # 895 / 1303 ≈ 0.687
    assert 0.65 < val < 0.72


def test_rb_school_sp_plus_populated():
    rush_pivot, rec_pivot, team_rush, sp = _make_rb_lookups()
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, sp)
    assert result["rb_school_sp_plus_missing"] == "0"
    assert float(result["rb_school_sp_plus"]) == pytest.approx(38.4)


def test_rb_features_missing_when_no_match():
    rush_pivot, rec_pivot, team_rush, sp = _make_rb_lookups()
    row = {"pfr_player_name": "No One", "college": "Alabama",
           "season": "2016", "age_at_draft": "22.0", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, sp)
    assert result["rb_final_dominator_missing"] == "1"


# ── compute_te_cfbd_features ──────────────────────────────────────────────────

def test_te_ypr_career_populated():
    """TE career YPR from receiving pivot."""
    pivot_14 = pivot_receiving_stats(RECV_2014, 2014)
    # Treat Amari Cooper as a TE for this unit test
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_te_cfbd_features(row, pivot_14, team_pass_attempts_lookup={})
    assert result["te_yards_per_reception_career_missing"] == "0"
    ypr = float(result["te_yards_per_reception_career"])
    # 1304 / 101 ≈ 12.91
    assert 12.5 < ypr < 13.5


def test_te_ryptpa_populated_from_lookup():
    """te_ryptpa_final uses preloaded team pass attempts."""
    pivot_14 = pivot_receiving_stats(RECV_2014, 2014)
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    # Provide mocked team pass attempts: Alabama 2014 = 350
    tpa_lookup = {("Alabama", 2014): 350.0}
    result = compute_te_cfbd_features(row, pivot_14, tpa_lookup)
    assert result["te_ryptpa_final_missing"] == "0"
    # 1304 / 350 ≈ 3.726
    val = float(result["te_ryptpa_final"])
    assert 3.5 < val < 4.0


def test_te_ryptpa_missing_when_no_pass_attempts():
    """If team pass attempts unavailable, te_ryptpa_final stays _missing=1."""
    pivot_14 = pivot_receiving_stats(RECV_2014, 2014)
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_te_cfbd_features(row, pivot_14, team_pass_attempts_lookup={})
    assert result["te_ryptpa_final_missing"] == "1"


# ── compute_era_proxy_features ────────────────────────────────────────────────

def test_era_proxy_final_college_age():
    """final_college_age = age_at_draft - 1 (proxy)."""
    row = {"age_at_draft": "22.5", "age_at_draft_missing": "0",
           "season": "2020", "position": "WR"}
    result = compute_era_proxy_features(row)
    assert result["final_college_age_missing"] == "0"
    assert float(result["final_college_age"]) == pytest.approx(21.5)
    assert result["final_college_age_source"] == "proxy_age_at_draft"


def test_era_proxy_early_declare_true():
    """age_at_draft ≤ 21.0 → early_declare = 1."""
    row = {"age_at_draft": "21.0", "age_at_draft_missing": "0",
           "season": "2018", "position": "WR"}
    result = compute_era_proxy_features(row)
    assert result["early_declare"] == "1"
    assert result["early_declare_missing"] == "0"


def test_era_proxy_early_declare_false():
    """age_at_draft > 21.0 → early_declare = 0."""
    row = {"age_at_draft": "22.8", "age_at_draft_missing": "0",
           "season": "2018", "position": "RB"}
    result = compute_era_proxy_features(row)
    assert result["early_declare"] == "0"
    assert result["early_declare_missing"] == "0"


def test_era_proxy_wr_early_declare_for_wr():
    """wr_early_declare populated for WR rows only."""
    wr_row = {"age_at_draft": "20.5", "age_at_draft_missing": "0",
              "season": "2019", "position": "WR"}
    result = compute_era_proxy_features(wr_row)
    assert result["wr_early_declare"] == "1"
    assert result["wr_early_declare_missing"] == "0"


def test_era_proxy_wr_early_declare_missing_for_rb():
    """wr_early_declare stays _missing=1 for non-WR rows."""
    rb_row = {"age_at_draft": "20.5", "age_at_draft_missing": "0",
              "season": "2019", "position": "RB"}
    result = compute_era_proxy_features(rb_row)
    assert result["wr_early_declare"] == ""
    assert result["wr_early_declare_missing"] == "1"


def test_era_proxy_covid_flag_true():
    """draft_year 2021/2022 + age_at_draft >= 23 → covid_eligibility_flag = 1."""
    row = {"age_at_draft": "23.5", "age_at_draft_missing": "0",
           "season": "2022", "position": "TE"}
    result = compute_era_proxy_features(row)
    assert result["covid_eligibility_flag"] == "1"
    assert result["covid_eligibility_flag_missing"] == "0"


def test_era_proxy_covid_flag_false_wrong_year():
    """draft_year outside COVID window → covid_eligibility_flag = 0."""
    row = {"age_at_draft": "24.0", "age_at_draft_missing": "0",
           "season": "2019", "position": "RB"}
    result = compute_era_proxy_features(row)
    assert result["covid_eligibility_flag"] == "0"
    assert result["covid_eligibility_flag_missing"] == "0"


def test_era_proxy_covid_flag_false_too_young():
    """draft_year 2021 but age < 23 → covid_eligibility_flag = 0."""
    row = {"age_at_draft": "21.5", "age_at_draft_missing": "0",
           "season": "2021", "position": "WR"}
    result = compute_era_proxy_features(row)
    assert result["covid_eligibility_flag"] == "0"


def test_era_proxy_missing_age_gives_missing_flags():
    """When age_at_draft is missing, all proxy features are _missing=1."""
    row = {"age_at_draft": "", "age_at_draft_missing": "1",
           "season": "2020", "position": "WR"}
    result = compute_era_proxy_features(row)
    assert result["final_college_age_missing"] == "1"
    assert result["early_declare_missing"] == "1"
    assert result["covid_eligibility_flag_missing"] == "1"


# ── Leakage guard ─────────────────────────────────────────────────────────────

def test_w2b_functions_emit_no_draft_capital_columns():
    """W2b compute functions must not emit any HEAD_B_PROHIBITED_COLUMNS."""
    pivot, team_rec = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0",
           "position": "WR"}
    wr_result = compute_wr_cfbd_features(row, pivot, team_rec)
    era_result = compute_era_proxy_features(row)
    all_keys = set(wr_result) | set(era_result)
    banned = {k for k in all_keys if k in HEAD_B_PROHIBITED_COLUMNS}
    assert not banned, f"W2b emitted prohibited columns: {banned}"
