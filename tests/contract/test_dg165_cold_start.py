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


# ---------------------------------------------------------------- Task 2: three-source draft evidence, positively labelled

def _draft_sources():
    picks = pd.DataFrame({"season": [2015, 2015, 2014], "round": [1, 2, 4], "pick": [1, 40, 120],
                          "gsis_id": ["00-A", "00-B", "00-LB"], "position": ["QB", "RB", "LB"], "pfr_player_name": ["Ann", "Bob", "Lou"]})
    players = pd.DataFrame({"gsis_id": ["00-A", "00-B", "00-C", "00-U", "00-LB"], "display_name": ["Ann", "Bob", "Cy", "Uma", "Lou"],
                            "birth_date": ["1993-01-01", "1994-02-02", "1995-03-03", "2003-04-04", "1992-05-05"],
                            "position": ["QB", "RB", "WR", "WR", "LB"], "college_name": ["A U", "B U", "C U", "U U", "L U"],
                            "rookie_season": [2015, 2015, 2017, 2026, 2014], "last_season": [2025, 2025, 2020, 2026, 2020],
                            "years_of_experience": [10, 10, 3, 0, 6],
                            "draft_year": [2015, 2015, None, None, 2014], "draft_round": [1, 2, None, None, 4],
                            "draft_pick": [1, 40, None, None, 120], "draft_team": ["X", "Y", None, None, "Z"]})
    rosters = pd.DataFrame({"season": [2025, 2025, 2020, 2026, 2019, 2026], "week": [1] * 6,
                            "gsis_id": ["00-A", "00-B", "00-C", "00-U", "00-LB", "00-B"], "position": ["QB", "RB", "WR", "WR", "LB", "RB"],
                            "status": ["ACT", "ACT", "ACT", "DEV", "ACT", "ACT"], "birth_date": ["1993-01-01", "1994-02-02", "1995-03-03", "2003-04-04", "1992-05-05", "1994-02-02"],
                            "college": ["A U", "B U", "C U", "U U", "L U", "B U"], "entry_year": [2015, 2015, 2017, 2026, 2014, 2015],
                            "rookie_year": [2015, 2015, 2017, 2026, 2014, 2015], "draft_club": ["X", "Y", None, None, "Z", "Y"],
                            "draft_number": [1, 41, None, None, 120, 41], "years_exp": [10, 10, 3, 0, 5, 11]})
    return picks, players, rosters


def test_draft_evidence_is_positive_only_and_never_says_udfa():
    from src.dynasty_genius.rookie.cold_start import draft_evidence
    picks, players, rosters = _draft_sources()
    ev = draft_evidence(pd.Series(["00-A", "00-B", "00-C", "00-U", "00-LB", "00-ZZ"]), draft_picks=picks, players=players, rosters=rosters)
    by = ev.set_index("gsis_id")
    assert by.loc["00-A", "draft_status"] == "drafted_verified" and by.loc["00-A", "draft_sources_positive"] == 3 and bool(by.loc["00-A", "draft_sources_agree"])
    assert by.loc["00-B", "draft_status"] == "draft_sources_conflict"  # picks/players say 40, rosters says 41
    assert by.loc["00-C", "draft_status"] == "no_draft_record_2_sources"  # present in players + rosters, no draft fields anywhere
    assert by.loc["00-U", "draft_status"] == "no_draft_record_2_sources" and by.loc["00-U", "entry_season"] == 2026
    assert by.loc["00-LB", "draft_status"] == "drafted_verified" and by.loc["00-LB", "draft_position"] == "LB"
    assert by.loc["00-ZZ", "draft_status"] == "unknown_identity"
    assert by.loc["00-A", "draft_season"] == 2015 and by.loc["00-A", "draft_pick"] == 1 and by.loc["00-A", "draft_round"] == 1
    assert by.loc["00-C", "college"] == "C U" and by.loc["00-C", "birth_date"] == "1995-03-03" and by.loc["00-C", "age_2026"] == pytest.approx(31.5, abs=0.1)
    joined = " ".join(ev["draft_status"].astype(str)).lower()
    assert "udfa" not in joined and "undrafted" not in joined
