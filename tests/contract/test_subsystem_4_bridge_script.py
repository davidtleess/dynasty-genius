"""Subsystem 4 bridge discovery script contracts."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import scripts.build_prospect_nfl_bridge as script
from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
)
from src.dynasty_genius.identity.prospect_nfl_bridge import (
    NflreadrEmptyTruthError,
    NflreadrSchemaDriftError,
    NflreadrTruthLoadResult,
    NflTruthLoadDiagnostics,
    NflTruthRow,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_prospect_nfl_bridge.py"


def _truth_row() -> NflTruthRow:
    return NflTruthRow(
        gsis_id="00-script001",
        pfr_id="SharTe00",
        full_name="Shared Loader",
        normalized_name="shared loader",
        position="WR",
        college="Test U",
        draft_year=2025,
        draft_pick_no=12,
        draft_round=1,
        nfl_team="TEN",
        fetched_at="2026-01-01T00:00:00Z",
    )


def _truth_result() -> NflreadrTruthLoadResult:
    return NflreadrTruthLoadResult(
        rows=[_truth_row()],
        diagnostics=NflTruthLoadDiagnostics(
            truth_rows_loaded=1,
            skipped_missing_gsis_id=2,
            required_columns_seen=[
                "college",
                "gsis_id",
                "pfr_player_id",
                "pfr_player_name",
                "pick",
                "position",
                "round",
                "season",
                "team",
            ],
        ),
    )


def _source_truth_row(**overrides):
    row = {
        "season": 2025,
        "round": 1,
        "pick": 12,
        "team": "TEN",
        "gsis_id": "00-script001",
        "pfr_player_id": "SharTe00",
        "pfr_player_name": "Shared Loader",
        "position": "WR",
        "college": "Test U",
    }
    row.update(overrides)
    return row


def _write_source_fixture(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "truth_fixture.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {"fetched_at": "2026-01-01T00:00:00Z"},
                "rows": rows,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_bridge_script_uses_shared_truth_loader_not_private_broad_except():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SCRIPT_PATH))

    assert not hasattr(script, "_load_nflreadr_draft_truth")
    assert all(
        not (
            isinstance(node, ast.FunctionDef)
            and node.name == "_load_nflreadr_draft_truth"
        )
        for node in tree.body
    )
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "src.dynasty_genius.identity.prospect_nfl_bridge"
        and any(alias.name == "load_nflreadr_draft_truth" for alias in node.names)
        for node in tree.body
    )
    assert not any(
        isinstance(node, ast.ExceptHandler)
        and getattr(node.type, "id", None) == "Exception"
        and any(
            isinstance(child, ast.Return)
            and isinstance(child.value, ast.List)
            and child.value.elts == []
            for child in node.body
        )
        for node in ast.walk(tree)
    )


def test_bridge_script_propagates_shared_loader_failures(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(script, "load_registry", lambda _path: CollegeProspectRegistry())
    monkeypatch.setattr(
        script,
        "load_nflreadr_draft_truth",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            NflreadrSchemaDriftError("required source column missing")
        ),
        raising=False,
    )
    monkeypatch.setattr(
        script,
        "_load_nflreadr_draft_truth",
        lambda *args, **kwargs: [],
        raising=False,
    )

    with pytest.raises(NflreadrSchemaDriftError, match="required source column"):
        script.main(
            [
                "--identity-dir",
                str(tmp_path),
                "--draft-year",
                "2025",
                "--run-id",
                "schema_drift",
            ]
        )

    assert not (tmp_path / "prospect_nfl_coverage_2025_schema_drift.json").exists()


def test_bridge_script_all_skipped_truth_source_fails_before_artifact_write(
    tmp_path: Path,
):
    fixture_path = _write_source_fixture(tmp_path, [_source_truth_row(gsis_id="")])

    with pytest.raises((NflreadrEmptyTruthError, ValueError)) as exc_info:
        script.main(
            [
                "--identity-dir",
                str(tmp_path),
                "--draft-year",
                "2025",
                "--run-id",
                "all_skipped",
                "--nflreadr-fixture",
                str(fixture_path),
            ]
        )

    message = str(exc_info.value)
    assert "0 usable" in message or "all-skipped" in message
    assert not (tmp_path / "prospect_nfl_coverage_2025_all_skipped.json").exists()
    assert not (
        tmp_path / "prospect_nfl_review_queue_2025_all_skipped.jsonl"
    ).exists()
    assert not (
        tmp_path / "prospect_nfl_unmatched_udfa_candidates_2025_all_skipped.jsonl"
    ).exists()


def test_bridge_script_surfaces_shared_loader_rows_and_diagnostics(
    monkeypatch,
    tmp_path: Path,
):
    calls: list[dict] = []
    truth_result = _truth_result()

    def fake_loader(draft_year: int, *, data_mode: str, fixture_path=None):
        calls.append(
            {
                "draft_year": draft_year,
                "data_mode": data_mode,
                "fixture_path": fixture_path,
            }
        )
        return truth_result

    monkeypatch.setattr(script, "load_registry", lambda _path: CollegeProspectRegistry())
    monkeypatch.setattr(script, "load_nflreadr_draft_truth", fake_loader, raising=False)
    monkeypatch.setattr(
        script,
        "_load_nflreadr_draft_truth",
        lambda *args, **kwargs: [],
        raising=False,
    )

    exit_code = script.main(
        [
            "--identity-dir",
            str(tmp_path),
            "--draft-year",
            "2025",
            "--run-id",
            "shared_loader",
        ]
    )

    assert exit_code == 0
    assert calls == [{"draft_year": 2025, "data_mode": "real", "fixture_path": None}]

    coverage = json.loads(
        (tmp_path / "prospect_nfl_coverage_2025_shared_loader.json").read_text(
            encoding="utf-8"
        )
    )
    assert coverage["total_nfl_truth_rows"] == 1
    assert coverage["truth_load_diagnostics"] == truth_result.diagnostics.model_dump()
