"""S4 Task-6 Step-2 deterministic bridge batch confirmation contracts."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    RegistryEntry,
    StatusHistoryEntry,
    atomic_write_registry,
    compute_match_key,
    normalize_name,
)
from src.dynasty_genius.identity.prospect_nfl_bridge import (
    load_bridge,
    load_decision_log,
)

RUN_ID = "manual_2025_20260603T025656Z"
HASH = "15a1af31fc2f64e0aecc1c253d754b38131666fb6cbfe9ec18f5c3063b1aa0fb"


def _registry_entry(
    *,
    uuid: str,
    name: str,
    position: str = "WR",
    school: str = "Test State",
) -> RegistryEntry:
    normalized_name = normalize_name(name)
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status="confirmed",
        match_key=compute_match_key(
            normalized_name=normalized_name,
            position_group=position,
            draft_class=2025,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid[-8:]}",
                decision="confirm",
                after_status="confirmed",
                decided_at="2026-06-03T00:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        raw_name=name,
        normalized_name=normalized_name,
        full_name=name,
        position=position,
        position_group=position,
        draft_class=2025,
        current_school=school,
        prior_schools=[],
        cfbd_athlete_id=f"cfbd_{uuid[-8:]}",
        cfb_player_id=None,
        pfr_id=None,
        gsis_id=None,
        sleeper_id=None,
        source="cfbd_roster_2024",
        source_record_id=f"cfbd_{uuid[-8:]}",
        source_snapshot_id="cfbd_roster_2024:test",
        id_provenance={
            "cfbd_athlete_id": {
                "source": "CFBD /roster v2",
                "source_record_id": f"cfbd_{uuid[-8:]}",
            },
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        notes=None,
    )


def _truth_row(
    *,
    gsis_id: str,
    name: str,
    position: str = "WR",
    college: str = "Test State",
    pick: int = 100,
) -> dict:
    return {
        "gsis_id": gsis_id,
        "pfr_id": f"{name.replace(' ', '')[:8]}00",
        "full_name": name,
        "normalized_name": normalize_name(name),
        "position": position,
        "college": college,
        "draft_year": 2025,
        "draft_pick_no": pick,
        "draft_round": 4,
        "nfl_team": "TEN",
        "fetched_at": "2026-06-03T02:56:56Z",
    }


def _review_row(
    *,
    index: int,
    uuid: str,
    gsis_id: str,
    score: float = 1.0,
    college: str = "Test State",
    name: str = "Clean Receiver",
) -> dict:
    return {
        "run_id": RUN_ID,
        "review_id": f"{RUN_ID}_review_{index:04d}",
        "prospect_uuid": uuid,
        "gsis_id": gsis_id,
        "match_score": score,
        "score_breakdown": {"final": score},
        "risk_flags": [],
        "nfl_truth_row": _truth_row(
            gsis_id=gsis_id,
            name=name,
            college=college,
            pick=100 + index,
        ),
        "draft_truth_content_hash": HASH,
        "decided_at": None,
        "decision": None,
        "event_id": None,
    }


def _write_identity_dir(
    identity_dir: Path,
    *,
    registry_entries: list[RegistryEntry],
    review_rows: list[dict],
) -> None:
    identity_dir.mkdir(parents=True, exist_ok=True)
    registry = CollegeProspectRegistry(
        metadata={"schema_version": "college_prospect_registry_v1.0.0"},
        entries={entry.prospect_uuid: entry for entry in registry_entries},
    )
    atomic_write_registry(registry, identity_dir / "college_prospect_registry.json")
    (identity_dir / f"prospect_nfl_review_queue_2025_{RUN_ID}.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in review_rows),
        encoding="utf-8",
    )
    (identity_dir / f"prospect_nfl_coverage_2025_{RUN_ID}.json").write_text(
        json.dumps(
            {
                "draft_year": 2025,
                "run_id": RUN_ID,
                "total_s3_confirmed_prospects": len(registry_entries),
                "total_nfl_truth_rows": 256,
                "prospects_with_candidates": len(registry_entries),
                "prospects_unmatched_as_udfa": 0,
                "draft_truth_content_hash": HASH,
                "truth_load_diagnostics": {
                    "truth_rows_loaded": 256,
                    "skipped_missing_gsis_id": 1,
                    "skipped_bad_pick": 0,
                    "skipped_bad_round": 0,
                    "skipped_missing_name": 0,
                    "skipped_missing_position": 0,
                    "skipped_missing_team": 0,
                    "required_columns_seen": [
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
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _load_batch_module():
    return importlib.import_module("scripts.batch_confirm_2025_bridge_candidates")


def test_batch_confirms_only_exact_single_college_agree_candidates(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    uuid_a = "cpr_00000000-0000-4000-8000-0000000000a1"
    uuid_b = "cpr_00000000-0000-4000-8000-0000000000b2"
    uuid_manual = "cpr_00000000-0000-4000-8000-0000000000c3"
    _write_identity_dir(
        identity_dir,
        registry_entries=[
            _registry_entry(uuid=uuid_a, name="Clean Receiver", school="Ole Miss"),
            _registry_entry(uuid=uuid_b, name="Clean Back", position="RB", school="UCF"),
            _registry_entry(uuid=uuid_manual, name="Manual Receiver", school="Iowa State"),
        ],
        review_rows=[
            _review_row(index=1, uuid=uuid_a, gsis_id="00-a1", college="Mississippi"),
            _review_row(index=2, uuid=uuid_b, gsis_id="00-b2", college="Central Florida"),
            _review_row(index=3, uuid=uuid_manual, gsis_id="00-c3", college="Iowa St."),
            _review_row(index=4, uuid=uuid_manual, gsis_id="00-noise", college="Virginia Tech"),
        ],
    )
    module = _load_batch_module()

    result = module.batch_confirm_exact_single_bridge_candidates(
        identity_dir=identity_dir,
        draft_year=2025,
        run_id=RUN_ID,
        expected_count=2,
        reviewer_id="davidleess",
    )

    assert result.exit_code == 0
    assert result.confirmed_count == 2
    assert result.skipped_non_batch_count == 1

    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert {entry.prospect_uuid for entry in bridge.entries} == {uuid_a, uuid_b}
    by_uuid = {entry.prospect_uuid: entry for entry in bridge.entries}
    assert by_uuid[uuid_a].gsis_id == "00-a1"
    assert by_uuid[uuid_a].draft_truth_content_hash == HASH
    assert by_uuid[uuid_a].nflreadr_fetched_at == "2026-06-03T02:56:56Z"
    assert by_uuid[uuid_a].evidence_snapshot["college"] == "Mississippi"
    assert by_uuid[uuid_b].gsis_id == "00-b2"

    log = load_decision_log(identity_dir / "prospect_nfl_bridge_decision_log_2025.jsonl")
    assert len(log) == 2
    assert {event["decision"] for event in log} == {"confirm"}
    assert {event["reviewer_id"] for event in log} == {"davidleess"}

    review_rows = [
        json.loads(line)
        for line in (
            identity_dir / f"prospect_nfl_review_queue_2025_{RUN_ID}.jsonl"
        ).read_text().splitlines()
        if line.strip()
    ]
    assert [row["decision"] for row in review_rows] == ["confirm", "confirm", None, None]
    assert review_rows[0]["event_id"] != review_rows[1]["event_id"]


@pytest.mark.parametrize(
    ("review_rows", "match"),
    [
        (
                [
                    _review_row(
                        index=1,
                        uuid="cpr_00000000-0000-4000-8000-0000000000a1",
                        gsis_id="00-a1",
                        score=0.9995,
                    )
                ],
                "score",
        ),
        (
            [
                _review_row(
                    index=1,
                    uuid="cpr_00000000-0000-4000-8000-0000000000a1",
                    gsis_id="00-a1",
                    college="Auburn",
                )
            ],
            "college",
        ),
        (
            [
                _review_row(
                    index=1,
                    uuid="cpr_00000000-0000-4000-8000-0000000000a1",
                    gsis_id="",
                )
            ],
            "gsis",
        ),
    ],
)
def test_batch_fails_closed_before_writes_when_single_candidate_guard_fails(
    tmp_path: Path,
    review_rows: list[dict],
    match: str,
):
    identity_dir = tmp_path / "identity"
    uuid_a = "cpr_00000000-0000-4000-8000-0000000000a1"
    _write_identity_dir(
        identity_dir,
        registry_entries=[
            _registry_entry(uuid=uuid_a, name="Clean Receiver", school="Test State"),
        ],
        review_rows=review_rows,
    )
    review_before = (
        identity_dir / f"prospect_nfl_review_queue_2025_{RUN_ID}.jsonl"
    ).read_bytes()
    module = _load_batch_module()

    with pytest.raises(ValueError, match=match):
        module.batch_confirm_exact_single_bridge_candidates(
            identity_dir=identity_dir,
            draft_year=2025,
            run_id=RUN_ID,
            expected_count=1,
            reviewer_id="davidleess",
        )

    assert not (identity_dir / "prospect_to_nfl_bridge_2025.json").exists()
    assert not (identity_dir / "prospect_nfl_bridge_decision_log_2025.jsonl").exists()
    assert (
        identity_dir / f"prospect_nfl_review_queue_2025_{RUN_ID}.jsonl"
    ).read_bytes() == review_before


def test_batch_fails_closed_when_expected_count_does_not_match(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    uuid_a = "cpr_00000000-0000-4000-8000-0000000000a1"
    _write_identity_dir(
        identity_dir,
        registry_entries=[
            _registry_entry(uuid=uuid_a, name="Clean Receiver", school="Test State"),
        ],
        review_rows=[
            _review_row(index=1, uuid=uuid_a, gsis_id="00-a1", college="Test State")
        ],
    )
    module = _load_batch_module()

    with pytest.raises(ValueError, match="expected 68"):
        module.batch_confirm_exact_single_bridge_candidates(
            identity_dir=identity_dir,
            draft_year=2025,
            run_id=RUN_ID,
            expected_count=68,
            reviewer_id="davidleess",
        )

    assert not (identity_dir / "prospect_to_nfl_bridge_2025.json").exists()
