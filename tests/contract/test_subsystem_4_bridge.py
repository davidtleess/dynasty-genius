"""Subsystem 4 bridge atomic persistence + decision-log replay tests (§3.2)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
)
from src.dynasty_genius.identity.prospect_nfl_bridge import (
    NFL_POSITION_WHITELIST,
    BridgeConflictingDecisionError,
    BridgeEvidenceRequiredError,
    BridgeValidationError,
    CollegeProspectBridge,
    NflTruthRow,
    PromotionDecision,
    PromotionResult,
    ProspectNflBridgeEntry,
    apply_decision_event,
    atomic_write_bridge,
    atomic_write_decision_log,
    is_nfl_position_pair_compatible,
    load_bridge,
    load_decision_log,
    promote_bridge_candidate,
    replay_decision_log,
    score_nfl_candidate,
    surface_nfl_bridge_candidates,
    validate_bridge_graph,
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


def _s3_row_for(
    uuid: str,
    status: str = "confirmed",
    draft_class: int = 2025,
) -> RegistryEntry:
    base = NormalizedCollegeProspectRow.model_validate(
        {
            "raw_name": "Arch Manning",
            "normalized_name": "arch manning",
            "full_name": "Arch Manning",
            "position": "QB",
            "position_group": "QB",
            "draft_class": draft_class,
            "current_school": "Texas",
            "prior_schools": [],
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
            "source": "manual_fixture",
            "source_record_id": f"src_{uuid[:8]}",
            "source_snapshot_id": "fixture_2025_v1",
            "id_provenance": {
                "cfbd_athlete_id": None,
                "cfb_player_id": None,
                "pfr_id": None,
                "gsis_id": None,
                "sleeper_id": None,
            },
            "notes": None,
        }
    )
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,
        match_key=compute_match_key(
            normalized_name=base.normalized_name,
            position_group="QB",
            draft_class=draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status=status,
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **base.model_dump(),
    )


def _s3_registry_for(*uuids: str, draft_class: int = 2025) -> CollegeProspectRegistry:
    return CollegeProspectRegistry(
        entries={uuid: _s3_row_for(uuid, draft_class=draft_class) for uuid in uuids}
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


def _confirmed_s3_row(
    uuid: str,
    name: str,
    position: str,
    position_group: str,
    school: str = "Texas",
) -> RegistryEntry:
    base = NormalizedCollegeProspectRow.model_validate(
        {
            "raw_name": name,
            "normalized_name": name.lower(),
            "full_name": name,
            "position": position,
            "position_group": position_group,
            "draft_class": 2025,
            "current_school": school,
            "prior_schools": [],
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
            "source": "manual_fixture",
            "source_record_id": f"src_{uuid[:8]}",
            "source_snapshot_id": "fixture_2025_v1",
            "id_provenance": {
                "cfbd_athlete_id": None,
                "cfb_player_id": None,
                "pfr_id": None,
                "gsis_id": None,
                "sleeper_id": None,
            },
            "notes": None,
        }
    )
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status="confirmed",
        match_key=compute_match_key(
            normalized_name=base.normalized_name,
            position_group=position_group,
            draft_class=2025,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status="confirmed",
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **base.model_dump(),
    )


def _nfl_truth_row(
    name: str,
    position: str,
    gsis_id: str,
    pick_no: int,
    team: str = "CAR",
) -> NflTruthRow:
    return NflTruthRow(
        gsis_id=gsis_id,
        pfr_id=None,
        full_name=name,
        normalized_name=name.lower(),
        position=position,
        college="Texas",
        draft_year=2025,
        draft_pick_no=pick_no,
        draft_round=1 if pick_no <= 32 else 2,
        nfl_team=team,
        fetched_at="2026-05-28T12:00:00Z",
    )


def test_nfl_position_whitelist_supports_known_transitions():
    assert frozenset({"EDGE", "OLB"}) in NFL_POSITION_WHITELIST
    assert is_nfl_position_pair_compatible("QB", "QB") is True
    assert is_nfl_position_pair_compatible("EDGE", "OLB") is True
    assert is_nfl_position_pair_compatible("EDGE", "DE") is True
    assert is_nfl_position_pair_compatible("S", "FS") is True
    assert is_nfl_position_pair_compatible("S", "SS") is True
    assert is_nfl_position_pair_compatible("CB", "CB") is True
    assert is_nfl_position_pair_compatible("WR", "RB") is False


def test_nfl_position_hard_blocks_offense_vs_defense():
    assert is_nfl_position_pair_compatible("QB", "DE") is False
    assert is_nfl_position_pair_compatible("WR", "CB") is False


def test_score_nfl_candidate_uses_s3_score_candidate_pattern():
    college = _confirmed_s3_row("cpr_aaa", "Arch Manning", "QB", "QB")
    nfl_truth = _nfl_truth_row("Arch Manning", "QB", "00-0001", 1)

    result = score_nfl_candidate(college, nfl_truth)

    assert 0.0 <= result.match_score <= 1.0
    assert result.gsis_id == "00-0001"


def test_surface_nfl_bridge_candidates_returns_high_score_matches():
    college = _confirmed_s3_row("cpr_aaa", "Arch Manning", "QB", "QB")
    nfl_rows = [
        _nfl_truth_row("Caleb Williams", "QB", "00-0002", 10),
        _nfl_truth_row("Arch Manning", "QB", "00-0001", 1),
    ]

    candidates = surface_nfl_bridge_candidates(college, nfl_rows)

    assert candidates
    assert candidates[0].gsis_id == "00-0001"


def test_surface_excludes_hard_blocked_positions():
    college = _confirmed_s3_row("cpr_aaa", "Arch Manning", "QB", "QB")
    nfl_rows = [_nfl_truth_row("Arch Manning", "DE", "00-0001", 1)]

    assert surface_nfl_bridge_candidates(college, nfl_rows) == []


def test_surface_includes_whitelist_position_transition():
    college = _confirmed_s3_row("cpr_aaa", "Aidan Hutchinson", "EDGE", "EDGE")
    nfl_rows = [_nfl_truth_row("Aidan Hutchinson", "OLB", "00-0001", 1)]

    candidates = surface_nfl_bridge_candidates(college, nfl_rows)

    assert candidates
    assert "position_transition_allowed" in candidates[0].risk_flags


def _make_review_payload(review_id: str, prospect_uuid: str, gsis_id: str) -> dict:
    return {
        "review_id": review_id,
        "prospect_uuid": prospect_uuid,
        "gsis_id": gsis_id,
        "match_score": 0.95,
        "decided_at": None,
        "decision": None,
        "event_id": None,
    }


def test_promote_confirm_writes_three_point_trail(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    review_path = identity_dir / "prospect_nfl_review_queue_2025_run_a.jsonl"
    review_path.write_text(
        json.dumps(_make_review_payload("rev_1", "cpr_aaa", "00-0001")) + "\n"
    )
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    decision = PromotionDecision(kind="confirm", entry=entry)

    result = promote_bridge_candidate(
        review_id="rev_1",
        decision=decision,
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
        s3_registry=_s3_registry_for("cpr_aaa"),
    )

    assert isinstance(result, PromotionResult)
    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert len(bridge.entries) == 1
    assert bridge.entries[0].prospect_uuid == "cpr_aaa"
    log = load_decision_log(identity_dir / "prospect_nfl_bridge_decision_log_2025.jsonl")
    assert len(log) == 1
    assert log[0]["decision"] == "confirm"
    closed_rows = [
        json.loads(line) for line in review_path.read_text().splitlines() if line.strip()
    ]
    assert closed_rows[0]["decision"] == "confirm"
    assert closed_rows[0]["event_id"] is not None
    assert closed_rows[0]["decided_at"] is not None


def test_promote_udfa_requires_evidence(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    udfa_entry = _udfa_entry("cpr_udfa")
    decision = PromotionDecision(kind="udfa", entry=udfa_entry)

    with pytest.raises(BridgeEvidenceRequiredError):
        promote_bridge_candidate(
            review_id=None,
            decision=decision,
            identity_dir=identity_dir,
            draft_year=2025,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
            s3_registry=_s3_registry_for("cpr_udfa"),
        )


def test_promote_reject_closes_review_without_mutating_bridge(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    review_path = identity_dir / "prospect_nfl_review_queue_2025_run_a.jsonl"
    review_path.write_text(
        json.dumps(_make_review_payload("rev_1", "cpr_xxx", "00-9999")) + "\n"
    )
    decision = PromotionDecision(kind="reject", prospect_uuid="cpr_xxx")

    result = promote_bridge_candidate(
        review_id="rev_1",
        decision=decision,
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note="not a match",
    )

    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert bridge.entries == []
    closed_rows = [
        json.loads(line) for line in review_path.read_text().splitlines() if line.strip()
    ]
    assert closed_rows[0]["decision"] == "reject"


def test_promote_defer_closes_review_without_mutating_bridge(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    review_path = identity_dir / "prospect_nfl_review_queue_2025_run_a.jsonl"
    review_path.write_text(
        json.dumps(_make_review_payload("rev_1", "cpr_xxx", "00-9999")) + "\n"
    )
    decision = PromotionDecision(kind="defer", prospect_uuid="cpr_xxx")

    result = promote_bridge_candidate(
        review_id="rev_1",
        decision=decision,
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note="transfer pending verification",
    )

    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert bridge.entries == []
    closed_rows = [
        json.loads(line) for line in review_path.read_text().splitlines() if line.strip()
    ]
    assert closed_rows[0]["decision"] == "defer"


def test_idempotent_rerun_same_decision_is_noop(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    decision = PromotionDecision(kind="confirm", entry=entry)
    s3_registry = _s3_registry_for("cpr_aaa")
    result_first = promote_bridge_candidate(
        review_id=None,
        decision=decision,
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
        s3_registry=s3_registry,
    )
    log_path = identity_dir / "prospect_nfl_bridge_decision_log_2025.jsonl"
    before = log_path.read_bytes()

    result_second = promote_bridge_candidate(
        review_id=None,
        decision=decision,
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
        s3_registry=s3_registry,
    )

    assert result_second.exit_code == 0
    assert result_second.event_id == result_first.event_id
    assert before == log_path.read_bytes()


def test_conflicting_rerun_raises(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    s3_registry = _s3_registry_for("cpr_aaa")
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    promote_bridge_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", entry=entry),
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
        s3_registry=s3_registry,
    )
    udfa_entry = _udfa_entry("cpr_aaa")

    with pytest.raises(BridgeConflictingDecisionError):
        promote_bridge_candidate(
            review_id=None,
            decision=PromotionDecision(kind="udfa", entry=udfa_entry),
            identity_dir=identity_dir,
            draft_year=2025,
            reviewer_id="davidleess",
            evidence="verified not drafted",
            note=None,
            s3_registry=s3_registry,
        )


def test_validate_bridge_graph_rejects_duplicate_prospect_uuid():
    e1 = _drafted_entry("cpr_aaa", "00-0001", 1)
    e2 = _drafted_entry("cpr_aaa", "00-0002", 5)
    bridge = CollegeProspectBridge(entries=[e1, e2])
    errors = validate_bridge_graph(bridge)
    assert any("prospect_uuid" in error and "duplicate" in error.lower() for error in errors)


def test_validate_bridge_graph_rejects_duplicate_gsis_id():
    e1 = _drafted_entry("cpr_aaa", "00-0001", 1)
    e2 = _drafted_entry("cpr_bbb", "00-0001", 5)
    bridge = CollegeProspectBridge(entries=[e1, e2])
    errors = validate_bridge_graph(bridge)
    assert any("gsis_id" in error and "duplicate" in error.lower() for error in errors)


def test_defer_then_confirm_succeeds(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    promote_bridge_candidate(
        review_id=None,
        decision=PromotionDecision(kind="defer", prospect_uuid="cpr_aaa"),
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note="transfer pending",
    )
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)

    result = promote_bridge_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", entry=entry),
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
        s3_registry=_s3_registry_for("cpr_aaa"),
    )

    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert any(entry.prospect_uuid == "cpr_aaa" for entry in bridge.entries)


def test_reject_then_confirm_succeeds(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    promote_bridge_candidate(
        review_id=None,
        decision=PromotionDecision(kind="reject", prospect_uuid="cpr_aaa"),
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note="wrong match candidate",
    )
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)

    result = promote_bridge_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", entry=entry),
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
        s3_registry=_s3_registry_for("cpr_aaa"),
    )

    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert any(entry.prospect_uuid == "cpr_aaa" for entry in bridge.entries)


def test_confirm_then_different_accepted_decision_conflicts(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    s3_registry = _s3_registry_for("cpr_aaa")
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    promote_bridge_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", entry=entry),
        identity_dir=identity_dir,
        draft_year=2025,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
        s3_registry=s3_registry,
    )
    udfa_entry = _udfa_entry("cpr_aaa")

    with pytest.raises(BridgeConflictingDecisionError):
        promote_bridge_candidate(
            review_id=None,
            decision=PromotionDecision(kind="udfa", entry=udfa_entry),
            identity_dir=identity_dir,
            draft_year=2025,
            reviewer_id="davidleess",
            evidence="verified not drafted",
            note=None,
            s3_registry=s3_registry,
        )


def test_promote_confirm_rejects_entry_draft_year_mismatching_artifact_draft_year(
    tmp_path: Path,
):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    uuid = "cpr_00000000-0000-4000-8000-000000000001"
    s3_registry = CollegeProspectRegistry(
        entries={uuid: _s3_row_for(uuid, status="confirmed", draft_class=2024)}
    )
    entry_2024 = ProspectNflBridgeEntry.model_validate(
        {**_drafted_entry("cpr_tmp", "00-0001", 1).model_dump(), "prospect_uuid": uuid, "draft_year": 2024}
    )

    with pytest.raises(BridgeValidationError):
        promote_bridge_candidate(
            review_id=None,
            decision=PromotionDecision(kind="confirm", entry=entry_2024),
            identity_dir=identity_dir,
            draft_year=2025,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
            s3_registry=s3_registry,
        )

    assert not (identity_dir / "prospect_to_nfl_bridge_2024.json").exists()
    assert not (identity_dir / "prospect_to_nfl_bridge_2025.json").exists()
