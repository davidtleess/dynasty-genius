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

#: Declared QB feature family. A declared family that publishes at 0% coverage is
#: a failed ingest wearing the costume of a legitimately sparse feature (G5).
QB_FEATURE_COLUMNS: tuple[str, ...] = (
    "qb_completion_pct_final",
    "qb_yards_per_attempt_final",
    "qb_td_int_ratio_final",
    "qb_sack_rate_final",
)

#: Plausible band for a qualifying college completion rate expressed as a
#: fraction (G4). The 2026-08-01 defect published 0.00594 for 62/62 rows — a
#: value no completion rate can take on any scale.
COMPLETION_PCT_BOUNDS: tuple[float, float] = (0.20, 0.95)

#: A published family may not lose more than this share of its coverage against
#: the previous manifest without an explicit decision (G5).
MAX_COVERAGE_REGRESSION = 0.05


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
    """Hash the raw snapshot, refusing anything that is not a raw API response.

    G6. CFBD endpoints return JSON arrays of objects. A bare scalar (the old
    `tpa_*` cache held `430.0`) or a normalized feature dict (the old
    `qb_stats_*` cache held the 11-key contract shape) is a *derivative*, not a
    snapshot. Storing derivatives here is why the 2026-08-01 investigation could
    not prove which player CFBD actually returned: the evidence was discarded
    before it was written.
    """
    files = sorted(raw_cache_dir.glob("*.json"))
    if not files:
        raise CfbdRefreshError("CFBD builder produced no raw JSON cache files")
    combined = hashlib.sha256()
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CfbdRefreshError(f"invalid raw JSON cache file: {path}") from exc
        if not isinstance(payload, list):
            raise CfbdRefreshError(
                f"{path.name} is not a raw API response: expected a JSON array of "
                f"objects, found {type(payload).__name__}. A normalized feature "
                f"dict or a scalar derivative is not a raw snapshot."
            )
        offenders = [item for item in payload if not isinstance(item, dict)]
        if offenders:
            raise CfbdRefreshError(
                f"{path.name} is not a raw API response: the array holds "
                f"non-object entries ({type(offenders[0]).__name__}). A scalar "
                f"or normalized derivative is not a raw snapshot."
            )
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

    qb_rows = [row for row in rows if (row.get("position") or "").upper() == "QB"]
    declared = [column for column in QB_FEATURE_COLUMNS if column in rows[0]]
    feature_coverage = _validate_qb_family(qb_rows, declared)

    return {
        "row_count": len(rows),
        "identity_resolved_rows": resolved,
        "identity_coverage": coverage,
        "populated_source_columns": source_columns,
        "feature_coverage": feature_coverage,
    }


def _validate_qb_family(
    qb_rows: list[dict[str, str]], declared: list[str]
) -> dict[str, float]:
    """Run the QB publication gates and return per-field coverage.

    G3 (collision), G4 (semantic range) and G5 (zero coverage). Each refusal
    names the players involved, because "some rows collided" is not actionable
    and the whole point of these gates is that a human can act on the refusal.
    """
    if not qb_rows or not declared:
        return {}

    # G4 — a qualifying completion rate outside any physically possible band.
    low, high = COMPLETION_PCT_BOUNDS
    if "qb_completion_pct_final" in declared:
        for row in qb_rows:
            raw = (row.get("qb_completion_pct_final") or "").strip()
            if not raw:
                continue
            try:
                value = float(raw)
            except ValueError as exc:
                raise CfbdRefreshError(
                    f"qb_completion_pct_final is not numeric for "
                    f"{row.get('gsis_id')}: {raw!r}"
                ) from exc
            if not low <= value <= high:
                raise CfbdRefreshError(
                    f"qb_completion_pct_final {value} for {row.get('gsis_id')} is "
                    f"outside the plausible range [{low}, {high}]; a completion "
                    f"rate cannot take this value on any scale"
                )

    # G3 — distinct players carrying a byte-identical complete feature vector.
    complete: dict[tuple[str, ...], set[str]] = {}
    for row in qb_rows:
        values = tuple((row.get(column) or "").strip() for column in declared)
        if not all(values):
            continue  # an incomplete vector cannot evidence a collision
        # Scoped to the season: the defect spread ONE season's payload across
        # that season's quarterbacks. Two players in different seasons sharing a
        # rounded vector is coincidence, and flagging it would be a false alarm.
        key = (str(row.get("season") or ""), *values)
        complete.setdefault(key, set()).add(str(row.get("gsis_id") or "?"))
    for values, players in complete.items():
        # Distinct players, not row count: a duplicated row for ONE player is a
        # different defect and must not be reported as a cross-player collision.
        if len(players) > 1:
            raise CfbdRefreshError(
                f"identical complete QB feature vector shared by {len(players)} "
                f"distinct players ({', '.join(sorted(players)[:6])}): {values}. A "
                f"cross-player collision means the response was not bound to a "
                f"player."
            )

    # G5 — a declared family that publishes at zero coverage.
    coverage: dict[str, float] = {}
    for column in declared:
        populated = sum(1 for row in qb_rows if (row.get(column) or "").strip())
        coverage[column] = populated / len(qb_rows)
        if populated == 0:
            raise CfbdRefreshError(
                f"declared QB feature {column} has 0% coverage across "
                f"{len(qb_rows)} QB rows; a fully dark declared family is a "
                f"failed ingest, not a sparse feature"
            )
    return coverage


def _read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_coverage_retention(
    previous: Mapping[str, Any] | None, curated_quality: Mapping[str, Any]
) -> None:
    """Refuse a publish that materially loses feature coverage (G5).

    The 2026-07-31 run published `status: ok` while dropping QB values relative
    to the vintage it replaced. A refresh that knows less than its predecessor
    is a regression, and publishing it silently is how a source gets quietly
    worse while every status marker stays green.
    """
    if not previous:
        return
    before = previous.get("feature_coverage") or {}
    after = curated_quality.get("feature_coverage") or {}
    regressions = []
    for column, previous_value in before.items():
        if column not in after:
            regressions.append(f"{column}: {previous_value:.1%} -> absent")
            continue
        if after[column] < previous_value - MAX_COVERAGE_REGRESSION:
            regressions.append(
                f"{column}: {previous_value:.1%} -> {after[column]:.1%}"
            )
    if regressions:
        raise CfbdRefreshError(
            "CFBD curated output regresses feature coverage against the previous "
            f"manifest ({'; '.join(sorted(regressions))}); refusing publish. "
            "Coverage retention is a publication gate, not a warning."
        )


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

            _validate_coverage_retention(previous, curated_quality)

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
