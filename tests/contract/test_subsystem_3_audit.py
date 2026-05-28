"""Subsystem 3 - Round 2 audit, coverage, and provisional-leak contracts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeAliasBridge,
    CollegeAliasBridgeEntry,
    CollegeProspectRegistry,
    ConfirmedProspectUuid,
    NormalizedCollegeProspectRow,
    ProspectUuidDeprecatedMerged,
    ProspectUuidNotConfirmed,
    RegistryEntry,
    StatusHistoryEntry,
    UnknownProspectUuid,
    atomic_write_registry,
    compute_match_key,
    ingest_fixture,
    load_registry,
    normalize_name,
    resolve_prospect_cfbd_athlete_id,
    validate_registry_graph,
)

_INVIOLATE_PATHS = [
    Path("app/data/identity/_runs/prospect_registry.json"),
    Path("app/data/identity/_runs/composite_registry.json"),
    Path("app/data/prospect_alias_bridge.json"),
    Path("src/dynasty_genius/adapters/prospect_identity_resolver.py"),
]

_BANNED_FIELD_NAMES = {
    "ktc_value",
    "fc_value",
    "adp",
    "market_value",
    "mock_rank",
    "draft_selection_pct",
    "drafts_selected_in",
    "dynasty_nerds_adp",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _basic_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.json"
    path.write_text(
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
                    }
                ],
            }
        )
    )
    return path


def _row(name: str, *, source_record_id: str) -> NormalizedCollegeProspectRow:
    return NormalizedCollegeProspectRow.model_validate(
        {
            "raw_name": name,
            "normalized_name": normalize_name(name),
            "full_name": name,
            "position": "WR",
            "position_group": "WR",
            "draft_class": 2027,
            "current_school": "Texas",
            "prior_schools": [],
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
            "source": "manual_fixture",
            "source_record_id": source_record_id,
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


def _entry(
    uuid: str,
    *,
    status: str,
    source_record_id: str,
    name: str = "Sample",
    merged_into: str | None = None,
) -> RegistryEntry:
    row = _row(name, source_record_id=source_record_id)
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
                decision="confirm",
                after_status=status,
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=merged_into,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **row.model_dump(),
    )


def test_leak_contract_1_init_rejects_provisional_deprecated_unknown(tmp_path: Path):
    fixture = _basic_fixture(tmp_path)
    out = tmp_path / "out"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="run_a")
    registry = load_registry(out / "college_prospect_registry.json")
    provisional_uuid = next(iter(registry.entries.values())).prospect_uuid

    with pytest.raises(ProspectUuidNotConfirmed):
        ConfirmedProspectUuid(provisional_uuid, registry=registry)
    with pytest.raises(UnknownProspectUuid):
        ConfirmedProspectUuid("cpr_nonexistent", registry=registry)

    survivor_uuid = "cpr_11111111-1111-4111-8111-111111111111"
    deprecated_uuid = "cpr_22222222-2222-4222-8222-222222222222"
    registry.entries[survivor_uuid] = _entry(
        survivor_uuid,
        status="confirmed",
        source_record_id="survivor_src",
    )
    registry.entries[deprecated_uuid] = _entry(
        deprecated_uuid,
        status="deprecated",
        source_record_id="deprecated_src",
        merged_into=survivor_uuid,
    )
    with pytest.raises(ProspectUuidDeprecatedMerged):
        ConfirmedProspectUuid(deprecated_uuid, registry=registry)


def test_leak_contract_2_resolver_returns_none_on_provisional(tmp_path: Path):
    fixture = _basic_fixture(tmp_path)
    out = tmp_path / "out"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="run_a")
    registry = load_registry(out / "college_prospect_registry.json")

    result = resolve_prospect_cfbd_athlete_id(
        name="Arch Manning",
        position="QB",
        draft_class=2027,
        registry=registry,
    )

    assert result is None


def test_leak_contract_3_bridge_entry_maps_only_to_confirmed_uuid():
    provisional_uuid = "cpr_p1111111-1111-4111-8111-111111111111"
    deprecated_uuid = "cpr_d2222222-2222-4222-8222-222222222222"
    confirmed_uuid = "cpr_c3333333-3333-4333-8333-333333333333"
    registry = CollegeProspectRegistry(
        entries={
            provisional_uuid: _entry(
                provisional_uuid,
                status="provisional",
                source_record_id="src_provisional",
            ),
            deprecated_uuid: _entry(
                deprecated_uuid,
                status="deprecated",
                source_record_id="src_deprecated",
            ),
            confirmed_uuid: _entry(
                confirmed_uuid,
                status="confirmed",
                source_record_id="src_confirmed",
            ),
        }
    )
    match_key = compute_match_key(
        normalized_name="sample",
        position_group="WR",
        draft_class=2027,
    )

    for target_uuid in [provisional_uuid, deprecated_uuid, "cpr_unknown"]:
        bridge = CollegeAliasBridge(
            entries=[
                CollegeAliasBridgeEntry(
                    match_key=match_key,
                    source_record_id=f"bridge_{target_uuid}",
                    target_prospect_uuid=target_uuid,
                )
            ]
        )
        errors = validate_registry_graph(registry, bridge=bridge)
        assert errors, f"bridge target {target_uuid} should fail validation"

    valid_bridge = CollegeAliasBridge(
        entries=[
            CollegeAliasBridgeEntry(
                match_key=match_key,
                source_record_id="bridge_confirmed",
                target_prospect_uuid=confirmed_uuid,
            )
        ]
    )
    assert validate_registry_graph(registry, bridge=valid_bridge) == []


def test_leak_contract_4_source_record_id_unique_per_confirmed_uuid():
    registry = CollegeProspectRegistry(
        entries={
            "cpr_aaaa": _entry(
                "cpr_aaaa",
                status="confirmed",
                source_record_id="shared_001",
                name="First Shared",
            ),
            "cpr_bbbb": _entry(
                "cpr_bbbb",
                status="confirmed",
                source_record_id="shared_001",
                name="Second Shared",
            ),
        }
    )

    errors = validate_registry_graph(registry)

    assert any("source_record_id collision" in error for error in errors)


def test_leak_contract_5_full_graph_validation_runs_clean_on_empty():
    assert validate_registry_graph(CollegeProspectRegistry()) == []


def test_source_id_conflict_queue_contains_no_market_or_mock_fields(tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    seed_uuid = "cpr_seed1111-1111-4111-8111-111111111111"
    seed_registry = CollegeProspectRegistry(
        entries={
            seed_uuid: _entry(
                seed_uuid,
                status="confirmed",
                source_record_id="src_001",
                name="Seed Name",
            )
        }
    )
    atomic_write_registry(seed_registry, out_dir / "college_prospect_registry.json")
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "metadata": {"snapshot_id": "fixture_2027_v1"},
                "entries": [
                    {
                        **_row(
                            "Conflicting Name",
                            source_record_id="src_001",
                        ).model_dump(),
                        "current_school": "Bama",
                    }
                ],
            }
        )
    )

    ingest_fixture(fixture_path=fixture, identity_dir=out_dir, run_id="audit_run")

    conflict_path = out_dir / "college_identity_source_id_conflict_audit_run.jsonl"
    assert conflict_path.exists()
    records = [
        json.loads(line)
        for line in conflict_path.read_text().splitlines()
        if line.strip()
    ]
    assert records
    for record in records:
        leaked = set(record) & _BANNED_FIELD_NAMES
        assert leaked == set()


def test_existing_artifacts_byte_unchanged_before_and_after_subsystem_3_module_import():
    repo_root = Path(__file__).resolve().parents[2]
    existing_paths = [path for path in _INVIOLATE_PATHS if (repo_root / path).exists()]
    assert existing_paths, "byte-unchanged test requires at least one real artifact"
    before = {path: _sha256(repo_root / path) for path in existing_paths}

    from src.dynasty_genius.identity.college_prospect_identity import (
        CollegeProspectRegistry as ImportedRegistry,
    )

    _ = ImportedRegistry()
    after = {path: _sha256(repo_root / path) for path in existing_paths}
    assert before == after


def test_registry_schema_has_no_market_or_mock_fields():
    fields = set(NormalizedCollegeProspectRow.model_fields) | set(
        RegistryEntry.model_fields
    )
    leaked = fields & _BANNED_FIELD_NAMES
    assert leaked == set()


def test_coverage_matrix_counts_reconcile_including_round_2_kinds(tmp_path: Path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "metadata": {"snapshot_id": "fixture_2027_v1"},
                "entries": [
                    {
                        **_row(
                            f"Person {idx}",
                            source_record_id=f"fixture_2027_{idx:03d}",
                        ).model_dump(),
                        "raw_name": f"Person {idx}",
                        "normalized_name": normalize_name(f"Person {idx}"),
                        "full_name": f"Person {idx}",
                    }
                    for idx in range(1, 4)
                ],
            }
        )
    )
    out = tmp_path / "out"
    result = ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="reconcile_run")
    coverage = json.loads(
        (out / "college_identity_coverage_matrix_reconcile_run.json").read_text()
    )

    counted_kinds = [
        "minted_new",
        "idempotent_rerun",
        "minted_new_provisional_with_review_candidate",
        "minted_new_with_surfaced_candidates",
        "source_id_conflict",
    ]
    assert "source_id_conflict" in coverage
    accounted = sum(coverage.get(kind, 0) for kind in counted_kinds)
    assert accounted == coverage["total_input_rows"] == 3
    assert result.exit_code == 0
