"""PlayerProfiler Advanced Gamelog — layer 1 contract tests.

Anchored to facts measured from the live 2020-2025 exports on 2026-08-01. The two suites
that matter are NA semantics (the null token changed meaning mid-archive) and duplicate
keying (two of them were real, and one was the vendor attributing one game to two players).
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import pytest

from src.dynasty_genius.playerprofiler import CANONICAL_RESOLVED, CONFLICT
from src.dynasty_genius.playerprofiler_gamelog import (
    COLUMN_RENAMES,
    GAMELOG_TABLE,
    NA_AMBIGUOUS,
    NA_MEANS_NO_OPPORTUNITY,
    NA_UNCLASSIFIED,
    GamelogError,
    classify_na_semantics,
    column_availability,
    read_gamelog_export,
    run_gamelog_ingest,
    status_marker_path,
)
from src.dynasty_genius.playerprofiler_roster import run_roster_key_ingest

# 2021+ shape (subset of the real 117-column file, real spellings)
MODERN = ["player", "name", "week", "position", "team", "opponent", "snaps", "snap_share",
          "routes_run", "targets", "receptions", "target_share", "hog_rate",
          "yards_created_receiving", "routes_vs_man", "passing_yards", "rushing_yards"]
# 2020 shape — different names for the same measurements
LAUNCH = ["player_id", "name", "week", "season", "position", "team", "opponent", "snaps",
          "snap_share", "routes_run", "targets", "receptions", "target_share", "hog_rate",
          "man_coverage_routes", "pass_yards", "rush_yards"]

ROSTER_GSIS = ["player_id", "name", "week", "team", "number", "position", "dob"]
ROSTER_AGE = ["player_id", "name", "week", "team", "number", "position", "age"]


def _write(path: Path, columns: list[str], rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})
    return path


def _modern(**over) -> dict:
    base = {"player": "00-0036322", "name": "Justin Jefferson", "week": "1",
            "position": "WR", "team": "MIN", "opponent": "GB", "snaps": "60",
            "snap_share": "0.90", "routes_run": "40", "targets": "10", "receptions": "7",
            "target_share": "0.28", "hog_rate": "0.25", "yards_created_receiving": "35",
            "routes_vs_man": "12", "passing_yards": "0", "rushing_yards": "0"}
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
    """The gamelog requires the roster key's bridge, so build a real one first."""
    _write(paths["roster"] / "2022-Weekly-Roster-Key.csv", ROSTER_AGE, [
        {"player_id": "JJ-1000", "name": "Justin Jefferson", "week": "1", "team": "MIN",
         "number": "18", "position": "WR", "age": "23"}])
    _write(paths["roster"] / "2023-Weekly-Roster-Key.csv", ROSTER_GSIS, [
        {"player_id": "00-0036322", "name": "Justin Jefferson", "week": "1", "team": "MIN",
         "number": "18", "position": "WR", "dob": "06/16/1999"}])
    run_roster_key_ingest(export_paths=_files(paths["roster"]),
                          db_path=paths["db_path"], root=paths["root"])
    return paths


# --- NA semantics: the most dangerous thing in this dataset -----------------------

def test_na_is_safe_as_zero_only_when_it_never_co_occurs_with_opportunity(tmp_path):
    """MEASURED on 2021: snap_share is NA on 12 rows, ALL with zero snaps — so NA there
    means 'no opportunity' and reads as zero."""
    path = _write(tmp_path / "2021-Advanced-Gamelog.csv", MODERN, [
        _modern(snaps="0", snap_share="NA"),
        _modern(week="2", snaps="60", snap_share="0.9"),
    ])
    result = classify_na_semantics([read_gamelog_export(path)])
    assert result["columns"]["snap_share"]["verdict"] == NA_MEANS_NO_OPPORTUNITY
    assert "snap_share" in result["safe_to_zero_fill"]


def test_na_alongside_real_opportunity_is_ambiguous_and_never_zero_filled(tmp_path):
    """MEASURED on 2021: yards_created_receiving is NA on 3,178 rows with zero receptions
    AND on 3,802 rows that HAD receptions. Zero-filling would invent 3,802 measurements
    that were never taken — and the invented zeros would drag every average down."""
    path = _write(tmp_path / "2021-Advanced-Gamelog.csv", MODERN, [
        _modern(receptions="0", yards_created_receiving="NA"),
        _modern(week="2", receptions="7", yards_created_receiving="NA"),
    ])
    result = classify_na_semantics([read_gamelog_export(path)])
    entry = result["columns"]["yards_created_receiving"]
    assert entry["verdict"] == NA_AMBIGUOUS
    assert entry["na_with_nonzero_denominator"] == 1
    assert "yards_created_receiving" in result["never_zero_fill"]
    assert "yards_created_receiving" not in result["safe_to_zero_fill"]


def test_a_column_with_no_declared_denominator_is_unclassified_not_assumed_safe(tmp_path):
    """Conservative by construction: proving nothing must not read as proving safety."""
    path = _write(tmp_path / "2021-Advanced-Gamelog.csv", MODERN,
                  [_modern(passing_yards="NA")])
    result = classify_na_semantics([read_gamelog_export(path)])
    assert result["columns"]["passing_yards"]["verdict"] == NA_UNCLASSIFIED
    assert "passing_yards" in result["unclassified"]
    assert "passing_yards" not in result["safe_to_zero_fill"]


def test_na_is_stored_as_null_never_coerced(paths, with_bridge):
    """The adapter stores NULL and publishes the classification; it does not decide."""
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN,
           [_modern(yards_created_receiving="NA")])
    run_gamelog_ingest(export_paths=_files(paths["exports"]),
                       db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    got = conn.execute(
        f"SELECT yards_created_receiving FROM {GAMELOG_TABLE}").fetchone()[0]
    assert got is None, "NA was coerced instead of stored as NULL"


# --- the 2020 rename era ----------------------------------------------------------

def test_2020_names_map_onto_the_canonical_modern_names(paths, with_bridge):
    """2020 ships pass_yards/rush_yards/man_coverage_routes; 2021+ ships
    passing_yards/rushing_yards/routes_vs_man. Verified numerically before mapping."""
    _write(paths["exports"] / "2020-Advanced-Gamelog.csv", LAUNCH, [{
        "player_id": "JJ-1000", "name": "Justin Jefferson", "week": "1", "season": "2020",
        "position": "WR", "team": "MIN", "opponent": "GB", "snaps": "60",
        "snap_share": "0.9", "routes_run": "40", "targets": "10", "receptions": "7",
        "target_share": "0.28", "hog_rate": "0.25", "man_coverage_routes": "12",
        "pass_yards": "0", "rush_yards": "15"}])
    run_gamelog_ingest(export_paths=_files(paths["exports"]),
                       db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({GAMELOG_TABLE})")]
    assert "rushing_yards" in cols and "routes_vs_man" in cols
    assert "rush_yards" not in cols, "the 2020 spelling survived instead of being mapped"
    assert conn.execute(f"SELECT rushing_yards FROM {GAMELOG_TABLE}").fetchone()[0] == "15"


def test_unreconcilable_pairs_are_deliberately_not_in_the_rename_map():
    """carries_inside_10 / carries_inside_5 (2020) vs carries_inside (2021+) is a
    two-into-one merge on an unstated threshold. Mapping it would silently fuse two
    different measurements, so it is absent — and must STAY absent."""
    for never_map in ("carries_inside_10", "carries_inside_5", "opportunity_share",
                      "juke_rate", "average_cushion"):
        assert never_map not in COLUMN_RENAMES


# --- availability windows ---------------------------------------------------------

def test_column_availability_records_the_post_2024_coverage_blind_window(tmp_path):
    """MEASURED: the 2025 file dropped all nine man/zone coverage columns. Absent is not
    zero — an average over 2021-2025 would divide a four-season sum by five."""
    a = _write(tmp_path / "a" / "2024-Advanced-Gamelog.csv", MODERN, [_modern()])
    b = _write(tmp_path / "b" / "2025-Advanced-Gamelog.csv",
               [c for c in MODERN if c != "routes_vs_man"],
               [{k: v for k, v in _modern().items() if k != "routes_vs_man"}])
    result = column_availability([read_gamelog_export(a), read_gamelog_export(b)])
    assert "routes_vs_man" in result["columns_with_gaps"]
    assert result["columns_with_gaps"]["routes_vs_man"]["absent"] == ["2025"]
    assert "routes_vs_man" not in result["columns_in_every_season"]
    assert "snap_share" in result["columns_in_every_season"]


# --- duplicate keying: two real defects -------------------------------------------

def test_exact_duplicate_rows_are_dropped_silently_because_they_carry_no_information(
        paths, with_bridge):
    """MEASURED: the 2020 file ships each of Lynn Bowden's week-14 games twice, byte for
    byte. An exact duplicate adds nothing, so collapsing it loses nothing."""
    row = _modern()
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN, [row, dict(row)])
    status = run_gamelog_ingest(export_paths=_files(paths["exports"]),
                                db_path=paths["db_path"], root=paths["root"])
    assert status["rows"]["gamelog_week"] == 1
    assert status["exact_duplicate_rows_dropped"] == {"2023": 1}


def test_two_distinct_games_under_one_week_label_both_survive(paths, with_bridge):
    """MEASURED: Lynn Bowden has TWO different 2020 week-14 games (vs WAS and vs KC) — one
    week label is wrong at source. Keying on week alone would delete a real game."""
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN, [
        _modern(opponent="WAS", targets="1"),
        _modern(opponent="KC", targets="9"),
    ])
    status = run_gamelog_ingest(export_paths=_files(paths["exports"]),
                                db_path=paths["db_path"], root=paths["root"])
    assert status["rows"]["gamelog_week"] == 2
    conn = sqlite3.connect(paths["db_path"])
    assert {r[0] for r in conn.execute(f"SELECT opponent FROM {GAMELOG_TABLE}")} == {"WAS", "KC"}


def test_two_players_sharing_one_id_both_survive_and_neither_resolves(paths):
    """MEASURED: DM-3050 is two David Moores and SB-9929 is two Spencer Browns. In 2021
    they appear in the same week against the same opponent with identical stat lines,
    differing only by team — the vendor attributed one game to both. Both rows must
    survive and NEITHER may be resolved to a canonical id."""
    _write(paths["roster"] / "2022-Weekly-Roster-Key.csv", ROSTER_AGE, [
        {"player_id": "DM-3050", "name": "David Moore", "week": "1", "team": "CLE",
         "number": "1", "position": "WR", "age": "27"},
        {"player_id": "DM-3050", "name": "David Moore", "week": "1", "team": "GB",
         "number": "2", "position": "WR", "age": "26"},
        {"player_id": "JJ-1000", "name": "Justin Jefferson", "week": "1", "team": "MIN",
         "number": "18", "position": "WR", "age": "23"}])
    _write(paths["roster"] / "2023-Weekly-Roster-Key.csv", ROSTER_GSIS, [
        {"player_id": "00-0033891", "name": "David Moore", "week": "1", "team": "CLE",
         "number": "1", "position": "WR", "dob": "01/01/1995"},
        {"player_id": "00-0036322", "name": "Justin Jefferson", "week": "1", "team": "MIN",
         "number": "18", "position": "WR", "dob": "06/16/1999"}])
    run_roster_key_ingest(export_paths=_files(paths["roster"]),
                          db_path=paths["db_path"], root=paths["root"])

    _write(paths["exports"] / "2022-Advanced-Gamelog.csv", MODERN, [
        _modern(player="DM-3050", name="David Moore", team="CLE", opponent="MIN"),
        _modern(player="DM-3050", name="David Moore", team="GB", opponent="MIN"),
    ])
    status = run_gamelog_ingest(export_paths=_files(paths["exports"]),
                                db_path=paths["db_path"], root=paths["root"])
    assert status["rows"]["gamelog_week"] == 2, "a colliding player's game was dropped"
    conn = sqlite3.connect(paths["db_path"])
    rows = conn.execute(
        f"SELECT team, identity_status, dg_player_id FROM {GAMELOG_TABLE}").fetchall()
    assert {r[0] for r in rows} == {"CLE", "GB"}
    assert {r[1] for r in rows} == {CONFLICT}
    assert {r[2] for r in rows} == {None}


def test_conflicting_rows_sharing_a_key_refuse(paths, with_bridge):
    """If two rows share a key and DISAGREE, one is a real measurement that would be
    silently deleted. Refuse instead of picking."""
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN, [
        _modern(targets="10"),
        _modern(targets="4"),   # same key, different measurement
    ])
    with pytest.raises(GamelogError, match="conflicting_duplicate_rows"):
        run_gamelog_ingest(export_paths=_files(paths["exports"]),
                           db_path=paths["db_path"], root=paths["root"])


# --- identity + run contract ------------------------------------------------------

def test_gsis_era_is_vendor_supplied_pp_era_goes_through_the_bridge(paths, with_bridge):
    _write(paths["exports"] / "2022-Advanced-Gamelog.csv", MODERN,
           [_modern(player="JJ-1000")])
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN,
           [_modern(player="00-0036322")])
    status = run_gamelog_ingest(export_paths=_files(paths["exports"]),
                                db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    ids = {r[0] for r in conn.execute(f"SELECT dg_player_id FROM {GAMELOG_TABLE}")}
    assert ids == {"00-0036322"}, "the two eras did not land on one canonical id"
    assert status["coverage"]["by_identity_status"][CANONICAL_RESOLVED] == 2
    assert status["coverage"]["vendor_supplied_share"] == 0.5


def test_ingest_without_the_roster_bridge_refuses(paths):
    """Without the bridge every pre-2023 row is unidentifiable, and the run would look
    perfectly healthy while resolving nothing."""
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN, [_modern()])
    with pytest.raises(GamelogError, match="bridge_missing"):
        run_gamelog_ingest(export_paths=_files(paths["exports"]),
                           db_path=paths["db_path"], root=paths["root"])


def test_season_label_mismatch_between_filename_and_content_refuses(tmp_path):
    """The 2020 file carries its own season column. If it disagrees with the filename one
    of them is wrong, and picking either silently files a season's rows under a lie."""
    path = _write(tmp_path / "2021-Advanced-Gamelog.csv", LAUNCH, [{
        "player_id": "JJ-1000", "name": "X", "week": "1", "season": "2020",
        "position": "WR", "team": "MIN", "opponent": "GB", "snaps": "1",
        "snap_share": "0.1", "routes_run": "1", "targets": "1", "receptions": "1",
        "target_share": "0.1", "hog_rate": "0.1", "man_coverage_routes": "1",
        "pass_yards": "0", "rush_yards": "0"}])
    with pytest.raises(GamelogError, match="season_label_mismatch"):
        read_gamelog_export(path)


def test_stored_rows_equal_marker_rows_equal_coverage_rows(paths, with_bridge):
    """The roster key's marker once over-reported by exactly the number of rows dropped.
    All three counts must agree or rows are going missing."""
    row = _modern()
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN,
           [row, dict(row), _modern(week="2")])
    status = run_gamelog_ingest(export_paths=_files(paths["exports"]),
                                db_path=paths["db_path"], root=paths["root"])
    conn = sqlite3.connect(paths["db_path"])
    stored = conn.execute(f"SELECT COUNT(*) FROM {GAMELOG_TABLE}").fetchone()[0]
    assert stored == status["rows"]["gamelog_week"] == status["coverage"]["rows_total"] == 2


def test_rerun_is_content_idempotent(paths, with_bridge):
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN,
           [_modern(), _modern(week="2")])
    kw = dict(export_paths=_files(paths["exports"]), db_path=paths["db_path"],
              root=paths["root"])
    first = run_gamelog_ingest(**kw)
    second = run_gamelog_ingest(**kw)
    assert first["rows"] == second["rows"]
    assert set(second["applied"].values()) == {"unchanged"}


def test_failure_writes_a_named_marker(paths, with_bridge):
    _write(paths["exports"] / "2023-Advanced-Gamelog.csv", MODERN, [_modern()])
    kw = dict(export_paths=_files(paths["exports"]), db_path=paths["db_path"],
              root=paths["root"])
    run_gamelog_ingest(**kw)
    assert json.loads(status_marker_path(paths["root"]).read_text())["status"] == "ok"

    _write(paths["exports"] / "2024-Advanced-Gamelog.csv", MODERN,
           [_modern(week="1"), _modern(week="1", targets="99")])
    with pytest.raises(GamelogError):
        run_gamelog_ingest(export_paths=_files(paths["exports"]),
                           db_path=paths["db_path"], root=paths["root"])
    marker = json.loads(status_marker_path(paths["root"]).read_text())
    assert marker["status"] == "failed"
    assert marker["failed_stage"] == "store"


def test_zero_exports_refuses(paths):
    with pytest.raises(GamelogError, match="no_exports"):
        run_gamelog_ingest(export_paths=[], db_path=paths["db_path"], root=paths["root"])
