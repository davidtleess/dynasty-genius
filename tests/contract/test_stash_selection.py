"""DG-177 stash-selection evaluation: contract tests on synthetic ids (P1, P2, ...). No names, no real data."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.dynasty_genius.eval import stash_selection as ss

DEFS = json.loads(Path("docs/experiments/stash_selection_definitions_v1.json").read_text())


# ── Task 1: frozen definitions ────────────────────────────────────────────────────────────────

def test_definitions_file_is_frozen_complete_and_hashed():
    d = ss.load_definitions(Path("docs/experiments/stash_selection_definitions_v1.json"))
    assert d["version"] == ss.DEFINITIONS_VERSION and d["frozen_before_first_result"] is True
    assert set(ss.REQUIRED_DEFINITION_KEYS) <= set(d)
    assert len(d["_file"]["sha256"]) == 64 and d["_file"]["bytes"] > 0
    assert d["low_production"]["starter_slots"] == {"QB": 24, "RB": 36, "WR": 48, "TE": 18}
    assert d["outcome"]["horizons"] == [1, 2, 3] and d["metrics"]["budgets_per_position_per_origin"] == [2, 4, 8]


def test_definitions_loader_refuses_a_file_missing_a_required_section(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"version": ss.DEFINITIONS_VERSION, "frozen_before_first_result": True}))
    with pytest.raises(ss.StashSelectionError, match="outcome"):
        ss.load_definitions(p)


# ── shared fixtures ───────────────────────────────────────────────────────────────────────────

def cohort_row(player_id, season, *, position="WR", total_points_t=50.0, ppg_t=5.0, games_t=10, age=24, seasons_played=1, **over):
    row = {"player_id": player_id, "feature_season": season, "position": position, "total_points_t": total_points_t, "ppg_t": ppg_t,
           "games_t": games_t, "age": age, "seasons_played": seasons_played}
    row.update(over)
    return row


def outcome_row(player_id, season, points, games=None, appeared=None):
    games = int(round(points / 10)) if games is None else games
    return {"player_id": player_id, "season": season, "points": points, "games": games,
            "appeared": (games >= 1) if appeared is None else appeared}


def draft_row(gsis_id, season, rnd, pick, position="WR"):
    return {"gsis_id": gsis_id, "season": season, "round": rnd, "pick": pick, "position": position}


SLOTS = {"QB": 24, "RB": 36, "WR": 48, "TE": 18}
SMALL_SLOTS = {"WR": 2, "RB": 2, "QB": 2, "TE": 2}


# ── Task 2: starter lines and the candidate cohort ───────────────────────────────────────────

def test_starter_line_is_the_nth_highest_window_points_with_absent_rows_as_zero():
    cohort = pd.DataFrame([cohort_row(p, 2015) for p in ("P1", "P2", "P3", "P4")])
    outcomes = pd.DataFrame([outcome_row("P1", 2015, 200.0), outcome_row("P2", 2015, 120.0), outcome_row("P3", 2015, 30.0)])  # P4 absent
    lines = ss.starter_lines(cohort, outcomes, slots=SMALL_SLOTS).set_index(["position", "season"])
    assert lines.loc[("WR", 2015), "line_points"] == 120.0 and lines.loc[("WR", 2015), "rows_in_cell"] == 4
    half = ss.starter_lines(cohort, outcomes, slots=SMALL_SLOTS, multiplier=0.5).set_index(["position", "season"])
    assert half.loc[("WR", 2015), "slots"] == 1 and half.loc[("WR", 2015), "line_points"] == 200.0


def test_cell_with_fewer_rows_than_slots_has_line_zero_and_is_disclosed():
    cohort = pd.DataFrame([cohort_row("P1", 2015)])
    lines = ss.starter_lines(cohort, pd.DataFrame([outcome_row("P1", 2015, 10.0)]), slots=SMALL_SLOTS)
    assert lines.iloc[0].line_points == 0.0 and lines.iloc[0].rows_in_cell == 1 and bool(lines.iloc[0].short_cell) is True


def test_candidates_are_below_the_origin_line_and_within_the_observed_history_stratum():
    cohort = pd.DataFrame([cohort_row("P1", 2015, seasons_played=1), cohort_row("P2", 2015, seasons_played=1),
                           cohort_row("P3", 2015, seasons_played=1), cohort_row("P4", 2015, seasons_played=4)])
    outcomes = pd.DataFrame([outcome_row("P1", 2015, 200.0), outcome_row("P2", 2015, 120.0), outcome_row("P3", 2015, 30.0)])
    c = ss.candidates(cohort, outcomes, pd.DataFrame(columns=["gsis_id", "season", "round", "pick"]), definitions=DEFS,
                      slots=SMALL_SLOTS)
    assert c.player_id.tolist() == ["P3"]                                    # P1/P2 at or above the line; P4 too many observed seasons
    row = c.iloc[0]
    assert row.origin_points == 30.0 and row.origin_label_source == "artifact_row" and row.origin_line == 120.0
    assert row.observed_history_seasons == 1
    no_cut = ss.candidates(cohort, outcomes, pd.DataFrame(columns=["gsis_id", "season", "round", "pick"]), definitions=DEFS,
                           slots=SMALL_SLOTS, max_observed_history_seasons=None)
    assert sorted(no_cut.player_id) == ["P3", "P4"]


def test_absent_origin_outcome_is_no_record_zero_and_counts_as_low_production():
    cohort = pd.DataFrame([cohort_row("P1", 2015), cohort_row("P2", 2015), cohort_row("P5", 2015)])
    outcomes = pd.DataFrame([outcome_row("P1", 2015, 200.0), outcome_row("P2", 2015, 120.0)])
    c = ss.candidates(cohort, outcomes, pd.DataFrame(columns=["gsis_id", "season", "round", "pick"]), definitions=DEFS, slots=SMALL_SLOTS)
    assert c.player_id.tolist() == ["P5"] and c.iloc[0].origin_label_source == "no_record_zero" and c.iloc[0].origin_points == 0.0


def test_draft_facts_are_visible_only_when_the_draft_season_is_at_or_before_the_origin():
    cohort = pd.DataFrame([cohort_row("P1", 2015), cohort_row("P2", 2015), cohort_row("P3", 2015), cohort_row("P6", 2015)])
    outcomes = pd.DataFrame([outcome_row("P1", 2015, 200.0), outcome_row("P2", 2015, 120.0), outcome_row("P3", 2015, 30.0),
                             outcome_row("P6", 2015, 20.0)])
    draft = pd.DataFrame([draft_row("P3", 2014, 2, 40), draft_row("P6", 2016, 1, 3)])
    c = ss.candidates(cohort, outcomes, draft, definitions=DEFS, slots=SMALL_SLOTS).set_index("player_id")
    assert bool(c.loc["P3", "draft_visible"]) is True and c.loc["P3", "draft_pick"] == 40 and c.loc["P3", "nfl_years_since_draft"] == 2
    assert bool(c.loc["P6", "draft_visible"]) is False and pd.isna(c.loc["P6", "draft_pick"]) and pd.isna(c.loc["P6", "nfl_years_since_draft"])


def test_origins_outside_the_frozen_range_or_positions_are_refused_or_excluded():
    cohort = pd.DataFrame([cohort_row("P1", 2009), cohort_row("P2", 2015, position="K")])
    with pytest.raises(ss.StashSelectionError, match="origin"):
        ss.candidates(cohort, pd.DataFrame(columns=["player_id", "season", "points", "games", "appeared"]),
                      pd.DataFrame(columns=["gsis_id", "season", "round", "pick"]), definitions=DEFS, slots=SMALL_SLOTS)
