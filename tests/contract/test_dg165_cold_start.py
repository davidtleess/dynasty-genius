"""Contract tests for the unowned cold-start coverage tool (DG-165, available-players build 2026-09-06).

Fixtures are a tiny synthetic census run (the shape of DG-178's dg178_current_census) and a tiny accepted
report (the shape of dg178_audit/report.json's comparable_board + current_census blocks).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_census_run(root: Path, *, census: pd.DataFrame | None = None) -> Path:
    run = root / "census"
    run.mkdir(parents=True)
    if census is None:
        census = pd.DataFrame({
            "sleeper_id": ["1", "2", "3", "4", "5", "6", "7"],
            "name": ["Owned Vet", "Active NoFc", "PS NoFc", "IR HasFc", "Cut NoFc", "Active HasFc", "Unknown"],
            "league_position": ["WR", "QB", "RB", "TE", "WR", "WR", "TE"],
            "fantasy_positions": ["WR", "QB", "RB", "TE", "WR", "WR", "TE"],
            "sleeper_status": ["Active"] * 7, "sleeper_team": ["A"] * 7,
            "sleeper_gsis_id": [None, "00-B", None, "00-D", None, "00-F", None],
            "nfl_team": ["A", "B", "C", "D", None, "F", None], "nfl_position": ["WR", "QB", "RB", "TE", None, "WR", None],
            "nfl_status_raw": ["ACT", "ACT", "DEV", "RES", None, "ACT", None],
            "nfl_gsis_id": ["00-A", "00-B", "00-C", "00-D", None, "00-F", None],
            "availability_class": ["active", "active", "practice_squad", "injured_reserve", "cut", "active", "unknown"],
            "join_basis": ["sleeper_id"] * 6 + ["none"], "identity_conflict": [False] * 7,
            "league_owned": [True, False, False, False, False, False, False],
            "roster_id": [3, None, None, None, None, None, None],
            "contested_nfl_gsis_id": [None] * 7,
        })
    uncovered = pd.DataFrame({"sleeper_id": ["99"], "name": ["Nobody"], "league_position": ["WR"], "sleeper_status": ["Inactive"],
                              "sleeper_team": [None], "sleeper_gsis_id": [None], "reason": ["not_listed"]})
    cb = census.to_csv(index=False).encode()
    ub = uncovered.to_csv(index=False).encode()
    (run / "census.csv").write_bytes(cb)
    (run / "uncovered.csv").write_bytes(ub)
    report = {"run": "20260906T000000Z", "season": 2026, "census_csv_sha256": _sha(cb), "uncovered_csv_sha256": _sha(ub),
              "counts": {"members": len(census)}, "sources": {}}
    (run / "report.json").write_text(json.dumps(report, sort_keys=True))
    return run


def make_accepted_report(root: Path, census_dir: Path, *, coverage: dict | None = None) -> Path:
    rows = [{"player_id": "00-A", "sleeper_id": "1", "name": "Owned Vet", "position": "WR", "producer": "vet"},
            {"player_id": "00-D", "sleeper_id": "4", "name": "IR HasFc", "position": "TE", "producer": "vet"},
            {"player_id": "00-F", "sleeper_id": "6", "name": "Active HasFc", "position": "WR", "producer": "vet"}]
    census_sha = json.loads((census_dir / "report.json").read_text())["census_csv_sha256"]
    # the real report's coverage block: listed_unowned.by_position[position][class]{with_forecast, without_forecast}
    if coverage is None:
        coverage = {"listed_unowned": {"by_position": {
            "QB": {"active": {"with_forecast": 0, "without_forecast": 1}},
            "RB": {"practice_squad": {"with_forecast": 0, "without_forecast": 1}},
            "TE": {"injured_reserve": {"with_forecast": 1, "without_forecast": 0}, "unknown": {"with_forecast": 0, "without_forecast": 1}},
            "WR": {"active": {"with_forecast": 1, "without_forecast": 0}, "cut": {"with_forecast": 0, "without_forecast": 1}},
        }}}
    report = {"run": "20260906T000001Z", "comparable_board": {"all_inspectable": rows},
              "current_census": {"census_csv_sha256": census_sha, "coverage": coverage}}
    root.mkdir(parents=True, exist_ok=True)
    path = root / "accepted_report.json"
    path.write_text(json.dumps(report, sort_keys=True))
    return path


# ---------------------------------------------------------------- Task 1: loaders + default-pool reconciliation

def test_census_loader_verifies_bytes_and_unique_ids(tmp_path):
    from src.dynasty_genius.rookie.cold_start import load_census_run
    run = make_census_run(tmp_path)
    c = load_census_run(run)
    assert len(c.census) == 7 and c.census_sha256 == json.loads((run / "report.json").read_text())["census_csv_sha256"]
    (run / "census.csv").write_text((run / "census.csv").read_text().replace("Owned Vet", "Owned Vet!"))
    with pytest.raises(ValueError, match="sha256"):
        load_census_run(run)


def test_missing_default_pool_reconciles_with_the_accepted_report(tmp_path):
    from src.dynasty_genius.rookie.cold_start import (
        load_accepted_report,
        load_census_run,
        missing_default_pool,
    )
    census = load_census_run(make_census_run(tmp_path))
    accepted = load_accepted_report(make_accepted_report(tmp_path, tmp_path / "census"))
    miss = missing_default_pool(census, accepted)
    assert miss["name"].tolist() == ["Active NoFc", "PS NoFc"]  # cut and unknown are NOT in the default pool; owned excluded
    bad_cov = {"listed_unowned": {"by_position": {
        "QB": {"active": {"with_forecast": 0, "without_forecast": 2}},  # the report claims two missing QBs; the census has one
        "RB": {"practice_squad": {"with_forecast": 0, "without_forecast": 1}},
        "TE": {"injured_reserve": {"with_forecast": 1, "without_forecast": 0}},
        "WR": {"active": {"with_forecast": 1, "without_forecast": 0}},
    }}}
    bad = load_accepted_report(make_accepted_report(tmp_path / "b", tmp_path / "census", coverage=bad_cov))
    with pytest.raises(ValueError, match="reconcile"):
        missing_default_pool(census, bad)


def test_accepted_report_must_describe_the_same_census(tmp_path):
    from src.dynasty_genius.rookie.cold_start import (
        load_accepted_report,
        load_census_run,
        missing_default_pool,
    )
    census = load_census_run(make_census_run(tmp_path))
    other = make_census_run(tmp_path / "other", census=pd.read_csv(tmp_path / "census" / "census.csv").iloc[:6])
    accepted = load_accepted_report(make_accepted_report(tmp_path / "x", other))  # written against a different census
    with pytest.raises(ValueError, match="census"):
        missing_default_pool(census, accepted)
