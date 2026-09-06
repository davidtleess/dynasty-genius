"""DG-165 runner — build, evaluate and score the draft-capital rookie candidate.

    .venv/bin/python scripts/dg165/run_rookie_capital.py [--panel PATH] [--forecast-year 2026]

Writes ONE immutable run directory under ``runs/<UTC>/dg165_rookie_capital/`` and nothing
else. Reads nflverse (network, immutable upstream) and, optionally, a saved panel parquet.
Never touches ``app/data``, never restarts anything, never publishes.

Outputs (all inside the run directory):
    manifest.json                 what was run, on what, with input hashes and definitions
    evaluation.json / EVALUATION.md   walk-forward results with information cutoffs
    out_of_time_predictions.csv   every graded forecast row, for re-slicing
    rookie_scores_<T>.csv / ROOKIES_<T>.md   the scored class, one row per drafted rookie
    training_descriptives.json    in-sample rates by round and position (descriptive only)
    inputs/                       copies of the inputs (gitignored; hashes are in the manifest)
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
)
from src.dynasty_genius.rookie.evaluate import (  # noqa: E402
    evaluate_walk_forward,
    walk_forward_splits,
)
from src.dynasty_genius.rookie.labels import (  # noqa: E402
    AVAILABILITY_BAR,
    horizon_labels,
    played_season_keys,
    qualifying_season_keys,
    season_ppg_map,
)
from src.dynasty_genius.rookie.model import (  # noqa: E402
    MODEL_VERSION,
    RookieCapitalModel,
)
from src.dynasty_genius.rookie.panel import build_panel, load_panel  # noqa: E402
from src.dynasty_genius.rookie.report import (  # noqa: E402
    render_evaluation_markdown,
    render_scores_markdown,
)
from src.dynasty_genius.rookie.run_dir import create_run_dir  # noqa: E402
from src.dynasty_genius.rookie.score import (  # noqa: E402
    bootstrap_intervals,
    score_class,
)

DG176_NAMES = ("Fernando Mendoza", "Ty Simpson", "Kenyon Sadiq")


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
    p.add_argument("--eval-start", type=int, default=2005, help="first forecast year in the walk-forward")
    p.add_argument("--horizons", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6],
                   help="six by default: the DG-164 cells give R1..R5 on top of the current season, so the "
                        "veteran board sums six seasons; both five- and six-season assemblies stay possible")
    p.add_argument("--bar", default="availability", choices=["availability"],
                   help="qualification bar; only the availability bar is wired (DG-171 variant is a parameter away)")
    p.add_argument("--bootstrap", type=int, default=200, help="refits for score intervals")
    p.add_argument("--eval-boot", type=int, default=1000, help="resamples for pooled metric intervals")
    p.add_argument("--runs-root", type=Path, default=REPO / "runs")
    p.add_argument("--prospects-csv", type=Path, default=None,
                   help="optional prospects_with_outcomes_v3.csv to cross-check age at draft against nflverse")
    return p.parse_args(argv)


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
        raise SystemExit(
            f"panel covers {panel['season'].min()}-{panel['season'].max()}, "
            f"need {args.first_class}-{last_completed}; refusing to label against a short panel"
        )
    print(f"panel: {len(panel)} player-seasons {panel['season'].min()}-{panel['season'].max()} ({panel_source})")

    # ---------------------------------------------------------------- events
    qualifying = qualifying_season_keys(panel, bar)
    played = played_season_keys(panel)
    season_ppg = season_ppg_map(panel)
    cohort, coverage = draft_cohort_from_picks(picks, seasons=range(args.first_class, T + 1))
    leaking = find_leaking_columns(cohort)
    if leaking:
        raise SystemExit(f"cohort frame carries market-derived columns: {leaking}")
    print(f"cohort: {coverage}")

    # ---------------------------------------------------------------- evaluation
    forecast_years = range(args.eval_start, T)
    splits = walk_forward_splits(
        cohort, qualifying=qualifying, played=played, horizons=horizons,
        forecast_years=forecast_years, last_completed_season_today=last_completed, season_ppg=season_ppg,
    )
    present = {(s.forecast_year, s.horizon) for s in splits}
    absent = []
    for t in forecast_years:
        for h in horizons:
            if (t, h) in present:
                continue
            if t + h - 1 > last_completed:
                absent.append({"forecast_year": t, "horizon": h,
                               "reason": f"window {t}-{t + h - 1} not complete by {last_completed}; cannot be graded yet"})
            else:
                absent.append({"forecast_year": t, "horizon": h,
                               "reason": "training set below the minimum size at this cutoff"})
    print(f"walk-forward: {len(splits)} (T,h) splits, {len(absent)} absent")
    evaluation, predictions = evaluate_walk_forward(splits, n_boot=args.eval_boot)
    evaluation["absent_pairs"] = absent
    evaluation["forecast_years_requested"] = [int(forecast_years.start), int(forecast_years.stop - 1)]
    (run_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=1, default=_json_default))
    (run_dir / "EVALUATION.md").write_text(render_evaluation_markdown(evaluation))
    predictions.to_csv(run_dir / "out_of_time_predictions.csv", index=False)
    for h, e in sorted(evaluation["pooled_by_horizon"].items()):
        q = e["qual"]
        print(f"  h={h}: n={e['n']} AUC={q['auc']:.3f} CI{tuple(round(x, 3) for x in e['qual_auc_ci90'])} "
              f"Brier {q['brier']:.4f} vs base {q['brier_base_rate']:.4f} | E[N] RMSE {e['seasons']['rmse']:.3f} vs {e['seasons']['rmse_base_rate']:.3f}")
    for j, e in sorted(evaluation["level_by_year"].items()):
        print(f"  level season {j}: n={e['n']} qualifiers, mean actual {e['mean_actual']:.2f} vs predicted {e['mean_predicted']:.2f} ppg, "
              f"RMSE {e['rmse']:.2f} vs position-mean {e['rmse_position_mean']:.2f}")

    # ---------------------------------------------------------------- final fit and scores
    train = horizon_labels(cohort.loc[cohort["draft_season"] < T], qualifying=qualifying, played=played,
                           horizons=horizons, last_completed_season=last_completed, season_ppg=season_ppg)
    model = RookieCapitalModel(horizons=horizons).fit(train)
    rookies = cohort.loc[cohort["draft_season"] == T].reset_index(drop=True)
    if rookies.empty:
        raise SystemExit(f"no {T} draft class in the nflverse pick table; nothing to score")
    scores = score_class(model, rookies)
    intervals = bootstrap_intervals(train, rookies, horizons=horizons, n_boot=args.bootstrap)
    scores = scores.merge(intervals, on="gsis_id", how="left")
    assert len(scores) == len(rookies), "rows lost in the interval merge"
    scores = scores.sort_values("pick").reset_index(drop=True)
    scores.to_csv(run_dir / f"rookie_scores_{T}.csv", index=False)
    (run_dir / f"ROOKIES_{T}.md").write_text(render_scores_markdown(scores, horizons, T))
    print(f"scored {len(scores)} rookies of class {T}; coverage: {scores['coverage_status'].value_counts().to_dict()}")

    dg176 = {name: bool((scores["name"] == name).any()) for name in DG176_NAMES}
    print(f"DG-176 names present with a row: {dg176}")

    # ---------------------------------------------------------------- descriptives (in-sample, labelled as such)
    descriptives = {"note": "IN-SAMPLE rates on the final training set; descriptive, not validated probabilities",
                    "by_round": {}, "by_position": {}}
    for h in horizons:
        obs = train.loc[train[f"q_{h}"].notna()]
        descriptives["by_round"][h] = {int(r): {"n": int(len(g)), "qual_rate": float(g[f"q_{h}"].mean()),
                                               "mean_qual_seasons": float(g[f"n_{h}"].mean())}
                                       for r, g in obs.groupby("round")}
        descriptives["by_position"][h] = {p: {"n": int(len(g)), "qual_rate": float(g[f"q_{h}"].mean()),
                                              "mean_qual_seasons": float(g[f"n_{h}"].mean())}
                                          for p, g in obs.groupby("position")}
    # The level's transparent comparator: mean rate of the qualifiers in the final training
    # set by position and NFL season j. Out of time the fitted level beats this by only a
    # few percent of RMSE (see evaluation.json), so a consumer can see what the fit adds.
    descriptives["level_qualifier_mean_ppg_by_position_and_season"] = {
        j: {p: {"n": int(len(g)), "mean_ppg": float(g[f"ppg_year_{j}"].mean()),
                "sd_ppg": float(g[f"ppg_year_{j}"].std(ddof=1)) if len(g) > 1 else None}
            for p, g in train.loc[train[f"qy_{j}"] == 1].groupby("position")}
        for j in range(1, max(horizons) + 1)
    }
    (run_dir / "training_descriptives.json").write_text(json.dumps(descriptives, indent=1))

    # ---------------------------------------------------------------- optional age cross-check
    age_check = None
    if args.prospects_csv:
        csv = pd.read_csv(args.prospects_csv, low_memory=False, usecols=["gsis_id", "age_at_draft", "season"])
        merged = cohort.merge(csv, on="gsis_id", suffixes=("", "_csv"))
        diff = (merged["age_at_draft"] - merged["age_at_draft_csv"]).abs()
        age_check = {"overlap_rows": int(len(merged)), "both_present": int(diff.notna().sum()),
                     "agree_within_0.5": int((diff <= 0.5).sum()), "max_abs_diff": float(diff.max()) if diff.notna().any() else None,
                     "source": str(args.prospects_csv), "sha256": sha256(args.prospects_csv)}
        print(f"age cross-check vs prospects CSV: {age_check}")

    # ---------------------------------------------------------------- manifest
    manifest = {
        "ticket": "DG-165",
        "model_version": MODEL_VERSION,
        "status": "RESEARCH CANDIDATE — not served, not promoted, not merged",
        "run_dir": str(run_dir.relative_to(REPO)),
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "forecast_date": {"forecast_year": T, "season_clock": f"pre-season {T}, after the NFL draft; rookie season = NFL season 1 = {T}",
                          "last_completed_season": last_completed},
        "cohort": {"source": "nflreadpy.load_draft_picks()", "classes": [args.first_class, T],
                   "positions": ["QB", "RB", "WR", "TE"], "coverage": coverage,
                   "no_gsis_rule": "a pick without a gsis_id and with zero PFR career games is KEPT under a synthetic id and labels 0 "
                                   "(107 of 108 such picks 1999-2025 never played; dropping them deletes washouts); "
                                   "a no-id pick who played is unlabelable and dropped, counted above",
                   "played_but_absent_from_panel": "picks with PFR career games > 0 who never appear in the skill-position weekly "
                                                   "stats (fullbacks, long snappers, position changes; 66 of 1,932 in 1999-2025, none "
                                                   "found under another id by name) are labelled not-played and not-qualified, which "
                                                   "is correct for the fantasy question and slightly understates P(played)",
                   "undrafted": "NOT in the cohort and NOT modelled — no undrafted-prospect population table exists in the product; see REPORT"},
        "labels": {
            "qualifying_season": f"finished at or above the bar rank for the position by regular-season PPR total; bar = {bar}; "
                                 "tie-robust N-th largest (same as the canonical DG-164 cells, preserved publish_v3.py)",
            "played_season": "at least one weekly stat row in nflverse regular-season player stats",
            "horizons": list(horizons),
            "window": "NFL seasons c .. c+h-1 for draft class c; label is NaN when c+h-1 > last completed season at the cutoff",
            "cutoff_rule": "at forecast year T, training uses last_completed_season = T-1; class c contributes at horizon h only if c <= T-h",
            "events_are_distinct": "P(played_h), P(Q_h) and E[N_h] are separate estimands; nothing here multiplies them. "
                                   "Engine A's rate is conditional on >= 8 career games (build_head_b_targets.py:84) and composes with P(played), never with P(Q).",
            "level": "e_ppg_given_qual_year{j} = E[ppg in season j | qualifies in season j], fitted ONLY on qualifying player-seasons; "
                     "ppg = REG-season PPR points / games with a weekly stat row. This denominator is NOT the served all-games ppg "
                     "(DG-024) and the replacement rates the assembler subtracts are on the served denominator; reconcile, do not absorb. "
                     "Multiplying p_qual_year{j} x e_ppg_given_qual_year{j} is the CONSUMER's act (DG-178), never done here.",
        },
        # Flat blocks for the DG-178 reader adapter (davidleess-cb, 2026-09-06): it takes the
        # qualifying definition from `definitions` and the ppg denominator from a key
        # containing "denominator" under `units`, and rides both on every rookie term.
        "definitions": {
            "qualifying_season": f"finished at or above the bar rank for the position by regular-season PPR total; "
                                 f"bar = {bar}; tie-robust N-th largest (canonical DG-164 cells)",
            "played_season": "at least one weekly stat row in nflverse regular-season player stats",
            "level": "e_ppg_given_qual_year{j} = E[ppg in NFL season j | qualifies in season j]; fitted only on qualifying player-seasons",
        },
        "units": {
            "ppg_denominator": "REG-season PPR points / games with a weekly nflverse stat row — NOT the served all-games "
                               "denominator (DG-024); the served replacement rates use the served denominator; reconcile, do not absorb",
            "seasons": "NFL season j = 1 is the rookie season = forecast_year; E[N_h] counts qualifying seasons in 1..h",
        },
        "model": model.describe(),
        "evaluation": {"forecast_years": [int(forecast_years.start), int(forecast_years.stop - 1)],
                       "splits": len(splits), "absent_pairs": len(absent), "n_boot": args.eval_boot},
        "score_intervals": {"method": "refit on player-resampled training sets, 5th/95th percentile",
                            "n_boot_requested": args.bootstrap, "n_boot_effective": intervals.attrs.get("n_boot_effective")},
        "dg176_names_present": dg176,
        "inputs": {
            "nflverse_draft_picks": {"path": str(picks_path.relative_to(run_dir)), "sha256": sha256(picks_path), "rows": int(len(picks))},
            "panel": {"path": str(panel_path.relative_to(run_dir)), "sha256": sha256(panel_path), "rows": int(len(panel)),
                      "seasons": [int(panel["season"].min()), int(panel["season"].max())], "source": panel_source},
            "age_cross_check": age_check,
        },
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                        "sklearn": __import__("sklearn").__version__, "nflreadpy": __import__("nflreadpy").__version__},
        "outputs": sorted(p.name for p in run_dir.iterdir() if p.is_file()),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=_json_default))
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
