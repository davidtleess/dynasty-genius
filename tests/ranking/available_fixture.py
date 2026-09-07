"""Shared synthetic fixture for the available-player catalog tests: a dated census run, a league
snapshot, two producer CSVs and the accepted report that binds them (mirrors the real shapes)."""
from __future__ import annotations

import csv
import hashlib
import json

CENSUS_COLS = ["sleeper_id", "name", "league_position", "fantasy_positions", "sleeper_status", "sleeper_team",
               "sleeper_gsis_id", "nfl_team", "nfl_position", "nfl_status_raw", "nfl_gsis_id", "availability_class",
               "join_basis", "identity_conflict", "league_owned", "roster_id", "contested_nfl_gsis_id"]
UNCOVERED_COLS = ["sleeper_id", "name", "league_position", "sleeper_status", "sleeper_team", "sleeper_gsis_id", "reason"]


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _census_row(sid, name, pos, cls, owned, gsis, roster="", conflict="", basis="sleeper_id", team="KC", raw="ACT"):
    return dict(zip(CENSUS_COLS, [sid, name, pos, pos, "Active", team, gsis, team if cls != "unknown" else "", pos, raw,
                                  gsis, cls, basis, conflict, str(owned), roster, ""]))


def _fixture(tmp_path, *, drop_year=False, break_csv_sha=False):
    src = tmp_path / "src"
    src.mkdir(parents=True)
    snap = src / "snapshot.json"
    snap.write_text(json.dumps({"captured_at": "2026-09-06T13:00:52+00:00", "david_roster_id": 1,
                                "rosters": [{"roster_id": 1, "players": ["100"]}, {"roster_id": 2, "players": ["101"]}]}))
    roster = src / "roster_2026.csv"
    roster.write_bytes(b"season,team\n2026,KC\n")
    sleeper = src / "sleeper_eligibility.csv"
    sleeper.write_bytes(b"sleeper_id\n100\n")
    bridge = src / "bridge.csv"
    bridge.write_bytes(b"sleeper_id,my_gsis_id\n13516,00-0041081\n")
    # census: 2 owned; unowned: active WR with forecast, active RB rookie (bridge) with forecast, PS WR without forecast,
    # IR TE with a NEGATIVE forecast, cut QB, retired RB, unknown TE
    rows = [
        _census_row("100", "Owned One", "QB", "active", True, "00-1", roster="1"),
        _census_row("101", "Owned Two", "WR", "active", True, "00-2", roster="2"),
        _census_row("200", "Free Wideout", "WR", "active", False, "00-3"),
        _census_row("13516", "Max Bredeson", "RB", "active", False, "", basis="gsis_id_via_bridge", team="MIN"),
        _census_row("201", "Practice Guy", "WR", "practice_squad", False, "00-5", raw="DEV"),
        _census_row("202", "Reserve End", "TE", "injured_reserve", False, "00-6", raw="RES"),
        _census_row("203", "Cut Passer", "QB", "cut", False, "00-7", raw="CUT"),
        _census_row("204", "Retired Back", "RB", "retired", False, "00-8", raw="RET"),
        _census_row("205", "Contested End", "TE", "unknown", False, "00-9", conflict="contested"),
    ]
    run = tmp_path / "20260906T202057Z" / "dg178_current_census"
    run.mkdir(parents=True)
    with (run / "census.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CENSUS_COLS)
        w.writeheader()
        w.writerows(rows)
    with (run / "uncovered.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=UNCOVERED_COLS)
        w.writeheader()
        w.writerow(dict(zip(UNCOVERED_COLS, ["4098", "Kareem Hunt", "RB", "Active", "", "00-0033923", "no verified join"])))
    report_c = {"season": 2026, "run": "20260906T202057Z", "denominator_note": "members = listed-or-owned, NOT active NFL",
                "sources": {"nflverse_roster": {"path": str(roster), "sha256": _sha(roster), "http_last_modified": "Sun, 06 Sep 2026 11:28:11 GMT"},
                            "sleeper_eligibility": {"path": str(sleeper), "sha256": _sha(sleeper), "captured_at": "2026-09-06T16:41:07+00:00"},
                            "league_snapshot": {"path": str(snap), "sha256": _sha(snap), "owned_ids": 2},
                            "identity_bridge": [{"path": str(bridge), "sha256": _sha(bridge)}]},
                "counts": {"members": len(rows), "uncovered": 1, "nfl_rows_unclaimed": 141, "contested_nfl_records": 1},
                "census_csv_sha256": _sha(run / "census.csv")}
    (run / "report.json").write_text(json.dumps(report_c))
    # producers: a veteran CSV keyed by gsis player_id, a rookie CSV keyed by (draft_season, pick)+gsis
    vet = src / "basic_forecasts.csv"
    vcols = ["player_id", "position", "forecast_cutoff", "arm"] + [c for j in range(1, 6) for c in
             (f"p_appear_year{j}", f"e_points_year{j}_given_appear", f"e_games_year{j}_given_appear", f"e_points_year{j}", f"e_games_year{j}",
              f"forecast_season_year{j}")]
    def vrow(pid, pos, pts, missing_year=None):
        r = {"player_id": pid, "position": pos, "forecast_cutoff": "post-2025-season", "arm": "basic_arm"}
        for j in range(1, 6):
            r[f"forecast_season_year{j}"] = f"{2025 + j}.0"
            if missing_year == j:
                continue
            r.update({f"p_appear_year{j}": 0.8, f"e_points_year{j}_given_appear": pts[j - 1] / 0.8, f"e_games_year{j}_given_appear": 14,
                      f"e_points_year{j}": pts[j - 1], f"e_games_year{j}": 11.2})
        return r
    with vet.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=vcols)
        w.writeheader()
        w.writerow(vrow("00-1", "QB", [300, 290, 280, 270, 260]))
        w.writerow(vrow("00-3", "WR", [120.5, 110, 100, 90, 80]))
        w.writerow(vrow("00-6", "TE", [-1.5, 2, 0, 1, 1], missing_year=5 if drop_year else None))
        w.writerow(vrow("00-7", "QB", [50, 40, 30, 20, 10]))
    rk = src / "rookie_scores_2026.csv"
    rcols = ["gsis_id", "name", "position", "draft_season", "pick", "model_version", "scoring_arm_id"] + [c for j in range(1, 7) for c in
             (f"p_appear_year{j}", f"e_points_year{j}_given_appear", f"e_games_year{j}_given_appear", f"e_points_year{j}", f"e_games_year{j}")]
    with rk.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rcols)
        w.writeheader()
        r = {"gsis_id": "00-0041081", "name": "Max Bredeson", "position": "TE", "draft_season": 2026, "pick": 159,
             "model_version": "dg165_rookie", "scoring_arm_id": "dg165_rookie:inner_menu:trend"}
        for j, pts in enumerate((10, 20, 40, 60, 70, 75), start=1):
            r.update({f"p_appear_year{j}": 0.5, f"e_points_year{j}_given_appear": pts / 0.5, f"e_games_year{j}_given_appear": 10,
                      f"e_points_year{j}": pts, f"e_games_year{j}": 5})
        w.writerow(r)
    # the accepted report (what the audit wrote), pointing at the census and the producers
    def rrow(pid, sid, name, pos, value, margins, readiness="comparable", reason=None, producer="vet"):
        return {"player_id": pid, "sleeper_id": sid, "name": name, "position": pos, "value": value, "readiness": readiness,
                "reason": reason, "producer": producer if readiness == "comparable" else "annual_target",
                "seasons": [{"season": 2026 + i, "expected_margin": m, "action": "retain" if m > 0 else "replace",
                             "advantage": max(0.0, m)} for i, m in enumerate(margins)]}
    board = {"readiness": {"comparable": 4, "none": 2}, "horizons_summed": 5,
             "annual_producers": [
                 {"model_version": "vet", "csv": str(vet), "csv_sha256": _sha(vet) if not break_csv_sha else "0" * 64,
                  "manifest_sha256": "m" * 64, "seasons": 5,
                  "evidence": {"verified": True, "scoring_arm": "basic_arm", "graded_arm": "basic_arm"}},
                 {"model_version": "dg165_rookie", "csv": str(rk), "csv_sha256": _sha(rk), "manifest_sha256": "n" * 64, "seasons": 6,
                  "evidence": {"verified": True, "scoring_arm": "dg165_rookie:inner_menu:trend", "graded_arm": "inner_menu"}},
                 {"model_version": "union_replacement", "seasons": 5, "replacement": {}},
             ],
             "davids_roster": [], "league_rostered": [], "top": [],
             "all_inspectable": [rrow("00-1", "100", "Owned One", "QB", 900.0, [180, 180, 180, 180, 180]),
                                 rrow("00-3", "200", "Free Wideout", "WR", 0.0, [-10, -5, -3, -2, -1]),
                                 rrow("00-0041081", "13516", "Max Bredeson", "RB", 40.2, [-70, -30, 0, 30, 40.2], producer="dg165_rookie"),
                                 rrow("00-6", "202", "Reserve End", "TE", 0.0, [-110, -100, -100, -100, -100]),
                                 rrow("00-7", "203", "Cut Passer", "QB", 0.0, [-60, -60, -60, -60, -60])]}
    report = {"run": "20260906T214512Z", "forecast_date": "2026-09-06",
              "inputs": {"snapshot": {"path": str(snap), "sha256": _sha(snap), "id": "league-20260906T130052Z",
                                      "captured_at": "2026-09-06T13:00:52+00:00"}},
              "board_target": {"window": "championship_week17", "labels_through": 2025},
              "outcome_artifact": {"schema_version": "dg179_league_season_outcomes_v1", "outcomes_csv_sha256": "o" * 64,
                                   "target_identity": "t" * 64},
              "comparable_views": {"h2": "comparable_board", "h5": "horizon_board"},
              "comparable_board": {**board, "horizons_summed": 2}, "horizon_board": board,
              "current_census": {"run_id": "20260906T202057Z", "run_dir": str(run), "census_csv_sha256": _sha(run / "census.csv"),
                                 "report_sha256": _sha(run / "report.json"), "uncovered_csv_sha256": _sha(run / "uncovered.csv"),
                                 "sources": report_c["sources"]},
              "provenance": {"git_head": "abc", "git_dirty": False},
              "unforecast_eligible_census": {"QB": {"count": 368}}}
    rp = tmp_path / "report.json"
    rp.write_text(json.dumps(report))
    return rp, run, snap, [vet, rk]


