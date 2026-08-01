"""PlayerProfiler Advanced PBP — layer 1 contract tests.

Anchored to facts measured from the live 2020-2025 exports on 2026-08-01. The centre of
gravity is the three-era slot vocabulary: this stream describes WHICH PLAYER FILLED WHICH
ROLE on a play, and PlayerProfiler changed that vocabulary twice, losing information both
times. A mapping error here does not produce a null — it attaches the wrong player to the
wrong role on every play in a season.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import pytest

from src.dynasty_genius.playerprofiler import CONFLICT
from src.dynasty_genius.playerprofiler_pbp import (
    ERA_2020,
    ERA_2021,
    ERA_2023,
    PLAY_TABLE,
    SLOT_TABLE,
    PbpError,
    discover_pbp_exports,
    read_pbp_header,
    receiver_slot_coverage,
    run_pbp_ingest,
    status_marker_path,
)
from src.dynasty_genius.playerprofiler_roster import (
    BASIS_NAME_BRIDGE,
    BASIS_VENDOR_GSIS,
    run_roster_key_ingest,
)

ROSTER_GSIS = ["player_id", "name", "week", "team", "number", "position", "dob"]
ROSTER_AGE = ["player_id", "name", "week", "team", "number", "position", "age"]

# Minimal but REAL column sets — the era signatures and slot families are what matter.
COLS_2020 = ["game_key", "week", "nfl_play_id", "team_play_charted_order", "quarter",
             "yards_gained", "qb", "runner", "targeted_player",
             "wr1", "defender_wr1", "cushion_wr1", "coverage_wr1", "wr1_route_run",
             "wr2", "defender_wr2", "cushion_wr2", "coverage_wr2", "wr2_route_run",
             "wr5", "defender_wr5", "cushion_wr5", "coverage_wr5", "wr5_route_run",
             "slot1", "defender_slot1", "cushion_slot1", "coverage_slot1", "slot1_route_run",
             "slot2", "defender_slot2", "cushion_slot2", "coverage_slot2", "slot2_route_run",
             "te1", "defender_te1", "te1_route_run", "te2", "defender_te2", "te2_route_run",
             "te3", "defender_te3", "te3_route_run",
             "rb1", "defender_rb1", "rb1_route_run", "rb2", "defender_rb2", "rb2_route_run",
             "rb3", "defender_rb3", "rb3_route_run"]

COLS_2021 = ["playid", "season", "week", "gamekey", "quarter", "yards_gained", "qb_id",
             "runner_id"] + [
    f"{p}_{s}" for p in ("receiver1", "receiver2", "receiver5")
    for s in ("id", "route", "motion", "cushion_yards", "coverage", "defender_id")] + [
    f"{p}_{s}" for p in ("inline_te1", "inline_te2", "inline_te3",
                         "backfield_rb1", "backfield_rb2", "backfield_rb3")
    for s in ("id", "route", "motion")]

COLS_2023 = ["playid", "season", "week", "gamekey_internal", "quarter", "yards_gained",
             "qb_id", "runner_id", "coverage_type", "forecast_temp"] + [
    f"skill{i}{s}" for i in range(1, 6)
    for s in ("", "_route", "_motion", "_cushion")]


def _write(path: Path, columns: list[str], rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})
    return path


def _row_2020(**over) -> dict:
    base = {"game_key": "2020-10-04CLE_at_DAL", "week": "4", "nfl_play_id": "3026",
            "team_play_charted_order": "1", "quarter": "1", "yards_gained": "7",
            "qb": "DW-1725", "runner": "DJ-1325", "targeted_player": "WF-0300",
            "wr1": "WF-0300", "defender_wr1": "LS-1562", "cushion_wr1": "5",
            "coverage_wr1": "Man", "wr1_route_run": "1",
            "slot1": "RC-1500", "defender_slot1": "AB-1000", "cushion_slot1": "3",
            "coverage_slot1": "Zone", "slot1_route_run": "1",
            "te1": "JA-0462", "defender_te1": "XX-0001", "te1_route_run": "1",
            "rb1": "DJ-1325", "defender_rb1": "YY-0002", "rb1_route_run": "0"}
    base.update(over)
    return base


def _row_2021(**over) -> dict:
    base = {"playid": "1001", "season": "2021", "week": "1", "gamekey": "G1",
            "quarter": "1", "yards_gained": "7", "qb_id": "DP-1000",
            "runner_id": "DH-2000",
            "receiver1_id": "JJ-1000", "receiver1_route": "3", "receiver1_motion": "P",
            "receiver1_cushion_yards": "5", "receiver1_coverage": "man",
            "receiver1_defender_id": "LS-1562",
            "inline_te1_id": "TE-1000", "inline_te1_route": "2", "inline_te1_motion": "",
            "backfield_rb1_id": "RB-1000", "backfield_rb1_route": "0",
            "backfield_rb1_motion": ""}
    base.update(over)
    return base


def _row_2023(**over) -> dict:
    base = {"playid": "2001", "season": "2023", "week": "1",
            "gamekey_internal": "2023-09-07_KC_DET", "quarter": "1", "yards_gained": "7",
            "qb_id": "00-0033873", "runner_id": "00-0034791", "coverage_type": "2",
            "forecast_temp": "71",
            "skill1": "00-0036322", "skill1_route": "3", "skill1_motion": "P",
            "skill1_cushion": "5"}
    base.update(over)
    return base


@pytest.fixture()
def paths(tmp_path: Path) -> dict:
    return {"db_path": tmp_path / "pp.db", "root": tmp_path / "root",
            "exports": tmp_path / "exports", "roster": tmp_path / "roster"}


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in Path(folder).iterdir() if p.is_file())


@pytest.fixture()
def with_bridge(paths):
    _write(paths["roster"] / "2022-Weekly-Roster-Key.csv", ROSTER_AGE, [
        {"player_id": pid, "name": nm, "week": "1", "team": "MIN", "number": "1",
         "position": "WR", "age": "25"}
        for pid, nm in (("JJ-1000", "Justin Jefferson"), ("DP-1000", "Dak Prescott"),
                        ("DH-2000", "Derrick Henry"), ("TE-1000", "Travis Kelce"),
                        ("RB-1000", "Alvin Kamara"), ("WF-0300", "Will Fuller"),
                        ("DW-1725", "Deshaun Watson"), ("DJ-1325", "David Johnson"),
                        ("RC-1500", "Rondale Carter"), ("JA-0462", "Jack Adams"))])
    _write(paths["roster"] / "2023-Weekly-Roster-Key.csv", ROSTER_GSIS, [
        {"player_id": gid, "name": nm, "week": "1", "team": "MIN", "number": "1",
         "position": "WR", "dob": "01/01/1995"}
        for gid, nm in (("00-0036322", "Justin Jefferson"), ("00-0033077", "Dak Prescott"),
                        ("00-0032764", "Derrick Henry"), ("00-0030506", "Travis Kelce"),
                        ("00-0033906", "Alvin Kamara"), ("00-0033536", "Will Fuller"),
                        ("00-0031280", "Deshaun Watson"), ("00-0033891", "David Johnson"),
                        ("00-0039001", "Rondale Carter"), ("00-0039002", "Jack Adams"))])
    run_roster_key_ingest(export_paths=_files(paths["roster"]),
                          db_path=paths["db_path"], root=paths["root"])
    return paths


# --- the three eras ---------------------------------------------------------------

@pytest.mark.parametrize("cols,rowf,era", [
    (COLS_2020, _row_2020, ERA_2020),
    (COLS_2021, _row_2021, ERA_2021),
    (COLS_2023, _row_2023, ERA_2023),
])
def test_each_era_is_detected_from_its_own_signature(tmp_path, cols, rowf, era):
    year = era[:4]
    path = _write(tmp_path / f"{year}-Advanced-PBP-Data.csv", cols, [rowf()])
    assert read_pbp_header(path).schema_era == era


def test_unknown_era_refuses_rather_than_mapping_onto_a_known_one(tmp_path):
    """A mapping error here does not yield a null — it attaches the wrong player to the
    wrong role on every play in the season."""
    path = _write(tmp_path / "2026-Advanced-PBP-Data.csv",
                  ["playid", "week", "mystery1", "qb_id"],
                  [{"playid": "1", "week": "1", "mystery1": "x", "qb_id": "00-0036322"}])
    with pytest.raises(PbpError, match="unknown_schema_era"):
        read_pbp_header(path)


def test_receiver_slot_coverage_records_the_dropped_slot_receiver(tmp_path):
    """THE HEADLINE FINDING. 2020 charts five receiver positions and NAMES the slot
    receiver. 2021 charts three — indices 1, 2 and 5 — because 2020's slot1/slot2 are the
    absent receiver3/receiver4. A consumer counting receivers per play across the seam
    would read a vendor coverage change as a change in NFL personnel usage."""
    a = read_pbp_header(_write(tmp_path / "a" / "2020-Advanced-PBP-Data.csv",
                               COLS_2020, [_row_2020()]))
    b = read_pbp_header(_write(tmp_path / "b" / "2021-Advanced-PBP-Data.csv",
                               COLS_2021, [_row_2021()]))
    cov = receiver_slot_coverage([a, b])["by_season"]
    assert cov["2020"]["receiver_slots_charted"] == 5
    assert "slot1" in cov["2020"]["indices"] and "slot2" in cov["2020"]["indices"]
    assert cov["2021"]["receiver_slots_charted"] == 3
    assert cov["2021"]["indices"] == ["receiver1", "receiver2", "receiver5"]


def test_2023_slots_are_anonymous_and_marked_as_such(paths, with_bridge):
    """From 2023 the vendor does not say whether skill1 is a WR, TE or RB. Anything that
    reads those slots positionally is inferring, and slot_role_known says so."""
    _write(paths["exports"] / "2023-Advanced-PBP-Data.csv", COLS_2023, [_row_2023()])
    run_pbp_ingest(export_paths=_files(paths["exports"]),
                   db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    rows = conn.execute(
        f"SELECT slot_kind, slot_role_known FROM {SLOT_TABLE}").fetchall()
    assert rows, "no slot rows were extracted"
    assert {r[0] for r in rows} == {"skill"}
    assert {r[1] for r in rows} == {"0"}, "an anonymous slot was marked role-known"


def test_pre_2023_slots_keep_the_vendors_own_role_words(paths, with_bridge):
    """slot_kind records what the VENDOR called it — wr / slot / te / rb — never a
    normalisation we invented, so the 2020 slot receiver stays identifiable."""
    _write(paths["exports"] / "2020-Advanced-PBP-Data.csv", COLS_2020, [_row_2020()])
    run_pbp_ingest(export_paths=_files(paths["exports"]),
                   db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    kinds = dict(conn.execute(
        f"SELECT slot_kind, slot_role_known FROM {SLOT_TABLE}").fetchall())
    assert {"wr", "slot", "te", "rb"} <= set(kinds)
    assert set(kinds.values()) == {"1"}


def test_slot_rows_carry_the_charting_detail_that_makes_this_stream_worth_having(
        paths, with_bridge):
    _write(paths["exports"] / "2020-Advanced-PBP-Data.csv", COLS_2020, [_row_2020()])
    run_pbp_ingest(export_paths=_files(paths["exports"]),
                   db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        f"SELECT * FROM {SLOT_TABLE} WHERE slot_kind='slot' AND slot_index='1'").fetchone()
    assert row["coverage"] == "Zone"
    assert row["cushion"] == "3"
    assert row["defender_id"] == "AB-1000"
    assert row["route"] == "1"


# --- the duplicate-charting defect ------------------------------------------------

def test_a_play_charted_twice_keeps_both_chartings(paths, with_bridge):
    """MEASURED: four 2020 plays are charted TWICE and the two chartings DISAGREE about who
    was on the field — different wr1, defender, cushion and coverage. The first cut keyed
    without team_play_charted_order and silently discarded one real observation."""
    _write(paths["exports"] / "2020-Advanced-PBP-Data.csv", COLS_2020, [
        _row_2020(team_play_charted_order="1", wr1="WF-0300", coverage_wr1="Man"),
        _row_2020(team_play_charted_order="2", wr1="RC-1500", coverage_wr1="Zone"),
    ])
    status = run_pbp_ingest(export_paths=_files(paths["exports"]),
                            db_path=paths["db_path"], root=paths["root"])
    assert status["rows"]["pbp_play"] == 2, "a differing charting was silently dropped"
    conn = sqlite3.connect(paths["db_path"])
    got = {r[0] for r in conn.execute(
        f"SELECT coverage FROM {SLOT_TABLE} WHERE slot_kind='wr' AND slot_index='1'")}
    assert got == {"Man", "Zone"}


def test_two_disagreeing_rows_under_one_key_refuse(paths, with_bridge):
    """If the key cannot separate them, refuse rather than pick."""
    _write(paths["exports"] / "2021-Advanced-PBP-Data.csv", COLS_2021, [
        _row_2021(yards_gained="7"),
        _row_2021(yards_gained="99"),
    ])
    with pytest.raises(PbpError, match="conflicting_duplicate_play"):
        run_pbp_ingest(export_paths=_files(paths["exports"]),
                       db_path=paths["db_path"], root=paths["root"])


def test_every_source_play_reaches_the_store(paths, with_bridge):
    """The count that proves nothing vanished: stored plays == marker plays == rows in."""
    rows = [_row_2021(playid=str(i)) for i in range(50)]
    _write(paths["exports"] / "2021-Advanced-PBP-Data.csv", COLS_2021, rows)
    status = run_pbp_ingest(export_paths=_files(paths["exports"]),
                            db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    stored = conn.execute(f"SELECT COUNT(*) FROM {PLAY_TABLE}").fetchone()[0]
    assert stored == status["rows"]["pbp_play"] == 50


# --- identity ---------------------------------------------------------------------

def test_gsis_era_is_vendor_supplied_and_pp_era_uses_the_bridge(paths, with_bridge):
    _write(paths["exports"] / "2021-Advanced-PBP-Data.csv", COLS_2021, [_row_2021()])
    _write(paths["exports"] / "2023-Advanced-PBP-Data.csv", COLS_2023, [_row_2023()])
    run_pbp_ingest(export_paths=_files(paths["exports"]),
                   db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    pairs = conn.execute(
        f"SELECT id_namespace, identity_basis, dg_player_id FROM {SLOT_TABLE} "
        "WHERE source_player_id IN ('JJ-1000','00-0036322')").fetchall()
    by_ns = {p[0]: (p[1], p[2]) for p in pairs}
    assert by_ns["pp_internal"] == (BASIS_NAME_BRIDGE, "00-0036322")
    assert by_ns["gsis"] == (BASIS_VENDOR_GSIS, "00-0036322")


def test_a_colliding_source_id_is_never_resolved(paths):
    """Same rule as every other PlayerProfiler stream: an id standing for two humans
    resolves to nobody."""
    _write(paths["roster"] / "2022-Weekly-Roster-Key.csv", ROSTER_AGE, [
        {"player_id": "JJ-1000", "name": "David Moore", "week": "1", "team": "CLE",
         "number": "1", "position": "WR", "age": "27"},
        {"player_id": "JJ-1000", "name": "David Moore", "week": "1", "team": "GB",
         "number": "2", "position": "WR", "age": "26"},
        {"player_id": "DP-1000", "name": "Dak Prescott", "week": "1", "team": "DAL",
         "number": "4", "position": "QB", "age": "29"}])
    _write(paths["roster"] / "2023-Weekly-Roster-Key.csv", ROSTER_GSIS, [
        {"player_id": "00-0033891", "name": "David Moore", "week": "1", "team": "CLE",
         "number": "1", "position": "WR", "dob": "01/01/1995"},
        {"player_id": "00-0033077", "name": "Dak Prescott", "week": "1", "team": "DAL",
         "number": "4", "position": "QB", "dob": "07/29/1993"}])
    run_roster_key_ingest(export_paths=_files(paths["roster"]),
                          db_path=paths["db_path"], root=paths["root"])

    _write(paths["exports"] / "2021-Advanced-PBP-Data.csv", COLS_2021, [_row_2021()])
    run_pbp_ingest(export_paths=_files(paths["exports"]),
                   db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    row = conn.execute(
        f"SELECT identity_status, dg_player_id FROM {SLOT_TABLE} "
        "WHERE source_player_id='JJ-1000'").fetchone()
    assert row == (CONFLICT, None)


def test_ingest_without_the_roster_bridge_refuses(paths):
    _write(paths["exports"] / "2023-Advanced-PBP-Data.csv", COLS_2023, [_row_2023()])
    with pytest.raises(PbpError, match="bridge_missing"):
        run_pbp_ingest(export_paths=_files(paths["exports"]),
                       db_path=paths["db_path"], root=paths["root"])


# --- run contract -----------------------------------------------------------------

def test_rerun_is_idempotent_on_the_source_digest(paths, with_bridge):
    _write(paths["exports"] / "2023-Advanced-PBP-Data.csv", COLS_2023,
           [_row_2023(), _row_2023(playid="2002")])
    kw = dict(export_paths=_files(paths["exports"]), db_path=paths["db_path"],
              root=paths["root"])
    first = run_pbp_ingest(**kw)
    second = run_pbp_ingest(**kw)
    assert first["rows"] == second["rows"]
    assert set(second["applied"].values()) == {"unchanged"}


def test_changed_source_is_reingested(paths, with_bridge):
    export = paths["exports"] / "2023-Advanced-PBP-Data.csv"
    _write(export, COLS_2023, [_row_2023()])
    kw = dict(export_paths=_files(paths["exports"]), db_path=paths["db_path"],
              root=paths["root"])
    run_pbp_ingest(**kw)
    _write(export, COLS_2023, [_row_2023(), _row_2023(playid="2002")])
    second = run_pbp_ingest(export_paths=_files(paths["exports"]),
                            db_path=paths["db_path"], root=paths["root"])
    assert set(second["applied"].values()) == {"updated"}
    assert second["rows"]["pbp_play"] == 2


def test_season_label_mismatch_refuses(tmp_path):
    path = _write(tmp_path / "2022-Advanced-PBP-Data.csv", COLS_2021,
                  [_row_2021(season="2021")])
    with pytest.raises(PbpError, match="season_label_mismatch"):
        read_pbp_header(path)


def test_two_files_for_one_season_that_differ_refuse(tmp_path):
    a = _write(tmp_path / "a" / "2021-Advanced-PBP-Data.csv", COLS_2021, [_row_2021()])
    b = _write(tmp_path / "b" / "2021-Advanced-PBP-Data.csv", COLS_2021,
               [_row_2021(yards_gained="99")])
    with pytest.raises(PbpError, match="conflicting_season_files"):
        discover_pbp_exports([a, b])


def test_failure_writes_a_named_marker(paths, with_bridge):
    _write(paths["exports"] / "2023-Advanced-PBP-Data.csv", COLS_2023, [_row_2023()])
    kw = dict(export_paths=_files(paths["exports"]), db_path=paths["db_path"],
              root=paths["root"])
    run_pbp_ingest(**kw)
    assert json.loads(status_marker_path(paths["root"]).read_text())["status"] == "ok"

    _write(paths["exports"] / "2024-Advanced-PBP-Data.csv", COLS_2023,
           [_row_2023(season="2024"), _row_2023(season="2024", yards_gained="99")])
    with pytest.raises(PbpError):
        run_pbp_ingest(export_paths=_files(paths["exports"]),
                       db_path=paths["db_path"], root=paths["root"])
    marker = json.loads(status_marker_path(paths["root"]).read_text())
    assert marker["status"] == "failed"
    assert marker["failed_stage"] == "store"


def test_zero_exports_refuses(paths):
    with pytest.raises(PbpError, match="no_exports"):
        run_pbp_ingest(export_paths=[], db_path=paths["db_path"], root=paths["root"])
