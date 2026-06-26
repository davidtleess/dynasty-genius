"""F-feature-refresh T2 — atomic, fail-closed publish of a validated feature candidate.

`publish_runtime` validates a candidate (via `feature_validation`) and, ONLY if every gate
passes, atomically promotes it to the runtime CSV alongside a ready marker and a refresh
report. An invalid candidate NEVER replaces a prior valid runtime; a write failure mid-publish
restores the prior runtime/ready bytes. The report and ready marker carry
`decision_supported=false` and contain no David-facing decision language.

This module publishes a derived FEATURE artifact only — it trains nothing and writes no model.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from src.dynasty_genius.features.feature_validation import (
    ValidationResult,
    validate_feature_candidate,
)

_RUNTIME_NAME = "engine_b_features_runtime.csv"
_READY_NAME = "engine_b_features_runtime.ready.json"
_REPORT_NAME = "feature_refresh_latest_report.json"

# Defaults so callers that only pin coverage params still get the integrity gates the
# committed seed satisfies.
DEFAULT_CRITICAL_FEATURES: tuple[str, ...] = ("snap_share", "games_t", "ppg_t", "age")
DEFAULT_MAX_NULL_RATE_BY_COLUMN: dict[str, float] = {
    "snap_share": 0.0,
    "games_t": 0.0,
    "ppg_t": 0.0,
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = Path(f"{path}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _restore(path: Path, prior_bytes: Optional[bytes]) -> None:
    """Restore a path to its pre-publish state (rewrite prior bytes, or remove if none)."""
    if prior_bytes is not None:
        path.write_bytes(prior_bytes)
    elif path.exists():
        path.unlink()


def _validation_payload(validation: ValidationResult) -> dict:
    return {
        "ok": validation.ok,
        "failures": validation.failures,
        "drift": validation.drift,
    }


def _write_report(
    report_path: Path,
    *,
    status: str,
    validation: dict,
    runtime_sha256: Optional[str] = None,
    blocked_reason: Optional[str] = None,
) -> None:
    report: dict = {"status": status, "decision_supported": False, "validation": validation}
    if runtime_sha256 is not None:
        report["runtime_sha256"] = runtime_sha256
    if blocked_reason is not None:
        report["blocked_reason"] = blocked_reason
    _atomic_write_text(report_path, json.dumps(report, sort_keys=True))


def publish_runtime(
    candidate_path: Path | str,
    *,
    runtime_dir: Path | str,
    inference_season: int,
    min_total_rows: int,
    min_position_rows: dict[str, int],
    critical_features: tuple[str, ...] = DEFAULT_CRITICAL_FEATURES,
    max_null_rate_by_column: Optional[dict[str, float]] = None,
    replace_fn: Optional[Callable[..., None]] = None,
) -> dict:
    """Validate then atomically publish a candidate to the runtime (fail-closed)."""
    runtime_dir = Path(runtime_dir)
    candidate_path = Path(candidate_path)
    runtime_path = runtime_dir / _RUNTIME_NAME
    ready_path = runtime_dir / _READY_NAME
    report_path = runtime_dir / _REPORT_NAME
    max_null = (
        DEFAULT_MAX_NULL_RATE_BY_COLUMN
        if max_null_rate_by_column is None
        else max_null_rate_by_column
    )
    replace = replace_fn if replace_fn is not None else os.replace

    runtime_dir.mkdir(parents=True, exist_ok=True)
    candidate = pd.read_csv(candidate_path)
    prior = pd.read_csv(runtime_path) if runtime_path.exists() else None

    validation = validate_feature_candidate(
        candidate,
        inference_season=inference_season,
        min_total_rows=min_total_rows,
        min_position_rows=min_position_rows,
        critical_features=critical_features,
        max_null_rate_by_column=max_null,
        prior_runtime=prior,
    )
    validation_payload = _validation_payload(validation)

    # Fail-closed: an invalid candidate blocks WITHOUT touching the prior runtime/ready.
    if not validation.ok:
        _write_report(report_path, status="blocked", validation=validation_payload)
        return {
            "status": "blocked",
            "publish_performed": False,
            "decision_supported": False,
            "restored_from_backup": False,
            "validation": validation_payload,
            "blocked_reason": "; ".join(validation.failures),
            "dirty_paths": [str(report_path)],
        }

    # Valid: atomic temp -> replace -> ready, with restore-on-failure of the prior runtime.
    prior_runtime_bytes = runtime_path.read_bytes() if runtime_path.exists() else None
    prior_ready_bytes = ready_path.read_bytes() if ready_path.exists() else None
    tmp_runtime = runtime_dir / f"{_RUNTIME_NAME}.tmp"
    try:
        candidate.to_csv(tmp_runtime, index=False)
        replace(str(tmp_runtime), str(runtime_path))
        runtime_sha256 = _sha256_file(runtime_path)
        ready = {
            "status": "ok",
            "runtime_sha256": runtime_sha256,
            "inference_season": inference_season,
            "decision_supported": False,
            "validation": validation_payload,
        }
        _atomic_write_text(ready_path, json.dumps(ready, sort_keys=True))
    except Exception as exc:
        _restore(runtime_path, prior_runtime_bytes)
        _restore(ready_path, prior_ready_bytes)
        if tmp_runtime.exists():
            tmp_runtime.unlink()
        _write_report(
            report_path,
            status="blocked",
            validation=validation_payload,
            blocked_reason=str(exc),
        )
        return {
            "status": "blocked",
            "publish_performed": False,
            "decision_supported": False,
            "restored_from_backup": prior_runtime_bytes is not None,
            "validation": validation_payload,
            "blocked_reason": str(exc),
            "dirty_paths": [str(report_path)],
        }

    _write_report(
        report_path,
        status="ok",
        validation=validation_payload,
        runtime_sha256=runtime_sha256,
    )
    return {
        "status": "ok",
        "publish_performed": True,
        "decision_supported": False,
        "runtime_promotable_to_seed": True,
        "runtime_sha256": runtime_sha256,
        "runtime_path": str(runtime_path),
        "ready_path": str(ready_path),
        "validation": validation_payload,
        "dirty_paths": [str(runtime_path), str(ready_path), str(report_path)],
    }
