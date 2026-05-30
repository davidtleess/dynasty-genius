#!/usr/bin/env python3.14
"""Step-5a — read-only verification of a DynastyProcess git archive as the G3 source.

Probes a LOCAL clone of github.com/dynastyprocess/data (read-only) to de-risk the
eventual point-in-time backfill loader BEFORE any database write. For each target
fold date it selects the nearest commit touching files/values.csv within ±7 days
(PREFERRING on-or-before the target — no look-ahead), verifies the value_2qb schema
and GPL-3.0 license, computes the era-matched fp_id→sleeper_id crosswalk coverage
and per-position matched-pool sizes (vs PRIMARY_NDCG_K evaluability), confirms
survivorship sentinels, and fails closed on schema drift (missing value_2qb) or a
scrape_date later than the commit date (post-hoc revision).

The values are FantasyPros-ECR-derived (source_family = dynastyprocess_ecr_2qb),
NOT the FantasyCalc trade-market — labeled as such so a G3 verdict on this source
reads as "beats expert consensus," not "beats the trade market."

READ-ONLY: performs only `git log`/`git show`; NO snapshot-store writes, NO loader,
NO imputation/smoothing/composite. Approved by David (fresh §8.4-extension sign-off).
"""
from __future__ import annotations

import csv
import io
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.eval.backtest_harness import PRIMARY_NDCG_K  # noqa: E402

_PIT_WINDOW_DAYS = 7
_SOURCE_FAMILY = "dynastyprocess_ecr_2qb"
_METHODOLOGY = "fantasypros_ecr_consensus"
_LICENSE = "GPL-3.0"
_VALUES_PATH = "files/values.csv"
_IDS_PATH = "files/db_playerids.csv"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout


def _git_show(repo: Path, sha: str, path: str) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), "show", f"{sha}:{path}"],
            check=True, capture_output=True, text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None


def _commits_for(repo: Path, path: str) -> list[tuple[str, date]]:
    out = _git(repo, "log", "--format=%H %cI", "--", path)
    commits: list[tuple[str, date]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, iso = line.split(" ", 1)
        commits.append((sha, date.fromisoformat(iso[:10])))
    return commits


def _select_commit(
    commits: list[tuple[str, date]], target: date
) -> tuple[str, date, int] | None:
    """Nearest commit within ±7 days, preferring the latest on-or-before the target
    (no post-target look-ahead). Returns (sha, commit_date, delta_days) or None."""
    in_window = [
        (sha, d, (d - target).days)
        for sha, d in commits
        if abs((d - target).days) <= _PIT_WINDOW_DAYS
    ]
    if not in_window:
        return None
    on_or_before = [c for c in in_window if c[2] <= 0]
    if on_or_before:
        return max(on_or_before, key=lambda c: c[1])  # latest on-or-before
    return min(in_window, key=lambda c: c[2])  # else nearest after target


def verify_source(repo_path, target_dates, survivorship_sentinels) -> dict:
    """Read-only verification report over a local DynastyProcess clone. No writes."""
    repo = Path(repo_path)
    sentinels_map = survivorship_sentinels or {}
    report: dict = {
        "writes_performed": [],
        "source_family": _SOURCE_FAMILY,
        "methodology": _METHODOLOGY,
        "license": _LICENSE,
        "targets": {},
    }
    commits = _commits_for(repo, _VALUES_PATH)

    for td_str in target_dates:
        td = date.fromisoformat(td_str)
        t: dict = {
            "status": "unavailable",
            "findings": [],
            "source_family": _SOURCE_FAMILY,
            "methodology": _METHODOLOGY,
            "license": _LICENSE,
            "selected_commit": None,
            "schema": {"value_2qb_present": False, "values_header": []},
            "crosswalk": None,
            "per_position_matched_pool_n": {},
            "pool_evaluability": {},
            "survivorship_sentinels": [],
            "revision_guard": None,
        }

        sel = _select_commit(commits, td)
        if sel is None:
            t["findings"].append("no_commit_in_window")
            report["targets"][td_str] = t
            continue
        sha, cdate, delta = sel
        t["selected_commit"] = {
            "sha": sha, "commit_date": cdate.isoformat(), "delta_days": delta,
        }
        if delta > 0:
            t["findings"].append("after_target_no_on_or_before_commit")

        values_text = _git_show(repo, sha, _VALUES_PATH)
        if values_text is None:
            t["findings"].append("values_file_not_found")
            report["targets"][td_str] = t
            continue
        reader = csv.DictReader(io.StringIO(values_text))
        rows = list(reader)
        header = list(reader.fieldnames or [])
        t["schema"]["values_header"] = header

        if "value_2qb" not in header:
            t["findings"].append("value_2qb_missing")
            t["status"] = "unavailable"
            t["crosswalk"] = None
            report["targets"][td_str] = t
            continue
        t["schema"]["value_2qb_present"] = True

        # Revision guard: no row's scrape_date may be later than the commit date.
        scrape_dates = [
            date.fromisoformat(r["scrape_date"][:10])
            for r in rows
            if r.get("scrape_date")
        ]
        max_scrape = max(scrape_dates, default=None)
        rg_fail = max_scrape is not None and max_scrape > cdate
        t["revision_guard"] = {
            "status": "fail" if rg_fail else "pass",
            "max_scrape_date": max_scrape.isoformat() if max_scrape else None,
            "commit_date": cdate.isoformat(),
        }
        if rg_fail:
            t["findings"].append("scrape_date_after_commit_date")
            t["status"] = "unavailable"
            report["targets"][td_str] = t
            continue

        # Era-matched crosswalk (db_playerids at the SAME commit). The join is
        # values.fp_id → db_playerids.fantasypros_id → sleeper_id.
        ids_text = _git_show(repo, sha, _IDS_PATH)
        crosswalk: dict[str, str] = {}
        if ids_text:
            for r in csv.DictReader(io.StringIO(ids_text)):
                fp, sl = r.get("fantasypros_id"), r.get("sleeper_id")
                if fp and sl:
                    crosswalk[fp] = sl

        # Coverage is over PLAYER rows only. Draft picks (pos == "PICK") are not
        # player realized-outcome rows for NDCG and must not inflate per-position
        # pools — they are excluded but surfaced as mapped_pick_rows_excluded.
        values_rows = len(rows)
        mapped_player = unmapped_player = mapped_pick = 0
        pools: dict[str, int] = {}
        for r in rows:
            pos = r.get("pos")
            is_mapped = r.get("fp_id") in crosswalk
            if pos == "PICK":
                if is_mapped:
                    mapped_pick += 1
                continue
            if is_mapped:
                mapped_player += 1
                if pos:
                    pools[pos] = pools.get(pos, 0) + 1
            else:
                unmapped_player += 1
        player_rows = mapped_player + unmapped_player
        t["crosswalk"] = {
            "values_rows": values_rows,
            "mapped_rows": mapped_player,
            "mapped_pick_rows_excluded": mapped_pick,
            "unmapped_rows": unmapped_player,
            "coverage_pct": (
                round(100.0 * mapped_player / player_rows, 4) if player_rows else 0.0
            ),
        }
        t["per_position_matched_pool_n"] = pools
        for pos, n in pools.items():
            k = PRIMARY_NDCG_K.get(pos)
            if k is None:
                continue
            t["pool_evaluability"][pos] = {
                "primary_k": k,
                "matched_pool_n": n,
                "status": "evaluable" if n >= k else "defer_pool_below_k",
            }

        # Survivorship sentinels: must appear in this snapshot to prove it is genuine.
        present_fp = {r.get("fp_id") for r in rows}
        t["survivorship_sentinels"] = [
            {"fp_id": s["fp_id"], "name": s["name"], "present": s["fp_id"] in present_fp}
            for s in sentinels_map.get(td_str, [])
        ]

        t["status"] = "available"
        report["targets"][td_str] = t

    return report


def render_report(report: dict) -> str:
    """Render the verification report as a human-readable findings markdown."""
    lines = [
        "# Step-5a — DynastyProcess source-verification findings",
        "",
        f"- source_family: `{report['source_family']}` "
        f"(methodology: {report['methodology']}; license: {report['license']})",
        f"- writes_performed: {report['writes_performed']} (read-only)",
        "",
        "| Target | Status | Commit (Δdays) | value_2qb | crosswalk % | per-position pool | evaluable? |",
        "|---|---|---|---|---|---|---|",
    ]
    for td, t in report["targets"].items():
        sc = t["selected_commit"]
        commit = f"{sc['sha'][:8]} ({sc['delta_days']:+d}d)" if sc else "—"
        cov = t["crosswalk"]["coverage_pct"] if t["crosswalk"] else "—"
        pools = t["per_position_matched_pool_n"]
        ev = {p: e["status"] for p, e in t["pool_evaluability"].items()}
        lines.append(
            f"| {td} | {t['status']} | {commit} | "
            f"{t['schema']['value_2qb_present']} | {cov} | {pools} | {ev} |"
        )
        if t["findings"]:
            lines.append(f"|  | findings: {', '.join(t['findings'])} ||||||")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Read-only verification of a local DynastyProcess clone (Step-5a)."
    )
    parser.add_argument("--repo-path", required=True, type=Path)
    parser.add_argument("--target-dates", nargs="+", required=True)
    parser.add_argument("--sentinels-json", default="{}")
    args = parser.parse_args()
    rep = verify_source(
        repo_path=args.repo_path,
        target_dates=args.target_dates,
        survivorship_sentinels=json.loads(args.sentinels_json),
    )
    print(render_report(rep))
    print(json.dumps(rep, indent=2))
