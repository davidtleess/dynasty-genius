"""PlayerProfiler ingest — layer 1 contract tests.

Every test here is a named failure the live 2026-07-31 exports actually produced, or a
refusal the adapter must make rather than store something untrustworthy. They run on
synthetic fixtures so they are hermetic, but each one is anchored to a measured fact from
the real subscriber exports — noted in the test's own docstring.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import pytest

from src.dynasty_genius.playerprofiler import (
    CANONICAL_RESOLVED,
    CONFLICT,
    MEDICAL_COVERAGE_END,
    UNKNOWN,
    NameIdentityIndex,
    PlayerProfilerError,
    PlayerProfilerStore,
    _medical_universe_split,
    check_medical_schema,
    medical_blind_window,
    read_export,
    run_playerprofiler_ingest,
    status_marker_path,
)

# --- fixtures ---------------------------------------------------------------------

#: Column names taken VERBATIM from the live 2026-07-31 export (lowercase, and the
#: digit-leading combine columns are the point). The real file carries 317 columns; these
#: are the ones the adapter reasons about, in their real spelling.
SEASON_COLUMNS = [
    "name", "position", "status", "current_team", "season", "draft_year", "college",
    "40_yard_dash", "3_cone_drill", "20_yard_shuttle", "breakout_age", "target_share",
]

MEDICAL_COLUMNS = [
    "Player", "Player_ID", "Team", "Injury Description", "Body Part", "Severity",
    "Incident Date", "Year", "Games Missed", "Games On Injury Report", "Surgery",
    "Recovery Timetable",
]


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})
    return path


def _season_row(name: str, **over) -> dict:
    base = {
        "name": name, "position": "WR", "status": "Active", "current_team": "MIN",
        "season": "2025", "draft_year": "2022", "college": "Ohio State",
        "40_yard_dash": "4.41", "3_cone_drill": "6.88", "20_yard_shuttle": "4.19",
        "breakout_age": "19.4", "target_share": "0.291",
    }
    base.update(over)
    return base


def _medical_row(name: str, year: str, **over) -> dict:
    base = {
        "Player": name, "Player_ID": "JS-1000", "Team": "MIN",
        "Injury Description": "Hamstring strain", "Body Part": "Hamstring",
        "Severity": "Moderate", "Incident Date": f"{year}-10-04", "Year": year,
        "Games Missed": "2", "Games On Injury Report": "3", "Surgery": "No",
        "Recovery Timetable": "2-4 weeks",
    }
    base.update(over)
    return base


@pytest.fixture()
def identity(tmp_path: Path) -> NameIdentityIndex:
    """A two-player governed crosswalk, one of which is a deliberate name collision."""
    payload = {"entries": [
        {"gsis_id": "00-0036322", "name": "Justin Jefferson",
         "draft_year": 2020, "college": "LSU"},
        {"gsis_id": "00-0037240", "name": "Garrett Wilson",
         "draft_year": 2022, "college": "Ohio State"},
        # Two Mike Williamses, distinguishable only by draft year / college.
        {"gsis_id": "00-0033536", "name": "Mike Williams",
         "draft_year": 2017, "college": "Clemson"},
        {"gsis_id": "00-0027702", "name": "Mike Williams",
         "draft_year": 2010, "college": "Syracuse"},
    ]}
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return NameIdentityIndex.from_governed_crosswalk(path)


@pytest.fixture()
def paths(tmp_path: Path) -> dict:
    return {"db_path": tmp_path / "pp.db", "root": tmp_path / "pp_root",
            "exports": tmp_path / "exports"}


def _files(folder: Path) -> list[Path]:
    """``run_playerprofiler_ingest`` takes FILE paths; the CLI does the globbing."""
    return sorted(p for p in Path(folder).iterdir() if p.is_file())


# --- the regression that actually bit ---------------------------------------------

def test_digit_leading_column_names_survive_ddl_and_insert(identity, paths):
    """REGRESSION: `20_yard_shuttle` is not a legal bare SQLite identifier.

    The live export ships `40_yard_dash`, `3_cone_drill` and `20_yard_shuttle`. SQLite
    rejects an unquoted identifier starting with a digit, and the first live run died with
    `unrecognized token: "20_yard_shuttle"` inside CREATE TABLE. The fix quotes rather than
    renames, so the stored column still matches the vendor's documentation — which means
    this test must assert the ORIGINAL name round-trips, not merely that no error is raised.
    """
    _write_csv(paths["exports"] / "data_analysis_report-WR-2025.csv", SEASON_COLUMNS,
               [_season_row("Garrett Wilson")])
    run_playerprofiler_ingest(export_paths=_files(paths["exports"]), identity=identity,
                              db_path=paths["db_path"], root=paths["root"])

    conn = sqlite3.connect(paths["db_path"])
    cols = [r[1] for r in conn.execute("PRAGMA table_info(pp_player_season)")]
    for expected in ("20_yard_shuttle", "3_cone_drill", "40_yard_dash"):
        assert expected in cols, f"{expected} was renamed away instead of quoted"
    # And the VALUE landed, not just the column.
    got = conn.execute('SELECT "40_yard_dash", "20_yard_shuttle" FROM pp_player_season').fetchone()
    assert got == ("4.41", "4.19")


# --- identity ---------------------------------------------------------------------

def test_ambiguous_name_is_held_as_conflict_never_guessed(identity):
    """Two Mike Williamses exist. An export row with neither draft year nor college
    cannot be told apart, and resolving it would silently attach one player's injuries to
    another. It must come back CONFLICT with both candidates named."""
    dg, status, candidates = identity.resolve("Mike Williams")
    assert status == CONFLICT
    assert dg is None, "a conflict must not carry a resolved id"
    assert set(candidates) == {"00-0033536", "00-0027702"}


def test_disambiguation_by_draft_year_resolves_the_collision(identity):
    dg, status, _ = identity.resolve("Mike Williams", draft_year="2017")
    assert (status, dg) == (CANONICAL_RESOLVED, "00-0033536")


def test_unknown_name_is_unknown_not_conflict(identity):
    dg, status, _ = identity.resolve("Nobody Atall")
    assert (status, dg) == (UNKNOWN, None)


def test_empty_crosswalk_refuses(tmp_path):
    """An empty universe would resolve everything to `unknown` and look like a clean run."""
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"entries": []}), encoding="utf-8")
    with pytest.raises(PlayerProfilerError, match="governed_crosswalk_empty"):
        NameIdentityIndex.from_governed_crosswalk(path)


# --- schema drift -----------------------------------------------------------------

def _medical_export(tmp_path: Path, year: str, columns: list[str]) -> "object":
    path = _write_csv(tmp_path / f"MedicalHistory_{year}.csv", columns,
                      [_medical_row("Garrett Wilson", year)])
    return read_export(path)


def test_additive_medical_drift_is_accepted(tmp_path):
    """Measured: medical grew 12 -> 17 columns across 2017-2023, only ever adding."""
    exports = [
        _medical_export(tmp_path / "a", "2017", list(MEDICAL_COLUMNS)),
        _medical_export(tmp_path / "b", "2023",
                        list(MEDICAL_COLUMNS) + ["Body Zone", "Injured Reserve"]),
    ]
    assert check_medical_schema(exports)["additive_only"] is True


def test_removed_medical_core_column_refuses(tmp_path):
    """A dropped column is NOT safe to union: every prior year's value would read as
    missing, which is indistinguishable from 'no injury'."""
    truncated = [c for c in MEDICAL_COLUMNS if c != "Games Missed"]
    exports = [
        _medical_export(tmp_path / "a", "2017", list(MEDICAL_COLUMNS)),
        _medical_export(tmp_path / "b", "2023", truncated),
    ]
    with pytest.raises(PlayerProfilerError):
        check_medical_schema(exports)


# --- the blind window -------------------------------------------------------------

def test_medical_blind_window_is_declared_and_not_decision_grade():
    """The archive stops at 2023. The failure mode is that a naive join renders 'no
    record' identically to 'was healthy'. The boundary must be machine-readable."""
    window = medical_blind_window()
    assert window["coverage_end_season"] == MEDICAL_COVERAGE_END == 2023
    assert window["decision_supported"] is False
    assert 2025 in window["blind_seasons"]


def test_status_marker_carries_the_blind_window(identity, paths):
    _write_csv(paths["exports"] / "data_analysis_report-WR-2025.csv", SEASON_COLUMNS,
               [_season_row("Garrett Wilson")])
    _write_csv(paths["exports"] / "MedicalHistory_2023.csv", MEDICAL_COLUMNS,
               [_medical_row("Garrett Wilson", "2023")])
    run_playerprofiler_ingest(export_paths=_files(paths["exports"]), identity=identity,
                              db_path=paths["db_path"], root=paths["root"])
    marker = json.loads(status_marker_path(paths["root"]).read_text(encoding="utf-8"))
    assert marker["status"] == "ok"
    assert marker["medical_blind_window"]["decision_supported"] is False


# --- coverage reporting -----------------------------------------------------------

def test_medical_universe_split_separates_real_gap_from_out_of_universe():
    """Measured on the live archive: 1,723 unresolved medical rows, of which only 155 are
    on skill players. Reporting the blended 82.4% would indict a healthy adapter."""
    season = [{"name": "Garrett Wilson"}, {"name": "Mike Williams"}]
    medical = [
        {"player": "Garrett Wilson", "identity_status": CANONICAL_RESOLVED},
        {"player": "Mike Williams", "identity_status": CONFLICT},   # in universe: real gap
        {"player": "Alex Mack", "identity_status": UNKNOWN},        # a center: not our universe
        {"player": "Andrew Whitworth", "identity_status": UNKNOWN},  # a tackle: likewise
    ]
    split = _medical_universe_split(medical, season)
    assert split["resolved"] == 1
    assert split["in_universe_unresolved"] == 1
    assert split["out_of_universe_unresolved"] == 2
    assert split["coverage_over_modelled_universe"] == 0.5
    assert "Mike Williams" in split["in_universe_unresolved_names"]
    assert "Alex Mack" not in split["in_universe_unresolved_names"]


def test_coverage_is_reported_per_stream_never_blended(identity, paths):
    """A single blended rate describes neither stream. The marker must break it out, and
    must warn on the combined figure so no reader treats it as identity health."""
    _write_csv(paths["exports"] / "data_analysis_report-WR-2025.csv", SEASON_COLUMNS,
               [_season_row("Garrett Wilson")])
    _write_csv(paths["exports"] / "MedicalHistory_2023.csv", MEDICAL_COLUMNS,
               [_medical_row("Andrew Whitworth", "2023")])
    status = run_playerprofiler_ingest(export_paths=_files(paths["exports"]), identity=identity,
                                       db_path=paths["db_path"], root=paths["root"])
    coverage = status["coverage"]
    assert coverage["player_season"]["rows_canonical_resolved"] == 1
    assert coverage["medical_history"]["universe_split"]["out_of_universe_unresolved"] == 1
    assert "warning" in coverage["all_rows_combined"]


# --- idempotence ------------------------------------------------------------------

def test_rerun_is_content_idempotent(identity, paths):
    """Same bytes twice must not double the rows. Idempotence is content-verified, not
    inferred from a filename or an mtime."""
    _write_csv(paths["exports"] / "data_analysis_report-WR-2025.csv", SEASON_COLUMNS,
               [_season_row("Garrett Wilson"), _season_row("Justin Jefferson", draft_year="2020",
                                                           college="LSU")])
    kwargs = dict(export_paths=_files(paths["exports"]), identity=identity,
                  db_path=paths["db_path"], root=paths["root"])
    first = run_playerprofiler_ingest(**kwargs)
    second = run_playerprofiler_ingest(**kwargs)

    assert first["rows"]["player_season"] == 2
    assert second["rows"]["player_season"] == 2
    conn = sqlite3.connect(paths["db_path"])
    assert conn.execute("SELECT COUNT(*) FROM pp_player_season").fetchone()[0] == 2
    assert set(second["applied"].values()) == {"unchanged"}, second["applied"]


def test_changed_content_is_applied_not_skipped(identity, paths):
    """The other half of idempotence: the store must not mistake 'seen this block' for
    'nothing to do'. A changed value has to land."""
    export = paths["exports"] / "data_analysis_report-WR-2025.csv"
    _write_csv(export, SEASON_COLUMNS, [_season_row("Garrett Wilson")])
    kwargs = dict(export_paths=_files(paths["exports"]), identity=identity,
                  db_path=paths["db_path"], root=paths["root"])
    run_playerprofiler_ingest(**kwargs)

    _write_csv(export, SEASON_COLUMNS, [_season_row("Garrett Wilson", target_share="0.315")])
    second = run_playerprofiler_ingest(**kwargs)

    assert set(second["applied"].values()) == {"updated"}, second["applied"]
    conn = sqlite3.connect(paths["db_path"])
    assert conn.execute("SELECT target_share FROM pp_player_season").fetchone()[0] == "0.315"


# --- failure is named -------------------------------------------------------------

def test_failure_leaves_a_named_failed_marker_not_a_stale_ok(identity, paths, monkeypatch):
    """A run that dies must never leave the previous run's `ok` marker in place — that is
    how a silently dead feed goes unnoticed. It must land `failed` with the stage named."""
    _write_csv(paths["exports"] / "data_analysis_report-WR-2025.csv", SEASON_COLUMNS,
               [_season_row("Garrett Wilson")])
    kwargs = dict(export_paths=_files(paths["exports"]), identity=identity,
                  db_path=paths["db_path"], root=paths["root"])
    run_playerprofiler_ingest(**kwargs)
    assert json.loads(status_marker_path(paths["root"]).read_text())["status"] == "ok"

    def boom(*a, **k):
        raise RuntimeError("simulated store failure")

    monkeypatch.setattr(PlayerProfilerStore, "apply_block", boom)
    with pytest.raises(RuntimeError, match="simulated store failure"):
        run_playerprofiler_ingest(**kwargs)

    marker = json.loads(status_marker_path(paths["root"]).read_text(encoding="utf-8"))
    assert marker["status"] == "failed"
    assert marker["failed_stage"]
    assert "simulated store failure" in marker["reason"]


def test_no_exports_found_refuses_rather_than_reporting_a_clean_empty_run(identity, paths):
    """Zero files must not produce `ok` with zero rows: that is exactly what a broken
    download path looks like, and it would read as a healthy feed."""
    paths["exports"].mkdir(parents=True, exist_ok=True)
    assert _files(paths["exports"]) == []
    with pytest.raises(PlayerProfilerError):
        run_playerprofiler_ingest(export_paths=[], identity=identity,
                                  db_path=paths["db_path"], root=paths["root"])
