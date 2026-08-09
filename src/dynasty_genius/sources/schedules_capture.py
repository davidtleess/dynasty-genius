"""B21 `schedules` — source-first capture of the nflverse global schedule offering.

GREEN for `tests/contract/test_b21_schedules_capture_red.py`, CLEARed at pin
`38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86`.

THE SOURCE, AS MEASURED RATHER THAN ASSUMED. nflverse publishes ONE global Parquet asset covering
every season (`nflreadpy/load_schedules.py:30` -> `downloader.py:38-48`, which filters seasons in
memory afterwards). So the offering, the check and the content vintage are global, and a
`(season, week)` view is a PROJECTION of one retained vintage — never a fetch parameter.

The installed client cannot serve as our transport: `downloader._download_file` returns a parsed
frame and never surfaces the response body, so a route built on it holds no raw bytes and can prove
nothing about what the provider sent. This module fetches the same asset itself and hashes the bytes
before interpreting them.

WHAT THIS ROUTE REFUSES TO CLAIM. The feed carries no terminal-status field and no end-time, and may
publish interim scores. A populated score proves play was OBSERVED, never that play ENDED. So the
descriptor declares `finality_capability="unverified"`, every score the provider publishes is
retained, and NO derived status field is ever emitted. `scripts/run_realized_outcome_scoring.py:345`
infers `"final"` from a populated score; this module deliberately does not, and nothing here should
be wired into that inference without its own governed terminal evidence.

RETENTION NOTE. A no-change check is common (the asset is republished frequently) and the payload is
megabytes. Raw bytes are therefore stored ONCE per content hash under `content/`, with each check's
`raw/<check_id>.parquet` a hard link to it. Every check keeps its own addressable raw path — the
bytes behind identical checks are simply not duplicated.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[3]

#: The exact asset the installed client resolves, assembled the same way `_build_url` does.
NFLVERSE_SCHEDULES_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet"
)

DEFAULT_ROOT = REPO_ROOT / "app" / "data" / "sources" / "nflverse_schedules"

#: Bumped whenever the parse or validation semantics change, so a stored vintage can always say
#: which rules produced it.
PARSER_VERSION = "b21.schedules.v1"

#: Columns this repo consumes by name. A REQUIRED SUBSET — every other provider column is retained
#: losslessly; these are the ones whose absence is fatal rather than merely lossy.
REQUIRED_COLUMNS = (
    "game_id", "season", "week", "game_type", "gameday", "gametime",
    "away_team", "home_team", "away_score", "home_score",
)

_INTEGER_FIELDS = ("season", "week")
_NON_EMPTY_TEXT_FIELDS = ("game_id", "away_team", "home_team")
_SCORE_FIELDS = ("away_score", "home_score")

#: Strict 24-hour wall clock. Measured at immutable upstream `793d10a9…`: 7,289 of 7,289 non-empty
#: `gametime` values take this form and zero take any other, so a wider rule would admit a provider
#: drift that has never occurred.
_HH_MM = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

#: Identifiers become path segments, so they are constrained before they are ever joined to a root.
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_BOUNDARIES = ("raw", "store", "index", "marker")


class CaptureError(RuntimeError):
    """A refusal to accept an offering. `code` is stable and is what callers branch on."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        #: The message WITHOUT the code prefix, so re-wrapping (e.g. sanitizing a transport failure)
        #: does not stutter the code — `str(exc)` already leads with it.
        self.detail = message


class FetchError(CaptureError):
    """The provider could not be reached, or refused. Distinct from a bad payload."""


class PublishError(RuntimeError):
    """A storage boundary failed mid-publication. Everything this attempt wrote is rolled back."""

    def __init__(self, boundary: str, message: str = "") -> None:
        super().__init__(f"{boundary}: {message}" if message else boundary)
        self.boundary = boundary


# ── transport ────────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FetchResult:
    """What came back, and from where — BOTH ends of the delivery, never collapsed into one.

    `requested_url` is what we asked for; `final_url` is what actually served the bytes. They differ
    on every normal retrieval, because GitHub answers a release URL with a 302 to a signed asset, and
    provenance that keeps only one of them cannot answer "where did this really come from?".
    """

    requested_url: str
    final_url: str
    body: bytes
    retrieved_at: str


#: The provider's own delivery domains. `github.com` issues the release URL and
#: `release-assets.githubusercontent.com` served the signed asset when this was measured
#: (2026-08-09). Matching is DOT-ANCHORED: a bare `endswith("githubusercontent.com")` would accept
#: `…githubusercontent.com.evil.example`, which is how an allowlist stops meaning anything.
_SANCTIONED_HOSTS = ("github.com", "githubusercontent.com")


#: Any URL appearing inside free text. Scrubbing at the point every failure is WRITTEN — rather than
#: at each call site that happens to build a message today — is the difference between a rule and a
#: habit: a transport exception embeds the URL it failed on, and that URL is the signed one.
_URL_IN_TEXT = re.compile(r"https?://[^\s'\"]+")


def _scrub(text: str) -> str:
    """Reduce every URL in free-form text to the SAME non-secret form `_sanitize_url` produces.

    This delegates rather than pattern-matching its own way to an answer, because it already got that
    wrong once: the first cut stripped everything after `?` or `#` and left `user:password@host`
    untouched — so this module could claim userinfo was handled (true of `_sanitize_url`) while the
    error-text path leaked it. One policy, two entry points, and the entry points must not disagree.
    """

    def _redact(match: re.Match[str]) -> str:
        url = match.group(0)
        base = _sanitize_url(url)
        # Say that something was removed, without saying what.
        return f"{base}?<redacted>" if ("?" in url or "#" in url) else base

    return _URL_IN_TEXT.sub(_redact, text)


def _sanitize_url(url: str) -> str:
    """Scheme, host and path — never the query or fragment.

    GitHub's signed release asset carries signature and JWT parameters in its query string. Recording
    the delivery URL verbatim wrote SHORT-LIVED CREDENTIALS into the vintage, the marker and the
    ledger on the very first successful production run — and this store is a REQUIRED entry in the
    backup manifest, so the next daily run would have shipped them offsite.

    Provenance answers "which host served which path". It has never needed the query string, and the
    failure path is sanitized too: a refusal names the URL it refused, and a foreign host's URL is
    exactly the one most likely to carry credential material.
    """
    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    if parts.port:
        host = f"{host}:{parts.port}"
    return f"{parts.scheme}://{host}{parts.path}" if host else parts.scheme + "://"


def _delivery_host_is_sanctioned(url: str) -> bool:
    parts = urlparse(url)
    if parts.scheme != "https":
        return False
    host = (parts.hostname or "").lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in _SANCTIONED_HOSTS)


class HttpFetcher:
    """The production transport. Deliberately tiny: it retrieves bytes and reports where they came
    from. It does not parse, cache, or interpret — every judgement about the payload belongs to the
    store, which can be exercised offline."""

    def __init__(self, timeout: int = 60) -> None:
        self.timeout = timeout

    def fetch(self, url: str) -> FetchResult:
        import requests  # imported lazily so the module stays importable without the network stack

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - any transport failure is one failed check
            raise FetchError("fetch_failed", f"{type(exc).__name__}: {exc}") from exc
        return FetchResult(
            requested_url=url,
            final_url=response.url or url,
            body=response.content,
            retrieved_at=datetime.now().astimezone().isoformat(),
        )


class RecordingFetcher:
    """A transport collaborator for contracts and dry runs: it serves prepared bodies, records every
    URL it was asked for, and can simulate a transport failure, a sanctioned redirect, or a foreign
    substitution."""

    def __init__(self, bodies: list[bytes], retrieved_at: str,
                 error: str | None = None, final_url: str | None = None) -> None:
        self.bodies = list(bodies)
        self.retrieved_at = retrieved_at
        self.error = error
        self.final_url = final_url
        self.calls: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.calls.append(url)
        if self.error is not None:
            raise FetchError("fetch_failed", self.error)
        if not self.bodies:
            raise FetchError("fetch_failed", "no body prepared")
        return FetchResult(requested_url=url, final_url=self.final_url or url,
                           body=self.bodies.pop(0), retrieved_at=self.retrieved_at)


def default_fetcher() -> HttpFetcher:
    """Looked up through the module at call time so a caller can substitute a transport without the
    CLI knowing anything about it."""
    return HttpFetcher()


# ── storage boundaries ───────────────────────────────────────────────────────────────────────────


class FilesystemStorage:
    """Every write the route performs, named by boundary. Publication is atomic per file (write a
    temp beside the target, then `os.replace`), and the caller rolls back the set on any failure."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    # -- helpers ---------------------------------------------------------------------------------

    def _atomic_write(self, path: Path, data: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        try:
            tmp.write_bytes(data)
            os.replace(tmp, path)
        except BaseException:
            # Our own half-finished write is ours to clean up. The rollback sweep below is the
            # backstop for a temp file some other failure left behind.
            tmp.unlink(missing_ok=True)
            raise
        return path

    def read_json(self, path: Path, default: Any = None) -> Any:
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    # -- boundaries ------------------------------------------------------------------------------

    def write_raw(self, content_path: Path, link_path: Path, data: bytes,
                  expected_sha256: str) -> list[Path]:
        """Content-addressed body plus this check's own addressable link.

        AN EXISTING OBJECT IS VERIFIED, NEVER TRUSTED. The path is a CLAIM about the bytes behind it,
        and a claim from a filename is not evidence: a crash mid-write, a truncated copy or a restore
        of the wrong file all leave a plausible object at the right address. Reusing one unchecked
        published a marker asserting the incoming hash over bytes that were something else entirely —
        silent corruption of the evidence itself, which is the worst failure this route can have.
        """
        created: list[Path] = []
        if content_path.is_file():
            _verify_object(content_path, data, expected_sha256)
        else:
            self._atomic_write(content_path, data)
            created.append(content_path)
        link_path.parent.mkdir(parents=True, exist_ok=True)
        if link_path.exists():
            _verify_object(link_path, data, expected_sha256)
        else:
            try:
                os.link(content_path, link_path)
            except OSError:
                shutil.copyfile(content_path, link_path)
            created.append(link_path)
        return created

    def write_vintage(self, path: Path, payload: dict) -> list[Path]:
        existed = path.is_file()
        self._atomic_write(path, _dumps(payload))
        return [] if existed else [path]

    def write_index(self, path: Path, payload: dict) -> list[Path]:
        existed = path.is_file()
        self._atomic_write(path, _dumps(payload))
        return [] if existed else [path]

    def write_marker(self, path: Path, payload: dict) -> list[Path]:
        existed = path.is_file()
        self._atomic_write(path, _dumps(payload))
        return [] if existed else [path]

    def append_audit(self, path: Path, record: dict) -> None:
        """Outside the publication transaction ON PURPOSE. A route that fails every night must never
        look identical to one nobody scheduled, so the evidence that we TRIED survives the rollback
        of what we tried to write."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def quarantine(self, path: Path, data: bytes) -> None:
        """Bytes that arrived but could not be accepted are the only proof of what the provider
        served on a bad day. Refusing them is correct; discarding them destroys the diagnosis."""
        if not path.is_file():
            self._atomic_write(path, data)


class _Journal:
    """Prior state for every file an attempt touches, so a failure can undo an OVERWRITE and not
    merely a creation.

    The first implementation tracked created paths only. That passed three of the four boundary
    cases and failed the fourth: a marker-boundary failure left the already-rewritten index naming a
    vintage the publication had abandoned — the exact "second run half-succeeds over a good one"
    hazard E1 exists to catch.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.entries: list[tuple[Path, bytes | None]] = []

    def note(self, path: Path) -> Path:
        self.entries.append((path, path.read_bytes() if path.is_file() else None))
        return path

    def rollback(self) -> None:
        for path, prior in reversed(self.entries):
            if prior is None:
                path.unlink(missing_ok=True)
                continue
            # Replaced, never written in place: raw links share an inode with the content store, and
            # an in-place write would reach through the link and corrupt a retained vintage.
            tmp = path.with_name(f".{path.name}.rollback")
            tmp.write_bytes(prior)
            os.replace(tmp, path)
        self.sweep_temp_artifacts()

    def sweep_temp_artifacts(self) -> None:
        """Remove half-finished writes wherever they came from.

        Restoring only what this journal itself touched is not enough: a boundary that fails PARTWAY
        THROUGH leaves a temp file the journal never recorded, and an independent probe proved it —
        `.index.json.tmp` survived a rolled-back publication while every other invariant held.
        """
        if not self.root.is_dir():
            return
        for path in self.root.rglob("*"):
            if path.is_file() and path.name.startswith(".") and (
                    path.name.endswith(".tmp") or path.name.endswith(".rollback")):
                path.unlink(missing_ok=True)


class FailingAt:
    """Injects a failure at one named storage boundary. A fault-injection PARAMETER on the route
    would ship test-only surface into production; a collaborator does not.

    `fault` matters as much as `boundary`. Raising the route's OWN exception only exercises the path
    the route already expects — a real filesystem raises `OSError` from `mkdir`, temp writes, links,
    copies and `os.replace`, and that class escaped this route unnormalised until it was injected.
    """

    def __init__(self, inner: FilesystemStorage, boundary: str,
                 fault: str = "route_error") -> None:
        if boundary not in _BOUNDARIES:
            raise ValueError(f"unknown boundary: {boundary}")
        if fault not in ("route_error", "os_error", "mid_write"):
            raise ValueError(f"unknown fault: {fault}")
        self.inner = inner
        self.boundary = boundary
        self.fault = fault
        self.root = inner.root

    def _guard(self, boundary: str, target: Path | None = None) -> None:
        """`route_error` and `os_error` raise BEFORE the filesystem is touched, which is why neither
        could reproduce the failure that actually happens on a full disk. `mid_write` creates the
        temp file the real writer would have created, then fails — leaving exactly the half-finished
        state an independent probe used to falsify the no-partials invariant."""
        if boundary != self.boundary:
            return
        if self.fault == "mid_write" and target is not None:
            tmp = target.with_name(f".{target.name}.tmp")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(b"partially written")
            raise OSError(28, "No space left on device")
        if self.fault in ("os_error", "mid_write"):
            raise OSError(28, "No space left on device")
        raise PublishError(boundary, "injected storage failure")

    def read_json(self, path: Path, default: Any = None) -> Any:
        return self.inner.read_json(path, default)

    def write_raw(self, content_path: Path, link_path: Path, data: bytes,
                  expected_sha256: str) -> list[Path]:
        self._guard("raw", content_path)
        return self.inner.write_raw(content_path, link_path, data, expected_sha256)

    def write_vintage(self, path: Path, payload: dict) -> list[Path]:
        self._guard("store", path)
        return self.inner.write_vintage(path, payload)

    def write_index(self, path: Path, payload: dict) -> list[Path]:
        self._guard("index", path)
        return self.inner.write_index(path, payload)

    def write_marker(self, path: Path, payload: dict) -> list[Path]:
        self._guard("marker", path)
        return self.inner.write_marker(path, payload)

    def append_audit(self, path: Path, record: dict) -> None:
        self.inner.append_audit(path, record)

    def quarantine(self, path: Path, data: bytes) -> None:
        self.inner.quarantine(path, data)


# ── route descriptor ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RouteDescriptor:
    name: str
    competition: str
    source_url: str
    offering_scope: str
    revision_bearing: bool
    versioned: bool
    seasonal: bool
    finality_capability: str
    finality_reason: str
    entrypoint: str


def route_descriptor() -> RouteDescriptor:
    return RouteDescriptor(
        name="b21_schedules",
        competition="nfl",
        source_url=NFLVERSE_SCHEDULES_URL,
        offering_scope="global",
        revision_bearing=True,
        versioned=True,
        seasonal=True,
        finality_capability="unverified",
        finality_reason=(
            "the schedules feed carries no terminal-status field and no end-time, and may publish "
            "interim scores; a populated score proves play was observed, never that play ended"
        ),
        entrypoint="scripts/run_schedules_capture.py",
    )


# ── records ──────────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OfferingRecord:
    check_id: str
    vintage_id: str
    raw_sha256: str
    byte_count: int
    schema_hash: str
    created_vintage: bool
    observed_at: str
    retrieved_at: str
    source_url: str
    #: What actually served the bytes. Equal to `source_url` on a direct record; a signed
    #: `release-assets.githubusercontent.com` URL on a normal provider retrieval.
    delivered_from: str


@dataclass(frozen=True)
class WeekSlice:
    season: int
    week: int
    vintage_id: str
    source_sha256: str
    rows: list[dict]
    membership_evidence: str

    @property
    def row_count(self) -> int:
        return len(self.rows)


# ── helpers ──────────────────────────────────────────────────────────────────────────────────────


def _dumps(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify_object(path: Path, data: bytes, expected_sha256: str) -> None:
    """Size first, then the full hash — size is the cheap discriminator and the hash is the proof."""
    existing = path.read_bytes()
    if len(existing) != len(data) or _sha256(existing) != expected_sha256:
        raise CaptureError(
            "content_integrity_mismatch",
            f"{path.name} holds {len(existing)} bytes hashing to {_sha256(existing)}, "
            f"but the address claims {len(data)} bytes hashing to {expected_sha256}",
        )


def _safe_id(identifier: Any) -> str:
    """Capture identities become path segments. A `retrieved_at` string-sliced into a path is how a
    traversal value escaped a layout in this repo once already, so the check is on the identifier
    itself rather than on the joined result."""
    if not isinstance(identifier, str) or not _SAFE_ID.match(identifier):
        raise CaptureError("unsafe_identifier", repr(identifier))
    return identifier


def _require_timestamp(value: Any, code: str) -> str:
    """Timezone-aware or nothing. A naive instant cannot be ordered against any other evidence, and
    every freshness answer built on it would be meaningless."""
    if not isinstance(value, str):
        raise CaptureError(code, repr(value))
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CaptureError(code, repr(value)) from exc
    if parsed.tzinfo is None:
        raise CaptureError(code, f"{value!r} carries no UTC offset")
    return value


def _dtype_pairs(frame: pl.DataFrame) -> list[list[str]]:
    return [[name, str(dtype)] for name, dtype in frame.schema.items()]


def _schema_hash(frame: pl.DataFrame) -> str:
    """Hashes the ORDERED [column, dtype] pairs as compact JSON. The canonical form is pinned so a
    reviewer can recompute the number an acceptance packet reports — a hash nobody can reproduce is
    decoration."""
    canonical = json.dumps(_dtype_pairs(frame), separators=(",", ":"))
    return _sha256(canonical.encode("utf-8"))


def _is_integer_dtype(dtype: Any) -> bool:
    return dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                     pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64)


def _is_numeric_or_null_dtype(dtype: Any) -> bool:
    return _is_integer_dtype(dtype) or dtype in (pl.Float32, pl.Float64, pl.Null)


def _validate(frame: pl.DataFrame) -> None:
    """Fail-closed semantic validation, in a DELIBERATE order: an unusable field is a more basic
    fact than a disagreement between two fields, so type/null checks precede identifier consistency
    and the diagnostic names the cause rather than a downstream symptom."""
    if frame.height == 0:
        raise CaptureError("raw_empty", "the offering carries zero rows")

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise CaptureError("schema_missing_column", ", ".join(missing))

    schema = frame.schema
    for field in _INTEGER_FIELDS:
        if not _is_integer_dtype(schema[field]):
            raise CaptureError("required_field_type_invalid",
                               f"{field} is {schema[field]}, expected an integer")
    for field in _NON_EMPTY_TEXT_FIELDS:
        if schema[field] != pl.String:
            raise CaptureError("required_field_type_invalid",
                               f"{field} is {schema[field]}, expected text")
    for field in _SCORE_FIELDS:
        if not _is_numeric_or_null_dtype(schema[field]):
            raise CaptureError("score_type_invalid",
                               f"{field} is {schema[field]}, expected a number")

    rows = frame.to_dicts()

    for row in rows:
        for field in _INTEGER_FIELDS:
            if row[field] is None:
                raise CaptureError("required_field_type_invalid", f"{field} is null")
        for field in _NON_EMPTY_TEXT_FIELDS:
            value = row[field]
            if value is None or not str(value).strip():
                raise CaptureError("required_field_type_invalid",
                                   f"{field} is {'null' if value is None else 'empty'}")

    for row in rows:
        _validate_source_times(row)

    for row in rows:
        for field in _SCORE_FIELDS:
            value = row[field]
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise CaptureError("score_type_invalid", f"{field}={value!r}")
            if isinstance(value, float) and (value != value or value in (float("inf"),
                                                                         float("-inf"))):
                raise CaptureError("score_type_invalid", f"{field} is not finite")

    seen: set[str] = set()
    for row in rows:
        game_id = row["game_id"]
        if game_id in seen:
            raise CaptureError("duplicate_game_id", game_id)
        seen.add(game_id)

    for row in rows:
        expected = f"{row['season']}_{int(row['week']):02d}_{row['away_team']}_{row['home_team']}"
        if row["game_id"] != expected:
            raise CaptureError(
                "game_id_inconsistent",
                f"{row['game_id']!r} disagrees with its own row (expected {expected!r})",
            )


def _validate_source_times(row: dict) -> None:
    """The provider's own kickoff, kept distinct from OUR capture provenance so a provider fault is
    never read as a fault in our own timestamps."""
    gameday = row["gameday"]
    if not isinstance(gameday, str):
        raise CaptureError("source_time_invalid", f"gameday={gameday!r}")
    try:
        date.fromisoformat(gameday)
    except ValueError as exc:
        raise CaptureError("source_time_invalid", f"gameday={gameday!r}") from exc

    gametime = row["gametime"]
    if gametime is None or gametime == "":
        # An UNPUBLISHED kickoff time. Measured: 259 of 7,548 held rows carry one, and the offering
        # is global, so they arrive in the very first capture. This is the provider declining to
        # claim something — the one kind of missingness a Layer 1 route must never overwrite.
        return
    if not isinstance(gametime, str) or not _HH_MM.match(gametime):
        raise CaptureError("source_time_invalid", f"gametime={gametime!r}")


# ── the store ────────────────────────────────────────────────────────────────────────────────────


class ScheduleStore:
    """Retains what the provider published, and nothing it did not.

    Three identities, deliberately separate: a CHECK is one retrieval attempt; a CONTENT VINTAGE is
    one distinct payload keyed by the hash of the raw bytes; a WEEK SLICE is a derived view of one
    vintage. Most checks find nothing new — minting a vintage per check would fabricate a change
    history the source never had.
    """

    def __init__(self, root: Path | str, storage: Any | None = None) -> None:
        self.root = Path(root)
        self.storage = storage if storage is not None else FilesystemStorage(self.root)

    # -- paths -----------------------------------------------------------------------------------

    def raw_path(self, check_id: str) -> Path:
        return self.root / "raw" / f"{_safe_id(check_id)}.parquet"

    def content_path(self, raw_sha256: str) -> Path:
        return self.root / "content" / f"{_safe_id(raw_sha256)}.parquet"

    def vintage_path(self, vintage_id: str) -> Path:
        return self.root / "vintages" / f"{_safe_id(vintage_id)}.json"

    def index_path(self) -> Path:
        return self.root / "index.json"

    def marker_path(self) -> Path:
        return self.root / "ready.json"

    def ledger_path(self) -> Path:
        return self.root / "ledger.jsonl"

    def quarantine_path(self, raw_sha256: str) -> Path:
        return self.root / "quarantine" / f"{_safe_id(raw_sha256)}.parquet"

    def quarantined_raw(self, raw_sha256: str) -> Path | None:
        path = self.quarantine_path(raw_sha256)
        return path if path.is_file() else None

    # -- reads -----------------------------------------------------------------------------------

    def _index(self) -> dict:
        return self.storage.read_json(self.index_path(),
                                      {"checks": [], "vintages": {}}) or {"checks": [],
                                                                          "vintages": {}}

    def _audit(self) -> list[dict]:
        path = self.ledger_path()
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def read_raw(self, check_id: str) -> bytes:
        path = self.raw_path(check_id)
        if not path.is_file():
            raise CaptureError("raw_missing", check_id)
        return path.read_bytes()

    def parse(self, raw: bytes) -> list[dict]:
        return _read_frame(raw).to_dicts()

    def get_vintage(self, vintage_id: str) -> dict | None:
        """Metadata from disk, rows DERIVED from the retained bytes.

        The parsed rows are not persisted (David, 2026-08-09). They were 9.1 MB of a 9.1 MB file
        whose actual metadata is 1.7 KB, they re-derive in ~200 ms, and persisting them created a
        second source of truth that could drift from the Parquet it came from — the very thing S4
        exists to prevent. `parser_version` plus the retained bytes reconstructs any past parse.
        """
        path = self.vintage_path(vintage_id)
        if not path.is_file():
            return None
        # A fresh object every call: a store that hands out references to its own structures lets a
        # caller silently rewrite recorded history. Deriving from bytes gives that for free.
        vintage = json.loads(path.read_text(encoding="utf-8"))
        vintage.pop("rows", None)  # tolerate a pre-migration file without trusting its copy
        content = self.content_path(vintage["raw_sha256"])
        if content.is_file():
            vintage["rows"] = self.parse(content.read_bytes())
        return vintage

    def marker(self) -> dict | None:
        return self.storage.read_json(self.marker_path(), None)

    def vintage_count(self) -> int:
        return len(self._index()["vintages"])

    def successful_check_count(self) -> int:
        return len(self._index()["checks"])

    def failed_check_count(self) -> int:
        return sum(1 for record in self._audit() if record.get("status") == "failed")

    def check_count(self) -> int:
        return self.successful_check_count() + self.failed_check_count()

    def partial_artifacts(self) -> list[str]:
        """Anything on disk the index does not vouch for: a temp file, an orphan raw link, an
        unreferenced vintage. A successful publish leaves none, and so must a rolled-back one."""
        index = self._index()
        known_checks = {entry["check_id"] for entry in index["checks"]}
        known_vintages = set(index["vintages"])
        orphans: list[str] = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(self.root).as_posix()
            if path.name.startswith(".") and ".tmp" in path.name:
                orphans.append(relative)
            elif path.parent.name == "raw" and path.stem not in known_checks:
                orphans.append(relative)
            elif path.parent.name == "vintages" and path.stem not in known_vintages:
                orphans.append(relative)
        return orphans

    # -- projections -----------------------------------------------------------------------------

    def week_slice(self, *, vintage_id: str, season: int, week: int) -> WeekSlice:
        """A week is a VIEW of one retained vintage. Rows are selected by their OWN season and week,
        so a caller cannot file 2025 Week 2 rows under a 2026 Week 1 path, and two partial vintages
        can never be unioned into a completeness the source never published at any single instant."""
        vintage = self.get_vintage(vintage_id)
        if vintage is None:
            raise CaptureError("vintage_unknown", vintage_id)
        rows = [row for row in vintage["rows"]
                if row.get("season") == season and row.get("week") == week]
        return WeekSlice(
            season=season,
            week=week,
            vintage_id=vintage_id,
            source_sha256=vintage["raw_sha256"],
            rows=rows,
            membership_evidence="derived_from_vintage" if rows else "absent_from_vintage",
        )

    def replay(self, check_id: str) -> dict:
        """Re-derive the parse from retained bytes. An AUDIT operation, not a retrieval: it mints no
        check identity and does not advance the check clock, or the route's own history would
        inflate every time anybody re-read it."""
        raw = self.read_raw(check_id)
        return {"check_id": check_id, "raw_sha256": _sha256(raw), "rows": self.parse(raw)}

    # -- writes ----------------------------------------------------------------------------------

    def capture(self, *, fetcher: Any, observed_at: str) -> OfferingRecord:
        """One scheduled look at the provider: retrieve, then record. Exactly one retrieval."""
        observed_at = _require_timestamp(observed_at, "observed_at_invalid")
        url = NFLVERSE_SCHEDULES_URL
        try:
            result = fetcher.fetch(url)
        except FetchError as exc:
            detail = _scrub(exc.detail)
            self._record_failure(observed_at=observed_at, reason=exc.code, detail=detail)
            # A NEW, SANITIZED exception — never a bare re-raise. A transport exception embeds the
            # URL it failed on, that URL is the signed one, and whatever is raised here is printed
            # by the CLI into a terminal, a log file, or a scheduler's captured output. Scrubbing
            # only the ledger closed one surface and left the louder one open.
            raise FetchError(exc.code, detail) from None

        # A redirect is NORMAL for this provider — GitHub 302s the release URL to a signed asset on
        # `release-assets.githubusercontent.com`. Requiring the final URL to equal the requested one
        # rejected every real retrieval. What must hold is that we ASKED the sanctioned URL and the
        # bytes were delivered by the provider's own domains; an arbitrary mirror is still refused.
        # Validate against the FULL url (scheme and host are what the policy is about), but never
        # let the query string past this point — not into the store, not into the audit trail, and
        # not into the exception message.
        delivered_from = _sanitize_url(result.final_url)
        if result.requested_url != url or not _delivery_host_is_sanctioned(result.final_url):
            self._record_failure(
                observed_at=observed_at, reason="source_identity_unexpected",
                detail=f"requested={_sanitize_url(result.requested_url)} final={delivered_from}")
            raise CaptureError(
                "source_identity_unexpected",
                f"requested {url!r}, bytes delivered by {delivered_from!r}, which is not a "
                f"sanctioned provider host",
            )
        try:
            retrieved_at = _require_timestamp(result.retrieved_at, "retrieved_at_invalid")
        except CaptureError as exc:
            self._record_failure(observed_at=observed_at, reason=exc.code,
                                 detail=repr(result.retrieved_at))
            raise
        return self.record_offering(observed_at=observed_at, raw=result.body,
                                    source_url=url, retrieved_at=retrieved_at,
                                    delivered_from=delivered_from)

    def record_offering(self, *, observed_at: str, raw: Any, source_url: str,
                        retrieved_at: str | None = None,
                        delivered_from: str | None = None) -> OfferingRecord:
        """Accept one offering: hash first, interpret after, publish atomically.

        `retrieved_at` defaults to `observed_at` for direct (non-transport) recording, where the
        observation instant IS the moment the bytes were taken in hand.
        """
        if source_url != NFLVERSE_SCHEDULES_URL:
            raise CaptureError("source_identity_unexpected", repr(source_url))
        if not isinstance(raw, (bytes, bytearray)):
            raise CaptureError("raw_bytes_required", f"got {type(raw).__name__}")
        raw = bytes(raw)
        observed_at = _require_timestamp(observed_at, "observed_at_invalid")
        retrieved_at = _require_timestamp(retrieved_at or observed_at, "retrieved_at_invalid")

        raw_sha256 = _sha256(raw)
        try:
            frame = _read_frame(raw)
            _validate(frame)
        except CaptureError as exc:
            # Bytes that arrived but cannot be accepted are retained with their hash: they are the
            # only evidence of what the provider actually served.
            self.storage.quarantine(self.quarantine_path(raw_sha256), raw)
            self._record_failure(observed_at=observed_at, reason=exc.code, detail=str(exc),
                                 raw_sha256=raw_sha256)
            raise

        rows = frame.to_dicts()
        schema_hash = _schema_hash(frame)
        vintage_id = f"v-{raw_sha256[:16]}"
        check_id = f"c-{_compact(observed_at)}-{raw_sha256[:12]}"

        index = self._index()
        created_vintage = vintage_id not in index["vintages"]
        record = OfferingRecord(
            check_id=check_id, vintage_id=vintage_id, raw_sha256=raw_sha256,
            byte_count=len(raw), schema_hash=schema_hash, created_vintage=created_vintage,
            observed_at=observed_at, retrieved_at=retrieved_at, source_url=source_url,
            delivered_from=_sanitize_url(delivered_from or source_url),
        )

        journal = _Journal(self.root)
        try:
            journal.note(self.content_path(raw_sha256))
            journal.note(self.raw_path(check_id))
            self._boundary("raw", lambda: self.storage.write_raw(
                self.content_path(raw_sha256), self.raw_path(check_id), raw, raw_sha256))
            if created_vintage:
                journal.note(self.vintage_path(vintage_id))
                self._boundary("store", lambda: self.storage.write_vintage(
                    self.vintage_path(vintage_id), {
                    "vintage_id": vintage_id,
                    "raw_sha256": raw_sha256,
                    "byte_count": len(raw),
                    "schema_hash": schema_hash,
                    "dtypes": _dtype_pairs(frame),
                    "observed_at": observed_at,
                    "retrieved_at": retrieved_at,
                    "source_url": source_url,
                    "delivered_from": record.delivered_from,
                    "parser_version": PARSER_VERSION,
                    "row_count": len(rows),
                    "column_count": len(frame.columns),
                    }))
            index["checks"] = [*index["checks"], {
                "check_id": check_id, "vintage_id": vintage_id, "raw_sha256": raw_sha256,
                "observed_at": observed_at, "retrieved_at": retrieved_at,
                "created_vintage": created_vintage,
            }]
            if created_vintage:
                index["vintages"] = {**index["vintages"], vintage_id: {
                    "raw_sha256": raw_sha256, "first_seen_at": observed_at,
                    "schema_hash": schema_hash,
                }}
            journal.note(self.index_path())
            self._boundary("index",
                           lambda: self.storage.write_index(self.index_path(), index))

            previous = self.marker() or {}
            journal.note(self.marker_path())
            self._boundary("marker", lambda: self.storage.write_marker(self.marker_path(), {
                "route": route_descriptor().name,
                "source_url": source_url,
                "delivered_from": record.delivered_from,
                "vintage_id": vintage_id,
                "raw_sha256": raw_sha256,
                "byte_count": len(raw),
                "schema_hash": schema_hash,
                "parser_version": PARSER_VERSION,
                "observed_at": observed_at,
                "retrieved_at": retrieved_at,
                "last_checked_at": observed_at,
                # Frozen on a no-change check: advancing it would report a revision that never
                # happened, and every downstream "when did this last change?" answer would be wrong.
                "last_changed_at": observed_at if created_vintage
                else previous.get("last_changed_at", observed_at),
                "finality_capability": route_descriptor().finality_capability,
            }))
        except PublishError as exc:
            journal.rollback()
            self._record_failure(observed_at=observed_at, reason=f"publish_failed:{exc.boundary}",
                                 detail=str(exc), raw_sha256=raw_sha256)
            raise
        except CaptureError as exc:
            # An integrity refusal discovered mid-publication is still a refusal to ADD, never a
            # licence to damage what is already retained: roll back, audit, and leave the prior
            # capture exactly as it was.
            journal.rollback()
            self._record_failure(observed_at=observed_at, reason=exc.code, detail=str(exc),
                                 raw_sha256=raw_sha256)
            raise

        self.storage.append_audit(self.ledger_path(), {
            "status": "ok", "check_id": check_id, "vintage_id": vintage_id,
            "raw_sha256": raw_sha256, "byte_count": len(raw), "schema_hash": schema_hash,
            "observed_at": observed_at, "retrieved_at": retrieved_at,
            "created_vintage": created_vintage, "source_url": source_url,
            "delivered_from": record.delivered_from, "parser_version": PARSER_VERSION,
        })
        return record

    def _boundary(self, name: str, write: Any) -> Any:
        """Run one storage boundary, normalizing a REAL filesystem failure into this route's own
        publication failure.

        Production storage raises `OSError` — from `mkdir`, a temp write, a link, a copy, or
        `os.replace`. Until this existed, that class escaped unnormalised: rollback never ran, the
        attempt was never audited, orphan artifacts survived, and the CLI produced a traceback
        instead of the named failure the scheduler reads.
        """
        try:
            return write()
        except PublishError:
            raise
        except OSError as exc:
            raise PublishError(name, f"{type(exc).__name__}: {exc}") from exc

    def _record_failure(self, *, observed_at: str, reason: str, detail: str,
                        raw_sha256: str | None = None) -> None:
        self.storage.append_audit(self.ledger_path(), {
            "status": "failed", "reason": reason, "detail": _scrub(detail),
            "observed_at": observed_at, "raw_sha256": raw_sha256,
            "source_url": NFLVERSE_SCHEDULES_URL, "parser_version": PARSER_VERSION,
        })


def _read_frame(raw: bytes) -> pl.DataFrame:
    try:
        return pl.read_parquet(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001 - any decode failure is one refusal
        raise CaptureError("raw_unparseable", f"{type(exc).__name__}: {exc}") from exc


def _compact(timestamp: str) -> str:
    """A timestamp flattened into a path-safe token. Never sliced — `_safe_id` still guards the
    result, because a value derived from provider-influenced material is not trusted by derivation.
    """
    return re.sub(r"[^0-9A-Za-z]", "", timestamp)
