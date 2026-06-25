"""F-feature-refresh T1 — source-hash-gated refresh runner (candidate only).

Regenerates the engine_b feature candidate when the upstream source actually changed
(honest `noop` otherwise). T1 writes a CANDIDATE only — it does NOT publish a runtime,
read runtime in production, or run a scheduler (those are T2+). It derives features
ONLY: it never calls a model `.fit`, imports a training entrypoint, or writes a model
artifact (enforced by the T1 audit test).

T1 status semantics: `candidate_ready` (source changed → candidate written, NOT
published), `noop` (source unchanged vs the last recorded hash), `blocked` (error).
`publish_performed` is always False in T1; `ok`/publish is introduced in T2.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

# Wall-clock / audit-only keys excluded from the source hash (C4/C5): the hash must
# reflect source CONTENT, never run time, so identical data on a later run still noops.
_AUDIT_ONLY_CONFIG_KEYS = frozenset({"generated_at"})


def _canonical_frame(df: pd.DataFrame) -> str:
    """Deterministic, content-sensitive serialization of a source frame."""
    cols = sorted(map(str, df.columns))
    return df.reindex(columns=cols).to_csv(index=False)


def compute_source_hash(
    *,
    loader_outputs: dict[str, pd.DataFrame],
    seasons_window: list[int],
    package_version: Optional[str],
    builder_config: Optional[dict],
    te_rubric_artifacts: Any,
    identity_inputs: Any,
) -> str:
    """Canonical hash over the defined source-input set (C4); excludes wall-clock (C5)."""
    config = {
        k: v for k, v in (builder_config or {}).items() if k not in _AUDIT_ONLY_CONFIG_KEYS
    }
    payload = {
        "seasons_window": list(seasons_window),
        "package_version": package_version,
        "builder_config": config,
        "te_rubric_artifacts": te_rubric_artifacts,
        "identity_inputs": identity_inputs,
        "loader_outputs": {
            name: _canonical_frame(frame)
            for name, frame in sorted((loader_outputs or {}).items())
        },
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def run_feature_refresh(
    *,
    runtime_dir: Path | str,
    seed_path: Path | str,
    now_fn: Callable[[], Any],
    read_fns: dict[str, Any],
    source_inputs: dict[str, Any],
    assemble_fn: Callable[..., pd.DataFrame],
    preflight: bool = False,
) -> dict[str, Any]:
    """Source-hash-gated candidate regeneration (T1: no publish, no model writes).

    Returns a status dict; `noop` when the source hash matches the last recorded hash
    (no assemble, no write), else `candidate_ready` (writes the candidate + records the
    hash). NEVER publishes a runtime or touches model artifacts in T1.
    """
    runtime_dir = Path(runtime_dir)
    report_path = runtime_dir / "feature_refresh_latest_report.json"
    candidate_path = runtime_dir / "engine_b_features_candidate.csv"
    source_hash = (source_inputs or {}).get("source_hash")

    last_hash: Optional[str] = None
    if report_path.exists():
        try:
            last_hash = json.loads(report_path.read_text()).get("source_hash")
        except (ValueError, OSError):
            last_hash = None

    if last_hash is not None and last_hash == source_hash:
        return {
            "status": "noop",
            "publish_performed": False,
            "refresh_performed": False,
            "decision_supported": False,
            "source_hash": source_hash,
            "source_hash_unchanged": True,
            "dirty_paths": [],
            "commit_required_for_repo_baseline": False,
        }

    # Source changed/new — derive a fresh CANDIDATE only (no publish in T1).
    candidate = assemble_fn(
        read_fns=read_fns, seasons_window=(source_inputs or {}).get("seasons_window")
    )
    runtime_dir.mkdir(parents=True, exist_ok=True)
    candidate.to_csv(candidate_path, index=False)
    report_path.write_text(
        json.dumps(
            {"source_hash": source_hash, "generated_at": now_fn().isoformat()},
            sort_keys=True,
        )
    )
    return {
        "status": "candidate_ready",
        "publish_performed": False,
        "refresh_performed": True,
        "decision_supported": False,
        "source_hash": source_hash,
        "candidate_path": str(candidate_path),
        "dirty_paths": [str(candidate_path)],
        "commit_required_for_repo_baseline": False,
    }
