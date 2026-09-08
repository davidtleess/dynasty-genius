"""Archive one workspace snapshot from the command line (DG-190).

Reads the verified sources, hands them to the archive store, and prints the receipt as JSON.

Two deliberate refusals to be convenient:

* **Every path is explicit.** There is no environment default and no built-in archive location, because a default
  is how a local experiment quietly writes a shared store.
* **The capture code identity is the commit only when the tree is clean.** A dirty tree means the code that ran is
  not the code that commit contains, so the receipt says ``unknown``. Admitting ignorance is worth more later than a
  commit hash that points at something else.

Saving the same sources again converges on the existing archive and reports ``created: false`` with its original
saved time. Note that the id covers the whole saved reading: the same underlying forecast can be archived more than
once if the surrounding presentation changed, which is a second RECORDING, never a second prediction. The receipt's
six-field ``source`` block is what identifies the forecast itself.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.capture.workspace_snapshot_store import (  # noqa: E402
    WorkspaceSnapshotError,
    save_snapshot,
)

UNKNOWN_CODE = "unknown"
EXIT_OK = 0
EXIT_REFUSED = 1


def capture_code_identity(repo: Path) -> str:
    """The commit that contains the running code, or ``unknown``.

    Only a clean tree may claim its HEAD. Anything else — uncommitted edits, a detached or broken repository, git
    missing entirely — is ``unknown``, never a guess and never a model version.
    """
    try:
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, check=False,
        )
        if status.returncode != 0 or status.stdout.strip():
            return UNKNOWN_CODE
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return UNKNOWN_CODE
    revision = head.stdout.strip()
    if head.returncode != 0 or len(revision) != 40 or set(revision) - set("0123456789abcdef"):
        return UNKNOWN_CODE
    return revision


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capture_workspace_snapshot",
        description="Archive one verified workspace snapshot and print its receipt.",
    )
    parser.add_argument("--manifest", type=Path, required=True, help="the market-ranks source manifest")
    parser.add_argument("--catalog", type=Path, required=True, help="the available-player catalog")
    parser.add_argument("--catalog-companion", type=Path, required=True, help="the catalog's companion report")
    parser.add_argument(
        "--archive-root", type=Path, required=True,
        help="the private directory to archive into; there is deliberately no default",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    load: Callable[..., Any] | None = None,
    clock: Callable[[], datetime] | None = None,
    code: str | None = None,
    stdout: Any = None,
    stderr: Any = None,
) -> int:
    options = _parser().parse_args(argv)
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr

    if load is None:
        try:
            from src.dynasty_genius.capture.workspace_snapshot_sources import (
                load_workspace_snapshot as load,
            )
        except ImportError as exc:
            print(f"the workspace source loader is unavailable: {exc}", file=err)
            return EXIT_REFUSED

    captured_at = (clock() if clock is not None else datetime.now(timezone.utc)).astimezone(timezone.utc)
    code_sha = code if code is not None else capture_code_identity(REPO_ROOT)

    try:
        bundle = load(options.manifest, options.catalog, options.catalog_companion)
        result = save_snapshot(
            options.archive_root, bundle, captured_at=captured_at, code_sha=code_sha
        )
    except WorkspaceSnapshotError as exc:
        print(f"refusing to archive this snapshot: {exc}", file=err)
        return EXIT_REFUSED
    except (OSError, ValueError) as exc:
        print(f"could not read the workspace sources: {exc}", file=err)
        return EXIT_REFUSED

    print(json.dumps(result, indent=2, sort_keys=True), file=out)
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
