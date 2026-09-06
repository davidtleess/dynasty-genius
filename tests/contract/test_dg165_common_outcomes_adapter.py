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

MANIFEST = {
    "artifact": "dg179_common_outcomes_v1",
    "scoring": {"id": "nflverse_default_ppr_league_window_v1",
                "note": "nflverse fantasy_points_ppr as saved; not asserted equal to David's league rules"},
    "window": {"rule": "REG weeks 1-16 through 2020, REG weeks 1-17 from 2021, equal weights",
               "by_season": {"2020": [1, 16], "2021": [1, 17]}},
    "mask": "points, games and appeared share one mask: appeared = games >= 1 within the window",
    "closure": {"labels_through": 2025},
    "source": {"weekly_capture_manifest_sha256": "abc"},
}


def _write(tmp_path, rows, manifest=MANIFEST):
    csv = tmp_path / "common_outcomes.csv"
    pd.DataFrame(rows, columns=["player_id", "season", "points", "games", "appeared"]).to_csv(csv, index=False)
    man = tmp_path / "manifest.json"
    man.write_text(json.dumps(manifest))
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
    assert isinstance(out, CommonOutcomes) and out.labels_through == 2025
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


def test_outcome_binding_records_hashes_scoring_window_and_closure(tmp_path):
    csv, man = _write(tmp_path, [("a", 2020, 100.0, 10, 1)])
    out = load_common_outcomes(csv, man)
    b = outcome_binding(out)
    assert b["artifact"] == "dg179_common_outcomes_v1" and b["scoring_id"] == "nflverse_default_ppr_league_window_v1"
    assert b["labels_through"] == 2025 and "weeks 1-16 through 2020" in b["window_rule"]
    assert len(b["csv_sha256"]) == 64 and len(b["manifest_sha256"]) == 64
    assert b["scoring_caveat"].startswith("nflverse")
