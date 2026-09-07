#!/usr/bin/env python
"""Cold-start candidate for drafted skill players with no rookie-year regular-season record (DG-165, 2026-09-06).

Population, chronology, features, baselines, support floors and the per-horizon selection rule were frozen by root
before any fit (see docs/superpowers/plans/2026-09-06-unowned-cold-start-forecasts.md, Tasks 5-6). Every consumed
byte is verified against its producer's declaration; outputs go to a NEW immutable run directory. The accepted
825 rows and the coverage run's recovery sidecar are never touched.

    PYTHONPATH=. .venv/bin/python scripts/dg165/run_cold_start_candidate.py \\
        --capture runs/20260906T191723Z/weekly_source_capture \\
        --rookie-run runs/20260906T195904Z/dg165_rookie_capital \\
        --coverage-run runs/20260907T010020Z/dg165_cold_start_coverage \\
        --seed 20260906 --draws 2000
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dynasty_genius.rookie.cold_start import verified_parquet  # noqa: E402
from src.dynasty_genius.rookie.cold_start_model import (  # noqa: E402
    HORIZONS,
    SKILL_POSITIONS,
    assert_capture_coverage,
    evaluate_candidate,
    export_sidecar,
    first_full_reg_season,
    fit_arms,
    never_record_population,
    predict_arms,
    support_table,
    unresolved_from_ledger,
    verify_capture,
    write_candidate_run,
)
from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402
from src.dynasty_genius.rookie.transition_audit import load_rookie_run  # noqa: E402

REQUIRED_SEASONS = tuple(range(2001, 2026))
LAST_COMPLETE_SEASON = 2025
ORIGIN_2026 = 2026


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verified(path: Path, declared: str, what: str) -> bytes:
    data = path.read_bytes()
    if _sha(data) != declared:
        raise ValueError(f"{what}: sha256 mismatch for {path.name}")
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", required=True)
    ap.add_argument("--rookie-run", required=True)
    ap.add_argument("--coverage-run", required=True)
    ap.add_argument("--origins", type=int, nargs=2, default=[2012, 2025], metavar=("FIRST", "LAST"))
    ap.add_argument("--seed", type=int, default=20260906)
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--runs-root", default="runs")
    args = ap.parse_args(argv)
    try:
        capture = Path(args.capture)
        season_files = assert_capture_coverage(capture, required_seasons=REQUIRED_SEASONS)
        capture_files = verify_capture(capture)
        capture_manifest_sha = _sha((capture / "manifest.json").read_bytes())
        rookie = load_rookie_run(args.rookie_run)  # cohort, out_of_time, draft picks and the outcome artifact verified by hash
        players = verified_parquet(Path(args.rookie_run) / "inputs" / "nflverse_players.parquet",
                                   rookie.manifest["inputs"]["nflverse_players"]["sha256"], "rookie run players")
        art_path = Path(rookie.manifest["outcomes"]["csv_path"])
        outcomes = pd.read_csv(io.BytesIO(_verified(art_path, rookie.manifest["outcomes"]["csv_sha256"], "outcome artifact")))
        cov_dir = Path(args.coverage_run)
        cov_manifest = json.loads((cov_dir / "manifest.json").read_text())
        ledger = pd.read_csv(io.BytesIO(_verified(cov_dir / "ledger.csv", cov_manifest["outputs_sha256"]["ledger.csv"], "coverage run")),
                             dtype={"sleeper_id": str, "gsis_id": str})
        first_reg = first_full_reg_season(capture)
        population = never_record_population(cohort=rookie.cohort, first_reg=first_reg, outcomes=outcomes, players=players,
                                             last_complete_season=LAST_COMPLETE_SEASON)
        origins = range(args.origins[0], args.origins[1] + 1)
        support = support_table(population, origins=origins, horizons=HORIZONS)
        evaluation = evaluate_candidate(population, origins=origins, horizons=HORIZONS, seed=args.seed, draws=args.draws)
        paired_rows = evaluation["paired_rows_frame"]
        # the verified new-eligible candidates: ledger route never_appeared_drafted, class 2025, skill draft position, in the population
        cand = ledger.loc[(ledger["route"] == "never_appeared_drafted") & (ledger["draft_season"] == 2025)
                          & ledger["draft_position"].isin(SKILL_POSITIONS)].copy()
        in_pop = set(population.loc[population["draft_season"] == 2025, "gsis_id"])
        cand = cand.loc[cand["gsis_id"].isin(in_pop)]
        cand_rows = population.loc[population["gsis_id"].isin(set(cand["gsis_id"]))].copy()
        # final fits at origin 2026: training rows with c + h < 2026 and jointly complete labels
        pred = pd.DataFrame({"gsis_id": cand_rows["gsis_id"].astype(str).to_numpy()})
        final_support = {}
        selected = {}
        for h in HORIZONS:
            complete = population[f"appear_{h}"].notna() & population[f"points_{h}"].notna() & population[f"games_{h}"].notna()
            train = population.loc[(population["draft_season"] + h < ORIGIN_2026) & complete]
            fit = fit_arms(train, horizon=h, origin=ORIGIN_2026)
            final_support[str(h)] = {"train_rows": fit["candidate"]["n_train"], "train_appearers": fit["candidate"]["n_appearers"],
                                     "candidate_supported": bool(fit["candidate"]["supported"]), "candidate_reason": fit["candidate"]["reason"],
                                     "age_fallback": fit["candidate"]["age_fallback"],
                                     "b1_cells": {p: {k: c[k] for k in ("n", "appearers", "supported", "conditional_supported")} for p, c in fit["b1"]["cells"].items()}}
            ph = predict_arms(fit, cand_rows)
            for col in ph.columns:
                if col != "gsis_id":
                    pred[f"{col}_{h}"] = ph[col].to_numpy()
            selected[h] = evaluation["horizons"].get(str(h), {}).get("selection", "unsupported")
        evaluation["final_origin_2026"] = {"support": final_support, "selected_per_horizon": {str(k): v for k, v in selected.items()}}
        cand_export = cand.rename(columns={"draft_position": "draft_position"})[["sleeper_id", "gsis_id", "name", "draft_position", "draft_season",
                                                                                 "route", "draft_status", "identity_status"]]
        binding = {"origin_year": ORIGIN_2026, "capture_manifest_sha256": capture_manifest_sha, "artifact_sha256": rookie.manifest["outcomes"]["csv_sha256"],
                   "cohort_sha256": rookie.verified["cohort.csv"], "coverage_run": str(cov_dir)}
        sidecar = export_sidecar(cand_export, pred, selected_per_horizon=selected, origin_year=ORIGIN_2026, binding=binding)
        unresolved = unresolved_from_ledger(ledger, candidate_ids=set(cand["gsis_id"]))
        recovered = int((ledger["route"] == "existing_forecast_join_failure").sum())
        if len(sidecar) + len(unresolved) != len(ledger) or len(sidecar) + recovered + int((unresolved["status"] == "unresolved").sum()) != len(ledger):
            raise ValueError("candidates + recovered + unresolved must partition the ledger exactly")
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    inputs = {
        "capture": {"dir": str(capture), "manifest_sha256": capture_manifest_sha, "files": capture_files, "season_files": season_files,
                    "required_seasons": [REQUIRED_SEASONS[0], REQUIRED_SEASONS[-1]]},
        "rookie_run": {"run_dir": str(rookie.run_dir), "manifest_sha256": rookie.manifest_sha256, "verified": rookie.verified,
                       "players_parquet_sha256": rookie.manifest["inputs"]["nflverse_players"]["sha256"]},
        "outcome_artifact": {"path": str(art_path), "sha256": rookie.manifest["outcomes"]["csv_sha256"],
                             "target_identity": rookie.manifest["outcomes"]["target_identity"]},
        "coverage_run": {"run_dir": str(cov_dir), "manifest_sha256": _sha((cov_dir / "manifest.json").read_bytes()),
                         "ledger_sha256": cov_manifest["outputs_sha256"]["ledger.csv"]},
        "partition": {"ledger_rows": int(len(ledger)), "candidates": int(len(sidecar)), "recovered_existing_forecast": recovered,
                      "unresolved": int((unresolved["status"] == "unresolved").sum())},
        "population": {"rows": int(len(population)), "by_position": population["draft_position"].value_counts().to_dict()},
    }
    run_dir = create_run_dir(args.runs_root, name="dg165_cold_start_candidate")
    write_candidate_run(run_dir, population=population, support=support, evaluation=evaluation, paired_rows=paired_rows, sidecar=sidecar,
                        unresolved=unresolved, inputs=inputs, git_sha=git_sha())
    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
