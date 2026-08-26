"""Layer 1 daily source control plane — the runnable entrypoint.

One command that answers, for every source: how do we connect, can we automate it, and
is it current? It runs the routes this controller owns, records the rest honestly, and
writes one atomic aggregate report.

    # read-only: verify routes and credentials exist, fetch nothing, write nothing
    .venv/bin/python3.14 scripts/run_layer1_daily_control.py --preflight

    # plan without launching anything
    .venv/bin/python3.14 scripts/run_layer1_daily_control.py --dry-run

    # the daily run
    .venv/bin/python3.14 scripts/run_layer1_daily_control.py

    # narrow to one owned route
    .venv/bin/python3.14 scripts/run_layer1_daily_control.py --only sleeper_transactions

DELIBERATELY ABSENT: any flag that executes a PAID source. CFBD bills per run, so a
cost decision does not belong behind a command-line switch on a job that may one day be
scheduled. It stays a separate, explicit act.

This script installs nothing and schedules nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.sources.daily_control import (  # noqa: E402
    DEFAULT_REPORT_ROOT,
    build_manifest,
    execute,
    preflight,
)


def _print_preflight(report) -> int:
    print("\nLayer 1 preflight — read-only. Nothing fetched, nothing written.\n")
    bad = [s for s in report.entries if not s.ok]
    print(f"  routes checked ......... {len(report.entries)}")
    print(f"  routes incomplete ...... {len(bad)}")
    for s in bad:
        print(f"      {s.source:26} {', '.join(s.missing)}")
    if report.gated:
        print("\n  paid gates (not executed):")
        for g in report.gated:
            print(f"      {g.source:26} {g.reason}")
    if report.credentials:
        print("\n  credentials:")
        for c in report.credentials:
            state = "present" if c.present else "ABSENT"
            print(f"      {c.source:26} {c.variable} {state}")
    blocking = [s for s in report.entries if s.blocking]
    if blocking:
        print("  BLOCKING — these automatic routes cannot run:")
        for s in blocking:
            print(f"      {s.source:26} {', '.join(s.missing)}")
    print()
    # R4: an incomplete MANUAL route means a human has not downloaded something yet —
    # informational. A broken AUTOMATIC route is a pipeline that cannot run, and a
    # preflight that returns success for it is worse than no preflight.
    return 1 if blocking else 0


def _print_result(result) -> None:
    print("\nLayer 1 daily control — result\n")
    width = max(len(s) for s in result.by_source) if result.by_source else 10
    for source, r in sorted(result.by_source.items()):
        age = "" if r.age_days is None else f"  age={r.age_days}d"
        miss = f"  missing={','.join(r.missing)}" if r.missing else ""
        flag = "FAILED " if r.failed else "       "
        print(f"  {flag}{source:{width}}  {r.state:28} {r.freshness:8}{age}{miss}")
    print(f"\n  report: {result.report_path}")
    print(f"  exit:   {result.exit_code}\n")


def main(argv: list[str] | None = None) -> int:
    # ── RETIRED — David's ruling 2026-08-26 ("retire daily control") ────────────
    # The scheduled-control-plane role this runner held is superseded by the
    # capture-gap alert (DG-044), the capture-health surface (SR-10a), and
    # event-stream attestation (DG-049). It never had a schedule, its last real
    # report was 2026-08-08, and a control surface that has stopped being
    # consulted is worse than none. Every mode refuses — a stray invocation must
    # not write a marker that resurrects the illusion of a consulted control
    # plane (one such stray run on 2026-08-26 reached a production store through
    # worktree symlinks; see dg-build DG-048). The daily_control MODULE lives on
    # as library code. Restoring this runner is a David-ruling-sized decision.
    print(
        "RETIRED (David 2026-08-26, DG-048): the Layer 1 Daily Control runner no "
        "longer runs in any mode.\nIts role is served by the capture-gap alert "
        "(DG-044), the capture-health surface, and\nevent-stream attestation "
        "(DG-049). The last real report (2026-08-08) is preserved in\n"
        "dg-build/preserved/2026-08-26-daily-control-last-real-report.json.",
        flush=True,
    )
    return 2

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight", action="store_true",
        help="READ-ONLY: verify routes and credentials exist; fetch and write nothing",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="plan the run and write the report without launching any source",
    )
    parser.add_argument(
        "--only", nargs="+", default=None,
        help="narrow to named controller-owned sources (never widens the default set)",
    )
    parser.add_argument(
        "--report-root", type=Path, default=DEFAULT_REPORT_ROOT,
        help=f"where the aggregate report is written (default: {DEFAULT_REPORT_ROOT})",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the report payload to stdout",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest()

    if args.preflight:
        return _print_preflight(preflight(manifest=manifest))

    result = execute(
        manifest=manifest,
        report_root=args.report_root,
        only=args.only,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(
            {k: vars(v) for k, v in result.by_source.items()},
            indent=2, sort_keys=True, default=str,
        ))
    else:
        _print_result(result)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
