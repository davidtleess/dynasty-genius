"""Subsystem 3 - Round 2 ingestion, bridge, and ambiguity contracts (section 10.5)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeAliasBridge,
    CollegeAliasBridgeEntry,
    CollegeProspectRegistry,
    IngestionOutcome,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    atomic_write_bridge,
    atomic_write_registry,
    compute_match_key,
    ingest_fixture,
    load_bridge,
    load_registry,
    mint_or_match,
    normalize_name,
    validate_registry_graph,
)


def _row(
    name: str,
    position: str = "WR",
    position_group: str = "WR",
    school: str = "Ohio State",
    draft_class: int = 2027,
    sid: str = "fixture_2027_001",
    cfbd: str | None = None,
) -> NormalizedCollegeProspectRow:
    return NormalizedCollegeProspectRow.model_validate(
        {
            "raw_name": name,
            "normalized_name": normalize_name(name),
            "full_name": name,
            "position": position,
            "position_group": position_group,
            "draft_class": draft_class,
            "current_school": school,
            "prior_schools": [],
            "cfbd_athlete_id": cfbd,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
            "source": "manual_fixture",
            "source_record_id": sid,
            "source_snapshot_id": "fixture_2027_v1",
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


def _registry_entry(
    uuid: str,
    *,
    status: str,
    row: NormalizedCollegeProspectRow,
    decision: str = "ingest",
    merged_into: str | None = None,
) -> RegistryEntry:
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,
        match_key=compute_match_key(
            normalized_name=row.normalized_name,
            position_group=row.position_group,
            draft_class=row.draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision=decision,
                after_status=status,
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="system_ingestion",
            )
        ],
        merged_into_prospect_uuid=merged_into,
        reviewer_id="system_ingestion",
        reviewer_metadata={},
        **row.model_dump(),
    )


def test_atomic_write_uses_tmp_then_rename(tmp_path: Path, monkeypatch):
    path = tmp_path / "registry.json"
    registry = CollegeProspectRegistry(
        metadata={"snapshot": "fixture_2027_v1"},
        entries={},
    )
    seen_tmp: list[Path] = []
    original_replace = os.replace

    def spy_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]):
        seen_tmp.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr("os.replace", spy_replace)
    atomic_write_registry(registry, path)

    assert path.exists()
    assert seen_tmp and seen_tmp[0].name.endswith(".tmp")
    reloaded = load_registry(path)
    assert reloaded.metadata == {"snapshot": "fixture_2027_v1"}


def test_idempotent_rerun_same_source_record_id_and_snapshot_reuses_uuid():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()
    incoming = _row(
        "Arch Manning",
        position="QB",
        position_group="QB",
        school="Texas",
        sid="fixture_2027_001",
    )

    outcome_1 = mint_or_match(incoming, registry, bridge=bridge)
    assert isinstance(outcome_1, IngestionOutcome)
    assert outcome_1.kind == "minted_new"
    first_uuid = outcome_1.prospect_uuid

    outcome_2 = mint_or_match(incoming, registry, bridge=bridge)
    assert outcome_2.kind == "idempotent_rerun"
    assert outcome_2.prospect_uuid == first_uuid


def test_same_match_key_different_source_record_id_mints_provisional_with_common_name_flag():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()
    first = _row("Mike Williams", position="WR", position_group="WR", school="Clemson", sid="src_A")
    second = _row("Mike Williams", position="WR", position_group="WR", school="USC", sid="src_B")

    outcome_1 = mint_or_match(first, registry, bridge=bridge)
    outcome_2 = mint_or_match(second, registry, bridge=bridge)

    assert outcome_1.prospect_uuid != outcome_2.prospect_uuid
    assert outcome_2.kind in {
        "minted_new_provisional_with_review_candidate",
        "minted_new_with_surfaced_candidates",
    }
    assert outcome_2.review_candidates, "common_name candidate should be surfaced"
    assert any("common_name" in c.risk_flags for c in outcome_2.review_candidates)


def test_multiple_existing_matches_emit_ambiguous_existing_candidates_review_entry():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()
    first = _row("Common Surname", school="Texas", sid="src_A")
    second = _row("Common Surname", school="LSU", sid="src_B")
    third = _row("Common Surname", school="Bama", sid="src_C")

    mint_or_match(first, registry, bridge=bridge)
    mint_or_match(second, registry, bridge=bridge)
    outcome = mint_or_match(third, registry, bridge=bridge)

    assert outcome.review_candidates
    assert any(
        "ambiguous_existing_candidates" in cand.risk_flags
        for cand in outcome.review_candidates
    )


def test_source_id_conflict_preempts_fuzzy_output_and_writes_to_dedicated_queue():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()

    first = _row("Original Name", school="Texas", sid="src_001")
    mint_or_match(first, registry, bridge=bridge)
    existing_uuid = next(iter(registry.entries.keys()))
    registry.entries[existing_uuid].verification_status = "confirmed"

    conflicting = _row("Different Person", school="Bama", sid="src_001")
    outcome = mint_or_match(conflicting, registry, bridge=bridge)

    assert outcome.kind == "source_id_conflict"
    assert outcome.review_candidates == ()
    assert outcome.source_id_conflict_record is not None
    assert outcome.source_id_conflict_record["incoming_source_record_id"] == "src_001"
    assert outcome.source_id_conflict_record["existing_prospect_uuid"] == existing_uuid


def test_source_id_conflict_also_fires_on_shared_cfbd_athlete_id():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()

    first = _row(
        "Arch Manning",
        position="QB",
        position_group="QB",
        school="Texas",
        sid="src_A",
        cfbd="cfbd_12345",
    )
    mint_or_match(first, registry, bridge=bridge)
    next(iter(registry.entries.values())).verification_status = "confirmed"

    second = _row(
        "Wrong Name",
        position="WR",
        position_group="WR",
        school="LSU",
        sid="src_B",
        cfbd="cfbd_12345",
    )
    outcome = mint_or_match(second, registry, bridge=bridge)

    assert outcome.kind == "source_id_conflict"
    assert outcome.review_candidates == ()


def test_whitelist_neighbor_surfaced_via_section_5_4_query_even_with_different_match_key():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()

    existing_wr = _row(
        "Whitelist Name",
        position="WR",
        position_group="WR",
        school="Whitelist U",
        sid="existing_001",
    )
    mint_or_match(existing_wr, registry, bridge=bridge)
    existing_uuid = next(iter(registry.entries.keys()))
    registry.entries[existing_uuid].verification_status = "confirmed"

    incoming_te = _row(
        "Whitelist Name",
        position="TE",
        position_group="TE",
        school="Whitelist U",
        sid="incoming_001",
    )
    outcome = mint_or_match(incoming_te, registry, bridge=bridge)

    assert outcome.review_candidates, "section 5.4 must surface WR-TE neighbor"
    cross = [
        c for c in outcome.review_candidates if "cross_position_group" in c.risk_flags
    ]
    assert cross
    assert all("position_transition_allowed" in c.risk_flags for c in cross)


def test_mint_or_match_calls_surface_review_candidates_not_just_exact_match_key():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()

    existing = _row("Fuzzy Source", school="Source U", sid="existing_001")
    mint_or_match(existing, registry, bridge=bridge)
    next(iter(registry.entries.values())).verification_status = "confirmed"

    incoming = _row("Fuzy Source", school="Source U", sid="incoming_001")
    outcome = mint_or_match(incoming, registry, bridge=bridge)

    assert compute_match_key(
        normalized_name=incoming.normalized_name,
        position_group=incoming.position_group,
        draft_class=incoming.draft_class,
    ) != compute_match_key(
        normalized_name=existing.normalized_name,
        position_group=existing.position_group,
        draft_class=existing.draft_class,
    )
    assert outcome.review_candidates, (
        "near-name candidate should surface via surface_review_candidates(), "
        "not just exact match_key lookup"
    )


def test_atomic_write_bridge_uses_tmp_then_rename(tmp_path: Path, monkeypatch):
    path = tmp_path / "bridge.json"
    bridge = CollegeAliasBridge(metadata={"snapshot": "fixture_2027_v1"}, entries=[])
    seen_tmp: list[Path] = []
    original_replace = os.replace

    def spy_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]):
        seen_tmp.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr("os.replace", spy_replace)
    atomic_write_bridge(bridge, path)

    assert path.exists()
    assert seen_tmp and seen_tmp[0].name.endswith(".tmp")
    reloaded = load_bridge(path)
    assert reloaded.metadata == {"snapshot": "fixture_2027_v1"}


def test_validate_bridge_targets_rejects_provisional_target():
    provisional_uuid = "cpr_pppppppp-pppp-4ppp-8ppp-pppppppppppp"
    registry = CollegeProspectRegistry()
    row = _row("Sample", sid="src_X")
    registry.entries[provisional_uuid] = _registry_entry(
        provisional_uuid,
        status="provisional",
        row=row,
    )
    bridge = CollegeAliasBridge(
        entries=[
            CollegeAliasBridgeEntry(
                match_key=compute_match_key(
                    normalized_name="sample",
                    position_group="WR",
                    draft_class=2027,
                ),
                source_record_id="src_X",
                target_prospect_uuid=provisional_uuid,
            )
        ]
    )

    errors = validate_registry_graph(registry, bridge=bridge)
    assert any(
        "bridge target" in error.lower() and "not confirmed" in error.lower()
        for error in errors
    )


def test_ingest_fixture_writes_alias_bridge_artifact(tmp_path: Path):
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "metadata": {"snapshot_id": "fixture_2027_v1"},
                "entries": [
                    _row(
                        "Arch Manning",
                        position="QB",
                        position_group="QB",
                        school="Texas",
                        sid="fixture_2027_001",
                    ).model_dump()
                ],
            }
        )
    )
    out_dir = tmp_path / "out"

    result = ingest_fixture(
        fixture_path=fixture_path,
        identity_dir=out_dir,
        run_id="run_bridge",
    )

    bridge_path = out_dir / "college_alias_bridge.json"
    assert bridge_path.exists()
    bridge = load_bridge(bridge_path)
    assert bridge.entries == [], "fresh ingestion seeds an empty bridge"
    assert result.exit_code == 0


def test_ingest_fixture_writes_source_id_conflict_queue_when_conflicts_found(
    tmp_path: Path,
):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    seed_registry = CollegeProspectRegistry()
    seed_row = _row("Original Name", school="Texas", sid="src_001")
    seed_uuid = "cpr_seed0000-0000-4000-8000-000000000001"
    seed_registry.entries[seed_uuid] = _registry_entry(
        seed_uuid,
        status="confirmed",
        row=seed_row,
        decision="confirm",
    )
    atomic_write_registry(seed_registry, out_dir / "college_prospect_registry.json")

    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "metadata": {"snapshot_id": "fixture_2027_v1"},
                "entries": [
                    _row("Different Person", school="Bama", sid="src_001").model_dump()
                ],
            }
        )
    )

    result = ingest_fixture(
        fixture_path=fixture_path,
        identity_dir=out_dir,
        run_id="conflict_run",
    )

    conflict_path = out_dir / "college_identity_source_id_conflict_conflict_run.jsonl"
    assert conflict_path.exists()
    lines = [line for line in conflict_path.read_text().splitlines() if line.strip()]
    assert lines, "source_id_conflict queue must record the collision"
    record = json.loads(lines[0])
    assert record["incoming_source_record_id"] == "src_001"
    assert record["existing_prospect_uuid"] == seed_uuid
    assert result.exit_code != 0

    review_path = out_dir / "college_identity_review_queue_conflict_run.jsonl"
    if review_path.exists() and review_path.read_text().strip():
        for line in review_path.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            assert entry["incoming_source_record_id"] != "src_001"


def test_ingest_fixture_coverage_matrix_includes_source_id_conflict_count(
    tmp_path: Path,
):
    out_dir = tmp_path / "out"
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "metadata": {"snapshot_id": "fixture_2027_v1"},
                "entries": [
                    _row("Person A", sid="src_A").model_dump(),
                    _row("Person B", sid="src_B").model_dump(),
                ],
            }
        )
    )

    result = ingest_fixture(
        fixture_path=fixture_path,
        identity_dir=out_dir,
        run_id="counts_run",
    )

    coverage_path = out_dir / "college_identity_coverage_matrix_counts_run.json"
    coverage = json.loads(coverage_path.read_text())
    assert "source_id_conflict" in coverage
    assert coverage["source_id_conflict"] == 0
    assert coverage["total_input_rows"] == 2
    assert result.exit_code == 0


def test_ingest_fixture_handles_missing_fixture_file(tmp_path: Path):
    result = ingest_fixture(
        fixture_path=tmp_path / "missing_fixture.json",
        identity_dir=tmp_path / "out",
        run_id="missing_fixture_run",
    )

    assert result.exit_code == 0
    assert result.coverage["total_input_rows"] == 0


def test_ingest_fixture_handles_zero_byte_fixture_file(tmp_path: Path):
    fixture_path = tmp_path / "zero_byte_fixture.json"
    fixture_path.write_text("")

    result = ingest_fixture(
        fixture_path=fixture_path,
        identity_dir=tmp_path / "out",
        run_id="zero_byte_fixture_run",
    )

    assert result.exit_code == 0
    assert result.coverage["total_input_rows"] == 0


def test_validate_bridge_targets_rejects_deprecated_target():
    deprecated_uuid = "cpr_dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    registry = CollegeProspectRegistry()
    row = _row("Sample", sid="src_X")
    registry.entries[deprecated_uuid] = _registry_entry(
        deprecated_uuid,
        status="deprecated",
        row=row,
        decision="merge_into",
    )
    bridge = CollegeAliasBridge(
        entries=[
            CollegeAliasBridgeEntry(
                match_key=compute_match_key(
                    normalized_name="sample",
                    position_group="WR",
                    draft_class=2027,
                ),
                source_record_id="src_X",
                target_prospect_uuid=deprecated_uuid,
            )
        ]
    )

    errors = validate_registry_graph(registry, bridge=bridge)
    assert any(
        "bridge target" in error.lower() and "not confirmed" in error.lower()
        for error in errors
    )
