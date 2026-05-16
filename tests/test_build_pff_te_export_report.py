from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.build_pff_te_export_report import main


def test_build_pff_te_export_report_writes_redacted_summary(tmp_path: Path) -> None:
    csv_path = tmp_path / "receiving_summary (9).csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "player",
                "player_id",
                "position",
                "team_name",
                "routes",
                "inline_snaps",
                "slot_snaps",
                "wide_snaps",
                "targets",
                "receptions",
                "yards",
                "grades_offense",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "player": "TE Alpha",
                "player_id": "9001",
                "position": "TE",
                "team_name": "Iowa",
                "routes": "100",
                "inline_snaps": "80",
                "slot_snaps": "15",
                "wide_snaps": "5",
                "targets": "20",
                "receptions": "12",
                "yards": "150",
                "grades_offense": "91.0",
            }
        )

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "exports": [
                    {
                        "path": str(csv_path),
                        "season": 2024,
                        "label": "v10",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    eligible_path = tmp_path / "eligible.json"
    eligible_path.write_text(
        json.dumps(
            {
                "eligible": [
                    {
                        "player_id": "te_alpha_te",
                        "pff_id": "9001",
                        "draft_year": 2025,
                        "name": "TE Alpha",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "report.json"

    assert main(
        [
            "--manifest",
            str(manifest_path),
            "--eligible-manifest",
            str(eligible_path),
            "--out",
            str(out_path),
            "--generated-at",
            "2026-05-16T12:00:00Z",
        ]
    ) == 0

    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["summary"]["unique_matched_drafted_te_ids"] == 1
    assert report["files"][0]["file_name"] == "receiving_summary (9).csv"
    assert report["files"][0]["prohibited_columns"] == ["grades_offense"]
    rendered = json.dumps(report)
    assert str(tmp_path) not in rendered
    assert "TE Alpha" not in rendered


def test_build_pff_te_export_report_can_merge_draft_year_from_cohort(tmp_path: Path) -> None:
    csv_path = tmp_path / "receiving_summary (9).csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "player",
                "player_id",
                "position",
                "team_name",
                "routes",
                "inline_snaps",
                "slot_snaps",
                "wide_snaps",
                "targets",
                "receptions",
                "yards",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "player": "TE Alpha",
                "player_id": "9001",
                "position": "TE",
                "team_name": "Iowa",
                "routes": "100",
                "inline_snaps": "80",
                "slot_snaps": "15",
                "wide_snaps": "5",
                "targets": "20",
                "receptions": "12",
                "yards": "150",
            }
        )

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"exports": [{"path": str(csv_path), "season": 2024, "label": "v10"}]}),
        encoding="utf-8",
    )
    eligible_path = tmp_path / "eligible.json"
    eligible_path.write_text(
        json.dumps(
            {
                "eligible": [
                    {"player_id": "te_alpha_te", "pff_id": "9001", "name": "TE Alpha"},
                    {"player_id": "te_missing_te", "pff_id": "9002", "name": "TE Missing"},
                ]
            }
        ),
        encoding="utf-8",
    )
    cohort_path = tmp_path / "cohort.json"
    cohort_path.write_text(
        json.dumps(
            {
                "entries": [
                    {"pff_id": "9001", "draft_year": 2025, "name": "TE Alpha"},
                    {"pff_id": "9002", "draft_year": 2025, "name": "TE Missing"},
                ]
            }
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "report.json"

    assert main(
        [
            "--manifest",
            str(manifest_path),
            "--eligible-manifest",
            str(eligible_path),
            "--cohort",
            str(cohort_path),
            "--out",
            str(out_path),
            "--generated-at",
            "2026-05-16T12:00:00Z",
        ]
    ) == 0

    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["missing_by_draft_year"] == {"2025": 1}
