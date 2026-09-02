"""DG-128 (2026-09-01): draft capital for veterans comes from a governed offline snapshot.

The Engine A prior needs a veteran's pick, round and draft-season age. Those live in nflverse
draft_picks — the same table Engine A was trained from — captured ONCE into a tracked,
content-hashed snapshot and read offline by the serving batch. These tests pin the loader's
contract: no imputation, no network, and conflicts fail closed with a count rather than a pick.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.draft_capital import (
    SCHEMA,
    DraftCapitalError,
    build_snapshot,
    load_draft_capital,
    write_snapshot,
)

# The nflverse row shape (only the columns the snapshot keeps matter; extra columns are dropped).
_SOURCE_ROWS = [
    {"gsis_id": "00-0037247", "season": 2022, "round": 1, "pick": 10, "age": 22, "position": "WR", "team": "NYJ"},
    {"gsis_id": "00-0039853", "season": 2024, "round": 4, "pick": 134, "age": 20, "position": "RB", "college": "Wisconsin"},
    {"gsis_id": "00-0031234", "season": 2015, "round": 7, "pick": 250, "age": None, "position": "TE"},
    {"gsis_id": None, "season": 2019, "round": 6, "pick": 200, "age": 23, "position": "WR"},
    {"gsis_id": "00-0022222", "season": 2010, "round": 2, "pick": 40, "age": 22, "position": "WR"},
    {"gsis_id": "00-0022222", "season": 2011, "round": 3, "pick": 70, "age": 23, "position": "WR"},
    {"gsis_id": "00-0055555", "season": 2020, "round": 1, "pick": 3, "age": 21, "position": "CB"},
]


def _snapshot(tmp_path: Path) -> Path:
    path = tmp_path / "nflverse_draft_picks.json"
    snapshot = build_snapshot(
        _SOURCE_ROWS,
        seasons=(2000, 2026),
        pulled_at="2026-09-01T00:00:00+00:00",
        source="nflreadpy.load_draft_picks",
    )
    write_snapshot(snapshot, path)
    return path


def test_a_drafted_veteran_gets_pick_round_and_draft_season_age(tmp_path: Path) -> None:
    index = load_draft_capital(_snapshot(tmp_path))
    capital = index.get("00-0037247")
    assert capital is not None
    assert (capital.season, capital.round, capital.pick, capital.age) == (2022, 1, 10, 22.0)
    # The assembler's keys, as floats, and NEVER `age` (that key is the veteran's current age).
    assert capital.engine_a_features() == {"pick": 10.0, "round": 1.0, "age_at_nfl_entry": 22.0}


def test_a_null_draft_age_is_left_absent_never_imputed(tmp_path: Path) -> None:
    index = load_draft_capital(_snapshot(tmp_path))
    capital = index.get("00-0031234")
    assert capital is not None
    assert capital.age is None
    assert capital.engine_a_features() == {"pick": 250.0, "round": 7.0}


def test_two_draft_rows_on_one_gsis_exclude_both_and_are_counted(tmp_path: Path) -> None:
    index = load_draft_capital(_snapshot(tmp_path))
    assert index.get("00-0022222") is None
    assert index.accounting["gsis_conflict_rows"] == 2


def test_rows_without_a_gsis_cannot_join_and_are_counted(tmp_path: Path) -> None:
    index = load_draft_capital(_snapshot(tmp_path))
    assert index.accounting["gsis_missing_rows"] == 1
    # 7 source rows, the CB is not a skill position, 1 has no gsis, 2 conflict → 3 indexed.
    assert index.accounting["snapshot_rows"] == 6
    assert index.accounting["indexed_players"] == 3
    assert index.get("00-0055555") is None


def test_the_snapshot_records_its_provenance_and_the_loader_exposes_it(tmp_path: Path) -> None:
    path = _snapshot(tmp_path)
    index = load_draft_capital(path)
    written = json.loads(path.read_text())
    assert written["schema"] == SCHEMA
    assert written["source"] == "nflreadpy.load_draft_picks"
    assert written["seasons"] == [2000, 2026]
    assert written["positions"] == ["QB", "RB", "WR", "TE"]
    assert len(written["content_sha256"]) == 64
    assert index.content_sha256 == written["content_sha256"]
    assert index.path == path


def test_a_missing_snapshot_fails_closed_with_a_bare_token(tmp_path: Path) -> None:
    with pytest.raises(DraftCapitalError, match=r"^draft_capital_snapshot_missing$"):
        load_draft_capital(tmp_path / "absent.json")


def test_an_edited_snapshot_fails_the_content_hash(tmp_path: Path) -> None:
    path = _snapshot(tmp_path)
    snapshot = json.loads(path.read_text())
    snapshot["rows"][0]["pick"] = 1  # a hand edit that would hand a veteran a better pick
    path.write_text(json.dumps(snapshot))
    with pytest.raises(DraftCapitalError, match=r"^draft_capital_sha_mismatch$"):
        load_draft_capital(path)


def test_a_foreign_schema_is_refused(tmp_path: Path) -> None:
    path = _snapshot(tmp_path)
    snapshot = json.loads(path.read_text())
    snapshot["schema"] = "something.else.v9"
    path.write_text(json.dumps(snapshot))
    with pytest.raises(DraftCapitalError, match=r"^draft_capital_schema_mismatch$"):
        load_draft_capital(path)


def test_the_snapshot_keeps_only_the_pinned_columns(tmp_path: Path) -> None:
    written = json.loads(_snapshot(tmp_path).read_text())
    assert all(
        set(row) == {"gsis_id", "season", "round", "pick", "age", "position"} for row in written["rows"]
    )
