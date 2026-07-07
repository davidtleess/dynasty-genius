from __future__ import annotations

import importlib
import importlib.util
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def _asset_module():
    spec = importlib.util.find_spec("scripts.build_player_asset_cache")
    assert spec is not None, "Expected scripts.build_player_asset_cache for H2 Increment 0"
    return importlib.import_module("scripts.build_player_asset_cache")


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    content: bytes


def _jpeg_bytes(marker: bytes = b"asset") -> bytes:
    return b"\xff\xd8\xff\xe0" + marker + b"\xff\xd9"


def _player(
    sleeper_player_id: str | None,
    *,
    dg_player_id: str | None = "dg_1",
    team_id: str = "ATL",
) -> dict[str, Any]:
    return {
        "sleeper_player_id": sleeper_player_id,
        "dg_player_id": dg_player_id,
        "full_name": "Bijan Robinson",
        "position": "RB",
        "team_id": team_id,
    }


def test_asset_cache_paths_manifest_schema_and_backup_exclusion_are_pinned() -> None:
    backup_manifest = json.loads(
        (REPO_ROOT / "app" / "config" / "backup_manifest.json").read_text()
    )

    exclusions = {
        item["path"]: item["reason"]
        for item in backup_manifest.get("exclusions", [])
        if isinstance(item, dict)
    }
    assert "app/data/assets/" in exclusions
    assert "rebuildable" in exclusions["app/data/assets/"].lower()

    module = _asset_module()
    assert module.ASSET_CACHE_ROOT == "app/data/assets/headshots"
    assert module.HEADSHOT_MANIFEST_PATH == "app/data/assets/headshot_manifest.json"
    assert module.TEAM_COLORS_PATH == "app/config/team_colors.json"
    assert module.HEADSHOT_MANIFEST_SCHEMA_VERSION == "headshot_manifest.v1"


def test_successful_fetch_writes_sleeper_keyed_cache_and_provenance_manifest(
    tmp_path: Path,
) -> None:
    module = _asset_module()
    cache_root = tmp_path / "headshots"
    manifest_path = tmp_path / "headshot_manifest.json"

    def fetcher(url: str) -> FetchResult:
        assert url.endswith("/1234.jpg")
        assert "sleepercdn.com/content/nfl/players/thumb/" in url
        return FetchResult(status_code=200, content=_jpeg_bytes())

    report = module.build_headshot_cache(
        players=[_player("1234", dg_player_id=None)],
        cache_root=cache_root,
        manifest_path=manifest_path,
        fetcher=fetcher,
        now_utc=lambda: datetime(2026, 7, 6, 16, 0, tzinfo=timezone.utc),
    )

    cached = cache_root / "1234.jpg"
    assert cached.read_bytes() == _jpeg_bytes()
    manifest = json.loads(manifest_path.read_text())
    entry = manifest["entries"]["1234"]
    assert manifest["schema_version"] == "headshot_manifest.v1"
    assert entry == {
        "bytes": len(_jpeg_bytes()),
        "fetched_at": "2026-07-06T16:00:00+00:00",
        "http_status": 200,
        "sha256": module.sha256_bytes(_jpeg_bytes()),
        "source_url": "https://sleepercdn.com/content/nfl/players/thumb/1234.jpg",
        "status": "fresh",
    }
    assert report["fetched_count"] == 1
    assert report["skipped_identity_count"] == 0


def test_fetch_timeout_without_prior_cache_reports_missing_asset_and_does_not_guess(
    tmp_path: Path,
) -> None:
    module = _asset_module()

    def fetcher(_url: str) -> FetchResult:
        raise TimeoutError("offline")

    report = module.build_headshot_cache(
        players=[_player("1234"), _player(None), _player(""), _player("0")],
        cache_root=tmp_path / "headshots",
        manifest_path=tmp_path / "manifest.json",
        fetcher=fetcher,
        now_utc=lambda: datetime(2026, 7, 6, 16, 0, tzinfo=timezone.utc),
    )

    assert not (tmp_path / "headshots" / "1234.jpg").exists()
    assert report["missing_asset_ids"] == ["1234"]
    assert report["skipped_identity_ids"] == [None, "", "0"]
    assert report["stale_served_ids"] == []


def test_fetch_timeout_with_prior_cache_keeps_existing_bytes_and_marks_stale(
    tmp_path: Path,
) -> None:
    module = _asset_module()
    cache_root = tmp_path / "headshots"
    cache_root.mkdir()
    prior = cache_root / "1234.jpg"
    prior.write_bytes(_jpeg_bytes(b"prior"))

    def fetcher(_url: str) -> FetchResult:
        raise TimeoutError("offline")

    report = module.build_headshot_cache(
        players=[_player("1234")],
        cache_root=cache_root,
        manifest_path=tmp_path / "manifest.json",
        fetcher=fetcher,
        now_utc=lambda: datetime(2026, 7, 6, 16, 0, tzinfo=timezone.utc),
    )

    assert prior.read_bytes() == _jpeg_bytes(b"prior")
    assert report["stale_served_ids"] == ["1234"]
    entry = json.loads((tmp_path / "manifest.json").read_text())["entries"]["1234"]
    assert entry["status"] == "refetch_failed"
    assert entry["bytes"] == len(_jpeg_bytes(b"prior"))


def test_corrupt_or_zero_byte_fetch_is_rejected_and_prior_cache_is_not_deleted(
    tmp_path: Path,
) -> None:
    module = _asset_module()
    cache_root = tmp_path / "headshots"
    cache_root.mkdir()
    prior = cache_root / "5678.jpg"
    prior.write_bytes(_jpeg_bytes(b"keep"))
    responses = {
        "1234": FetchResult(status_code=200, content=b""),
        "5678": FetchResult(status_code=200, content=b"not-an-image"),
    }

    def fetcher(url: str) -> FetchResult:
        sleeper_id = Path(url).stem
        return responses[sleeper_id]

    report = module.build_headshot_cache(
        players=[_player("1234"), _player("5678")],
        cache_root=cache_root,
        manifest_path=tmp_path / "manifest.json",
        fetcher=fetcher,
        now_utc=lambda: datetime(2026, 7, 6, 16, 0, tzinfo=timezone.utc),
    )

    assert not (cache_root / "1234.jpg").exists()
    assert prior.read_bytes() == _jpeg_bytes(b"keep")
    assert report["invalid_image_ids"] == ["1234", "5678"]


def test_cache_build_preserves_assets_not_in_current_input_without_delete_flag(
    tmp_path: Path,
) -> None:
    module = _asset_module()
    cache_root = tmp_path / "headshots"
    cache_root.mkdir()
    orphan = cache_root / "9999.jpg"
    orphan.write_bytes(_jpeg_bytes(b"orphan"))

    module.build_headshot_cache(
        players=[],
        cache_root=cache_root,
        manifest_path=tmp_path / "manifest.json",
        fetcher=lambda _url: FetchResult(status_code=404, content=b""),
        now_utc=lambda: datetime(2026, 7, 6, 16, 0, tzinfo=timezone.utc),
    )

    assert orphan.read_bytes() == _jpeg_bytes(b"orphan")


def test_team_color_map_is_checked_in_identity_only_and_contrast_resolvable() -> None:
    team_colors_path = REPO_ROOT / "app" / "config" / "team_colors.json"
    payload = json.loads(team_colors_path.read_text())

    assert payload["schema_version"] == "team_colors.v1"
    assert len(payload["teams"]) == 32
    for team_id, colors in payload["teams"].items():
        assert set(colors) == {"primary", "secondary"}
        assert colors["primary"].startswith("oklch("), team_id
        assert colors["secondary"].startswith("oklch("), team_id

    frontend_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "frontend" / "src").rglob("*.*")
        if path.suffix in {".css", ".tsx", ".ts", ".jsx", ".js"}
    )
    assert "team_colors.json" not in frontend_sources
    assert "background: var(--dg-team" not in frontend_sources
    assert "status-color-from-team" not in frontend_sources
