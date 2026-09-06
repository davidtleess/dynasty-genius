"""DG-165 — adapter for Codex's common player-season outcome artifact (DG-179).

Synthetic frames only. What each test would catch:
* a loader that accepts an artifact whose appearance mask disagrees with its games, or that
  carries duplicate or id-less rows (fail closed, never repair);
* season stats built from rows that did not appear (points must come only from the one mask);
* a cohort player ranked at his current NFL position instead of his draft role, or an
  offensive player dropped because his current position string is defensive;
* a run that does not bind the outcome artifact's hashes, scoring id, window and closure.
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from src.dynasty_genius.rookie.outcomes import (
    CommonOutcomes,
    load_common_outcomes,
    outcome_binding,
    qualification_panel,
    season_stats_from_outcomes,
)

SCHEMA = "dg179_league_season_outcomes_v1"


def _manifest(csv_bytes: bytes, **overrides) -> dict:
    """The implemented DG-179 manifest shape (read from Codex's module 2026-09-06)."""
    m = {
        "schema_version": SCHEMA,
        "scoring_preset": "nflverse_default_ppr_championship_window_v1",
        "league_scoring_exact": False,
        "saved_league_scoring_settings": {"rec": 1.0}, "saved_league_scoring_sha256": "c" * 64,
        "exact_league_scoring_gaps": {"fum_lost": "not established"},
        "scoring_rule": "Sum supplied fantasy_points_ppr; no component rescoring or generator-equivalence claim.",
        "window_rule": "Equal-weight REG stat records in weeks 1-16 through 2020 and weeks 1-17 from 2021; POST records do not contribute outcomes.",
        "season_windows": {"2020": {"included_reg_weeks": list(range(1, 17)), "excluded_final_reg_week": 17, "expected_full_reg_weeks": list(range(1, 18)), "weekly_weight": 1.0},
                           "2021": {"included_reg_weeks": list(range(1, 18)), "excluded_final_reg_week": 18, "expected_full_reg_weeks": list(range(1, 19)), "weekly_weight": 1.0}},
        "exposure_definition": "unique stat_record weeks within the outcome window",
        "appearance_definition": "At least one stat record inside the identical points/games window.",
        "zero_definition": "Identified full-source player-season with no in-window stat record; never a fabricated unknown pair.",
        "last_complete_season": 2021,
        "coverage_status": "qualified_research_game_complete_identified_rows",
        "source_validation": {"seasons": {"2020": {"reg_players": 600}, "2021": {"reg_players": 600}}},
        "source_validation_limitations": "not proof that no individual record was omitted",
        "source_identity": {"sha256": "d" * 64, "source_preparation": {"schema_version": "dg179_source_preparation_v1"}},
        "source_identity_sha256": "e" * 64,
        "scoring_identity": "f" * 64, "window_identity": "1" * 64, "target_identity": "2" * 64,
        "outputs": {"outcomes.csv": {"sha256": hashlib.sha256(csv_bytes).hexdigest(), "bytes": len(csv_bytes)}},
        "outcome_rows": csv_bytes.count(b"\n") - 1,
    }
    m.update(overrides)
    return m


def _write(tmp_path, rows, **overrides):
    csv = tmp_path / "outcomes.csv"
    frame = pd.DataFrame(rows, columns=["player_id", "season", "points", "games", "appeared"])
    frame["appeared"] = frame["appeared"].map(lambda v: "True" if v in (1, True) else "False")   # the artifact writes booleans
    csv.write_text(frame.to_csv(index=False, lineterminator="\n"))
    man = tmp_path / "manifest.json"
    man.write_text(json.dumps(_manifest(csv.read_bytes(), **overrides)))
    return csv, man


def test_loader_refuses_a_mask_that_disagrees_duplicates_and_idless_rows(tmp_path):
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 0, 1)])
    with pytest.raises(ValueError, match="mask"):
        load_common_outcomes(csv, man)
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 10, 1), ("a", 2020, 90.0, 9, 1)])
    with pytest.raises(ValueError, match="duplicate"):
        load_common_outcomes(csv, man)
    csv, man = _write(tmp_path, [(None, 2020, 6.0, 1, 1)])
    with pytest.raises(ValueError, match="player_id"):
        load_common_outcomes(csv, man)


def test_season_stats_come_only_from_appeared_rows_and_points_are_never_filled(tmp_path):
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 10, 1), ("b", 2020, 0.0, 0, 0), ("c", 2021, None, 3, 1)])
    out = load_common_outcomes(csv, man)
    assert isinstance(out, CommonOutcomes) and out.labels_through == 2021
    stats = season_stats_from_outcomes(out)
    assert stats[("a", 2020)] == (100.0, 10)
    assert ("b", 2020) not in stats                       # did not appear → absent, the measured zero
    assert ("c", 2021) in stats and stats[("c", 2021)][1] == 3 and stats[("c", 2021)][0] != stats[("c", 2021)][0]  # NaN kept


def test_qualification_panel_ranks_cohort_players_at_their_draft_role_and_others_at_weekly_position(tmp_path):
    csv, man = _write(tmp_path, [("te_now_fb", 2021, 120.0, 12, 1), ("vet", 2021, 200.0, 17, 1),
                                 ("nopos", 2021, 50.0, 5, 1), ("db_now", 2021, 80.0, 8, 1)])
    out = load_common_outcomes(csv, man)
    weekly_positions = {("te_now_fb", 2021): "FB", ("vet", 2021): "WR", ("db_now", 2021): "DB"}
    draft_roles = {"te_now_fb": "TE", "db_now": "WR"}   # an offensive draftee now listed defensive stays offensive
    panel, report = qualification_panel(out, weekly_positions=weekly_positions, draft_roles=draft_roles)
    got = panel.set_index("player_id")
    assert got.loc["te_now_fb", "position"] == "TE" and got.loc["vet", "position"] == "WR" and got.loc["db_now", "position"] == "WR"
    assert "nopos" not in got.index and report["rows_without_position"] == 1
    assert list(panel.columns) == ["player_id", "position", "season", "points", "games"]


def test_outcome_binding_records_identities_hashes_window_coverage_and_the_caveats(tmp_path):
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 10, 1)])
    out = load_common_outcomes(csv, man)
    b = outcome_binding(out)
    assert b["schema_version"] == SCHEMA and b["scoring_preset"] == "nflverse_default_ppr_championship_window_v1"
    assert b["league_scoring_exact"] is False and b["coverage_status"] == "qualified_research_game_complete_identified_rows"
    assert b["labels_through"] == 2021 and "weeks 1-16 through 2020" in b["window_rule"] and b["covered_seasons"] == [2020, 2021]
    assert b["target_identity"] == "2" * 64 and b["scoring_identity"] == "f" * 64 and b["window_identity"] == "1" * 64
    assert b["source_identity_sha256"] == "e" * 64 and len(b["csv_sha256"]) == 64 and len(b["manifest_sha256"]) == 64
    assert b["exposure_definition"] == "unique stat_record weeks within the outcome window"
    assert "not proof" in b["qualification_note"].lower() and b["scoring_caveat"].startswith("nflverse")


def test_loader_refuses_another_schema_a_hash_mismatch_or_an_exact_league_claim(tmp_path):
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 10, 1)], schema_version="something_else")
    with pytest.raises(ValueError, match="schema_version"):
        load_common_outcomes(csv, man)
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 10, 1)])
    csv.write_text(csv.read_text() + "b,2020,1.0,1,True\n")   # bytes no longer match the declared hash
    with pytest.raises(ValueError, match="sha256"):
        load_common_outcomes(csv, man)
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 10, 1)], league_scoring_exact=True)
    with pytest.raises(ValueError, match="league_scoring_exact"):
        load_common_outcomes(csv, man)
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 10, 1)], coverage_status="made_up")
    with pytest.raises(ValueError, match="coverage_status"):
        load_common_outcomes(csv, man)


def test_weekly_positions_are_the_reg_season_mode_per_player_season_and_missing_stays_missing():
    from src.dynasty_genius.rookie.outcomes import weekly_positions_by_player_season

    weekly = pd.DataFrame({
        "player_id": ["a", "a", "a", "b", "c", None], "season": [2021, 2021, 2021, 2021, 2021, 2021],
        "week": [1, 2, 3, 1, 1, 4], "season_type": ["REG", "REG", "POST", "REG", "REG", "REG"],
        "position": ["TE", "FB", "FB", "WR", None, None],
    })
    got = weekly_positions_by_player_season(weekly)
    assert got[("a", 2021)] == "TE" or got[("a", 2021)] == "FB"   # a tie over REG weeks resolves deterministically
    assert got[("a", 2021)] == weekly_positions_by_player_season(weekly)[("a", 2021)]
    assert got[("b", 2021)] == "WR" and ("c", 2021) not in got     # no position → absent, never guessed
    assert all(k[0] is not None for k in got)


def test_outcome_inputs_bind_the_artifact_and_cut_the_bar_on_the_common_outcomes(tmp_path):
    from src.dynasty_genius.rookie.outcomes import outcome_inputs

    rows = [("r1", 2021, 300.0, 16, 1), ("v1", 2021, 250.0, 16, 1), ("v2", 2021, 100.0, 10, 1), ("v3", 2021, 40.0, 4, 1),
            ("gone", 2021, 0.0, 0, 0)]
    csv, man = _write(tmp_path, rows)
    cohort = pd.DataFrame({"gsis_id": ["r1", "gone"], "draft_season": [2021, 2021], "position": ["WR", "RB"]})
    weekly_positions = {("v1", 2021): "WR", ("v2", 2021): "WR", ("v3", 2021): "WR", ("r1", 2021): "CB"}  # r1 listed CB now
    inputs = outcome_inputs(csv, man, cohort=cohort, weekly_positions=weekly_positions, bar={"WR": 2, "RB": 1, "QB": 1, "TE": 1},
                            require_positions=("WR",))
    assert inputs.labels_through == 2021 and inputs.binding["scoring_preset"] == "nflverse_default_ppr_championship_window_v1"
    assert ("r1", 2021) in inputs.qualifying and ("v1", 2021) in inputs.qualifying and ("v2", 2021) not in inputs.qualifying
    assert inputs.season_stats[("r1", 2021)] == (300.0, 16) and ("gone", 2021) not in inputs.season_stats
    assert inputs.panel_report["ranked_at_draft_role"] == 1
