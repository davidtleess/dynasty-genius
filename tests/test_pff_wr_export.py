"""Tests for Phase 16.2 PFF WR export parser."""
import csv

import pytest

from src.dynasty_genius.adapters.pff_wr_export import (
    PFFWRExportError,
    parse_pff_wr_season,
)


def _write_csv(rows: list[dict], tmp_path, filename="test.csv") -> str:
    path = tmp_path / filename
    if not rows:
        path.write_text("")
        return str(path)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def _base_row(**kwargs):
    defaults = {
        "player_id": "12345",
        "player": "Test Player",
        "position": "WR",
        "team_name": "Alabama",
        "routes": "400",
        "yprr": "2.50",
        "yards": "1000",
        "targets": "120",
        "receptions": "80",
    }
    defaults.update(kwargs)
    return defaults


def test_parse_returns_wr_rows(tmp_path):
    rows = [_base_row(player_id="1", player="Alpha WR", position="WR")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert len(result.rows) == 1
    assert result.rows[0]["position"] == "WR"


def test_parse_includes_rb_rows(tmp_path):
    rows = [_base_row(player_id="2", player="RB Player", position="RB")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert len(result.rows) == 1
    assert result.rows[0]["position"] == "RB"


def test_parse_excludes_te_rows(tmp_path):
    rows = [
        _base_row(player_id="1", position="WR"),
        _base_row(player_id="2", position="TE"),
    ]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert len(result.rows) == 1
    assert result.rows[0]["pff_id"] == "1"


def test_parse_tolerates_grade_columns(tmp_path):
    # Real PFF exports include grades_* columns — parser must tolerate them,
    # report them in prohibited_columns, and never emit grade keys in rows.
    rows = [_base_row(**{"grades_offense": "88.5"})]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert len(result.rows) == 1
    assert "grades_offense" in result.prohibited_columns
    assert all("grade" not in key.lower() for key in result.rows[0])


def test_parse_hb_normalized_to_rb(tmp_path):
    rows = [_base_row(player_id="3", player="HB Player", position="HB")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert len(result.rows) == 1
    assert result.rows[0]["position"] == "RB"


def test_parse_yprr_as_float(tmp_path):
    rows = [_base_row(yprr="1.87")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert result.rows[0]["yprr"] == pytest.approx(1.87)


def test_parse_season_injected(tmp_path):
    rows = [_base_row()]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2019)
    assert result.rows[0]["season"] == 2019


def test_content_hash_present(tmp_path):
    rows = [_base_row()]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert isinstance(result.content_hash, str)
    assert len(result.content_hash) == 12


def test_parse_missing_required_column_raises(tmp_path):
    rows = [{"player_id": "1", "player": "Test", "position": "WR"}]
    path = _write_csv(rows, tmp_path)
    with pytest.raises(PFFWRExportError, match="missing required"):
        parse_pff_wr_season(path, season=2022)


def test_parse_null_yprr_allowed(tmp_path):
    rows = [_base_row(yprr="")]
    path = _write_csv(rows, tmp_path)
    result = parse_pff_wr_season(path, season=2022)
    assert result.rows[0]["yprr"] is None
