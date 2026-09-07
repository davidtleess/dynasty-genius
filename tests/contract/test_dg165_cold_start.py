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
    # the real census report declares ONLY census_csv_sha256 and carries the uncovered rows inline; the accepted
    # report declares uncovered_csv_sha256 (see make_accepted_report)
    report = {"run": "20260906T000000Z", "season": 2026, "census_csv_sha256": _sha(cb), "uncovered": uncovered.to_dict("records"),
              "counts": {"members": len(census)}, "sources": {}}
    (run / "report.json").write_text(json.dumps(report, sort_keys=True))
    return run


def make_accepted_report(root: Path, census_dir: Path, *, coverage: dict | None = None) -> Path:
    rows = [{"player_id": "00-A", "sleeper_id": "1", "name": "Owned Vet", "position": "WR", "producer": "vet"},
            {"player_id": "00-D", "sleeper_id": "4", "name": "IR HasFc", "position": "TE", "producer": "vet"},
            {"player_id": "00-F", "sleeper_id": "6", "name": "Active HasFc", "position": "WR", "producer": "vet"}]
    census_sha = json.loads((census_dir / "report.json").read_text())["census_csv_sha256"]
    uncovered_sha = _sha((census_dir / "uncovered.csv").read_bytes())
    # the real report's coverage block: listed_unowned.by_position[position][class]{with_forecast, without_forecast}
    if coverage is None:
        coverage = {"listed_unowned": {"by_position": {
            "QB": {"active": {"with_forecast": 0, "without_forecast": 1}},
            "RB": {"practice_squad": {"with_forecast": 0, "without_forecast": 1}},
            "TE": {"injured_reserve": {"with_forecast": 1, "without_forecast": 0}, "unknown": {"with_forecast": 0, "without_forecast": 1}},
            "WR": {"active": {"with_forecast": 1, "without_forecast": 0}, "cut": {"with_forecast": 0, "without_forecast": 1}},
        }}}
    report = {"run": "20260906T000001Z", "comparable_board": {"all_inspectable": rows},
              "current_census": {"census_csv_sha256": census_sha, "uncovered_csv_sha256": uncovered_sha, "coverage": coverage}}
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


def test_uncovered_file_is_verified_against_the_accepted_reports_declaration(tmp_path):
    from src.dynasty_genius.rookie.cold_start import (
        load_accepted_report,
        load_census_run,
        missing_default_pool,
    )
    run = make_census_run(tmp_path)
    accepted = load_accepted_report(make_accepted_report(tmp_path, run))
    (run / "uncovered.csv").write_text((run / "uncovered.csv").read_text().replace("Nobody", "Somebody"))
    with pytest.raises(ValueError, match="uncovered"):
        missing_default_pool(load_census_run(run), accepted)


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
    assert by.loc["00-ZZ", "draft_status"] == "no_history_in_held_sources"
    assert by.loc["00-A", "draft_season"] == 2015 and by.loc["00-A", "draft_pick"] == 1 and by.loc["00-A", "draft_round"] == 1
    assert by.loc["00-C", "college"] == "C U" and by.loc["00-C", "birth_date"] == "1995-03-03" and by.loc["00-C", "age_2026"] == pytest.approx(31.5, abs=0.1)
    joined = " ".join(ev["draft_status"].astype(str)).lower()
    assert "udfa" not in joined and "undrafted" not in joined


# ---------------------------------------------------------------- Task 3: NFL history, existing-forecast join check, route, ledger

def _history_sources():
    outcomes = pd.DataFrame({"player_id": ["00-A", "00-A", "00-C", "00-C", "00-D"], "season": [2024, 2025, 2022, 2023, 2025],
                             "points": [100.0, 120.0, 30.0, 0.0, 15.0], "games": [15, 16, 6, 0, 3], "appeared": [True, True, True, False, True]})
    basic_cohort = pd.DataFrame({"player_id": ["00-A", "00-C", "00-D"], "feature_season": [2025, 2023, 2025], "games_t": [16, 0, 3]})
    basic_forecasts = pd.DataFrame({"player_id": ["00-A", "00-D"], "feature_season": [2025, 2025], "e_points_year1": [110.0, 20.0]})
    rookie_scores = pd.DataFrame({"gsis_id": ["00-R"], "name": ["Rook"], "e_points_year1": [50.0]})
    return outcomes, basic_cohort, basic_forecasts, rookie_scores


def test_nfl_history_reads_the_artifact_and_the_frozen_producers():
    from src.dynasty_genius.rookie.cold_start import nfl_history
    outcomes, bc, bf, rs = _history_sources()
    h = nfl_history(pd.Series(["00-A", "00-C", "00-U", "00-D", "00-R"]), outcomes=outcomes, basic_cohort=bc, basic_forecasts=bf,
                    rookie_scores=rs, last_complete_season=2025).set_index("gsis_id")
    assert h.loc["00-A", "nfl_appearance_seasons"] == 2 and h.loc["00-A", "last_appearance_season"] == 2025 and bool(h.loc["00-A", "dg177_2025_forecast_row"])
    assert h.loc["00-C", "nfl_appearance_seasons"] == 1 and h.loc["00-C", "last_appearance_season"] == 2022 and h.loc["00-C", "seasons_since_last_appearance"] == 3
    assert h.loc["00-C", "window_points_last_appearance"] == 30.0 and h.loc["00-C", "dg177_last_feature_season"] == 2023
    assert h.loc["00-U", "nfl_appearance_seasons"] == 0 and pd.isna(h.loc["00-U", "first_appearance_season"]) and pd.isna(h.loc["00-U", "seasons_since_last_appearance"])
    assert bool(h.loc["00-R", "dg165_rookie_2026_row"]) and not bool(h.loc["00-U", "dg177_2025_feature_row"])


def test_route_classification_and_ledger_keep_every_missing_player():
    from src.dynasty_genius.rookie.cold_start import (
        build_ledger,
        draft_evidence,
        nfl_history,
        route_for,
    )
    picks, players, rosters = _draft_sources()
    outcomes, bc, bf, rs = _history_sources()
    missing = pd.DataFrame({"sleeper_id": ["10", "11", "12", "13", "14"], "name": ["Ann", "Cy", "Uma", "Dee", "Zed"],
                            "league_position": ["QB", "WR", "WR", "TE", "RB"], "fantasy_positions": ["QB", "WR", "WR", "TE", "RB"],
                            "availability_class": ["active", "practice_squad", "practice_squad", "injured_reserve", "active"],
                            "nfl_team": ["A", "C", "U", "D", "Z"], "nfl_status_raw": ["ACT", "DEV", "DEV", "RES", "ACT"],
                            "nfl_gsis_id": ["00-A", "00-C", "00-U", "00-D", "00-ZZ"], "sleeper_gsis_id": ["00-A", None, None, "00-X", None],
                            "join_basis": ["sleeper_id"] * 5})
    ev = draft_evidence(missing["nfl_gsis_id"], draft_picks=picks, players=players, rosters=rosters)
    hist = nfl_history(missing["nfl_gsis_id"], outcomes=outcomes, basic_cohort=bc, basic_forecasts=bf, rookie_scores=rs, last_complete_season=2025)
    led = build_ledger(missing, ev, hist).set_index("sleeper_id")
    assert len(led) == 5
    assert led.loc["10", "route"] == "existing_forecast_join_failure"      # a DG-177 2025 forecast exists under this gsis
    assert led.loc["11", "route"] == "dormant_no_draft_record" and led.loc["11", "seasons_since_last_appearance"] == 3
    assert led.loc["12", "route"] == "never_appeared_no_draft_record" and "stat row" in led.loc["12", "route_reason"]
    assert led.loc["13", "route"] == "existing_forecast_join_failure" and led.loc["13", "sleeper_gsis_agrees"] == False  # noqa: E712
    assert led.loc["14", "route"] == "no_held_source_history"
    assert "zero production" not in led.loc["12", "route_reason"].lower()
    assert set(led.columns) >= {"draft_status", "entry_season", "age_2026", "inputs_available", "identity_status"}
    assert route_for({"draft_status": "drafted_verified", "nfl_appearance_seasons": 0, "dg177_2025_forecast_row": False, "dg165_rookie_2026_row": False})[0] == "never_appeared_drafted"
    # root 2026-09-06: a draft-source conflict stays an EXPLICIT unresolved route, never folded into "no draft record"
    assert route_for({"draft_status": "draft_sources_conflict", "nfl_appearance_seasons": 2, "dg177_2025_forecast_row": False, "dg165_rookie_2026_row": False})[0] == "draft_sources_conflict_unresolved"


def test_full_nfl_source_reason_sits_beside_the_window_route():
    from src.dynasty_genius.rookie.cold_start import (
        build_ledger,
        draft_evidence,
        full_nfl_source_status,
        nfl_history,
    )
    picks, players, rosters = _draft_sources()
    outcomes, bc, bf, rs = _history_sources()
    # Muse-like case: a week-18 REG record (full-NFL history says appeared) but no championship-window row
    universe = pd.DataFrame({"sleeper_id": ["12", "11"], "name": ["Uma", "Cy"], "position": ["WR", "WR"], "rostered": [False, False],
                             "gsis_id": ["00-U", "00-C"], "status": ["no_nfl_history", "left_cohort_two_absent_seasons"],
                             "last_season_seen": [None, 2023], "cohort_position": [None, "WR"], "games_2025": [0, 0]})
    missing = pd.DataFrame({"sleeper_id": ["11", "12"], "name": ["Cy", "Uma"], "league_position": ["WR", "WR"], "fantasy_positions": ["WR", "WR"],
                            "availability_class": ["practice_squad", "practice_squad"], "nfl_team": ["C", "U"], "nfl_status_raw": ["DEV", "DEV"],
                            "nfl_gsis_id": ["00-C", "00-U"], "sleeper_gsis_id": [None, None], "join_basis": ["sleeper_id"] * 2})
    ev = draft_evidence(missing["nfl_gsis_id"], draft_picks=picks, players=players, rosters=rosters)
    hist = nfl_history(missing["nfl_gsis_id"], outcomes=outcomes, basic_cohort=bc, basic_forecasts=bf, rookie_scores=rs, last_complete_season=2025)
    fn = full_nfl_source_status(missing["sleeper_id"], universe)
    led = build_ledger(missing, ev, hist, fn).set_index("sleeper_id")
    assert led.loc["11", "full_nfl_source_reason"] == "left_cohort_two_absent_seasons" and led.loc["11", "route"] == "dormant_no_draft_record"
    assert led.loc["12", "full_nfl_source_reason"] == "no_nfl_history" and led.loc["12", "route"] == "never_appeared_no_draft_record"



# ---------------------------------------------------------------- Task 4: recovery sidecar, writer, CLI

def test_recovery_sidecar_copies_original_producer_rows_and_binds_them():
    from src.dynasty_genius.rookie.cold_start import recovery_sidecar
    bf = _bf_full()
    ledger = pd.DataFrame({"sleeper_id": ["10", "13", "12"], "name": ["Ann", "Dee", "Uma"], "gsis_id": ["00-A", "00-D", "00-U"],
                           "fantasy_positions": ["QB", "TE", "WR"], "route": ["existing_forecast_join_failure", "existing_forecast_join_failure", "never_appeared_no_draft_record"], "identity_status": ["verified_nfl_join"] * 3})
    side = recovery_sidecar(ledger, basic_forecasts=bf, veteran_binding={"manifest_sha256": "m" * 64, "corrected_manifest_sha256": "c" * 64,
                                                                          "basic_forecasts_sha256": "b" * 64, "run_dir": "/vet"})
    assert side["sleeper_id"].tolist() == ["10", "13"] and side["gsis_id"].tolist() == ["00-A", "00-D"]
    assert side.set_index("gsis_id").loc["00-A", "e_points_year1"] == 100.0  # the ORIGINAL row value, copied not refitted
    assert (side["estimate_class"] == "recovered_existing_forecast").all() and (side["producer_basic_forecasts_sha256"] == "b" * 64).all()
    assert (side["producer_manifest_sha256"] == "m" * 64).all() and (side["producer_corrected_manifest_sha256"] == "c" * 64).all()


def test_recovery_sidecar_refuses_a_join_failure_without_an_original_row():
    from src.dynasty_genius.rookie.cold_start import recovery_sidecar
    ledger = pd.DataFrame({"sleeper_id": ["77"], "name": ["Ghost"], "gsis_id": ["00-G"], "fantasy_positions": ["RB"], "route": ["existing_forecast_join_failure"], "identity_status": ["verified_nfl_join"]})
    with pytest.raises(ValueError, match="original"):
        recovery_sidecar(ledger, basic_forecasts=_bf_full(), veteran_binding={"manifest_sha256": "m" * 64, "corrected_manifest_sha256": None,
                                                                     "basic_forecasts_sha256": "b" * 64, "run_dir": "/vet"})


def test_write_coverage_is_immutable_hashes_outputs_and_renders_from_summary(tmp_path):
    from src.dynasty_genius.rookie.cold_start import (
        build_ledger,
        draft_evidence,
        nfl_history,
        summarize_ledger,
        write_coverage,
    )
    picks, players, rosters = _draft_sources()
    outcomes, bc, bf, rs = _history_sources()
    missing = pd.DataFrame({"sleeper_id": ["11", "12"], "name": ["Cy", "Uma"], "league_position": ["WR", "WR"], "fantasy_positions": ["WR", "WR"],
                            "availability_class": ["practice_squad", "active"], "nfl_team": ["C", "U"], "nfl_status_raw": ["DEV", "ACT"],
                            "nfl_gsis_id": ["00-C", "00-U"], "sleeper_gsis_id": [None, None], "join_basis": ["sleeper_id"] * 2})
    ev = draft_evidence(missing["nfl_gsis_id"], draft_picks=picks, players=players, rosters=rosters)
    hist = nfl_history(missing["nfl_gsis_id"], outcomes=outcomes, basic_cohort=bc, basic_forecasts=bf, rookie_scores=rs, last_complete_season=2025)
    led = build_ledger(missing, ev, hist)
    summary = summarize_ledger(led)
    assert summary["rows"] == 2 and summary["by_route"]["dormant_no_draft_record"] == 1 and summary["by_route"]["never_appeared_no_draft_record"] == 1
    out = tmp_path / "runs" / "20990101T000000Z" / "dg165_cold_start_coverage"
    out.mkdir(parents=True)
    manifest = write_coverage(out, ledger=led, summary=summary, recovery=None, inputs={"census.csv": {"path": "/c", "sha256": "1" * 64}}, git_sha="abc")
    for name, sha in manifest["outputs_sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == sha
    assert {"ledger.csv", "summary.json", "REPORT.md"} <= set(manifest["outputs_sha256"])
    report = (out / "REPORT.md").read_text()
    assert "never_appeared_no_draft_record: 1" in report and "undrafted" not in report.lower()
    with pytest.raises(FileExistsError):
        write_coverage(out, ledger=led, summary=summary, recovery=None, inputs={}, git_sha="abc")


# ---------------------------------------------------------------- root coverage review 2026-09-06: recovery guards, verified parquet bytes

def _bf_full():
    cols = {}
    for j in range(1, 6):
        cols[f"p_appear_year{j}"] = [0.6 - 0.1 * j, 0.1]
        cols[f"e_points_year{j}_given_appear"] = [180.0 - 10 * j, 200.0]
        cols[f"e_games_year{j}_given_appear"] = [12.0, 3.0]
        cols[f"e_points_year{j}"] = [110.0 - 10 * j, 20.0]
        cols[f"e_games_year{j}"] = [7.2, 0.3]
        cols[f"forecast_season_year{j}"] = [2025 + j, 2025 + j]
    return pd.DataFrame({"player_id": ["00-A", "00-D"], "feature_season": [2025, 2025], "arm": ["basic_cohort_3col_plus_lags"] * 2,
                         "position": ["RB", "RB"], "statline_position": ["FB", "FB"], **cols})


def _binding():
    return {"manifest_sha256": "m" * 64, "corrected_manifest_sha256": "c" * 64, "basic_forecasts_sha256": "b" * 64, "run_dir": "/vet"}


def test_recovery_carries_years_arm_and_binding_and_copies_every_value_exactly():
    from src.dynasty_genius.rookie.cold_start import recovery_sidecar
    bf = _bf_full()
    ledger = pd.DataFrame({"sleeper_id": ["10", "13"], "name": ["Ann", "Dee"], "gsis_id": ["00-A", "00-D"], "fantasy_positions": ["RB", "RB"],
                           "route": ["existing_forecast_join_failure"] * 2, "identity_status": ["verified_nfl_join"] * 2})
    side = recovery_sidecar(ledger, basic_forecasts=bf, veteran_binding=_binding())
    assert side["forecast_years"].tolist() == ["2026-2030"] * 2 and (side["producer_arm"] == "basic_cohort_3col_plus_lags").all()
    assert (side["producer_feature_season"] == 2025).all() and (side["source_binding"] == "basic_forecasts.csv@" + "b" * 64).all()
    for j in range(1, 6):
        assert side.set_index("gsis_id").loc["00-A", f"e_points_year{j}"] == 110.0 - 10 * j
        assert side.set_index("gsis_id").loc["00-A", f"season_year{j}"] == 2025 + j


def test_recovery_refuses_partial_or_nonfinite_paths_and_discordant_identities():
    from src.dynasty_genius.rookie.cold_start import recovery_sidecar
    ledger = pd.DataFrame({"sleeper_id": ["10"], "name": ["Ann"], "gsis_id": ["00-A"], "fantasy_positions": ["RB"], "route": ["existing_forecast_join_failure"], "identity_status": ["verified_nfl_join"]})
    bf = _bf_full()
    bf.loc[bf.player_id == "00-A", "e_points_year4"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        recovery_sidecar(ledger, basic_forecasts=bf, veteran_binding=_binding())
    bf = _bf_full().drop(columns=["e_games_year5"])
    with pytest.raises(ValueError, match="partial"):
        recovery_sidecar(ledger, basic_forecasts=bf, veteran_binding=_binding())
    bf = pd.concat([_bf_full(), _bf_full().iloc[[0]]], ignore_index=True)  # duplicate producer row for 00-A: never silently dropped
    with pytest.raises(ValueError, match="unique"):
        recovery_sidecar(ledger, basic_forecasts=bf, veteran_binding=_binding())
    two = pd.DataFrame({"sleeper_id": ["10", "11"], "name": ["Ann", "Ann2"], "gsis_id": ["00-A", "00-A"], "fantasy_positions": ["RB", "RB"],
                        "route": ["existing_forecast_join_failure"] * 2, "identity_status": ["verified_nfl_join"] * 2})  # two Sleeper ids claiming one GSIS: discordant
    with pytest.raises(ValueError, match="identit"):
        recovery_sidecar(two, basic_forecasts=_bf_full(), veteran_binding=_binding())


def test_verified_parquet_refuses_altered_bytes(tmp_path):
    from src.dynasty_genius.rookie.cold_start import verified_parquet
    path = tmp_path / "players.parquet"
    pd.DataFrame({"gsis_id": ["00-A"], "position": ["QB"]}).to_parquet(path, index=False)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(verified_parquet(path, sha, "players")) == 1
    pd.DataFrame({"gsis_id": ["00-B"], "position": ["QB"]}).to_parquet(path, index=False)
    with pytest.raises(ValueError, match="sha256"):
        verified_parquet(path, sha, "players")


# ---------------------------------------------------------------- root coverage review 2 (2026-09-06): ambiguous evidence, wording, recovery boundaries

def test_duplicate_positive_draft_evidence_is_ambiguous_not_silently_first():
    from src.dynasty_genius.rookie.cold_start import draft_evidence
    picks, players, rosters = _draft_sources()
    picks = pd.concat([picks, pd.DataFrame({"season": [2015], "round": [3], "pick": [99], "gsis_id": ["00-A"], "position": ["QB"], "pfr_player_name": ["Ann"]})], ignore_index=True)
    ev = draft_evidence(pd.Series(["00-A"]), draft_picks=picks, players=players, rosters=rosters).set_index("gsis_id")
    assert ev.loc["00-A", "draft_status"] == "draft_sources_conflict" and "draft_picks" in str(ev.loc["00-A", "draft_conflict_detail"])


def test_unknown_to_historical_sources_keeps_the_verified_current_identity():
    from src.dynasty_genius.rookie.cold_start import (
        build_ledger,
        draft_evidence,
        nfl_history,
    )
    picks, players, rosters = _draft_sources()
    outcomes, bc, bf, rs = _history_sources()
    missing = pd.DataFrame({"sleeper_id": ["14"], "name": ["Zed"], "league_position": ["RB"], "fantasy_positions": ["RB"], "availability_class": ["active"],
                            "nfl_team": ["Z"], "nfl_status_raw": ["ACT"], "nfl_gsis_id": ["00-ZZ"], "sleeper_gsis_id": [None], "join_basis": ["sleeper_id"]})
    ev = draft_evidence(missing["nfl_gsis_id"], draft_picks=picks, players=players, rosters=rosters)
    hist = nfl_history(missing["nfl_gsis_id"], outcomes=outcomes, basic_cohort=bc, basic_forecasts=bf, rookie_scores=rs, last_complete_season=2025)
    led = build_ledger(missing, ev, hist).set_index("sleeper_id")
    assert led.loc["14", "draft_status"] == "no_history_in_held_sources" and led.loc["14", "route"] == "no_held_source_history"
    assert led.loc["14", "identity_status"] == "verified_nfl_join"  # the census join is verified; only the HISTORICAL sources lack him
    assert "unverified" not in str(led.loc["14", "route_reason"]).lower()


def test_recovery_refuses_conflicting_identity_multiple_feature_seasons_and_empty_binding():
    from src.dynasty_genius.rookie.cold_start import recovery_sidecar
    base = pd.DataFrame({"sleeper_id": ["10"], "name": ["Ann"], "gsis_id": ["00-A"], "fantasy_positions": ["RB"], "route": ["existing_forecast_join_failure"], "identity_status": ["verified_nfl_join"]})
    conflicting = base.assign(identity_status=["sleeper_gsis_disagrees"])
    with pytest.raises(ValueError, match="identit"):
        recovery_sidecar(conflicting, basic_forecasts=_bf_full(), veteran_binding=_binding(), feature_season=2025)
    two_seasons = pd.concat([_bf_full().assign(feature_season=2018), _bf_full()], ignore_index=True)  # 2018 row first, 2025 second
    side = recovery_sidecar(base, basic_forecasts=two_seasons, veteran_binding=_binding(), feature_season=2025)
    assert (side["producer_feature_season"] == 2025).all() and side.set_index("gsis_id").loc["00-A", "e_points_year1"] == 100.0
    twice_2025 = pd.concat([_bf_full(), _bf_full()], ignore_index=True)
    with pytest.raises(ValueError, match="unique"):
        recovery_sidecar(base, basic_forecasts=twice_2025, veteran_binding=_binding(), feature_season=2025)
    with pytest.raises(ValueError, match="binding"):
        recovery_sidecar(base, basic_forecasts=_bf_full(), veteran_binding={"manifest_sha256": None, "corrected_manifest_sha256": None,
                                                                             "basic_forecasts_sha256": "", "run_dir": "/vet"}, feature_season=2025)
    bf_inf = _bf_full()
    bf_inf.loc[bf_inf.player_id == "00-A", "e_games_year2"] = float("inf")
    with pytest.raises(ValueError, match="finite"):
        recovery_sidecar(base, basic_forecasts=bf_inf, veteran_binding=_binding(), feature_season=2025)


def test_current_roster_capture_recovers_a_2026_entry_without_touching_history():
    from src.dynasty_genius.rookie.cold_start import draft_evidence
    picks, players, rosters = _draft_sources()
    current = pd.DataFrame({"season": [2026], "gsis_id": ["00-ZZ"], "position": ["RB"], "status": ["ACT"], "entry_year": [2026], "rookie_year": [2026],
                            "draft_number": [None], "draft_club": [None], "birth_date": ["2004-01-01"], "college": ["Z U"]})
    ev = draft_evidence(pd.Series(["00-ZZ", "00-A"]), draft_picks=picks, players=players, rosters=rosters, current_roster=current).set_index("gsis_id")
    assert ev.loc["00-ZZ", "draft_status"] == "no_draft_record_1_source" and ev.loc["00-ZZ", "entry_season"] == 2026
    assert ev.loc["00-ZZ", "known_to_historical_sources"] == 0 and bool(ev.loc["00-ZZ", "known_to_current_roster"]) and ev.loc["00-ZZ", "current_roster_entry_year"] == 2026
    assert ev.loc["00-A", "draft_status"] == "drafted_verified"  # the current capture adds nothing to a verified draft record



# ---------------------------------------------------------------- root regression: every recovery row is validated, not just the first

def _two_row_ledger(**second):
    rows = [{"sleeper_id": "10", "name": "Ann", "gsis_id": "00-A", "fantasy_positions": "RB", "route": "existing_forecast_join_failure", "identity_status": "verified_nfl_join"},
            {"sleeper_id": "13", "name": "Dee", "gsis_id": "00-D", "fantasy_positions": "RB", "route": "existing_forecast_join_failure", "identity_status": "verified_nfl_join"}]
    rows[1].update(second)
    return pd.DataFrame(rows)


def test_recovery_validates_the_second_row_too():
    from src.dynasty_genius.rookie.cold_start import recovery_sidecar
    # second row's forecast seasons are 2019-2023 (a stale copied path): refuse
    bf = _bf_full()
    for j in range(1, 6):
        bf.loc[bf.player_id == "00-D", f"forecast_season_year{j}"] = 2018 + j
    with pytest.raises(ValueError, match="2026"):
        recovery_sidecar(_two_row_ledger(), basic_forecasts=bf, veteran_binding=_binding(), feature_season=2025)
    # second row's identity disagrees: refuse
    with pytest.raises(ValueError, match="identit"):
        recovery_sidecar(_two_row_ledger(identity_status="sleeper_gsis_disagrees"), basic_forecasts=_bf_full(), veteran_binding=_binding(), feature_season=2025)
    # second row's arm is not the selected arm: refuse
    bf = _bf_full()
    bf.loc[bf.player_id == "00-D", "arm"] = "other_arm"
    with pytest.raises(ValueError, match="arm"):
        recovery_sidecar(_two_row_ledger(), basic_forecasts=bf, veteran_binding=_binding(), feature_season=2025)
    # missing forecast-season columns are never inferred from the feature season: refuse
    bf = _bf_full().drop(columns=["forecast_season_year3"])
    with pytest.raises(ValueError, match="forecast_season"):
        recovery_sidecar(_two_row_ledger(), basic_forecasts=bf, veteran_binding=_binding(), feature_season=2025)
    # an empty binding dict refuses
    with pytest.raises(ValueError, match="binding"):
        recovery_sidecar(_two_row_ledger(), basic_forecasts=_bf_full(), veteran_binding={}, feature_season=2025)
    # a ledger without identity_status cannot be recovered (identity must be verified explicitly)
    with pytest.raises(ValueError, match="identit"):
        recovery_sidecar(_two_row_ledger().drop(columns=["identity_status"]), basic_forecasts=_bf_full(), veteran_binding=_binding(), feature_season=2025)
    good = recovery_sidecar(_two_row_ledger(), basic_forecasts=_bf_full(), veteran_binding=_binding(), feature_season=2025)
    assert len(good) == 2 and (good["producer_feature_season"] == 2025).all()
