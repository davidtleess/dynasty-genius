"""Isolated raw-to-curated publication wrapper for the existing CFBD enrichment."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cfbd_foundation.v1"
SOURCE_NAME = "cfbd"
MIN_IDENTITY_COVERAGE = 0.99


class CfbdRefreshError(RuntimeError):
    """Raised when a staged CFBD refresh cannot meet its publication contract."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _run_id(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    shutil.copyfile(source, temporary)
    os.replace(temporary, target)


@contextmanager
def _exclusive_lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "refresh.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise CfbdRefreshError(
            f"refresh lock exists at {lock_path}; another run may be active"
        ) from exc
    try:
        os.write(descriptor, b"cfbd_foundation_refresh\n")
        os.close(descriptor)
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def _validate_json_cache(raw_cache_dir: Path) -> tuple[int, str]:
    files = sorted(raw_cache_dir.glob("*.json"))
    if not files:
        raise CfbdRefreshError("CFBD builder produced no raw JSON cache files")
    combined = hashlib.sha256()
    for path in files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CfbdRefreshError(f"invalid raw JSON cache file: {path}") from exc
        combined.update(path.name.encode("utf-8"))
        combined.update(_sha256(path).encode("ascii"))
    return len(files), combined.hexdigest()


def _validate_curated(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise CfbdRefreshError(f"CFBD builder did not produce curated output: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise CfbdRefreshError("CFBD curated output contains zero rows")

    required = {"position", "gsis_id", "w2b_cfbd_degraded"}
    missing = required - set(rows[0])
    if missing:
        raise CfbdRefreshError(
            f"CFBD curated output missing required columns: {sorted(missing)}"
        )
    degraded = sum(row.get("w2b_cfbd_degraded") != "0" for row in rows)
    if degraded:
        raise CfbdRefreshError(
            f"CFBD curated output contains {degraded} degraded rows; refusing publish"
        )

    resolved = sum(bool((row.get("gsis_id") or "").strip()) for row in rows)
    coverage = resolved / len(rows)
    if coverage < MIN_IDENTITY_COVERAGE:
        raise CfbdRefreshError(
            f"CFBD identity coverage {coverage:.4%} is below "
            f"{MIN_IDENTITY_COVERAGE:.0%}"
        )
    source_columns = [
        column
        for column in rows[0]
        if column.endswith("_source")
        and any((row.get(column) or "").startswith("cfbd") for row in rows)
    ]
    if not source_columns:
        raise CfbdRefreshError(
            "CFBD curated output has no populated CFBD provenance source columns"
        )
    return {
        "row_count": len(rows),
        "identity_resolved_rows": resolved,
        "identity_coverage": coverage,
        "populated_source_columns": source_columns,
    }


def _read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run_cfbd_foundation_refresh(
    *,
    source_root: Path,
    input_path: Path,
    builder: Callable[[Path, Path], None],
    now_fn: Callable[[], datetime] = _utc_now,
) -> dict[str, Any]:
    """Execute the existing CFBD builder in isolation and atomically publish outputs."""
    if not input_path.exists():
        raise CfbdRefreshError(f"curation input does not exist: {input_path}")

    with _exclusive_lock(source_root):
        started_at_dt = now_fn()
        started_at = _iso_utc(started_at_dt)
        run_id = _run_id(started_at_dt)
        stage_root = source_root / f".stage-{run_id}"
        if stage_root.exists():
            raise CfbdRefreshError(f"staging path already exists: {stage_root}")
        raw_stage = stage_root / "raw_cache"
        curated_stage = stage_root / "curated" / "prospects_with_outcomes_v3.csv"
        raw_stage.mkdir(parents=True)
        curated_stage.parent.mkdir(parents=True)
        shutil.copyfile(input_path, curated_stage)
        input_hash_before = _sha256(input_path)

        try:
            builder(curated_stage, raw_stage)
            if _sha256(input_path) != input_hash_before:
                raise CfbdRefreshError(
                    "CFBD builder mutated the source input; refusing publish"
                )
            raw_file_count, raw_hash = _validate_json_cache(raw_stage)
            curated_quality = _validate_curated(curated_stage)
            curated_hash = _sha256(curated_stage)

            previous = _read_manifest(source_root / "manifest_latest.json")
            if (
                previous
                and previous.get("raw_content_sha256") == raw_hash
                and previous.get("curated_sha256") == curated_hash
            ):
                status = {
                    "schema_version": SCHEMA_VERSION,
                    "source": SOURCE_NAME,
                    "status": "noop",
                    "checked_at": started_at,
                    "last_changed_at": previous["captured_at"],
                    "raw_content_sha256": raw_hash,
                    "curated_sha256": curated_hash,
                }
                _atomic_json(source_root / "status_latest.json", status)
                return status

            raw_root = source_root / "raw" / run_id
            if raw_root.exists():
                raise CfbdRefreshError(
                    f"immutable raw run path already exists: {raw_root}"
                )
            raw_root.parent.mkdir(parents=True, exist_ok=True)
            os.replace(raw_stage, raw_root)

            curated_path = (
                source_root / "curated" / "prospects_with_outcomes_v3.csv"
            )
            _atomic_copy(curated_stage, curated_path)
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "source": SOURCE_NAME,
                "provider": "College Football Data",
                "run_id": run_id,
                "captured_at": started_at,
                "input_path": str(input_path),
                "input_sha256": input_hash_before,
                "raw_root": str(raw_root),
                "raw_file_count": raw_file_count,
                "raw_content_sha256": raw_hash,
                "curated_path": str(curated_path),
                "curated_sha256": curated_hash,
                **curated_quality,
            }
            _atomic_json(raw_root / "manifest.json", manifest)
            _atomic_json(source_root / "manifest_latest.json", manifest)
            status = {
                **manifest,
                "status": "ok",
                "last_changed_at": started_at,
            }
            _atomic_json(source_root / "status_latest.json", status)
            return status
        finally:
            if stage_root.exists():
                shutil.rmtree(stage_root)
