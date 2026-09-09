"""The immutable store for track-record enrollments and the grades that later reference them.

A track record is only worth reading if what was registered cannot change afterwards. So a record is
content-addressed: its id is a digest over its kind, its document and its artifact bytes. Saving the
same content twice returns the ORIGINAL receipt with its original time — a later clock never rewrites
an earlier registration. Reading a record whose bytes no longer hash to the id it is filed under is
corruption and raises; it never returns a value that has quietly drifted.

DG-207 writes its grades through this same module rather than a second store, which is why ``kind`` is
a closed set and why a grade's reference to its enrollment is verified on the way in. A grade's
``snapshot_id`` is read from its own document, never passed in beside it, so the two can never
disagree.

The root is defended the way ``workspace_snapshot_store`` defends the archive: a symlink anywhere in
the path is refused, because that is exactly how a private local directory silently becomes a shared
one. This is evaluation evidence and it is never public data.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSIONS = {
    "enrollment": "track_record.enrollment.v1",
    "grade": "track_record.grade.v1",
}
KINDS = tuple(SCHEMA_VERSIONS)

_PLATFORM_ALIASES = {Path("/tmp"), Path("/var")}


class TrackRecordStoreError(ValueError):
    """The record cannot be stored or trusted; the message says which rule failed."""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise TrackRecordStoreError(message)


def _store_root(root: Path | str) -> Path:
    """A private, real directory. Every symlink in the path is refused except the platform's own."""
    path = Path(root)
    for candidate in (path, *path.parents):
        if candidate.is_symlink() and candidate not in _PLATFORM_ALIASES:
            raise TrackRecordStoreError(
                f"the evaluation root passes through a symlink at {candidate}; "
                "this store holds private evidence and must be a real local directory"
            )
    return path if path.is_absolute() else path.resolve()


def _canonical(document: Any, *, what: str) -> bytes:
    """Stable bytes for hashing. Rejects the values JSON will happily carry and arithmetic will not."""
    def check(value: Any, path: str) -> None:
        if isinstance(value, bool):
            if path.endswith("eligible") or path.endswith("scored") or path.endswith("missing"):
                raise TrackRecordStoreError(f"{what}: {path} is a boolean, not a count")
            return
        if isinstance(value, float) and not math.isfinite(value):
            raise TrackRecordStoreError(f"{what}: {path} is {value!r}, which is not a number")
        if isinstance(value, Mapping):
            for key, item in value.items():
                _require(isinstance(key, str), f"{what}: a key at {path} is not a string")
                check(item, f"{path}.{key}" if path else str(key))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                check(item, f"{path}[{index}]")

    check(document, "")
    try:
        return json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as bad:
        raise TrackRecordStoreError(f"{what} cannot be written as JSON: {bad}") from bad


def _validated_artifacts(artifacts: Any) -> dict[str, bytes]:
    _require(isinstance(artifacts, Mapping), "the artifacts must be a mapping of name to bytes")
    out: dict[str, bytes] = {}
    for name, payload in artifacts.items():
        _require(isinstance(name, str) and name, "an artifact name is empty")
        _require("/" not in name and "\\" not in name and name not in {".", ".."},
                 f"the artifact name {name!r} is not a plain file name")
        _require(isinstance(payload, (bytes, bytearray)), f"the artifact {name} is not bytes")
        out[name] = bytes(payload)
    return out


def _instant(value: Any, what: str) -> str:
    _require(isinstance(value, datetime), f"{what} must be a datetime")
    assert isinstance(value, datetime)
    _require(value.tzinfo is not None, f"{what} must carry a timezone")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record_id(kind: str, document_bytes: bytes, artifacts: Mapping[str, bytes]) -> str:
    digest = hashlib.sha256()
    digest.update(kind.encode("utf-8"))
    digest.update(b"\0")
    digest.update(document_bytes)
    for name in sorted(artifacts):
        digest.update(b"\0")
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(artifacts[name]).hexdigest().encode("utf-8"))
    return digest.hexdigest()


def _snapshot_id_of(document: Mapping[str, Any]) -> str:
    value = document.get("snapshot_id")
    _require(isinstance(value, str) and value, "the document carries no snapshot_id")
    return str(value)


def _record_dir(root: Path, record_id: str) -> Path:
    _require(len(record_id) == 64 and all(c in "0123456789abcdef" for c in record_id),
             f"{record_id!r} is not a record id")
    return root / record_id[:2] / record_id


def _write_atomically(directory: Path, files: Mapping[str, bytes]) -> None:
    """Publish the whole record or none of it: build beside the destination, then rename once."""
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=directory.parent))
    try:
        for name, payload in files.items():
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        os.rename(staging, directory)
    except FileExistsError:
        # someone published the same content first; their copy stands
        for item in sorted(staging.rglob("*"), reverse=True):
            item.rmdir() if item.is_dir() else item.unlink()
        staging.rmdir()
    except BaseException:
        for item in sorted(staging.rglob("*"), reverse=True):
            item.rmdir() if item.is_dir() else item.unlink()
        staging.rmdir()
        raise


def _load(directory: Path, record_id: str) -> dict[str, Any]:
    receipt_path, document_path = directory / "receipt.json", directory / "document.json"
    _require(receipt_path.is_file() and document_path.is_file(),
             f"record {record_id} is incomplete on disk")
    try:
        receipt = json.loads(receipt_path.read_text())
        document = json.loads(document_path.read_text())
    except json.JSONDecodeError as bad:
        raise TrackRecordStoreError(f"record {record_id} holds unreadable JSON: {bad}") from bad

    artifacts: dict[str, bytes] = {}
    artifact_dir = directory / "artifacts"
    if artifact_dir.is_dir():
        artifacts = {p.name: p.read_bytes() for p in sorted(artifact_dir.iterdir()) if p.is_file()}

    kind = receipt.get("kind")
    _require(kind in KINDS, f"record {record_id} names an unknown kind {kind!r}")
    recomputed = _record_id(str(kind), _canonical(document, what="the stored document"), artifacts)
    if recomputed != record_id:
        raise TrackRecordStoreError(
            f"record {record_id} no longer matches its content (recomputed {recomputed}); "
            "the document or an artifact was changed after it was written"
        )
    return {
        "record_id": record_id,
        "kind": kind,
        "recorded_at": receipt["recorded_at"],
        "snapshot_id": receipt["snapshot_id"],
        "document": document,
        "artifact_hashes": receipt["artifact_hashes"],
    }


def _verify_references(root: Path, kind: str, document: Mapping[str, Any]) -> None:
    """A grade that points at an enrollment must point at one that exists."""
    if kind != "grade":
        return
    enrollment_id = document.get("enrollment_id")
    _require(isinstance(enrollment_id, str) and enrollment_id,
             "the grade carries no enrollment_id")
    directory = _record_dir(root, str(enrollment_id))
    if not directory.is_dir():
        raise TrackRecordStoreError(
            f"the grade references enrollment {enrollment_id}, which is not in this store"
        )
    referenced = _load(directory, str(enrollment_id))
    _require(referenced["kind"] == "enrollment",
             f"the grade's enrollment_id names a {referenced['kind']}, not an enrollment")


def save_record(
    root: Path | str, *, kind: str, document: Mapping[str, Any], artifacts: Mapping[str, bytes],
    recorded_at: datetime,
) -> dict[str, Any]:
    """Append one immutable record. Saving identical content again returns the FIRST receipt."""
    _require(kind in KINDS, f"the kind must be one of {KINDS}, not {kind!r}")
    _require(isinstance(document, Mapping), "the document must be a mapping")
    version = document.get("schema_version")
    _require(version == SCHEMA_VERSIONS[kind],
             f"the document's schema_version is {version!r}, not {SCHEMA_VERSIONS[kind]!r}")

    checked_artifacts = _validated_artifacts(artifacts)
    document_bytes = _canonical(document, what="the document")
    snapshot_id = _snapshot_id_of(document)
    stamp = _instant(recorded_at, "recorded_at")
    record_id = _record_id(kind, document_bytes, checked_artifacts)

    store = _store_root(root)
    _verify_references(store, kind, document)
    directory = _record_dir(store, record_id)
    if directory.exists():
        # Same content id. Confirm the bytes on disk really are that content before standing on them.
        return {"created": False, "record": _load(directory, record_id)}

    receipt = {
        "record_id": record_id,
        "kind": kind,
        "recorded_at": stamp,
        "snapshot_id": snapshot_id,
        "artifact_hashes": {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in sorted(checked_artifacts.items())
        },
    }
    files: dict[str, bytes] = {
        "document.json": document_bytes,
        "receipt.json": _canonical(receipt, what="the receipt"),
    }
    for name, payload in checked_artifacts.items():
        files[f"artifacts/{name}"] = payload
    _write_atomically(directory, files)
    return {"created": True, "record": _load(directory, record_id)}


def read_record(root: Path | str, record_id: str) -> dict[str, Any]:
    """One validated record. Corrupt content raises rather than returning a drifted value."""
    store = _store_root(root)
    directory = _record_dir(store, record_id)
    if not directory.is_dir():
        raise FileNotFoundError(f"no record {record_id}")
    return _load(directory, record_id)


def list_records(root: Path | str, *, snapshot_id: str) -> list[dict[str, Any]]:
    """Every record for one snapshot, in a stable recorded_at then record_id order."""
    store = _store_root(root)
    _require(isinstance(snapshot_id, str) and snapshot_id, "a snapshot_id is required")
    if not store.is_dir():
        return []
    found: list[dict[str, Any]] = []
    for shard in sorted(p for p in store.iterdir() if p.is_dir() and len(p.name) == 2):
        for directory in sorted(p for p in shard.iterdir() if p.is_dir()):
            record = _load(directory, directory.name)
            if record["snapshot_id"] == snapshot_id:
                found.append(record)
    found.sort(key=lambda r: (r["recorded_at"], r["record_id"]))
    return found
