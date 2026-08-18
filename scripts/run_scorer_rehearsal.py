#!/usr/bin/env python3.14
"""Week-1 dress rehearsal for the Realized-Outcome Loop — with a negative control.

WHY THIS EXISTS
    As of 2026-08-18 the loop had graded zero predictions, ever. Its whole logged history
    was five ``noop`` and one failure. "It will work on Week 1" was an assumption, and Week
    1 morning is the worst possible time to discover otherwise.

    Loading 501 real predictions proves the plumbing carries data. It does NOT prove the
    grader discriminates: a scorer that silently no-ops, or one whose identity join quietly
    drops everything, reports a clean scorecard either way. So this harness runs the SAME
    path twice — once with the real frozen predictions, once with a deliberately WRONG set
    — and requires the scorecard to tell them apart. If it cannot, the rehearsal FAILS.

WHAT IS REAL AND WHAT IS SUBSTITUTED — read before citing any number this emits
    REAL: the 501 frozen predictions (declared capture 2026-08-05), the identity bridge and
    its sleeper→gsis crosswalk, the scoring code path, and the realized outcome rows.
    SUBSTITUTED: the outcomes come from a COMPLETED season, because the target season has
    played no games yet. The schedule is synthesized as finalized so the finality gate opens.

    Therefore the emitted scorecard is a PLUMBING artifact, not a model result. A 2026
    projection graded against a prior season's actuals says nothing about model accuracy.
    Every artifact is stamped ``rehearsal: true`` and carries its substitution list so it can
    never be mistaken for the model's record. The scoreboard's real seed numbers are QB-1's
    fourteen contrasts; this supplies the SHAPE the scoreboard renders, and the proof that
    live weeks will populate it.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_realized_outcome_scoring import (  # noqa: E402
    _default_identity_snapshot_loader,
    _default_prediction_loader,
    _default_stat_loader,
    _default_util_loader,
    run_scoring,
)

REHEARSAL_DIR = ROOT / "app" / "data" / "backtest" / "rehearsal"
PREDICTION_SEASON = 2026  # the season the frozen set predicts
DEFAULT_OUTCOME_SEASON = 2025  # completed season standing in for unplayed outcomes


def _finalized_schedule(season: int, week: int, *, game_count: int = 16) -> dict[str, Any]:
    """A synthetic FINALIZED schedule so the finality gate opens.

    `week_status` requires `expected_game_count` to match the number of listed games and
    every game to be `final`. Nothing downstream reads team names, so the games are
    placeholders; the gameday is backdated only so the nonfinal-age law is not tripped.
    """
    return {
        "expected_game_count": game_count,
        "games": [
            {
                "season": season,
                "week": week,
                "game_id": f"rehearsal-{season}-{week}-{index}",
                "status": "final",
                "gameday": "2026-09-14",
            }
            for index in range(game_count)
        ],
    }


def _restamp(rows: list[dict[str, Any]], *, season: int) -> list[dict[str, Any]]:
    """Relabel substituted outcome rows to the target season.

    The capture store asserts that every stat/util row's season matches the ingest season
    and raises otherwise — a correct guard that caught this harness feeding prior-season
    rows into a target-season ingest on the first run. The VALUES stay real and untouched;
    only the season label moves, and the artifact discloses the substitution. Nothing here
    weakens the guard: it still protects every production path, which never restamps.
    """
    return [{**row, "season": season} for row in rows]


def _corrupt_predictions(rows: list[dict[str, Any]], *, seed: int) -> list[dict[str, Any]]:
    """The negative control: keep every player, permute the projections between them.

    This is deliberately the HARDEST corruption for a broken grader to hide. Row count,
    schema, identity fields, and the value DISTRIBUTION are all identical to the real set —
    only the pairing of player→projection is destroyed. Coverage, join, and shape checks
    therefore look untouched; solely the rank correlation should collapse. A scorer that
    reports the same metrics for both is not grading, it is echoing.
    """
    corrupted = [dict(row) for row in rows]
    projections = [row.get("projection_2y") for row in corrupted]
    rng = random.Random(seed)
    rng.shuffle(projections)
    for row, projection in zip(corrupted, projections):
        row["projection_2y"] = projection
    return corrupted


def _run_once(
    label: str,
    predictions: list[dict[str, Any]],
    *,
    outcome_season: int,
    week: int,
) -> dict[str, Any]:
    report_path = REHEARSAL_DIR / f"scorecard_{label}.json"
    REHEARSAL_DIR.mkdir(parents=True, exist_ok=True)

    # The marker goes to a FRESH directory every invocation, and this is load-bearing.
    # `run_scoring` short-circuits to `noop:already_scored` when a marker records the same
    # (season, week) as ok — correct for the scheduled loop, fatal for a rehearsal: the run
    # grades nothing, and the summary below then reads the PREVIOUS run's scorecard off disk
    # and reports it as this run's result. That is a rehearsal that passes without rehearsing
    # — the exact false confidence this harness exists to prevent. Caught 2026-08-18 when
    # both markers came back `already_scored` one millisecond apart.
    marker_dir = Path(tempfile.mkdtemp(prefix="scorer-rehearsal-"))
    marker_path = marker_dir / f"marker_{label}.json"

    # Fail loudly rather than silently re-reading: if the scorecard is not rewritten by this
    # call, the numbers below are not this run's.
    before_mtime = report_path.stat().st_mtime if report_path.exists() else None

    result = run_scoring(
        season=PREDICTION_SEASON,
        week=week,
        report_path=report_path,
        marker_path=marker_path,
        enforce_target_freshness=False,  # explicit target: this is an intentional backfill
        schedule_loader=lambda season, wk: _finalized_schedule(season, wk),
        # Outcomes come from the completed season; the target season has played no games.
        stat_loader=lambda season, wk: _restamp(
            _default_stat_loader(outcome_season, wk), season=season
        ),
        util_loader=lambda season, wk: _restamp(
            _default_util_loader(outcome_season, wk), season=season
        ),
        prediction_loader=lambda _season, _wk: list(predictions),
        identity_snapshot_loader=lambda season, wk: _default_identity_snapshot_loader(
            season, wk
        ),
    )
    if result.get("status") == "noop" and result.get("noop_reason") == "already_scored":
        raise RuntimeError(
            f"[{label}] scoring short-circuited on a stale marker — the rehearsal graded "
            "nothing. This must never be reported as a pass."
        )
    after_mtime = report_path.stat().st_mtime if report_path.exists() else None
    if after_mtime is not None and after_mtime == before_mtime:
        raise RuntimeError(
            f"[{label}] scorecard was NOT rewritten by this run ({report_path}); any "
            "metrics read from it belong to an earlier invocation."
        )
    return {"label": label, "result": result, "report_path": report_path}


def _rank_metrics(report_path: Path) -> dict[str, Any]:
    """Pull the per-position rank metrics out of an emitted scorecard."""
    if not report_path.exists():
        return {}
    payload = json.loads(report_path.read_text())
    found: dict[str, Any] = {}
    for position, block in (payload.get("cohort_metrics") or {}).items():
        block = block or {}
        found[position] = {
            "status": block.get("status"),
            "spearman": (block.get("spearman") or {}).get("value"),
            "ndcg": (block.get("ndcg") or {}).get("value"),
            "eligible": block.get("eligible_count"),
        }
    found["_coverage"] = {
        key: (payload.get("coverage") or {}).get(key)
        for key in ("graded_count", "rank_eligible_count", "resolved_count")
    }
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--outcome-season", type=int, default=DEFAULT_OUTCOME_SEASON)
    parser.add_argument("--seed", type=int, default=20260818)
    args = parser.parse_args(argv)

    envelope = _default_prediction_loader(PREDICTION_SEASON, args.week)
    real_rows = envelope["rows"] if isinstance(envelope, dict) else list(envelope)
    print(f"loaded {len(real_rows)} real frozen predictions")

    runs = [
        _run_once("real", real_rows, outcome_season=args.outcome_season, week=args.week),
        _run_once(
            "control_shuffled",
            _corrupt_predictions(real_rows, seed=args.seed),
            outcome_season=args.outcome_season,
            week=args.week,
        ),
    ]

    summary: dict[str, Any] = {"runs": {}, "rehearsal": True}
    for run in runs:
        status = run["result"].get("status")
        metrics = _rank_metrics(run["report_path"])
        summary["runs"][run["label"]] = {
            "status": status,
            "failure_reason": run["result"].get("failure_reason"),
            "noop_reason": run["result"].get("noop_reason"),
            "rank_metrics": metrics,
        }
        print(f"\n[{run['label']}] status={status}")
        for position, values in sorted(metrics.items()):
            if position == "_coverage":
                continue
            print(
                f"  {position}: status={values['status']} n={values['eligible']!r} "
                f"spearman={values['spearman']!r} ndcg={values['ndcg']!r}"
            )

    # ── the verdict: the control MUST score materially worse, or this proved nothing ──
    real = summary["runs"]["real"]["rank_metrics"]
    control = summary["runs"]["control_shuffled"]["rank_metrics"]
    verdict: dict[str, Any] = {"discriminated": {}, "undiscriminated": []}
    for position in sorted(k for k in real if k != "_coverage"):
        real_rho = (real.get(position) or {}).get("spearman")
        control_rho = (control.get(position) or {}).get("spearman")
        if real_rho is None or control_rho is None:
            verdict["undiscriminated"].append(
                f"{position}: metrics not computed "
                f"(status={(real.get(position) or {}).get('status')}) — a corrupted set "
                f"is INDISTINGUISHABLE from the real one at this week"
            )
            continue
        verdict["discriminated"][position] = {
            "real_spearman": real_rho,
            "control_spearman": control_rho,
            "delta": real_rho - control_rho,
        }
    summary["verdict"] = verdict

    print("\n=== NEGATIVE-CONTROL VERDICT ===")
    for position, values in sorted(verdict["discriminated"].items()):
        print(
            f"  {position}: real {values['real_spearman']:+.3f} vs "
            f"control {values['control_spearman']:+.3f}  (delta {values['delta']:+.3f})"
        )
    for line in verdict["undiscriminated"]:
        print(f"  ! {line}")
    passed = bool(verdict["discriminated"]) and not verdict["undiscriminated"]
    summary["rehearsal_passed"] = passed
    print(f"\nREHEARSAL {'PASSED' if passed else 'INCONCLUSIVE'}")

    (REHEARSAL_DIR / "rehearsal_summary.json").write_text(
        json.dumps(summary, indent=2, default=str)
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
