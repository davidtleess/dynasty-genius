"""Subsystem 4 bridge join + realized outcome contract tests (§5.1, §11.5)."""
from __future__ import annotations

import builtins
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.dynasty_genius.eval import backtest_mock_draft as bmd
from src.dynasty_genius.identity.prospect_nfl_bridge import (
    CollegeProspectBridge,
    NflTruthRow,
    ProspectNflBridgeEntry,
)

UUID_A = "cpr_00000000-0000-4000-8000-000000000001"
UUID_B = "cpr_00000000-0000-4000-8000-000000000002"
UUID_C = "cpr_00000000-0000-4000-8000-000000000003"


def _consensus(prospect_uuid: str = UUID_A) -> bmd.ProspectConsensus:
    return bmd.ProspectConsensus(
        prospect_uuid=prospect_uuid,
        projected_pick_median=12.0,
        projected_pick_iqr=4.0,
        projected_pick_min=10,
        projected_pick_max=14,
        n_sources=5,
        n_unique_analysts=5,
        snapshot_ids_used=["snapshot_a", "snapshot_b"],
        staleness_days=4.0,
        abstention_tier="exact_pick",
        abstention_reason=None,
    )


def _provenance() -> dict:
    return {
        "nflreadr_source": "nflreadpy.draft_picks",
        "nflreadr_season": 2025,
        "draft_truth_content_hash": "hash_2025_v1",
        "nflreadr_fetched_at": "2026-05-28T12:00:00Z",
    }


def _evidence(
    *,
    full_name: str = "Arch Manning",
    position: str = "QB",
    college: str = "Texas",
) -> dict:
    return {
        "full_name": full_name,
        "position": position,
        "college": college,
        "fetched_at": "2026-05-28T12:00:00Z",
    }


def _drafted_entry(
    prospect_uuid: str = UUID_A,
    *,
    gsis_id: str = "00-0001",
    pfr_id: str | None = "MannAr00",
    draft_year: int = 2025,
    pick_no: int = 1,
    draft_round: int = 1,
    team: str = "TEN",
    evidence_snapshot: dict | None = None,
) -> ProspectNflBridgeEntry:
    return ProspectNflBridgeEntry.model_validate(
        {
            "prospect_uuid": prospect_uuid,
            "gsis_id": gsis_id,
            "pfr_id": pfr_id,
            "draft_year": draft_year,
            "draft_pick_no": pick_no,
            "draft_round": draft_round,
            "nfl_team": team,
            "udfa": False,
            "evidence_snapshot": (
                _evidence() if evidence_snapshot is None else evidence_snapshot
            ),
            "event_id": f"ev_{prospect_uuid[-4:]}",
            "decided_at": "2026-05-28T12:00:00Z",
            "reviewer_id": "davidleess",
            "decision": "confirm",
            "note": None,
            **_provenance(),
        }
    )


def _udfa_entry(prospect_uuid: str = UUID_A) -> ProspectNflBridgeEntry:
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
            "event_id": f"ev_{prospect_uuid[-4:]}",
            "decided_at": "2026-05-28T12:00:00Z",
            "reviewer_id": "davidleess",
            "decision": "udfa",
            "note": "verified absent from nflreadr draft truth",
            **_provenance(),
        }
    )


def _bridge(*entries: ProspectNflBridgeEntry) -> CollegeProspectBridge:
    return CollegeProspectBridge(
        metadata={"draft_year": 2025, "schema_version": "prospect_nfl_bridge_v1.0.0"},
        entries=list(entries),
    )


def _truth(
    *,
    gsis_id: str = "00-0001",
    pfr_id: str | None = "MannAr00",
    full_name: str = "Arch Manning",
    position: str = "QB",
    college: str | None = "Texas",
    draft_year: int = 2025,
    pick_no: int = 1,
    draft_round: int = 1,
    team: str = "TEN",
) -> NflTruthRow:
    return NflTruthRow(
        gsis_id=gsis_id,
        pfr_id=pfr_id,
        full_name=full_name,
        normalized_name=full_name.lower(),
        position=position,
        college=college,
        draft_year=draft_year,
        draft_pick_no=pick_no,
        draft_round=draft_round,
        nfl_team=team,
        fetched_at="2026-05-28T12:00:00Z",
    )


def _join(consensuses, bridge, truth_rows):
    return bmd.join_bridge_to_realized(consensuses, bridge, truth_rows)


def test_realized_outcome_schema_extra_forbid():
    RealizedOutcome = getattr(bmd, "RealizedOutcome")
    expected_fields = {
        "prospect_uuid",
        "gsis_id",
        "pfr_id",
        "draft_year",
        "draft_pick_no",
        "draft_round",
        "nfl_team",
        "udfa",
        "unbridged_prospect",
        "bridge_stale_warning",
        "warnings",
        "evidence_full_name",
        "evidence_position",
        "evidence_college",
    }
    assert set(RealizedOutcome.model_fields) == expected_fields

    outcome = RealizedOutcome.model_validate(
        {
            "prospect_uuid": UUID_A,
            "gsis_id": "00-0001",
            "pfr_id": "MannAr00",
            "draft_year": 2025,
            "draft_pick_no": 1,
            "draft_round": 1,
            "nfl_team": "TEN",
            "udfa": False,
            "unbridged_prospect": False,
            "bridge_stale_warning": False,
            "warnings": [],
            "evidence_full_name": "Arch Manning",
            "evidence_position": "QB",
            "evidence_college": "Texas",
        }
    )
    assert outcome.prospect_uuid == UUID_A

    bad = outcome.model_dump()
    bad["unexpected"] = "reject"
    with pytest.raises(ValidationError):
        RealizedOutcome.model_validate(bad)


def test_join_diagnostics_schema_extra_forbid():
    JoinDiagnostics = getattr(bmd, "JoinDiagnostics")
    expected_fields = {
        "hard_block_reasons",
        "review_queue_payload",
        "duplicate_gsis_ids_detected",
        "wrong_year_truth_collisions",
        "evidence_incomplete_uuids",
    }
    assert set(JoinDiagnostics.model_fields) == expected_fields

    diagnostics = JoinDiagnostics.model_validate(
        {
            "hard_block_reasons": [],
            "review_queue_payload": [],
            "duplicate_gsis_ids_detected": [],
            "wrong_year_truth_collisions": [],
            "evidence_incomplete_uuids": [],
        }
    )
    assert diagnostics.hard_block_reasons == []

    bad = diagnostics.model_dump()
    bad["unexpected"] = "reject"
    with pytest.raises(ValidationError):
        JoinDiagnostics.model_validate(bad)


def test_join_matches_confirmed_bridge_entry():
    pairs, diagnostics = _join(
        [_consensus(UUID_A)],
        _bridge(_drafted_entry(UUID_A, pick_no=7, team="LV")),
        [_truth(pick_no=7, team="LV")],
    )

    assert len(pairs) == 1
    consensus, outcome = pairs[0]
    assert consensus.prospect_uuid == UUID_A
    assert outcome.prospect_uuid == UUID_A
    assert outcome.gsis_id == "00-0001"
    assert outcome.draft_pick_no == 7
    assert outcome.nfl_team == "LV"
    assert outcome.udfa is False
    assert outcome.unbridged_prospect is False
    assert outcome.bridge_stale_warning is False
    assert outcome.warnings == []
    assert diagnostics.hard_block_reasons == []


def test_join_represents_explicit_udfa_entry():
    pairs, diagnostics = _join(
        [_consensus(UUID_A)],
        _bridge(_udfa_entry(UUID_A)),
        [],
    )

    outcome = pairs[0][1]
    assert outcome.prospect_uuid == UUID_A
    assert outcome.udfa is True
    assert outcome.gsis_id is None
    assert outcome.pfr_id is None
    assert outcome.draft_pick_no is None
    assert outcome.draft_round is None
    assert outcome.nfl_team is None
    assert outcome.unbridged_prospect is False
    assert outcome.bridge_stale_warning is False
    assert outcome.warnings == []
    assert diagnostics.hard_block_reasons == []


def test_join_flags_unbridged_prospect():
    pairs, diagnostics = _join([_consensus(UUID_A)], _bridge(), [])

    outcome = pairs[0][1]
    assert outcome.prospect_uuid == UUID_A
    assert outcome.unbridged_prospect is True
    assert outcome.udfa is False
    assert "unbridged_prospect" in outcome.warnings
    assert diagnostics.hard_block_reasons == []


def test_truth_disappearance_fires_stale_warning():
    pairs, diagnostics = _join(
        [_consensus(UUID_A)],
        _bridge(_drafted_entry(UUID_A, gsis_id="00-9999")),
        [_truth(gsis_id="00-0001")],
    )

    outcome = pairs[0][1]
    assert outcome.bridge_stale_warning is True
    assert "truth_row_missing" in outcome.warnings
    assert diagnostics.hard_block_reasons == []


def test_duplicate_gsis_id_in_nflreadr_fail_closed():
    pairs, diagnostics = _join(
        [_consensus(UUID_A)],
        _bridge(_drafted_entry(UUID_A, gsis_id="00-0001")),
        [
            _truth(gsis_id="00-0001", pick_no=1),
            _truth(gsis_id="00-0001", pick_no=2),
        ],
    )

    outcome = pairs[0][1]
    assert "nflreadr_duplicate_gsis_id_warning" in outcome.warnings
    assert diagnostics.duplicate_gsis_ids_detected == ["00-0001"]
    assert "nflreadr_duplicate_gsis_id" in diagnostics.hard_block_reasons
    assert outcome.bridge_stale_warning is True


def test_compound_key_wrong_year_truth_mismatch_hard_conflict():
    pairs, diagnostics = _join(
        [_consensus(UUID_A)],
        _bridge(_drafted_entry(UUID_A, gsis_id="00-0001", draft_year=2025)),
        [_truth(gsis_id="00-0001", draft_year=2024)],
    )

    outcome = pairs[0][1]
    assert "truth_row_wrong_year_warning" in outcome.warnings
    assert diagnostics.wrong_year_truth_collisions == ["00-0001"]
    assert "wrong_year_truth_collision" in diagnostics.hard_block_reasons
    assert diagnostics.review_queue_payload
    review_entry = diagnostics.review_queue_payload[0]
    assert review_entry["prospect_uuid"] == UUID_A
    assert review_entry["gsis_id"] == "00-0001"
    assert review_entry["reason"] == "wrong_year_truth_collision"


def test_missing_evidence_snapshot_drafted_entry_hard_block():
    pairs, diagnostics = _join(
        [_consensus(UUID_A)],
        _bridge(_drafted_entry(UUID_A, evidence_snapshot={})),
        [_truth(gsis_id="00-0001")],
    )

    outcome = pairs[0][1]
    assert "evidence_snapshot_missing_warning" in outcome.warnings
    assert outcome.bridge_stale_warning is True
    assert outcome.evidence_full_name is None
    assert diagnostics.evidence_incomplete_uuids == [UUID_A]
    assert "evidence_snapshot_missing" in diagnostics.hard_block_reasons


def test_pick_round_team_divergence_fires_stale_warning_with_normalization():
    pairs, diagnostics = _join(
        [
            _consensus(UUID_A),
            _consensus(UUID_B),
            _consensus(UUID_C),
        ],
        _bridge(
            _drafted_entry(UUID_A, gsis_id="00-0001", pick_no=10, team="TEN"),
            _drafted_entry(UUID_B, gsis_id="00-0002", pick_no=32, draft_round=1),
            _drafted_entry(UUID_C, gsis_id="00-0003", pick_no=18, team="OAK"),
        ),
        [
            _truth(gsis_id="00-0001", pick_no=11, team="TEN"),
            _truth(gsis_id="00-0002", pick_no=32, draft_round=2),
            _truth(gsis_id="00-0003", pick_no=18, team="LVR"),
        ],
    )

    outcomes = {outcome.prospect_uuid: outcome for _consensus, outcome in pairs}
    assert outcomes[UUID_A].bridge_stale_warning is True
    assert "draft_pick_no_diverged" in outcomes[UUID_A].warnings
    assert outcomes[UUID_B].bridge_stale_warning is True
    assert "draft_round_diverged" in outcomes[UUID_B].warnings
    assert outcomes[UUID_C].bridge_stale_warning is False
    assert "nfl_team_diverged" not in outcomes[UUID_C].warnings
    assert diagnostics.hard_block_reasons == []


def test_normalize_team_code_equivalence_classes():
    assert bmd.normalize_team_code("OAK") == bmd.normalize_team_code("LVR")
    assert bmd.normalize_team_code("SDG") == bmd.normalize_team_code("LAC")
    assert bmd.normalize_team_code("LAR") == bmd.normalize_team_code("LA")
    assert bmd.normalize_team_code("WAS") == bmd.normalize_team_code("WSH")
    assert bmd.normalize_team_code(" ten ") == "TEN"


def test_join_is_purely_functional(monkeypatch):
    writes: list[tuple[str, object]] = []
    original_open = builtins.open
    original_path_open = Path.open

    def spy_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            writes.append(("builtins.open", file))
        return original_open(file, mode, *args, **kwargs)

    def forbid_write_text(self, *args, **kwargs):
        writes.append(("Path.write_text", self))
        raise AssertionError("join_bridge_to_realized must not write files")

    def forbid_write_bytes(self, *args, **kwargs):
        writes.append(("Path.write_bytes", self))
        raise AssertionError("join_bridge_to_realized must not write files")

    def spy_path_open(self, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            writes.append(("Path.open", self))
        return original_path_open(self, mode, *args, **kwargs)

    def forbid_replace(*args, **kwargs):
        writes.append(("os.replace", args))
        raise AssertionError("join_bridge_to_realized must not write files")

    def forbid_rename(*args, **kwargs):
        writes.append(("os.rename", args))
        raise AssertionError("join_bridge_to_realized must not write files")

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(Path, "write_text", forbid_write_text)
    monkeypatch.setattr(Path, "write_bytes", forbid_write_bytes)
    monkeypatch.setattr(Path, "open", spy_path_open)
    monkeypatch.setattr(os, "replace", forbid_replace)
    monkeypatch.setattr(os, "rename", forbid_rename)

    _join(
        [_consensus(UUID_A)],
        _bridge(_drafted_entry(UUID_A, pick_no=4)),
        [_truth(pick_no=4)],
    )

    assert writes == []
