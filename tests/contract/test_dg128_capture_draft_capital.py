"""DG-128 (2026-09-01): the one-shot capture that writes the tracked draft-capital snapshot."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.capture_draft_capital import run_capture
from src.dynasty_genius.draft_capital import SCHEMA, load_draft_capital

_UPSTREAM = [
    {"gsis_id": "00-0037247", "season": 2022, "round": 1, "pick": 10, "age": 22, "position": "WR", "team": "NYJ"},
    {"gsis_id": "00-0040676", "season": 2025, "round": 1, "pick": 1, "age": 23, "position": "QB", "team": "TEN"},
    {"gsis_id": "00-0055555", "season": 2020, "round": 1, "pick": 3, "age": 21, "position": "CB", "team": "DET"},
]


def test_the_capture_writes_a_loadable_snapshot_and_reports_its_counts(tmp_path: Path, capsys) -> None:
    output = tmp_path / "draft_capital" / "nflverse_draft_picks.json"
    seen_seasons: list[list[int]] = []

    def _fetch(seasons: list[int]) -> list[dict]:
        seen_seasons.append(seasons)
        return _UPSTREAM

    exit_code = run_capture(output_path=output, seasons=(2020, 2025), fetch_fn=_fetch)

    assert exit_code == 0
    assert seen_seasons == [list(range(2020, 2026))]
    index = load_draft_capital(output)
    assert len(index) == 2  # the CB is not a skill position
    written = json.loads(output.read_text())
    assert written["schema"] == SCHEMA
    assert written["source"] == "nflreadpy.load_draft_picks"
    assert written["seasons"] == [2020, 2025]
    out = capsys.readouterr().out
    assert "rows=2" in out and written["content_sha256"][:12] in out


def test_an_empty_upstream_writes_nothing_and_exits_1(tmp_path: Path) -> None:
    output = tmp_path / "nflverse_draft_picks.json"
    exit_code = run_capture(output_path=output, seasons=(2020, 2025), fetch_fn=lambda seasons: [])
    assert exit_code == 1
    assert not output.exists()
