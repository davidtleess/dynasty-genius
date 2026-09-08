"""Fill a private cache with the real photo of every workspace player (DG-193, 2026-09-08).

David asked for headshots for all players. The only way to fail him badly here is to satisfy that request with the
wrong face, so identity is exact everywhere: a photo is fetched only from that player's OWN Sleeper id, or from the
ESPN id carried on his own Sleeper record. Nothing is matched by name or guessed from position.

What comes back is checked before it is kept. Bytes must carry a real image magic AND survive a real decode, because
a 404 page and a one-pixel tracker both arrive with HTTP 200 and would otherwise be filed as somebody's face. If the
decoder is unavailable the run refuses rather than accepting what it cannot check.

A player with no photo is not an error. He is reported by name with a reason, keeps the initials fallback on screen,
and the run still exits zero — missing coverage is a fact to hand back, not something to bury.

Three facts inherited from the legacy builder's real runs and from root's probe of the live CDN, so nobody has to
rediscover them:

* Sleeper serves **PNG bytes under `.jpg` URLs**. Validation is by magic, and the original bytes are written
  unchanged; the filename stays `<id>.jpg` because that is the URL contract the frontend already uses.
* macOS system Python ships **no CA bundle** — the first real run failed all 272 fetches on certificate
  verification, so TLS is verified against `certifi`.
* An unknown id answers **403, not 404**. Any 4xx therefore means "absent": it is reported and never retried. Only a
  5xx or a connection failure is transient, and even then exactly once.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import urlsplit

SCHEMA_VERSION = "workspace_headshots.v1"

SLEEPER_THUMB_URL = "https://sleepercdn.com/content/nfl/players/thumb/{sleeper_id}.jpg"
SLEEPER_FULL_URL = "https://sleepercdn.com/content/nfl/players/{sleeper_id}.jpg"
ESPN_HEADSHOT_URL = "https://a.espncdn.com/i/headshots/nfl/players/full/{espn_id}.png"
#: The same ESPN id, under ESPN's college-football tree. Measured live on 2026-09-08: Sal Cannella's id 4242536
#: gives 404 on the nfl path and 200 on this one. A player who never established an NFL headshot there can still
#: have his college portrait under the very same identifier, so this is a second PATH for one id, never a second id.
ESPN_COLLEGE_HEADSHOT_URL = (
    "https://a.espncdn.com/i/headshots/college-football/players/full/{espn_id}.png"
)
#: The approved hosts a verified direct headshot URL may name. Anything else — a lookalike, an unapproved CDN, plain HTTP —
#: is refused, because a URL supplied in a map is exactly where a wrong face would enter.
NFL_HEADSHOT_HOST = "static.www.nfl.com"
OFFICIAL_HEADSHOT_HOSTS = {NFL_HEADSHOT_HOST, "fordhamsports.com"}

#: The legacy builder's rule, unchanged: anything else is an identity defect, never a URL and never a path.
SLEEPER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
#: `RIFF` alone also matches WAV, so WebP needs its fourcc too.
IMAGE_MAGICS = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_CONCURRENCY = 4
REQUEST_TIMEOUT_SECONDS = 20
MIN_IMAGE_PIXELS = 16
SIPS_PATH = Path("/usr/bin/sips")
SYSTEM_ALIASES = {"/tmp": "/private/tmp", "/var": "/private/var"}
SHARED_STORE_PARTS = (("app", "data"), ("app", "cache"))
NO_PHOTO = "no photo found at any source for this identifier"


class HeadshotBuildError(RuntimeError):
    """The run cannot proceed honestly. Missing photos are NOT this — they are reported and the run succeeds."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def has_image_magic(payload: bytes) -> bool:
    if payload.startswith(IMAGE_MAGICS):
        return True
    return payload.startswith(b"RIFF") and payload[8:12] == b"WEBP"


def sips_validator(*, sips_path: Path = SIPS_PATH) -> Callable[[bytes], bool]:
    """A validator that really decodes. Refuses to exist when the decoder does not.

    Magic bytes prove a header, not a picture: a 1×1 tracking pixel and a truncated file both pass them. So the
    bytes are handed to the system decoder and must come back with real dimensions. Without that decoder we would be
    claiming a check we did not perform, which is worse than stopping.
    """
    if not Path(sips_path).exists():
        raise HeadshotBuildError(
            f"the image decoder {sips_path} is unavailable, so a fetched file cannot be verified as a real image; "
            f"refusing rather than accepting bytes on their magic alone"
        )

    def validate(payload: bytes) -> bool:
        if not has_image_magic(payload):
            return False
        with tempfile.NamedTemporaryFile(suffix=".img") as handle:
            handle.write(payload)
            handle.flush()
            probe = subprocess.run(
                [str(sips_path), "-g", "pixelWidth", "-g", "pixelHeight", handle.name],
                capture_output=True, text=True, check=False,
            )
        if probe.returncode != 0:
            return False
        sizes = [int(part.split(":")[1]) for part in probe.stdout.splitlines() if "pixel" in part]
        return len(sizes) == 2 and all(size >= MIN_IMAGE_PIXELS for size in sizes)

    return validate


# --- where the output may go -------------------------------------------------------------------------


def _prepared_output(output_dir: Path | str) -> Path:
    """A new, absolute, real directory. Never an existing one, never through a link, never a shared store."""
    path = Path(output_dir)
    if not path.is_absolute():
        raise HeadshotBuildError(f"the output directory {path} must be an absolute path")
    if path.is_symlink():
        raise HeadshotBuildError(
            f"the output directory {path} is a symlink; a link writes somewhere else, and a dangling one passes an "
            f"existence check while still doing so"
        )
    if path.exists():
        raise HeadshotBuildError(
            f"the output directory {path} already exists; each run writes a new directory so one can never "
            f"overwrite another's evidence"
        )
    for candidate in path.parents:
        if not candidate.is_symlink():
            continue
        if SYSTEM_ALIASES.get(str(candidate)) == str(candidate.resolve()):
            continue
        raise HeadshotBuildError(
            f"the output path crosses the symlink {candidate}; a link here silently writes somewhere else"
        )
    parts = path.resolve().parts
    for shared in SHARED_STORE_PARTS:
        for index in range(len(parts) - len(shared) + 1):
            if tuple(parts[index : index + len(shared)]) == shared:
                raise HeadshotBuildError(
                    f"the output directory {path} resolves inside the shared {'/'.join(shared)} store; this builder "
                    f"never writes there"
                )
    return path


# --- the population -----------------------------------------------------------------------------------


def _validated_population(players: Iterable[dict]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_id: dict[str, str] = {}
    for player in players:
        if not isinstance(player, dict):
            raise HeadshotBuildError(f"the population contains {player!r}, which is not a player row")
        identifier = player.get("sleeper_player_id")
        name = player.get("name")
        if not _is_safe_id(identifier):
            raise HeadshotBuildError(
                f"the population carries the unsafe sleeper identifier {identifier!r} for {name!r}; a malformed "
                f"population is a defect in the input, not a player without a photo"
            )
        if identifier in by_id:
            if by_id[identifier] == name:
                raise HeadshotBuildError(f"the population lists {identifier} ({name}) twice; a duplicate row")
            raise HeadshotBuildError(
                f"the population gives {identifier} two names, {by_id[identifier]!r} and {name!r}; refusing rather "
                f"than choosing which face belongs to that identifier"
            )
        by_id[identifier] = name
        rows.append(
            {"sleeper_id": identifier, "name": name, "position": player.get("position")}
        )
    return rows


def _validated_official_url(url: Any, identifier: str) -> str:
    """A direct headshot URL uses an explicitly approved official host over ordinary HTTPS.

    Credentials, an explicit port and a fragment are all refused too: each is a way to make a string that reads like
    the allowed host while fetching from somewhere else.
    """
    if not isinstance(url, str) or not url:
        raise HeadshotBuildError(f"{identifier}: headshot_url is {url!r}, not a URL")
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise HeadshotBuildError(f"{identifier}: headshot_url must be https, not {parts.scheme!r}")
    if (parts.hostname or "").lower() not in OFFICIAL_HEADSHOT_HOSTS:
        raise HeadshotBuildError(
            f"{identifier}: headshot_url names {parts.hostname!r}; only approved official headshot hosts are allowed"
        )
    if parts.username or parts.password:
        raise HeadshotBuildError(f"{identifier}: headshot_url carries credentials")
    if parts.port is not None:
        raise HeadshotBuildError(f"{identifier}: headshot_url names an explicit port")
    if parts.fragment:
        raise HeadshotBuildError(f"{identifier}: headshot_url carries a fragment")
    return url


def _validated_verified(verified: Any, known: set[str]) -> dict[str, dict]:
    """The audited exact-id map: keyed only by a target Sleeper id, and every entry says where it came from."""
    if verified is None:
        return {}
    if not isinstance(verified, dict):
        raise HeadshotBuildError("the verified identities map is not a mapping of sleeper id to record")
    unknown = [key for key in verified if key not in known]
    if unknown:
        raise HeadshotBuildError(
            f"the verified identities map is not keyed by a target sleeper id: {', '.join(sorted(unknown)[:3])} "
            f"matches no player in this population"
        )
    for identifier, entry in verified.items():
        if not isinstance(entry, dict):
            raise HeadshotBuildError(f"{identifier}: the verified entry is not a record")
        provenance = entry.get("provenance")
        if not isinstance(provenance, dict) or not provenance.get("source") or not provenance.get("sha256"):
            raise HeadshotBuildError(
                f"{identifier}: the verified entry states no provenance (source and sha256); an exact-id claim with "
                f"no stated origin is how a wrong face gets in"
            )
        if entry.get("headshot_url") is not None:
            _validated_official_url(entry["headshot_url"], identifier)
        espn_id = entry.get("espn_id")
        if espn_id is not None and not (isinstance(espn_id, str) and SLEEPER_ID_PATTERN.fullmatch(espn_id)):
            raise HeadshotBuildError(f"{identifier}: the verified espn_id {espn_id!r} is not a plain identifier")
    return verified


def _is_safe_id(identifier: Any) -> bool:
    return (
        isinstance(identifier, str)
        and identifier not in ("", "0")
        and SLEEPER_ID_PATTERN.fullmatch(identifier) is not None
    )


def _validated_identities(identities: Any, known: set[str]) -> dict[str, dict]:
    if identities is None:
        return {}
    if not isinstance(identities, dict):
        raise HeadshotBuildError("the identities map is not a mapping of sleeper id to player record")
    unknown = [key for key in identities if key not in known]
    if unknown:
        raise HeadshotBuildError(
            f"the identities map is not keyed by sleeper id: {', '.join(sorted(unknown)[:3])} matches no player in "
            f"this population. A name-keyed map would put one player's photo under another's id."
        )
    return identities


# --- fetching one player ---------------------------------------------------------------------------------


def _sources(identifier: str, identities: dict[str, dict], verified: dict[str, dict]) -> list[tuple[str, str]]:
    """Sleeper first, then the audited direct NFL URL, then the exact ESPN id. Every entry is keyed on THIS
    player's own id; no list here can be reached by a name."""
    sources = [
        ("sleeper_thumb", SLEEPER_THUMB_URL.format(sleeper_id=identifier)),
        ("sleeper_full", SLEEPER_FULL_URL.format(sleeper_id=identifier)),
    ]
    record = verified.get(identifier) or {}
    if record.get("headshot_url"):
        source = "nfl_verified" if urlsplit(record["headshot_url"]).hostname == NFL_HEADSHOT_HOST else "college_verified"
        sources.append((source, record["headshot_url"]))
    espn_id = record.get("espn_id") or (identities.get(identifier) or {}).get("espn_id")
    if isinstance(espn_id, str) and espn_id.strip() and SLEEPER_ID_PATTERN.fullmatch(espn_id):
        sources.append(("espn", ESPN_HEADSHOT_URL.format(espn_id=espn_id)))
        sources.append(("espn_college", ESPN_COLLEGE_HEADSHOT_URL.format(espn_id=espn_id)))
    return sources


def _attempt(fetcher, validator, source: str, url: str) -> dict[str, Any]:
    """One request, with one retry for a transient failure only."""
    record: dict[str, Any] = {
        "source": source, "url": url, "http_status": None, "bytes": 0, "sha256": None,
        "outcome": "error", "detail": None,
    }
    for remaining in (1, 0):
        try:
            result = fetcher(url)
            status = int(result.status_code)
            content = bytes(result.content)
        except Exception as exc:  # a connection problem is transient; the message is kept for the report
            record["outcome"], record["detail"] = "error", f"{type(exc).__name__}: {exc}"
            if remaining:
                continue
            return record
        record["http_status"] = status
        if 400 <= status < 500:
            # 403 and 404 both mean "there is no photo here". Asking again would be noise on somebody else's CDN.
            record["outcome"] = "not_found"
            return record
        if status != 200:
            record["outcome"], record["detail"] = "http_error", f"HTTP {status}"
            if remaining:
                continue
            return record
        if len(content) > MAX_IMAGE_BYTES:
            record["outcome"] = "too_large"
            record["bytes"] = len(content)
            return record
        record["bytes"] = len(content)
        record["sha256"] = sha256_bytes(content)
        if not validator(content):
            record["outcome"] = "invalid_image"
            return record
        record["outcome"] = "image"
        record["content"] = content
        return record
    return record


def _collect_one(
    player: dict, *, fetcher, validator, identities, verified, seed_cache: Path | None
) -> dict[str, Any]:
    identifier = player["sleeper_id"]
    outcome: dict[str, Any] = {
        **player, "status": "missing", "source": None, "sha256": None, "bytes": 0, "attempts": [],
        "missing_reason": NO_PHOTO, "content": None,
        "identity_provenance": (verified.get(identifier) or {}).get("provenance"),
    }

    if seed_cache is not None:
        candidate = Path(seed_cache) / f"{identifier}.jpg"       # that exact id, never a neighbour's file
        if candidate.is_file() and not candidate.is_symlink():
            payload = candidate.read_bytes()
            if len(payload) <= MAX_IMAGE_BYTES and validator(payload):
                outcome.update(
                    status="available", source="seed", sha256=sha256_bytes(payload),
                    bytes=len(payload), content=payload, missing_reason=None,
                )
                return outcome

    for source, url in _sources(identifier, identities, verified):
        record = _attempt(fetcher, validator, source, url)
        content = record.pop("content", None)
        outcome["attempts"].append(record)
        if content is not None:
            outcome.update(
                status="available", source=source, sha256=record["sha256"],
                bytes=record["bytes"], content=content, missing_reason=None,
            )
            return outcome
    return outcome


# --- the run ------------------------------------------------------------------------------------------------


def build_workspace_headshots(
    *,
    players: Iterable[dict],
    output_dir: Path | str,
    fetcher: Callable[[str], Any],
    validator: Callable[[bytes], bool],
    seed_cache: Path | str | None = None,
    identities: dict | None = None,
    verified_identities: dict | None = None,
    now_utc: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    rows = _validated_population(players)
    known = {row["sleeper_id"] for row in rows if isinstance(row["sleeper_id"], str)}
    if identities is not None and verified_identities is not None:
        raise HeadshotBuildError(
            "--identities-json and --verified-identities-json may not be supplied together; one run uses one map"
        )
    identity_map = _validated_identities(identities, known)
    verified_map = _validated_verified(verified_identities, known)
    destination = _prepared_output(output_dir)

    if seed_cache is not None:
        seed_cache = Path(seed_cache)
        if not seed_cache.is_dir():
            raise HeadshotBuildError(f"the seed cache {seed_cache} is not a directory")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
        collected = list(
            pool.map(
                lambda row: _collect_one(
                    row, fetcher=fetcher, validator=validator,
                    identities=identity_map, verified=verified_map, seed_cache=seed_cache,
                ),
                rows,
            )
        )

    images = destination / "headshots"
    images.mkdir(parents=True)
    by_hash: dict[str, list[str]] = {}
    entries: list[dict[str, Any]] = []
    for player in collected:
        content = player.pop("content")
        if content is not None:
            (images / f"{player['sleeper_id']}.jpg").write_bytes(content)
            by_hash.setdefault(player["sha256"], []).append(player["sleeper_id"])
        entries.append(player)

    available = [row for row in entries if row["status"] == "available"]
    missing = [
        {"sleeper_id": row["sleeper_id"], "name": row["name"], "position": row["position"],
         "reason": row["missing_reason"]}
        for row in entries if row["status"] == "missing"
    ]
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_utc().isoformat(),
        "counts": {
            "total": len(entries),
            "available": len(available),
            "missing": len(missing),
            "from_seed": sum(1 for row in available if row["source"] == "seed"),
            "fetched": sum(1 for row in available if row["source"] != "seed"),
        },
        "players": entries,
        "missing": missing,
        # Several players sharing one image is how a CDN placeholder passes as coverage. Grouping them is the only
        # way root can see it, because every one of those files decodes perfectly.
        "duplicate_content": [
            {"sha256": digest, "sleeper_ids": sorted(ids)}
            for digest, ids in sorted(by_hash.items()) if len(ids) > 1
        ],
    }
    (destination / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main(argv: Sequence[str] | None = None, *, fetcher=None, validator=None) -> int:
    parser = argparse.ArgumentParser(prog="build_workspace_headshots", description=__doc__)
    parser.add_argument("--players-json", type=Path, required=True, help="the workspace population to cover")
    parser.add_argument(
        "--output-dir", type=Path, required=True,
        help="a new absolute run-scoped directory; there is deliberately no default",
    )
    parser.add_argument("--seed-cache", type=Path, default=None, help="an existing cache to reuse, read only")
    parser.add_argument(
        "--identities-json", type=Path, default=None,
        help="a Sleeper player map keyed by sleeper id, used only for that player's own espn_id",
    )
    parser.add_argument(
        "--verified-identities-json", type=Path, default=None,
        help="an audited map keyed by target sleeper id carrying espn_id, headshot_url and provenance",
    )
    options = parser.parse_args(argv)

    try:
        if validator is None:
            validator = sips_validator()
        if fetcher is None:
            fetcher = _certifi_fetcher()
        players = json.loads(options.players_json.read_text())
        identities = (
            json.loads(options.identities_json.read_text()) if options.identities_json is not None else None
        )
        verified = (
            json.loads(options.verified_identities_json.read_text())
            if options.verified_identities_json is not None else None
        )
        report = build_workspace_headshots(
            players=players, output_dir=options.output_dir, fetcher=fetcher, validator=validator,
            seed_cache=options.seed_cache, identities=identities, verified_identities=verified,
        )
    except HeadshotBuildError as exc:
        print(f"refusing to build the headshot cache: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"could not read the inputs: {exc}", file=sys.stderr)
        return 1

    # Missing photos are reported, not an error: root decides what recovery is worth doing.
    print(json.dumps({key: report[key] for key in ("counts", "missing", "duplicate_content")}, indent=2))
    return 0


def _certifi_fetcher() -> Callable[[str], Any]:
    import ssl
    import urllib.request

    import certifi

    class HttpResult:
        def __init__(self, status_code: int, content: bytes) -> None:
            self.status_code = status_code
            self.content = content

    # macOS system Python has no CA bundle; without this every fetch fails certificate verification.
    context = ssl.create_default_context(cafile=certifi.where())

    def fetch(url: str) -> HttpResult:
        request = urllib.request.Request(url, headers={"User-Agent": "dynasty-genius-headshots/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS, context=context) as response:  # noqa: S310
                return HttpResult(response.status, response.read(MAX_IMAGE_BYTES + 1))
        except urllib.error.HTTPError as exc:                     # 403/404 are answers, not failures
            return HttpResult(exc.code, b"")

    return fetch


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
