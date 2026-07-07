"""H2 Increment 0 — governed player asset cache (rethink v3 / Increment-0 spec v2).

Mirrors Sleeper CDN headshots into a gitignored local store keyed by
``sleeper_player_id`` (the asset source's own key; ``dg_player_id`` is nullable
today — the identity layer owns the dg→sleeper mapping and this script never
invents identity). Fetch-time mirroring only: the app never hotlinks at render
time.

Fail-closed contracts (spec §3 + seeds 1–6):
- missing/blank/zero sleeper id → skipped and counted, never guessed;
- fetch failure with NO prior cache → reported missing, nothing written;
- fetch failure WITH prior cache → existing bytes preserved and served,
  manifest entry marked ``refetch_failed``;
- zero-byte or non-JPEG payload → rejected (``invalid_image_ids``), prior
  cache never deleted;
- assets absent from the current input are preserved (no deletes without an
  explicit flag — none exists yet by design).

The backup manifest carries an exclusions entry for ``app/data/assets/``:
this store is rebuildable from public sources and is NOT irreplaceable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ASSET_CACHE_ROOT = "app/data/assets/headshots"
HEADSHOT_MANIFEST_PATH = "app/data/assets/headshot_manifest.json"
TEAM_COLORS_PATH = "app/config/team_colors.json"
HEADSHOT_MANIFEST_SCHEMA_VERSION = "headshot_manifest.v1"

# Cache keys are Sleeper ids: opaque alphanumeric tokens. Anything else —
# wrong type, traversal characters, separators — is an identity defect and is
# skipped+reported, never written (Codex GREEN-review F1/F2: '../escape' must
# not escape cache_root; a non-string id must not crash the manifest write).
_SLEEPER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _is_cacheable_sleeper_id(sleeper_id: Any) -> bool:
    return (
        isinstance(sleeper_id, str)
        and sleeper_id not in ("", "0")
        and _SLEEPER_ID_PATTERN.fullmatch(sleeper_id) is not None
    )

_SLEEPER_HEADSHOT_URL = "https://sleepercdn.com/content/nfl/players/thumb/{sleeper_id}.jpg"
# Real-shape fact (first live run, 2026-07-06): Sleeper serves PNG bytes under
# .jpg URLs. Validate against the real image magics, not the URL extension.
_IMAGE_MAGICS = (
    b"\xff\xd8\xff",  # JPEG
    b"\x89PNG\r\n\x1a\n",  # PNG
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_valid_image(payload: bytes) -> bool:
    if len(payload) == 0:
        return False
    if payload.startswith(_IMAGE_MAGICS):
        return True
    # WebP is a RIFF container — the RIFF magic alone also matches WAV etc.
    # (Codex probe: RIFF....WAVE was accepted); require the WEBP fourcc.
    return payload.startswith(b"RIFF") and payload[8:12] == b"WEBP"


def build_headshot_cache(
    *,
    players: list[dict[str, Any]],
    cache_root: Path,
    manifest_path: Path,
    fetcher: Callable[[str], Any],
    now_utc: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    cache_root.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    entries: dict[str, Any] = {}
    fetched_count = 0
    skipped_identity_ids: list[Any] = []
    missing_asset_ids: list[str] = []
    stale_served_ids: list[str] = []
    invalid_image_ids: list[str] = []

    for player in players:
        sleeper_id = player.get("sleeper_player_id")
        if not _is_cacheable_sleeper_id(sleeper_id):
            skipped_identity_ids.append(sleeper_id)
            continue

        source_url = _SLEEPER_HEADSHOT_URL.format(sleeper_id=sleeper_id)
        cached_file = cache_root / f"{sleeper_id}.jpg"

        try:
            result = fetcher(source_url)
            status_code = int(result.status_code)
            content = bytes(result.content)
            fetch_failed = status_code != 200
        except Exception:
            status_code = None
            content = b""
            fetch_failed = True

        if fetch_failed:
            if cached_file.exists():
                prior = cached_file.read_bytes()
                stale_served_ids.append(sleeper_id)
                entries[sleeper_id] = {
                    "bytes": len(prior),
                    "fetched_at": now_utc().isoformat(),
                    "http_status": status_code,
                    "sha256": sha256_bytes(prior),
                    "source_url": source_url,
                    "status": "refetch_failed",
                }
            else:
                missing_asset_ids.append(sleeper_id)
            continue

        if not _is_valid_image(content):
            invalid_image_ids.append(sleeper_id)
            continue

        cached_file.write_bytes(content)
        fetched_count += 1
        entries[sleeper_id] = {
            "bytes": len(content),
            "fetched_at": now_utc().isoformat(),
            "http_status": status_code,
            "sha256": sha256_bytes(content),
            "source_url": source_url,
            "status": "fresh",
        }

    manifest = {
        "schema_version": HEADSHOT_MANIFEST_SCHEMA_VERSION,
        "generated_at": now_utc().isoformat(),
        "entries": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    return {
        "fetched_count": fetched_count,
        "skipped_identity_count": len(skipped_identity_ids),
        "skipped_identity_ids": skipped_identity_ids,
        "missing_asset_ids": missing_asset_ids,
        "stale_served_ids": stale_served_ids,
        "invalid_image_ids": invalid_image_ids,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--players-json",
        required=True,
        help="Path to a JSON list of player rows carrying sleeper_player_id.",
    )
    args = parser.parse_args(argv)

    import ssl
    import urllib.request

    import certifi

    class _HttpResult:
        def __init__(self, status_code: int, content: bytes) -> None:
            self.status_code = status_code
            self.content = content

    # macOS system Python ships no CA bundle — verify against certifi's
    # (first real run failed all 272 fetches on CERTIFICATE_VERIFY_FAILED).
    _ssl_context = ssl.create_default_context(cafile=certifi.where())

    def _fetch(url: str) -> _HttpResult:
        with urllib.request.urlopen(  # noqa: S310
            url, timeout=20, context=_ssl_context
        ) as response:
            return _HttpResult(response.status, response.read())

    players = json.loads(Path(args.players_json).read_text())
    report = build_headshot_cache(
        players=players,
        cache_root=Path(ASSET_CACHE_ROOT),
        manifest_path=Path(HEADSHOT_MANIFEST_PATH),
        fetcher=_fetch,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
