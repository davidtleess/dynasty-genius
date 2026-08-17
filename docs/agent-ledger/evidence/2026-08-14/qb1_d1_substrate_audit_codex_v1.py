"""Read-only audit of the David-authorized QB-1 D1 raw substrate."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.adapters.nflreadpy_qb_adapter import (
    VALIDATION_DATASET_COLUMNS,
)
from src.dynasty_genius.eval.qb_validation.sources import VALIDATION_DATASETS


RAW_ROOT = ROOT / "app/data/backtest/qb_validation/raw"
MANIFEST_PATH = RAW_ROOT / "fetch_manifest.json"
EXPECTED_SEASONS = set(range(2015, 2026))
EXPECTED_REGISTRATION_PIN = (
    "37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _season_values(frame: pl.LazyFrame) -> set[int]:
    rows = frame.select(pl.col("season").cast(pl.Int64).unique()).collect()
    return {int(value) for value in rows["season"].to_list()}


def main() -> int:
    failures: list[str] = []
    manifest = json.loads(MANIFEST_PATH.read_text())

    if manifest.get("operation") != "qb1_d1_seven_dataset_fetch":
        failures.append("operation mismatch")
    if manifest.get("registration_pin") != EXPECTED_REGISTRATION_PIN:
        failures.append("registration pin mismatch")
    if manifest.get("decision_supported") is not False:
        failures.append("decision_supported must be false")
    if manifest.get("nflreadpy_version") != "0.1.5":
        failures.append("nflreadpy version mismatch")
    if manifest.get("authorization", {}).get("word_verbatim") != (
        "run the seven fetches - authorized"
    ):
        failures.append("authorization word mismatch")

    started = datetime.fromisoformat(manifest["started_at"])
    finished = datetime.fromisoformat(manifest["finished_at"])
    if started.tzinfo is None or finished.tzinfo is None or not started < finished:
        failures.append("fetch window must be aware and increasing")

    datasets = manifest.get("datasets")
    if not isinstance(datasets, dict) or tuple(datasets) != tuple(sorted(datasets)):
        failures.append("datasets must be a sorted mapping")
    if set(datasets or {}) != set(VALIDATION_DATASETS):
        failures.append(
            f"dataset set mismatch: {sorted(datasets or {})} != {sorted(VALIDATION_DATASETS)}"
        )

    declared_paths: set[Path] = set()
    audited: list[dict[str, object]] = []
    total_bytes = 0
    total_snapshots = 0
    manifest_mtime = MANIFEST_PATH.stat().st_mtime_ns

    for dataset in VALIDATION_DATASETS:
        entry = datasets[dataset]
        snapshots = entry.get("snapshots")
        if not isinstance(snapshots, list) or not snapshots:
            failures.append(f"{dataset}: missing snapshots")
            continue
        for snapshot in snapshots:
            total_snapshots += 1
            relative = Path(snapshot["file"])
            path = ROOT / relative
            if RAW_ROOT not in path.resolve().parents:
                failures.append(f"{dataset}: path escapes raw root: {relative}")
                continue
            if path in declared_paths:
                failures.append(f"{dataset}: duplicate path: {relative}")
            declared_paths.add(path)
            if not path.is_file() or path.is_symlink():
                failures.append(f"{dataset}: missing or symlink snapshot: {relative}")
                continue
            actual_bytes = path.stat().st_size
            actual_sha = _sha256(path)
            total_bytes += actual_bytes
            if actual_bytes != snapshot.get("bytes"):
                failures.append(f"{dataset}: byte mismatch: {relative}")
            if actual_sha != snapshot.get("sha256"):
                failures.append(f"{dataset}: sha mismatch: {relative}")
            if path.stat().st_mtime_ns > manifest_mtime:
                failures.append(f"{dataset}: snapshot newer than completion manifest: {relative}")

            frame = pl.scan_parquet(path)
            schema = frame.collect_schema()
            rows = frame.select(pl.len()).collect().item()
            columns = len(schema)
            if rows != snapshot.get("rows"):
                failures.append(f"{dataset}: row mismatch: {relative}")
            if columns != snapshot.get("columns"):
                failures.append(f"{dataset}: column mismatch: {relative}")
            missing = sorted(set(VALIDATION_DATASET_COLUMNS[dataset]) - set(schema.names()))
            if missing:
                failures.append(f"{dataset}: missing pinned columns {missing}")

            seasons: list[int] | None = None
            if dataset in {"weekly", "season_summary", "rosters"}:
                observed = _season_values(frame)
                seasons = sorted(observed)
                if observed != EXPECTED_SEASONS:
                    failures.append(f"{dataset}: season coverage {seasons}")
            elif dataset == "pbp":
                observed = _season_values(frame)
                seasons = sorted(observed)
                expected = int(path.stem.rsplit("_", 1)[-1])
                if observed != {expected}:
                    failures.append(f"pbp: {relative} has seasons {seasons}")
            elif dataset == "draft_picks":
                observed = _season_values(frame)
                if not set(range(1980, 2026)).issubset(observed):
                    failures.append("draft_picks: incomplete admitted 1980-2025 coverage")

            audited.append(
                {
                    "dataset": dataset,
                    "file": str(relative),
                    "rows": rows,
                    "columns": columns,
                    "bytes": actual_bytes,
                    "sha256": actual_sha,
                    "seasons": seasons,
                }
            )

    actual_parquet = set(RAW_ROOT.rglob("*.parquet"))
    if actual_parquet != declared_paths:
        failures.append(
            "manifest/file census mismatch: "
            f"extra={sorted(str(p.relative_to(ROOT)) for p in actual_parquet - declared_paths)} "
            f"missing={sorted(str(p.relative_to(ROOT)) for p in declared_paths - actual_parquet)}"
        )
    if total_snapshots != 17:
        failures.append(f"snapshot count {total_snapshots} != 17")
    if total_bytes != 154_360_748:
        failures.append(f"byte total {total_bytes} != 154360748")

    backup = json.loads((ROOT / "app/config/backup_manifest.json").read_text())
    backup_entries = [
        item
        for item in backup.get("required", [])
        if item.get("path") == "app/data/backtest/qb_validation/raw"
    ]
    if backup_entries != [
        {
            "path": "app/data/backtest/qb_validation/raw",
            "required": True,
            "kind": "directory",
        }
    ]:
        failures.append(f"backup entry mismatch: {backup_entries}")

    result = {
        "status": "failed" if failures else "passed",
        "manifest_sha256": _sha256(MANIFEST_PATH),
        "datasets": list(VALIDATION_DATASETS),
        "snapshots": total_snapshots,
        "bytes": total_bytes,
        "audited": audited,
        "failures": failures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
