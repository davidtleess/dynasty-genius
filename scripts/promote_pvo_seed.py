"""F-seed-split T5a — David-gated promotion of the verified runtime PVO pair to the seed.

Promotes the current VERIFIED runtime PVO+coverage pair to the committed seed paths
(``app/data/valuation/universe_pvo_latest.json`` + coverage). Read-only by default; the
``--confirm`` flag is the ONLY write authorization. The tool NEVER git-commits — it writes
the seed files and reminds David to review + commit the baseline (the D2 Option-C ruling that
committing a refreshed baseline is David-gated).

Fail-closed: it refuses to promote when nothing valid is published — ``no_runtime_published``
(resolver serves the seed: no runtime) or ``runtime_not_ready`` (present-but-unverified /
corrupt runtime). The seed is a tracked asset, so a confirmed promotion is an ATOMIC PAIR:
if writing either seed file fails, BOTH prior seed files are restored byte-identical (never a
half-written / desynced tracked seed). ``decision_supported`` is always False.

Usage:
    .venv/bin/python3.14 scripts/promote_pvo_seed.py            # dry-run (show drift, no write)
    .venv/bin/python3.14 scripts/promote_pvo_seed.py --confirm  # promote runtime -> seed
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess  # noqa: F401 — guarded seam: the tool must NEVER invoke git (tests patch subprocess.run to forbid)
import sys
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.pvo_source import (  # noqa: E402
    PvoSourceNotReadyError,
    resolve_pvo_source,
)

DEFAULT_SEED_PVO_PATH = "app/data/valuation/universe_pvo_latest.json"
DEFAULT_SEED_COVERAGE_PATH = "app/data/valuation/universe_pvo_coverage_latest.json"
DEFAULT_RUNTIME_DIR = "app/data/valuation_runtime"


def _write_temp(path: Path, data: bytes) -> Path:
    """Write ``data`` to a sibling temp file (same dir -> same filesystem for atomic rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".promote.tmp")
    tmp.write_bytes(data)
    return tmp


def _restore(path: Path, prior: Optional[bytes]) -> None:
    """Restore ``path`` to its prior bytes (or remove it if it did not exist before)."""
    if prior is None:
        if path.exists():
            path.unlink()
    else:
        path.write_bytes(prior)


def promote_pvo_seed(
    *,
    seed_pvo_path: Path | str,
    seed_coverage_path: Path | str,
    runtime_dir: Path | str,
    confirm: bool,
    replace_fn: Callable[[Path | str, Path | str], None] = os.replace,
) -> dict[str, Any]:
    """Promote the verified runtime PVO pair to the committed seed (David-gated).

    Resolves the current source; refuses unless a VERIFIED runtime is published. Without
    ``confirm`` it is a read-only dry-run that shows the drift. With ``confirm`` it copies the
    verified runtime bytes onto the seed pair as an atomic pair (restore-both-on-fail) and
    never git-commits.
    """
    seed_pvo_path = Path(seed_pvo_path)
    seed_coverage_path = Path(seed_coverage_path)
    try:
        resolved = resolve_pvo_source(
            seed_paths={"pvo": seed_pvo_path, "coverage": seed_coverage_path},
            runtime_dir=runtime_dir,
        )
    except PvoSourceNotReadyError as exc:
        return {
            "status": "refused",
            "reason": "runtime_not_ready",
            "aborted_reason": str(exc),
            "decision_supported": False,
        }
    if resolved.source_kind == "seed":
        return {
            "status": "refused",
            "reason": "no_runtime_published",
            "decision_supported": False,
        }

    runtime_section = {
        "pvo_path": str(resolved.pvo_path),
        "coverage_path": str(resolved.coverage_path),
        "pvo_sha256": resolved.pvo_sha256,
        "coverage_sha256": resolved.coverage_sha256,
        "source_as_of": resolved.source_as_of,
    }
    seed_staleness = resolved.seed_staleness

    if not confirm:
        return {
            "status": "dry_run",
            "would_promote": True,
            "decision_supported": False,
            "runtime": runtime_section,
            "seed_staleness": seed_staleness,
            "manual_commit_required": True,
        }

    # --confirm: copy the verified runtime bytes onto the committed seed as an ATOMIC PAIR.
    # The verified runtime bytes are read directly (resolve_pvo_source already verified the
    # hashes; no second verification). Back up the prior seed pair first; on ANY write failure
    # restore BOTH seed files byte-identical so the tracked seed is never left desynced.
    prior = {
        seed_pvo_path: seed_pvo_path.read_bytes() if seed_pvo_path.exists() else None,
        seed_coverage_path: (
            seed_coverage_path.read_bytes() if seed_coverage_path.exists() else None
        ),
    }
    pvo_bytes = resolved.pvo_path.read_bytes()
    coverage_bytes = resolved.coverage_path.read_bytes()
    temps: list[Path] = []
    try:
        tmp_pvo = _write_temp(seed_pvo_path, pvo_bytes)
        temps.append(tmp_pvo)
        replace_fn(tmp_pvo, seed_pvo_path)
        tmp_coverage = _write_temp(seed_coverage_path, coverage_bytes)
        temps.append(tmp_coverage)
        replace_fn(tmp_coverage, seed_coverage_path)
    except Exception as exc:
        for path, prior_bytes in prior.items():
            _restore(path, prior_bytes)
        for tmp in temps:
            if Path(tmp).exists():
                Path(tmp).unlink()
        return {
            "status": "aborted",
            "aborted_stage": "promote",
            "aborted_reason": str(exc),
            "restored_from_backup": True,
            "decision_supported": False,
            "runtime": runtime_section,
            "seed_staleness": seed_staleness,
        }

    return {
        "status": "promoted",
        "decision_supported": False,
        "git_commit_performed": False,
        "manual_commit_required": True,
        "runtime": runtime_section,
        "seed_staleness": seed_staleness,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "David-gated promotion of the verified runtime PVO pair to the committed seed. "
            "Read-only unless --confirm; never git-commits."
        )
    )
    parser.add_argument("--seed-pvo-path", default=DEFAULT_SEED_PVO_PATH)
    parser.add_argument("--seed-coverage-path", default=DEFAULT_SEED_COVERAGE_PATH)
    parser.add_argument("--runtime-dir", default=DEFAULT_RUNTIME_DIR)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="The ONLY write authorization. Without it the tool is a read-only dry-run.",
    )
    args = parser.parse_args(argv)

    report = promote_pvo_seed(
        seed_pvo_path=Path(args.seed_pvo_path),
        seed_coverage_path=Path(args.seed_coverage_path),
        runtime_dir=Path(args.runtime_dir),
        confirm=args.confirm,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {"dry_run", "promoted"} else 1


if __name__ == "__main__":
    sys.exit(main())
