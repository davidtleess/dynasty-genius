"""DG-165 runner — build, evaluate and score the draft-capital rookie candidate.

    .venv/bin/python scripts/dg165/run_rookie_capital.py [--panel PATH] [--forecast-year 2026]

Writes ONE immutable run directory under ``runs/<UTC>/dg165_rookie_capital/`` and nothing
else. Reads nflverse (network, immutable upstream) and, optionally, a saved panel parquet.
Never touches ``app/data``, never restarts anything, never publishes.

Outputs (all inside the run directory):
    manifest.json                  what was run, on what, with input hashes and definitions
    evaluation.json / EVALUATION.md    historical evaluation, one fit per forecast year
    evaluation_sensitivity_unresolved_as_zero.json   the same with unknown identities forced to zero
    out_of_time_predictions.csv    every graded forecast row with labels and training baselines
    rookie_scores_<T>.csv / ROOKIES_<T>.md   the scored class, one row per drafted rookie
    training_descriptives.json     in-sample rates by round and position (descriptive only)
    REPORT.md                      the numeric record rendered from the JSON; NOTES.md is prose
    inputs/                        copies of the inputs (gitignored; hashes are in the manifest)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.dynasty_genius.models.leakage import find_leaking_columns  # noqa: E402
from src.dynasty_genius.rookie.cohort import (  # noqa: E402
    draft_cohort_from_picks,
    load_draft_picks,
    load_players,
    load_rosters,
)
from src.dynasty_genius.rookie.evaluate import (  # noqa: E402
    evaluate_forecast_years,
    fit_at_forecast_year,
    training_frame_at,
    trend_experiment,
)
from src.dynasty_genius.rookie.labels import (  # noqa: E402
    AVAILABILITY_BAR,
    qualifying_season_keys,
    season_stats_map,
)
from src.dynasty_genius.rookie.model import MODEL_VERSION  # noqa: E402
from src.dynasty_genius.rookie.panel import build_panel, load_panel  # noqa: E402
from src.dynasty_genius.rookie.report import (  # noqa: E402
    render_evaluation_markdown,
    render_report_markdown,
    render_scores_markdown,
)
from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402
from src.dynasty_genius.rookie.score import (  # noqa: E402
    bootstrap_intervals,
    score_class,
)

DG176_NAMES = ("Fernando Mendoza", "Ty Simpson", "Kenyon Sadiq")
HEADLINE_QUANTITIES = (("annual", 1, "p_qual_year", "auc"), ("annual", 1, "p_qual_year", "brier"),
                       ("annual", 3, "p_qual_year", "auc"), ("annual", 1, "e_points_year", "rmse"),
                       ("annual", 3, "e_points_year", "rmse"), ("horizon", 5, "p_qual_h", "auc"),
                       ("horizon", 5, "e_qual_seasons_h", "rmse"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception as exc:  # pragma: no cover
        return f"unavailable: {exc}"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--panel", type=Path, help="saved player-season panel parquet; if omitted, built from nflverse")
    p.add_argument("--forecast-year", type=int, default=2026)
    p.add_argument("--last-completed-season", type=int, default=None, help="default forecast_year - 1")
    p.add_argument("--first-class", type=int, default=1999)
    p.add_argument("--eval-start", type=int, default=2005, help="first forecast year in the historical evaluation")
    p.add_argument("--horizons", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6])
    p.add_argument("--bootstrap", type=int, default=200, help="refits for score intervals")
    p.add_argument("--eval-boot", type=int, default=1000, help="resamples for pooled metric intervals")
    p.add_argument("--runs-root", type=Path, default=REPO / "runs")
    p.add_argument("--prospects-csv", type=Path, default=None, help="optional prospects CSV to cross-check age at draft")
    p.add_argument("--no-trend-experiment", action="store_true", help="skip the bounded class-year trend experiment")
    return p.parse_args(argv)


def _headline(evaluation: dict) -> dict[str, float]:
    out = {}
    for block, key, quantity, metric in HEADLINE_QUANTITIES:
        entry = evaluation.get(block, {}).get(key, {}).get(quantity, {})
        out[f"{block}[{key}].{quantity}.{metric}"] = entry.get(metric, float("nan"))
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    T = args.forecast_year
    last_completed = args.last_completed_season if args.last_completed_season is not None else T - 1
    horizons = tuple(sorted(set(args.horizons)))
    bar = dict(AVAILABILITY_BAR)
    started = datetime.now(timezone.utc)

    run_dir = create_run_dir(args.runs_root, name="dg165_rookie_capital")
    inputs = run_dir / "inputs"
    inputs.mkdir()
    (run_dir / ".gitignore").write_text("inputs/\n")
    print(f"run dir: {run_dir}")

    # ---------------------------------------------------------------- inputs
    picks = load_draft_picks()
    picks_path = inputs / "nflverse_draft_picks.parquet"
    picks.to_parquet(picks_path)
    players = load_players()
    players_path = inputs / "nflverse_players.parquet"
    players.to_parquet(players_path)
    rosters = load_rosters(range(args.first_class, last_completed + 1))
    rosters_path = inputs / "nflverse_rosters.parquet"
    rosters.to_parquet(rosters_path)
    if args.panel:
        panel_path = inputs / "panel.parquet"
        shutil.copy2(args.panel, panel_path)
        panel = load_panel(panel_path)
        panel_source = f"copied from {args.panel}"
    else:
        panel = build_panel(range(args.first_class, last_completed + 1))
        panel_path = inputs / "panel.parquet"
        panel.to_parquet(panel_path)
        panel_source = "built from nflreadpy.load_player_stats (REG, PPR)"
    if int(panel["season"].max()) < last_completed or int(panel["season"].min()) > args.first_class:
        raise SystemExit(f"panel covers {panel['season'].min()}-{panel['season'].max()}, need {args.first_class}-{last_completed}")
    print(f"panel: {len(panel)} player-seasons {panel['season'].min()}-{panel['season'].max()} ({panel_source})")

    # ---------------------------------------------------------------- events and cohort
    qualifying = qualifying_season_keys(panel, bar)
    season_stats = season_stats_map(panel)
    cohort, coverage = draft_cohort_from_picks(picks, seasons=range(args.first_class, T + 1), players=players, rosters=rosters)
    leaking = find_leaking_columns(cohort)
    if leaking:
        raise SystemExit(f"cohort frame carries market-derived columns: {leaking}")
    print(f"cohort: {coverage}")
    cohort.to_csv(run_dir / "cohort.csv", index=False)

    # ---------------------------------------------------------------- historical evaluation: the trend
    # experiment runs BOTH arms with the one procedure; the arm the pre-stated rule picks is
    # the arm that scores, and ITS evaluation and predictions are the canonical files. The
    # other arm is written beside them, never mixed in. (A run once wrote the plain arm's
    # evaluation next to a trend-scored class file; a consumer graded the wrong arm.)
    forecast_years = range(args.eval_start, T)
    common = dict(qualifying=qualifying, season_stats=season_stats, horizons=horizons,
                  forecast_years=forecast_years, last_completed_season_today=last_completed, n_boot=args.eval_boot)
    trend_result = None
    trend_for_scoring: bool | str = False
    if args.no_trend_experiment:
        evaluation, predictions = evaluate_forecast_years(cohort, **common)
    else:
        trend_result = trend_experiment(cohort, **common)
        trend_for_scoring = "auto" if trend_result["decision"] == "auto_trend" else False
        chosen = trend_result["decision"]
        other = "plain" if chosen == "auto_trend" else "auto_trend"
        evaluation, predictions = trend_result["arms"][chosen], trend_result["predictions"][chosen]
        (run_dir / f"evaluation_other_arm_{other}.json").write_text(
            json.dumps(trend_result["arms"][other], indent=1, default=_json_default))
        trend_result["predictions"][other].to_csv(run_dir / f"out_of_time_predictions_{other}.csv", index=False)
        slim = {k: v for k, v in trend_result.items() if k not in ("arms", "predictions")}
        slim["arms_written_as"] = {chosen: "evaluation.json (canonical: the arm that scores)",
                                   other: f"evaluation_other_arm_{other}.json"}
        (run_dir / "trend_experiment.json").write_text(json.dumps(slim, indent=1, default=_json_default))
        print(f"trend experiment: decision={chosen} wins={trend_result['auto_trend_wins']}/{trend_result['metrics_compared']} "
              f"auto selected trend in {trend_result['auto_selected_trend_in_forecast_years']}/{trend_result['forecast_years_evaluated']} forecast years")
        trend_result = slim
    (run_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=1, default=_json_default))
    (run_dir / "EVALUATION.md").write_text(render_evaluation_markdown(evaluation))
    predictions.to_csv(run_dir / "out_of_time_predictions.csv", index=False)
    for name, value in _headline(evaluation).items():
        print(f"  {name} = {value:.4f}")
    sensitivity_eval, _ = evaluate_forecast_years(cohort, unresolved_as_zero=True, trend=trend_for_scoring, **{**common, "n_boot": 0})
    (run_dir / "evaluation_sensitivity_unresolved_as_zero.json").write_text(json.dumps(sensitivity_eval, indent=1, default=_json_default))
    deltas = []
    for name, value in _headline(evaluation).items():
        arm = _headline(sensitivity_eval)[name]
        deltas.append({"quantity": name, "default": value, "arm": arm, "delta": arm - value})

    # ---------------------------------------------------------------- final fit and scores (THE procedure)
    fit_kwargs = dict(qualifying=qualifying, season_stats=season_stats, horizons=horizons, forecast_year=T)
    model = fit_at_forecast_year(cohort, trend=trend_for_scoring, **fit_kwargs)
    train = training_frame_at(cohort, **fit_kwargs)
    rookies = cohort.loc[cohort["draft_season"] == T].reset_index(drop=True)
    if rookies.empty:
        raise SystemExit(f"no {T} draft class in the nflverse pick table; nothing to score")
    scores = score_class(model, rookies)
    intervals = bootstrap_intervals(train, rookies, horizons=horizons, n_boot=args.bootstrap, trend=bool(model.trend))
    scores = scores.merge(intervals, on="gsis_id", how="left")
    assert len(scores) == len(rookies), "rows lost in the interval merge"
    scores = scores.sort_values("pick").reset_index(drop=True)
    scores.to_csv(run_dir / f"rookie_scores_{T}.csv", index=False)
    (run_dir / f"ROOKIES_{T}.md").write_text(render_scores_markdown(scores, horizons, T))
    print(f"scored {len(scores)} rookies of class {T}; identity: {scores['identity_status'].value_counts().to_dict()}; "
          f"coverage: {scores['coverage_status'].value_counts().to_dict()}")
    arm_model = fit_at_forecast_year(cohort, unresolved_as_zero=True, trend=trend_for_scoring, **fit_kwargs)
    arm_scores = score_class(arm_model, rookies)
    base_scores = scores.set_index("gsis_id")
    score_deltas = []
    for col in [c for c in arm_scores.columns if c.startswith(("p_", "e_"))]:
        diff = (arm_scores[col].to_numpy() - base_scores.loc[arm_scores["gsis_id"], col].to_numpy())
        diff = np.abs(diff)
        i = int(np.nanargmax(diff)) if np.isfinite(diff).any() else 0
        score_deltas.append({"column": col, "max_abs_delta": float(np.nanmax(diff)), "player": str(arm_scores["name"].iloc[i])})
    sensitivity = {"evaluation_deltas": deltas, "score_deltas": sorted(score_deltas, key=lambda r: -r["max_abs_delta"])[:12]}
    (run_dir / "sensitivity_unresolved_as_zero.json").write_text(json.dumps(sensitivity, indent=1, default=_json_default))
    dg176 = {name: bool((scores["name"] == name).any()) for name in DG176_NAMES}
    print(f"DG-176 names present with a row: {dg176}")

    # ---------------------------------------------------------------- descriptives (in-sample, labelled as such)
    descriptives = {"note": "IN-SAMPLE rates on the final training set; descriptive, not validated probabilities",
                    "by_round": {}, "by_position": {}, "appearer_mean_points_by_position_and_season": {},
                    "qualifier_mean_ppg_by_position_and_season": {}}
    for h in horizons:
        obs = train.loc[train[f"q_{h}"].notna()]
        descriptives["by_round"][h] = {int(r): {"n": int(len(g)), "qual_rate": float(g[f"q_{h}"].mean()), "mean_qual_seasons": float(g[f"n_{h}"].mean())}
                                       for r, g in obs.groupby("round")}
        descriptives["by_position"][h] = {p: {"n": int(len(g)), "qual_rate": float(g[f"q_{h}"].mean()), "mean_qual_seasons": float(g[f"n_{h}"].mean())}
                                          for p, g in obs.groupby("position")}
    for j in range(1, max(horizons) + 1):
        descriptives["appearer_mean_points_by_position_and_season"][j] = {
            p: {"n": int(len(g)), "mean_points": float(g[f"points_{j}"].mean()), "mean_games": float(g[f"games_{j}"].mean())}
            for p, g in train.loc[train[f"appear_{j}"] == 1].groupby("position")}
        descriptives["qualifier_mean_ppg_by_position_and_season"][j] = {
            p: {"n": int(len(g)), "mean_ppg": float(g[f"ppg_{j}"].mean())}
            for p, g in train.loc[train[f"qy_{j}"] == 1].groupby("position")}
    (run_dir / "training_descriptives.json").write_text(json.dumps(descriptives, indent=1, default=_json_default))

    # ---------------------------------------------------------------- optional age cross-check
    age_check = None
    if args.prospects_csv:
        csv = pd.read_csv(args.prospects_csv, low_memory=False, usecols=["gsis_id", "age_at_draft", "season"])
        merged = cohort.merge(csv, on="gsis_id", suffixes=("", "_csv"))
        diff = (merged["age_at_draft"] - merged["age_at_draft_csv"]).abs()
        age_check = {"overlap_rows": int(len(merged)), "both_present": int(diff.notna().sum()),
                     "agree_within_0.5": int((diff <= 0.5).sum()), "max_abs_diff": float(diff.max()) if diff.notna().any() else None,
                     "source": str(args.prospects_csv), "sha256": sha256(args.prospects_csv)}

    # ---------------------------------------------------------------- manifest
    manifest = {
        "ticket": "DG-165",
        "model_version": MODEL_VERSION,
        "status": "RESEARCH CANDIDATE — not served, not promoted, not merged",
        "run_dir": str(run_dir.relative_to(REPO)),
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "forecast_date": {
            "forecast_year": T,
            "forecast_cutoff": f"{T}-09-01 (pre-season {T}, after the NFL draft)",
            "label_window": f"labels through NFL season {last_completed}; NFL season j = 1 is the rookie season = {T}",
            "last_completed_season": last_completed,
        },
        "definitions": {
            "qualifying_season": f"finished at or above the bar rank for the position by regular-season PPR total; bar = {bar}; "
                                 "tie-robust N-th largest (canonical DG-164 cells)",
            "appearance": "at least one weekly stat row in nflverse regular-season player stats (not 'dressed', not 'took a snap'); "
                          "a player without a stat row scored zero fantasy points that season",
            "season_points": "regular-season PPR points (nflverse weekly fantasy_points_ppr), exactly 0 without an appearance",
            "games": "weeks with a weekly stat row, exactly 0 without an appearance",
            "identity_unresolved": "no gsis_id in nflverse draft picks and no match in the players table or 1999-%d rosters by draft key or name+year; "
                                   "labels NaN, never zero, except in the named sensitivity arm" % last_completed,
        },
        "units": {
            "scoring_scope": "regular season only; PPR as in nflverse weekly player stats",
            "exposure_definition": "stat-row games (weeks with a weekly stat row)",
            "ppg_denominator": "REG-season PPR points / stat-row games — NOT the served all-games denominator (DG-024); reconcile, do not absorb",
            "seasons": "NFL season j = 1 is the rookie season = forecast_year; E[N_h] counts qualifying seasons in 1..h",
        },
        "construction": "see model.construction; cumulative events are nested by hazard arithmetic; E[points_j] = P(A_j) x E[points_j | A_j] "
                        "is the only product formed, valid because points are exactly zero without an appearance",
        "no_composition_claims": "nothing here states how these quantities compose with Engine A, Engine B or the DG-164 cells; "
                                 "that comparability is the ranking lane's typed contract (DG-178)",
        "cohort": {"source": "nflreadpy.load_draft_picks(); identities resolved via load_players() and load_rosters(1999-%d)" % last_completed,
                   "classes": [args.first_class, T], "positions": ["QB", "RB", "WR", "TE"], "coverage": coverage,
                   "undrafted": "NOT in the cohort and NOT modelled — no undrafted-prospect population table exists in the product"},
        "model": model.describe(),
        "evaluation": {"forecast_years": [int(forecast_years.start), int(forecast_years.stop - 1)], "n_boot": args.eval_boot,
                       "headline": _headline(evaluation), "sensitivity_unresolved_as_zero": deltas},
        "trend_experiment": None if trend_result is None else {
            "decision": trend_result["decision"], "rule": trend_result["rule"],
            "auto_trend_wins": trend_result["auto_trend_wins"], "metrics_compared": trend_result["metrics_compared"],
            "auto_selected_trend_in_forecast_years": trend_result["auto_selected_trend_in_forecast_years"],
            "forecast_years_evaluated": trend_result["forecast_years_evaluated"],
            "comparison": trend_result["comparison"],
            "final_scoring_uses": "auto-selected class-year trend" if trend_for_scoring == "auto" else "plain model (no trend term)",
            "canonical_evaluation_is": "the arm that scores; evaluation.json and out_of_time_predictions.csv describe the same model as rookie_scores",
        },
        "score_intervals": {"method": "refit on player-resampled training sets, 5th/95th percentile; fit uncertainty conditional on this model form",
                            "n_boot_requested": args.bootstrap, "n_boot_effective": intervals.attrs.get("n_boot_effective")},
        "dg176_names_present": dg176,
        "inputs": {
            "nflverse_draft_picks": {"path": str(picks_path.relative_to(run_dir)), "sha256": sha256(picks_path), "rows": int(len(picks))},
            "nflverse_players": {"path": str(players_path.relative_to(run_dir)), "sha256": sha256(players_path), "rows": int(len(players))},
            "nflverse_rosters": {"path": str(rosters_path.relative_to(run_dir)), "sha256": sha256(rosters_path), "rows": int(len(rosters))},
            "panel": {"path": str(panel_path.relative_to(run_dir)), "sha256": sha256(panel_path), "rows": int(len(panel)),
                      "seasons": [int(panel["season"].min()), int(panel["season"].max())], "source": panel_source},
            "age_cross_check": age_check,
        },
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                        "sklearn": __import__("sklearn").__version__, "nflreadpy": __import__("nflreadpy").__version__},
    }
    manifest["outputs"] = sorted(p.name for p in run_dir.iterdir() if p.is_file()) + ["manifest.json", "REPORT.md"]
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=_json_default))
    (run_dir / "REPORT.md").write_text(render_report_markdown(manifest, evaluation, sensitivity, scores, trend_result))
    print(f"manifest written: {run_dir / 'manifest.json'}")
    return 0


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not serialisable: {type(o)}")


if __name__ == "__main__":
    raise SystemExit(main())
