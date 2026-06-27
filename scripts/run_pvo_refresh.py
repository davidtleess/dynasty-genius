"""Dual Daily PIT Capture — T4 PVO-refresh runner (Option C, local-refresh-no-commit).

Refreshes the two TRACKED PVO artifacts in place locally (Phase-17.2 PVO rebuild only),
then optionally calls the independent T3 capture path. Option C discipline:
- mutates ONLY universe_pvo_latest.json + universe_pvo_coverage_latest.json
- NEVER auto-commits; a dirty working tree after a refresh is EXPECTED local state
- NEVER runs the full league-intelligence chain or any feature/training/model producer
- backup/restore so a failed refresh leaves both artifacts byte-identical
- emits a refresh report (pre/post 3-hash, dirty_paths, commit_required_for_repo_baseline,
  decision_supported=false)

The committed artifacts stay tracked (load-bearing for 4 API routes); committing a
refreshed baseline is a David-gated action. The scheduler + first live run are T5.

Spec: docs/superpowers/specs/2026-06-24-model-output-forward-capture-brick-design.md (§7/§7a)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.capture.model_forward_capture_driver import (  # noqa: E402
    _canon,
    _semantic_projection,
    _sha,
    capture_model_pvo_snapshot,
    resolve_provenance_subset,
)

DEFAULT_PVO_PATH = "app/data/valuation/universe_pvo_latest.json"
DEFAULT_COVERAGE_PATH = "app/data/valuation/universe_pvo_coverage_latest.json"
PHASE = "phase17_2_pvo_rebuild_only"

# F-seed-split T2a: gitignored runtime artifact + marker names. MUST match the names the
# resolver reads in src/dynasty_genius/pvo_source.py (single source of the runtime contract).
_RUNTIME_PVO_NAME = "universe_pvo_runtime.json"
_RUNTIME_COVERAGE_NAME = "universe_pvo_coverage_runtime.json"
_RUNTIME_MARKER_NAME = "universe_pvo_runtime.ready.json"
# Default gitignored runtime dir for the scheduled refresh, and the producer run-id whose
# output filenames equal the publisher's candidate paths (universe_pvo_<run_id>.json).
DEFAULT_RUNTIME_DIR = "app/data/valuation_runtime"
_CANDIDATE_RUN_ID = "candidate"
_FORBIDDEN_TOKENS = (
    "refresh_league_intelligence",
    "assemble_engine_b_dataset",
    "train_engine_b",
)


def assert_allowed_refresh_command(cmd: list[Any]) -> None:
    """Allow ONLY the Phase-17.2 PVO rebuild; reject git and any other producer."""
    parts = [str(c) for c in cmd]
    joined = " ".join(parts)
    if parts and parts[0] == "git":
        raise ValueError(f"forbidden refresh command (git/commit/add not allowed): {joined}")
    for token in _FORBIDDEN_TOKENS:
        if token in joined:
            raise ValueError(f"forbidden refresh command ({token}): {joined}")
    if "build_universe_pvo_batch" not in joined:
        raise ValueError(
            f"forbidden refresh command (only Phase-17.2 build_universe_pvo_batch allowed): {joined}"
        )


def _git_head_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def _phase17_2_refresh(*, pvo_artifact_path: Path, coverage_artifact_path: Path) -> None:
    """Run ONLY the Phase-17.2 PVO rebuild producer into the candidate paths' dir (no chain,
    no commit). F-seed-split T2a: steer the producer at the CANDIDATE output dir via
    --output-dir under the 'candidate' run-id, so it writes exactly the candidate pair the
    publisher promotes (universe_pvo_candidate.json / universe_pvo_coverage_candidate.json) —
    a temp/runtime location, never the tracked seed dir when called in runtime mode."""
    out_dir = Path(pvo_artifact_path).parent
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_universe_pvo_batch.py"),
        "--output-dir",
        str(out_dir),
        "--run-id",
        _CANDIDATE_RUN_ID,
    ]
    assert_allowed_refresh_command(cmd)
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _artifact_hashes(
    pvo_bytes: bytes,
    *,
    read_artifact: Callable[[Any], bytes],
    feature_source: Optional[Any] = None,
) -> dict[str, Optional[str]]:
    """3-hash snapshot of a PVO artifact: literal audit / semantic output / provenance.

    provenance_hash is LINEAGE-GRADE (the same T2 subset: producer + Engine-B manifest/
    per-position/feature hashes + derived cutoff + Engine-A pointers) so a model/feature/
    producer change is detected even when the scored output is unchanged. Raises
    FileNotFoundError if required model provenance is unresolvable (caller aborts+restores).

    ``feature_source`` may pin a ``ResolvedFeatureSource`` so injected-artifact-reader tests
    hash the seed/runtime they intend, independent of ambient gitignored runtime files after
    a feature-refresh catch-up; when None the ambient resolver runs (the production path).
    """
    artifact_sha256 = _sha(pvo_bytes)
    try:
        pvo = json.loads(pvo_bytes)
    except (json.JSONDecodeError, ValueError):
        return {
            "artifact_sha256": artifact_sha256,
            "semantic_output_hash": None,
            "provenance_hash": None,
        }
    players = pvo.get("players") or []
    return {
        "artifact_sha256": artifact_sha256,
        "semantic_output_hash": _sha(_canon([_semantic_projection(r) for r in players])),
        "provenance_hash": _sha(
            _canon(
                resolve_provenance_subset(
                    pvo, read_artifact=read_artifact, feature_source=feature_source
                )
            )
        ),
    }


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp = Path(f"{path}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = Path(f"{path}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _restore_bytes(path: Path, prior: Optional[bytes]) -> None:
    """Restore a runtime path to its pre-publish bytes (or remove it if there were none)."""
    if prior is not None:
        path.write_bytes(prior)
    elif path.exists():
        path.unlink()


def _publish_runtime(
    *,
    runtime_dir: Path,
    refresh_fn: Callable[..., None],
    report_path: Optional[Path],
    capture_fn: Optional[Callable[..., dict]],
    capture_db_path: Optional[Path],
    capture_report_path: Optional[Path],
    read_artifact: Callable[[Any], bytes],
    now_fn: Callable[[], datetime],
) -> dict[str, Any]:
    """F-seed-split T2a: publish the PVO pair to the gitignored runtime dir (seed-split mode).

    The producer writes a CANDIDATE pair into a temp dir OUTSIDE the runtime dir; we then
    ATOMICALLY promote the pair (+ a both-hash ready marker) into ``runtime_dir`` via
    temp-then-rename, backing up the prior runtime first and restoring it on ANY publish
    failure (never a half-written runtime). The tracked seed path is NEVER written, so
    ``dirty_paths`` is empty and a baseline commit is NOT required (Option C, no auto-commit)."""
    runtime_dir = Path(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_pvo = runtime_dir / _RUNTIME_PVO_NAME
    runtime_coverage = runtime_dir / _RUNTIME_COVERAGE_NAME
    marker_path = runtime_dir / _RUNTIME_MARKER_NAME

    def _persist(report: dict) -> dict:
        if report_path is not None:
            Path(report_path).parent.mkdir(parents=True, exist_ok=True)
            Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True))
        return report

    # 1. Producer writes the candidate pair into a temp dir OUTSIDE runtime_dir (so a producer
    #    failure cannot touch the prior runtime, and the seed path is never a candidate target).
    with tempfile.TemporaryDirectory(prefix="pvo_candidate_") as tmp:
        cand_pvo = Path(tmp) / "universe_pvo_candidate.json"
        cand_coverage = Path(tmp) / "universe_pvo_coverage_candidate.json"
        try:
            refresh_fn(pvo_artifact_path=cand_pvo, coverage_artifact_path=cand_coverage)
            pvo_bytes = cand_pvo.read_bytes()
            coverage_bytes = cand_coverage.read_bytes()
        except Exception as exc:  # producer/candidate failure: runtime dir untouched
            return _persist(
                {
                    "status": "aborted",
                    "aborted_stage": "refresh",
                    "aborted_reason": str(exc),
                    "restored_from_backup": False,
                    "decision_supported": False,
                    "commit_required_for_repo_baseline": False,
                    "dirty_paths": [],
                }
            )

    # 2. Atomically promote the pair + marker, backing up the prior runtime for restore-on-fail.
    prior = {
        p: (p.read_bytes() if p.exists() else None)
        for p in (runtime_pvo, runtime_coverage, marker_path)
    }
    pvo_sha = hashlib.sha256(pvo_bytes).hexdigest()
    coverage_sha = hashlib.sha256(coverage_bytes).hexdigest()
    marker = {
        "status": "ok",
        "pvo_sha256": pvo_sha,
        "coverage_sha256": coverage_sha,
        "source_as_of": now_fn().isoformat(),
        "decision_supported": False,
    }
    try:
        _atomic_write_bytes(runtime_pvo, pvo_bytes)
        _atomic_write_bytes(runtime_coverage, coverage_bytes)
        _atomic_write_text(marker_path, json.dumps(marker, sort_keys=True))
    except Exception as exc:  # restore the prior runtime pair + marker byte-identical
        for path, prior_bytes in prior.items():
            _restore_bytes(path, prior_bytes)
        return _persist(
            {
                "status": "aborted",
                "aborted_stage": "publish",
                "aborted_reason": str(exc),
                "restored_from_backup": True,
                "decision_supported": False,
                "commit_required_for_repo_baseline": False,
                "dirty_paths": [],
            }
        )

    report: dict[str, Any] = {
        "status": "ok",
        "decision_supported": False,
        "runtime": {
            "pvo_path": str(runtime_pvo),
            "coverage_path": str(runtime_coverage),
            "ready_marker_path": str(marker_path),
            "pvo_sha256": pvo_sha,
            "coverage_sha256": coverage_sha,
        },
        "dirty_paths": [],
        "commit_required_for_repo_baseline": False,
    }

    # 3. Optional capture stage over the published RUNTIME pair. A capture failure does NOT
    #    restore the runtime (the refresh already succeeded) — it records a capture-stage abort.
    if capture_fn is not None:
        try:
            report["capture_report"] = capture_fn(
                db_path=capture_db_path,
                report_path=capture_report_path,
                pvo_artifact_path=runtime_pvo,
                coverage_artifact_path=runtime_coverage,
                read_artifact=read_artifact,
                now_fn=now_fn,
                git_sha_fn=lambda: _git_head_sha(),
            )
        except Exception as exc:
            report.update(
                {
                    "status": "aborted",
                    "aborted_stage": "capture",
                    "aborted_reason": str(exc),
                    "restored_from_backup": False,
                }
            )

    return _persist(report)


def run_pvo_refresh(
    *,
    pvo_artifact_path: Path,
    coverage_artifact_path: Path,
    report_path: Optional[Path],
    refresh_fn: Callable[..., None],
    runtime_dir: Optional[Path | str] = None,
    capture_fn: Optional[Callable[..., dict]] = None,
    capture_db_path: Optional[Path] = None,
    capture_report_path: Optional[Path] = None,
    read_artifact: Optional[Callable[[Any], bytes]] = None,
    feature_source: Optional[Any] = None,
) -> dict[str, Any]:
    """Refresh the two PVO artifacts, then optionally capture.

    ``runtime_dir`` (F-seed-split T2a): when given, publish into the gitignored runtime dir
    (seed-split mode — the tracked seed path is never written); when None, the legacy in-place
    Option-C refresh runs (back-compat). ``feature_source`` may pin a ``ResolvedFeatureSource``
    for hermetic tests; when None the ambient resolver runs so a production refresh hashes the
    published runtime."""
    if read_artifact is None:
        read_artifact = lambda path: Path(path).read_bytes()  # noqa: E731
    if runtime_dir is not None:
        return _publish_runtime(
            runtime_dir=Path(runtime_dir),
            refresh_fn=refresh_fn,
            report_path=report_path,
            capture_fn=capture_fn,
            capture_db_path=capture_db_path,
            capture_report_path=capture_report_path,
            read_artifact=read_artifact,
            now_fn=lambda: datetime.now(timezone.utc),
        )
    pvo = Path(pvo_artifact_path)
    coverage = Path(coverage_artifact_path)
    pre_pvo_bytes = pvo.read_bytes()
    pre_coverage_bytes = coverage.read_bytes()

    def _persist(report: dict) -> dict:
        if report_path is not None:
            Path(report_path).parent.mkdir(parents=True, exist_ok=True)
            Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True))
        return report

    def _restore_and_abort(reason: str) -> dict:
        pvo.write_bytes(pre_pvo_bytes)
        coverage.write_bytes(pre_coverage_bytes)
        return _persist(
            {
                "status": "aborted",
                "aborted_stage": "refresh",
                "aborted_reason": reason,
                "restored_from_backup": True,
                "decision_supported": False,
                "commit_required_for_repo_baseline": False,
            }
        )

    # ── pre-refresh lineage-grade hashes (unresolvable required provenance → abort) ──
    try:
        pre = _artifact_hashes(
            pre_pvo_bytes, read_artifact=read_artifact, feature_source=feature_source
        )
    except FileNotFoundError as exc:
        return _restore_and_abort(f"required_provenance_missing:{exc}")

    # ── refresh in place; on ANY failure restore both artifacts byte-identical ──
    try:
        refresh_fn(pvo_artifact_path=pvo, coverage_artifact_path=coverage)
    except Exception as exc:  # restore-on-any-failure safety
        return _restore_and_abort(str(exc))

    post_pvo_bytes = pvo.read_bytes()
    post_coverage_bytes = coverage.read_bytes()
    try:
        post = _artifact_hashes(
            post_pvo_bytes, read_artifact=read_artifact, feature_source=feature_source
        )
    except FileNotFoundError as exc:
        return _restore_and_abort(f"required_provenance_missing:{exc}")

    dirty_paths: list[str] = []
    if post_pvo_bytes != pre_pvo_bytes:
        dirty_paths.append(str(pvo))
    if post_coverage_bytes != pre_coverage_bytes:
        dirty_paths.append(str(coverage))

    # Refresh SUCCEEDED — this metadata is preserved in BOTH the ok report and a
    # capture-stage abort report.
    refresh_meta = {
        "pre": pre,
        "post": post,
        "semantic_changed": pre["semantic_output_hash"] != post["semantic_output_hash"],
        "provenance_changed": pre["provenance_hash"] != post["provenance_hash"],
        "dirty_paths": sorted(dirty_paths),
    }

    # ── orchestrated capture (independent of refresh; capture CLI stays callable) ──
    # The refresh already succeeded, so a capture-stage failure does NOT restore the PVO
    # (Option C local freshness holds); it writes a capture-stage abort report instead.
    capture_report: Optional[dict] = None
    if capture_fn is not None:
        try:
            capture_report = capture_fn(
                db_path=capture_db_path,
                report_path=capture_report_path,
                pvo_artifact_path=pvo,
                coverage_artifact_path=coverage,
                read_artifact=read_artifact,
                now_fn=lambda: datetime.now(timezone.utc),
                git_sha_fn=lambda: _git_head_sha(),
            )
        except Exception as exc:  # capture-stage failure: report, do NOT restore the PVO
            return _persist(
                {
                    "status": "aborted",
                    "aborted_stage": "capture",
                    "aborted_reason": str(exc),
                    "restored_from_backup": False,
                    "decision_supported": False,
                    "commit_required_for_repo_baseline": True,
                    **refresh_meta,
                    "capture_report": None,
                    "forbidden_commands_attempted": [],
                }
            )

    return _persist(
        {
            "status": "ok",
            "decision_supported": False,
            "commit_required_for_repo_baseline": True,
            **refresh_meta,
            "forbidden_commands_attempted": [],
            "capture_report": capture_report,
            "aborted_reason": None,
        }
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the PVO artifacts in place (Phase-17.2 only; never commits)."
    )
    parser.add_argument("--pvo-artifact-path", default=DEFAULT_PVO_PATH)
    parser.add_argument("--coverage-artifact-path", default=DEFAULT_COVERAGE_PATH)
    parser.add_argument(
        "--runtime-dir",
        default=DEFAULT_RUNTIME_DIR,
        help="gitignored runtime dir to publish into (seed-split mode, the default — the "
        "tracked seed paths are never written). Pass empty to fall back to legacy in-place.",
    )
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--capture-db-path", default=None)
    parser.add_argument("--capture-report-path", default=None)
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Print resolved config and exit; performs no refresh, capture, or write.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.preflight:
        print(
            json.dumps(
                {
                    "preflight": True,
                    "pvo_artifact_path": args.pvo_artifact_path,
                    "coverage_artifact_path": args.coverage_artifact_path,
                    "runtime_dir": args.runtime_dir or None,
                    "report_path": args.report_path,
                    "capture_db_path": args.capture_db_path,
                    "phase": PHASE,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    capture_fn = capture_model_pvo_snapshot if args.capture_db_path else None
    # Seed-split mode is the DEFAULT: a scheduled run publishes into the gitignored runtime
    # dir and never mutates the tracked seed pair. An empty --runtime-dir opts into the
    # legacy in-place refresh (back-compat for direct/manual callers only).
    report = run_pvo_refresh(
        pvo_artifact_path=Path(args.pvo_artifact_path),
        coverage_artifact_path=Path(args.coverage_artifact_path),
        runtime_dir=Path(args.runtime_dir) if args.runtime_dir else None,
        report_path=Path(args.report_path) if args.report_path else None,
        refresh_fn=_phase17_2_refresh,
        capture_fn=capture_fn,
        capture_db_path=Path(args.capture_db_path) if args.capture_db_path else None,
        capture_report_path=(
            Path(args.capture_report_path) if args.capture_report_path else None
        ),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
