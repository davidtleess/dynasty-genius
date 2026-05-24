"""Tests for Phase 19 W2b CFBD player-level enrichment pipeline.

TDD suite covering:
  - pivot_receiving_stats: CFBD API record pivot (YDS, REC, TD, G)
  - pivot_rushing_stats: CFBD API record pivot (YDS, CAR, TD, G)
  - build_team_rec_lookup: sum player receiving yards by (school, year)
  - build_team_td_lookup: sum player receiving TDs by (school, year)
  - build_team_rush_lookup: sum player rushing yards by (school, year)
  - build_sp_lookup: SP+ rating keyed by (school, year)
  - compute_wr_cfbd_features: WR features; dominator = avg(yds_share, td_share)
  - compute_rb_cfbd_features: RB scrimmage dominator + SP+
  - compute_te_cfbd_features: TE RYPTPA + YPR career
  - compute_era_proxy_features: final_college_age, early_declare,
      wr_early_declare, covid_eligibility_flag from existing v3 columns
  - Dark features: wr_rec_tds_per_game_final, yprr_college permanently _missing=1
      (CFBD player/season endpoint omits games played; yprr_college requires PFF)
  - Games-proxy features: rb_scrimmage_ypg, rb_rec_ypg populated when team_games_lookup
      provided (CFBD /games endpoint team-games proxy); dark when lookup absent
  - wr_ryptpa: populated when team_pass_attempts_lookup provided; dark otherwise
  - Games-count caching: _load_games_count_cache / _save_games_count_cache round-trip
  - w2b_cfbd_degraded: always-written provenance flag
  - TPA caching: _load_tpa_cache / _save_tpa_cache round-trip
  - Leakage guard: no draft-capital columns emitted by W2b functions
"""
from __future__ import annotations

import csv
import json

import pytest

import scripts.build_w2b_cfbd as bw2b
from scripts.build_w2b_cfbd import (
    DOMINATOR_BREAKOUT_THRESHOLD,
    build_sp_lookup,
    build_team_rec_lookup,
    build_team_rush_lookup,
    build_team_td_lookup,
    compute_era_proxy_features,
    compute_qb_cfbd_features,
    compute_rb_cfbd_features,
    compute_te_cfbd_features,
    compute_wr_cfbd_features,
    load_team_games_count,
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
# Team total receiving TDs  2014 Alabama = 11 + 3 = 14
# Cooper yds_share 2014 = 1304 / 1766 ≈ 0.738
# Cooper td_share  2014 = 11 / 14 ≈ 0.786
# Cooper dominator 2014 = (0.738 + 0.786) / 2 ≈ 0.762  (above 0.20 threshold)

RECV_2013 = [
    # Cooper below breakout threshold in 2013
    {"player": "Amari Cooper", "team": "Alabama", "statType": "YDS", "stat": "300"},
    {"player": "Amari Cooper", "team": "Alabama", "statType": "REC", "stat": "45"},
    {"player": "Amari Cooper", "team": "Alabama", "statType": "TD", "stat": "4"},
    {"player": "Kevin Norwood", "team": "Alabama", "statType": "YDS", "stat": "1800"},
    {"player": "Kevin Norwood", "team": "Alabama", "statType": "REC", "stat": "120"},
    {"player": "Kevin Norwood", "team": "Alabama", "statType": "TD", "stat": "15"},
]
# Team total 2013 Alabama: yds = 300 + 1800 = 2100, TDs = 4 + 15 = 19
# Cooper yds_share 2013 = 300/2100 ≈ 0.143; td_share = 4/19 ≈ 0.211
# Cooper dominator 2013 = (0.143 + 0.211) / 2 ≈ 0.177  (below 0.20 — no breakout yet)

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
# Henry rush dominator 2015 = 895/1303 ≈ 0.687
# Scrimmage dominator (no rec data) = (895+0)/(1303+0) ≈ 0.687

SP_2015 = [
    {"team": "Alabama", "rating": 38.4},
    {"team": "LSU", "rating": 18.2},
    {"team": "Ohio State", "rating": 32.1},
]


# ── normalize_player_name ─────────────────────────────────────────────────────

def test_normalize_removes_apostrophes():
    # "Ja'Marr" has two r's: J-a-M-a-r-r → stripped of apostrophe → "jamarr"
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
    """G stat is mapped when present (not returned by real API but handled correctly)."""
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
    """G stat is mapped when present (not returned by real API but handled correctly)."""
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


# ── build_team_td_lookup ──────────────────────────────────────────────────────

def test_build_team_td_lookup_sums_correctly():
    pivot = pivot_receiving_stats(RECV_2014, 2014)
    lookup = build_team_td_lookup(pivot)
    assert ("alabama", 2014) in lookup
    # 11 (Cooper) + 3 (Stewart) = 14
    assert lookup[("alabama", 2014)] == pytest.approx(14.0)


def test_build_team_td_lookup_2013():
    pivot = pivot_receiving_stats(RECV_2013, 2013)
    lookup = build_team_td_lookup(pivot)
    # 4 (Cooper) + 15 (Norwood) = 19
    assert lookup[("alabama", 2013)] == pytest.approx(19.0)


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
    """Build rec_pivot, team_rec_lookup, team_td_lookup from synthetic 2013+2014 data."""
    pivot_14 = pivot_receiving_stats(RECV_2014, 2014)
    pivot_13 = pivot_receiving_stats(RECV_2013, 2013)
    pivot = {**pivot_14, **pivot_13}
    team_rec = build_team_rec_lookup(pivot)
    team_td = build_team_td_lookup(pivot)
    return pivot, team_rec, team_td


def test_wr_dominator_final_is_avg_yds_and_td_share():
    """wr_dominator_final = avg(yds_share, td_share) in final season (spec §3A.1)."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    assert result["wr_dominator_final_missing"] == "0"
    val = float(result["wr_dominator_final"])
    # yds_share = 1304/1766 ≈ 0.738; td_share = 11/14 ≈ 0.786; avg ≈ 0.762
    assert 0.72 < val < 0.80


def test_wr_market_share_yds_is_yds_share_only():
    """wr_market_share_yds = yds/team_yds only in final season (spec §3A.3)."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    assert result["wr_market_share_yds_missing"] == "0"
    msy = float(result["wr_market_share_yds"])
    # 1304/1766 ≈ 0.738 — must differ from dominator_final which is averaged
    assert 0.70 < msy < 0.76
    dom = float(result["wr_dominator_final"])
    assert msy != dom, "market_share_yds should differ from dominator_final (yds-only vs avg)"


def test_wr_breakout_age_populated():
    """WR breakout_age = first season ≥ 0.20 averaged dominator.

    2013: avg(0.143, 0.211) ≈ 0.177 — below threshold.
    2014: avg(0.738, 0.786) ≈ 0.762 — above threshold.
    breakout_age = age in 2014 = 21.0 - (2015 - 2014) = 20.0.
    """
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    assert result["wr_breakout_age_missing"] == "0"
    assert float(result["wr_breakout_age"]) == pytest.approx(20.0)


def test_wr_ypr_career_populated():
    """Career YPR = total_rec_yds / total_rec across all seasons."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    assert result["wr_yards_per_reception_career_missing"] == "0"
    ypr = float(result["wr_yards_per_reception_career"])
    # (1304 + 300) / (101 + 45) = 1604 / 146 ≈ 10.99
    assert 10.0 < ypr < 12.0


def test_wr_rec_tds_per_game_final_is_dark():
    """wr_rec_tds_per_game_final is a dark feature: CFBD omits games from player stats."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    assert result["wr_rec_tds_per_game_final_missing"] == "1"
    assert result["wr_rec_tds_per_game_final"] == ""


def test_wr_ryptpa_populated_from_cfbd_receiving_and_team_pass_attempts():
    """ryptpa = final_season_rec_yds / team_pass_attempts (downstream contract column name)."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    tpa_lookup = {("Alabama", 2014): 350.0}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td,
                                      team_pass_attempts_lookup=tpa_lookup)
    assert result["ryptpa_missing"] == "0"
    val = float(result["ryptpa"])
    # Cooper 2014: rec_yds=1304, Alabama 2014 TPA=350 → 1304/350 ≈ 3.726
    assert 3.5 < val < 4.0


def test_wr_ryptpa_missing_when_no_pass_attempts_available():
    """ryptpa stays _missing=1 when no TPA lookup entry for player's college/year."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td,
                                      team_pass_attempts_lookup={})
    assert result["ryptpa_missing"] == "1"
    assert result["ryptpa"] == ""


def test_wr_cfbd_features_does_not_emit_wr_ryptpa():
    """W2b must write 'ryptpa', not 'wr_ryptpa' — downstream bakeoff contract uses 'ryptpa'."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    assert "wr_ryptpa" not in result, "must not emit 'wr_ryptpa' — contract column is 'ryptpa'"
    assert "wr_ryptpa_missing" not in result
    assert "wr_ryptpa_source" not in result


def test_wr_yprr_college_is_dark():
    """yprr_college is permanently dark: requires PFF premium routes-run data absent from CFBD."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    assert result["yprr_college_missing"] == "1"
    assert result["yprr_college"] == ""


def test_wr_features_missing_when_no_match():
    """Player not in pivot → all WR computed features return _missing=1."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Unknown Player", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0"}
    result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    for col in ("wr_dominator_final", "wr_breakout_age", "wr_yards_per_reception_career",
                "wr_market_share_yds"):
        assert result[f"{col}_missing"] == "1", f"{col}_missing should be 1 for unmatched player"


# ── compute_rb_cfbd_features ──────────────────────────────────────────────────

def _make_rb_lookups():
    rush_pivot = pivot_rushing_stats(RUSH_2015, 2015)
    team_rush = build_team_rush_lookup(rush_pivot)
    rec_pivot: dict = {}
    team_rec: dict = {}  # empty — Henry has no receiving data in fixture
    sp = build_sp_lookup(SP_2015, 2015)
    return rush_pivot, rec_pivot, team_rush, team_rec, sp


def test_rb_final_dominator_scrimmage_formula():
    """rb_final_dominator uses (rush_yds + rec_yds) / (team_rush + team_rec)."""
    rush_pivot, rec_pivot, team_rush, team_rec, sp = _make_rb_lookups()
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_final_dominator_missing"] == "0"
    val = float(result["rb_final_dominator"])
    # player: 895 rush + 0 rec = 895; team: 1303 rush + 0 rec = 1303 → 895/1303 ≈ 0.687
    assert 0.65 < val < 0.72


def test_rb_scrimmage_ypg_missing_when_no_games_provided():
    """rb_scrimmage_ypg is dark when team_games_lookup is empty (no games proxy available)."""
    rush_pivot, rec_pivot, team_rush, team_rec, sp = _make_rb_lookups()
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_scrimmage_ypg_missing"] == "1"
    assert result["rb_scrimmage_ypg"] == ""


def test_rb_rec_ypg_missing_when_no_games_provided():
    """rb_rec_ypg is dark when team_games_lookup is empty (no games proxy available)."""
    rush_pivot, rec_pivot, team_rush, team_rec, sp = _make_rb_lookups()
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_rec_ypg_missing"] == "1"
    assert result["rb_rec_ypg"] == ""


def test_rb_scrimmage_ypg_populated_using_team_games_proxy():
    """rb_scrimmage_ypg = (rush_yds + rec_yds) / team_games when lookup provided."""
    rush_pivot, rec_pivot, team_rush, team_rec, sp = _make_rb_lookups()
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    games_lookup = {("alabama", 2015): 14}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp,
                                      team_games_lookup=games_lookup)
    assert result["rb_scrimmage_ypg_missing"] == "0"
    val = float(result["rb_scrimmage_ypg"])
    # Henry 2015: rush_yds=895, rec_yds=0 → scrimmage=895 / 14 games ≈ 63.93
    assert 60.0 < val < 68.0


def test_rb_rec_ypg_populated_using_team_games_proxy():
    """rb_rec_ypg = rec_yds / team_games when lookup and rec data both provided."""
    rush_pivot = pivot_rushing_stats(RUSH_2015, 2015)
    recv_henry_2015 = [
        {"player": "Derrick Henry", "team": "Alabama", "statType": "YDS", "stat": "100"},
        {"player": "Derrick Henry", "team": "Alabama", "statType": "REC", "stat": "8"},
        {"player": "Other WR", "team": "Alabama", "statType": "YDS", "stat": "600"},
    ]
    rec_pivot = pivot_receiving_stats(recv_henry_2015, 2015)
    team_rush = build_team_rush_lookup(rush_pivot)
    team_rec = build_team_rec_lookup(rec_pivot)
    sp = build_sp_lookup(SP_2015, 2015)
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    games_lookup = {("alabama", 2015): 14}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp,
                                      team_games_lookup=games_lookup)
    assert result["rb_rec_ypg_missing"] == "0"
    val = float(result["rb_rec_ypg"])
    # Henry 2015: rec_yds=100, team_games=14 → 100/14 ≈ 7.14
    assert 6.5 < val < 8.0


def test_rb_scrimmage_dominator_includes_receiving_when_available():
    """When rec data exists, scrimmage formula uses both numerator and denominator."""
    rush_pivot = pivot_rushing_stats(RUSH_2015, 2015)
    # Add receiving data for Henry in 2015
    recv_henry_2015 = [
        {"player": "Derrick Henry", "team": "Alabama", "statType": "YDS", "stat": "100"},
        {"player": "Derrick Henry", "team": "Alabama", "statType": "REC", "stat": "8"},
        {"player": "Other WR", "team": "Alabama", "statType": "YDS", "stat": "600"},
    ]
    rec_pivot = pivot_receiving_stats(recv_henry_2015, 2015)
    team_rush = build_team_rush_lookup(rush_pivot)
    team_rec = build_team_rec_lookup(rec_pivot)
    sp = build_sp_lookup(SP_2015, 2015)

    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_final_dominator_missing"] == "0"
    val = float(result["rb_final_dominator"])
    # player: 895 + 100 = 995; team: 1303 + 700 = 2003 → 995/2003 ≈ 0.497
    assert 0.45 < val < 0.55


def test_rb_school_sp_plus_populated():
    rush_pivot, rec_pivot, team_rush, team_rec, sp = _make_rb_lookups()
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_school_sp_plus_missing"] == "0"
    assert float(result["rb_school_sp_plus"]) == pytest.approx(38.4)


def test_rb_features_missing_when_no_match():
    rush_pivot, rec_pivot, team_rush, team_rec, sp = _make_rb_lookups()
    row = {"pfr_player_name": "No One", "college": "Alabama",
           "season": "2016", "age_at_draft": "22.0", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
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


# ── Phase 20 W2 RB efficiency features ───────────────────────────────────────

RUSH_2014_LOW_ATT = [
    {"player": "Low Carries RB", "team": "Alabama", "statType": "YDS", "stat": "200"},
    {"player": "Low Carries RB", "team": "Alabama", "statType": "CAR", "stat": "30"},
]

RECV_HENRY_MULTI = [
    # 2015 (final year before 2016 draft)
    {"player": "Derrick Henry", "team": "Alabama", "statType": "YDS", "stat": "180"},
    {"player": "Derrick Henry", "team": "Alabama", "statType": "REC", "stat": "18"},
    # 2014
    {"player": "Derrick Henry", "team": "Alabama", "statType": "YDS", "stat": "90"},
    {"player": "Derrick Henry", "team": "Alabama", "statType": "REC", "stat": "9"},
]


def test_rb_yards_per_carry_final_computed_from_rush_att():
    """rb_yards_per_carry_final = rush_yds / rush_att in final season."""
    rush_pivot, rec_pivot, team_rush, team_rec, sp = _make_rb_lookups()
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_yards_per_carry_final_missing"] == "0", (
        "Expected rb_yards_per_carry_final to be populated for Henry 2015 (110 CAR ≥ 50)"
    )
    ypc = float(result["rb_yards_per_carry_final"])
    # 895 yds / 110 CAR ≈ 8.136
    assert 8.0 < ypc < 8.3, f"Got {ypc}, expected ~8.14"
    assert result["rb_yards_per_carry_final_source"] == "cfbd"


def test_rb_yards_per_carry_final_volume_gate_below_50_att():
    """Below 50 rush attempts → rb_yards_per_carry_final dark (_missing=1)."""
    rush_pivot = pivot_rushing_stats(RUSH_2014_LOW_ATT, 2014)
    team_rush = build_team_rush_lookup(rush_pivot)
    rec_pivot: dict = {}
    team_rec: dict = {}
    sp = build_sp_lookup(SP_2015, 2015)
    row = {"pfr_player_name": "Low Carries RB", "college": "Alabama",
           "season": "2015", "age_at_draft": "22.0", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_yards_per_carry_final_missing"] == "1", (
        "30 CAR < 50 volume gate — should be _missing=1"
    )
    assert result["rb_yards_per_carry_final"] == ""


def test_rb_yards_per_reception_career_computed_from_career_rec():
    """rb_yards_per_reception_career = career rec_yds / career rec (≥10 threshold)."""
    rush_pivot = pivot_rushing_stats(RUSH_2015, 2015)
    team_rush = build_team_rush_lookup(rush_pivot)
    # Multi-year receiving: 2015 (final) + 2014 = 180+90=270 yds, 18+9=27 rec
    recv_pivot_15 = pivot_receiving_stats(RECV_HENRY_MULTI[:2], 2015)
    recv_pivot_14 = pivot_receiving_stats(RECV_HENRY_MULTI[2:], 2014)
    rec_pivot = {**recv_pivot_15, **recv_pivot_14}
    team_rec = build_team_rec_lookup(rec_pivot)
    sp = build_sp_lookup(SP_2015, 2015)
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_yards_per_reception_career_missing"] == "0", (
        "Expected rb_yards_per_reception_career populated (27 career rec ≥ 10)"
    )
    ypr = float(result["rb_yards_per_reception_career"])
    # 270 career rec_yds / 27 career rec = 10.0
    assert 9.5 < ypr < 10.5, f"Got {ypr}, expected ~10.0"
    assert result["rb_yards_per_reception_career_source"] == "cfbd"


def test_rb_yards_per_reception_career_volume_gate_below_10_rec():
    """Below 10 career receptions → rb_yards_per_reception_career dark."""
    rush_pivot, rec_pivot, team_rush, team_rec, sp = _make_rb_lookups()
    row = {"pfr_player_name": "Derrick Henry", "college": "Alabama",
           "season": "2016", "age_at_draft": "21.9", "age_at_draft_missing": "0"}
    # _make_rb_lookups() gives empty rec_pivot → career_rec = 0 < 10
    result = compute_rb_cfbd_features(row, rush_pivot, rec_pivot, team_rush, team_rec, sp)
    assert result["rb_yards_per_reception_career_missing"] == "1", (
        "0 career rec < 10 volume gate — should be _missing=1"
    )


# ── Phase 20 W3 QB compute function ─────────────────────────────────────────

def test_compute_qb_cfbd_features_maps_four_features(tmp_path):
    """compute_qb_cfbd_features returns four QB feature columns when adapter succeeds
    and pass_attempts >= 100."""
    from unittest.mock import patch as mock_patch

    mock_stats = {
        "completion_pct": 0.652,
        "yards_per_attempt": 8.1,
        "td_int_ratio": 3.75,
        "sack_rate": 0.04,
        "pass_attempts": 400,
    }
    row = {"pfr_player_name": "Trevor Lawrence", "college": "Clemson",
           "season": "2021", "position": "QB"}
    with mock_patch(
        "scripts.build_w2b_cfbd.fetch_qb_college_stats",
        return_value=mock_stats,
    ):
        result = compute_qb_cfbd_features(row, api_key="test-key", cache_dir=tmp_path)

    assert result["qb_completion_pct_final_missing"] == "0"
    assert result["qb_yards_per_attempt_final_missing"] == "0"
    assert result["qb_td_int_ratio_final_missing"] == "0"
    assert result["qb_sack_rate_final_missing"] == "0"
    assert float(result["qb_completion_pct_final"]) == pytest.approx(0.652)
    assert float(result["qb_yards_per_attempt_final"]) == pytest.approx(8.1)
    assert float(result["qb_td_int_ratio_final"]) == pytest.approx(3.75)
    assert float(result["qb_sack_rate_final"]) == pytest.approx(0.04)
    for col in ("qb_completion_pct_final", "qb_yards_per_attempt_final",
                "qb_td_int_ratio_final", "qb_sack_rate_final"):
        assert result[f"{col}_source"] == "cfbd"


def test_compute_qb_cfbd_features_volume_gate_below_100(tmp_path):
    """pass_attempts < 100 → all four QB features set to _missing=1."""
    from unittest.mock import patch as mock_patch

    mock_stats = {
        "completion_pct": 0.60,
        "yards_per_attempt": 7.0,
        "td_int_ratio": 2.0,
        "sack_rate": 0.06,
        "pass_attempts": 45,
    }
    row = {"pfr_player_name": "Backup QB", "college": "Small College",
           "season": "2019", "position": "QB"}
    with mock_patch(
        "scripts.build_w2b_cfbd.fetch_qb_college_stats",
        return_value=mock_stats,
    ):
        result = compute_qb_cfbd_features(row, api_key="test-key", cache_dir=tmp_path)

    for col in ("qb_completion_pct_final", "qb_yards_per_attempt_final",
                "qb_td_int_ratio_final", "qb_sack_rate_final"):
        assert result[f"{col}_missing"] == "1", f"{col} should be _missing=1 below gate"
        assert result[col] == ""
        assert result[f"{col}_source"] == "below_volume_gate"


def test_compute_qb_cfbd_features_player_not_found_dark(tmp_path):
    """Adapter returning all None → all four QB features dark."""
    from unittest.mock import patch as mock_patch

    mock_stats = {
        "completion_pct": None,
        "yards_per_attempt": None,
        "td_int_ratio": None,
        "sack_rate": None,
        "pass_attempts": None,
    }
    row = {"pfr_player_name": "Unknown QB", "college": "Unknown",
           "season": "2018", "position": "QB"}
    with mock_patch(
        "scripts.build_w2b_cfbd.fetch_qb_college_stats",
        return_value=mock_stats,
    ):
        result = compute_qb_cfbd_features(row, api_key="test-key", cache_dir=tmp_path)

    for col in ("qb_completion_pct_final", "qb_yards_per_attempt_final",
                "qb_td_int_ratio_final", "qb_sack_rate_final"):
        assert result[f"{col}_missing"] == "1"


# ── compute_era_proxy_features ────────────────────────────────────────────────

def test_era_proxy_final_college_age():
    """final_college_age = age_at_draft - 1 (proxy; assumes final season = draft_year - 1)."""
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


# ── TPA cache round-trip ──────────────────────────────────────────────────────

def test_tpa_cache_roundtrip_positive(tmp_path, monkeypatch):
    """Positive TPA cache: (True, float) round-trip."""
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path)
    bw2b._save_tpa_cache("Alabama", 2021, 438.0)
    hit, value = bw2b._load_tpa_cache("Alabama", 2021)
    assert hit is True
    assert value == pytest.approx(438.0)


def test_tpa_cache_miss_when_absent(tmp_path, monkeypatch):
    """No cache file → (False, None); caller must fetch from API."""
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path)
    hit, value = bw2b._load_tpa_cache("NoTeam", 2021)
    assert hit is False
    assert value is None


def test_tpa_negative_cache_roundtrip(tmp_path, monkeypatch):
    """Negative TPA cache: (True, None) prevents redundant API re-fetch."""
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path)
    bw2b._save_tpa_cache("FCS School", 2021, None)
    hit, value = bw2b._load_tpa_cache("FCS School", 2021)
    assert hit is True
    assert value is None


# ── Games-count cache round-trip ─────────────────────────────────────────────

def test_games_count_cache_roundtrip_positive(tmp_path, monkeypatch):
    """Positive games-count cache: (True, int) round-trip."""
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path)
    bw2b._save_games_count_cache("Alabama", 2021, 14)
    hit, value = bw2b._load_games_count_cache("Alabama", 2021)
    assert hit is True
    assert value == 14


def test_games_count_cache_miss_when_absent(tmp_path, monkeypatch):
    """No cache file → (False, None); caller must fetch from API."""
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path)
    hit, value = bw2b._load_games_count_cache("NoTeam", 2021)
    assert hit is False
    assert value is None


def test_games_count_negative_cache_roundtrip(tmp_path, monkeypatch):
    """Negative games-count cache: (True, None) prevents redundant re-fetch."""
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path)
    bw2b._save_games_count_cache("FCS School", 2021, None)
    hit, value = bw2b._load_games_count_cache("FCS School", 2021)
    assert hit is True
    assert value is None


# ── w2b_cfbd_degraded provenance flag ────────────────────────────────────────

def _minimal_v3_csv(path):
    """Write a minimal one-row WR v3 CSV for pipeline tests."""
    path.write_text(
        "season,position,pfr_player_name,college,age_at_draft,age_at_draft_missing\n"
        "2023,WR,Test Player,Alabama,21.0,0\n",
        encoding="utf-8",
    )


def test_w2b_degraded_flag_set_on_fetch_error(monkeypatch, tmp_path):
    """--allow-degraded writes w2b_cfbd_degraded=1 when API calls fail."""
    v3_path = tmp_path / "v3.csv"
    _minimal_v3_csv(v3_path)

    monkeypatch.setattr(bw2b, "V3_CSV", v3_path)
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(bw2b, "_cfbd_api_key", lambda: "test_key")

    def _fail_load(year, category, api_key, force_fetch=False):
        raise ConnectionError("simulated failure")

    def _fail_sp(year, api_key, force_fetch=False):
        raise ConnectionError("simulated failure")

    monkeypatch.setattr(bw2b, "load_player_stats", _fail_load)
    monkeypatch.setattr(bw2b, "load_sp_ratings", _fail_sp)
    monkeypatch.setattr(bw2b, "fetch_team_pass_attempts", lambda *a, **kw: None)

    bw2b.main(allow_degraded=True)

    with v3_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["w2b_cfbd_degraded"] == "1"


def test_w2b_degraded_flag_cleared_on_success(monkeypatch, tmp_path):
    """Successful run writes w2b_cfbd_degraded=0, clearing any stale 1."""
    v3_path = tmp_path / "v3.csv"
    # Pre-stamp with stale degraded=1
    v3_path.write_text(
        "season,position,pfr_player_name,college,age_at_draft,age_at_draft_missing,w2b_cfbd_degraded\n"
        "2023,WR,Test Player,Alabama,21.0,0,1\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(bw2b, "V3_CSV", v3_path)
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(bw2b, "_cfbd_api_key", lambda: "test_key")
    monkeypatch.setattr(bw2b, "load_player_stats", lambda *a, **kw: [])
    monkeypatch.setattr(bw2b, "load_sp_ratings", lambda *a, **kw: [])
    monkeypatch.setattr(bw2b, "fetch_team_pass_attempts", lambda *a, **kw: None)

    bw2b.main(allow_degraded=False)

    with v3_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["w2b_cfbd_degraded"] == "0"


def test_w2b_wr_output_includes_ryptpa_and_yprr_college_stubs(monkeypatch, tmp_path):
    """W2b main() must write 'ryptpa' and 'yprr_college' columns for all WR rows.

    Verifies the downstream bakeoff contract: run_head_a_bakeoff.py and
    run_wr_college_bakeoff.py both consume 'ryptpa' and 'yprr_college'.
    """
    v3_path = tmp_path / "v3.csv"
    v3_path.write_text(
        "season,position,pfr_player_name,college,age_at_draft,age_at_draft_missing\n"
        "2015,WR,Amari Cooper,Alabama,21.0,0\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(bw2b, "V3_CSV", v3_path)
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(bw2b, "_cfbd_api_key", lambda: "test_key")
    monkeypatch.setattr(bw2b, "load_player_stats", lambda *a, **kw: [])
    monkeypatch.setattr(bw2b, "load_sp_ratings", lambda *a, **kw: [])
    monkeypatch.setattr(bw2b, "fetch_team_pass_attempts", lambda *a, **kw: None)

    bw2b.main(allow_degraded=False)

    with v3_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    row = rows[0]
    assert "ryptpa" in row, "W2b must write 'ryptpa' column (not 'wr_ryptpa') for WR rows"
    assert "wr_ryptpa" not in row, "W2b must not emit 'wr_ryptpa'"
    assert "yprr_college" in row, "W2b must write 'yprr_college' stub for WR rows"
    assert row["yprr_college"] == "", "yprr_college must be empty (permanently dark)"
    assert row["yprr_college_missing"] == "1", "yprr_college_missing must be 1"


def test_w2b_mixed_position_csv_writes_all_columns(monkeypatch, tmp_path):
    """W2b main() must write all position-specific columns to all rows (restval='').

    WR-enriched columns like ryptpa/yprr_college must appear in CSV headers so
    non-WR rows can be read by DictReader without KeyError.
    """
    v3_path = tmp_path / "v3.csv"
    v3_path.write_text(
        "season,position,pfr_player_name,college,age_at_draft,age_at_draft_missing\n"
        "2015,WR,Amari Cooper,Alabama,21.0,0\n"
        "2016,RB,Derrick Henry,Alabama,21.9,0\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(bw2b, "V3_CSV", v3_path)
    monkeypatch.setattr(bw2b, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(bw2b, "_cfbd_api_key", lambda: "test_key")
    monkeypatch.setattr(bw2b, "load_player_stats", lambda *a, **kw: [])
    monkeypatch.setattr(bw2b, "load_sp_ratings", lambda *a, **kw: [])
    monkeypatch.setattr(bw2b, "fetch_team_pass_attempts", lambda *a, **kw: None)

    bw2b.main(allow_degraded=False)

    with v3_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # All rows must be readable (no KeyError) — DictWriter used union fieldnames
    wr_row = next(r for r in rows if r["position"] == "WR")
    rb_row = next(r for r in rows if r["position"] == "RB")
    assert "ryptpa" in wr_row
    assert "yprr_college" in wr_row
    # RB row has those columns in the CSV (empty string from restval)
    assert "ryptpa" in rb_row
    assert rb_row["ryptpa"] == ""


# ── Leakage guard ─────────────────────────────────────────────────────────────

def test_w2b_functions_emit_no_draft_capital_columns():
    """W2b compute functions must not emit any HEAD_B_PROHIBITED_COLUMNS."""
    pivot, team_rec, team_td = _make_wr_lookups()
    row = {"pfr_player_name": "Amari Cooper", "college": "Alabama",
           "season": "2015", "age_at_draft": "21.0", "age_at_draft_missing": "0",
           "position": "WR"}
    wr_result = compute_wr_cfbd_features(row, pivot, team_rec, team_td)
    era_result = compute_era_proxy_features(row)
    all_keys = set(wr_result) | set(era_result)
    banned = {k for k in all_keys if k in HEAD_B_PROHIBITED_COLUMNS}
    assert not banned, f"W2b emitted prohibited columns: {banned}"
