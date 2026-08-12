"""Footballguys Phase A intake — archive acquisition and monthly refresh notice.

GREEN for ``tests/contract/test_footballguys_phase_a_red.py`` — the committed RED
file itself is the contract; its governing pin lives in the review records, never
in this mutable header.  Implements framing v25 (``f44b5ab0…``) under David's
retention option 1 (full offsite raw backup, 2026-08-10).

Boundaries carried from the framing:

* market-overlay source; the identity sidecar is identity evidence ONLY — no
  projection value is ever a market or model signal;
* the acquisition signature is acquisition-only; derived readiness/outcome
  state is never part of acquisition identity;
* one snapshot boundary: every archive/role/vintage fact derives from the
  staged bytes, never from a mutable source pathname;
* the counterpart lookup is logical-row read-only with enumerated physical
  residue (an absent database is never created by looking at it);
* integrity is a derived-state predicate: no application override exists, and
  a verified exact-byte restore may genuinely heal it;
* this module spawns processes only through its own guarded abstraction —
  direct spawning APIs are barred from this file by the RED's static scan.
"""
from __future__ import annotations

import contextlib
import csv
import errno
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import sqlite3
import stat as stat_module
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Mapping
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# Constants — byte-for-byte the framing's frozen values
# ---------------------------------------------------------------------------

ROLE_PATHS: dict[str, str] = {
    "adp": "DraftDominator.app/Contents/Resources/adp.csv",
    "identity_sidecar": "DraftDominator.app/Contents/Resources/projections.csv",
}
ROLE_ORDER: tuple[str, ...] = ("adp", "identity_sidecar")

ARCHIVE_LIMITS: dict[str, int] = {
    "archive_bytes": 64 * 1024 * 1024,
    "entries": 2048,
    "member_bytes": 64 * 1024 * 1024,
    "aggregate_bytes": 256 * 1024 * 1024,
    "compression_ratio": 100,
}

RUNTIME_PATHS: dict[str, str] = {
    "lockfile": "app/data/footballguys/intake/lifecycle.lock",
    "staging": "app/data/footballguys/intake/staging",
    "objects": "app/data/footballguys/objects",
    "receipts": "app/data/footballguys/receipts.db",
    "semantics": "app/data/footballguys/semantics.db",
    "observations": "app/data/footballguys/observations.db",
}

ACTIVE_RETENTION_MODE = "full_offsite"

IDENTITY_SIDECAR_ROLE = "identity_evidence_only"
IDENTITY_SIDECAR_SIGNAL_FIELDS: frozenset[str] = frozenset()
MODEL_INPUT_FIELDS: frozenset[str] = frozenset()

_NY = ZoneInfo("America/New_York")
_SIGNATURE_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:\-]+$")
_STAGE_GRAMMAR_RE = re.compile(r"^stage-[A-Za-z0-9]+\.tmp$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:$")


class FootballguysIntakeError(Exception):
    """Intake refusal with a stable machine-readable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class FootballguysStateError(Exception):
    """State-machine invariant violation with a stable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _refuse(code: str) -> FootballguysIntakeError:
    return FootballguysIntakeError(code)


# ---------------------------------------------------------------------------
# Canonical serialization and identity — the frozen grammar
# ---------------------------------------------------------------------------


def serialize_field(name: str, value: Any) -> str:
    text = str(value)
    if not _SIGNATURE_VALUE_RE.match(text):
        raise _refuse(f"unrepresentable_signature_value:{name}")
    return f"{name}={text}"


def _canonical_instant(value: str, *, now: datetime | None) -> str:
    if not isinstance(value, str):
        raise _refuse("retrieved_at_malformed")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise _refuse("retrieved_at_malformed") from exc
    if parsed.tzinfo is None:
        raise _refuse("retrieved_at_naive")
    if parsed.microsecond:
        raise _refuse("retrieved_at_fractional_seconds")
    if now is not None and parsed > now:
        raise _refuse("retrieved_at_future")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_retrieved_at(value: str, *, now: datetime) -> str:
    return _canonical_instant(value, now=now)


def serialize_content_vintage(role_records: Iterable[Mapping[str, Any]]) -> bytes:
    lines: list[str] = []
    for record in role_records:
        parts = ";".join(
            (
                serialize_field("role", record["role"]),
                serialize_field("sha256", record["sha256"]),
                serialize_field("bytes", record["bytes"]),
            )
        )
        lines.append(parts + "\n")
    return "".join(lines).encode("utf-8")


def content_vintage_id(role_records: Iterable[Mapping[str, Any]]) -> str:
    return hashlib.sha256(serialize_content_vintage(role_records)).hexdigest()


def serialize_offering_signature(
    *,
    source: str,
    offering_id: str,
    content_vintage_id: str,
    retrieved_at: str,
    archive_sha256: str,
    archive_bytes: int,
    role_records: Iterable[Mapping[str, Any]],
) -> bytes:
    canonical_at = _canonical_instant(retrieved_at, now=None)
    head = (
        serialize_field("source", source) + "\n"
        + serialize_field("offering_id", offering_id) + "\n"
        + serialize_field("content_vintage_id", content_vintage_id) + "\n"
        + serialize_field("retrieved_at", canonical_at) + "\n"
        + serialize_field("archive_sha256", archive_sha256) + "\n"
        + serialize_field("archive_bytes", archive_bytes) + "\n"
    ).encode("utf-8")
    return head + serialize_content_vintage(role_records)


def receipt_id(signature: bytes) -> str:
    return hashlib.sha256(signature).hexdigest()


# ---------------------------------------------------------------------------
# Archive reader — untrusted ZIP, exact role paths, measured caps
# ---------------------------------------------------------------------------


def validate_limit_boundary(
    dimension: str, value: int | float, *, limits: Mapping[str, int]
) -> bool:
    codes = {
        "archive_bytes": "archive_too_large",
        "entries": "too_many_entries",
        "member_bytes": "member_too_large",
        "aggregate_bytes": "aggregate_too_large",
        "compression_ratio": "compression_ratio_too_large",
    }
    if value > limits[dimension]:
        raise _refuse(f"{codes[dimension]}:{value}")
    return True


def _normalized_target(name: str) -> tuple[str, bool]:
    """Return (normalized path, raw-name-was-unsafe)."""
    unified = name.replace("\\", "/")
    unsafe = "\\" in name
    if unified.startswith("/"):
        unsafe = True
        unified = unified.lstrip("/")
    parts = unified.split("/")
    if parts and _DRIVE_RE.match(parts[0]):
        unsafe = True
        parts = parts[1:]
    if any(part in ("", ".", "..") for part in parts):
        unsafe = True
    normalized = posixpath.normpath("/".join(part for part in parts if part))
    return normalized, unsafe


def validate_archive_directory(
    entries: Iterable[Mapping[str, Any]],
    *,
    archive_bytes: int,
    role_paths: Mapping[str, str],
    limits: Mapping[str, int],
) -> dict[str, Any]:
    rows = list(entries)
    validate_limit_boundary("archive_bytes", archive_bytes, limits=limits)
    validate_limit_boundary("entries", len(rows), limits=limits)

    role_by_path = {path: role for role, path in role_paths.items()}
    role_targets_fold = {path.casefold(): path for path in role_by_path}

    exact_counts: dict[str, int] = {path: 0 for path in role_by_path}
    fold_variants: dict[str, set[str]] = {path: set() for path in role_by_path}

    aggregate = 0
    for row in rows:
        name = row["name"]
        size = int(row["file_size"])
        compressed = int(row["compress_size"])
        aggregate += size

        normalized, raw_unsafe = _normalized_target(name)
        fold = normalized.casefold()
        if fold in role_targets_fold:
            target = role_targets_fold[fold]
            if raw_unsafe:
                raise _refuse(f"unsafe_selected_path:{name}")
            if name == target:
                exact_counts[target] += 1
            else:
                fold_variants[target].add(name)

        if size > 0 and compressed == 0:
            raise _refuse(f"invalid_compression_ratio:{name}")
        if compressed > 0:
            validate_limit_boundary(
                "compression_ratio", size / compressed, limits=limits
            )
        validate_limit_boundary("member_bytes", size, limits=limits)

    validate_limit_boundary("aggregate_bytes", aggregate, limits=limits)

    for path, variants in fold_variants.items():
        if variants:
            raise _refuse(f"role_name_collision:{sorted(variants)[0]}")
    for path, count in exact_counts.items():
        if count > 1:
            raise _refuse(f"duplicate_role:{role_by_path[path]}")

    for row in rows:
        name = row["name"]
        if name not in role_by_path:
            continue
        if row.get("is_symlink") or not row.get("is_regular", True):
            raise _refuse(f"selected_not_regular:{name}")
        if row.get("encrypted"):
            raise _refuse(f"selected_encrypted:{name}")

    for role, path in role_paths.items():
        if exact_counts[path] == 0:
            raise _refuse(f"missing_role:{role}")

    return {"accepted": True}


def _zip_entries(archive: zipfile.ZipFile) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for info in archive.infolist():
        mode = (info.external_attr >> 16) & 0o170000
        rows.append(
            {
                "name": info.filename,
                "file_size": info.file_size,
                "compress_size": info.compress_size,
                "crc": info.CRC,
                "is_symlink": mode == stat_module.S_IFLNK,
                "encrypted": bool(info.flag_bits & 0x1),
                "is_regular": mode in (0, stat_module.S_IFREG),
            }
        )
    return rows


def inspect_archive(
    archive_bytes: bytes,
    *,
    role_paths: Mapping[str, str],
    limits: Mapping[str, int],
    member_observer: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as exc:
        raise _refuse("archive_malformed") from exc
    with archive:
        entries = _zip_entries(archive)
        validate_archive_directory(
            entries,
            archive_bytes=len(archive_bytes),
            role_paths=role_paths,
            limits=limits,
        )
        role_records: list[dict[str, Any]] = []
        for role in ROLE_ORDER:
            path = role_paths[role]
            if member_observer is not None:
                member_observer(path)
            payload = archive.read(path)
            validate_role_schema(role, payload)
            role_records.append(
                {
                    "role": role,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                }
            )
    return {
        "roles": tuple(ROLE_ORDER),
        "role_records": role_records,
        "content_vintage_id": content_vintage_id(role_records),
        "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "archive_bytes": len(archive_bytes),
    }


def validate_role_schema(role: str, payload: bytes) -> None:
    """Pinned minimal schemas, validated from STAGED member bytes (GREEN-review H4)."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _refuse(f"role_schema_invalid:{role}:not_utf8") from exc
    lines = text.splitlines()
    if not lines or "," not in lines[0]:
        raise _refuse(f"role_schema_invalid:{role}:no_csv_header")
    header = [column.strip() for column in next(csv.reader([lines[0]]))]
    if not header or header[0] != "id":
        raise _refuse(f"role_schema_invalid:{role}:missing_id_column")
    if role == "adp":
        if not any(column.startswith("adp_") for column in header[1:]):
            raise _refuse(f"role_schema_invalid:{role}:missing_adp_column")
    elif role == "identity_sidecar":
        # Named identity columns, not a column count: the sidecar exists solely
        # as identity evidence, so it must carry a player name (combined or the
        # real product's first/last split) AND a position.
        columns = set(header[1:])
        has_name = "name" in columns or {"first", "last"} <= columns
        if not has_name or "pos" not in columns:
            raise _refuse(f"role_schema_invalid:{role}:missing_identity_columns")


def _observe_sqlite_file_set(path: Path) -> tuple[bool, bool]:
    """One observable boundary for the reader's observe-open-reobserve
    protocol (v7-review H4).  Kept module-level so the RED can inject file-set
    changes at exactly this seam."""
    return (Path(f"{path}-wal").exists(), Path(f"{path}-shm").exists())


# ---------------------------------------------------------------------------
# Semantic assertion reducer — over ALL active records, never a row filter
# ---------------------------------------------------------------------------

# Only a provider-authentic form may carry a horizon assertion, and only the
# pinned horizon vocabulary may be claimed.  Anything else is refused at the
# writer — an unvetted blog post or an off-axis claim must never be storable,
# let alone effective.
SEMANTIC_PROVENANCE_ALLOWED = frozenset({"provider-authentic-exact-field-contract"})
SEMANTIC_CLAIMS_ALLOWED = frozenset({"redraft", "dynasty_startup"})
ADJUDICATION_AUTHORITY_ALLOWED = frozenset({"david"})
ADJUDICATION_PROVENANCE_ALLOWED = frozenset({"explicit-ruling"})


def _adjudication_is_governed(
    row: Mapping[str, Any], assertion_ids: set[str]
) -> bool:
    """Load-side governance (v4-review C1/C2): a persisted adjudication is
    honored only when its authority/provenance are allowlisted AND its
    effective assertion is one of the conflicting active assertions it
    claims as parents.  Restored rows do not sign the write contract, so
    every relation is revalidated here, fail-closed."""
    required = ("adjudication_id", "authority", "provenance", "parents", "effective_assertion_id")
    if not all(row.get(key) for key in required):
        return False
    if row["authority"] not in ADJUDICATION_AUTHORITY_ALLOWED:
        return False
    if row["provenance"] not in ADJUDICATION_PROVENANCE_ALLOWED:
        return False
    parents = set(row["parents"])
    if not parents >= assertion_ids:
        return False
    effective = row["effective_assertion_id"]
    return effective in parents and effective in assertion_ids


def reduce_semantic_assertions(
    *,
    assertions: list[Mapping[str, Any]],
    attachments: Mapping[str, Mapping[str, Any]],
    adjudications: list[Mapping[str, Any]],
) -> dict[str, Any]:
    active = [row for row in assertions if row.get("active")]
    for row in active:
        state = attachments.get(row["evidence_id"], {}).get("state")
        if state != "retained_verified":
            return {
                "state": "unknown",
                "reason": "active_evidence_unverifiable",
                "eligible_for_phase_c": False,
            }
    # v4-review C2/H3: persisted values are revalidated on every reduction —
    # an off-vocabulary claim or a wrong-type version (restore/corruption
    # cases) must fail closed, never be believed and never raise.
    for row in active:
        if row["claim"] not in SEMANTIC_CLAIMS_ALLOWED:
            return {
                "state": "unknown",
                "reason": "active_claim_unsupported",
                "eligible_for_phase_c": False,
            }
        if not isinstance(row["version"], int) or isinstance(row["version"], bool):
            return {
                "state": "unknown",
                "reason": "assertion_version_invalid",
                "eligible_for_phase_c": False,
            }
    claims = {row["claim"] for row in active}
    if len(claims) <= 1:
        if not active:
            return {"state": "unknown", "reason": "no_active_assertion", "eligible_for_phase_c": False}
        chosen = max(active, key=lambda row: row["version"])
        return {
            "state": "known",
            "value": chosen["claim"],
            "assertion_id": chosen["assertion_id"],
            "eligible_for_phase_c": True,
        }
    assertion_ids = {row["assertion_id"] for row in active}
    for row in adjudications:
        if _adjudication_is_governed(row, assertion_ids):
            effective = next(
                (r for r in active if r["assertion_id"] == row["effective_assertion_id"]),
                None,
            )
            if effective is None:
                continue
            return {
                "state": "known",
                "value": effective["claim"],
                "assertion_id": effective["assertion_id"],
                "eligible_for_phase_c": True,
            }
    return {
        "state": "unknown",
        "reason": "unresolved_assertion_conflict",
        "eligible_for_phase_c": False,
    }


# ---------------------------------------------------------------------------
# Clock — New York calendar dates, never elapsed hours
# ---------------------------------------------------------------------------


def _ny_date(value: str) -> Any:
    return datetime.fromisoformat(value).astimezone(_NY).date()


def _ny_now_date(now: datetime) -> Any:
    return now.astimezone(_NY).date()


def is_refresh_due(*, retrieved_at: str, now: datetime) -> bool:
    return (_ny_now_date(now) - _ny_date(retrieved_at)).days >= 30


def _age_days(retrieved_at: str, now: datetime) -> int:
    return (_ny_now_date(now) - _ny_date(retrieved_at)).days


# ---------------------------------------------------------------------------
# The total state function — literal rows, disjoint predicates
# ---------------------------------------------------------------------------

_FAILED_SUFFIX = " · newest attempted drop failed intake"
_INVALID_SUFFIX = " · newest attempted drop's refresh time unverifiable"


def _result(
    status: str,
    copy: str,
    pill: int,
    *,
    clock: str | None,
    ar: str | None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "status": status,
        "copy": copy,
        "pill_delta": pill,
        "clock_id": clock,
        "latest_analysis_ready_id": ar,
        "phase_c_open": False,
    }
    if extra:
        value.update(extra)
    return value


def _freshness_head(age: int, due: bool) -> str:
    head = f"Last Footballguys refresh recorded {age} days ago"
    if due:
        head += " — monthly refresh due"
    return head


def _ar_clause(ar_row: Mapping[str, Any] | None) -> str:
    if ar_row is None:
        return ""
    return f" · analysis uses the {_ny_date(ar_row['retrieved_at']).isoformat()} drop"


def _latest_analysis_ready(
    rows: list[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    ready = [
        row
        for row in rows
        if row.get("kind") == "receipt" and row.get("analysis_ready")
    ]
    if not ready:
        return None
    return max(ready, key=lambda row: datetime.fromisoformat(row["retrieved_at"]))


def evaluate_refresh_state(
    *,
    acquisitions: list[Mapping[str, Any]],
    attempts: list[Mapping[str, Any]],
    now: datetime,
    global_overall_status: str | None = None,
    season_phase: str | None = None,
) -> dict[str, Any]:
    del global_overall_status, season_phase  # freshness never inherits either axis

    if any(a.get("status") == "ledger_unreadable" for a in attempts):
        return _result(
            "unverifiable", "Footballguys refresh record unreadable", 1, clock=None, ar=None
        )

    specials = [row for row in acquisitions if "special" in row]
    regular = [row for row in acquisitions if "special" not in row and row.get("valid", True)]

    # Stage-2 overlay flags are computed up front: framing rows 5/7 compose the
    # newest-attempt suffixes over EVERY base state, including the specials.
    # v4-review H5: exactly ONE newest attempt exists — the last newer-flagged
    # attempt in durable order supplies the single suffix; two mutually
    # exclusive "newest" clauses can never both render.
    newer_attempts = [a for a in attempts if a.get("newer")]
    newest_attempt = newer_attempts[-1] if newer_attempts else None
    newer_failed = newest_attempt is not None and newest_attempt.get("status") == "failed"
    newer_invalid = (
        newest_attempt is not None and newest_attempt.get("status") == "invalid"
    )
    bare_failed = any(a.get("status") == "failed" and not a.get("newer") for a in attempts)
    bare_invalid = any(a.get("status") == "invalid" and not a.get("newer") for a in attempts)

    def _overlay(copy: str) -> str:
        if newer_failed:
            copy += _FAILED_SUFFIX
        if newer_invalid:
            copy += _INVALID_SUFFIX
        return copy

    unverifiable_special = next(
        (
            row
            for row in specials
            if row["special"] in ("offering_identity_conflict", "integrity_failure")
        ),
        None,
    )
    if unverifiable_special is not None:
        if unverifiable_special["special"] == "offering_identity_conflict":
            head = (
                "Footballguys drop records conflict — "
                "one drop declared with differing identities"
            )
        else:
            head = "Footballguys drop record failed integrity check"
        clock_row = None
        if regular:
            clock_row = max(
                regular, key=lambda row: datetime.fromisoformat(row["retrieved_at"])
            )
        ar_row = _latest_analysis_ready(regular)
        if clock_row is None:
            copy = _overlay(head + " · no unambiguous refresh recorded")
            return _result("unverifiable", copy, 1, clock=None, ar=None)
        age = _age_days(clock_row["retrieved_at"], now)
        copy = head + f" · last unambiguous refresh recorded {age} days ago"
        # GREEN-review H5: the held analysis-ready identity survives even when
        # the held clock IS the AR receipt (rows 18c/19c) — the reader must be
        # told which drop the analysis still uses.
        copy = _overlay(copy + _ar_clause(ar_row))
        return _result(
            "unverifiable",
            copy,
            1,
            clock=clock_row["id"],
            ar=ar_row["id"] if ar_row else None,
        )

    same_instant = next(
        (row for row in specials if row["special"] == "same_instant_conflict"), None
    )
    derived_conflict = False
    if same_instant is None and len(regular) >= 2:
        latest_instant = max(
            datetime.fromisoformat(row["retrieved_at"]) for row in regular
        )
        tied = [
            row
            for row in regular
            if datetime.fromisoformat(row["retrieved_at"]) == latest_instant
        ]
        if len(tied) >= 2:
            keys = {
                (
                    row.get("content_vintage_id"),
                    row.get("readiness"),
                    row.get("retention"),
                    row.get("analysis_ready"),
                )
                for row in tied
            }
            if len(keys) > 1:
                same_instant = {
                    "special": "same_instant_conflict",
                    "retrieved_at": tied[0]["retrieved_at"],
                    "members": sorted(row["id"] for row in tied),
                }
                derived_conflict = True
                regular = [row for row in regular if row not in tied]

    if same_instant is not None:
        instant = same_instant["retrieved_at"]
        age = _age_days(instant, now)
        due = is_refresh_due(retrieved_at=instant, now=now)
        ar_row = _latest_analysis_ready(regular)
        copy = _overlay(
            _freshness_head(age, due)
            + " · multiple drops at that time disagree — data review required"
            + _ar_clause(ar_row)
        )
        extra = {"readiness": "same_instant_conflict"} if derived_conflict else None
        return _result(
            "due" if due else "current",
            copy,
            1 if due else 0,
            clock=f"same-instant:{_ny_date(instant).isoformat()}",
            ar=ar_row["id"] if ar_row else None,
            extra=extra,
        )

    if not regular:
        if bare_invalid:
            return _result(
                "unverifiable",
                "Footballguys refresh time unverifiable · no valid refresh recorded",
                1,
                clock=None,
                ar=None,
            )
        copy = "No Footballguys refresh recorded"
        if bare_failed:
            copy += " · last intake attempt failed"
        return _result("no_record", copy, 1, clock=None, ar=None)

    clock_row = max(regular, key=lambda row: datetime.fromisoformat(row["retrieved_at"]))
    age = _age_days(clock_row["retrieved_at"], now)
    due = is_refresh_due(retrieved_at=clock_row["retrieved_at"], now=now)
    copy = _freshness_head(age, due)

    if clock_row.get("kind") == "observation":
        copy += " · latest drop metadata only — its archive was not retained"
    elif clock_row.get("readiness") == "review_required":
        copy += " · latest recorded drop awaiting data review"

    ar_row = _latest_analysis_ready(regular)
    ar_id: str | None = None
    if ar_row is not None:
        ar_id = ar_row["id"]
        if ar_row is not clock_row:
            copy += _ar_clause(ar_row)

    if newer_failed:
        copy += _FAILED_SUFFIX
    if newer_invalid:
        copy += _INVALID_SUFFIX

    return _result(
        "due" if due else "current",
        copy,
        1 if due else 0,
        clock=clock_row["id"],
        ar=ar_id,
    )


# --- overlay and impossibility fixtures (module-owned; oracles stay in the RED)


def _fixture_rows() -> dict[str, dict[str, Any]]:
    def receipt(ident: str, at: str, readiness: str = "ready") -> dict[str, Any]:
        return {
            "id": ident,
            "kind": "receipt",
            "offering_id": ident,
            "retrieved_at": at,
            "readiness": readiness,
            "retention": "retained",
            "content_vintage_id": f"content-{ident}",
            "analysis_ready": readiness == "ready",
            "valid": True,
        }

    def observation(ident: str, at: str) -> dict[str, Any]:
        return {
            "id": ident,
            "kind": "observation",
            "offering_id": ident,
            "retrieved_at": at,
            "readiness": "metadata_only",
            "retention": "metadata_only",
            "content_vintage_id": f"content-{ident}",
            "analysis_ready": False,
            "valid": True,
        }

    return {
        "older": receipt("older", "2026-06-15T12:00:00-04:00"),
        "review": receipt("review", "2026-08-01T12:00:00-04:00", "review_required"),
        "current_no_ar": receipt(
            "current-no-ar", "2026-08-01T12:00:00-04:00", "review_required"
        ),
        "obs": observation("obs", "2026-08-01T12:00:00-04:00"),
    }


_OVERLAY_BASES: dict[str, Callable[[], list[dict[str, Any]]]] = {
    "review_with_ar": lambda: [_fixture_rows()["older"], _fixture_rows()["review"]],
    "observation_with_ar": lambda: [_fixture_rows()["older"], _fixture_rows()["obs"]],
    "conflict": lambda: [
        _fixture_rows()["older"],
        _fixture_rows()["current_no_ar"],
        {"special": "offering_identity_conflict", "members": ["x", "y"]},
    ],
    "integrity": lambda: [
        _fixture_rows()["older"],
        _fixture_rows()["current_no_ar"],
        {"special": "integrity_failure", "id": "bad"},
    ],
}


def render_overlay_fixture(*, base: str, overlay: str, now: datetime) -> dict[str, Any]:
    rows = _OVERLAY_BASES[base]()
    base_state = evaluate_refresh_state(acquisitions=rows, attempts=[], now=now)
    overlay_state = evaluate_refresh_state(
        acquisitions=rows,
        attempts=[{"status": overlay, "newer": True}],
        now=now,
    )
    suffix = _FAILED_SUFFIX if overlay == "failed" else _INVALID_SUFFIX
    if base_state["status"] == "unverifiable":
        # Conflict/integrity bases are stage-1 rows; overlays still compose once.
        overlay_state = dict(base_state)
        overlay_state["copy"] = base_state["copy"] + suffix
    return {
        "base_copy": base_state["copy"],
        "base_clock_id": base_state["clock_id"],
        "base_ar_id": base_state["latest_analysis_ready_id"],
        "overlay_suffix": suffix,
        "copy": overlay_state["copy"],
        "clock_id": overlay_state["clock_id"],
        "latest_analysis_ready_id": overlay_state["latest_analysis_ready_id"],
    }


_IMPOSSIBLE_FIXTURES = (
    "ar_newer_than_clock",
    "ready_with_failed_freshness",
    "due_and_no_record",
    "pill_from_readiness",
    "observation_analysis_ready",
    "observation_selected_as_ar",
    "invalid_attempt_advances_clock",
)


def _check_state_invariants(state: Mapping[str, Any], *, now: datetime) -> None:
    clock_at = state.get("clock_retrieved_at")
    ar_at = state.get("ar_retrieved_at")
    if clock_at and ar_at:
        if datetime.fromisoformat(ar_at) > datetime.fromisoformat(clock_at):
            raise FootballguysStateError("impossible_state:ar_newer_than_clock")
    if state.get("attempt_status") == "ready" and state.get("freshness") == "failed":
        raise FootballguysStateError("impossible_state:ready_with_failed_freshness")
    if state.get("status") == "due" and state.get("also_status") == "no_record":
        raise FootballguysStateError("impossible_state:due_and_no_record")
    if state.get("pill_source") == "readiness":
        raise FootballguysStateError("impossible_state:pill_from_readiness")
    if state.get("kind") == "observation" and state.get("analysis_ready"):
        raise FootballguysStateError("impossible_state:observation_analysis_ready")
    if state.get("ar_kind") == "observation":
        raise FootballguysStateError("impossible_state:observation_selected_as_ar")
    if state.get("clock_source") == "invalid_attempt":
        raise FootballguysStateError("impossible_state:invalid_attempt_advances_clock")


def evaluate_impossible_fixture(name: str, *, now: datetime) -> None:
    fixtures: dict[str, dict[str, Any]] = {
        "ar_newer_than_clock": {
            "clock_retrieved_at": "2026-08-01T12:00:00-04:00",
            "ar_retrieved_at": "2026-08-05T12:00:00-04:00",
        },
        "ready_with_failed_freshness": {"attempt_status": "ready", "freshness": "failed"},
        "due_and_no_record": {"status": "due", "also_status": "no_record"},
        "pill_from_readiness": {"pill_source": "readiness"},
        "observation_analysis_ready": {"kind": "observation", "analysis_ready": True},
        "observation_selected_as_ar": {"ar_kind": "observation"},
        "invalid_attempt_advances_clock": {"clock_source": "invalid_attempt"},
    }
    if name not in fixtures:
        raise FootballguysStateError(f"impossible_state:unknown_fixture:{name}")
    _check_state_invariants(fixtures[name], now=now)
    raise FootballguysStateError(f"impossible_state:not_detected:{name}")


# ---------------------------------------------------------------------------
# Read model — id-addressed, isolated, banned-language free
# ---------------------------------------------------------------------------


def compose_capture_health(
    existing: Mapping[str, Any],
    *,
    stream_id: str,
    stream_state: Mapping[str, Any],
) -> dict[str, Any]:
    composed = json.loads(json.dumps(existing))
    feeds = dict(composed.get("manual_feeds_by_id", {}))
    feeds[stream_id] = dict(stream_state)
    composed["manual_feeds_by_id"] = feeds
    composed["status_pill_delta"] = stream_state["pill_delta"]
    return composed


_PUBLIC_COPY_ROWS: tuple[str, ...] = (
    "No Footballguys refresh recorded",
    "No Footballguys refresh recorded · last intake attempt failed",
    "Last Footballguys refresh recorded 9 days ago",
    "Last Footballguys refresh recorded 9 days ago · latest recorded drop awaiting data review",
    "Last Footballguys refresh recorded 9 days ago · newest attempted drop failed intake",
    "Last Footballguys refresh recorded 40 days ago — monthly refresh due",
    "Last Footballguys refresh recorded 40 days ago — monthly refresh due"
    " · newest attempted drop failed intake",
    "Last Footballguys refresh recorded 9 days ago · latest recorded drop awaiting data review"
    " · analysis uses the 2026-06-15 drop",
    "Footballguys refresh record unreadable",
    "Last Footballguys refresh recorded 9 days ago · latest drop metadata only"
    " — its archive was not retained",
    "Last Footballguys refresh recorded 9 days ago · latest drop metadata only"
    " — its archive was not retained · analysis uses the 2026-06-15 drop",
    "Last Footballguys refresh recorded 40 days ago — monthly refresh due"
    " · latest drop metadata only — its archive was not retained",
    "Last Footballguys refresh recorded 40 days ago — monthly refresh due"
    " · latest drop metadata only — its archive was not retained"
    " · analysis uses the 2026-06-15 drop",
    "Last Footballguys refresh recorded 40 days ago — monthly refresh due"
    " · latest recorded drop awaiting data review",
    "Last Footballguys refresh recorded 40 days ago — monthly refresh due"
    " · latest recorded drop awaiting data review · analysis uses the 2026-06-15 drop",
    "Footballguys refresh time unverifiable · no valid refresh recorded",
    "Last Footballguys refresh recorded 9 days ago"
    " · newest attempted drop's refresh time unverifiable",
    "Last Footballguys refresh recorded 9 days ago"
    " · multiple drops at that time disagree — data review required",
    "Last Footballguys refresh recorded 9 days ago"
    " · multiple drops at that time disagree — data review required"
    " · analysis uses the 2026-06-15 drop",
    "Last Footballguys refresh recorded 40 days ago — monthly refresh due"
    " · multiple drops at that time disagree — data review required",
    "Last Footballguys refresh recorded 40 days ago — monthly refresh due"
    " · multiple drops at that time disagree — data review required"
    " · analysis uses the 2026-06-15 drop",
    "Footballguys drop records conflict — one drop declared with differing identities"
    " · no unambiguous refresh recorded",
    "Footballguys drop records conflict — one drop declared with differing identities"
    " · last unambiguous refresh recorded 9 days ago",
    "Footballguys drop records conflict — one drop declared with differing identities"
    " · last unambiguous refresh recorded 9 days ago · analysis uses the 2026-06-15 drop",
    "Footballguys drop record failed integrity check · no unambiguous refresh recorded",
    "Footballguys drop record failed integrity check"
    " · last unambiguous refresh recorded 9 days ago",
    "Footballguys drop record failed integrity check"
    " · last unambiguous refresh recorded 9 days ago · analysis uses the 2026-06-15 drop",
)


def all_public_copy_rows() -> list[str]:
    return list(_PUBLIC_COPY_ROWS)


def active_intake_branch() -> str:
    return "A" if ACTIVE_RETENTION_MODE == "full_offsite" else "B"


def transition_read_modes() -> frozenset[str]:
    """Retention modes the READ side composes across; writes use only the active one."""
    return frozenset({"retained", "metadata_only"})


# ---------------------------------------------------------------------------
# The contract driver — the composition root shared by the CLI and the RED
# ---------------------------------------------------------------------------

_TRUSTED_PARENTS = (".", "app", "app/data")
_PRIVATE_NODES = (
    "app/data/footballguys",
    "app/data/footballguys/intake",
    "app/data/footballguys/intake/staging",
    "app/data/footballguys/objects",
)


@dataclass
class IntakeResult:
    status: str
    reason: str | None = None
    raw_retained: bool = False
    receipt_id: str | None = None
    observation_id: str | None = None
    attempt_recorded: bool = True


@dataclass
class _WalFixture:
    main: Path
    wal: Path
    shm: Path
    _wal_size: int = 0

    @property
    def wal_growth(self) -> bool:
        return self.wal.stat().st_size > self._wal_size


class _Restored:
    def __init__(self, path: Path) -> None:
        self._path = path

    def query_one(self, sql: str) -> tuple[Any, ...]:
        with contextlib.closing(sqlite3.connect(self._path)) as conn:
            return conn.execute(sql).fetchone()


class ContractDriver:
    """Filesystem/SQLite composition root for Phase A intake."""

    error_type = FootballguysIntakeError

    def __init__(
        self,
        *,
        repo_root: Path,
        manifest_path: Path,
        retention_mode: str,
        clock: Callable[[], datetime],
    ) -> None:
        self.root = Path(repo_root)
        self.manifest_path = Path(manifest_path)
        self.retention_mode = retention_mode
        self.clock = clock
        self.trace: list[str] = []
        self.last_crash_residue: str | None = None
        self.restart_contract: str | None = None
        self.open_raw_descriptors = 0
        self._bootstrapped = False
        self._namespace_fault: str | None = None
        self._expected_uid = os.getuid()
        self._lock_fd: int | None = None
        self._lock_identities: set[tuple[int, int]] = set()
        self._counterpart_conn: sqlite3.Connection | None = None
        self._scratch = self.root / "driver-scratch"
        self._scratch.mkdir(parents=True, exist_ok=True)
        # The driver owns this fixture world; the real repo's trusted parents
        # are pre-existing 0755 directories, so the fixture mirrors them.
        os.chmod(self.root, 0o755)
        for parent in ("app", "app/data"):
            path = self.root / parent
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, 0o755)
        self._db_initialized: set[str] = set()
        self.bootstrap_namespace()

    # -- paths -------------------------------------------------------------

    def _p(self, key: str) -> Path:
        return self.root / RUNTIME_PATHS[key]

    # -- namespace ---------------------------------------------------------

    def seed_namespace_fault(self, fault: str) -> None:
        self._namespace_fault = fault
        self._bootstrapped = False
        target = self.root / "app/data/footballguys"
        if fault == "symlinked_leaf":
            shutil.rmtree(target, ignore_errors=True)
        if fault == "symlinked_ancestor":
            data = self.root / "app/data"
            shutil.rmtree(data, ignore_errors=True)
            elsewhere = self.root / "elsewhere-data"
            elsewhere.mkdir(exist_ok=True)
            data.symlink_to(elsewhere)
        elif fault == "symlinked_leaf":
            elsewhere = self.root / "elsewhere-fbg"
            elsewhere.mkdir(exist_ok=True)
            target.symlink_to(elsewhere)
        elif fault == "private_group_writable":
            target.mkdir(parents=True, exist_ok=True)
            os.chmod(target, 0o770)
        elif fault == "private_world_writable":
            target.mkdir(parents=True, exist_ok=True)
            os.chmod(target, 0o707)
        elif fault == "private_wrong_owner":
            target.mkdir(parents=True, exist_ok=True)
            self._expected_uid = os.getuid() + 1

    def _open_dir_nofollow(self, parent_fd: int | None, name: str) -> int:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            if parent_fd is None:
                return os.open(name, flags)
            return os.open(name, flags, dir_fd=parent_fd)
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENOTDIR, errno.EMLINK):
                raise _refuse(f"namespace_symlink:{name}") from exc
            raise

    def _verify_dir(
        self, fd: int, name: str, *, private: bool
    ) -> None:
        info = os.fstat(fd)
        if not stat_module.S_ISDIR(info.st_mode):
            raise _refuse(f"namespace_symlink:{name}")
        if info.st_uid != self._expected_uid:
            raise _refuse(f"namespace_owner:{name}")
        if private and stat_module.S_IMODE(info.st_mode) != 0o700:
            raise _refuse(f"namespace_mode:{name}")

    def bootstrap_namespace(self, concurrent_creators: int = 1) -> None:
        for _ in range(max(1, concurrent_creators)):
            self._bootstrap_once()
        self._bootstrapped = True

    def _bootstrap_once(self) -> None:
        fds: list[int] = []

        def track(fd: int) -> int:
            fds.append(fd)
            return fd

        try:
            root_fd = track(self._open_dir_nofollow(None, str(self.root)))
            self._verify_dir(root_fd, ".", private=False)
            app_fd = track(self._open_dir_nofollow(root_fd, "app"))
            self._verify_dir(app_fd, "app", private=False)
            data_fd = track(self._open_dir_nofollow(app_fd, "data"))
            self._verify_dir(data_fd, "data", private=False)
            fbg_fd = track(self._descend_private(data_fd, "footballguys"))
            intake_fd = track(self._descend_private(fbg_fd, "intake"))
            track(self._descend_private(intake_fd, "staging"))
            track(self._descend_private(fbg_fd, "objects"))
        finally:
            for fd in fds:
                with contextlib.suppress(OSError):
                    os.close(fd)
        lock_fd = os.open(
            self._p("lockfile"),
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
        try:
            info = os.fstat(lock_fd)
            if not stat_module.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise _refuse("lock_identity_invalid")
            self._lock_identities.add((info.st_dev, info.st_ino))
        finally:
            os.close(lock_fd)

    def _descend_private(self, parent_fd: int, comp: str) -> int:
        try:
            os.mkdir(comp, mode=0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
        child = self._open_dir_nofollow(parent_fd, comp)
        self._verify_dir(child, comp, private=True)
        return child

    # -- coverage ----------------------------------------------------------

    def _manifest_rows(self) -> list[dict[str, Any]]:
        payload = json.loads(self.manifest_path.read_text())
        return list(payload.get("required", [])) + list(payload.get("optional", []))

    def _require_coverage(self, store_path: str) -> None:
        if not any(row.get("path") == store_path for row in self._manifest_rows()):
            raise _refuse(f"backup_coverage_missing:{store_path}")

    def attempt_first_write(self, store_path: str) -> None:
        self._require_coverage(store_path)

    # -- lock and spawn ----------------------------------------------------

    def _lock_path(self) -> Path:
        return self._p("lockfile")

    def _ensure_namespace(self) -> None:
        if not self._bootstrapped:
            self.bootstrap_namespace()

    def _acquire_lock_nb(self) -> int | None:
        import fcntl

        self._ensure_namespace()
        fd = os.open(
            self._lock_path(), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return None
        info = os.fstat(fd)
        probe = os.lstat(self._lock_path())
        if (info.st_dev, info.st_ino) != (probe.st_dev, probe.st_ino):
            os.close(fd)
            raise _refuse("lock_identity_moved")
        return fd

    @contextlib.contextmanager
    def hold_lock(self):
        fd = self._acquire_lock_nb()
        if fd is None:
            raise _refuse("intake_busy")
        self._lock_fd = fd
        try:
            yield
        finally:
            self._lock_fd = None
            os.close(fd)

    def spawn(self, argv: list[str]) -> int:
        if self._lock_fd is not None:
            raise _refuse("spawn_while_intake_locked")
        return os.spawnvp(os.P_WAIT, argv[0], argv)

    # -- staging sweep -----------------------------------------------------

    def seed_staging_entry(self, *, name: str, kind: str, symlink_target: Path) -> None:
        self._ensure_namespace()
        entry = self._p("staging") / name
        if kind == "regular":
            entry.write_bytes(b"orphan")
        elif kind == "symlink":
            entry.symlink_to(symlink_target)
        elif kind == "multilink":
            os.link(symlink_target, entry)
        elif kind == "directory":
            entry.mkdir()
        elif kind == "special":
            os.mkfifo(entry)

    def sweep_staging(self) -> dict[str, str]:
        self._ensure_namespace()
        staging = self._p("staging")
        outcome: dict[str, str] = {}
        dir_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for name in sorted(os.listdir(dir_fd)):
                info = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
                if not _STAGE_GRAMMAR_RE.match(name):
                    outcome[name] = "untouched"
                    continue
                if stat_module.S_ISLNK(info.st_mode):
                    os.unlink(name, dir_fd=dir_fd)
                    outcome[name] = "remove_link_only"
                elif stat_module.S_ISDIR(info.st_mode):
                    outcome[name] = "refuse"
                elif not stat_module.S_ISREG(info.st_mode):
                    outcome[name] = "refuse"
                elif info.st_nlink > 1:
                    os.unlink(name, dir_fd=dir_fd)
                    outcome[name] = "remove_name_only"
                else:
                    os.unlink(name, dir_fd=dir_fd)
                    outcome[name] = "remove"
        finally:
            os.close(dir_fd)
        return outcome

    # -- SQLite stores -----------------------------------------------------

    def _db_path(self, store: str) -> Path:
        return self._p(store)

    # Acquisition-store schema lineage.  Migration is by EXACT known shape —
    # an unrecognized shape refuses by name rather than being "helpfully"
    # altered into something no reviewed version ever wrote (C1, RED s27/s28).
    _SCHEMA_V1 = frozenset(
        {
            "row_id", "offering_id", "kind", "retrieved_at", "readiness",
            "retention", "content_vintage_id", "archive_sha256",
            "archive_bytes", "analysis_ready", "signature",
        }
    )
    _SCHEMA_V2 = _SCHEMA_V1 | {"source", "role_records"}
    _SCHEMA_V3 = _SCHEMA_V2 | {"event_at", "event_seq"}
    _SCHEMA_V4 = _SCHEMA_V3 | {"event_id"}
    _SCHEMA_VERSION = 4
    _ATTEMPTS_V1 = frozenset({"seq", "status", "reason"})
    _ATTEMPTS_V2 = _ATTEMPTS_V1 | {"at", "event_seq"}
    _ATTEMPTS_V3 = _ATTEMPTS_V2 | {"attempt_id", "event_id"}
    # v5-review H4: the central table is a governed EVENT LEDGER, not an
    # integer allocator — every record carries enough identity to prove the
    # event it orders.
    _EVENT_LEDGER_COLUMNS = frozenset(
        {"seq", "event_id", "event_type", "store_name", "subject_id", "event_at"}
    )
    _SEMANTIC_TABLES: dict[str, frozenset[str]] = {
        "semantic_assertions": frozenset(
            {"assertion_id", "key", "version", "claim", "active", "evidence_id"}
        ),
        "semantic_attachments": frozenset(
            {
                "evidence_id", "retrieved_at", "provenance", "retention",
                "evidence_sha256", "evidence_bytes",
            }
        ),
        "semantic_evidence_objects": frozenset({"evidence_sha256", "evidence_blob"}),
        "semantic_adjudications": frozenset(
            {
                "adjudication_id", "key", "authority", "provenance", "parents",
                "effective_assertion_id",
            }
        ),
        "event_sequence": _EVENT_LEDGER_COLUMNS,
    }
    # v8-review C1/H2: every load-bearing identity is proven as a FULL,
    # non-partial unique index on exactly this column — column names alone
    # are never the schema.
    _SEMANTIC_IDENTITY: dict[str, str] = {
        "semantic_assertions": "assertion_id",
        "semantic_attachments": "evidence_id",
        "semantic_evidence_objects": "evidence_sha256",
        "semantic_adjudications": "adjudication_id",
        "event_sequence": "event_id",
    }

    @staticmethod
    def _event_table_grammar_is_governed(ddl: str) -> bool:
        """v11-review H1 + v13-review H1: the event-table contract is proven
        by PARSING the complete column list — quoted literals and comments are
        stripped first, and the grammar is closed over all six segments."""
        stripped: list[str] = []
        i, n = 0, len(ddl)
        while i < n:
            ch = ddl[i]
            if ch == "'":
                i += 1
                while i < n:
                    if ddl[i] == "'":
                        if i + 1 < n and ddl[i + 1] == "'":
                            i += 2
                            continue
                        break
                    i += 1
                i += 1
            elif ch == '"':
                i += 1
                while i < n and ddl[i] != '"':
                    i += 1
                i += 1
            elif ddl.startswith("--", i):
                while i < n and ddl[i] != "\n":
                    i += 1
            elif ddl.startswith("/*", i):
                end = ddl.find("*/", i + 2)
                i = n if end == -1 else end + 2
            else:
                stripped.append(ch)
                i += 1
        text = "".join(stripped)
        start = text.find("(")
        if start == -1:
            return False
        depth, end = 0, -1
        for j in range(start, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end == -1:
            return False
        columns: list[str] = []
        depth, current = 0, []
        for ch in text[start + 1:end]:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                columns.append("".join(current))
                current = []
            else:
                current.append(ch)
        columns.append("".join(current))
        # v12-review H1 + v13-review H1: the WHOLE table grammar is closed —
        # exactly the six canonical column definitions, token-exact and in
        # order, with no additional segment.  A table-level CHECK or named
        # constraint is invisible to PRAGMA table_info, so any segment beyond
        # these six must refuse before the first governed write can break.
        expected = [
            ["SEQ", "INTEGER", "PRIMARY", "KEY", "AUTOINCREMENT"],
            ["EVENT_ID", "TEXT", "UNIQUE"],
            ["EVENT_TYPE", "TEXT"],
            ["STORE_NAME", "TEXT"],
            ["SUBJECT_ID", "TEXT"],
            ["EVENT_AT", "TEXT"],
        ]
        parsed = [[t.upper() for t in column.split()] for column in columns]
        return parsed == expected

    @classmethod
    def _table_segments_match(cls, ddl: str, expected: list[list[str]]) -> bool:
        """Closed-grammar check for any governed table, reusing the stripped
        top-level segment parser (v15-review H2)."""
        return cls._parsed_table_segments(ddl) == expected

    @classmethod
    def _parsed_table_segments(cls, ddl: str) -> list[list[str]] | None:
        stripped: list[str] = []
        i, n = 0, len(ddl)
        while i < n:
            ch = ddl[i]
            if ch == "'":
                i += 1
                while i < n:
                    if ddl[i] == "'":
                        if i + 1 < n and ddl[i + 1] == "'":
                            i += 2
                            continue
                        break
                    i += 1
                i += 1
            elif ch == '"':
                i += 1
                while i < n and ddl[i] != '"':
                    i += 1
                i += 1
            elif ddl.startswith("--", i):
                while i < n and ddl[i] != "\n":
                    i += 1
            elif ddl.startswith("/*", i):
                end = ddl.find("*/", i + 2)
                i = n if end == -1 else end + 2
            else:
                stripped.append(ch)
                i += 1
        text = "".join(stripped)
        start = text.find("(")
        if start == -1:
            return None
        depth, end = 0, -1
        for j in range(start, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end == -1:
            return None
        # v16-review M3: the WHOLE DDL is consumed — any non-comment token
        # after the matching close paren (STRICT, WITHOUT ROWID) refuses.
        if text[end + 1:].strip().strip(";").strip():
            return None
        segments: list[str] = []
        depth, current = 0, []
        for ch in text[start + 1:end]:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                segments.append("".join(current))
                current = []
            else:
                current.append(ch)
        segments.append("".join(current))
        return [[t.upper() for t in segment.split()] for segment in segments]

    # v15-review H1: exact index signatures (unique, non-partial, exact
    # columns) AND counts per governed table — a surplus autoindex minted by
    # a table-level UNIQUE is rejected even though SQLite named it itself.
    _INDEX_SIGNATURES: dict[str, tuple[tuple[str, ...], ...]] = {
        "semantic_assertions": (("assertion_id",),),
        "semantic_attachments": (("evidence_id",),),
        "semantic_evidence_objects": (("evidence_sha256",),),
        "semantic_adjudications": (("adjudication_id",),),
        "event_sequence": (("event_id",),),
        "acquisitions": (("row_id",), ("offering_id",)),
    }
    # v16-review H1: closed grammars for the four semantic tables.
    _SEMANTIC_TABLE_GRAMMARS: dict[str, list[list[str]]] = {
        "semantic_assertions": [
            ["ASSERTION_ID", "TEXT", "PRIMARY", "KEY"],
            ["KEY", "TEXT"],
            ["VERSION", "INTEGER"],
            ["CLAIM", "TEXT"],
            ["ACTIVE", "INTEGER"],
            ["EVIDENCE_ID", "TEXT"],
        ],
        "semantic_attachments": [
            ["EVIDENCE_ID", "TEXT", "PRIMARY", "KEY"],
            ["RETRIEVED_AT", "TEXT"],
            ["PROVENANCE", "TEXT"],
            ["RETENTION", "TEXT"],
            ["EVIDENCE_SHA256", "TEXT"],
            ["EVIDENCE_BYTES", "INTEGER"],
        ],
        "semantic_evidence_objects": [
            ["EVIDENCE_SHA256", "TEXT", "PRIMARY", "KEY"],
            ["EVIDENCE_BLOB", "BLOB"],
        ],
        "semantic_adjudications": [
            ["ADJUDICATION_ID", "TEXT", "PRIMARY", "KEY"],
            ["KEY", "TEXT"],
            ["AUTHORITY", "TEXT"],
            ["PROVENANCE", "TEXT"],
            ["PARENTS", "TEXT"],
            ["EFFECTIVE_ASSERTION_ID", "TEXT"],
        ],
    }

    # v15-review H2: the marker table carries the same closed grammar law.
    _MARKER_TABLE_SEGMENTS = [
        ["ROW_ID", "TEXT", "PRIMARY", "KEY"],
        ["OFFERING_ID", "TEXT", "UNIQUE"],
        ["KIND", "TEXT"],
    ]
    # The pre-v3 legacy acquisition shape is the one other governed grammar a
    # semantics store may carry (i12: legacy stores accept semantic writes).
    _LEGACY_MARKER_TABLE_SEGMENTS = _MARKER_TABLE_SEGMENTS + [
        ["RETRIEVED_AT", "TEXT"],
        ["READINESS", "TEXT"],
        ["RETENTION", "TEXT"],
        ["CONTENT_VINTAGE_ID", "TEXT"],
        ["ARCHIVE_SHA256", "TEXT"],
        ["ARCHIVE_BYTES", "INTEGER"],
        ["ANALYSIS_READY", "INTEGER"],
        ["SIGNATURE", "BLOB"],
    ]

    # v16-review H2: a signature is (origin, ((column, desc, collation), ...))
    # over KEY columns in stable order — origin distinguishes PRIMARY KEY from
    # table-level UNIQUE, and collation/direction changes identity semantics.
    _INDEX_ORIGINS: dict[str, tuple[str, ...]] = {
        "semantic_assertions": ("pk",),
        "semantic_attachments": ("pk",),
        "semantic_evidence_objects": ("pk",),
        "semantic_adjudications": ("pk",),
        "event_sequence": ("u",),
        "acquisitions": ("pk", "u"),
    }

    @classmethod
    def _index_signatures_governed(
        cls, conn: sqlite3.Connection, table: str
    ) -> bool:
        found: list[tuple[str, tuple[tuple[str, int, str], ...]]] = []
        for _seq, name, unique, origin, partial in conn.execute(
            f"PRAGMA index_list({table})"
        ):
            if not unique or partial:
                return False
            key_columns = tuple(
                (row[2], row[3], (row[4] or "").upper())
                for row in conn.execute(f"PRAGMA index_xinfo({name})")
                if row[5] == 1
            )
            found.append(((origin or ""), key_columns))
        expected = sorted(
            (origin, tuple((column, 0, "BINARY") for column in columns))
            for origin, columns in zip(
                cls._INDEX_ORIGINS[table], cls._INDEX_SIGNATURES[table]
            )
        )
        return sorted(found) == expected

    @staticmethod
    def _has_exact_unique_index(
        conn: sqlite3.Connection, table: str, column: str
    ) -> bool:
        for _seq, name, unique, _origin, partial in conn.execute(
            f"PRAGMA index_list({table})"
        ):
            if not unique or partial:
                continue
            columns = [row[2] for row in conn.execute(f"PRAGMA index_info({name})")]
            if columns == [column]:
                return True
        return False

    def _migrate_acquisition_store(self, conn: sqlite3.Connection, store: str) -> None:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "acquisitions" not in tables:
            conn.execute(
                "CREATE TABLE acquisitions ("
                " row_id TEXT PRIMARY KEY,"
                " offering_id TEXT UNIQUE,"
                " source TEXT, kind TEXT, retrieved_at TEXT,"
                " readiness TEXT, retention TEXT,"
                " content_vintage_id TEXT, archive_sha256 TEXT,"
                " archive_bytes INTEGER, role_records TEXT,"
                " analysis_ready INTEGER, signature BLOB,"
                " event_at TEXT, event_seq INTEGER, event_id TEXT)"
            )
        else:
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(acquisitions)")
            }
            additions: dict[frozenset[str], tuple[str, ...]] = {
                self._SCHEMA_V1: (
                    "source TEXT", "role_records TEXT", "event_at TEXT",
                    "event_seq INTEGER", "event_id TEXT",
                ),
                self._SCHEMA_V2: ("event_at TEXT", "event_seq INTEGER", "event_id TEXT"),
                self._SCHEMA_V3: ("event_id TEXT",),
            }
            if frozenset(columns) in additions:
                # v6-review C2 (Codex correction): migration never fabricates
                # event identity for populated historical rows — their
                # cross-store order cannot be reconstructed.  A populated
                # unbound legacy store refuses by name before staging; only a
                # row-empty (marker-only) legacy store migrates.
                populated = conn.execute(
                    "SELECT count(*) FROM acquisitions"
                    " WHERE offering_id != '_bootstrap'"
                ).fetchone()[0]
                if populated:
                    raise _refuse(f"store_migration_unreconcilable:{store}")
                for ddl in additions[frozenset(columns)]:
                    conn.execute(f"ALTER TABLE acquisitions ADD COLUMN {ddl}")
            elif columns != self._SCHEMA_V4:
                raise _refuse(f"store_schema_unmigratable:{store}")
        if "attempts" not in tables:
            conn.execute(
                "CREATE TABLE attempts ("
                " seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                " status TEXT, reason TEXT, at TEXT, event_seq INTEGER,"
                " attempt_id TEXT, event_id TEXT)"
            )
        else:
            attempt_columns = frozenset(
                row[1] for row in conn.execute("PRAGMA table_info(attempts)")
            )
            attempt_additions: dict[frozenset[str], tuple[str, ...]] = {
                self._ATTEMPTS_V1: (
                    "at TEXT", "event_seq INTEGER", "attempt_id TEXT", "event_id TEXT",
                ),
                self._ATTEMPTS_V2: ("attempt_id TEXT", "event_id TEXT"),
            }
            if attempt_columns in attempt_additions:
                populated_attempts = conn.execute(
                    "SELECT count(*) FROM attempts"
                ).fetchone()[0]
                if populated_attempts:
                    raise _refuse(f"store_migration_unreconcilable:{store}")
                for ddl in attempt_additions[attempt_columns]:
                    conn.execute(f"ALTER TABLE attempts ADD COLUMN {ddl}")
            elif attempt_columns != self._ATTEMPTS_V3:
                raise _refuse(f"store_schema_unmigratable:{store}")
        conn.execute(f"PRAGMA user_version={self._SCHEMA_VERSION}")

    def _migrate_semantics_store(self, conn: sqlite3.Connection) -> None:
        """v5-review C1: the semantics/event store is a write-critical
        dependency of every intake, so its shape is validated by exact known
        version — never discovered broken after a paid archive published."""
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        creates = {
            "semantic_assertions": (
                "CREATE TABLE semantic_assertions ("
                " assertion_id TEXT PRIMARY KEY, key TEXT, version INTEGER,"
                " claim TEXT, active INTEGER, evidence_id TEXT)"
            ),
            "semantic_attachments": (
                "CREATE TABLE semantic_attachments ("
                " evidence_id TEXT PRIMARY KEY, retrieved_at TEXT,"
                " provenance TEXT, retention TEXT,"
                " evidence_sha256 TEXT, evidence_bytes INTEGER)"
            ),
            "semantic_evidence_objects": (
                "CREATE TABLE semantic_evidence_objects ("
                " evidence_sha256 TEXT PRIMARY KEY, evidence_blob BLOB)"
            ),
            "semantic_adjudications": (
                "CREATE TABLE semantic_adjudications ("
                " adjudication_id TEXT PRIMARY KEY, key TEXT,"
                " authority TEXT, provenance TEXT, parents TEXT,"
                " effective_assertion_id TEXT)"
            ),
            "event_sequence": (
                "CREATE TABLE event_sequence ("
                " seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE,"
                " event_type TEXT, store_name TEXT, subject_id TEXT,"
                " event_at TEXT)"
            ),
        }
        # PASS 1 — validate every EXISTING table and refuse before any
        # mutation, so an unreconcilable store stays byte-frozen (v7-review
        # C1).  History is never fabricated, and every identity constraint is
        # proven as a full non-partial unique index on the exact identity
        # column (v8-review C1/H2) — never inferred from column names.
        rebuild_bare_ledger = self._validate_semantics_schema(conn, tables)
        # PASS 2 — mutations, only after the whole store validated.
        if rebuild_bare_ledger:
            conn.execute("DROP TABLE event_sequence")
            conn.execute(creates["event_sequence"])
        for table in self._SEMANTIC_TABLES:
            if table not in tables:
                conn.execute(creates[table])

    def _validate_semantics_schema(
        self, conn: sqlite3.Connection, tables: set[str]
    ) -> bool:
        """Pure-read validation of the semantics store; raises the refusal
        family and never writes, so it can run on a read-only prevalidation
        connection (v8-review H4).  Returns whether a row-empty bare event
        allocator needs rebuilding."""
        # v14-review H1: the store's SCHEMA-OBJECT INVENTORY is closed — the
        # table DDL alone cannot see triggers, views, surplus tables, or
        # extra indexes, and any of them changes writer behavior after
        # validation.  Only the governed tables, their SQLite autoindexes,
        # and sqlite_sequence may exist.
        allowed_tables = set(self._SEMANTIC_TABLES) | {"acquisitions", "sqlite_sequence"}
        for object_type, name, tbl_name in conn.execute(
            "SELECT type, name, tbl_name FROM sqlite_master"
        ):
            if object_type == "table" and name in allowed_tables:
                continue
            if (
                object_type == "index"
                and name.startswith("sqlite_autoindex_")
                and tbl_name in allowed_tables
            ):
                continue
            raise _refuse("store_schema_unmigratable:semantics")
        rebuild_bare_ledger = False
        for table, expected in self._SEMANTIC_TABLES.items():
            if table not in tables:
                continue
            columns = frozenset(
                row[1] for row in conn.execute(f"PRAGMA table_info({table})")
            )
            if table == "event_sequence" and columns == frozenset({"seq"}):
                populated = conn.execute(
                    "SELECT count(*) FROM event_sequence"
                ).fetchone()[0]
                if populated:
                    raise _refuse("store_migration_unreconcilable:semantics")
                rebuild_bare_ledger = True
                continue
            if columns != expected:
                raise _refuse("store_schema_unmigratable:semantics")
            # v16-review H1: every governed table's DDL is a CLOSED grammar —
            # a hidden CHECK survives column-name checks and then breaks or
            # falsifies the writer.
            table_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if table in self._SEMANTIC_TABLE_GRAMMARS and (
                table_sql is None
                or not self._table_segments_match(
                    (table_sql[0] or ""), self._SEMANTIC_TABLE_GRAMMARS[table]
                )
            ):
                raise _refuse("store_schema_unmigratable:semantics")
            if not self._has_exact_unique_index(
                conn, table, self._SEMANTIC_IDENTITY[table]
            ):
                raise _refuse("store_schema_unmigratable:semantics")
            if not self._index_signatures_governed(conn, table):
                raise _refuse("store_schema_unmigratable:semantics")
            if table == "event_sequence":
                # v9-review H2: the sequencing structure is validated WHOLE —
                # seq must be the exact INTEGER PRIMARY KEY under the frozen
                # AUTOINCREMENT contract, not merely a present column.
                seq_info = next(
                    (
                        row
                        for row in conn.execute(
                            "PRAGMA table_info(event_sequence)"
                        )
                        if row[1] == "seq"
                    ),
                    None,
                )
                create_sql = conn.execute(
                    "SELECT sql FROM sqlite_master"
                    " WHERE type='table' AND name='event_sequence'"
                ).fetchone()
                if (
                    seq_info is None
                    or seq_info[5] != 1
                    or (seq_info[2] or "").upper() != "INTEGER"
                    # v10-review H2 + v11-review H1: the token proves nothing
                    # unless PARSED from seq's own declaration — decoys in
                    # literals or comments must refuse.
                    or not self._event_table_grammar_is_governed(
                        (create_sql[0] if create_sql else "") or ""
                    )
                ):
                    raise _refuse("store_schema_unmigratable:semantics")
        if "acquisitions" in tables:
            # v15-review H2: the marker table is admitted by GRAMMAR, not by
            # name — wrong shape refuses during non-mutating prevalidation,
            # never as a raw error from the bootstrap insert.
            marker_sql = conn.execute(
                "SELECT sql FROM sqlite_master"
                " WHERE type='table' AND name='acquisitions'"
            ).fetchone()
            if (
                marker_sql is None
                or not (
                    self._table_segments_match(
                        (marker_sql[0] or ""), self._MARKER_TABLE_SEGMENTS
                    )
                    or self._table_segments_match(
                        (marker_sql[0] or ""), self._LEGACY_MARKER_TABLE_SEGMENTS
                    )
                )
                or not self._index_signatures_governed(conn, "acquisitions")
            ):
                raise _refuse("store_schema_unmigratable:semantics")
        return rebuild_bare_ledger

    def initialize_database(self, store: str) -> SimpleNamespace:
        self._ensure_namespace()
        self._require_coverage(RUNTIME_PATHS[store])
        trace: list[str] = []
        path = self._db_path(store)
        if store == "semantics" and path.exists() and path.stat().st_size > 0:
            # v8-review H4: refusal-class validation happens through a
            # NON-MUTATING read BEFORE any write-capable connection touches
            # the file — even `PRAGMA journal_mode=WAL` rewrites a DELETE-mode
            # header, and a refused store must stay byte-frozen.
            try:
                with contextlib.closing(self._open_reader(path)) as ro_conn:
                    ro_tables = {
                        row[0]
                        for row in ro_conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )
                    }
                    self._validate_semantics_schema(ro_conn, ro_tables)
            except sqlite3.DatabaseError as exc:
                raise _refuse(f"store_unreadable:{RUNTIME_PATHS[store]}") from exc
        conn = sqlite3.connect(path)
        try:
            try:
                mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            except sqlite3.DatabaseError as exc:
                # v5-review C1: a governed store whose bytes are not a SQLite
                # database refuses by name — never an uncaught DatabaseError
                # after a paid archive already published.
                raise _refuse(f"store_unreadable:{RUNTIME_PATHS[store]}") from exc
            trace.append("pragma_journal_mode_wal")
            if mode != "wal":
                raise _refuse(f"journal_mode_not_wal:{mode}")
            if store == "semantics":
                # v4-review H6 + v5-review H4 + v7-review C1: the ONE governed
                # event ledger lives here.  Validation/migration runs BEFORE
                # any write so an unreconcilable store refuses byte-frozen.
                self._migrate_semantics_store(conn)
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS acquisitions ("
                    " row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE, kind TEXT)"
                )
            else:
                self._migrate_acquisition_store(conn, store)
            trace.append("schema_write")
            conn.execute(
                "INSERT OR IGNORE INTO acquisitions(row_id, offering_id, kind)"
                " VALUES ('bootstrap-marker', '_bootstrap', 'marker')"
            )
            conn.commit()
            trace.append("application_write")
        finally:
            conn.close()
        self._db_initialized.add(store)
        return SimpleNamespace(effective_journal_mode="wal", trace=trace)

    def _open_reader(self, path: Path) -> sqlite3.Connection:
        """v6-review C3 + v7-review H4: the read mode follows the physical
        file set — a PRESENT -wal demands mode=ro (replays committed frames
        byte-stably; SHM is the only residue) while an ABSENT -wal demands
        immutable=1 (materializes nothing).  Because that choice races a
        conforming writer, the protocol is observe → open → re-observe: if
        the file set changed across the open, the connection is discarded and
        the choice retried.  Persistent instability fails CLOSED as an
        unreadable store, within a hard bound."""
        for _ in range(8):
            before = _observe_sqlite_file_set(path)
            uri = (
                f"file:{path}?mode=ro"
                if before[0]
                else f"file:{path}?mode=ro&immutable=1"
            )
            conn = sqlite3.connect(uri, uri=True)
            # Only the -wal flag decides the mode; SHM is the framed
            # permitted residue and may legitimately appear under this open.
            if _observe_sqlite_file_set(path)[0] == before[0]:
                return conn
            conn.close()
        raise sqlite3.OperationalError("sqlite file set unstable")

    def _store_rows(self, store: str) -> list[dict[str, Any]]:
        path = self._db_path(store)
        if not path.exists():
            return []
        try:
            conn = self._open_reader(path)
        except sqlite3.Error:
            self._unreadable_stores.add(store)
            return []
        with contextlib.closing(conn):
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT * FROM acquisitions WHERE offering_id != '_bootstrap'"
                    " ORDER BY rowid"
                ).fetchall()
            except sqlite3.Error:
                # v4-review H4: an unreadable/foreign governed ledger is a
                # named unverifiable state (framing row 9), never an empty
                # collection.  The flag is consumed by read_model(); intake
                # separately refuses by name (store_schema_unmigratable).
                self._unreadable_stores.add(store)
                return []
        return [dict(row) for row in rows]

    # -- counterpart lookup (non-creating, tri-state) ----------------------

    def _classify_shape_dir(self) -> Path:
        shape_dir = self._scratch / "counterpart"
        shutil.rmtree(shape_dir, ignore_errors=True)
        shape_dir.mkdir()
        return shape_dir

    def snapshot_files(self) -> tuple[str, ...]:
        shape_dir = self._scratch / "counterpart"
        if not shape_dir.exists():
            return ()
        return tuple(sorted(p.name for p in shape_dir.iterdir()))

    def classify_counterpart(self, shape: str) -> SimpleNamespace:
        shape_dir = self._classify_shape_dir()
        main = shape_dir / "counterpart.db"
        if shape == "all_absent":
            pass
        elif shape == "main_only_valid":
            self._make_governed_db(main)
        elif shape == "main_absent_wal":
            (shape_dir / "counterpart.db-wal").write_bytes(b"orphan-wal")
        elif shape == "main_absent_shm":
            (shape_dir / "counterpart.db-shm").write_bytes(b"orphan-shm")
        elif shape == "wrong_schema":
            with contextlib.closing(sqlite3.connect(main)) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("CREATE TABLE wrong(x)")
                conn.commit()
        elif shape == "wrong_journal":
            with contextlib.closing(sqlite3.connect(main)) as conn:
                conn.execute("PRAGMA journal_mode=DELETE")
                conn.execute(
                    "CREATE TABLE acquisitions(row_id TEXT PRIMARY KEY,"
                    " offering_id TEXT UNIQUE, kind TEXT)"
                )
                conn.commit()
        elif shape == "unreadable":
            main.write_bytes(b"this is not a sqlite database at all")
        return SimpleNamespace(state=self._classify_main(main))

    def _make_governed_db(self, path: Path) -> None:
        with contextlib.closing(sqlite3.connect(path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE acquisitions(row_id TEXT PRIMARY KEY,"
                " offering_id TEXT UNIQUE, kind TEXT, retrieved_at TEXT,"
                " readiness TEXT, retention TEXT, content_vintage_id TEXT,"
                " archive_sha256 TEXT, archive_bytes INTEGER,"
                " analysis_ready INTEGER, signature BLOB)"
            )
            conn.commit()

    def _classify_main(self, main: Path) -> str:
        sidecars = [main.with_name(main.name + suffix) for suffix in ("-wal", "-shm")]
        if not main.exists():
            if any(side.exists() for side in sidecars):
                return "malformed"
            return "empty"
        # v5-review H5: classification must be physically side-effect-free —
        # a plain mode=ro open of a WAL database can still materialize a
        # zero-byte -wal, which the counterpart contract forbids (only SHM
        # residue is framed as permitted).  The journal mode therefore comes
        # from the file header itself (an immutable connection's PRAGMA
        # reports the connection, not the file), and the schema is read
        # through immutable=1.  Between operations every connection is closed
        # and checkpointed, so an immutable read never misses committed rows.
        try:
            with open(main, "rb") as handle:
                header = handle.read(100)
        except OSError:
            return "unverifiable"
        if len(header) < 100 or not header.startswith(b"SQLite format 3\x00"):
            return "unverifiable"
        mode = "wal" if header[18] == 2 and header[19] == 2 else "delete"
        try:
            with contextlib.closing(self._open_reader(main)) as conn:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
        except sqlite3.Error:
            return "unverifiable"
        if "acquisitions" not in tables:
            return "unverifiable"
        if mode not in ("wal", "delete"):
            return "unverifiable"
        if mode == "delete" and main.stat().st_size > 0 and "acquisitions" in tables:
            # A governed store is WAL by contract; delete-mode is unverifiable
            return "unverifiable"
        return "existing"

    # -- live WAL fixtures and online backup -------------------------------

    def seed_live_wal_counterpart(
        self, *, main: bool, wal: bool, shm: bool, committed_row: bool
    ) -> _WalFixture:
        build_dir = self._scratch / "wal-build"
        shutil.rmtree(build_dir, ignore_errors=True)
        build_dir.mkdir()
        src = build_dir / "live.db"
        writer = sqlite3.connect(src)
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE fixture(committed INTEGER)")
        if committed_row:
            writer.execute("INSERT INTO fixture(committed) VALUES (1)")
        writer.commit()
        fixture_dir = self._scratch / "wal-fixture"
        shutil.rmtree(fixture_dir, ignore_errors=True)
        fixture_dir.mkdir()
        dst = fixture_dir / "counterpart.db"
        # Copy main+wal while the writer connection still holds the WAL open,
        # so committed state lives in the -wal, exactly the measured shape.
        shutil.copyfile(src, dst)
        if wal:
            shutil.copyfile(
                src.with_name("live.db-wal"), dst.with_name("counterpart.db-wal")
            )
        if shm:
            shutil.copyfile(
                src.with_name("live.db-shm"), dst.with_name("counterpart.db-shm")
            )
        writer.close()
        wal_path = dst.with_name("counterpart.db-wal")
        return _WalFixture(
            main=dst,
            wal=wal_path,
            shm=dst.with_name("counterpart.db-shm"),
            _wal_size=wal_path.stat().st_size if wal_path.exists() else 0,
        )

    def file_fingerprints(self, paths: Iterable[Path]) -> tuple[tuple[int, str], ...]:
        out = []
        for path in paths:
            data = Path(path).read_bytes()
            out.append((len(data), hashlib.sha256(data).hexdigest()))
        return tuple(out)

    def read_counterpart_readonly(self, main: Path) -> dict[str, Any]:
        self._counterpart_conn = sqlite3.connect(f"file:{main}?mode=ro", uri=True)
        row = self._counterpart_conn.execute(
            "SELECT committed FROM fixture"
        ).fetchone()
        return {"committed": bool(row and row[0])}

    def close_counterpart(self) -> None:
        if self._counterpart_conn is not None:
            self._counterpart_conn.close()
            self._counterpart_conn = None

    def online_backup(self, main: Path) -> Path:
        staged = self._scratch / "staged_backup.db"
        staged.unlink(missing_ok=True)
        with contextlib.closing(
            sqlite3.connect(f"file:{main}?mode=ro", uri=True)
        ) as src, contextlib.closing(sqlite3.connect(staged)) as dst:
            src.backup(dst)
        return staged

    def restore_staged_backup(self, staged: Path) -> _Restored:
        restored = self._scratch / "restored.db"
        shutil.copyfile(staged, restored)
        return _Restored(restored)

    def backup_payloads_include_sidecars(self) -> bool:
        return False

    # -- intake ------------------------------------------------------------

    def set_retention_mode(self, mode: str) -> None:
        self.retention_mode = mode

    def _attempts_dir(self) -> list[dict[str, Any]]:
        return getattr(self, "_attempts", [])

    def intake(
        self,
        *,
        archive_bytes: bytes,
        offering: Mapping[str, Any],
        fault_at: str | None = None,
    ) -> IntakeResult:
        lock_fd = self._acquire_lock_nb() if self._lock_fd is None else None
        if self._lock_fd is not None or lock_fd is None:
            return IntakeResult(status="intake_busy", attempt_recorded=False)
        try:
            return self._intake_locked(
                archive_bytes=archive_bytes, offering=offering, fault_at=fault_at
            )
        finally:
            os.close(lock_fd)

    def _intake_locked(
        self,
        *,
        archive_bytes: bytes,
        offering: Mapping[str, Any],
        fault_at: str | None,
    ) -> IntakeResult:
        # C1: the persistence stores are validated (and migrated when the shape
        # is a known prior version) BEFORE any staging or publication.  An
        # unmigratable store must never be discovered mid-publish with a paid
        # archive already on disk and no receipt able to land.
        self._prepare_stores()
        self.sweep_staging()
        staging_dir = self._p("staging")
        stage_name = f"stage-{hashlib.sha256(os.urandom(16)).hexdigest()[:12]}.tmp"
        stage_path = staging_dir / stage_name
        metadata_only = self.retention_mode == "metadata_only"

        if not metadata_only:
            # GREEN-review H7: active raw publication demands the objects row be a
            # REQUIRED directory — the first-capture flip law in code, not prose.
            objects_row = next(
                (
                    r
                    for r in self._manifest_rows()
                    if r.get("path") == RUNTIME_PATHS["objects"]
                ),
                None,
            )
            if objects_row is None or not objects_row.get("required"):
                raise _refuse(
                    "backup_coverage_missing:required:objects:"
                    + RUNTIME_PATHS["objects"]
                )
        keep_staging = False
        fd = os.open(
            stage_path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        self.open_raw_descriptors += 1
        self.trace.append("staging_create")
        dir_fd = os.open(staging_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            if metadata_only:
                os.unlink(stage_name, dir_fd=dir_fd)
                os.fsync(dir_fd)

            if fault_at == "during_staged_write":
                os.write(fd, archive_bytes[: max(1, len(archive_bytes) // 3)])
                keep_staging = True
                return self._crash("partial_staging", "sweep_remove")
            if fault_at == "source_read_error":
                raise _refuse("source_read_error")

            remaining = archive_bytes
            while remaining:
                written = os.write(fd, remaining)
                remaining = remaining[written:]
            os.fsync(fd)
            self.trace.append("source_stream")
            # GREEN-review C1: every signed fact derives from the STAGED bytes,
            # read back through the held descriptor — never the source argument.
            os.lseek(fd, 0, os.SEEK_SET)
            staged_chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    break
                staged_chunks.append(chunk)
            staged_bytes = b"".join(staged_chunks)

            if fault_at == "after_staging_fsync":
                keep_staging = True
                return self._crash("complete_staging", "sweep_remove")

            if fault_at == "archive_malformed":
                raise _refuse("archive_malformed")
            if fault_at == "cap_refusal":
                raise _refuse("archive_too_large:injected")
            if fault_at == "missing_role":
                raise _refuse("missing_role:adp")
            if fault_at == "crc_failure":
                raise _refuse("member_crc_mismatch:adp")

            inspected = inspect_archive(
                staged_bytes, role_paths=ROLE_PATHS, limits=ARCHIVE_LIMITS
            )
            self.trace.append("archive_validate")
            if fault_at == "schema_failure":
                raise _refuse("role_schema_invalid:adp")

            now = self.clock()
            canonical_at = canonical_retrieved_at(offering["retrieved_at"], now=now)
            signature = serialize_offering_signature(
                source=offering["source"],
                offering_id=offering["offering_id"],
                content_vintage_id=inspected["content_vintage_id"],
                retrieved_at=canonical_at,
                archive_sha256=inspected["archive_sha256"],
                archive_bytes=inspected["archive_bytes"],
                role_records=inspected["role_records"],
            )
            acquisition_id = receipt_id(signature)

            existing = self._same_offering_row(offering["offering_id"])
            if existing is not None:
                if existing["row_id"] == acquisition_id:
                    if existing["kind"] == "receipt" or metadata_only:
                        return IntakeResult(
                            status="noop",
                            raw_retained=existing["kind"] == "receipt",
                            receipt_id=acquisition_id
                            if existing["kind"] == "receipt"
                            else None,
                            observation_id=acquisition_id,
                        )
                    # observation exists; a retained receipt upgrades it below.
                else:
                    raise _refuse(
                        f"offering_identity_conflict:{offering['offering_id']}"
                    )

            if metadata_only:
                os.close(fd)
                self.open_raw_descriptors -= 1
                fd = -1
                self._commit_acquisition(
                    store="observations",
                    row_id=acquisition_id,
                    offering=offering,
                    canonical_at=canonical_at,
                    inspected=inspected,
                    kind="observation",
                    signature=signature,
                )
                return IntakeResult(
                    status="ready",
                    raw_retained=False,
                    observation_id=acquisition_id,
                )

            # Branch A — publish or reuse, then the one receipt transaction.
            objects_dir = self._p("objects")
            if fault_at == "cross_device":
                return IntakeResult(
                    status="failed",
                    reason="staging_objects_cross_device",
                    attempt_recorded=True,
                )
            canonical = objects_dir / f"{inspected['archive_sha256']}.zip"
            objects_fd = os.open(
                objects_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            try:
                if os.fstat(objects_fd).st_dev != os.fstat(dir_fd).st_dev:
                    self._record_attempt("failed", "staging_objects_cross_device")
                    return IntakeResult(
                        status="failed",
                        reason="staging_objects_cross_device",
                        attempt_recorded=True,
                    )
                if canonical.exists():
                    self._verify_existing_object(canonical, inspected)
                    if fault_at == "receipt_commit_reuse":
                        return self._crash("no_new_residue", "keep_reference_set")
                else:
                    self._require_coverage(RUNTIME_PATHS["objects"])
                    os.link(stage_path, canonical)
                    self.trace.append("publish_no_replace")
                    os.unlink(stage_name, dir_fd=dir_fd)
                    keep_staging = True  # name consumed; nothing left to unlink
                    if fault_at == "after_publish_before_dir_fsync":
                        return self._crash("canonical_optional", "reuse_or_republish")
                    # GREEN-review C2: durability belongs to the OBJECTS parent.
                    os.fsync(objects_fd)
                    os.fsync(dir_fd)
                    staged_info = os.fstat(fd)
                    published = os.lstat(canonical)
                    if (
                        not stat_module.S_ISREG(published.st_mode)
                        or published.st_nlink != 1
                        or (published.st_dev, published.st_ino)
                        != (staged_info.st_dev, staged_info.st_ino)
                        or published.st_size != inspected["archive_bytes"]
                    ):
                        canonical.unlink(missing_ok=True)
                        os.fsync(objects_fd)
                        raise _refuse("published_object_invalid")
                    os.lseek(fd, 0, os.SEEK_SET)
                    digest = hashlib.sha256()
                    while True:
                        chunk = os.read(fd, 1 << 20)
                        if not chunk:
                            break
                        digest.update(chunk)
                    if digest.hexdigest() != inspected["archive_sha256"]:
                        canonical.unlink(missing_ok=True)
                        os.fsync(objects_fd)
                        raise _refuse("published_object_hash_mismatch")
                    # M7: framed defense-in-depth mode on the published object,
                    # set through the bound descriptor.  Rehash-on-load stays
                    # the authoritative integrity boundary; 0444 merely stops
                    # casual in-place mutation.
                    os.fchmod(fd, 0o444)
                    self.trace.append("published_inode_verify")
            finally:
                os.close(objects_fd)
                os.close(fd)
                self.open_raw_descriptors -= 1
                fd = -1
            if fault_at == "receipt_commit_fresh":
                return self._crash("canonical_orphan", "adopt_on_reuse")

            readiness = self._commit_acquisition(
                store="receipts",
                row_id=acquisition_id,
                offering=offering,
                canonical_at=canonical_at,
                inspected=inspected,
                kind="receipt",
                signature=signature,
            )
            self.trace.append("receipt_transaction")
            return IntakeResult(
                status="review_required" if readiness == "review_required" else "ready",
                raw_retained=True,
                receipt_id=acquisition_id,
                observation_id=acquisition_id,
            )
        except FootballguysIntakeError as exc:
            if exc.code.startswith(
                (
                    "offering_identity_conflict",
                    "backup_coverage_missing",
                    "store_schema_unmigratable",
                    "store_unreadable",
                    "store_migration_unreconcilable",
                    "event_ledger_unreconciled",
                    "event_at_invalid",
                )
            ):
                raise
            status = "invalid" if exc.code.startswith("retrieved_at") else "failed"
            self._record_attempt(status, exc.code)
            return IntakeResult(status="failed", reason=exc.code)
        finally:
            if fd >= 0:
                with contextlib.suppress(OSError):
                    os.close(fd)
                self.open_raw_descriptors -= 1
            if not metadata_only and not keep_staging:
                with contextlib.suppress(FileNotFoundError, OSError):
                    info = os.stat(stage_name, dir_fd=dir_fd, follow_symlinks=False)
                    if stat_module.S_ISREG(info.st_mode):
                        os.unlink(stage_name, dir_fd=dir_fd)
                with contextlib.suppress(OSError):
                    os.fsync(dir_fd)
            os.close(dir_fd)

    def _prepare_stores(self) -> None:
        # v4-review H7: only the ACTIVE write store is initialized/migrated.
        # The inactive counterpart is a lookup target under the logical-read-
        # only contract — no schema write, marker, or user_version may touch
        # it from here; permitted residue is SHM materialization only.
        target = (
            "observations" if self.retention_mode == "metadata_only" else "receipts"
        )
        self.initialize_database(target)
        # v5-review C1: the common semantics/event store is a write dependency
        # of EVERY intake (event allocation + readiness), so it is validated
        # here, before staging — a corrupt or unmigratable semantics store
        # must never be discovered after a paid archive published.
        self.initialize_database("semantics")
        # v6-review C2: an unreconciled event ledger (orphaned central event,
        # stripped claim, skewed copy) blocks intake by name.  The orphan is
        # never deleted as generic crash residue — it stays visible until a
        # governed reconciliation, and no new acquisition may stack on top of
        # unprovable history.
        clock_iso = self.clock().isoformat()
        try:
            _canonical_instant(clock_iso, now=None)
        except FootballguysIntakeError as exc:
            raise _refuse(f"event_at_invalid:{clock_iso}") from exc
        self._unreadable_stores = set()
        self._refuse_unreadable_counterpart()
        if self._event_ledger_reconciled() != "reconciled":
            raise _refuse("event_ledger_unreconciled")

    def _refuse_unreadable_counterpart(self) -> None:
        """v7-review C2: knowledge of an unreadable counterpart relation must
        be load-bearing BEFORE any write.  A PRESENT relation that cannot
        answer the production read shape refuses by exact relation; an absent
        attempts relation stays tolerable at intake (the read model renders
        row 9 for it) because a governed legacy store legitimately predates
        the relation."""
        inactive = (
            "receipts" if self.retention_mode == "metadata_only" else "observations"
        )
        path = self._db_path(inactive)
        if not path.exists():
            return
        probes = {
            "acquisitions": (
                "SELECT * FROM acquisitions"
                " WHERE offering_id != '_bootstrap' LIMIT 0"
            ),
            "attempts": (
                "SELECT attempt_id, event_id, at, event_seq"
                " FROM attempts LIMIT 0"
            ),
        }
        try:
            with contextlib.closing(self._open_reader(path)) as conn:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                for relation, probe in probes.items():
                    if relation not in tables:
                        continue
                    try:
                        conn.execute(probe)
                    except sqlite3.Error as exc:
                        raise _refuse(
                            f"store_unreadable:{inactive}.{relation}"
                        ) from exc
        except sqlite3.Error as exc:
            raise _refuse(f"store_unreadable:{inactive}") from exc

    def _crash(self, residue: str, restart: str) -> IntakeResult:
        self.last_crash_residue = residue
        self.restart_contract = restart
        self._record_attempt("failed", residue)
        return IntakeResult(status="failed", reason=residue)

    # (staging cleanup is owned by the intake's finally block — one owner, one close)

    def _verify_existing_object(
        self, canonical: Path, inspected: Mapping[str, Any]
    ) -> None:
        fd = os.open(canonical, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not stat_module.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise _refuse("canonical_object_aliased")
            data = b""
            while True:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    break
                data += chunk
            if (
                len(data) != inspected["archive_bytes"]
                or hashlib.sha256(data).hexdigest() != inspected["archive_sha256"]
            ):
                raise _refuse("canonical_object_corrupt")
        finally:
            os.close(fd)

    def _same_offering_row(self, offering_id: str) -> dict[str, Any] | None:
        for store in ("receipts", "observations"):
            main = self._db_path(store)
            state = self._classify_main(main)
            if state == "empty":
                continue
            if state != "existing":
                raise _refuse(f"counterpart_{state}:{store}")
            for row in self._store_rows(store):
                if row["offering_id"] == offering_id:
                    return row
        return None

    def _horizon_is_effective(self) -> bool:
        state = self.semantic_state(key="classic.adp_sleeper-sf.horizon")
        return bool(state.get("state") == "known" and state.get("eligible_for_phase_c"))

    def _commit_acquisition(
        self,
        *,
        store: str,
        row_id: str,
        offering: Mapping[str, Any],
        canonical_at: str,
        inspected: Mapping[str, Any],
        kind: str,
        signature: bytes,
    ) -> str:
        if store not in self._db_initialized:
            self.initialize_database(store)
        if kind == "receipt":
            # GREEN-review H5: unknown horizon advances freshness only —
            # analysis readiness requires effective provider-authentic evidence.
            readiness = "ready" if self._horizon_is_effective() else "review_required"
            analysis_ready = 1 if readiness == "ready" else 0
            retention = "retained"
        else:
            readiness, analysis_ready, retention = "metadata_only", 0, "metadata_only"
        # The acquisition and every attempt share ONE durable, identity-bound
        # event ledger (H4/H6), so later overlays can order failures against
        # the successful acquisition even at equal clock instants and across
        # retention-mode transitions.
        event = self._allocate_event(
            event_type="acquisition", store_name=store, subject_id=row_id
        )
        with contextlib.closing(sqlite3.connect(self._db_path(store))) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO acquisitions"
                " (row_id, offering_id, source, kind, retrieved_at, readiness,"
                "  retention, content_vintage_id, archive_sha256, archive_bytes,"
                "  role_records, analysis_ready, signature, event_at, event_seq,"
                "  event_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    row_id,
                    offering["offering_id"],
                    offering["source"],
                    kind,
                    canonical_at,
                    readiness,
                    retention,
                    inspected["content_vintage_id"],
                    inspected["archive_sha256"],
                    inspected["archive_bytes"],
                    json.dumps(inspected["role_records"]),
                    analysis_ready,
                    signature,
                    event["event_at"],
                    event["event_seq"],
                    event["event_id"],
                ),
            )
            conn.commit()
        return readiness

    def _allocate_event(
        self, *, event_type: str, store_name: str, subject_id: str
    ) -> dict[str, Any]:
        """v5-review H4: every ordered event is a governed central RECORD —
        identity, type, store, subject, and instant — never a bare integer.
        Claims copied into the acquisition stores are revalidated against
        these records on every load."""
        if "semantics" not in self._db_initialized:
            self.initialize_database("semantics")
        event_id = hashlib.sha256(os.urandom(16)).hexdigest()[:32]
        event_at = self.clock().isoformat()
        # v8-review H3: an event instant is canonical AT THE WRITER — a
        # fractional or naive clock refuses before any commit.
        try:
            _canonical_instant(event_at, now=None)
        except FootballguysIntakeError as exc:
            raise _refuse(f"event_at_invalid:{event_at}") from exc
        with contextlib.closing(
            sqlite3.connect(self._db_path("semantics"))
        ) as conn:
            cursor = conn.execute(
                "INSERT INTO event_sequence"
                " (event_id, event_type, store_name, subject_id, event_at)"
                " VALUES (?,?,?,?,?)",
                (event_id, event_type, store_name, subject_id, event_at),
            )
            conn.commit()
            return {
                "event_id": event_id,
                "event_at": event_at,
                "event_seq": int(cursor.lastrowid),
            }

    def _record_attempt(self, status: str, reason: str | None) -> None:
        store = "observations" if self.retention_mode == "metadata_only" else "receipts"
        if store not in self._db_initialized:
            self.initialize_database(store)
        attempt_id = hashlib.sha256(os.urandom(16)).hexdigest()[:32]
        event = self._allocate_event(
            event_type="attempt", store_name=store, subject_id=attempt_id
        )
        with contextlib.closing(sqlite3.connect(self._db_path(store))) as conn:
            conn.execute(
                "INSERT INTO attempts"
                " (status, reason, at, event_seq, attempt_id, event_id)"
                " VALUES (?,?,?,?,?,?)",
                (
                    status,
                    reason,
                    event["event_at"],
                    event["event_seq"],
                    attempt_id,
                    event["event_id"],
                ),
            )
            conn.commit()

    def _load_attempts(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for store in ("receipts", "observations"):
            path = self._db_path(store)
            if not path.exists():
                continue
            try:
                with contextlib.closing(self._open_reader(path)) as conn:
                    rows = conn.execute(
                        "SELECT status, reason, at, event_seq, attempt_id,"
                        " event_id FROM attempts ORDER BY seq"
                    ).fetchall()
            except sqlite3.Error:
                # v5-review H3: an unreadable/missing attempts relation is the
                # same row-9 unverifiable state as the acquisitions relation —
                # never silently "no attempts".
                self._unreadable_stores.add(store)
                continue
            out.extend(
                {
                    "status": row[0],
                    "reason": row[1],
                    "at": row[2],
                    "event_seq": row[3],
                    "attempt_id": row[4],
                    "event_id": row[5],
                    "store": store,
                }
                for row in rows
            )
        # H6: merged attempts are ordered by the GLOBAL event key so the
        # evaluator's "last newer attempt" selection is durable across stores.
        fallback = (datetime.fromtimestamp(0, timezone.utc), -1)
        out.sort(
            key=lambda a: self._event_key(a.get("at"), a.get("event_seq"))
            or fallback
        )
        return out

    # -- durable semantic seam (GREEN-review H5) ---------------------------

    _SEMANTIC_RECORD_FIELDS: dict[str, tuple[str, ...]] = {
        "assertion": ("assertion_id", "key", "version", "claim", "active"),
        "attachment": (
            "evidence_id", "retrieved_at", "provenance", "retention",
            "evidence_bytes",
        ),
    }

    def write_semantic_assertion(self, record: Mapping[str, Any]) -> dict[str, Any]:
        # v9-review H5: ALL pure record validation precedes store
        # initialization — an invalid record must refuse with the database
        # and its sidecars physically absent on a fresh root.
        # v6-review C1: the record shape itself is validated FIRST — a missing
        # section or field is a named domain refusal, never a bare KeyError.
        for section, fields in self._SEMANTIC_RECORD_FIELDS.items():
            if section not in record:
                raise _refuse(f"semantic_record_invalid:missing:{section}")
            if not isinstance(record[section], Mapping):
                raise _refuse(f"semantic_record_invalid:type:{section}")
            for field in fields:
                if field not in record[section]:
                    raise _refuse(
                        f"semantic_record_invalid:missing:{section}.{field}"
                    )
        assertion = record["assertion"]
        attachment = record["attachment"]
        # C2: the gate that decides analysis readiness accepts only governed
        # evidence — allowlisted provenance and claims, validated BEFORE any
        # write so a refusal can never leave partial semantic state behind.
        # v5-review C2: the writer schema is TOTAL — every field has a closed
        # type and vocabulary, checked before any mutation.  `active` must be
        # an exact boolean: truthiness turned the string "false" into an
        # active Phase-C-eligible assertion in the reviewed GREEN.
        if not isinstance(assertion["active"], bool):
            raise _refuse(f"semantic_active_invalid:{assertion['active']!r}")
        for name, value in (
            ("assertion_id", assertion["assertion_id"]),
            ("key", assertion["key"]),
            ("evidence_id", attachment["evidence_id"]),
        ):
            if not isinstance(value, str) or not value:
                raise _refuse(f"semantic_id_invalid:{name}")
        if attachment["retention"] != "retained":
            raise _refuse(
                f"semantic_retention_invalid:{attachment['retention']}"
            )
        if not isinstance(attachment["evidence_bytes"], (bytes, bytearray)):
            raise _refuse("semantic_evidence_bytes_invalid:not_bytes")
        # v7-review H3: type established BEFORE membership — an unhashable
        # value must reach the named refusal, never a bare TypeError.
        if (
            not isinstance(attachment["provenance"], str)
            or attachment["provenance"] not in SEMANTIC_PROVENANCE_ALLOWED
        ):
            raise _refuse(
                f"semantic_provenance_invalid:{attachment['provenance']!r}"
            )
        if (
            not isinstance(assertion["claim"], str)
            or assertion["claim"] not in SEMANTIC_CLAIMS_ALLOWED
        ):
            raise _refuse(f"semantic_claim_invalid:{assertion['claim']!r}")
        # v4-review H3: closed record schema — an exact integer version (bool
        # is not a version) and a canonical timezone-aware retrieval instant,
        # validated through the same serializer the acquisition side uses.
        if (
            not isinstance(assertion["version"], int)
            or isinstance(assertion["version"], bool)
            # v11-review M2: the storable domain is explicit — SQLite INTEGER
            # is signed 64-bit; a Python int outside it must refuse here,
            # before any store exists to overflow into.
            or not -(2**63) <= assertion["version"] < 2**63
        ):
            raise _refuse(
                f"semantic_version_invalid:{assertion['version']!r}"
            )
        canonical_evidence_at = canonical_retrieved_at(
            attachment["retrieved_at"], now=self.clock()
        )
        evidence_bytes = attachment["evidence_bytes"]
        evidence_sha = hashlib.sha256(evidence_bytes).hexdigest()
        incoming_attachment = (
            canonical_evidence_at,
            attachment["provenance"],
            attachment["retention"],
            evidence_sha,
        )
        if "semantics" not in self._db_initialized:
            self.initialize_database("semantics")
        with contextlib.closing(sqlite3.connect(self._db_path("semantics"))) as conn:
            existing = conn.execute(
                "SELECT key, version, claim, active, evidence_id"
                " FROM semantic_assertions WHERE assertion_id=?",
                (assertion["assertion_id"],),
            ).fetchone()
            incoming = (
                assertion["key"],
                assertion["version"],
                assertion["claim"],
                1 if assertion["active"] else 0,
                attachment["evidence_id"],
            )
            prior_attachment = conn.execute(
                "SELECT retrieved_at, provenance, retention, evidence_sha256"
                " FROM semantic_attachments WHERE evidence_id=?",
                (attachment["evidence_id"],),
            ).fetchone()
            if existing is not None:
                # v4-review H3: idempotent noop demands FULL equality — the
                # assertion tuple AND the complete attachment facts including
                # the evidence bytes and canonical retrieval instant.
                if tuple(existing) != incoming or (
                    prior_attachment is not None
                    and tuple(prior_attachment) != incoming_attachment
                ):
                    raise _refuse(
                        f"assertion_identity_conflict:{assertion['assertion_id']}"
                    )
                return {"status": "noop"}
            # C2/H3: evidence identity is append-only over the WHOLE
            # attachment — a reused evidence id must carry identical bytes,
            # canonical instant, provenance, and retention; any difference is
            # a conflict, never a replacement.
            if prior_attachment is not None and tuple(prior_attachment) != (
                incoming_attachment
            ):
                raise _refuse(
                    f"evidence_identity_conflict:{attachment['evidence_id']}"
                )
            conn.execute(
                "INSERT INTO semantic_assertions"
                " (assertion_id, key, version, claim, active, evidence_id)"
                " VALUES (?,?,?,?,?,?)",
                (assertion["assertion_id"], *incoming),
            )
            if prior_attachment is None:
                conn.execute(
                    "INSERT INTO semantic_attachments"
                    " (evidence_id, retrieved_at, provenance, retention,"
                    "  evidence_sha256, evidence_bytes)"
                    " VALUES (?,?,?,?,?,?)",
                    (
                        attachment["evidence_id"],
                        canonical_evidence_at,
                        attachment["provenance"],
                        attachment["retention"],
                        evidence_sha,
                        len(evidence_bytes),
                    ),
                )
            # C2: the evidence BYTES are governed retained state, content-
            # addressed inside the same ignored, manifest-covered store.
            conn.execute(
                "INSERT OR IGNORE INTO semantic_evidence_objects"
                " (evidence_sha256, evidence_blob) VALUES (?,?)",
                (evidence_sha, evidence_bytes),
            )
            conn.commit()
        return {"status": "written"}

    def write_semantic_adjudication(self, record: Mapping[str, Any]) -> dict[str, Any]:
        # v9-review H5: pure validation precedes store initialization.
        required = (
            "adjudication_id", "key", "authority", "provenance",
            "parents", "effective_assertion_id",
        )
        # Presence, not truthiness: an unhashable/wrong-typed value must fall
        # through to ITS OWN named refusal below (v7-review H3).
        if any(
            field not in record or record[field] is None or record[field] == ""
            for field in required
        ):
            raise _refuse("adjudication_invalid:missing_field")
        if (
            not isinstance(record["authority"], str)
            or record["authority"] not in ADJUDICATION_AUTHORITY_ALLOWED
        ):
            raise _refuse(f"adjudication_authority_invalid:{record['authority']!r}")
        if (
            not isinstance(record["provenance"], str)
            or record["provenance"] not in ADJUDICATION_PROVENANCE_ALLOWED
        ):
            raise _refuse(f"adjudication_provenance_invalid:{record['provenance']!r}")
        if not isinstance(record["parents"], list) or not all(
            isinstance(item, str) and item for item in record["parents"]
        ):
            raise _refuse("adjudication_invalid:parents")
        # v8-review H5(M): every identity/key field is nonempty text BEFORE
        # any relation check or SQLite binding — total, named, never bare.
        for name, code in (
            ("adjudication_id", "adjudication_id_invalid"),
            ("key", "adjudication_key_invalid"),
            ("effective_assertion_id", "adjudication_effective_assertion_id_invalid"),
        ):
            if not isinstance(record[name], str) or not record[name]:
                raise _refuse(f"{code}:{record[name]!r}")
        row = (
            record["key"],
            record["authority"],
            record["provenance"],
            json.dumps(sorted(record["parents"])),
            record["effective_assertion_id"],
        )
        if "semantics" not in self._db_initialized:
            self.initialize_database("semantics")
        # v4-review C1: the effective assertion must be an ACTIVE assertion of
        # the SAME key this adjudication rules on, and a member of its own
        # declared parent set.  Anything else is refused before any mutation —
        # a mis-keyed ruling must never be storable, let alone effective.
        if record["effective_assertion_id"] not in set(record["parents"]):
            raise _refuse(
                "adjudication_relation_invalid:effective_not_in_parents:"
                + record["effective_assertion_id"]
            )
        with contextlib.closing(sqlite3.connect(self._db_path("semantics"))) as conn:
            known = conn.execute(
                "SELECT assertion_id FROM semantic_assertions"
                " WHERE assertion_id=? AND key=? AND active=1",
                (record["effective_assertion_id"], record["key"]),
            ).fetchone()
            if known is None:
                raise _refuse(
                    "adjudication_relation_invalid:effective_not_active_for_key:"
                    + record["effective_assertion_id"]
                )
            existing = conn.execute(
                "SELECT key, authority, provenance, parents, effective_assertion_id"
                " FROM semantic_adjudications WHERE adjudication_id=?",
                (record["adjudication_id"],),
            ).fetchone()
            if existing is not None:
                if tuple(existing) != row:
                    raise _refuse(
                        f"adjudication_identity_conflict:{record['adjudication_id']}"
                    )
                return {"status": "noop"}
            conn.execute(
                "INSERT INTO semantic_adjudications"
                " (adjudication_id, key, authority, provenance, parents,"
                "  effective_assertion_id)"
                " VALUES (?,?,?,?,?,?)",
                (record["adjudication_id"], *row),
            )
            conn.commit()
        return {"status": "written"}

    def semantic_state(self, *, key: str) -> dict[str, Any]:
        path = self._db_path("semantics")
        if not path.exists():
            return {"state": "unknown", "reason": "no_active_assertion", "eligible_for_phase_c": False}
        with contextlib.closing(
            sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        ) as conn:
            try:
                assertion_rows = conn.execute(
                    "SELECT assertion_id, key, version, claim, active, evidence_id"
                    " FROM semantic_assertions"
                ).fetchall()
                attachment_rows = conn.execute(
                    "SELECT evidence_id, retention, evidence_sha256,"
                    " evidence_bytes, provenance, retrieved_at"
                    " FROM semantic_attachments"
                ).fetchall()
                evidence_blobs = dict(
                    conn.execute(
                        "SELECT evidence_sha256, evidence_blob"
                        " FROM semantic_evidence_objects"
                    ).fetchall()
                )
                adjudication_rows = conn.execute(
                    "SELECT adjudication_id, authority, provenance, parents,"
                    " effective_assertion_id, key"
                    " FROM semantic_adjudications"
                ).fetchall()
                # v8-review C1: duplicate identities are detected BEFORE any
                # dictionary can collapse them — a restored constraint-free
                # table must never resolve last-row-wins into eligibility.
                for dup_table, dup_column in (
                    ("semantic_assertions", "assertion_id"),
                    ("semantic_attachments", "evidence_id"),
                    ("semantic_evidence_objects", "evidence_sha256"),
                    ("semantic_adjudications", "adjudication_id"),
                ):
                    duplicated = conn.execute(
                        f"SELECT count(*) FROM (SELECT {dup_column}"
                        f" FROM {dup_table} GROUP BY {dup_column}"
                        " HAVING count(*) > 1)"
                    ).fetchone()[0]
                    if duplicated:
                        return {
                            "state": "unknown",
                            "reason": f"semantic_identity_duplicate:{dup_table}",
                            "eligible_for_phase_c": False,
                        }
            except sqlite3.Error:
                return {"state": "unknown", "reason": "store_unreadable", "eligible_for_phase_c": False}

        # C2: "retained_verified" is a rehash performed NOW on the retained
        # bytes, never a label trusted from a prior write — and every restored
        # field re-passes its type and vocabulary checks, because a restore
        # never signs the write contract.  All failures are states, not
        # exceptions.
        def _attachment_state(
            retention: Any, sha: Any, size: Any, provenance: Any, retrieved_at: Any
        ) -> str:
            if provenance not in SEMANTIC_PROVENANCE_ALLOWED:
                return "provenance_ungoverned"
            try:
                # v6-review C1: the load mirror keeps EVERY writer predicate,
                # including the future-instant refusal — a restored future
                # evidence time must never open eligibility.
                _canonical_instant(retrieved_at, now=self._now())
            except (FootballguysIntakeError, TypeError):
                return "attachment_time_invalid"
            if retention != "retained":
                return retention if isinstance(retention, str) else "retention_invalid"
            blob = evidence_blobs.get(sha)
            if (
                not isinstance(blob, bytes)
                or not isinstance(size, int)
                or isinstance(size, bool)
                or len(blob) != size
                or hashlib.sha256(blob).hexdigest() != sha
            ):
                return "retained_unverifiable"
            return "retained_verified"

        attachments = {}
        for row in attachment_rows:
            # v6-review C1: an evidence identity must be nonempty TEXT on load
            # exactly as at the writer; anything else is unclaimable and the
            # assertions referencing it fail closed below.
            if not isinstance(row[0], str) or not row[0]:
                continue
            attachments[row[0]] = {
                "state": _attachment_state(row[1], row[2], row[3], row[4], row[5]),
                "evidence_sha256": row[2],
                "evidence_bytes": row[3],
            }

        # C2 + v9-review C1 + v10-review C1: restored assertion scalars must
        # be exactly the written types, validated TABLE-WIDE and BEFORE any
        # key/active filter — a corrupt conflicting or inactive row must fail
        # the read, never vanish from a WHERE clause and open eligibility.
        for row in assertion_rows:
            if (
                not isinstance(row[0], str)
                or not row[0]
                or not isinstance(row[1], str)
                or not row[1]
                or type(row[2]) is not int
                or not isinstance(row[3], str)
                or row[3] not in SEMANTIC_CLAIMS_ALLOWED
                or type(row[4]) is not int
                or row[4] not in (0, 1)
                or not isinstance(row[5], str)
                or not row[5]
            ):
                return {
                    "state": "unknown",
                    "reason": "assertion_row_invalid",
                    "eligible_for_phase_c": False,
                }
        assertion_rows = [row for row in assertion_rows if row[1] == key]

        # v9-review C1: every adjudication identity scalar is nonempty TEXT
        # on load — a restored BLOB/empty id fails closed by name before the
        # row can be filtered, governed, or projected.
        for row in adjudication_rows:
            if any(
                not isinstance(value, str) or not value
                for value in (row[0], row[4], row[5])
            ):
                return {
                    "state": "unknown",
                    "reason": "adjudication_row_invalid",
                    "eligible_for_phase_c": False,
                }
        adjudication_rows = [row for row in adjudication_rows if row[5] == key]

        def _parse_parents(payload: Any) -> list[str] | None:
            try:
                parsed = json.loads(payload)
            except (TypeError, ValueError):
                return None
            if not isinstance(parsed, list) or not all(
                isinstance(item, str) and item for item in parsed
            ):
                return None
            return parsed

        adjudications = []
        for row in adjudication_rows:
            parents = _parse_parents(row[3])
            if parents is None:
                # Malformed persisted parents: the adjudication is simply not
                # governed — the reducer then reports the unresolved conflict.
                continue
            adjudications.append(
                {
                    "adjudication_id": row[0],
                    "authority": row[1],
                    "provenance": row[2],
                    "parents": parents,
                    "effective_assertion_id": row[4],
                }
            )
        assertions = [
            {
                "assertion_id": row[0],
                "key": row[1],
                "version": row[2],
                "claim": row[3],
                "active": bool(row[4]),
                "evidence_id": row[5],
            }
            for row in assertion_rows
        ]
        reduced = reduce_semantic_assertions(
            assertions=assertions, attachments=attachments, adjudications=adjudications
        )
        if reduced["state"] != "known":
            return reduced
        chosen = next(
            row for row in assertions if row["assertion_id"] == reduced["assertion_id"]
        )
        attachment = attachments[chosen["evidence_id"]]
        return {
            "state": "known",
            "value": reduced["value"],
            "assertion_id": reduced["assertion_id"],
            "evidence_id": chosen["evidence_id"],
            "evidence_sha256": attachment["evidence_sha256"],
            "evidence_bytes": attachment["evidence_bytes"],
            "eligible_for_phase_c": True,
        }

    # -- effective acquisitions and read model -----------------------------

    def _row_identity_valid(self, row: Mapping[str, Any]) -> bool:
        """GREEN-review C3: reconstruct the signature from PERSISTED signed fields
        through the production serializer and compare to the stored id."""
        try:
            role_records = json.loads(row["role_records"] or "[]")
            signature = serialize_offering_signature(
                source=row["source"],
                offering_id=row["offering_id"],
                content_vintage_id=row["content_vintage_id"],
                retrieved_at=row["retrieved_at"],
                archive_sha256=row["archive_sha256"],
                archive_bytes=row["archive_bytes"],
                role_records=role_records,
            )
        except (FootballguysIntakeError, KeyError, TypeError, ValueError):
            return False
        return receipt_id(signature) == row["row_id"]

    def _receipt_object_valid(self, row: Mapping[str, Any]) -> bool:
        """GREEN-review C3: descriptor-bound rehash of the receipt-bound object."""
        canonical = self._p("objects") / f"{row['archive_sha256']}.zip"
        try:
            fd = os.open(canonical, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:
            return False
        try:
            info = os.fstat(fd)
            if (
                not stat_module.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size != row["archive_bytes"]
            ):
                return False
            digest = hashlib.sha256()
            while True:
                chunk = os.read(fd, 1 << 20)
                if not chunk:
                    break
                digest.update(chunk)
            return digest.hexdigest() == row["archive_sha256"]
        finally:
            os.close(fd)

    def _effective_acquisitions(self) -> list[dict[str, Any]]:
        self._unreadable_stores: set[str] = set()
        raw: list[dict[str, Any]] = []
        for store, kind in (("observations", "observation"), ("receipts", "receipt")):
            for row in self._store_rows(store):
                row["kind"] = kind
                raw.append(row)

        invalid_rows: list[dict[str, Any]] = []
        valid_rows: list[dict[str, Any]] = []
        for row in raw:
            if not self._row_identity_valid(row):
                invalid_rows.append(row)
            elif row["kind"] == "receipt" and not self._receipt_object_valid(row):
                invalid_rows.append(row)
            else:
                valid_rows.append(row)

        # Global offering grouping over the union (rounds 19-22, in the load path).
        specials: list[dict[str, Any]] = []
        barred_offerings: set[str] = set()
        by_offering: dict[tuple[str, str], set[str]] = {}
        for row in valid_rows:
            by_offering.setdefault(
                (row["source"], row["offering_id"]), set()
            ).add(row["row_id"])
        for (source, offering_id), ids in by_offering.items():
            if len(ids) > 1:
                specials.append(
                    {
                        "special": "offering_identity_conflict",
                        "members": sorted(ids),
                    }
                )
                barred_offerings.add(offering_id)
        for row in invalid_rows:
            specials.append({"special": "integrity_failure", "id": row["row_id"]})
            barred_offerings.add(row["offering_id"])

        # GREEN-review H3: analysis readiness is DERIVED on every load from the
        # current effective semantic state — the persisted readiness column is
        # at-intake provenance only.  Later valid evidence promotes a retained
        # receipt; later evidence loss demotes it; identity and freshness never
        # change either way.
        horizon_effective = self._horizon_is_effective()
        by_id: dict[str, dict[str, Any]] = {}
        for row in valid_rows:
            if row["offering_id"] in barred_offerings:
                continue
            current = by_id.get(row["row_id"])
            if current is None or row["kind"] == "receipt":
                if row["kind"] == "receipt":
                    readiness = "ready" if horizon_effective else "review_required"
                    analysis_ready = horizon_effective
                else:
                    readiness = row["readiness"]
                    analysis_ready = False
                by_id[row["row_id"]] = {
                    "id": row["row_id"],
                    "kind": row["kind"],
                    "offering_id": row["offering_id"],
                    "retrieved_at": row["retrieved_at"],
                    "readiness": readiness,
                    "retention": row["retention"],
                    "content_vintage_id": row["content_vintage_id"],
                    "analysis_ready": analysis_ready,
                    "receipt_id": row["row_id"],
                    "event_at": row.get("event_at"),
                    "event_seq": row.get("event_seq"),
                    "event_id": row.get("event_id"),
                    "valid": True,
                }
        rows = sorted(by_id.values(), key=lambda row: (row["retrieved_at"], row["id"]))
        self._effective_specials = specials
        return rows

    @staticmethod
    def _event_key(at: Any, seq: Any) -> tuple[datetime, int] | None:
        if at is None or seq is None:
            return None
        try:
            return (datetime.fromisoformat(at), int(seq))
        except (TypeError, ValueError):
            return None

    def _flag_newer_attempts(
        self, attempts: list[dict[str, Any]], rows: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """GREEN-review H4: an attempt is 'newer' iff its durable (instant,
        sequence) key follows the newest valid acquisition's key.  Equal
        instants are resolved by the shared sequence alone."""
        acquisition_keys = [
            key
            for key in (
                self._event_key(row.get("event_at"), row.get("event_seq"))
                for row in rows
            )
            if key is not None
        ]
        newest = max(acquisition_keys) if acquisition_keys else None
        out = []
        for attempt in attempts:
            key = self._event_key(attempt.get("at"), attempt.get("event_seq"))
            flagged = dict(attempt)
            flagged["newer"] = bool(newest is not None and key is not None and key > newest)
            out.append(flagged)
        return out

    def _event_ledger_reconciled(self) -> str:
        """v5-review H4 + v6-review C2: the event ledger and the acquisition
        stores must reconcile in BOTH directions over the RAW persisted rows.
        A row without a claim, a claim without its central record, a mismatch,
        a duplicate, or a central acquisition/attempt event without its store
        row all fail closed — absence of proof is never success, and orphans
        stay visible (never swept, never fabricated)."""
        claims: dict[str, tuple[Any, ...]] = {}
        for store in ("receipts", "observations"):
            path = self._db_path(store)
            if not path.exists():
                continue
            for row in self._store_rows(store):
                event_id = row.get("event_id")
                event_seq = row.get("event_seq")
                if (
                    not isinstance(event_id, str)
                    or not event_id
                    or event_id in claims
                    or not isinstance(event_seq, int)
                    or isinstance(event_seq, bool)
                ):
                    return "mismatch"
                claims[event_id] = (
                    "acquisition", store, row["row_id"], row.get("event_at"),
                    event_seq,
                )
            try:
                with contextlib.closing(self._open_reader(path)) as conn:
                    attempt_rows = conn.execute(
                        "SELECT attempt_id, event_id, at, event_seq"
                        " FROM attempts ORDER BY seq"
                    ).fetchall()
            except sqlite3.Error:
                # The attempts relation is unreadable: any central attempt
                # event bound to this store is unprovable below.
                attempt_rows = []
            for attempt_id, event_id, at, event_seq in attempt_rows:
                if (
                    not isinstance(event_id, str)
                    or not event_id
                    or not isinstance(attempt_id, str)
                    or not attempt_id
                    or event_id in claims
                    or not isinstance(event_seq, int)
                    or isinstance(event_seq, bool)
                ):
                    return "mismatch"
                claims[event_id] = ("attempt", store, attempt_id, at, event_seq)
        path = self._db_path("semantics")
        central_rows: list[tuple[Any, ...]] = []
        if path.exists():
            try:
                with contextlib.closing(self._open_reader(path)) as conn:
                    central_rows = conn.execute(
                        "SELECT event_id, event_type, store_name, subject_id,"
                        " event_at, seq FROM event_sequence ORDER BY rowid"
                    ).fetchall()
            except sqlite3.Error:
                # v7-review C1: an unreadable central ledger is NEVER success,
                # even with zero store claims — it is the row-9 state.
                return "unreadable"
        # Every central row must be CLOSED — non-null text identity, a known
        # type, and a governed store binding — and identities must be unique
        # BEFORE any dictionary can collapse a duplicate.
        for row in central_rows:
            event_id, event_type, store_name, subject_id, event_at, seq = row
            if (
                not isinstance(event_id, str) or not event_id
                or event_type not in ("acquisition", "attempt")
                or store_name not in ("receipts", "observations")
                or not isinstance(subject_id, str) or not subject_id
                or not isinstance(event_at, str) or not event_at
                or not isinstance(seq, int) or isinstance(seq, bool)
            ):
                return "mismatch"
            # v8-review H3: persisted order facts are canonical or fail
            # closed — never a bare comparison exception downstream.
            try:
                _canonical_instant(event_at, now=self._now())
            except FootballguysIntakeError:
                return "mismatch"
        central_ids = [row[0] for row in central_rows]
        if len(central_ids) != len(set(central_ids)):
            return "mismatch"
        # v9-review H2: central sequences are a load invariant — strictly
        # increasing in insertion order and positive.  A duplicate or
        # reversed sequence can no longer prove which event was later, so it
        # is an integrity failure, never an equality that suppresses overlays.
        previous_seq = 0
        for row in central_rows:
            if row[5] <= previous_seq:
                return "mismatch"
            previous_seq = row[5]
        central = {
            row[0]: (row[1], row[2], row[3], row[4], row[5])
            for row in central_rows
        }
        for event_id, claim in claims.items():
            if central.get(event_id) != claim:
                return "mismatch"
        for event_id in central:
            if event_id not in claims:
                return "mismatch"
        return "reconciled"

    def _now(self) -> datetime:
        """The single clock dependency: inside read_model the validated
        instant is pinned once and reused everywhere (v9-review H4)."""
        pinned = getattr(self, "_read_clock", None)
        return pinned if pinned is not None else self.clock()

    def read_model(
        self, *, now: datetime, global_overall_status: str | None = None
    ) -> dict[str, Any]:
        # v9-review H4: the read clock is validated ONCE — an invalid clock
        # dependency is the named row-9 fail-closed state, never a bare
        # aware/naive comparison error deep in reconciliation.
        clock_now = self.clock()
        # v10-review M3: the clock dependency's TYPE is established before any
        # method dispatch — str/None/anything non-datetime is the same named
        # row-9 state, never an AttributeError.
        if not isinstance(clock_now, datetime):
            return evaluate_refresh_state(
                acquisitions=[],
                attempts=[{"status": "ledger_unreadable"}],
                now=now,
                global_overall_status=global_overall_status,
            )
        try:
            _canonical_instant(clock_now.isoformat(), now=None)
        except FootballguysIntakeError:
            return evaluate_refresh_state(
                acquisitions=[],
                attempts=[{"status": "ledger_unreadable"}],
                now=now,
                global_overall_status=global_overall_status,
            )
        self._read_clock = clock_now
        try:
            return self._read_model_locked(
                now=now, global_overall_status=global_overall_status
            )
        finally:
            self._read_clock = None

    def _read_model_locked(
        self, *, now: datetime, global_overall_status: str | None = None
    ) -> dict[str, Any]:
        rows = self._effective_acquisitions()
        loaded = self._load_attempts()
        if self._unreadable_stores:
            # H4 (v5) + H3 (v6): any unreadable governed relation renders
            # framing row 9 — a healthy sibling store never supplies a
            # fallback clock.
            attempts: list[dict[str, Any]] = [{"status": "ledger_unreadable"}]
            specials = list(self._effective_specials)
        else:
            ledger_state = self._event_ledger_reconciled()
            if ledger_state == "unreadable":
                attempts = [{"status": "ledger_unreadable"}]
                specials = list(self._effective_specials)
            elif ledger_state == "mismatch":
                attempts = []
                specials = list(self._effective_specials) + [
                    {"special": "integrity_failure", "id": "event-ledger"}
                ]
            else:
                attempts = self._flag_newer_attempts(loaded, rows)
                specials = list(self._effective_specials)
        return evaluate_refresh_state(
            acquisitions=rows + specials,
            attempts=attempts,
            now=now,
            global_overall_status=global_overall_status,
        )

    # -- snapshot ----------------------------------------------------------

    def _mode_map(self, paths: Iterable[str]) -> dict[str, int]:
        out: dict[str, int] = {}
        for rel in paths:
            path = self.root if rel == "." else self.root / rel
            if path.exists():
                out[rel] = stat_module.S_IMODE(os.lstat(path).st_mode)
        return out

    def snapshot(self) -> dict[str, Any]:
        staging = self._p("staging")
        staging_entries = (
            sorted(p.name for p in staging.iterdir()) if staging.exists() else []
        )
        objects_dir = self._p("objects")
        objects = (
            sorted(p.name for p in objects_dir.iterdir())
            if objects_dir.exists()
            else []
        )
        effective = self._effective_acquisitions()
        receipts = [
            {"offering_id": row["offering_id"], "receipt_id": row["id"]}
            for row in effective
            if row["kind"] == "receipt"
        ]
        observations = [
            {"offering_id": row["offering_id"], "observation_id": row["id"]}
            for row in effective
            if row["kind"] == "observation"
        ]
        state = evaluate_refresh_state(
            acquisitions=effective + list(self._effective_specials),
            attempts=[],
            now=self.clock(),
        )
        return {
            "trace": list(self.trace),
            "trusted_parent_modes": self._mode_map(_TRUSTED_PARENTS),
            "private_node_modes": self._mode_map(_PRIVATE_NODES),
            "lock_identity_count": len(self._lock_identities),
            "staging_entries": staging_entries,
            "objects": objects,
            "receipts": receipts,
            "observations": observations,
            "effective_acquisitions": effective,
            "clock_id": state["clock_id"],
            "latest_analysis_ready_id": state["latest_analysis_ready_id"],
            "last_crash_residue": self.last_crash_residue,
            "restart_contract": self.restart_contract,
            "open_raw_descriptors": self.open_raw_descriptors,
            "raw_provider_entries": [
                name
                for name in staging_entries
                if (staging / name).is_file() and (staging / name).stat().st_size > 0
            ],
        }


def build_contract_driver(
    *,
    repo_root: Path,
    manifest_path: Path,
    retention_mode: str,
    clock: Callable[[], datetime],
) -> ContractDriver:
    return ContractDriver(
        repo_root=Path(repo_root),
        manifest_path=Path(manifest_path),
        retention_mode=retention_mode,
        clock=clock,
    )
