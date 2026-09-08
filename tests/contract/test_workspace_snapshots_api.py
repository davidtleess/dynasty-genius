"""Exercise the browser identity handshake and private archive through HTTP."""

import json
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import workspace_snapshots as route
from tests.contract.workspace_snapshot_fixtures import encoded, write_sources


@pytest.fixture
def client(tmp_path, monkeypatch):
    paths = write_sources(tmp_path / "inputs")
    monkeypatch.setenv("DG_WORKSPACE_ARCHIVE_ROOT", str(tmp_path / "archive"))
    monkeypatch.setenv("DG_MARKET_RANKS_MANIFEST", str(paths[0]))
    monkeypatch.setattr(route, "_current_paths", lambda: paths)
    monkeypatch.setattr(
        route, "_now", lambda: datetime(2026, 9, 9, tzinfo=timezone.utc)
    )
    monkeypatch.setattr(route, "_code_sha", lambda: "unknown")
    app = FastAPI()
    app.include_router(route.router, prefix="/api")
    return TestClient(app), tmp_path, paths


def expected(paths):
    bundle = route.load_workspace_snapshot(*paths)
    return route._source(bundle)


def test_get_never_creates_archive_and_missing_config_is_explicit(client, monkeypatch):
    http, root, _ = client
    assert http.get("/api/research/snapshots").json() == {
        "status": "available",
        "snapshots": [],
    }
    assert not (root / "archive").exists()
    monkeypatch.delenv("DG_WORKSPACE_ARCHIVE_ROOT")
    assert http.get("/api/research/snapshots").json() == {"status": "not_configured"}
    assert (
        http.post(
            "/api/research/snapshots",
            json={"expected": dict.fromkeys(route.SOURCE_KEYS, "a")},
        ).status_code
        == 503
    )
    assert not (root / "archive").exists()


def test_save_duplicate_reload_and_exact_archived_read(client):
    http, root, paths = client
    body = {"expected": expected(paths)}
    first = http.post("/api/research/snapshots", json=body)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["created"] is True
    receipt = result["snapshot"]
    assert receipt["evaluation_status"] == "ungraded"
    assert receipt["counts"]["model"] == 3
    assert receipt["counts"]["available"] == 2
    again = http.post("/api/research/snapshots", json=body).json()
    assert again["created"] is False and again["snapshot"] == receipt
    assert http.get("/api/research/snapshots").json()["snapshots"] == [receipt]
    replay = http.get("/api/research/snapshots/" + receipt["snapshot_id"])
    assert replay.status_code == 200
    assert replay.json()["ranks"] == route.load_workspace_snapshot(*paths).ranks
    assert (
        replay.json()["comparison"] == route.load_workspace_snapshot(*paths).comparison
    )
    assert http.get("/api/research/snapshots/" + "0" * 64).status_code == 404


@pytest.mark.parametrize(
    "key",
    [
        "report_run",
        "report_sha256",
        "market_sha256",
        "league_sha256",
        "catalog_run",
        "catalog_content_sha256",
    ],
)
def test_changed_browser_source_refuses_without_writing(client, key):
    http, root, paths = client
    source = expected(paths)
    source[key] = "changed"
    assert (
        http.post("/api/research/snapshots", json={"expected": source}).status_code
        == 409
    )
    assert not (root / "archive").exists()


def test_tampered_input_and_corrupt_archive_never_fall_back(client):
    http, root, paths = client
    body = {"expected": expected(paths)}
    receipt = http.post("/api/research/snapshots", json=body).json()["snapshot"]
    archived = root / "archive" / receipt["snapshot_id"] / "report.json"
    archived.write_bytes(archived.read_bytes() + b" ")
    assert http.get("/api/research/snapshots").status_code == 503
    assert (
        http.get("/api/research/snapshots/" + receipt["snapshot_id"]).status_code == 503
    )
    assert http.post("/api/research/snapshots", json=body).status_code == 503
    assert str(root) not in http.get("/api/research/snapshots").text
    paths[1].write_bytes(paths[1].read_bytes() + b" ")
    assert http.post("/api/research/snapshots", json=body).status_code == 503


def test_same_forecasts_with_new_prose_keep_original_reading_and_plan(
    client, monkeypatch
):
    http, _, paths = client
    body = {"expected": expected(paths)}
    receipt = http.post("/api/research/snapshots", json=body).json()["snapshot"]
    original = route.load_workspace_snapshot

    def revised(*args):
        bundle = original(*args)
        bundle.ranks["basis"]["summary"] = "A copy edit changes no football forecasts."
        plan = json.loads(bundle.artifacts["evaluation-plan.json"])
        plan["plan_id"] = "revised-v2"
        bundle.artifacts["evaluation-plan.json"] = encoded(plan)
        return bundle

    monkeypatch.setattr(route, "load_workspace_snapshot", revised)
    again = http.post("/api/research/snapshots", json=body).json()
    assert not again["created"] and again["snapshot"] == receipt


def test_unexpected_client_payload_refused(client):
    http, _, paths = client
    assert (
        http.post(
            "/api/research/snapshots", json={"expected": expected(paths), "ranks": []}
        ).status_code
        == 422
    )
