from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.dynasty_genius.adapters.pff_te_export import (
    PFFExportManifestEntry,
    parse_pff_te_export,
    summarize_pff_te_exports,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "player",
        "player_id",
        "position",
        "team_name",
        "routes",
        "inline_rate",
        "inline_snaps",
        "slot_rate",
        "slot_snaps",
        "wide_rate",
        "wide_snaps",
        "targets",
        "receptions",
        "yards",
        "yprr",
        "contested_catch_rate",
        "drop_rate",
        "grades_offense",
        "grades_pass_route",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_parse_pff_te_export_strips_grades_and_uses_snap_alignment_fallback(tmp_path: Path) -> None:
    csv_path = tmp_path / "pff_te_2024.csv"
    _write_csv(
        csv_path,
        [
            {
                "player": "TE Alpha",
                "player_id": "9001",
                "position": "TE",
                "team_name": "Iowa",
                "routes": "150",
                "inline_rate": "86.7",
                "inline_snaps": "130",
                "slot_rate": "10.0",
                "slot_snaps": "15",
                "wide_rate": "3.3",
                "wide_snaps": "5",
                "targets": "25",
                "receptions": "18",
                "yards": "180",
                "yprr": "1.20",
                "contested_catch_rate": "50.0",
                "drop_rate": "4.0",
                "grades_offense": "91.0",
                "grades_pass_route": "88.0",
            }
        ],
    )

    parsed = parse_pff_te_export(
        csv_path,
        season=2024,
        eligible_by_pff_id={
            "9001": {
                "player_id": "te_alpha_te",
                "draft_year": 2025,
            }
        },
        source_label="synthetic",
    )

    assert parsed.schema_report.alignment_source == "snaps_fallback"
    assert parsed.schema_report.required_missing == []
    assert sorted(parsed.schema_report.prohibited_columns) == [
        "grades_offense",
        "grades_pass_route",
    ]
    assert len(parsed.rows) == 1
    row = parsed.rows[0]
    assert row["player_id"] == "te_alpha_te"
    assert row["pff_id"] == "9001"
    assert row["season"] == 2024
    assert row["draft_year"] == 2025
    assert row["inline_snaps"] == 130.0
    assert row["slot_snaps"] == 15.0
    assert row["wide_snaps"] == 5.0
    assert row["context_signals"]["contested_catch_rate"] == 50.0
    assert all("grade" not in key for key in row)
    assert all("grade" not in key for key in row["context_signals"])


def test_parse_pff_te_export_filters_to_resolved_drafted_te_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "pff_te_2023.csv"
    _write_csv(
        csv_path,
        [
            {"player": "TE Alpha", "player_id": "9001", "position": "TE", "team_name": "Iowa"},
            {"player": "WR Beta", "player_id": "9002", "position": "WR", "team_name": "LSU"},
            {"player": "TE Gamma", "player_id": "9999", "position": "TE", "team_name": "Utah"},
        ],
    )

    parsed = parse_pff_te_export(
        csv_path,
        season=2023,
        eligible_by_pff_id={"9001": {"player_id": "te_alpha_te", "draft_year": 2024}},
        source_label="synthetic",
    )

    assert [row["pff_id"] for row in parsed.rows] == ["9001"]
    assert parsed.file_summary["te_rows"] == 2
    assert parsed.file_summary["matched_drafted_te_ids"] == 1
    assert parsed.file_summary["unmatched_te_ids"] == 1


def test_summarize_pff_te_exports_redacts_local_paths_and_player_names(tmp_path: Path) -> None:
    first = tmp_path / "receiving_summary (9).csv"
    second = tmp_path / "receiving_summary (10).csv"
    _write_csv(first, [{"player": "TE Alpha", "player_id": "9001", "position": "TE", "team_name": "Iowa"}])
    _write_csv(second, [{"player": "TE Beta", "player_id": "9002", "position": "TE", "team_name": "Georgia"}])

    report = summarize_pff_te_exports(
        [
            PFFExportManifestEntry(path=first, season=2023, label="v10"),
            PFFExportManifestEntry(path=second, season=2024, label="v11"),
        ],
        eligible_rows=[
            {"player_id": "te_alpha_te", "pff_id": "9001", "draft_year": 2024, "name": "TE Alpha"},
            {"player_id": "te_beta_te", "pff_id": "9002", "draft_year": 2025, "name": "TE Beta"},
            {"player_id": "te_missing_te", "pff_id": "9003", "draft_year": 2025, "name": "TE Missing"},
        ],
        generated_at="2026-05-16T11:45:00Z",
    )

    assert report["summary"]["eligible_count"] == 3
    assert report["summary"]["unique_matched_drafted_te_ids"] == 2
    assert report["summary"]["missing_drafted_te_ids"] == 1
    rendered = json.dumps(report)
    assert str(tmp_path) not in rendered
    assert "TE Alpha" not in rendered
    assert "TE Beta" not in rendered
    assert report["files"][0]["file_name"] == "receiving_summary (9).csv"
    assert report["missing_by_draft_year"] == {"2025": 1}


def test_summarize_pff_te_exports_rejects_unresolved_eligible_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "pff_te_2024.csv"
    _write_csv(csv_path, [{"player": "TE Alpha", "player_id": "9001", "position": "TE", "team_name": "Iowa"}])

    with pytest.raises(ValueError, match="canonical player_id"):
        summarize_pff_te_exports(
            [PFFExportManifestEntry(path=csv_path, season=2024, label="v10")],
            eligible_rows=[{"player_id": None, "pff_id": "9001", "draft_year": 2025}],
        )
