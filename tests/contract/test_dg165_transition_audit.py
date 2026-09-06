"""Contract tests for the rookie -> veteran transition audit (DG-165, build released 2026-09-06).

Fixtures are two tiny synthetic frozen runs with the same shapes as
runs/20260906T195904Z/dg165_rookie_capital and DG-177's dg177_basic_horizons.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

TARGET = "0" * 64
CSV_SHA = "1" * 64
MAN_SHA = "2" * 64
PRESET = "nflverse_default_ppr_championship_window_v1"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha(data)


def make_rookie_run(root: Path, *, oot: pd.DataFrame | None = None, cohort: pd.DataFrame | None = None,
                    target: str = TARGET) -> Path:
    run = root / "rookie"
    run.mkdir(parents=True)
    if cohort is None:
        cohort = pd.DataFrame({
            # 4 drafted skill players in class 2015 + one unresolved identity
            "gsis_id": ["00-A", "00-B", "00-C", "00-D", "unresolved:2015:250"],
            "draft_season": [2015, 2015, 2015, 2015, 2015],
            "position": ["QB", "RB", "WR", "TE", "WR"],
            "pick": [1, 40, 90, 150, 250],
            "round": [1, 2, 3, 5, 7],
            "age_at_draft": [22.0, 21.5, 22.3, 23.0, np.nan],
            "team": ["X"] * 5,
            "name": ["Ann", "Bob", "Cy", "Dee", "Eve"],
            # real label_basis values are the SOURCE that resolved the identity; only "unresolved" is unknown
            "label_basis": ["nflverse_gsis", "players:name+year", "nflverse_gsis", "rosters:entry_year+draft_number", "unresolved"],
            "position_current": ["QB", "RB", "WR", "TE", None],
        })
    if oot is None:
        oot = pd.DataFrame({
            "gsis_id": ["00-A", "00-B", "00-C", "00-D"],
            "draft_season": [2015] * 4, "position": ["QB", "RB", "WR", "TE"],
            "pick": [1, 40, 90, 150], "round": [1, 2, 3, 5], "age_at_draft": [22.0, 21.5, 22.3, 23.0],
            "team": ["X"] * 4, "name": ["Ann", "Bob", "Cy", "Dee"],
            "label_basis": ["nflverse_gsis", "players:name+year", "nflverse_gsis", "rosters:entry_year+draft_number"],
            "position_current": ["QB", "RB", "WR", "TE"],
            "forecast_year": [2015] * 4,
            # season-1 labels: Dee never appeared in the window
            "appear_1": [1.0, 1.0, 1.0, 0.0], "points_1": [200.0, 100.0, 50.0, 0.0], "games_1": [16.0, 12.0, 8.0, 0.0],
            # season-2 labels (target for k=1)
            "appear_2": [1.0, 1.0, 1.0, 0.0], "points_2": [250.0, 90.0, 40.0, 0.0], "games_2": [17.0, 10.0, 6.0, 0.0],
            "appear_3": [1.0, 1.0, np.nan, 0.0], "points_3": [240.0, 80.0, np.nan, 0.0], "games_3": [16.0, 9.0, np.nan, 0.0],
            "p_appear_year2": [0.95, 0.85, 0.70, 0.40], "e_points_year2": [230.0, 100.0, 60.0, 20.0],
            "e_points_year2_given_appear": [242.1, 117.6, 85.7, 50.0], "e_games_year2": [15.0, 11.0, 8.0, 4.0],
            "p_appear_year3": [0.93, 0.80, 0.65, 0.35], "e_points_year3": [225.0, 95.0, 55.0, 18.0],
            "e_points_year3_given_appear": [241.9, 118.8, 84.6, 51.4], "e_games_year3": [14.0, 10.0, 7.0, 3.0],
        })
    hashes = {}
    hashes["cohort.csv"] = _write(run / "cohort.csv", cohort.to_csv(index=False).encode())
    hashes["out_of_time_predictions.csv"] = _write(run / "out_of_time_predictions.csv", oot.to_csv(index=False).encode())
    picks = pd.DataFrame({
        # raw draft table covers 1980-2026; the modelling cohort starts at 2001, so a 1998 WR is a
        # drafted skill player OUTSIDE cohort coverage, not "drafted at another position"
        "season": [2015, 2015, 2015, 2015, 2015, 2014, 1998],
        "round": [1, 2, 3, 5, 7, 4, 3], "pick": [1, 40, 90, 150, 250, 120, 70],
        "gsis_id": ["00-A", "00-B", "00-C", "00-D", None, "00-LB", "00-OLD"],
        "position": ["QB", "RB", "WR", "TE", "WR", "LB", "WR"],
        "pfr_player_name": ["Ann", "Bob", "Cy", "Dee", "Eve", "Lou", "Old"],
    })
    (run / "inputs").mkdir()
    picks.to_parquet(run / "inputs" / "nflverse_draft_picks.parquet", index=False)
    picks_sha = _sha((run / "inputs" / "nflverse_draft_picks.parquet").read_bytes())
    manifest = {
        "model_version": "dg165_rookie_capital_v3_chain", "git_sha": "deadbeef",
        "scoring_arm_id": "dg165_rookie_capital_v3_chain:inner_menu:trend",
        "forecast_date": {"forecast_year": 2026, "labels_through": 2025, "last_completed_season": 2025},
        "outcomes": {"target_identity": target, "csv_sha256": CSV_SHA, "manifest_sha256": MAN_SHA, "scoring_preset": PRESET},
        "inputs": {"nflverse_draft_picks": {"path": "inputs/nflverse_draft_picks.parquet", "sha256": picks_sha, "rows": len(picks)}},
        "outputs_sha256": hashes,
    }
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return run


def make_veteran_run(root: Path, *, hist: pd.DataFrame | None = None, cohort: pd.DataFrame | None = None,
                     target: str = TARGET) -> Path:
    run = root / "veteran"
    run.mkdir(parents=True)
    if hist is None:
        # horizon-1 rows at feature season 2015 (= rookie season of class 2015) for A, B, C;
        # D has no row (never appeared); an undrafted player U and a drafted linebacker LB also have rows.
        hist = pd.DataFrame({
            "horizon": [1, 1, 1, 1, 1, 1, 1],
            "player_id": ["00-B", "00-A", "00-C", "00-U", "00-LB", "00-A", "00-B"],
            "position": ["RB", "QB", "WR", "WR", "RB", "QB", "RB"],
            "feature_season": [2015, 2015, 2015, 2015, 2015, 2016, 2016],
            "forecast_season": [2016, 2016, 2016, 2016, 2016, 2017, 2017],
            "policy_p_appear_year1": [0.90, 0.97, 0.75, 0.5, 0.5, 0.96, 0.88],
            "policy_e_points_year1_given_appear": [111.1, 247.4, 66.7, 40.0, 40.0, 250.0, 100.0],
            "policy_e_games_year1_given_appear": [12.0, 16.0, 9.0, 8.0, 8.0, 15.0, 11.0],
            "policy_e_points_year1": [100.0, 240.0, 50.0, 20.0, 20.0, 240.0, 88.0],
            "policy_e_games_year1": [10.8, 15.5, 6.75, 4.0, 4.0, 14.4, 9.7],
            "appeared_year1": [1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0],
            "games_year1": [10.0, 17.0, 6.0, 5.0, 0.0, 16.0, 9.0],
            "points_year1": [90.0, 250.0, 40.0, 30.0, 0.0, 240.0, 80.0],
        })
    if cohort is None:
        cohort = pd.DataFrame({
            "player_id": ["00-A", "00-B", "00-C", "00-U", "00-LB", "00-A", "00-B"],
            "feature_season": [2015, 2015, 2015, 2015, 2015, 2016, 2016],
            "position": ["QB", "RB", "WR", "WR", "RB", "QB", "RB"],
            "identity_status": ["resolved"] * 7,
            "games_t": [16.0, 12.0, 3.0, 4.0, 1.0, 17.0, 10.0],
            "seasons_played": [1, 1, 1, 1, 1, 2, 2],
        })
    hashes = {}
    hashes["historical_predictions.csv"] = _write(run / "historical_predictions.csv", hist.to_csv(index=False).encode())
    gz = gzip.compress(cohort.to_csv(index=False).encode(), mtime=0)
    hashes["basic_cohort.csv.gz"] = _write(run / "basic_cohort.csv.gz", gz)
    manifest = {
        "producer": "DG-177 veteran annual forecast candidate (report-only)", "candidate_arm": "basic_cohort_3col_plus_lags",
        "git_head": "cafebabe", "last_complete_season": 2025,
        "label_source": {"kind": "common_outcome_artifact", "target_identity": target, "csv_sha256": CSV_SHA,
                         "manifest_sha256": MAN_SHA, "scoring_preset": PRESET},
        "forecast_cutoff": {"rule": "features observed through the feature season; a year-j label trains only when "
                                    "feature_season + j <= last complete season"},
        "outputs_sha256": hashes,
    }
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return run


@pytest.fixture
def runs(tmp_path):
    return make_rookie_run(tmp_path), make_veteran_run(tmp_path)


# ---------------------------------------------------------------- Task 1: verified loaders, same target

def test_rookie_loader_verifies_every_declared_byte(runs):
    from src.dynasty_genius.rookie.transition_audit import load_rookie_run
    rookie_dir, _ = runs
    loaded = load_rookie_run(rookie_dir)
    assert set(loaded.verified) >= {"cohort.csv", "out_of_time_predictions.csv", "inputs/nflverse_draft_picks.parquet"}
    assert len(loaded.cohort) == 5 and len(loaded.out_of_time) == 4 and len(loaded.draft_picks) == 7


def test_rookie_loader_refuses_altered_bytes(runs):
    from src.dynasty_genius.rookie.transition_audit import load_rookie_run
    rookie_dir, _ = runs
    path = rookie_dir / "out_of_time_predictions.csv"
    path.write_text(path.read_text().replace("250.0", "251.0", 1))
    with pytest.raises(ValueError, match="sha256"):
        load_rookie_run(rookie_dir)


def test_veteran_loader_refuses_missing_declaration(runs):
    from src.dynasty_genius.rookie.transition_audit import load_veteran_run
    _, vet_dir = runs
    m = json.loads((vet_dir / "manifest.json").read_text())
    del m["outputs_sha256"]["basic_cohort.csv.gz"]
    (vet_dir / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="basic_cohort.csv.gz"):
        load_veteran_run(vet_dir)


def test_same_target_is_asserted_not_assumed(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        load_veteran_run,
        verify_same_target,
    )
    r = load_rookie_run(make_rookie_run(tmp_path))
    v = load_veteran_run(make_veteran_run(tmp_path, target="f" * 64))
    with pytest.raises(ValueError, match="target_identity"):
        verify_same_target(r, v)
    v2 = load_veteran_run(make_veteran_run(tmp_path / "again"))
    block = verify_same_target(r, v2)
    assert block["status"] == "same_target" and block["target_identity"] == TARGET


# ---------------------------------------------------------------- Task 2: draft status

def test_draft_status_distinguishes_drafted_no_record_and_unknown(runs):
    from src.dynasty_genius.rookie.transition_audit import (
        classify_draft_status,
        load_rookie_run,
    )
    rookie_dir, _ = runs
    r = load_rookie_run(rookie_dir)
    ids = pd.Series(["00-A", "00-B", "00-LB", "00-OLD", "00-U", "00-Z", "unresolved:2015:250"])
    status = pd.Series(["resolved", "resolved", "resolved", "resolved", "resolved", "unresolved_in_source", "resolved"])
    out = classify_draft_status(ids, status, r)
    # A resolved by nflverse_gsis and B by players:name+year are BOTH drafted skill players; the 1998 WR is a
    # drafted skill player outside cohort coverage (raw draft position classified positively); absence from the
    # draft table is "no draft record", never positive undrafted evidence.
    assert out.tolist() == ["drafted_skill", "drafted_skill", "drafted_other_position", "drafted_skill_outside_cohort",
                            "no_draft_record", "unknown_identity", "drafted_skill_unresolved"]
