"""PlayerProfiler Weekly Roster Key — layer 1 contract tests.

Anchored to facts measured from the live 2020-2025 exports on 2026-08-01. The centrepiece
is the collision suite: PlayerProfiler's internal id is initials-plus-a-number, so it can
stand for two humans, and the first cut of this adapter silently deleted one of them.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import pytest

from src.dynasty_genius.playerprofiler import CANONICAL_RESOLVED, CONFLICT, UNKNOWN
from src.dynasty_genius.playerprofiler_roster import (
    BASIS_NAME_BRIDGE,
    BASIS_VENDOR_GSIS,
    NAMESPACE_GSIS,
    NAMESPACE_PP_INTERNAL,
    ROSTER_TABLE,
    SOURCE_ID_COLLISION,
    RosterKeyError,
    build_identity_bridge,
    discover_roster_exports,
    find_colliding_source_ids,
    read_roster_export,
    run_roster_key_ingest,
    status_marker_path,
    verify_season_ordering,
)

GSIS_COLUMNS = ["player_id", "name", "week", "team", "number", "position", "dob"]
AGE_COLUMNS = ["player_id", "name", "week", "team", "number", "position", "age"]
LAUNCH_COLUMNS = ["week", "team", "jersey_number", "name", "player_id"]


def _write(path: Path, columns: list[str], rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        w = csv.DictWriter(handle, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})
    return path


def _gsis_rows(players: list[tuple[str, str, str]], weeks: int = 2) -> list[dict]:
    """players = [(gsis_id, name, position)]"""
    return [
        {"player_id": pid, "name": name, "week": str(w), "team": "MIN",
         "number": "1", "position": pos, "dob": "01/01/1995"}
        for pid, name, pos in players for w in range(1, weeks + 1)
    ]


def _age_rows(players: list[tuple[str, str, str, str]], weeks: int = 2) -> list[dict]:
    """players = [(pp_id, name, position, team)]"""
    return [
        {"player_id": pid, "name": name, "week": str(w), "team": team,
         "number": "1", "position": pos, "age": "27"}
        for pid, name, pos, team in players for w in range(1, weeks + 1)
    ]


@pytest.fixture()
def paths(tmp_path: Path) -> dict:
    return {"db_path": tmp_path / "pp.db", "root": tmp_path / "root",
            "exports": tmp_path / "exports"}


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in Path(folder).iterdir() if p.is_file())


# --- the collision suite: the bug that silently deleted players --------------------

def test_same_week_two_teams_is_a_collision_not_a_duplicate(tmp_path):
    """MEASURED: AS-2100 is Andre Smith the LB (BUF) and Andre Smith the OT (BAL), both
    listed in week 1. One human cannot be on two teams in one week, so this is two humans
    sharing an id — not a duplicate row to be deduplicated away."""
    path = _write(tmp_path / "2021-Weekly-Roster-Key.csv", AGE_COLUMNS, _age_rows([
        ("AS-2100", "Andre Smith", "LB", "BUF"),
        ("AS-2100", "Andre Smith", "OT", "BAL"),
    ]))
    collisions = find_colliding_source_ids([read_roster_export(path)])
    assert "AS-2100" in collisions
    assert collisions["AS-2100"]["reason"] == "same_week_two_teams"


def test_same_week_two_names_is_a_collision(tmp_path):
    """MEASURED: KD-0111 is Kalia Davis AND Kellen Diesch — not even the same name."""
    path = _write(tmp_path / "2022-Weekly-Roster-Key.csv", AGE_COLUMNS, _age_rows([
        ("KD-0111", "Kalia Davis", "DL", "SF"),
        ("KD-0111", "Kellen Diesch", "OL", "CHI"),
    ]))
    assert "KD-0111" in find_colliding_source_ids([read_roster_export(path)])


def test_nickname_variants_across_seasons_are_NOT_collisions(tmp_path):
    """MEASURED and deliberately excluded: Matt/Matthew Judon, Mike/Michael Badgley, and
    Robby Anderson -> Robbie Chosen (a legal name change) are ONE human under a STABLE id.
    Flagging these would bury the 13 real collisions under 85 false ones — and it would
    also invert the lesson, which is that the id is more stable than the name."""
    a = _write(tmp_path / "a" / "2021-Weekly-Roster-Key.csv", AGE_COLUMNS,
               _age_rows([("MJ-1000", "Matt Judon", "LB", "NE")]))
    b = _write(tmp_path / "b" / "2022-Weekly-Roster-Key.csv", AGE_COLUMNS,
               _age_rows([("MJ-1000", "Matthew Judon", "LB", "NE")]))
    assert find_colliding_source_ids([read_roster_export(a), read_roster_export(b)]) == {}


def test_position_label_drift_alone_is_not_a_collision(tmp_path):
    """MEASURED: 1,836 ids show position drift for one name (RB->FB, OL->OT). Benign."""
    a = _write(tmp_path / "a" / "2021-Weekly-Roster-Key.csv", AGE_COLUMNS,
               _age_rows([("CM-1850", "Connor McGovern", "C", "DAL")]))
    b = _write(tmp_path / "b" / "2022-Weekly-Roster-Key.csv", AGE_COLUMNS,
               _age_rows([("CM-1850", "Connor McGovern", "G", "DAL")]))
    assert find_colliding_source_ids([read_roster_export(a), read_roster_export(b)]) == {}


def test_a_colliding_id_is_never_bridged_to_a_single_canonical_id(tmp_path):
    """The consequence that matters. Bridging a two-human id to ONE canonical id merges two
    careers, and the merged result looks perfectly clean downstream — no null, no error.
    The first cut of this module confidently bridged 94 such ids."""
    old = _write(tmp_path / "a" / "2022-Weekly-Roster-Key.csv", AGE_COLUMNS, _age_rows([
        ("AS-2100", "Andre Smith", "LB", "BUF"),
        ("AS-2100", "Andre Smith", "OT", "BAL"),
    ]))
    new = _write(tmp_path / "b" / "2023-Weekly-Roster-Key.csv", GSIS_COLUMNS,
                 _gsis_rows([("00-0034430", "Andre Smith", "OT")]))
    bridge = build_identity_bridge([read_roster_export(old), read_roster_export(new)])
    record = next(r for r in bridge["records"] if r["pp_player_id"] == "AS-2100")
    assert record["bridge_status"] == SOURCE_ID_COLLISION
    assert record["dg_player_id"] is None, "a two-human id must not resolve to one player"
    assert bridge["summary"]["source_id_collision_held"] == 1


def test_collision_rows_both_survive_ingest(tmp_path, paths):
    """REGRESSION. The row key was (season, week, player_id), so the second Andre Smith
    overwrote the first and one real player vanished with no error and no warning. Both
    rows must survive, and both must be marked CONFLICT rather than resolved."""
    _write(paths["exports"] / "2022-Weekly-Roster-Key.csv", AGE_COLUMNS, _age_rows([
        ("AS-2100", "Andre Smith", "LB", "BUF"),
        ("AS-2100", "Andre Smith", "OT", "BAL"),
    ], weeks=1))
    _write(paths["exports"] / "2023-Weekly-Roster-Key.csv", GSIS_COLUMNS,
           _gsis_rows([("00-0034430", "Andre Smith", "OT")], weeks=1))
    run_roster_key_ingest(export_paths=_files(paths["exports"]),
                          db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    rows = conn.execute(
        f"SELECT team, identity_status, dg_player_id FROM {ROSTER_TABLE} "
        "WHERE source_player_id = 'AS-2100'").fetchall()
    assert len(rows) == 2, f"a collision row was silently dropped: {rows}"
    assert {r[0] for r in rows} == {"BUF", "BAL"}
    assert {r[1] for r in rows} == {CONFLICT}
    assert {r[2] for r in rows} == {None}


def test_null_sentinel_id_never_joins_players_together(tmp_path, paths):
    """MEASURED: the literal string '#N/A' is carried by Brandon Rusnak (Dallas) and CJ
    Goodwin (Jacksonville). Treated as an id it would merge every unidentified player."""
    _write(paths["exports"] / "2020-Weekly-Roster-Key.csv", LAUNCH_COLUMNS, [
        # A real id alongside the sentinels, exactly as the live 2020 file has it.
        {"week": "1", "team": "Arizona Cardinals", "jersey_number": "94",
         "name": "Zach Allen", "player_id": "ZA-0150"},
        {"week": "1", "team": "Dallas Cowboys", "jersey_number": "60",
         "name": "Brandon Rusnak", "player_id": "#N/A"},
        {"week": "1", "team": "Jacksonville Jaguars", "jersey_number": "30",
         "name": "CJ Goodwin", "player_id": "#N/A"},
    ])
    run_roster_key_ingest(export_paths=_files(paths["exports"]),
                          db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    rows = conn.execute(
        f"SELECT name, identity_status, dg_player_id, identity_candidates "
        f"FROM {ROSTER_TABLE} WHERE source_player_id = '#N/A'").fetchall()
    assert len(rows) == 2, "the two #N/A players collapsed into one row"
    assert {r[0] for r in rows} == {"Brandon Rusnak", "CJ Goodwin"}
    assert {r[1] for r in rows} == {UNKNOWN}
    assert {r[2] for r in rows} == {None}
    assert {r[3] for r in rows} == {"null_id_sentinel"}


# --- the two namespaces -----------------------------------------------------------

def test_gsis_era_is_vendor_supplied_and_pp_era_is_inferred(paths):
    """The whole point of identity_basis: an id the vendor handed us and an id we matched
    across the re-platform seam are different strengths of evidence and must stay
    distinguishable, even though both populate dg_player_id."""
    _write(paths["exports"] / "2022-Weekly-Roster-Key.csv", AGE_COLUMNS,
           _age_rows([("JJ-1000", "Justin Jefferson", "WR", "MIN")], weeks=1))
    _write(paths["exports"] / "2023-Weekly-Roster-Key.csv", GSIS_COLUMNS,
           _gsis_rows([("00-0036322", "Justin Jefferson", "WR")], weeks=1))
    run_roster_key_ingest(export_paths=_files(paths["exports"]),
                          db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    got = dict(conn.execute(
        f"SELECT id_namespace, identity_basis FROM {ROSTER_TABLE}").fetchall())
    assert got[NAMESPACE_GSIS] == BASIS_VENDOR_GSIS
    assert got[NAMESPACE_PP_INTERNAL] == BASIS_NAME_BRIDGE
    # ...and both landed on the SAME canonical id.
    ids = {r[0] for r in conn.execute(f"SELECT dg_player_id FROM {ROSTER_TABLE}")}
    assert ids == {"00-0036322"}


def test_mixed_namespace_file_refuses(tmp_path):
    """A file straddling both namespaces cannot be assigned one, and storing it would put
    non-comparable ids in the same column."""
    path = _write(tmp_path / "2023-Weekly-Roster-Key.csv", GSIS_COLUMNS, [
        {"player_id": "00-0036322", "name": "A", "week": "1", "team": "MIN",
         "number": "1", "position": "WR", "dob": "01/01/1999"},
        {"player_id": "JJ-1000", "name": "B", "week": "1", "team": "MIN",
         "number": "2", "position": "WR", "dob": "01/01/1999"},
    ])
    with pytest.raises(RosterKeyError, match="mixed_id_namespace"):
        read_roster_export(path)


def test_unknown_schema_era_refuses_rather_than_guessing(tmp_path):
    """PlayerProfiler re-platformed once and changed the id namespace when it did. An
    unknown era silently mapped onto a known one is how a whole season's ids become wrong."""
    path = _write(tmp_path / "2026-Weekly-Roster-Key.csv",
                  ["player_id", "name", "week", "team", "surprise"],
                  [{"player_id": "00-0036322", "name": "A", "week": "1",
                    "team": "MIN", "surprise": "x"}])
    with pytest.raises(RosterKeyError, match="unknown_schema_era"):
        read_roster_export(path)


# --- season labels are filename-derived, so they get checked ----------------------

def test_season_ordering_accepts_real_consecutive_rosters(tmp_path):
    """MEASURED on the live files: adjacent overlap runs 76-89%."""
    shared = [("JJ-1000", f"Player {i}", "WR", "MIN") for i in range(20)]
    a = _write(tmp_path/"a"/"2021-Weekly-Roster-Key.csv", AGE_COLUMNS,
               _age_rows([(f"P{i}-1", f"Player {i}", "WR", "MIN") for i in range(20)], weeks=1))
    b = _write(tmp_path/"b"/"2022-Weekly-Roster-Key.csv", AGE_COLUMNS,
               _age_rows([(f"P{i}-1", f"Player {i}", "WR", "MIN") for i in range(2, 22)], weeks=1))
    result = verify_season_ordering([read_roster_export(a), read_roster_export(b)])
    assert result["ordering_consistent"] is True
    assert result["adjacent_overlap"][0]["overlap"] >= 0.35
    del shared


def test_season_ordering_refuses_disjoint_adjacent_seasons(tmp_path):
    """The roster key has no season column, so the filename is the only label. A file whose
    roster looks nothing like its claimed neighbour is mislabeled, and that has to be caught
    before its rows are stored under a wrong season."""
    a = _write(tmp_path/"a"/"2021-Weekly-Roster-Key.csv", AGE_COLUMNS,
               _age_rows([(f"A{i}-1", f"Alpha {i}", "WR", "MIN") for i in range(20)], weeks=1))
    b = _write(tmp_path/"b"/"2022-Weekly-Roster-Key.csv", AGE_COLUMNS,
               _age_rows([(f"B{i}-1", f"Beta {i}", "WR", "MIN") for i in range(20)], weeks=1))
    with pytest.raises(RosterKeyError, match="season_ordering_implausible"):
        verify_season_ordering([read_roster_export(a), read_roster_export(b)])


def test_two_files_for_one_season_with_different_content_refuses(tmp_path):
    a = _write(tmp_path/"a"/"2023-Weekly-Roster-Key.csv", GSIS_COLUMNS,
               _gsis_rows([("00-0036322", "A", "WR")], weeks=1))
    b = _write(tmp_path/"b"/"2023-Weekly-Roster-Key.csv", GSIS_COLUMNS,
               _gsis_rows([("00-0037240", "B", "WR")], weeks=1))
    with pytest.raises(RosterKeyError, match="conflicting_season_files"):
        discover_roster_exports([a, b])


# --- run contract -----------------------------------------------------------------

def test_rerun_is_content_idempotent(paths):
    _write(paths["exports"] / "2023-Weekly-Roster-Key.csv", GSIS_COLUMNS,
           _gsis_rows([("00-0036322", "Justin Jefferson", "WR"),
                       ("00-0037240", "Garrett Wilson", "WR")]))
    kw = dict(export_paths=_files(paths["exports"]), db_path=paths["db_path"],
              root=paths["root"])
    first = run_roster_key_ingest(**kw)
    second = run_roster_key_ingest(**kw)
    assert first["rows"] == second["rows"]
    assert set(second["applied"].values()) == {"unchanged"}, second["applied"]


def test_stored_row_count_matches_the_marker(paths):
    """The marker counted pre-dedup rows while the store held post-dedup rows, so the
    marker over-reported by exactly the number of rows silently dropped. If these two ever
    disagree again, rows are going missing."""
    _write(paths["exports"] / "2022-Weekly-Roster-Key.csv", AGE_COLUMNS, _age_rows([
        ("AS-2100", "Andre Smith", "LB", "BUF"),
        ("AS-2100", "Andre Smith", "OT", "BAL"),
        ("JJ-1000", "Justin Jefferson", "WR", "MIN"),
    ]))
    status = run_roster_key_ingest(export_paths=_files(paths["exports"]),
                                   db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    stored = conn.execute(f"SELECT COUNT(*) FROM {ROSTER_TABLE}").fetchone()[0]
    assert stored == status["rows"]["roster_week"]


def test_failure_writes_a_named_marker_not_a_stale_ok(paths):
    _write(paths["exports"] / "2023-Weekly-Roster-Key.csv", GSIS_COLUMNS,
           _gsis_rows([("00-0036322", "A", "WR")], weeks=1))
    kw = dict(export_paths=_files(paths["exports"]), db_path=paths["db_path"],
              root=paths["root"])
    run_roster_key_ingest(**kw)
    assert json.loads(status_marker_path(paths["root"]).read_text())["status"] == "ok"

    _write(paths["exports"] / "2024-Weekly-Roster-Key.csv",
           ["player_id", "name", "week", "nope"],
           [{"player_id": "00-0036322", "name": "A", "week": "1", "nope": "x"}])
    with pytest.raises(RosterKeyError):
        run_roster_key_ingest(export_paths=_files(paths["exports"]),
                              db_path=paths["db_path"], root=paths["root"])
    marker = json.loads(status_marker_path(paths["root"]).read_text())
    assert marker["status"] == "failed"
    assert marker["failed_stage"] == "discover"


def test_zero_exports_refuses(paths):
    paths["exports"].mkdir(parents=True, exist_ok=True)
    with pytest.raises(RosterKeyError, match="no_exports"):
        run_roster_key_ingest(export_paths=[], db_path=paths["db_path"],
                              root=paths["root"])


def test_coverage_separates_vendor_ids_from_inferred_ids(paths):
    """A blended 'canonical' count would hide that 40% of the identified rows rest on a
    name match rather than a vendor id."""
    _write(paths["exports"] / "2022-Weekly-Roster-Key.csv", AGE_COLUMNS,
           _age_rows([("JJ-1000", "Justin Jefferson", "WR", "MIN")], weeks=1))
    _write(paths["exports"] / "2023-Weekly-Roster-Key.csv", GSIS_COLUMNS,
           _gsis_rows([("00-0036322", "Justin Jefferson", "WR")], weeks=1))
    status = run_roster_key_ingest(export_paths=_files(paths["exports"]),
                                   db_path=paths["db_path"], root=paths["root"])
    basis = status["coverage"]["by_identity_basis"]
    assert basis[BASIS_VENDOR_GSIS] == 1
    assert basis[BASIS_NAME_BRIDGE] == 1
    assert status["coverage"]["vendor_supplied_share"] == 0.5
    assert status["coverage"]["by_identity_status"][CANONICAL_RESOLVED] == 2
