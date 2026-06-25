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
    publish_fn: Optional[Callable[..., dict]] = None,
    preflight: bool = False,
) -> dict[str, Any]:
    """Source-hash-gated candidate regeneration with optional validated publish.

    Returns a status dict; `noop` when the source hash matches the last recorded hash
    (no assemble, no write). Otherwise it derives a fresh candidate. When `publish_fn` is
    None it stops at `candidate_ready` (T1 behaviour). When `publish_fn` is supplied it is
    invoked on the candidate (T2 atomic, fail-closed publish): `ok` on a validated publish,
    `blocked` if the candidate fails validation or the publish write fails. NEVER trains a
    model or writes a model artifact.
    """
    runtime_dir = Path(runtime_dir)
    report_path = runtime_dir / "feature_refresh_latest_report.json"
    candidate_path = runtime_dir / "engine_b_features_candidate.csv"
    source_hash = (source_inputs or {}).get("source_hash")

    last_hash: Optional[str] = None
    last_status: Optional[str] = None
    if report_path.exists():
        try:
            last_report = json.loads(report_path.read_text())
            last_hash = last_report.get("source_hash")
            last_status = last_report.get("status")
        except (ValueError, OSError):
            last_hash = None
            last_status = None

    # Noop only from a NON-blocked prior state. A blocked publish may disclose its
    # source_hash for audit, but must never make an identical-source retry skip forever
    # when no validated runtime was produced (Codex F1: noop poisoning). A bare legacy
    # report (no status) and accepted states (candidate_ready / ok) remain noop-eligible.
    if last_hash is not None and last_hash == source_hash and last_status != "blocked":
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

    # Source changed/new — derive a fresh candidate.
    candidate = assemble_fn(
        read_fns=read_fns, seasons_window=(source_inputs or {}).get("seasons_window")
    )
    runtime_dir.mkdir(parents=True, exist_ok=True)
    candidate.to_csv(candidate_path, index=False)

    if publish_fn is None:
        # T1 behaviour: candidate only, record the source hash + accepted status for
        # noop gating.
        report_path.write_text(
            json.dumps(
                {
                    "status": "candidate_ready",
                    "source_hash": source_hash,
                    "generated_at": now_fn().isoformat(),
                },
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

    # T2: validate + atomically publish the candidate (fail-closed inside publish_fn).
    publish_result = publish_fn(candidate_path, runtime_dir=runtime_dir)
    # Preserve source-hash noop gating: fold source_hash into whatever report publish wrote.
    _record_source_hash(report_path, source_hash, now_fn)

    if publish_result.get("status") == "ok":
        return {
            "status": "ok",
            "publish_performed": True,
            "refresh_performed": True,
            "decision_supported": False,
            "source_hash": source_hash,
            "candidate_path": str(candidate_path),
            "runtime_path": publish_result.get("runtime_path"),
            "runtime_sha256": publish_result.get("runtime_sha256"),
            "dirty_paths": publish_result.get("dirty_paths", [str(candidate_path)]),
            "commit_required_for_repo_baseline": False,
        }
    return {
        "status": "blocked",
        "publish_performed": False,
        "refresh_performed": True,
        "decision_supported": False,
        "source_hash": source_hash,
        "candidate_path": str(candidate_path),
        "validation": publish_result.get("validation"),
        "blocked_reason": publish_result.get("blocked_reason"),
        "dirty_paths": [str(candidate_path)],
        "commit_required_for_repo_baseline": False,
    }


def _record_source_hash(
    report_path: Path, source_hash: Optional[str], now_fn: Callable[[], Any]
) -> None:
    """Merge the source hash into the refresh report (preserves noop gating post-publish)."""
    report: dict[str, Any] = {}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text())
        except (ValueError, OSError):
            report = {}
    report["source_hash"] = source_hash
    report["generated_at"] = now_fn().isoformat()
    report_path.write_text(json.dumps(report, sort_keys=True))
