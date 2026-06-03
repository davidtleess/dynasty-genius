"""Subsystem 3 - Round 2 promotion lifecycle contract tests (section 10.6)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeAliasBridge,
    CollegeAliasBridgeEntry,
    ConflictingDecisionError,
    EvidenceRequiredError,
    PromotionDecision,
    PromotionResult,
    atomic_write_registry,
    ingest_fixture,
    load_bridge,
    load_registry,
    promote_review_candidate,
    replay_promotion_log,
)


def _two_row_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "metadata": {"snapshot_id": "fixture_2027_v1"},
                "entries": [
                    {
                        "raw_name": "Arch Manning",
                        "normalized_name": "arch manning",
                        "full_name": "Arch Manning",
                        "position": "QB",
                        "position_group": "QB",
                        "draft_class": 2027,
                        "current_school": "Texas",
                        "prior_schools": [],
                        "cfbd_athlete_id": None,
                        "cfb_player_id": None,
                        "pfr_id": None,
                        "gsis_id": None,
                        "sleeper_id": None,
                        "source": "manual_fixture",
                        "source_record_id": "fixture_2027_001",
                        "source_snapshot_id": "fixture_2027_v1",
                        "id_provenance": {
                            "cfbd_athlete_id": None,
                            "cfb_player_id": None,
                            "pfr_id": None,
                            "gsis_id": None,
                            "sleeper_id": None,
                        },
                        "notes": None,
                    },
                    {
                        "raw_name": "Mike Williams",
                        "normalized_name": "mike williams",
                        "full_name": "Mike Williams",
                        "position": "WR",
                        "position_group": "WR",
                        "draft_class": 2027,
                        "current_school": "Clemson",
                        "prior_schools": [],
                        "cfbd_athlete_id": None,
                        "cfb_player_id": None,
                        "pfr_id": None,
                        "gsis_id": None,
                        "sleeper_id": None,
                        "source": "manual_fixture",
                        "source_record_id": "fixture_2027_002",
                        "source_snapshot_id": "fixture_2027_v1",
                        "id_provenance": {
                            "cfbd_athlete_id": None,
                            "cfb_player_id": None,
                            "pfr_id": None,
                            "gsis_id": None,
                            "sleeper_id": None,
                        },
                        "notes": None,
                    },
                ],
            }
        )
    )
    out = tmp_path / "out"
    run_id = "genesis_run_001"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id=run_id)
    return fixture, out, run_id


def _provisional_uuid(out: Path) -> str:
    registry = load_registry(out / "college_prospect_registry.json")
    for entry in registry.entries.values():
        if entry.verification_status == "provisional":
            return entry.prospect_uuid
    raise AssertionError("expected a provisional row")


def _all_uuids(out: Path) -> list[str]:
    return list(load_registry(out / "college_prospect_registry.json").entries.keys())


def test_confirm_self_promotes_row_to_confirmed_and_logs(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)

    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    assert isinstance(result, PromotionResult)
    assert result.exit_code == 0
    registry = load_registry(out / "college_prospect_registry.json")
    assert registry.get(target).verification_status == "confirmed"
    assert (out / "college_identity_promotion_log.jsonl").exists()


def test_promote_review_candidate_cli_runs_from_repo_root_without_pythonpath(
    tmp_path: Path,
):
    _, out, run_id = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    review_id = f"{run_id}_cli_review_001"
    review_path = out / f"college_identity_review_queue_{run_id}.jsonl"
    review_payload = {
        "run_id": run_id,
        "review_id": review_id,
        "incoming_source_record_id": "fixture_2027_synthetic",
        "minted_prospect_uuid": target,
        "target_prospect_uuid": target,
        "match_score": 1.0,
        "score_breakdown": {"final": 1.0},
        "risk_flags": [],
        "raw_match_features": {},
        "matcher_algorithm_version": "cpr_matcher_v1.0.0",
        "decided_at": None,
        "decision": None,
        "event_id": None,
    }
    existing = review_path.read_text() if review_path.exists() else ""
    review_path.write_text(existing + json.dumps(review_payload, sort_keys=True) + "\n")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/promote_review_candidate.py",
            "--identity-dir",
            str(out),
            "--target",
            target,
            "--decision",
            "confirm",
            "--target-kind",
            "self",
            "--review-id",
            review_id,
            "--reviewer",
            "davidleess",
        ],
        cwd=Path.cwd(),
        env={},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    registry = load_registry(out / "college_prospect_registry.json")
    assert registry.get(target).verification_status == "confirmed"
    rows = [
        json.loads(line)
        for line in review_path.read_text().splitlines()
        if line.strip()
    ]
    row = next(row for row in rows if row["review_id"] == review_id)
    assert row["decision"] == "confirm"
    assert row["decided_at"] is not None
    assert row["event_id"] is not None


def test_reject_closes_review_without_mutating_identity(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    before = load_registry(
        out / "college_prospect_registry.json"
    ).get(target).verification_status

    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="reject", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    after = load_registry(
        out / "college_prospect_registry.json"
    ).get(target).verification_status
    assert result.exit_code == 0
    assert before == after


def test_merge_into_requires_non_empty_evidence(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    uuids = _all_uuids(out)

    with pytest.raises(EvidenceRequiredError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(
                kind="merge_into",
                target_kind="self",
                target=uuids[1],
                survivor=uuids[0],
            ),
            identity_dir=out,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
        )


def test_split_requires_non_empty_evidence(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)

    with pytest.raises(EvidenceRequiredError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(
                kind="split",
                target_kind="self",
                target=_provisional_uuid(out),
                new_full_name="Split Person",
                new_position="WR",
                new_position_group="WR",
            ),
            identity_dir=out,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
        )


def test_idempotent_rerun_same_decision_is_noop(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    log_path = out / "college_identity_promotion_log.jsonl"
    before = log_path.read_bytes()

    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    assert result.exit_code == 0
    assert before == log_path.read_bytes()


def test_conflicting_rerun_fails_closed_without_override(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    with pytest.raises(ConflictingDecisionError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(kind="reject", target_kind="self", target=target),
            identity_dir=out,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
        )


def test_split_mints_new_provisional_uuid_with_logged_metadata(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    before = set(_all_uuids(out))

    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(
            kind="split",
            target_kind="self",
            target=target,
            new_full_name="Second Person",
            new_position="WR",
            new_position_group="WR",
        ),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence="distinct CFBD athlete IDs (12345 vs 67890)",
        note=None,
    )

    assert result.exit_code == 0
    after = set(_all_uuids(out))
    new_uuids = after - before
    assert len(new_uuids) == 1
    new_uuid = next(iter(new_uuids))
    assert target in after

    registry = load_registry(out / "college_prospect_registry.json")
    new_row = registry.get(new_uuid)
    assert new_row.verification_status == "provisional"
    assert new_row.full_name == "Second Person"

    events = [
        json.loads(line)
        for line in (out / "college_identity_promotion_log.jsonl").read_text().splitlines()
        if line.strip()
    ]
    split_events = [event for event in events if event["decision"] == "split"]
    assert split_events
    assert split_events[0]["new_split_uuid"] == new_uuid
    assert split_events[0]["new_full_name"] == "Second Person"
    assert split_events[0]["new_position"] == "WR"
    assert split_events[0]["new_position_group"] == "WR"


def test_replay_after_split_reproduces_registry_byte_identical(tmp_path: Path):
    import shutil

    fixture, out, run_id = _two_row_fixture(tmp_path)

    # Snapshot the genesis state (the state produced by the most recent fixture
    # ingestion, per spec §6.3) BEFORE any promotions land — this is the state replay
    # is supposed to replay over. Re-running ingest_fixture would mint different
    # uuid4 values and break byte-identical reconstruction.
    genesis_dir = tmp_path / "replay_out"
    genesis_dir.mkdir()
    shutil.copy(
        out / "college_prospect_registry.json",
        genesis_dir / "college_prospect_registry.json",
    )
    shutil.copy(
        out / "college_alias_bridge.json",
        genesis_dir / "college_alias_bridge.json",
    )

    target = _provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(
            kind="split",
            target_kind="self",
            target=target,
            new_full_name="Second Person",
            new_position="WR",
            new_position_group="WR",
        ),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence="distinct CFBD athlete IDs",
        note=None,
    )
    registry_after = (out / "college_prospect_registry.json").read_bytes()

    replay_promotion_log(
        log_path=out / "college_identity_promotion_log.jsonl",
        identity_dir=genesis_dir,
    )

    assert (genesis_dir / "college_prospect_registry.json").read_bytes() == registry_after


def test_confirm_target_existing_writes_bridge_entry_and_log_carries_both_uuids(
    tmp_path: Path,
):
    _, out, run_id = _two_row_fixture(tmp_path)
    source_uuid, target_uuid = _all_uuids(out)[:2]

    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target_uuid),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    review_id = f"{run_id}_alias_review_001"
    review_path = out / f"college_identity_review_queue_{run_id}.jsonl"
    source_row = load_registry(out / "college_prospect_registry.json").get(source_uuid)
    review_payload = {
        "run_id": run_id,
        "review_id": review_id,
        "incoming_source_record_id": source_row.source_record_id,
        "minted_prospect_uuid": source_uuid,
        "target_prospect_uuid": target_uuid,
        "match_score": 0.93,
        "score_breakdown": {"final": 0.93},
        "risk_flags": ["cross_position_group"],
        "raw_match_features": {},
        "matcher_algorithm_version": "cpr_matcher_v1.0.0",
        "decided_at": None,
        "decision": None,
        "event_id": None,
    }
    existing = review_path.read_text() if review_path.exists() else ""
    review_path.write_text(existing + json.dumps(review_payload, sort_keys=True) + "\n")

    result = promote_review_candidate(
        review_id=review_id,
        decision=PromotionDecision(
            kind="confirm",
            target_kind="existing",
            target=source_uuid,
            survivor=target_uuid,
        ),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note="alias resolve",
    )

    assert result.exit_code == 0
    bridge = load_bridge(out / "college_alias_bridge.json")
    assert isinstance(bridge, CollegeAliasBridge)
    assert any(isinstance(entry, CollegeAliasBridgeEntry) for entry in bridge.entries)
    assert any(entry.target_prospect_uuid == target_uuid for entry in bridge.entries)

    events = [
        json.loads(line)
        for line in (out / "college_identity_promotion_log.jsonl").read_text().splitlines()
        if line.strip()
    ]
    alias_events = [
        event
        for event in events
        if event.get("source_prospect_uuid") == source_uuid
        and event.get("target_prospect_uuid") == target_uuid
    ]
    assert alias_events
    assert alias_events[0]["survivor_prospect_uuid"] == target_uuid
    assert alias_events[0]["after_status"] == "deprecated"


def test_review_queue_closure_marker_appended_to_originating_review_row(tmp_path: Path):
    _, out, run_id = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    review_id = f"{run_id}_closure_review_001"
    review_path = out / f"college_identity_review_queue_{run_id}.jsonl"
    review_payload = {
        "run_id": run_id,
        "review_id": review_id,
        "incoming_source_record_id": "fixture_2027_synthetic",
        "minted_prospect_uuid": target,
        "target_prospect_uuid": target,
        "match_score": 1.0,
        "score_breakdown": {"final": 1.0},
        "risk_flags": [],
        "raw_match_features": {},
        "matcher_algorithm_version": "cpr_matcher_v1.0.0",
        "decided_at": None,
        "decision": None,
        "event_id": None,
    }
    existing = review_path.read_text() if review_path.exists() else ""
    review_path.write_text(existing + json.dumps(review_payload, sort_keys=True) + "\n")

    result = promote_review_candidate(
        review_id=review_id,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    assert result.exit_code == 0
    rows = [
        json.loads(line)
        for line in review_path.read_text().splitlines()
        if line.strip()
    ]
    matched = [row for row in rows if row.get("review_id") == review_id]
    assert matched
    row = matched[0]
    assert row["decision"] == "confirm"
    assert row["decided_at"] is not None
    assert row["event_id"] is not None


def test_idempotent_same_decision_with_new_review_id_closes_additional_review_edge(
    tmp_path: Path,
):
    _, out, run_id = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    review_path = out / f"college_identity_review_queue_{run_id}.jsonl"

    review_ids = [
        f"{run_id}_multi_edge_review_001",
        f"{run_id}_multi_edge_review_002",
    ]
    for review_id in review_ids:
        review_payload = {
            "run_id": run_id,
            "review_id": review_id,
            "incoming_source_record_id": "fixture_2027_synthetic",
            "minted_prospect_uuid": target,
            "target_prospect_uuid": target,
            "match_score": 1.0,
            "score_breakdown": {"final": 1.0},
            "risk_flags": [],
            "raw_match_features": {},
            "matcher_algorithm_version": "cpr_matcher_v1.0.0",
            "decided_at": None,
            "decision": None,
            "event_id": None,
        }
        existing = review_path.read_text() if review_path.exists() else ""
        review_path.write_text(existing + json.dumps(review_payload, sort_keys=True) + "\n")

    first = promote_review_candidate(
        review_id=review_ids[0],
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    log_after_first = (out / "college_identity_promotion_log.jsonl").read_bytes()

    second = promote_review_candidate(
        review_id=review_ids[1],
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    assert second.exit_code == 0
    assert second.event_id == first.event_id
    assert (out / "college_identity_promotion_log.jsonl").read_bytes() == log_after_first
    rows = [
        json.loads(line)
        for line in review_path.read_text().splitlines()
        if line.strip()
    ]
    closed = {row["review_id"]: row for row in rows if row["review_id"] in review_ids}
    assert closed[review_ids[0]]["decision"] == "confirm"
    assert closed[review_ids[1]]["decision"] == "confirm"
    assert closed[review_ids[0]]["event_id"] == first.event_id
    assert closed[review_ids[1]]["event_id"] == first.event_id


def test_replay_reproduces_registry_AND_bridge_byte_identical(tmp_path: Path):
    import shutil

    fixture, out, run_id = _two_row_fixture(tmp_path)
    source_uuid, target_uuid = _all_uuids(out)[:2]

    # Snapshot the genesis state (per spec §6.3, the state produced by the most recent
    # fixture ingestion) BEFORE any promotions land — replay replays over this state.
    genesis_dir = tmp_path / "replay_out"
    genesis_dir.mkdir()
    shutil.copy(
        out / "college_prospect_registry.json",
        genesis_dir / "college_prospect_registry.json",
    )
    shutil.copy(
        out / "college_alias_bridge.json",
        genesis_dir / "college_alias_bridge.json",
    )

    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target_uuid),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(
            kind="confirm",
            target_kind="existing",
            target=source_uuid,
            survivor=target_uuid,
        ),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    registry_after = (out / "college_prospect_registry.json").read_bytes()
    bridge_after = (out / "college_alias_bridge.json").read_bytes()

    replay_promotion_log(
        log_path=out / "college_identity_promotion_log.jsonl",
        identity_dir=genesis_dir,
    )

    assert (genesis_dir / "college_prospect_registry.json").read_bytes() == registry_after
    assert (genesis_dir / "college_alias_bridge.json").read_bytes() == bridge_after


def test_promotion_log_event_carries_source_record_id_and_snapshot_id(tmp_path: Path):
    _, out, run_id = _two_row_fixture(tmp_path)
    source_uuid, target_uuid = _all_uuids(out)[:2]

    registry = load_registry(out / "college_prospect_registry.json")
    target_row = registry.get(target_uuid)
    source_row = registry.get(source_uuid)
    assert target_row is not None
    assert source_row is not None
    source_row.source_snapshot_id = "fixture_2027_source_snapshot_only"
    atomic_write_registry(registry, out / "college_prospect_registry.json")
    registry = load_registry(out / "college_prospect_registry.json")
    target_row = registry.get(target_uuid)
    source_row = registry.get(source_uuid)
    assert target_row is not None
    assert source_row is not None

    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target_uuid),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )

    review_id = f"{run_id}_source_provenance_review_001"
    review_path = out / f"college_identity_review_queue_{run_id}.jsonl"
    review_payload = {
        "run_id": run_id,
        "review_id": review_id,
        "incoming_source_record_id": source_row.source_record_id,
        "minted_prospect_uuid": source_uuid,
        "target_prospect_uuid": target_uuid,
        "match_score": 0.93,
        "score_breakdown": {"final": 0.93},
        "risk_flags": ["cross_position_group"],
        "raw_match_features": {},
        "matcher_algorithm_version": "cpr_matcher_v1.0.0",
        "decided_at": None,
        "decision": None,
        "event_id": None,
    }
    existing = review_path.read_text() if review_path.exists() else ""
    review_path.write_text(existing + json.dumps(review_payload, sort_keys=True) + "\n")

    promote_review_candidate(
        review_id=review_id,
        decision=PromotionDecision(
            kind="confirm",
            target_kind="existing",
            target=source_uuid,
            survivor=target_uuid,
        ),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note="alias resolve",
    )

    events = [
        json.loads(line)
        for line in (out / "college_identity_promotion_log.jsonl").read_text().splitlines()
        if line.strip()
    ]
    confirm_self_event = next(
        event
        for event in events
        if event["decision"] == "confirm"
        and event["target_kind"] == "self"
        and event["target_prospect_uuid"] == target_uuid
    )
    assert confirm_self_event["source_record_id"] == target_row.source_record_id
    assert confirm_self_event["source_snapshot_id"] == target_row.source_snapshot_id

    alias_event = next(
        event
        for event in events
        if event["decision"] == "confirm"
        and event["target_kind"] == "existing"
        and event["source_prospect_uuid"] == source_uuid
    )
    assert alias_event["source_record_id"] == source_row.source_record_id
    assert alias_event["source_snapshot_id"] == source_row.source_snapshot_id
    assert alias_event["source_record_id"] != target_row.source_record_id
    assert alias_event["source_snapshot_id"] != target_row.source_snapshot_id


def test_apply_logged_event_is_pure_no_fresh_timestamps_or_uuids(tmp_path: Path):
    from src.dynasty_genius.identity import college_prospect_identity as mod

    calls = {"now": 0, "uuid": 0}
    real_now = mod._now_iso
    real_uuid = mod._uuid.uuid4

    def fake_now():
        calls["now"] += 1
        return real_now()

    def fake_uuid():
        calls["uuid"] += 1
        return real_uuid()

    mod._now_iso = fake_now
    mod._uuid.uuid4 = fake_uuid
    try:
        fixture, out, run_id = _two_row_fixture(tmp_path)
        target = _provisional_uuid(out)
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
            identity_dir=out,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
        )
        calls["now"] = 0
        calls["uuid"] = 0

        genesis_dir = tmp_path / "replay_out"
        ingest_fixture(fixture_path=fixture, identity_dir=genesis_dir, run_id=run_id)
        calls["now"] = 0
        calls["uuid"] = 0
        replay_promotion_log(
            log_path=out / "college_identity_promotion_log.jsonl",
            identity_dir=genesis_dir,
        )

        assert calls["now"] == 0
        assert calls["uuid"] == 0
    finally:
        mod._now_iso = real_now
        mod._uuid.uuid4 = real_uuid
