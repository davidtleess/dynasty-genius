from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def _client_with_frontend_dist(monkeypatch, tmp_path: Path) -> TestClient:
    dist_dir = tmp_path / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>Dynasty Genius</div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text(
        "console.log('dynasty genius shell');\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    import app.main as app_main

    app_main = importlib.reload(app_main)
    return TestClient(app_main.app)


def test_frontend_spa_paths_serve_index_when_dist_exists(monkeypatch, tmp_path):
    client = _client_with_frontend_dist(monkeypatch, tmp_path)

    for path in ("/", "/roster"):
        response = client.get(path)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "Dynasty Genius" in response.text


def test_frontend_mount_does_not_shadow_api_or_fastapi_docs(monkeypatch, tmp_path):
    client = _client_with_frontend_dist(monkeypatch, tmp_path)

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    assert openapi_response.headers["content-type"].startswith("application/json")
    assert openapi_response.json()["openapi"]

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    assert docs_response.headers["content-type"].startswith("text/html")
    assert "swagger" in docs_response.text.lower()
    assert "<div id='root'>" not in docs_response.text

    redoc_response = client.get("/redoc")
    assert redoc_response.status_code == 200
    assert redoc_response.headers["content-type"].startswith("text/html")
    assert "redoc" in redoc_response.text.lower()
    assert "<div id='root'>" not in redoc_response.text

    unknown_api_response = client.get("/api/frontend-static-mount-red")
    assert unknown_api_response.status_code == 404
    assert unknown_api_response.headers["content-type"].startswith("application/json")
    assert "<div id='root'>" not in unknown_api_response.text


def test_frontend_asset_paths_do_not_fall_back_to_index(monkeypatch, tmp_path):
    client = _client_with_frontend_dist(monkeypatch, tmp_path)

    asset_response = client.get("/assets/app.js")
    assert asset_response.status_code == 200
    assert asset_response.headers["content-type"].startswith("text/javascript")
    assert "dynasty genius shell" in asset_response.text
    assert "<div id='root'>" not in asset_response.text

    missing_asset_response = client.get("/assets/missing.js")
    assert missing_asset_response.status_code == 404
    assert "<div id='root'>" not in missing_asset_response.text


def test_frontend_mount_does_not_claim_rookie_board_path(monkeypatch, tmp_path):
    client = _client_with_frontend_dist(monkeypatch, tmp_path)

    response = client.get("/rookie_board.html")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "<div id='root'>" not in response.text
