from __future__ import annotations

import json

from scripts.backfill_te_canonical_ids import (
    build_canonical_te_registry,
    write_canonical_te_artifacts,
)


def _eligible_manifest() -> dict:
    return {
        "run_id": "te_test_run",
        "generated_at": "2026-05-16T12:00:00Z",
        "eligible": [
            {
                "player_id": None,
                "sleeper_id": "200",
                "gsis_id": "00-0000002",
                "name": "John Smith",
                "resolution_stage": "ff_playerids_crosswalk",
                "pff_id": "9002",
            },
            {
                "player_id": None,
                "sleeper_id": "100",
                "gsis_id": "00-0000001",
                "name": "John Smith",
                "resolution_stage": "ff_playerids_crosswalk",
                "pff_id": "9001",
            },
            {
                "player_id": None,
                "sleeper_id": "300",
                "gsis_id": "00-0000003",
                "name": "T.J. Hockenson",
                "resolution_stage": "ff_playerids_crosswalk",
                "pff_id": "9003",
            },
        ],
    }


def test_build_canonical_te_registry_assigns_deterministic_ids():
    registry = build_canonical_te_registry(
        _eligible_manifest(),
        generated_at="2026-05-16T12:30:00Z",
    )

    assert registry["metadata"]["source_run_id"] == "te_test_run"
    assert registry["metadata"]["count"] == 3
    assert list(registry["players"]) == [
        "john_smith_te",
        "john_smith_te_2",
        "teejay_hockenson_te",
    ]

    first = registry["players"]["john_smith_te"]
    second = registry["players"]["john_smith_te_2"]
    assert first["gsis_id"] == "00-0000001"
    assert second["gsis_id"] == "00-0000002"
    assert first["sleeper_id"] == "100"
    assert second["sleeper_id"] == "200"


def test_write_canonical_te_artifacts_populates_snapshot_and_eligibility(tmp_path):
    source_path = tmp_path / "pff_te_eligible_te_test_run.json"
    source_path.write_text(json.dumps(_eligible_manifest()), encoding="utf-8")

    written = write_canonical_te_artifacts(
        source_path,
        out_dir=tmp_path,
        generated_at="2026-05-16T12:30:00Z",
    )

    registry = json.loads(written["registry"].read_text(encoding="utf-8"))
    snapshot = json.loads(written["snapshot"].read_text(encoding="utf-8"))
    eligible = json.loads(written["eligible"].read_text(encoding="utf-8"))

    assert registry["metadata"]["source_run_id"] == "te_test_run"
    assert set(snapshot["mappings"]) == set(registry["players"])
    assert snapshot["immutable"] is True
    assert eligible["eligible_count"] == 3
    assert {row["player_id"] for row in eligible["eligible"]} == set(registry["players"])
    assert all(row["canonical_player_id_source"] == "deterministic_name_position" for row in eligible["eligible"])
