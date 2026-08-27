"""SR-09: run the six morning producers as ONE dependency-ordered, fail-soft chain.

Replaces six independent wall-clock LaunchAgent slots (09:00-09:45) whose fixed
offsets turned any late start into a permanent, unbackfillable store hole. One
09:00 job runs the producers in order; a failed step is REPORTED, not amplified —
only a step whose declared hard upstream failed is skipped.

The step table below is the whole graph. Argument vectors are the exact vectors
the six plists carried on 2026-08-26 (re-dumped live, verified identical to
spec:814-836); a future change must be a one-line table edit, never control flow.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

_PY = Path(".venv") / "bin" / "python3.14"

_CHAIN_TARGET = (9, 0)
_REPORT_SCHEMA = 1


@dataclass(frozen=True)
class ChainStep:
    name: str
    argv: tuple[str, ...]
    hard_upstreams: tuple[str, ...]
    # The wall-clock slot the retired plist held — kept so the report can state
    # target-vs-actual drift (spec step 5), not to schedule anything.
    target: tuple[int, int]


def build_steps(repo_root: Path) -> tuple[ChainStep, ...]:
    root = repo_root
    py = str(root / _PY)
    scripts = root / "scripts"
    data = root / "app" / "data"
    return (
        ChainStep(
            name="run_fc_forward_capture",
            argv=(
                py,
                str(scripts / "run_fc_forward_capture.py"),
                "--db-path",
                str(data / "fc_forward_capture.db"),
                "--report-path",
                str(data / "capture" / "fc_forward_capture_latest_report.json"),
            ),
            hard_upstreams=(),
            target=(9, 0),
        ),
        ChainStep(
            name="run_feature_refresh",
            argv=(py, str(scripts / "run_feature_refresh.py")),
            hard_upstreams=(),
            target=(9, 15),
        ),
        ChainStep(
            name="run_league_snapshot_capture",
            argv=(
                py,
                str(scripts / "run_league_snapshot_capture.py"),
                "--runtime-root",
                str(data / "league_runtime"),
            ),
            hard_upstreams=(),
            target=(9, 20),
        ),
        ChainStep(
            name="run_pvo_refresh",
            argv=(
                py,
                str(scripts / "run_pvo_refresh.py"),
                "--runtime-dir",
                str(data / "valuation_runtime"),
                "--capture-db-path",
                str(data / "model_forward_capture.db"),
                "--report-path",
                str(data / "model_capture" / "pvo_refresh_latest_report.json"),
                "--capture-report-path",
                str(data / "model_capture" / "model_forward_capture_latest_report.json"),
            ),
            hard_upstreams=(),
            target=(9, 30),
        ),
        ChainStep(
            name="run_market_divergence_refresh",
            argv=(
                py,
                str(scripts / "run_market_divergence_refresh.py"),
                "--latest-path",
                str(data / "valuation" / "universe_market_divergence_latest.json"),
                "--coverage-latest-path",
                str(data / "valuation" / "universe_market_divergence_coverage_latest.json"),
                "--history-db-path",
                str(data / "market_divergence_history.db"),
                "--fc-forward-capture-db-path",
                str(data / "fc_forward_capture.db"),
                "--fc-source",
                "fc_native",
                "--fc-settings-hash",
                "e27351d720e9fcf0",
                "--marker-path",
                str(data / "valuation_runtime" / "market_divergence_refresh_status_latest.json"),
                "--report-path",
                str(data / "valuation_runtime" / "market_divergence_refresh_latest_report.json"),
            ),
            hard_upstreams=("run_fc_forward_capture",),
            target=(9, 40),
        ),
        ChainStep(
            name="run_what_changed_report",
            argv=(py, str(scripts / "run_what_changed_report.py")),
            hard_upstreams=(),
            target=(9, 45),
        ),
    )


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _fmt_target(target: tuple[int, int]) -> str:
    return f"{target[0]:02d}:{target[1]:02d}"


def _write_report(report_path: Path, payload: dict) -> None:
    # Atomic: the alert may read this path; it must never see a half-written file.
    report_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = report_path.with_suffix(report_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, report_path)


def validate_steps(steps: tuple[ChainStep, ...]) -> None:
    """Every hard_upstreams entry must name a step that appears EARLIER in the
    table. A typo'd or forward-referencing edge would otherwise perma-skip its
    dependent every morning while the chain exits 0 — a config error must die
    loudly at launch, not cost a store date quietly (review finding, 2026-08-26)."""
    seen: set[str] = set()
    for step in steps:
        for up in step.hard_upstreams:
            if up not in seen:
                raise ValueError(
                    f"hard upstream '{up}' of step '{step.name}' does not name an "
                    "earlier step in the table"
                )
        seen.add(step.name)


def apply_step_extras(
    steps: tuple[ChainStep, ...], extras: list[tuple[str, str]]
) -> tuple[ChainStep, ...]:
    """Append CLI-supplied per-step arguments (SR-19's rehearsal needs to force
    ``--season-end 2026`` through the chain's feature_refresh step). An extra
    naming an unknown step is refused — a typo must not silently vanish."""
    names = {s.name for s in steps}
    for name, _arg in extras:
        if name not in names:
            raise ValueError(f"--step-extra names unknown step '{name}'")
    by_step: dict[str, list[str]] = {}
    for name, arg in extras:
        by_step.setdefault(name, []).append(arg)
    return tuple(
        ChainStep(
            name=s.name,
            argv=s.argv + tuple(by_step.get(s.name, ())),
            hard_upstreams=s.hard_upstreams,
            target=s.target,
        )
        for s in steps
    )


def execute_chain(
    steps: tuple[ChainStep, ...],
    *,
    report_path: Path,
    now_fn=None,
) -> int:
    """Run every step in order. A failure is reported, never amplified: only a
    step whose declared hard upstream did not finish ``ok`` is skipped."""

    validate_steps(steps)
    now_fn = now_fn or _now_local
    chain_started = now_fn()
    target_dt = chain_started.replace(
        hour=_CHAIN_TARGET[0], minute=_CHAIN_TARGET[1], second=0, microsecond=0
    )
    drift_minutes = round((chain_started - target_dt).total_seconds() / 60)
    if drift_minutes < -120:
        # A past-midnight catch-up (e.g. 00:10) is chasing YESTERDAY's 09:00
        # target — hours late, not hours early. Nothing legitimately starts
        # hours before its slot; small negative jitter is kept as-is.
        target_dt -= timedelta(days=1)
        drift_minutes = round((chain_started - target_dt).total_seconds() / 60)

    statuses: dict[str, str] = {}
    step_rows: list[dict] = []
    for step in steps:
        bad_upstreams = [
            up for up in step.hard_upstreams if statuses.get(up) != "ok"
        ]
        started_at = now_fn()
        print(
            f"[daily-chain {started_at.isoformat()}] {step.name}"
            + (f" SKIPPED (hard upstream failed: {', '.join(bad_upstreams)})" if bad_upstreams else " starting"),
            flush=True,
        )
        if bad_upstreams:
            statuses[step.name] = "skipped_upstream_failed"
            step_rows.append(
                {
                    "name": step.name,
                    "exit_code": None,
                    "status": "skipped_upstream_failed",
                    "started_at": started_at.isoformat(),
                    "duration_s": 0.0,
                    "target": _fmt_target(step.target),
                }
            )
            continue
        t0 = time.monotonic()
        try:
            returncode: int | None = subprocess.run(step.argv).returncode
        except OSError as exc:
            # A step that cannot even spawn is a failure of that step, not of
            # the chain: report it and carry on, same as a non-zero exit.
            returncode = None
            print(
                f"[daily-chain {now_fn().isoformat()}] {step.name} spawn failed: {exc}",
                flush=True,
            )
        duration = time.monotonic() - t0
        status = "ok" if returncode == 0 else "failed"
        statuses[step.name] = status
        print(
            f"[daily-chain {now_fn().isoformat()}] {step.name} {status}"
            f" (exit {returncode}, {duration:.1f}s)",
            flush=True,
        )
        step_rows.append(
            {
                "name": step.name,
                "exit_code": returncode,
                "status": status,
                "started_at": started_at.isoformat(),
                "duration_s": round(duration, 3),
                "target": _fmt_target(step.target),
            }
        )

    any_failed = any(row["status"] == "failed" for row in step_rows)
    exit_code = 1 if any_failed else 0
    _write_report(
        report_path,
        {
            "schema": _REPORT_SCHEMA,
            "chain": {
                "target_start": _fmt_target(_CHAIN_TARGET),
                "started_at": chain_started.isoformat(),
                "finished_at": now_fn().isoformat(),
                "drift_minutes": drift_minutes,
                "exit_code": exit_code,
            },
            "steps": step_rows,
        },
    )
    return exit_code


def default_report_path(repo_root: Path) -> Path:
    # MUST equal what run_capture_gap_alert.py wires as chain_report_path
    # (its Runtime construction) — the cross-contract test holds them together.
    return repo_root / "app" / "data" / "ops" / "daily_chain_latest_report.json"


# Under --runtime-override, path rewriting covers every step that exposes its
# output paths as arguments. These two do not, so each carries its own
# data-declared redirect: feature_refresh HAS a flag for it; what_changed_report
# has no redirect flag at all (its report path is module-internal), so the only
# honest way to run it against a scratch runtime is its read-only --preflight.
_OVERRIDE_EXTRA: dict[str, tuple[str, ...]] = {
    "run_feature_refresh": ("--runtime-dir", "{override}"),
    "run_what_changed_report": ("--preflight",),
}


def apply_runtime_override(
    steps: tuple[ChainStep, ...],
    *,
    repo_root: Path,
    override_dir: Path,
) -> tuple[ChainStep, ...]:
    live_data = str(repo_root / "app" / "data")
    rewritten: list[ChainStep] = []
    for step in steps:
        argv = list(step.argv[:2])
        for arg in step.argv[2:]:
            if arg.startswith(live_data + os.sep):
                argv.append(str(override_dir) + arg[len(live_data):])
            else:
                argv.append(arg)
        for extra in _OVERRIDE_EXTRA.get(step.name, ()):
            argv.append(extra.replace("{override}", str(override_dir)))
        rewritten.append(
            ChainStep(
                name=step.name,
                argv=tuple(argv),
                hard_upstreams=step.hard_upstreams,
                target=step.target,
            )
        )
    return tuple(rewritten)


def load_steps_from(table_path: Path) -> tuple[ChainStep, ...]:
    rows = json.loads(table_path.read_text(encoding="utf-8"))
    return tuple(
        ChainStep(
            name=row["name"],
            argv=tuple(row["argv"]),
            hard_upstreams=tuple(row.get("hard_upstreams", ())),
            target=tuple(row.get("target", _CHAIN_TARGET)),
        )
        for row in rows
    )


def _print_plan(steps: tuple[ChainStep, ...]) -> None:
    print("daily chain — dependency order (dry run, nothing executed):")
    for index, step in enumerate(steps, start=1):
        upstream = (
            f"  hard upstreams: {', '.join(step.hard_upstreams)}"
            if step.hard_upstreams
            else "  hard upstreams: none"
        )
        print(f"  {index}. {step.name} (was {_fmt_target(step.target)}){upstream}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the six morning producers as one fail-soft chain (SR-09)."
    )
    parser.add_argument(
        "--dry-run",
        nargs="?",
        const="true",
        default="true",
        choices=("true", "false"),
        help="default true: print the plan and touch nothing. The plist passes --dry-run=false.",
    )
    parser.add_argument("--steps-from", type=Path, default=None)
    parser.add_argument("--runtime-override", type=Path, default=None)
    parser.add_argument("--report-path", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--step-extra",
        action="append",
        default=[],
        metavar="STEP=ARG",
        help="append ARG to STEP's argv (repeatable; SR-19's rehearsal forces "
        "--season-end through feature_refresh this way)",
    )
    args = parser.parse_args(argv)

    if (
        args.steps_from is not None
        and args.dry_run == "false"
        and args.report_path is None
        and args.runtime_override is None
    ):
        # Review finding (2026-08-26): the spec's own proof commands omit
        # --report-path, and a scratch step table writing the LIVE report path
        # feeds the 10:30 alert stub data — or silences a real failed morning.
        print(
            "refusing: --steps-from requires an explicit --report-path or "
            "--runtime-override — a scratch table must never write the "
            "production report the capture-gap alert reads",
            flush=True,
        )
        return 2

    repo_root = args.repo_root or Path(__file__).resolve().parents[1]
    steps = (
        load_steps_from(args.steps_from) if args.steps_from else build_steps(repo_root)
    )
    if args.runtime_override is not None:
        steps = apply_runtime_override(
            steps, repo_root=repo_root, override_dir=args.runtime_override
        )
    extras: list[tuple[str, str]] = []
    for raw in args.step_extra:
        name, sep, value = raw.partition("=")
        if not sep or not name or not value:
            print(f"refusing: malformed --step-extra '{raw}' (want STEP=ARG)", flush=True)
            return 2
        extras.append((name, value))
    try:
        if extras:
            steps = apply_step_extras(steps, extras)
        validate_steps(steps)
    except ValueError as exc:
        print(f"refusing: {exc}", flush=True)
        return 2

    if args.dry_run == "true":
        _print_plan(steps)
        return 0

    if args.report_path is not None:
        report_path = args.report_path
    elif args.runtime_override is not None:
        report_path = args.runtime_override / "daily_chain_latest_report.json"
    else:
        report_path = default_report_path(repo_root)
    return execute_chain(steps, report_path=report_path)


if __name__ == "__main__":
    raise SystemExit(main())
