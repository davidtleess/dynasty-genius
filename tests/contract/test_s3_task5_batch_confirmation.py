"""S3 Task-10A Task-5 batch confirmation contract tests."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    RegistryEntry,
    atomic_write_registry,
    load_registry,
    validate_registry_graph,
)


def _row(*, uuid: str, name: str, cfbd_id: str | None, status: str = "provisional"):
    return {
        "raw_name": name,
        "normalized_name": name.lower(),
        "full_name": name,
        "position": "WR",
        "position_group": "WR",
        "draft_class": 2025,
        "class_year": "4",
        "current_school": "Test State",
        "prior_schools": [],
        "cfbd_athlete_id": cfbd_id,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "cfbd_roster_2024",
        "source_record_id": cfbd_id or f"missing_{uuid}",
        "source_snapshot_id": "cfbd_roster_2024:test",
        "id_provenance": {
            "cfbd_athlete_id": (
                {"source": "CFBD /roster v2", "source_record_id": cfbd_id}
                if cfbd_id
                else None
            ),
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
        "prospect_uuid": uuid,
        "match_key": f"match_{uuid}",
        "verification_status": status,
        "merged_into_prospect_uuid": None,
        "reviewer_id": "system_ingestion",
        "reviewer_metadata": {},
        "status_history": [],
    }


def _write_registry(identity_dir: Path, rows: list[dict]) -> None:
    registry = load_registry(identity_dir / "college_prospect_registry.json")
    for raw in rows:
        entry = RegistryEntry.model_validate(raw)
        registry.entries[entry.prospect_uuid] = entry
    atomic_write_registry(registry, identity_dir / "college_prospect_registry.json")
    (identity_dir / "college_alias_bridge.json").write_text(
        json.dumps({"entries": [], "metadata": {}}, indent=2),
        encoding="utf-8",
    )


def _load_batch_module():
    return importlib.import_module("scripts.batch_confirm_2025_clean_prospects")


def test_batch_confirm_promotes_only_unflagged_rows_through_promotion_log(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    flagged = {"cpr_flagged_001"}
    _write_registry(
        identity_dir,
        [
            _row(uuid="cpr_clean_001", name="Clean One", cfbd_id="1001"),
            _row(uuid="cpr_clean_002", name="Clean Two", cfbd_id="1002"),
            _row(uuid="cpr_flagged_001", name="Flagged One", cfbd_id="2001"),
        ],
    )
    module = _load_batch_module()

    result = module.batch_confirm_clean_prospects(
        identity_dir=identity_dir,
        flagged_uuids=flagged,
        expected_count=2,
        reviewer_id="davidleess",
    )

    assert result.exit_code == 0
    assert result.confirmed_count == 2
    assert result.skipped_flagged_count == 1

    registry = load_registry(identity_dir / "college_prospect_registry.json")
    assert registry.get("cpr_clean_001").verification_status == "confirmed"
    assert registry.get("cpr_clean_002").verification_status == "confirmed"
    assert registry.get("cpr_flagged_001").verification_status == "provisional"
    assert validate_registry_graph(registry) == []

    events = [
        json.loads(line)
        for line in (identity_dir / "college_identity_promotion_log.jsonl")
        .read_text()
        .splitlines()
        if line.strip()
    ]
    assert len(events) == 2
    assert {event["target_prospect_uuid"] for event in events} == {
        "cpr_clean_001",
        "cpr_clean_002",
    }
    assert {event["decision"] for event in events} == {"confirm"}
    assert {event["target_kind"] for event in events} == {"self"}
    assert {event["reviewer_id"] for event in events} == {"davidleess"}
    assert {event["review_id"] for event in events} == {None}


def test_batch_confirm_is_idempotent_and_does_not_duplicate_events(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    _write_registry(
        identity_dir,
        [
            _row(uuid="cpr_clean_001", name="Clean One", cfbd_id="1001"),
            _row(uuid="cpr_flagged_001", name="Flagged One", cfbd_id="2001"),
        ],
    )
    module = _load_batch_module()

    first = module.batch_confirm_clean_prospects(
        identity_dir=identity_dir,
        flagged_uuids={"cpr_flagged_001"},
        expected_count=1,
        reviewer_id="davidleess",
    )
    log_after_first = (identity_dir / "college_identity_promotion_log.jsonl").read_bytes()
    second = module.batch_confirm_clean_prospects(
        identity_dir=identity_dir,
        flagged_uuids={"cpr_flagged_001"},
        expected_count=1,
        reviewer_id="davidleess",
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert second.confirmed_count == 0
    assert (identity_dir / "college_identity_promotion_log.jsonl").read_bytes() == log_after_first


@pytest.mark.parametrize(
    ("rows", "flagged", "expected_error"),
    [
        (
            [
                _row(uuid="cpr_clean_001", name="Clean One", cfbd_id="1001"),
                _row(uuid="cpr_flagged_001", name="Flagged One", cfbd_id="2001"),
            ],
            set(),
            "expected 1 clean provisional rows",
        ),
        (
            [
                _row(uuid="cpr_clean_001", name="Clean One", cfbd_id=None),
                _row(uuid="cpr_flagged_001", name="Flagged One", cfbd_id="2001"),
            ],
            {"cpr_flagged_001"},
            "missing cfbd_athlete_id",
        ),
    ],
)
def test_batch_confirm_fails_closed_before_writes(
    tmp_path: Path,
    rows: list[dict],
    flagged: set[str],
    expected_error: str,
):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    _write_registry(identity_dir, rows)
    registry_before = (identity_dir / "college_prospect_registry.json").read_bytes()
    module = _load_batch_module()

    with pytest.raises(ValueError, match=expected_error):
        module.batch_confirm_clean_prospects(
            identity_dir=identity_dir,
            flagged_uuids=flagged,
            expected_count=1,
            reviewer_id="davidleess",
        )

    assert (identity_dir / "college_prospect_registry.json").read_bytes() == registry_before
    assert not (identity_dir / "college_identity_promotion_log.jsonl").exists()


def test_batch_confirm_fails_closed_on_unexpected_status_before_writes(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    _write_registry(
        identity_dir,
        [
            _row(uuid="cpr_clean_001", name="Clean One", cfbd_id="1001", status="deprecated"),
            _row(uuid="cpr_flagged_001", name="Flagged One", cfbd_id="2001"),
        ],
    )
    registry_before = (identity_dir / "college_prospect_registry.json").read_bytes()
    module = _load_batch_module()

    with pytest.raises(ValueError, match="unexpected"):
        module.batch_confirm_clean_prospects(
            identity_dir=identity_dir,
            flagged_uuids={"cpr_flagged_001"},
            expected_count=1,
            reviewer_id="davidleess",
        )

    assert (identity_dir / "college_prospect_registry.json").read_bytes() == registry_before
    assert not (identity_dir / "college_identity_promotion_log.jsonl").exists()
