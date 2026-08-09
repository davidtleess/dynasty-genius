"""Source-authentic capture of CFBD's season-scoped FBS games offering."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from src.dynasty_genius.adapters import cfbd_http

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = REPO_ROOT / "app" / "data" / "sources" / "cfbd_fbs_schedules"
ENDPOINT = "https://api.collegefootballdata.com/games"
OPENAPI_VERSION = "5.21.0"
OPENAPI_SHA256 = "f6274010fb8f3d11c4c574fd4d648fd33e6c47e0eca2cfb61b481b20ca482ea3"
PARSER_VERSION = "cfbd.fbs_schedules.v1"

REQUIRED_FIELDS = frozenset(
    {
        "id", "season", "week", "seasonType", "startDate", "startTimeTBD",
        "completed", "neutralSite", "conferenceGame", "attendance", "venueId",
        "venue", "homeId", "homeTeam", "homeConference", "homeClassification",
        "homePoints", "homeLineScores", "homePostgameWinProbability",
        "homePregameElo", "homePostgameElo", "awayId", "awayTeam",
        "awayConference", "awayClassification", "awayPoints", "awayLineScores",
        "awayPostgameWinProbability", "awayPregameElo", "awayPostgameElo",
        "excitementIndex", "highlights", "notes", "playoff",
    }
)
PLAYOFF_FIELDS = frozenset(
    {"competition", "format", "round", "roundName", "bracketSlot", "homeSeed",
     "awaySeed", "bowlName"}
)
SEASON_TYPES = frozenset(
    {"regular", "postseason", "both", "allstar", "spring_regular", "spring_postseason"}
)
ROUTE_SEASON_TYPES = frozenset({"regular", "postseason"})
CLASSIFICATIONS = frozenset({"fbs", "fcs", "ii", "iii"})
PLAYOFF_ROUNDS = frozenset({"first_round", "quarterfinal", "semifinal", "championship"})
_BOUNDARIES = frozenset({"raw", "store", "index", "marker", "audit"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_URL_IN_TEXT = re.compile(r"https?://[^\s'\"]+")
_SOURCE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
)


class CaptureError(RuntimeError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.detail = message


class FetchError(CaptureError):
    def __init__(self, code: str, message: str = "", *, request_count: int = 0) -> None:
        super().__init__(code, message)
        self.request_count = request_count


class PublishError(RuntimeError):
    def __init__(self, boundary: str, message: str = "") -> None:
        super().__init__(f"{boundary}: {message}" if message else boundary)
        self.boundary = boundary


@dataclass(frozen=True)
class RouteDescriptor:
    name: str
    provider: str
    report_family: str
    competition: str
    endpoint: str
    query: dict[str, Any]
    request_url: str
    openapi_version: str
    openapi_sha256: str
    offering_scope: str


def route_descriptor(year: int) -> RouteDescriptor:
    _validate_year(year)
    query = {"year": year, "seasonType": "both", "classification": "fbs"}
    url = f"{ENDPOINT}?year={year}&seasonType=both&classification=fbs"
    return RouteDescriptor(
        name="cfbd_fbs_schedules",
        provider="College Football Data API",
        report_family="games",
        competition="fbs",
        endpoint=ENDPOINT,
        query=query,
        request_url=url,
        openapi_version=OPENAPI_VERSION,
        openapi_sha256=OPENAPI_SHA256,
        offering_scope="season",
    )


@dataclass(frozen=True)
class FetchResult:
    requested_url: str
    final_url: str
    body: bytes
    retrieved_at: str
    provider_date: str | None
    call_limit_remaining: object
    content_type: str
    request_count: int


class HttpFetcher:
    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def fetch(self, url: str, *, api_key: str) -> FetchResult:
        attempts = 0
        response: httpx.Response | None = None

        def operation() -> httpx.Response:
            nonlocal attempts
            attempts += 1
            result = httpx.get(
                url,
                headers={"Accept": "application/json", "Authorization": f"Bearer {api_key}"},
                follow_redirects=True,
                timeout=self.timeout,
            )
            result.raise_for_status()
            return result

        try:
            response = cfbd_http.with_retry(operation)
        except Exception as exc:  # noqa: BLE001 - normalize the transport boundary
            detail = scrub_message(f"{type(exc).__name__}: {exc}", api_key)
            raise FetchError("fetch_failed", detail, request_count=attempts) from None
        return FetchResult(
            requested_url=url,
            final_url=str(response.url),
            body=response.content,
            retrieved_at=datetime.now(UTC).isoformat(),
            provider_date=response.headers.get("Date"),
            call_limit_remaining=response.headers.get("X-CallLimit-Remaining"),
            content_type=response.headers.get("Content-Type", ""),
            request_count=attempts,
        )


class RecordingFetcher:
    def __init__(
        self,
        *,
        bodies: list[bytes],
        retrieved_at: str,
        provider_date: str | None,
        call_limit_remaining: object,
        content_type: str,
        final_url: str,
        error: str | None = None,
        request_count: int = 1,
    ) -> None:
        self.bodies = list(bodies)
        self.retrieved_at = retrieved_at
        self.provider_date = provider_date
        self.call_limit_remaining = call_limit_remaining
        self.content_type = content_type
        self.final_url = final_url
        self.error = error
        self.request_count = request_count
        self.calls: list[dict[str, Any]] = []

    def fetch(self, url: str, *, api_key: str) -> FetchResult:
        self.calls.append(
            {"url": url, "headers": {"Accept": "application/json",
                                      "Authorization": f"Bearer {api_key}"}}
        )
        if self.error is not None:
            raise FetchError("fetch_failed", self.error, request_count=self.request_count)
        if not self.bodies:
            raise FetchError("fetch_failed", "no prepared response", request_count=0)
        return FetchResult(
            requested_url=url,
            final_url=self.final_url,
            body=self.bodies.pop(0),
            retrieved_at=self.retrieved_at,
            provider_date=self.provider_date,
            call_limit_remaining=self.call_limit_remaining,
            content_type=self.content_type,
            request_count=self.request_count,
        )


def default_fetcher() -> HttpFetcher:
    return HttpFetcher()


def _sanitize_url(url: str) -> str:
    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    return f"{parts.scheme}://{host}{parts.path}" if host else f"{parts.scheme}://"


def scrub_message(text: str, secret: str | None = None) -> str:
    if secret:
        text = text.replace(secret, "<redacted>")

    def redact(match: re.Match[str]) -> str:
        url = match.group(0)
        suffix = "?<redacted>" if "?" in url or "#" in url else ""
        return _sanitize_url(url) + suffix

    return _URL_IN_TEXT.sub(redact, text)


def _safe_id(identifier: str) -> str:
    if not isinstance(identifier, str) or not _SAFE_ID.fullmatch(identifier):
        raise CaptureError("unsafe_identifier", repr(identifier))
    return identifier


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dumps(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _validate_year(year: Any) -> int:
    if isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 9999:
        raise ValueError(f"invalid year: {year!r}")
    return year


def _require_aware_timestamp(value: Any) -> str:
    if not isinstance(value, str):
        raise CaptureError("retrieved_at_invalid", repr(value))
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CaptureError("retrieved_at_invalid", repr(value)) from exc
    if parsed.tzinfo is None:
        raise CaptureError("retrieved_at_invalid", f"{value!r} has no offset")
    return value


def _parse_remaining(value: object) -> tuple[int | None, str]:
    if value is None:
        return None, "request_count_only_header_absent"
    if isinstance(value, bool):
        return None, "request_count_only_header_invalid"
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, "request_count_only_header_invalid"
    if parsed < 0 or (isinstance(value, float) and not value.is_integer()):
        return None, "request_count_only_header_invalid"
    return parsed, "request_count_and_remaining_header"


class _DuplicateMember(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateMember(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite number {value}")


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise AssertionError(type(value))


def _schema(rows: list[dict[str, Any]]) -> list[list[object]]:
    return [
        [field, sorted({_json_type(row[field]) for row in rows})]
        for field in sorted(rows[0])
    ]


def _schema_hash(rows: list[dict[str, Any]]) -> str:
    canonical = json.dumps(_schema(rows), separators=(",", ":"), ensure_ascii=False)
    return _sha256(canonical.encode())


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_type(condition: bool, field: str, value: Any) -> None:
    if not condition:
        raise CaptureError("required_field_type_invalid", f"{field}={value!r}")


def _validate_playoff(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise CaptureError("required_field_type_invalid", f"playoff={value!r}")
    if set(value) != PLAYOFF_FIELDS:
        raise CaptureError("nested_schema_invalid", "GamePlayoff field membership")
    if value["competition"] != "cfp" or value["round"] not in PLAYOFF_ROUNDS:
        raise CaptureError("nested_schema_invalid", "GamePlayoff enum")
    for field in ("format", "roundName", "bracketSlot"):
        if not isinstance(value[field], str):
            raise CaptureError("nested_schema_invalid", f"GamePlayoff.{field}")
    for field in ("homeSeed", "awaySeed"):
        item = value[field]
        if item is not None and not _is_int(item):
            raise CaptureError("nested_schema_invalid", f"GamePlayoff.{field}")
    if value["bowlName"] is not None and not isinstance(value["bowlName"], str):
        raise CaptureError("nested_schema_invalid", "GamePlayoff.bowlName")


def _validate_rows(rows: list[dict[str, Any]], year: int) -> None:
    if not rows:
        raise CaptureError("raw_empty", "zero games")
    for row in rows:
        if not isinstance(row, dict):
            raise CaptureError("raw_unparseable", "array member is not an object")
        fields = set(row)
        missing = REQUIRED_FIELDS - fields
        if missing:
            raise CaptureError("schema_missing_field", ",".join(sorted(missing)))
        extra = fields - REQUIRED_FIELDS
        if extra:
            raise CaptureError("schema_drift", ",".join(sorted(extra)))

    integer_fields = ("id", "season", "week", "homeId", "awayId")
    nullable_integer_fields = (
        "attendance", "venueId", "homePoints", "homePregameElo", "homePostgameElo",
        "awayPoints", "awayPregameElo", "awayPostgameElo",
    )
    boolean_fields = ("startTimeTBD", "completed", "neutralSite", "conferenceGame")
    string_fields = ("seasonType", "startDate", "homeTeam", "awayTeam")
    nullable_string_fields = (
        "venue", "homeConference", "homeClassification", "awayConference",
        "awayClassification", "highlights", "notes",
    )
    nullable_number_fields = (
        "homePostgameWinProbability", "awayPostgameWinProbability", "excitementIndex",
    )

    for row in rows:
        for field in integer_fields:
            _require_type(_is_int(row[field]), field, row[field])
        for field in nullable_integer_fields:
            value = row[field]
            _require_type(value is None or _is_int(value), field, value)
        for field in boolean_fields:
            _require_type(isinstance(row[field], bool), field, row[field])
        for field in string_fields:
            value = row[field]
            _require_type(isinstance(value, str) and bool(value.strip()), field, value)
        for field in nullable_string_fields:
            value = row[field]
            _require_type(value is None or isinstance(value, str), field, value)
        for field in nullable_number_fields:
            value = row[field]
            _require_type(value is None or _is_number(value), field, value)
        for field in ("homeLineScores", "awayLineScores"):
            value = row[field]
            _require_type(value is None or isinstance(value, list), field, value)
            if value is not None and not all(_is_number(item) for item in value):
                raise CaptureError("nested_field_type_invalid", field)
        _validate_playoff(row["playoff"])

    for row in rows:
        if row["seasonType"] not in SEASON_TYPES:
            raise CaptureError("enum_invalid", f"seasonType={row['seasonType']!r}")
        for field in ("homeClassification", "awayClassification"):
            value = row[field]
            if value is not None and value not in CLASSIFICATIONS:
                raise CaptureError("enum_invalid", f"{field}={value!r}")
        if row["seasonType"] not in ROUTE_SEASON_TYPES:
            raise CaptureError("season_type_scope_mismatch", row["seasonType"])
        if row["season"] != year:
            raise CaptureError("season_scope_mismatch", str(row["season"]))
        if row["homeClassification"] != "fbs" and row["awayClassification"] != "fbs":
            raise CaptureError("competition_scope_mismatch", str(row["id"]))
        try:
            if not _SOURCE_TIME.fullmatch(row["startDate"]):
                raise ValueError("non-provider timestamp shape")
            parsed = datetime.fromisoformat(row["startDate"])
        except ValueError as exc:
            raise CaptureError("source_time_invalid", row["startDate"]) from exc
        if not isinstance(parsed, datetime):  # pragma: no cover - documents intent
            raise CaptureError("source_time_invalid", row["startDate"])

    seen: set[int] = set()
    for row in rows:
        if row["id"] in seen:
            raise CaptureError("duplicate_game_id", str(row["id"]))
        seen.add(row["id"])


def _parse(raw: bytes, year: int) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except _DuplicateMember as exc:
        raise CaptureError("duplicate_json_member", str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - one stable refusal for malformed JSON
        raise CaptureError("raw_unparseable", f"{type(exc).__name__}: {exc}") from exc
    if not isinstance(parsed, list) or any(not isinstance(row, dict) for row in parsed):
        raise CaptureError("raw_unparseable", "top level must be an array of objects")
    _validate_rows(parsed, year)
    return parsed


def _verify_object(path: Path, incoming: bytes, expected_sha256: str) -> None:
    existing = path.read_bytes()
    if len(existing) != len(incoming) or _sha256(existing) != expected_sha256:
        raise CaptureError(
            "content_integrity_mismatch",
            f"{path.name}: existing bytes disagree with content address",
        )


class FilesystemStorage:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def _atomic_write(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def read_json(self, path: Path, default: Any) -> Any:
        if not path.is_file():
            return default
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CaptureError(
                "state_integrity_invalid", f"{path.name}: {type(exc).__name__}"
            ) from exc

    def write_raw(
        self, content_path: Path, check_path: Path, data: bytes, expected_sha256: str
    ) -> None:
        for path in (content_path, check_path):
            if path.is_file():
                _verify_object(path, data, expected_sha256)
            else:
                self._atomic_write(path, data)

    def write_vintage(self, path: Path, payload: dict[str, Any]) -> None:
        self._atomic_write(path, _dumps(payload))

    def write_index(self, path: Path, payload: dict[str, Any]) -> None:
        self._atomic_write(path, _dumps(payload))

    def write_marker(self, path: Path, payload: dict[str, Any]) -> None:
        self._atomic_write(path, _dumps(payload))

    def append_audit(self, path: Path, payload: dict[str, Any]) -> None:
        prior = path.read_bytes() if path.is_file() else b""
        line = (json.dumps(payload, sort_keys=True, allow_nan=False) + "\n").encode()
        self._atomic_write(path, prior + line)

    def quarantine(self, path: Path, data: bytes) -> None:
        if not path.is_file():
            self._atomic_write(path, data)


class _Journal:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.entries: list[tuple[Path, bytes | None]] = []

    def note(self, path: Path) -> None:
        self.entries.append((path, path.read_bytes() if path.is_file() else None))

    def rollback(self) -> None:
        for path, prior in reversed(self.entries):
            if prior is None:
                path.unlink(missing_ok=True)
            else:
                temporary = path.with_name(f".{path.name}.rollback")
                temporary.write_bytes(prior)
                os.replace(temporary, path)
        self.sweep()

    def sweep(self) -> None:
        if not self.root.exists():
            return
        for path in self.root.rglob("*"):
            if path.is_file() and path.name.startswith(".") and (
                path.name.endswith(".tmp") or path.name.endswith(".rollback")
            ):
                path.unlink(missing_ok=True)


class FailingAt:
    def __init__(self, inner: FilesystemStorage, boundary: str, *, fault: str) -> None:
        if boundary not in _BOUNDARIES or fault not in {"route_error", "os_error", "mid_write"}:
            raise ValueError(f"unknown failure injection: {boundary}/{fault}")
        self.inner = inner
        self.boundary = boundary
        self.fault = fault
        self.root = inner.root
        self._audit_failed = False

    def _guard(self, boundary: str, target: Path) -> None:
        if boundary != self.boundary:
            return
        if self.fault == "mid_write":
            temporary = target.with_name(f".{target.name}.tmp")
            temporary.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(b"partial")
            raise OSError(28, "No space left on device")
        if self.fault == "os_error":
            raise OSError(28, "No space left on device")
        raise PublishError(boundary, "injected failure")

    def read_json(self, path: Path, default: Any) -> Any:
        return self.inner.read_json(path, default)

    def write_raw(self, content: Path, check: Path, data: bytes, sha: str) -> None:
        self._guard("raw", content)
        self.inner.write_raw(content, check, data, sha)

    def write_vintage(self, path: Path, payload: dict[str, Any]) -> None:
        self._guard("store", path)
        self.inner.write_vintage(path, payload)

    def write_index(self, path: Path, payload: dict[str, Any]) -> None:
        self._guard("index", path)
        self.inner.write_index(path, payload)

    def write_marker(self, path: Path, payload: dict[str, Any]) -> None:
        self._guard("marker", path)
        self.inner.write_marker(path, payload)

    def append_audit(self, path: Path, payload: dict[str, Any]) -> None:
        if self.boundary == "audit" and not self._audit_failed:
            self._audit_failed = True
            self._guard("audit", path)
        self.inner.append_audit(path, payload)

    def quarantine(self, path: Path, data: bytes) -> None:
        self.inner.quarantine(path, data)


@dataclass(frozen=True)
class CaptureRecord:
    check_id: str
    vintage_id: str
    raw_sha256: str
    raw_bytes: int
    schema_hash: str
    retrieved_at: str
    request_count: int
    call_limit_remaining_after: int | None
    raw_path: str
    created_vintage: bool


class CfbdScheduleStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.storage = FilesystemStorage(self.root)

    def _content_path(self, sha: str) -> Path:
        return self.root / "raw" / "content" / f"{_safe_id(sha)}.json"

    def _check_path(self, check_id: str) -> Path:
        return self.root / "raw" / "checks" / f"{_safe_id(check_id)}.json"

    def _vintage_path(self, vintage_id: str) -> Path:
        return self.root / "vintages" / f"{_safe_id(vintage_id)}.json"

    def _index_path(self) -> Path:
        return self.root / "index.json"

    def _marker_path(self) -> Path:
        return self.root / "status_latest.json"

    def _ledger_path(self) -> Path:
        return self.root / "ledger.jsonl"

    def _quarantine_path(self, sha: str) -> Path:
        return self.root / "quarantine" / f"{_safe_id(sha)}.json"

    def _index(self, storage: Any | None = None) -> dict[str, Any]:
        active = storage or self.storage
        return active.read_json(
            self._index_path(),
            {"checks": [], "vintages": {}, "total_request_count": 0},
        )

    def load_vintage(self, vintage_id: str) -> dict[str, Any]:
        path = self._vintage_path(vintage_id)
        if not path.is_file():
            raise CaptureError("vintage_unknown", vintage_id)
        try:
            vintage = json.loads(path.read_text())
            index = self._index()
            metadata = index["vintages"][vintage_id]
            check = next(
                entry for entry in index["checks"] if entry["vintage_id"] == vintage_id
            )
            raw = self._content_path(metadata["raw_sha256"]).read_bytes()
        except (OSError, json.JSONDecodeError, KeyError, StopIteration) as exc:
            raise CaptureError("content_integrity_mismatch", vintage_id) from exc
        expected_sha = metadata["raw_sha256"]
        expected_bytes = check["raw_bytes"]
        if len(raw) != expected_bytes or _sha256(raw) != expected_sha:
            raise CaptureError("content_integrity_mismatch", vintage_id)
        rows = _parse(raw, check["year"])
        schema = _schema(rows)
        schema_hash = _schema_hash(rows)
        if (
            vintage.get("vintage_id") != vintage_id
            or vintage.get("raw_sha256") != expected_sha
            or vintage.get("raw_bytes") != expected_bytes
            or vintage.get("row_count") != len(rows)
            or vintage.get("schema") != schema
            or vintage.get("schema_hash") != schema_hash
            or vintage.get("games") != rows
        ):
            raise CaptureError("content_integrity_mismatch", vintage_id)
        return vintage

    def replay(self, check_id: str) -> dict[str, Any]:
        index = self._index()
        match = next(
            (entry for entry in index["checks"] if entry["check_id"] == check_id), None
        )
        if match is None:
            raise CaptureError("check_unknown", check_id)
        check_path = self._check_path(check_id)
        content_path = self._content_path(match["raw_sha256"])
        try:
            raw = check_path.read_bytes()
            content = content_path.read_bytes()
            vintage = self.load_vintage(match["vintage_id"])
        except (OSError, json.JSONDecodeError, CaptureError) as exc:
            raise CaptureError("content_integrity_mismatch", str(exc)) from exc
        expected_sha = match["raw_sha256"]
        expected_bytes = match["raw_bytes"]
        if (
            len(raw) != expected_bytes
            or _sha256(raw) != expected_sha
            or len(content) != expected_bytes
            or _sha256(content) != expected_sha
            or vintage.get("raw_sha256") != expected_sha
            or vintage.get("raw_bytes") != expected_bytes
            or vintage.get("vintage_id") != match["vintage_id"]
        ):
            raise CaptureError("content_integrity_mismatch", check_id)
        rows = _parse(raw, match["year"])
        return {"check_id": check_id, "raw_sha256": _sha256(raw), "games": rows}

    def partial_artifacts(self) -> list[str]:
        index = self._index()
        checks = {entry["check_id"] for entry in index["checks"]}
        vintages = set(index["vintages"])
        hashes = {value["raw_sha256"] for value in index["vintages"].values()}
        orphans: list[str] = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(self.root).as_posix()
            if path.name.startswith(".") and (
                path.name.endswith(".tmp") or path.name.endswith(".rollback")
            ):
                orphans.append(relative)
            elif path.parent.name == "checks" and path.stem not in checks:
                orphans.append(relative)
            elif path.parent.name == "content" and path.stem not in hashes:
                orphans.append(relative)
            elif path.parent.name == "vintages" and path.stem not in vintages:
                orphans.append(relative)
        return orphans

    def capture(
        self,
        *,
        fetcher: Any,
        api_key: str,
        year: int,
        storage: Any | None = None,
    ) -> CaptureRecord:
        _validate_year(year)
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("CFBD_API_KEY is required")
        descriptor = route_descriptor(year)
        try:
            result = fetcher.fetch(descriptor.request_url, api_key=api_key)
        except FetchError as exc:
            detail = scrub_message(exc.detail, api_key)
            self._record_failure(
                reason=exc.code,
                detail=detail,
                request_count=exc.request_count,
                year=year,
                storage=storage,
            )
            raise FetchError(exc.code, detail, request_count=exc.request_count) from None

        active = storage or self.storage
        raw = bytes(result.body)
        raw_sha = _sha256(raw)
        sanitized_final = _sanitize_url(result.final_url)
        try:
            self._validate_delivery(result, descriptor)
            if not result.content_type.lower().startswith("application/json"):
                raise CaptureError("content_type_unexpected", repr(result.content_type))
            retrieved_at = _require_aware_timestamp(result.retrieved_at)
            rows = _parse(raw, year)
        except CaptureError as exc:
            active.quarantine(self._quarantine_path(raw_sha), raw)
            self._record_failure(
                reason=exc.code,
                detail=exc.detail,
                request_count=result.request_count,
                year=year,
                raw_sha256=raw_sha,
                delivered_from=sanitized_final,
                storage=active,
            )
            raise CaptureError(exc.code, scrub_message(exc.detail, api_key)) from None

        remaining, accounting_quality = _parse_remaining(result.call_limit_remaining)
        return self._publish(
            rows=rows,
            raw=raw,
            raw_sha=raw_sha,
            retrieved_at=retrieved_at,
            provider_date=result.provider_date,
            delivered_from=sanitized_final,
            request_count=result.request_count,
            call_limit_remaining=remaining,
            accounting_quality=accounting_quality,
            year=year,
            storage=active,
        )

    def _validate_delivery(self, result: FetchResult, descriptor: RouteDescriptor) -> None:
        if (
            result.requested_url != descriptor.request_url
            or result.final_url != descriptor.request_url
        ):
            raise CaptureError(
                "source_identity_unexpected",
                f"delivery={_sanitize_url(result.final_url)}",
            )

    def _publish(
        self,
        *,
        rows: list[dict[str, Any]],
        raw: bytes,
        raw_sha: str,
        retrieved_at: str,
        provider_date: str | None,
        delivered_from: str,
        request_count: int,
        call_limit_remaining: int | None,
        accounting_quality: str,
        year: int,
        storage: Any,
    ) -> CaptureRecord:
        schema = _schema(rows)
        schema_hash = _schema_hash(rows)
        vintage_id = f"v-{raw_sha[:16]}"
        check_id = f"c-{re.sub(r'[^0-9A-Za-z]', '', retrieved_at)}-{raw_sha[:12]}"
        content_path = self._content_path(raw_sha)
        check_path = self._check_path(check_id)
        vintage_path = self._vintage_path(vintage_id)
        created_vintage = False
        descriptor = route_descriptor(year)
        provenance = {
            "source": "cfbd",
            "provider": descriptor.provider,
            "report_family": descriptor.report_family,
            "competition": descriptor.competition,
            "endpoint": descriptor.endpoint,
            "query": descriptor.query,
            "year": year,
            "raw_sha256": raw_sha,
            "raw_bytes": len(raw),
            "row_count": len(rows),
            "schema_hash": schema_hash,
            "parser_version": PARSER_VERSION,
            "openapi_version": OPENAPI_VERSION,
            "openapi_sha256": OPENAPI_SHA256,
        }
        journal = _Journal(self.root)
        try:
            index = self._index(storage)
            created_vintage = vintage_id not in index["vintages"]
            journal.note(content_path)
            journal.note(check_path)
            self._boundary(
                "raw",
                lambda: storage.write_raw(content_path, check_path, raw, raw_sha),
            )
            if created_vintage:
                journal.note(vintage_path)
                self._boundary(
                    "store",
                    lambda: storage.write_vintage(
                        vintage_path,
                        {
                            **provenance,
                            "vintage_id": vintage_id,
                            "retrieved_at": retrieved_at,
                            "provider_date": provider_date,
                            "delivered_from": delivered_from,
                            "schema": schema,
                            "games": rows,
                        },
                    ),
                )
            index["checks"] = [
                *index["checks"],
                {
                    "check_id": check_id,
                    "vintage_id": vintage_id,
                    "raw_sha256": raw_sha,
                    "raw_bytes": len(raw),
                    "retrieved_at": retrieved_at,
                    "request_count": request_count,
                    "year": year,
                },
            ]
            if created_vintage:
                index["vintages"] = {
                    **index["vintages"],
                    vintage_id: {
                        "raw_sha256": raw_sha,
                        "first_seen_at": retrieved_at,
                        "schema_hash": schema_hash,
                    },
                }
            index["total_request_count"] = index.get("total_request_count", 0) + request_count
            journal.note(self._index_path())
            self._boundary(
                "index", lambda: storage.write_index(self._index_path(), index)
            )
            previous = storage.read_json(self._marker_path(), {}) or {}
            marker = {
                **provenance,
                "status": "ok",
                "check_id": check_id,
                "vintage_id": vintage_id,
                "last_good_vintage_id": vintage_id,
                "retrieved_at": retrieved_at,
                "provider_date": provider_date,
                "delivered_from": delivered_from,
                "request_count": request_count,
                "call_limit_remaining_after": call_limit_remaining,
                "call_accounting_quality": accounting_quality,
                "last_checked": retrieved_at,
                "last_changed": (
                    retrieved_at if created_vintage else previous.get("last_changed", retrieved_at)
                ),
            }
            journal.note(self._marker_path())
            self._boundary(
                "marker", lambda: storage.write_marker(self._marker_path(), marker)
            )
            journal.note(self._ledger_path())
            self._boundary(
                "audit",
                lambda: storage.append_audit(
                    self._ledger_path(),
                    {
                        **provenance,
                        "status": "success",
                        "check_id": check_id,
                        "vintage_id": vintage_id,
                        "retrieved_at": retrieved_at,
                        "provider_date": provider_date,
                        "delivered_from": delivered_from,
                        "request_count": request_count,
                        "call_limit_remaining_after": call_limit_remaining,
                        "call_accounting_quality": accounting_quality,
                        "created_vintage": created_vintage,
                    },
                ),
            )
        except (PublishError, CaptureError) as exc:
            journal.rollback()
            reason = (
                f"publish_failed:{exc.boundary}"
                if isinstance(exc, PublishError)
                else exc.code
            )
            try:
                self._record_failure(
                    reason=reason,
                    detail=str(exc),
                    request_count=request_count,
                    year=year,
                    raw_sha256=raw_sha,
                    delivered_from=delivered_from,
                    boundary=exc.boundary if isinstance(exc, PublishError) else None,
                    storage=FilesystemStorage(self.root),
                )
            except Exception:  # noqa: BLE001 - never mask the named publication error
                pass
            raise
        return CaptureRecord(
            check_id=check_id,
            vintage_id=vintage_id,
            raw_sha256=raw_sha,
            raw_bytes=len(raw),
            schema_hash=schema_hash,
            retrieved_at=retrieved_at,
            request_count=request_count,
            call_limit_remaining_after=call_limit_remaining,
            raw_path=check_path.relative_to(self.root).as_posix(),
            created_vintage=created_vintage,
        )

    def _boundary(self, name: str, write: Any) -> Any:
        try:
            return write()
        except PublishError:
            raise
        except OSError as exc:
            raise PublishError(name, f"{type(exc).__name__}: {exc}") from exc

    def _record_failure(
        self,
        *,
        reason: str,
        detail: str,
        request_count: int,
        year: int,
        raw_sha256: str | None = None,
        delivered_from: str | None = None,
        boundary: str | None = None,
        storage: Any | None = None,
    ) -> None:
        active = storage or self.storage
        descriptor = route_descriptor(year)
        payload = {
            "status": "failed",
            "reason": reason,
            "detail": scrub_message(detail),
            "request_count": request_count,
            "raw_sha256": raw_sha256,
            "source": "cfbd",
            "provider": descriptor.provider,
            "report_family": descriptor.report_family,
            "competition": descriptor.competition,
            "endpoint": descriptor.endpoint,
            "query": descriptor.query,
            "year": year,
            "delivered_from": delivered_from,
            "parser_version": PARSER_VERSION,
            "openapi_version": OPENAPI_VERSION,
            "openapi_sha256": OPENAPI_SHA256,
        }
        if boundary is not None:
            payload["boundary"] = boundary
        active.append_audit(self._ledger_path(), payload)
