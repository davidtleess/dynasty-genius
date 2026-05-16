"""Identity snapshot generator tests.

The Phase 13 identity audit gates later training work. Historical bake-off
artifacts need an immutable capture of the identity map used for the run.
"""
from __future__ import annotations

import json

import pytest

from src.dynasty_genius.audit.identity_snapshot_generator import (
    IdentitySnapshotError,
    IdentitySnapshotRow,
    generate_identity_snapshot,
    load_identity_snapshot,
    write_identity_snapshot,
)


def test_generate_identity_snapshot_serializes_mapping_by_player_id():
    snapshot = generate_identity_snapshot(
        [
            IdentitySnapshotRow(
                player_id="dg_12345",
                gsis_id="00-0012345",
                sleeper_id="9876",
                pff_id="123",
                pfr_id="DoeJo00",
            )
        ],
        run_id="identity_run_001",
        created_at="2026-05-15T22:50:00Z",
        mapping_version="1.0.0",
    )

    data = snapshot.as_dict()

    assert data["run_id"] == "identity_run_001"
    assert data["timestamp"] == "2026-05-15T22:50:00Z"
    assert data["immutable"] is True
    assert data["mapping_version"] == "1.0.0"
    assert data["mappings"] == {
        "dg_12345": {
            "gsis_id": "00-0012345",
            "sleeper_id": "9876",
            "pff_id": "123",
            "pfr_id": "DoeJo00",
        }
    }


def test_generate_identity_snapshot_rejects_duplicate_player_ids():
    rows = [
        IdentitySnapshotRow(player_id="dg_duplicate", gsis_id="00-001"),
        IdentitySnapshotRow(player_id="dg_duplicate", gsis_id="00-002"),
    ]

    with pytest.raises(IdentitySnapshotError, match="duplicate player_id"):
        generate_identity_snapshot(rows, run_id="identity_run_001")


def test_write_identity_snapshot_refuses_to_overwrite(tmp_path):
    snapshot = generate_identity_snapshot(
        [IdentitySnapshotRow(player_id="dg_12345", sleeper_id="9876")],
        run_id="identity_run_001",
        created_at="2026-05-15T22:50:00Z",
    )
    path = tmp_path / "identity_snapshot_identity_run_001.json"

    write_identity_snapshot(path, snapshot)

    with pytest.raises(IdentitySnapshotError, match="already exists"):
        write_identity_snapshot(path, snapshot)


def test_load_identity_snapshot_requires_immutable_true(tmp_path):
    path = tmp_path / "identity_snapshot_bad.json"
    path.write_text(
        json.dumps(
            {
                "run_id": "identity_run_001",
                "timestamp": "2026-05-15T22:50:00Z",
                "immutable": False,
                "mapping_version": "1.0.0",
                "mappings": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(IdentitySnapshotError, match="immutable"):
        load_identity_snapshot(path)
