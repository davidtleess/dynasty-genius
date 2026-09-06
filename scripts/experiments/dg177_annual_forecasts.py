#!/usr/bin/env python3
"""DG-177 — year-1 / year-2 veteran forecast candidates on the appearance event.

REPORT-ONLY. Reads the tracked training CSV and the served manifest (read-only, for the
per-position feature lists), pulls nflverse weekly player stats over the network into
this run's directory (public data; saved with its sha so the labels are reproducible),
and writes ONLY a new run-scoped directory. Nothing served changes.

What it produces, per the annual target contract agreed with DG-178 on 2026-09-06:
  scope REG · scoring fantasy_points_ppr · exposure = weekly stat-row games ·
  event A_j = appeared (>= 1 game) · quantities p_appear, e_points|appear,
  e_games|appear, e_points = p x e, e_games = p x e · horizons j = 1, 2 only.

Two feature arms are evaluated historically on every horizon: the served position
feature list (the candidate) and the three-column recent-production set (comparator).
Both are graded against training-only baselines. The final forecasts exported for the
ranking lane use the served feature list, fitted on every row whose year-j label was
closed at the end of the last complete season, and score the inference partition.

Usage (from the worktree root):
    .venv/bin/python scripts/experiments/dg177_annual_forecasts.py [--draws 2000]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.experiments.dg177_veteran_candidate import (  # noqa: E402
    DATASET_PATH,
    MANIFEST_PATH,
    RECENT_PRODUCTION_FEATURES,
    RUNS_ROOT,
    _fmt,
    _fmt_delta,
    _git,
    collect_provenance,
    served_feature_lists,
)
from src.dynasty_genius.eval.annual_forecasts import (  # noqa: E402
    QUANTITIES,
    evaluate_horizon,
    fit_horizon,
    observed_mask,
)
from src.dynasty_genius.eval.annual_outcomes import (  # noqa: E402
    EVENT,
    EXPOSURE,
    SCOPES,
    SCORING_COLUMN,
    annual_targets,
    season_outcomes,
)
from src.dynasty_genius.eval.veteran_candidate import write_run_artifact  # noqa: E402
from src.dynasty_genius.models.label_closure import assert_labels_known  # noqa: E402

SCOPE = "REG"
HORIZONS = (1, 2)
INFERENCE_SEASON = 2025
LAST_COMPLETE_SEASON = 2025
PULL_SEASONS = list(range(2018, 2026))
FORECAST_CUTOFF_RULE = "features observed through the feature season; a year-j label trains only when feature_season + j <= last complete season"
ARM_CANDIDATE = "served_features"
ARM_COMPARATOR = "recent_production_3col"
TEST_SEASONS_BY_HORIZON = {1: [2019, 2020, 2021, 2022, 2023], 2: [2020, 2021, 2022, 2023]}
WEEKLY_COLUMNS = ["player_id", "season", "week", "season_type", "position", "team", SCORING_COLUMN]


def pull_weekly_stats(seasons: Iterable[int]) -> pd.DataFrame:
    """Weekly player stats from nflverse (network). Only the columns the labels need."""
    import nflreadpy as nfl

    frame = nfl.load_player_stats(seasons=list(seasons), summary_level="week")
    frame = frame.to_pandas() if hasattr(frame, "to_pandas") else frame
    out = frame[WEEKLY_COLUMNS].copy()
    out["season"] = out["season"].astype(int)
    out["week"] = out["week"].astype(int)
    out[SCORING_COLUMN] = pd.to_numeric(out[SCORING_COLUMN], errors="coerce").fillna(0.0)
    return out.reset_index(drop=True)


def final_forecasts(
    df: pd.DataFrame,
    features_by_position: dict[str, list[str]],
    *,
    horizons: Iterable[int],
    inference_season: int,
    last_complete_season: int,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    """Fit each horizon on every row whose year-j label was closed at the end of
    ``last_complete_season`` and score the inference partition. Refuses if a row the
    closure rule admits is marked censored — the frame and the claimed clock disagree."""
    horizons = [int(h) for h in horizons]
    frames: list[pd.DataFrame] = []
    fits: dict[str, dict[str, Any]] = {}
    for position, features in features_by_position.items():
        rows = df[df["position"] == position]
        test = rows[rows["feature_season"] == inference_season].reset_index(drop=True)
        if test.empty:
            continue
        out = test[["player_id", "position", "feature_season", "identity_status"]].copy()
        fits[position] = {}
        for j in horizons:
            closed = rows[rows["feature_season"].astype(int) + j <= int(last_complete_season)]
            contradicted = closed[closed[f"censored_year{j}"].astype(bool)]
            if len(contradicted):
                raise ValueError(
                    f"{len(contradicted)} {position} rows with feature seasons "
                    f"{sorted(contradicted['feature_season'].unique())} are admitted by the closure "
                    f"rule at last complete season {last_complete_season} but carry censored "
                    f"year-{j} labels; the frame and the claimed season clock disagree"
                )
            train = closed[observed_mask(closed, j)]
            assert_labels_known(train, int(last_complete_season), window=j)
            pred, meta = fit_horizon(train, test, features, horizon=j)
            out[f"forecast_season_year{j}"] = int(inference_season) + j
            for name in QUANTITIES(j):
                out[name] = pred[name]
            fits[position][f"year{j}"] = meta
        frames.append(out)
    forecasts = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return forecasts, fits


def build_manifest(
    *, horizons: Iterable[int], inference_season: int, last_complete_season: int, scope: str,
    source: dict[str, Any], git_head: str, features_by_position: dict[str, list[str]], population: str,
) -> dict[str, Any]:
    horizons = [int(h) for h in horizons]
    return {
        "producer": "DG-177 veteran annual forecast candidate (report-only)",
        "forecast_cutoff": {
            "rule": FORECAST_CUTOFF_RULE,
            "feature_season": int(inference_season),
            "information_through": f"end of the {inference_season} NFL season including postseason",
        },
        "last_complete_season": int(last_complete_season),
        "label_window": {f"year{j}": j for j in horizons},
        "scoring_scope": {"scope": scope, "scoring": SCORING_COLUMN, "season_types": list(SCOPES[scope])},
        "exposure_definition": EXPOSURE,
        "event": EVENT,
        "quantities": {f"year{j}": QUANTITIES(j) for j in horizons},
        "composition": "e_points_year{j} = p_appear_year{j} x e_points_year{j}_given_appear on the same event and rows; "
                       "points and games are exactly 0 when absent",
        "horizons_supported": horizons,
        "longer_horizons": "unsupported: not measured",
        "population": population,
        "no_forecast_reason_for_absent_players": "no_feature_row",
        "features_by_position": {p: list(f) for p, f in features_by_position.items()},
        "intervals": "none exported; historical bootstrap intervals are conditional on the fitted models "
                     "(fit uncertainty), not model or season uncertainty",
        "source": source,
        "git_head": git_head,
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_report(results: dict[str, Any]) -> str:
    lines = ["# DG-177 — year-1 / year-2 forecast candidates on the appearance event\n"]
    m = results["manifest"]
    lines.append(f"Scope `{m['scoring_scope']['scope']}` · scoring `{m['scoring_scope']['scoring']}` · event: {m['event']} · "
                 f"exposure: {m['exposure_definition']} · horizons {m['horizons_supported']} · git `{m['git_head']}`\n")
    a = results.get("alignment_check", {})
    if a:
        lines.append(f"Alignment of the pulled ALL-games points with the training file's `total_points_t` on the same "
                     f"player-seasons: {a['rows_compared']} rows, {a['share_within_0_01']:.1%} within 0.01, "
                     f"max abs diff {a['max_abs_diff']:.3f}.\n")
    for position, block in results["historical"].items():
        for j_key, horizons in block.items():
            for arm, ev in horizons.items():
                lines.append(f"\n## {position} · {j_key} · arm `{arm}` (k = {ev['k']})\n")
                lines.append("| test season | forecast season | train seasons | train obs | test obs / appeared | status |")
                lines.append("|---|---|---|---:|---|---|")
                for f in ev["folds"]:
                    status = "evaluated" if f["skipped_reason"] is None else f"skipped — {f['skipped_reason']}"
                    lines.append(f"| {f['test_season']} | {f['forecast_season']} | {f['train_seasons']} | "
                                 f"{f['n_train_observed']} | {f['n_test_observed']} / {f['n_test_appeared']} | {status} |")
                p = ev.get("pooled") or {}
                if not p:
                    lines.append("\nNo fold evaluable.\n")
                    continue
                pr = p["probability"]
                lines.append(f"\nP(appear): Brier {_fmt(pr['brier'])} vs baseline {_fmt(pr['baseline_brier'])} · AUC "
                             f"{_fmt(pr['auc'])} · base rate {_fmt(pr['base_rate'])} · mean predicted {_fmt(pr['mean_predicted'])} · "
                             f"n {pr['n']}\n")
                lines.append("| quantity | model RMSE | baseline RMSE | ΔRMSE vs baseline [90%] | model r² | Δr² [90%] | ΔSpearman [90%] | Δtop-k by season [90%] |")
                lines.append("|---|---:|---:|---|---:|---|---|---|")
                for key, label in (("points_given_appear", "points | appear"), ("games_given_appear", "games | appear"),
                                   ("points_unconditional", "points (unconditional)")):
                    b = p[key]
                    d = b["delta_vs_baseline"]
                    lines.append(f"| {label} | {_fmt(b['model']['rmse'])} | {_fmt(b['baseline']['rmse'])} | "
                                 f"{_fmt_delta(d['delta_rmse'])} | {_fmt(b['model']['r2'])} | {_fmt_delta(d['delta_r2'])} | "
                                 f"{_fmt_delta(d['delta_spearman'])} | {_fmt_delta(d['delta_topk_overlap'])} |")
                lines.append("\nPer fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:\n")
                for f in ev["folds"]:
                    if f["skipped_reason"] is None:
                        lines.append(f"- {f['test_season']}→{f['forecast_season']}: Brier {_fmt(f['probability']['brier'])} / "
                                     f"{_fmt(f['probability']['baseline_brier'])}; points|appear ΔRMSE "
                                     f"{_fmt_delta(f['points_given_appear']['delta_vs_baseline']['delta_rmse'])}; "
                                     f"alpha points {f['fit']['points_model']['alpha']:g}, games {f['fit']['games_model']['alpha']:g}")
    fc = results.get("final_forecast_coverage", {})
    if fc:
        lines.append("\n## Final forecasts exported (inference partition)\n")
        lines.append(f"Feature season {fc['feature_season']}; rows {fc['rows']} ({fc['by_position']}); "
                     f"identity {fc['identity_status']}; players with no {fc['feature_season']} feature row receive no forecast "
                     f"(reason `no_feature_row`), never 0.\n")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--min-train-rows", type=int, default=60)
    parser.add_argument("--out-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args(argv)

    from src.dynasty_genius.eval.backtest_harness import PRIMARY_NDCG_K

    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / run_id / "dg177_annual_forecasts"

    df = pd.read_csv(DATASET_PATH, low_memory=False)
    served = served_feature_lists(MANIFEST_PATH, ROOT)
    features_by_position = {p: info["features"] for p, info in served.items()}

    pulled_at = datetime.now(timezone.utc)
    weekly = pull_weekly_stats(PULL_SEASONS)
    snapshot_bytes = gzip.compress(weekly.to_csv(index=False).encode("utf-8"))
    snapshot_sha = _sha256_bytes(snapshot_bytes)
    import nflreadpy

    outcomes = season_outcomes(weekly, scope=SCOPE)
    outcomes_all = season_outcomes(weekly, scope="ALL")
    labelled = annual_targets(df, outcomes, horizons=HORIZONS, last_complete_season=LAST_COMPLETE_SEASON)
    df = pd.concat([df.reset_index(drop=True), labelled.drop(columns=["player_id", "position", "feature_season"])], axis=1)

    # The pulled ALL-games points must reproduce the training file's own totals for the
    # same player-seasons; if they do not, the label source is not the product's source.
    check = df[["player_id", "feature_season", "total_points_t"]].merge(
        outcomes_all.rename(columns={"season": "feature_season", "points": "pulled_points_all"}),
        on=["player_id", "feature_season"], how="left",
    )
    diff = (check["total_points_t"] - check["pulled_points_all"]).abs()
    alignment = {
        "rows_compared": int(diff.notna().sum()),
        "rows_unmatched": int(diff.isna().sum()),
        "share_within_0_01": float((diff <= 0.01).mean()),
        "max_abs_diff": float(diff.max()),
        "basis": "sum of fantasy_points_ppr over REG+POST vs total_points_t (DG-024 all games)",
    }
    print(f"rows {len(df)} · weekly rows {len(weekly)} · alignment within 0.01: {alignment['share_within_0_01']:.3%}")

    historical: dict[str, Any] = {}
    prediction_frames: list[pd.DataFrame] = []
    for position, features in features_by_position.items():
        k = int(PRIMARY_NDCG_K.get(position, 12))
        pos_df = df[df["position"] == position]
        historical[position] = {}
        for j in HORIZONS:
            historical[position][f"year{j}"] = {}
            for arm, feats in ((ARM_CANDIDATE, features), (ARM_COMPARATOR, RECENT_PRODUCTION_FEATURES)):
                ev, preds = evaluate_horizon(
                    pos_df, feats, horizon=j, test_seasons=TEST_SEASONS_BY_HORIZON[j], k=k,
                    draws=args.draws, seed=args.seed, min_train_rows=args.min_train_rows,
                )
                historical[position][f"year{j}"][arm] = ev
                preds.insert(0, "arm", arm)
                preds.insert(0, "horizon", j)
                prediction_frames.append(preds)
                print(f"  {position} year{j} {arm}: evaluated {ev['evaluated_test_seasons']}")

    forecasts, fits = final_forecasts(
        df, features_by_position, horizons=HORIZONS, inference_season=INFERENCE_SEASON,
        last_complete_season=LAST_COMPLETE_SEASON,
    )
    forecasts.insert(3, "forecast_cutoff", f"post-{INFERENCE_SEASON}-season")
    coverage = {
        "feature_season": INFERENCE_SEASON,
        "rows": int(len(forecasts)),
        "by_position": forecasts.groupby("position").size().to_dict() if len(forecasts) else {},
        "identity_status": forecasts["identity_status"].value_counts().to_dict() if len(forecasts) else {},
    }

    files = {"training_csv": DATASET_PATH, "engine_b_manifest": MANIFEST_PATH}
    for position, info in served.items():
        files[f"served_{position.lower()}_pickle"] = ROOT / info["path"]
    source = {
        "weekly_stats": "nflreadpy.load_player_stats(seasons=2018..2025, summary_level='week')",
        "weekly_stats_pulled_at_utc": pulled_at.isoformat(),
        "weekly_stats_rows": int(len(weekly)),
        "weekly_stats_sha256": snapshot_sha,
        "weekly_stats_snapshot": "weekly_stats_snapshot.csv.gz (in this run directory)",
        "nflreadpy": nflreadpy.__version__,
    }
    manifest = build_manifest(
        horizons=HORIZONS, inference_season=INFERENCE_SEASON, last_complete_season=LAST_COMPLETE_SEASON,
        scope=SCOPE, source=source, git_head=_git("rev-parse", "HEAD"),
        features_by_position=features_by_position,
        population=f"every row of the {INFERENCE_SEASON} feature partition of the training file "
                   f"(players with >= 4 stat-row games in {INFERENCE_SEASON}, rostered or not)",
    )
    provenance = collect_provenance(files, extra={
        "git_head": _git("rev-parse", "HEAD"), "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "worktree": json.loads((ROOT / ".dg-worktree.json").read_text()) if (ROOT / ".dg-worktree.json").exists() else None,
        "source": source, "finished_utc": datetime.now(timezone.utc).isoformat(),
    })
    results = {
        "run_id": run_id, "started_utc": started.isoformat(), "manifest": manifest,
        "alignment_check": alignment, "historical": historical, "final_fits": fits,
        "final_forecast_coverage": coverage,
        "config": {"draws": args.draws, "seed": args.seed, "min_train_rows": args.min_train_rows,
                   "test_seasons_by_horizon": TEST_SEASONS_BY_HORIZON, "arms": [ARM_CANDIDATE, ARM_COMPARATOR]},
    }
    historical_predictions = pd.concat(prediction_frames, ignore_index=True)
    report = render_report(results)
    written = write_run_artifact(out_dir, results, historical_predictions, provenance=provenance, report_md=report)
    (out_dir / "annual_forecasts.csv").write_text(forecasts.to_csv(index=False))
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out_dir / "weekly_stats_snapshot.csv.gz").write_bytes(snapshot_bytes)
    (out_dir / "predictions.csv").rename(out_dir / "historical_predictions.csv")
    print(f"wrote {written + ['annual_forecasts.csv', 'manifest.json', 'weekly_stats_snapshot.csv.gz']} to {out_dir}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
