import json
from collections import Counter
from pathlib import Path

import pytest

from src.dynasty_genius.capture.workspace_snapshot_sources import (
    WorkspaceSnapshotSourceError,
    load_workspace_snapshot,
)
from tests.contract.workspace_snapshot_fixtures import encoded, sha, write_sources


def test_loads_exact_buffers_and_complete_populations(tmp_path, monkeypatch):
    paths = write_sources(tmp_path / "inputs")
    calls = Counter()
    original = Path.read_bytes

    def read(path):
        calls[path] += 1
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    bundle = load_workspace_snapshot(*paths)
    assert len(bundle.artifacts) == 7
    assert set(calls.values()) == {1}
    assert (
        json.loads(bundle.artifacts["evaluation-plan.json"])["plan_id"]
        == "workspace-production-2026-v1"
    )
    assert bundle.ranks["coverage"]["model_players"] == 3
    assert bundle.ranks["coverage"]["common_players"] == 2
    assert len(bundle.comparison["roster"]) == 1
    assert len(bundle.comparison["available"]) == 3  # includes the cut player
    assert bundle.comparison["available"][0]["now_points"] is None
    assert bundle.ranks["rows"][0]["model_value"] is not None
    assert bundle.artifacts["report.json"] == original(tmp_path / "inputs/report.json")
    assert bundle.comparison["source"]["catalog_content_sha256"] == sha(
        json.dumps(
            json.loads(bundle.artifacts["catalog.json"]),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    )


@pytest.mark.parametrize(
    "filename", ["report.json", "market.json", "league.json", "catalog.json"]
)
def test_refuses_tampered_source_bytes(tmp_path, filename):
    paths = write_sources(tmp_path / "inputs")
    p = tmp_path / "inputs" / filename
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(WorkspaceSnapshotSourceError):
        load_workspace_snapshot(*paths)


def test_refuses_catalog_from_another_report_even_if_companion_rebound(tmp_path):
    paths = write_sources(tmp_path / "inputs")
    catalog = json.loads(paths[1].read_bytes())
    catalog["source_report_run"] = "other"
    paths[1].write_bytes(encoded(catalog))
    companion = json.loads(paths[2].read_bytes())
    companion["outputs_sha256"]["catalog.json"] = sha(encoded(catalog))
    paths[2].write_bytes(encoded(companion))
    with pytest.raises(WorkspaceSnapshotSourceError):
        load_workspace_snapshot(*paths)


def test_refuses_duplicate_json_keys_in_manifest(tmp_path):
    paths = write_sources(tmp_path / "inputs")
    paths[0].write_bytes(b'{"schema_version":1,"schema_version":1}')
    with pytest.raises(WorkspaceSnapshotSourceError):
        load_workspace_snapshot(*paths)


def test_refuses_catalog_position_conflict_with_rank_population(tmp_path):
    paths = write_sources(tmp_path / "inputs")
    catalog = json.loads(paths[1].read_bytes())
    catalog["rows_detail"][1]["league_position"] = "WR"
    paths[1].write_bytes(encoded(catalog))
    companion = json.loads(paths[2].read_bytes())
    companion["outputs_sha256"]["catalog.json"] = sha(encoded(catalog))
    paths[2].write_bytes(encoded(companion))
    with pytest.raises(WorkspaceSnapshotSourceError):
        load_workspace_snapshot(*paths)
