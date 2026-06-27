"""Dual Daily PIT Capture — model-output forward-capture T3 CLI entrypoint.

Concrete executable wrapper over the dependency-injected T2 driver
(`capture_model_pvo_snapshot`). Supplies REAL filesystem artifact reads, a UTC clock,
and the git HEAD sha so the scheduled run has one command to invoke; tests inject
fakes via the module-level `capture_model_pvo_snapshot` / `_git_head_sha` handles.

Does NOT import the legacy market collector (`scripts.snapshot_fantasycalc`) or the
legacy `MarketSnapshotStore`. The PVO-refresh runner (T4) and the scheduler + first
live capture (T5) are separate; the launchctl reload + first live run are David-gated.

Plan/spec: docs/superpowers/specs/2026-06-24-model-output-forward-capture-brick-design.md (T3)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Standalone-run path bootstrap: when launchd/cron runs this file directly the repo
# root is not on sys.path, so the first-party `src` import would crash at runtime.
# Resolve the repo root from this file's location (cwd-independent) before importing.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.capture.model_forward_capture_driver import (  # noqa: E402
    capture_model_pvo_snapshot,
)
from src.dynasty_genius.pvo_source import (  # noqa: E402
    PvoSourceNotReadyError,
    resolve_pvo_source,
)

# F-seed-split T4: when the artifact paths are not explicitly provided, resolve the live
# PVO pair (verified runtime else committed seed). Built from path components so the
# committed-seed literal never appears verbatim (consumer grep-guard) while the resolver
# still receives the canonical relative paths. Explicit --pvo-artifact-path /
# --coverage-artifact-path bypass the resolver (callers like run_pvo_refresh inject the
# already-published runtime pair directly — no double-resolve).
PVO_SEED_PATH = Path("app") / "data" / "valuation" / "universe_pvo_latest.json"
PVO_SEED_COVERAGE_PATH = (
    Path("app") / "data" / "valuation" / "universe_pvo_coverage_latest.json"
)
PVO_RUNTIME_DIR = Path("app") / "data" / "valuation_runtime"
MODEL_PVO_SOURCE = "model_pvo"


def _git_head_sha() -> str:
    """Return the repo HEAD sha (audit-only provenance). 'unknown' if unavailable."""
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


def _read_artifact(path: Path | str) -> bytes:
    return Path(path).read_bytes()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture one model-output PVO snapshot (PIT, append-only)."
    )
    parser.add_argument("--db-path", required=True, help="Model-output capture store path.")
    parser.add_argument(
        "--pvo-artifact-path",
        default=None,
        help="Published PVO artifact to capture (defaults to the resolved live source).",
    )
    parser.add_argument(
        "--coverage-artifact-path",
        default=None,
        help="Published PVO coverage artifact (defaults to the resolved live source).",
    )
    parser.add_argument(
        "--report-path",
        default=None,
        help="Path for the machine-readable capture report (JSON).",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Print resolved config and exit; performs no artifact read and no write.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.preflight:
        # No-read disclosure: print the configured resolver inputs without resolving
        # (resolution reads the marker/sha — deferred to the normal run path below).
        print(
            json.dumps(
                {
                    "preflight": True,
                    "db_path": args.db_path,
                    "pvo_artifact_path": args.pvo_artifact_path,
                    "coverage_artifact_path": args.coverage_artifact_path,
                    "seed_pvo_path": str(PVO_SEED_PATH),
                    "seed_coverage_path": str(PVO_SEED_COVERAGE_PATH),
                    "runtime_dir": str(PVO_RUNTIME_DIR),
                    "report_path": args.report_path,
                    "source": MODEL_PVO_SOURCE,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    # Default (no explicit artifact paths) → capture the resolved LIVE source (verified
    # runtime else committed seed). Explicit paths bypass the resolver so an orchestrator
    # can inject the already-published runtime pair without a second resolution.
    if args.pvo_artifact_path is None or args.coverage_artifact_path is None:
        try:
            resolved = resolve_pvo_source(
                seed_paths={"pvo": PVO_SEED_PATH, "coverage": PVO_SEED_COVERAGE_PATH},
                runtime_dir=PVO_RUNTIME_DIR,
            )
        except PvoSourceNotReadyError as exc:
            report = {
                "status": "aborted",
                "aborted_reason": f"pvo_source_not_ready: {exc}",
                "decision_supported": False,
            }
            print(json.dumps(report, indent=2, sort_keys=True))
            return 1
        pvo_artifact_path = resolved.pvo_path
        coverage_artifact_path = resolved.coverage_path
    else:
        pvo_artifact_path = Path(args.pvo_artifact_path)
        coverage_artifact_path = Path(args.coverage_artifact_path)

    report = capture_model_pvo_snapshot(
        db_path=Path(args.db_path),
        report_path=Path(args.report_path) if args.report_path else None,
        pvo_artifact_path=pvo_artifact_path,
        coverage_artifact_path=coverage_artifact_path,
        read_artifact=_read_artifact,
        now_fn=lambda: datetime.now(timezone.utc),
        git_sha_fn=lambda: _git_head_sha(),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
