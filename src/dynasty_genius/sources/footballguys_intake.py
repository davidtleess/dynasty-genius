"""Footballguys Phase A intake — archive acquisition and monthly refresh notice.

GREEN for ``tests/contract/test_footballguys_phase_a_red.py`` (pin ``1130f2bc…``),
implementing framing v25 (``f44b5ab0…``) under David's retention option 1
(full offsite raw backup, 2026-08-10).

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


# ---------------------------------------------------------------------------
# Semantic assertion reducer — over ALL active records, never a row filter
# ---------------------------------------------------------------------------


def _adjudication_is_governed(
    row: Mapping[str, Any], assertion_ids: set[str]
) -> bool:
    required = ("adjudication_id", "authority", "provenance", "parents", "effective_assertion_id")
    if not all(row.get(key) for key in required):
        return False
    return set(row["parents"]) >= assertion_ids


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
                r for r in active if r["assertion_id"] == row["effective_assertion_id"]
            )
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
            copy = head + " · no unambiguous refresh recorded"
            return _result("unverifiable", copy, 1, clock=None, ar=None)
        age = _age_days(clock_row["retrieved_at"], now)
        copy = head + f" · last unambiguous refresh recorded {age} days ago"
        copy += _ar_clause(ar_row if ar_row and ar_row is not clock_row else None)
        return _result(
            "unverifiable",
            copy,
            1,
            clock=clock_row["id"],
            ar=ar_row["id"] if ar_row and ar_row is not clock_row else None,
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
        copy = (
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

    newer_failed = any(a.get("status") == "failed" and a.get("newer") for a in attempts)
    newer_invalid = any(a.get("status") == "invalid" and a.get("newer") for a in attempts)
    bare_failed = any(a.get("status") == "failed" and not a.get("newer") for a in attempts)
    bare_invalid = any(a.get("status") == "invalid" and not a.get("newer") for a in attempts)

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

    def initialize_database(self, store: str) -> SimpleNamespace:
        self._ensure_namespace()
        self._require_coverage(RUNTIME_PATHS[store])
        trace: list[str] = []
        path = self._db_path(store)
        conn = sqlite3.connect(path)
        try:
            mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            trace.append("pragma_journal_mode_wal")
            if mode != "wal":
                raise _refuse(f"journal_mode_not_wal:{mode}")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS acquisitions ("
                " row_id TEXT PRIMARY KEY,"
                " offering_id TEXT UNIQUE,"
                " kind TEXT, retrieved_at TEXT, readiness TEXT, retention TEXT,"
                " content_vintage_id TEXT, archive_sha256 TEXT, archive_bytes INTEGER,"
                " analysis_ready INTEGER, signature BLOB)"
            )
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

    def _store_rows(self, store: str) -> list[dict[str, Any]]:
        path = self._db_path(store)
        if not path.exists():
            return []
        with contextlib.closing(
            sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        ) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM acquisitions WHERE offering_id != '_bootstrap'"
                " ORDER BY rowid"
            ).fetchall()
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
        try:
            with contextlib.closing(
                sqlite3.connect(f"file:{main}?mode=ro", uri=True)
            ) as conn:
                mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
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
        self.sweep_staging()
        staging_dir = self._p("staging")
        stage_name = f"stage-{hashlib.sha256(os.urandom(16)).hexdigest()[:12]}.tmp"
        stage_path = staging_dir / stage_name
        metadata_only = self.retention_mode == "metadata_only"

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

            os.write(fd, archive_bytes)
            os.fsync(fd)
            self.trace.append("source_stream")

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
                archive_bytes, role_paths=ROLE_PATHS, limits=ARCHIVE_LIMITS
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
            if canonical.exists():
                self._verify_existing_object(canonical, inspected)
                if fault_at == "receipt_commit_reuse":
                    return self._crash("no_new_residue", "keep_reference_set")
            else:
                self._require_coverage(RUNTIME_PATHS["objects"])
                os.link(stage_path, canonical)
                self.trace.append("publish_no_replace")
                os.unlink(stage_name, dir_fd=dir_fd)
                keep_staging = True  # name consumed by publish; nothing left to unlink
                if fault_at == "after_publish_before_dir_fsync":
                    keep_staging = True  # the staging NAME is already unlinked
                    return self._crash("canonical_optional", "reuse_or_republish")
                os.fsync(dir_fd)
                staged_info = os.fstat(fd)
                published = os.lstat(canonical)
                if (
                    not stat_module.S_ISREG(published.st_mode)
                    or published.st_nlink != 1
                    or (published.st_dev, published.st_ino)
                    != (staged_info.st_dev, staged_info.st_ino)
                ):
                    canonical.unlink(missing_ok=True)
                    raise _refuse("published_object_invalid")
                self.trace.append("published_inode_verify")
                os.close(fd)
                self.open_raw_descriptors -= 1
                fd = -1
                if fault_at == "receipt_commit_fresh":
                    return self._crash("canonical_orphan", "adopt_on_reuse")

            self._commit_acquisition(
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
                status="ready",
                raw_retained=True,
                receipt_id=acquisition_id,
                observation_id=acquisition_id,
            )
        except FootballguysIntakeError as exc:
            if exc.code.startswith(("offering_identity_conflict", "backup_coverage_missing")):
                raise
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

    def _crash(self, residue: str, restart: str) -> IntakeResult:
        self.last_crash_residue = residue
        self.restart_contract = restart
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
    ) -> None:
        if store not in self._db_initialized:
            self.initialize_database(store)
        with contextlib.closing(sqlite3.connect(self._db_path(store))) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO acquisitions"
                " (row_id, offering_id, kind, retrieved_at, readiness, retention,"
                "  content_vintage_id, archive_sha256, archive_bytes,"
                "  analysis_ready, signature)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    row_id,
                    offering["offering_id"],
                    kind,
                    canonical_at,
                    "ready" if kind == "receipt" else "metadata_only",
                    "retained" if kind == "receipt" else "metadata_only",
                    inspected["content_vintage_id"],
                    inspected["archive_sha256"],
                    inspected["archive_bytes"],
                    1 if kind == "receipt" else 0,
                    signature,
                ),
            )
            conn.commit()

    # -- effective acquisitions and read model -----------------------------

    def _effective_acquisitions(self) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for store, kind in (("observations", "observation"), ("receipts", "receipt")):
            for row in self._store_rows(store):
                recomputed = receipt_id(row["signature"])
                if recomputed != row["row_id"]:
                    row["integrity"] = "invalid"
                current = by_id.get(row["row_id"])
                if current is None or kind == "receipt":
                    by_id[row["row_id"]] = {
                        "id": row["row_id"],
                        "kind": kind,
                        "offering_id": row["offering_id"],
                        "retrieved_at": row["retrieved_at"],
                        "readiness": row["readiness"],
                        "retention": row["retention"],
                        "content_vintage_id": row["content_vintage_id"],
                        "analysis_ready": bool(row["analysis_ready"]),
                        "receipt_id": row["row_id"],
                        "valid": True,
                    }
        return sorted(
            by_id.values(), key=lambda row: (row["retrieved_at"], row["id"])
        )

    def read_model(
        self, *, now: datetime, global_overall_status: str | None = None
    ) -> dict[str, Any]:
        return evaluate_refresh_state(
            acquisitions=self._effective_acquisitions(),
            attempts=[],
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
            acquisitions=effective, attempts=[], now=self.clock()
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
