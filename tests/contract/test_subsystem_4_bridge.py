"""Subsystem 4 bridge atomic persistence + decision-log replay tests (§3.2)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.dynasty_genius.identity.prospect_nfl_bridge import (
    BridgeValidationError,
    CollegeProspectBridge,
    ProspectNflBridgeEntry,
    apply_decision_event,
    atomic_write_bridge,
    atomic_write_decision_log,
    load_bridge,
    load_decision_log,
    replay_decision_log,
)


def _provenance() -> dict:
    return {
        "nflreadr_source": "nflreadpy.draft_picks",
        "nflreadr_season": 2025,
        "draft_truth_content_hash": "abc123",
        "nflreadr_fetched_at": "2026-05-28T12:00:00Z",
    }


def _drafted_entry(
    prospect_uuid: str,
    gsis_id: str,
    pick_no: int,
) -> ProspectNflBridgeEntry:
    return ProspectNflBridgeEntry.model_validate(
        {
            "prospect_uuid": prospect_uuid,
            "gsis_id": gsis_id,
            "pfr_id": None,
            "draft_year": 2025,
            "draft_pick_no": pick_no,
            "draft_round": 1 if pick_no <= 32 else (pick_no - 1) // 32 + 1,
            "nfl_team": "CAR",
            "udfa": False,
            "evidence_snapshot": {
                "full_name": "X",
                "position": "QB",
                "college": "Y",
                "fetched_at": "Z",
            },
            "event_id": f"ev_{prospect_uuid[:8]}",
            "decided_at": "2026-05-28T12:00:00Z",
            "reviewer_id": "davidleess",
            "decision": "confirm",
            "note": None,
            **_provenance(),
        }
    )


def _udfa_entry(prospect_uuid: str) -> ProspectNflBridgeEntry:
    return ProspectNflBridgeEntry.model_validate(
        {
            "prospect_uuid": prospect_uuid,
            "gsis_id": None,
            "pfr_id": None,
            "draft_year": 2025,
            "draft_pick_no": None,
            "draft_round": None,
            "nfl_team": None,
            "udfa": True,
            "evidence_snapshot": None,
            "event_id": f"ev_{prospect_uuid[:8]}",
            "decided_at": "2026-05-28T12:00:00Z",
            "reviewer_id": "davidleess",
            "decision": "udfa",
            "note": "verified absent from nflreadr 2025 post-draft truth",
            **_provenance(),
        }
    )


def test_load_bridge_handles_missing_file(tmp_path: Path):
    bridge = load_bridge(tmp_path / "absent.json")
    assert isinstance(bridge, CollegeProspectBridge)
    assert bridge.entries == []


def test_load_bridge_handles_zero_byte_file(tmp_path: Path):
    bridge_path = tmp_path / "empty.json"
    bridge_path.write_text("")
    bridge = load_bridge(bridge_path)
    assert isinstance(bridge, CollegeProspectBridge)
    assert bridge.entries == []


def test_atomic_write_bridge_uses_tmp_then_rename(tmp_path: Path, monkeypatch):
    bridge_path = tmp_path / "bridge.json"
    bridge = CollegeProspectBridge(metadata={"draft_year": 2025}, entries=[])
    seen_tmp_paths: list[Path] = []
    original_replace = os.replace

    def spy_replace(src, dst):
        seen_tmp_paths.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy_replace)
    atomic_write_bridge(bridge, bridge_path)

    assert bridge_path.exists()
    assert seen_tmp_paths
    assert seen_tmp_paths[0].name.endswith(".tmp")
    assert load_bridge(bridge_path).metadata == {"draft_year": 2025}


def test_decision_log_round_trip(tmp_path: Path):
    log_path = tmp_path / "decision_log.jsonl"
    events = [
        {"event_id": "ev_1", "decision": "confirm", "prospect_uuid": "cpr_a"},
        {"event_id": "ev_2", "decision": "reject", "prospect_uuid": "cpr_b"},
    ]

    atomic_write_decision_log(events, log_path)

    assert load_decision_log(log_path) == events


def test_apply_decision_event_confirm_appends_accepted_entry():
    bridge = CollegeProspectBridge(entries=[])
    entry = _drafted_entry("cpr_a", "00-0001", 1)
    event = {"decision": "confirm", "entry": entry.model_dump()}

    apply_decision_event(event, bridge)

    assert len(bridge.entries) == 1
    assert bridge.entries[0].prospect_uuid == "cpr_a"


def test_apply_decision_event_reject_does_not_mutate_bridge():
    bridge = CollegeProspectBridge(entries=[])
    event = {"decision": "reject", "prospect_uuid": "cpr_a", "event_id": "ev_1"}

    apply_decision_event(event, bridge)

    assert bridge.entries == []


def test_apply_decision_event_defer_does_not_mutate_bridge():
    bridge = CollegeProspectBridge(entries=[])
    event = {
        "decision": "defer",
        "prospect_uuid": "cpr_a",
        "event_id": "ev_1",
        "note": "need more info",
    }

    apply_decision_event(event, bridge)

    assert bridge.entries == []


def test_replay_fail_closed_on_non_empty_genesis(tmp_path: Path):
    pre_existing_entry = _drafted_entry("cpr_pre", "00-9999", 32)
    seeded_bridge = CollegeProspectBridge(entries=[pre_existing_entry])
    bridge_path = tmp_path / "seeded_bridge.json"
    atomic_write_bridge(seeded_bridge, bridge_path)
    log_path = tmp_path / "decision_log.jsonl"
    atomic_write_decision_log([], log_path)

    with pytest.raises(BridgeValidationError):
        replay_decision_log(log_path=log_path, bridge_path=bridge_path)


def test_replay_decision_log_reproduces_bridge_byte_identical(tmp_path: Path):
    entries_to_accept = [
        _drafted_entry("cpr_aaaa", "00-0001", 1),
        _udfa_entry("cpr_udfa"),
        _drafted_entry("cpr_bbbb", "00-0002", 5),
    ]
    log_events = [
        {
            "decision": "confirm",
            "entry": entries_to_accept[0].model_dump(),
            "event_id": "ev_1",
            "prospect_uuid": "cpr_aaaa",
        },
        {
            "decision": "reject",
            "event_id": "ev_2",
            "prospect_uuid": "cpr_xxxx",
            "note": "not a match",
        },
        {
            "decision": "udfa",
            "entry": entries_to_accept[1].model_dump(),
            "event_id": "ev_3",
            "prospect_uuid": "cpr_udfa",
        },
        {
            "decision": "confirm",
            "entry": entries_to_accept[2].model_dump(),
            "event_id": "ev_4",
            "prospect_uuid": "cpr_bbbb",
        },
        {
            "decision": "defer",
            "event_id": "ev_5",
            "prospect_uuid": "cpr_yyyy",
            "note": "transfer pending",
        },
    ]
    log_path = tmp_path / "decision_log.jsonl"
    atomic_write_decision_log(log_events, log_path)

    live_bridge = CollegeProspectBridge(entries=[])
    for event in log_events:
        apply_decision_event(event, live_bridge)
    live_bridge_path = tmp_path / "live_bridge.json"
    atomic_write_bridge(live_bridge, live_bridge_path)

    replay_bridge_path = tmp_path / "replay" / "live_bridge.json"
    replay_decision_log(log_path=log_path, bridge_path=replay_bridge_path)

    assert replay_bridge_path.read_bytes() == live_bridge_path.read_bytes()
    reloaded = load_bridge(replay_bridge_path)
    assert len(reloaded.entries) == 3
    assert {entry.prospect_uuid for entry in reloaded.entries} == {
        "cpr_aaaa",
        "cpr_bbbb",
        "cpr_udfa",
    }
