from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.build_te_archetype_rubric import build_te_archetype_artifact
from src.dynasty_genius.audit.te_archetype_rubric import (
    TEArchetypeInput,
    classify_te_archetype,
)

PLAYER_ROW_KEYS = {
    "player_id",
    "draft_year",
    "selected_season",
    "coverage_status",
    "labeling_status",
    "archetype",
    "source_row_hash",
    "alignment_snap_total",
    "detached_rate_from_snaps",
    "inline_rate_from_snaps",
    "routes",
    "targets",
    "receptions",
    "yards",
    "yprr_computed",
    "tprr_computed",
    "elite_efficiency_prior",
    "near_volume_threshold",
    "alignment_source",
    "threshold_basis",
}

TOP_LEVEL_KEYS = {"metadata", "players", "sensitivity", "coverage_gap"}


def test_receiving_leaning_at_inclusive_detached_boundary():
    row = TEArchetypeInput(
        player_id="te_receiving",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash001",
        inline_snaps=60.0,
        slot_snaps=35.0,
        wide_snaps=5.0,
        routes=100.0,
        targets=25.0,
        receptions=18.0,
        yards=190.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] == "receiving_leaning"
    assert label["labeling_status"] == "labeled"
    assert label["detached_rate_from_snaps"] == 0.4
    assert label["inline_rate_from_snaps"] == 0.6


def test_blocking_leaning_at_inclusive_inline_boundary():
    row = TEArchetypeInput(
        player_id="te_blocking",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash002",
        inline_snaps=70.0,
        slot_snaps=25.0,
        wide_snaps=5.0,
        routes=100.0,
        targets=10.0,
        receptions=8.0,
        yards=70.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] == "blocking_leaning"
    assert label["labeling_status"] == "labeled"
    assert label["inline_rate_from_snaps"] == 0.7


def test_ambiguous_between_thresholds():
    row = TEArchetypeInput(
        player_id="te_ambiguous",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash003",
        inline_snaps=65.0,
        slot_snaps=30.0,
        wide_snaps=5.0,
        routes=100.0,
        targets=15.0,
        receptions=10.0,
        yards=110.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] == "ambiguous"
    assert label["labeling_status"] == "labeled"


def test_low_volume_has_null_archetype():
    row = TEArchetypeInput(
        player_id="te_low_volume",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash004",
        inline_snaps=40.0,
        slot_snaps=10.0,
        wide_snaps=0.0,
        routes=20.0,
        targets=5.0,
        receptions=3.0,
        yards=40.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] is None
    assert label["labeling_status"] == "low_volume"


def test_invalid_alignment_has_null_archetype():
    row = TEArchetypeInput(
        player_id="te_invalid",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash005",
        inline_snaps=0.0,
        slot_snaps=0.0,
        wide_snaps=0.0,
        routes=80.0,
        targets=4.0,
        receptions=2.0,
        yards=20.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] is None
    assert label["labeling_status"] == "invalid_alignment"


def test_efficiency_flags_are_context_only():
    row = TEArchetypeInput(
        player_id="te_efficient_blocker",
        draft_year=2024,
        selected_season=2023,
        source_row_hash="hash006",
        inline_snaps=80.0,
        slot_snaps=15.0,
        wide_snaps=5.0,
        routes=100.0,
        targets=30.0,
        receptions=20.0,
        yards=200.0,
    )

    label = classify_te_archetype(row)

    assert label["archetype"] == "blocking_leaning"
    assert label["elite_efficiency_prior"] is True
    assert label["yprr_computed"] == 2.0
    assert label["tprr_computed"] == 0.3


def test_build_artifact_includes_all_players_and_excludes_missing_rows(tmp_path: Path):
    parsed_rows = [
        {
            "player_id": "te_labeled",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2023,
            "source_label": "synthetic_2023",
            "routes": 100.0,
            "inline_snaps": 60.0,
            "slot_snaps": 35.0,
            "wide_snaps": 5.0,
            "targets": 25.0,
            "receptions": 18.0,
            "yards": 190.0,
        }
    ]
    eligible_rows = [
        {"player_id": "te_labeled", "pff_id": "9001", "draft_year": 2024},
        {"player_id": "te_missing", "pff_id": "9002", "draft_year": 2024},
    ]
    file_summaries = [{"source_label": "synthetic_2023", "season": 2023, "content_hash": "contenthash01"}]

    artifact = build_te_archetype_artifact(
        parsed_rows,
        eligible_rows=eligible_rows,
        file_summaries=file_summaries,
        run_id="test_run",
        generated_at="2026-05-16T12:30:00Z",
    )

    assert artifact["metadata"]["eligible_count"] == 2
    assert artifact["metadata"]["coverage_count"] == 1
    assert artifact["metadata"]["missing_count"] == 1
    assert set(artifact["players"]) == {"te_labeled", "te_missing"}
    assert artifact["players"]["te_labeled"]["archetype"] == "receiving_leaning"
    assert artifact["players"]["te_labeled"]["source_row_hash"]
    assert artifact["players"]["te_missing"]["archetype"] is None
    assert artifact["players"]["te_missing"]["coverage_status"] == "pff_alignment_missing"
    assert artifact["players"]["te_missing"]["labeling_status"] == "excluded"
    rendered = json.dumps(artifact)
    assert "9001" not in rendered
    assert "9002" not in rendered


def test_build_artifact_selects_final_college_season_before_fallback():
    parsed_rows = [
        {
            "player_id": "te_multi",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2022,
            "source_label": "synthetic_2022",
            "routes": 100.0,
            "inline_snaps": 90.0,
            "slot_snaps": 5.0,
            "wide_snaps": 5.0,
            "targets": 10.0,
            "receptions": 7.0,
            "yards": 80.0,
        },
        {
            "player_id": "te_multi",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2023,
            "source_label": "synthetic_2023",
            "routes": 100.0,
            "inline_snaps": 50.0,
            "slot_snaps": 40.0,
            "wide_snaps": 10.0,
            "targets": 30.0,
            "receptions": 20.0,
            "yards": 220.0,
        },
    ]
    eligible_rows = [{"player_id": "te_multi", "pff_id": "9001", "draft_year": 2024}]
    file_summaries = [
        {"source_label": "synthetic_2022", "season": 2022, "content_hash": "hash2022"},
        {"source_label": "synthetic_2023", "season": 2023, "content_hash": "hash2023"},
    ]

    artifact = build_te_archetype_artifact(
        parsed_rows,
        eligible_rows=eligible_rows,
        file_summaries=file_summaries,
        run_id="test_run",
        generated_at="2026-05-16T12:30:00Z",
    )

    row = artifact["players"]["te_multi"]
    assert row["selected_season"] == 2023
    assert row["archetype"] == "receiving_leaning"


def test_build_artifact_falls_back_to_draft_year_minus_two():
    parsed_rows = [
        {
            "player_id": "te_fallback",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2022,
            "source_label": "synthetic_2022",
            "routes": 100.0,
            "inline_snaps": 50.0,
            "slot_snaps": 40.0,
            "wide_snaps": 10.0,
            "targets": 30.0,
            "receptions": 20.0,
            "yards": 220.0,
        }
    ]
    eligible_rows = [{"player_id": "te_fallback", "pff_id": "9001", "draft_year": 2024}]
    file_summaries = [{"source_label": "synthetic_2022", "season": 2022, "content_hash": "hash2022"}]

    artifact = build_te_archetype_artifact(
        parsed_rows,
        eligible_rows=eligible_rows,
        file_summaries=file_summaries,
        run_id="test_run",
        generated_at="2026-05-16T12:30:00Z",
    )

    row = artifact["players"]["te_fallback"]
    assert row["selected_season"] == 2022
    assert row["archetype"] == "receiving_leaning"


def test_build_artifact_rejects_duplicate_player_season_rows():
    parsed_rows = [
        {
            "player_id": "te_duplicate",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2023,
            "source_label": "synthetic_2023",
            "routes": 100.0,
            "inline_snaps": 60.0,
            "slot_snaps": 35.0,
            "wide_snaps": 5.0,
            "targets": 25.0,
            "receptions": 18.0,
            "yards": 190.0,
        },
        {
            "player_id": "te_duplicate",
            "pff_id": "9001",
            "draft_year": 2024,
            "season": 2023,
            "source_label": "synthetic_2023_duplicate",
            "routes": 100.0,
            "inline_snaps": 70.0,
            "slot_snaps": 25.0,
            "wide_snaps": 5.0,
            "targets": 20.0,
            "receptions": 12.0,
            "yards": 120.0,
        },
    ]
    eligible_rows = [{"player_id": "te_duplicate", "pff_id": "9001", "draft_year": 2024}]
    file_summaries = [
        {"source_label": "synthetic_2023", "season": 2023, "content_hash": "hash2023a"},
        {"source_label": "synthetic_2023_duplicate", "season": 2023, "content_hash": "hash2023b"},
    ]

    with pytest.raises(ValueError, match="duplicate PFF TE rows"):
        build_te_archetype_artifact(
            parsed_rows,
            eligible_rows=eligible_rows,
            file_summaries=file_summaries,
            run_id="test_run",
            generated_at="2026-05-16T12:30:00Z",
        )


def test_committed_te_archetype_artifact_contract():
    path = Path("app/data/identity/te_archetype_rubric_20260516.json")
    artifact = json.loads(path.read_text(encoding="utf-8"))

    assert set(artifact) == TOP_LEVEL_KEYS
    assert artifact["metadata"]["eligible_count"] == 116
    assert len(artifact["players"]) == 116
    assert artifact["metadata"]["coverage_count"] == 110
    assert artifact["metadata"]["missing_count"] == 6
    assert artifact["coverage_gap"]["missing_by_draft_year"] == {
        "2018": 1,
        "2020": 2,
        "2021": 1,
        "2022": 1,
        "2023": 1,
    }
    assert artifact["metadata"]["model_features_changed"] is False
    assert artifact["metadata"]["te_promotion_changed"] is False
    assert artifact["metadata"]["market_data_used"] is False

    rendered = json.dumps(artifact).lower()
    assert "pff_id" not in rendered
    assert "sleeper_id" not in rendered
    assert "gsis_id" not in rendered
    assert "grades_" not in rendered
    assert "/users/" not in rendered
    assert "downloads" not in rendered

    statuses = {row["labeling_status"] for row in artifact["players"].values()}
    assert statuses <= {"labeled", "low_volume", "invalid_alignment", "excluded"}

    excluded = [
        row for row in artifact["players"].values()
        if row["labeling_status"] == "excluded"
    ]
    assert len(excluded) == 6
    assert all(row["archetype"] is None for row in excluded)
    assert all(row["source_row_hash"] is None for row in excluded)

    covered = [
        row for row in artifact["players"].values()
        if row["coverage_status"] == "pff_alignment_available"
    ]
    assert len(covered) == 110
    for player_id, row in artifact["players"].items():
        assert set(row) == PLAYER_ROW_KEYS
        assert row["player_id"] == player_id
        if row["coverage_status"] == "pff_alignment_available":
            assert re.fullmatch(r"[0-9a-f]{12}", row["source_row_hash"])
            assert row["selected_season"] in {row["draft_year"] - 1, row["draft_year"] - 2}
            assert row["alignment_source"] == "snaps_fallback"
            assert row["threshold_basis"] == "snap_counts"
