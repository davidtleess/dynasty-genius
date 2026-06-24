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
import json
import subprocess
import sys
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
    """Default refresh: run ONLY the Phase-17.2 PVO rebuild producer (no chain, no commit)."""
    cmd = [sys.executable, str(ROOT / "scripts" / "build_universe_pvo_batch.py")]
    assert_allowed_refresh_command(cmd)
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _artifact_hashes(
    pvo_bytes: bytes, *, read_artifact: Callable[[Any], bytes]
) -> dict[str, Optional[str]]:
    """3-hash snapshot of a PVO artifact: literal audit / semantic output / provenance.

    provenance_hash is LINEAGE-GRADE (the same T2 subset: producer + Engine-B manifest/
    per-position/feature hashes + derived cutoff + Engine-A pointers) so a model/feature/
    producer change is detected even when the scored output is unchanged. Raises
    FileNotFoundError if required model provenance is unresolvable (caller aborts+restores).
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
            _canon(resolve_provenance_subset(pvo, read_artifact=read_artifact))
        ),
    }


def run_pvo_refresh(
    *,
    pvo_artifact_path: Path,
    coverage_artifact_path: Path,
    report_path: Optional[Path],
    refresh_fn: Callable[..., None],
    capture_fn: Optional[Callable[..., dict]] = None,
    capture_db_path: Optional[Path] = None,
    capture_report_path: Optional[Path] = None,
    read_artifact: Optional[Callable[[Any], bytes]] = None,
) -> dict[str, Any]:
    """Refresh the two PVO artifacts in place (Option C), then optionally capture."""
    if read_artifact is None:
        read_artifact = lambda path: Path(path).read_bytes()  # noqa: E731
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
                "aborted_reason": reason,
                "restored_from_backup": True,
                "decision_supported": False,
                "commit_required_for_repo_baseline": False,
            }
        )

    # ── pre-refresh lineage-grade hashes (unresolvable required provenance → abort) ──
    try:
        pre = _artifact_hashes(pre_pvo_bytes, read_artifact=read_artifact)
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
        post = _artifact_hashes(post_pvo_bytes, read_artifact=read_artifact)
    except FileNotFoundError as exc:
        return _restore_and_abort(f"required_provenance_missing:{exc}")

    dirty_paths: list[str] = []
    if post_pvo_bytes != pre_pvo_bytes:
        dirty_paths.append(str(pvo))
    if post_coverage_bytes != pre_coverage_bytes:
        dirty_paths.append(str(coverage))

    # ── orchestrated capture (independent of refresh; capture CLI stays callable) ──
    capture_report: Optional[dict] = None
    if capture_fn is not None:
        capture_report = capture_fn(
            db_path=capture_db_path,
            report_path=capture_report_path,
            pvo_artifact_path=pvo,
            coverage_artifact_path=coverage,
            read_artifact=read_artifact,
            now_fn=lambda: datetime.now(timezone.utc),
            git_sha_fn=lambda: _git_head_sha(),
        )

    return _persist(
        {
            "status": "ok",
            "decision_supported": False,
            "commit_required_for_repo_baseline": True,
            "pre": pre,
            "post": post,
            "semantic_changed": pre["semantic_output_hash"] != post["semantic_output_hash"],
            "provenance_changed": pre["provenance_hash"] != post["provenance_hash"],
            "dirty_paths": sorted(dirty_paths),
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
    report = run_pvo_refresh(
        pvo_artifact_path=Path(args.pvo_artifact_path),
        coverage_artifact_path=Path(args.coverage_artifact_path),
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
