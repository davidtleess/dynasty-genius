#!/usr/bin/env python
"""Coverage ledger for unowned default-pool players without a forecast (DG-165, available-players build).

Reads hash-verified captured inputs only and writes a NEW immutable run under --runs-root:
ledger.csv (one row per missing player), summary.json, REPORT.md, recovery_sidecar.csv (original
DG-177 rows for identity-join failures, copied not refitted) and manifest.json. Produces no estimate
and alters no accepted forecast. Exit code non-zero on any refusal.

    PYTHONPATH=. .venv/bin/python scripts/dg165/audit_cold_start_coverage.py \\
        --census-run /Users/davidleess/dg-wt/DG-178/runs/20260906T202057Z/dg178_current_census \\
        --accepted-report /Users/davidleess/dg-wt/DG-178/runs/20260906T214512Z/dg178_audit/report.json \\
        --rookie-run runs/20260906T195904Z/dg165_rookie_capital \\
        --veteran-run /Users/davidleess/dg-wt/DG-177/runs/20260906T195728Z/dg177_basic_horizons
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.rookie.cold_start import (  # noqa: E402
    build_ledger,
    draft_evidence,
    full_nfl_source_status,
    load_accepted_report,
    load_census_run,
    missing_default_pool,
    nfl_history,
    recovery_sidecar,
    summarize_ledger,
    verified_parquet,
    write_coverage,
)
from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402
from src.dynasty_genius.rookie.transition_audit import (  # noqa: E402
    load_rookie_run,
    load_veteran_run,
)


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _verified(path: Path, declared: str, what: str) -> bytes:
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != declared:
        raise ValueError(f"{what}: sha256 mismatch for {path.name}: declared {declared[:12]}…, actual {actual[:12]}…")
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--census-run", required=True)
    ap.add_argument("--accepted-report", required=True)
    ap.add_argument("--rookie-run", required=True, help="frozen DG-165 rookie run (hashed nflverse inputs, rookie scores, bound outcome artifact)")
    ap.add_argument("--veteran-run", required=True, help="frozen DG-177 run (basic cohort/forecasts, universe reconciliation), read-only")
    ap.add_argument("--runs-root", default="runs")
    args = ap.parse_args(argv)
    try:
        census = load_census_run(args.census_run)
        accepted = load_accepted_report(args.accepted_report)
        rookie = load_rookie_run(args.rookie_run)
        veteran = load_veteran_run(args.veteran_run)
        missing = missing_default_pool(census, accepted)
        vet_dir = Path(args.veteran_run)
        declared = veteran.manifest["outputs_sha256"]
        bf_raw = _verified(vet_dir / "basic_forecasts.csv", declared["basic_forecasts.csv"], "veteran run")
        ur_raw = _verified(vet_dir / "universe_reconciliation.csv", declared["universe_reconciliation.csv"], "veteran run")
        import io
        basic_forecasts = pd.read_csv(io.BytesIO(bf_raw))
        universe = pd.read_csv(io.BytesIO(ur_raw))
        rookie_scores_path = Path(args.rookie_run) / "rookie_scores_2026.csv"
        rs_raw = _verified(rookie_scores_path, rookie.manifest["outputs_sha256"]["rookie_scores_2026.csv"], "rookie run")
        rookie_scores = pd.read_csv(io.BytesIO(rs_raw))
        art_path = Path(rookie.manifest["outcomes"]["csv_path"])
        outcomes = pd.read_csv(io.BytesIO(_verified(art_path, rookie.manifest["outcomes"]["csv_sha256"], "outcome artifact")))
        players_sha = rookie.manifest["inputs"]["nflverse_players"]["sha256"]
        rosters_sha = rookie.manifest["inputs"]["nflverse_rosters"]["sha256"]
        players = verified_parquet(Path(args.rookie_run) / "inputs" / "nflverse_players.parquet", players_sha, "rookie run players")
        rosters = verified_parquet(Path(args.rookie_run) / "inputs" / "nflverse_rosters.parquet", rosters_sha, "rookie run rosters")
        evidence = draft_evidence(missing["nfl_gsis_id"], draft_picks=rookie.draft_picks, players=players, rosters=rosters)
        history = nfl_history(missing["nfl_gsis_id"], outcomes=outcomes, basic_cohort=veteran.cohort, basic_forecasts=basic_forecasts,
                              rookie_scores=rookie_scores, last_complete_season=int(veteran.manifest["last_complete_season"]))
        full_nfl = full_nfl_source_status(missing["sleeper_id"], universe)
        ledger = build_ledger(missing, evidence, history, full_nfl)
        recovery = recovery_sidecar(ledger, basic_forecasts=basic_forecasts, veteran_binding={
            "run_dir": str(vet_dir), "manifest_sha256": veteran.manifest_sha256, "corrected_manifest_sha256": veteran.corrected_manifest_sha256,
            "basic_forecasts_sha256": declared["basic_forecasts.csv"]})
        summary = summarize_ledger(ledger)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    inputs = {
        "census_run": {"run_dir": str(census.run_dir), "census_csv_sha256": census.census_sha256, "report_sha256": census.report_sha256},
        "accepted_report": {"path": str(accepted.path), "sha256": accepted.sha256},
        "rookie_run": {"run_dir": str(rookie.run_dir), "manifest_sha256": rookie.manifest_sha256, "verified": rookie.verified,
                       "rookie_scores_sha256": rookie.manifest["outputs_sha256"]["rookie_scores_2026.csv"],
                       "players_parquet_sha256": players_sha, "rosters_parquet_sha256": rosters_sha,
                       "players_rosters_bytes_verified": True},
        "veteran_run": {"run_dir": str(vet_dir), "manifest_sha256": veteran.manifest_sha256, "corrected_manifest_sha256": veteran.corrected_manifest_sha256,
                        "basic_forecasts_sha256": declared["basic_forecasts.csv"], "universe_reconciliation_sha256": declared["universe_reconciliation.csv"],
                        "basic_cohort_sha256": declared["basic_cohort.csv.gz"]},
        "outcome_artifact": {"path": str(art_path), "sha256": rookie.manifest["outcomes"]["csv_sha256"]},
    }
    run_dir = create_run_dir(args.runs_root, name="dg165_cold_start_coverage")
    write_coverage(run_dir, ledger=ledger, summary=summary, recovery=recovery, inputs=inputs, git_sha=git_sha())
    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
