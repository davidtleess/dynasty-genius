"""A preview can serve a verified private headshot collection without shared cache writes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.headshot_assets import (
    HeadshotCacheConfigurationError,
    mount_headshots,
)


def test_explicit_collection_served_at_existing_player_urls(tmp_path, monkeypatch):
    source = tmp_path / "run/headshots"
    source.mkdir(parents=True)
    image = b"\x89PNG\r\n\x1a\nsource-photo"
    (source / "9509.jpg").write_bytes(image)
    monkeypatch.setenv("DG_HEADSHOT_CACHE_ROOT", str(source))
    app = FastAPI()
    mount_headshots(app, repo_root=tmp_path / "repo")
    http = TestClient(app)
    assert http.get("/assets/headshots/9509.jpg").content == image
    assert http.get("/assets/headshots/absent.jpg").status_code == 404
    assert not (tmp_path / "repo").exists()


def test_absent_default_cache_does_not_create_directories(tmp_path, monkeypatch):
    monkeypatch.delenv("DG_HEADSHOT_CACHE_ROOT", raising=False)
    app = FastAPI()
    mount_headshots(app, repo_root=tmp_path)
    assert TestClient(app).get("/assets/headshots/9509.jpg").status_code == 404
    assert list(tmp_path.iterdir()) == []


def test_existing_default_collection_still_works(tmp_path, monkeypatch):
    monkeypatch.delenv("DG_HEADSHOT_CACHE_ROOT", raising=False)
    source = tmp_path / "app/data/assets/headshots"
    source.mkdir(parents=True)
    (source / "9509.jpg").write_bytes(b"cached-photo")
    app = FastAPI()
    mount_headshots(app, repo_root=tmp_path)
    assert TestClient(app).get("/assets/headshots/9509.jpg").content == b"cached-photo"


@pytest.mark.parametrize(
    "value", ["relative/headshots", "/nonexistent-dg192-headshots"]
)
def test_invalid_explicit_configuration_refuses_instead_of_silent_old_cache(
    tmp_path, monkeypatch, value
):
    monkeypatch.setenv("DG_HEADSHOT_CACHE_ROOT", value)
    with pytest.raises(HeadshotCacheConfigurationError):
        mount_headshots(FastAPI(), repo_root=tmp_path)


def test_mount_does_not_expose_parent_or_linked_private_files(tmp_path, monkeypatch):
    source = tmp_path / "headshots"
    source.mkdir()
    secret = tmp_path / "private.txt"
    secret.write_text("not-a-photo")
    (source / "9509.jpg").symlink_to(secret)
    monkeypatch.setenv("DG_HEADSHOT_CACHE_ROOT", str(source))
    app = FastAPI()
    mount_headshots(app, repo_root=tmp_path)
    http = TestClient(app)
    assert http.get("/assets/headshots/9509.jpg").status_code == 404
    assert http.get("/assets/headshots/%2e%2e/private.txt").status_code == 404


def test_existing_relative_collection_is_rejected(tmp_path, monkeypatch):
    (tmp_path / "relative/headshots").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DG_HEADSHOT_CACHE_ROOT", "relative/headshots")
    with pytest.raises(HeadshotCacheConfigurationError):
        mount_headshots(FastAPI(), repo_root=tmp_path)
