#!/usr/bin/env python3.14
"""Step-5b.1 — load the verified DynastyProcess archive into the backfill adapter.

For each target fold date, selects the nearest ON-OR-BEFORE commit of
files/values.csv within ±7 days (an after-target commit is REFUSED — no
look-ahead without explicit David approval), maps that commit's PLAYER rows
(pos != "PICK", and mapped via the era crosswalk) to backfill_market_archive
adapter rows, and writes them through the W1.4 adapter (which re-applies the
point-in-time gates + immutable append). PICK pseudo-positions and unmapped rows
are excluded.

Source is tagged ``dp_archive`` (FantasyPros-ECR expert consensus, NOT the
FantasyCalc trade-market). NO imputation/smoothing/composite; writes only to the
local snapshot store. David-approved (fresh §8.4-extension sign-off).
"""
from __future__ import annotations

import csv
import io
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backfill_market_archive import (  # noqa: E402
    DEFAULT_DB_PATH,
    backfill_market_archive,
)

_PIT_WINDOW_DAYS = 7
_VALUES_PATH = "files/values.csv"
_IDS_PATH = "files/db_playerids.csv"


def _git_show(repo: Path, sha: str, path: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), "show", f"{sha}:{path}"],
            check=True, capture_output=True, text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None


def _commits_for(repo: Path, path: str) -> list[tuple[str, date]]:
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--format=%H %cI", "--", path],
        check=True, capture_output=True, text=True,
    ).stdout
    commits: list[tuple[str, date]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, iso = line.split(" ", 1)
        commits.append((sha, date.fromisoformat(iso[:10])))
    return commits


def load_dynastyprocess_archive(repo_path, target_dates, db_path=DEFAULT_DB_PATH) -> dict:
    """Map verified DynastyProcess commits → backfill adapter → store. No imputation."""
    repo = Path(repo_path)
    commits = _commits_for(repo, _VALUES_PATH)
    result: dict = {"targets": {}}

    for td_str in target_dates:
        td = date.fromisoformat(td_str)
        t: dict = {
            "status": "unavailable",
            "findings": [],
            "selected_commit": None,
            "adapter_rows_emitted": 0,
            "pick_rows_excluded": 0,
            "unmapped_rows_skipped": 0,
            "malformed_rows_skipped": 0,
            "rows_written": 0,
        }

        in_window = [
            (sha, d, (d - td).days)
            for sha, d in commits
            if abs((d - td).days) <= _PIT_WINDOW_DAYS
        ]
        on_or_before = [c for c in in_window if c[2] <= 0]
        if not on_or_before:
            # An after-target commit in window is REFUSED (look-ahead); nothing
            # in window at all → no clean source. Either way: no store write.
            t["findings"].append(
                "after_target_commit_disallowed"
                if in_window
                else "no_on_or_before_commit_in_window"
            )
            result["targets"][td_str] = t
            continue

        sha, cdate, delta = max(on_or_before, key=lambda c: c[1])
        t["selected_commit"] = {
            "sha": sha, "commit_date": cdate.isoformat(), "delta_days": delta,
        }

        values_text = _git_show(repo, sha, _VALUES_PATH)
        ids_text = _git_show(repo, sha, _IDS_PATH)
        if values_text is None or ids_text is None:
            t["findings"].append("values_or_ids_file_not_found")
            result["targets"][td_str] = t
            continue

        # Fail closed for the whole target if the required value column is absent
        # (schema drift) — never crash on KeyError, never partial-write.
        values_reader = csv.DictReader(io.StringIO(values_text))
        if "value_2qb" not in (values_reader.fieldnames or []):
            t["findings"].append("value_2qb_missing")
            result["targets"][td_str] = t
            continue

        crosswalk: dict[str, str] = {}
        for r in csv.DictReader(io.StringIO(ids_text)):
            fp, sl = r.get("fantasypros_id"), r.get("sleeper_id")
            if fp and sl:
                crosswalk[fp] = sl

        adapter_rows: list[dict] = []
        for r in values_reader:
            pos = r.get("pos")
            if pos == "PICK":
                t["pick_rows_excluded"] += 1
                continue
            sleeper_id = crosswalk.get(r.get("fp_id"))
            if not sleeper_id:
                t["unmapped_rows_skipped"] += 1
                continue
            try:
                value = int(r.get("value_2qb"))
            except (ValueError, TypeError):
                # Malformed external archive content → skip (fail closed), never crash.
                t["malformed_rows_skipped"] += 1
                continue
            adapter_rows.append({
                "sleeper_id": sleeper_id,
                "value": value,
                "position": pos,
                "archive_publish_date": cdate.isoformat(),
                "source": "dp_archive",
                "updated_at": r.get("scrape_date"),
                "overall_rank": None,
                "position_rank": None,
            })
        t["adapter_rows_emitted"] = len(adapter_rows)

        backfill = backfill_market_archive(
            adapter_rows, db_path=db_path, snapshot_dates=[td_str]
        )
        t["rows_written"] = backfill["rows_written"]
        t["rows_skipped"] = backfill.get("rows_skipped", 0)
        t["status"] = "loaded"
        result["targets"][td_str] = t

    return result


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Load verified DynastyProcess commits into the backfill store."
    )
    parser.add_argument("--repo-path", required=True, type=Path)
    parser.add_argument("--target-dates", nargs="+", required=True)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    out = load_dynastyprocess_archive(
        repo_path=args.repo_path,
        target_dates=args.target_dates,
        db_path=args.db_path,
    )
    print(json.dumps(out, indent=2))
