#!/usr/bin/env python3.14
"""DG-155 — capture one annual consensus snapshot from the DynastyProcess archive.

    .venv/bin/python3.14 scripts/capture_dynastyprocess_snapshot.py --year 2025

Extracts ``files/values.csv`` from ``github.com/dynastyprocess/data`` at the commit nearest
that year's 8 September, preferring on-or-before, and writes it beside the four snapshots the
market-versus-model comparison already rests on, with its provenance.

**Lawfulness, checked before this was written (Fred, 2026-09-04):** the repository is public
and GPL-3.0 — read out of the repository itself, not taken from the docstring in
``scripts/verify_dynastyprocess_source.py`` that asserts it. Access is a read-only git clone,
never scraping, and GPL-3.0 grants copying. The source is absent from the prohibited registry
(which names KTC, FootballGuys and Dynasty Nerds) and the verification script records David's
own sign-off for it.

**There is no capture deadline, and this is why the script takes a year.** The four stored
files were extracted from git history, not downloaded on their dates; history reaches back to
2019 across 361 commits touching the file, and git history is immutable. Verified end to end:
the nearest commit on-or-before 2024-09-08 (``1f17c551``, committed 2024-09-06) reproduces the
stored ``values_2024-09-08.csv`` byte for byte. So any missing year can be recovered whenever
someone asks — including 2025, which the filing called a permanent gap and which sits at a
2025-09-05 commit.

Two risks remain and neither has a clock: the upstream repository disappearing, and someone
rewriting its history. Measured, so nobody reaches for the wrong defence: a blobless history
clone is 1.4 MB and takes seconds, but it does NOT survive the repository disappearing,
because blobs are fetched on demand; a full mirror did not finish a ten-minute clone. The
defence that actually works is the one this script performs — keep the extracted CSV in our
own archive, where it no longer depends on the upstream existing.

Writes ONLY the snapshot and its provenance sidecar. Never clobbers an existing snapshot: if
one is already there and differs, that is a LOUD failure, because these files are the evidence
other results were computed on.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.sources.dynastyprocess_snapshot import (  # noqa: E402
    SOURCE_PATH,
    SOURCE_URL,
    NoCommitInWindow,
    provenance_record,
    select_snapshot_commit,
    snapshot_filename,
    snapshot_target,
    validate_snapshot_columns,
)

DEFAULT_OUT_DIR = ROOT / "app" / "data" / "backtest" / "qb_validation" / "raw" / "dp_values"


def _git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, capture_output=True, text=True
    ).stdout


def _ensure_clone(repo_path: Optional[str], work_dir: Path) -> str:
    """A local clone to read. Reuses one when given, else makes a run-scoped blobless clone.

    ``--filter=blob:none`` fetches the commit graph and pulls file contents only for the one
    commit actually read, which keeps this cheap enough to run on demand.
    """
    if repo_path:
        return str(Path(repo_path))
    work_dir.mkdir(parents=True, exist_ok=True)
    target = work_dir / "dynastyprocess-data"
    if (target / ".git").exists():
        _git(str(target), "fetch", "--quiet", "origin")
        return str(target)
    subprocess.run(
        ["git", "clone", "--filter=blob:none", "--no-checkout", "--quiet", SOURCE_URL + ".git", str(target)],
        check=True, capture_output=True, text=True,
    )
    return str(target)


def _commits_touching_values(repo: str) -> list[dict[str, Any]]:
    out = _git(repo, "log", "--format=%H %cI", "--", SOURCE_PATH)
    commits: list[dict[str, Any]] = []
    for line in out.splitlines():
        sha, _, stamp = line.partition(" ")
        if not sha or not stamp:
            continue
        commits.append(
            {"sha": sha, "committed": datetime.fromisoformat(stamp).date()}
        )
    return commits


def _file_at_commit(repo: str, sha: str, path: str) -> str:
    return _git(repo, "show", f"{sha}:{path}")


def capture(
    *,
    year: int,
    out_dir: Path | str = DEFAULT_OUT_DIR,
    work_dir: Path | str | None = None,
    repo_path: Optional[str] = None,
) -> dict[str, Any]:
    """Capture one year's snapshot. Idempotent; refuses rather than overwriting."""
    out_dir = Path(out_dir)
    work = Path(work_dir) if work_dir is not None else Path(tempfile.gettempdir()) / "dg155"
    target = snapshot_target(year)

    def _failed(reason: str) -> dict[str, Any]:
        return {"status": "failed", "failure_reason": reason, "year": year,
                "target_date": target.isoformat(), "decision_supported": False}

    repo = _ensure_clone(repo_path, work)
    try:
        chosen = select_snapshot_commit(_commits_touching_values(repo), target=target)
    except NoCommitInWindow:
        return _failed("no_commit_in_window")

    content = _file_at_commit(repo, chosen["sha"], SOURCE_PATH)
    reader = csv.reader(io.StringIO(content))
    try:
        header = next(reader)
    except StopIteration:
        return _failed("empty_snapshot")
    try:
        validate_snapshot_columns(header)
    except ValueError as exc:
        return _failed(str(exc))

    scrape_date = None
    try:
        first = next(reader)
        if "scrape_date" in header:
            scrape_date = first[header.index("scrape_date")]
    except StopIteration:
        return _failed("snapshot_has_no_rows")

    digest = hashlib.sha256(content.encode()).hexdigest()
    snapshot_path = out_dir / snapshot_filename(target)
    if snapshot_path.exists():
        existing = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        if existing == digest:
            return {"status": "noop", "noop_reason": "already_captured_identical",
                    "year": year, "target_date": target.isoformat(),
                    "path": str(snapshot_path), "sha256": digest,
                    "decision_supported": False}
        # These files are the evidence other results were computed on. A differing upstream
        # revision is a finding, not something to write over.
        return _failed("existing_snapshot_differs")

    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(content)
    provenance = provenance_record(
        target=target,
        commit_sha=chosen["sha"],
        commit_date=chosen["committed"],
        sha256=digest,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        scrape_date=scrape_date,
    )
    (out_dir / f"{snapshot_path.stem}.provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )
    return {"status": "ok", "year": year, "target_date": target.isoformat(),
            "path": str(snapshot_path), "provenance": provenance,
            "decision_supported": False}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--repo-path", default=None, help="reuse an existing local clone")
    args = parser.parse_args(argv)

    result = capture(year=args.year, out_dir=args.out_dir,
                     work_dir=args.work_dir, repo_path=args.repo_path)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result["status"] in ("ok", "noop") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
