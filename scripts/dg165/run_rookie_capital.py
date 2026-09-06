"""DG-165 runner — build, evaluate and score the draft-capital rookie candidate.

    .venv/bin/python scripts/dg165/run_rookie_capital.py [--panel PATH] [--forecast-year 2026] [--policy inner_menu]

Writes ONE immutable run directory under ``runs/<UTC>/dg165_rookie_capital/`` and nothing
else. Reads nflverse (network, immutable upstream) and, optionally, a saved panel parquet.
Never touches ``app/data``, never restarts anything, never publishes.

The model POLICY is declared here, before anything is evaluated, and the canonical
evaluation is that policy's outer evaluation. Exploratory alternatives are written beside
it and compared by a paired bootstrap; nothing chooses among arms on the outer years.

Outputs (all inside the run directory):
    manifest.json                  what was run, on what, with input/output hashes, identifiers, pairing block
    evaluation.json / EVALUATION.md    the declared policy's historical evaluation (policy_id, arm_ids)
    evaluation_exploratory_<arm>.json / out_of_time_predictions_<arm>.csv   the exploratory arms
    policy_comparison.json         paired-bootstrap differences, evidence status per arm
    calibration_assessment.json / CALIBRATION.md   the bounded QB / first-round assessment
    evaluation_sensitivity_unresolved_as_zero.json   the policy with unknown identities forced to zero
    out_of_time_predictions.csv    every graded forecast row with labels and training baselines
    rookie_scores_<T>.csv / ROOKIES_<T>.md   the scored class, one row per drafted rookie, with identifiers
    training_descriptives.json     in-sample rates by round and position (descriptive only)
    REPORT.md                      the numeric record rendered from the JSON; NOTES.md is prose
    inputs/                        copies of the inputs (gitignored; hashes are in the manifest)
"""
from __future__ import annotations

import argparse
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
from src.dynasty_genius.rookie.calibration import (  # noqa: E402
    calibration_assessment,
    render_assessment_markdown,
)
from src.dynasty_genius.rookie.cohort import (  # noqa: E402
    draft_cohort_from_picks,
    load_draft_picks,
    load_players,
    load_rosters,
)
from src.dynasty_genius.rookie.evaluate import (  # noqa: E402
    POLICIES,
    evaluate_forecast_years,
    fit_at_forecast_year,
    policy_experiment,
    training_frame_at,
)
from src.dynasty_genius.rookie.identifiers import (  # noqa: E402
    sha256_file,
    verify_pairing,
)
from src.dynasty_genius.rookie.labels import (  # noqa: E402
    AVAILABILITY_BAR,
    qualifying_season_keys,
    season_stats_map,
)
from src.dynasty_genius.rookie.model import MODEL_VERSION  # noqa: E402
from src.dynasty_genius.rookie.outcomes import (  # noqa: E402
    outcome_inputs,
    weekly_positions_by_player_season,
)
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
    p.add_argument("--policy", default="inner_menu", choices=list(POLICIES),
                   help="the DECLARED model policy; 'inner_menu' selects a variant inside each training window")
    p.add_argument("--exploratory", nargs="*", default=["plain"], help="alternative arms evaluated beside the policy, never chosen on outer years")
    p.add_argument("--bootstrap", type=int, default=200, help="refits for score intervals")
    p.add_argument("--eval-boot", type=int, default=1000, help="resamples for pooled metric intervals and paired comparisons")
    p.add_argument("--runs-root", type=Path, default=REPO / "runs")
    p.add_argument("--prospects-csv", type=Path, default=None, help="optional prospects CSV to cross-check age at draft")
    p.add_argument("--outcomes-csv", type=Path, default=None,
                   help="Codex's common player-season outcome artifact (DG-179); when given, labels come from it, not from --panel")
    p.add_argument("--outcomes-manifest", type=Path, default=None)
    p.add_argument("--weekly-capture", type=Path, default=None,
                   help="a weekly_source_capture run directory; its raw files supply the weekly position per player-season")
    return p.parse_args(argv)


def _weekly_positions_from_capture(capture_dir: Path) -> dict:
    frames = []
    for path in sorted((capture_dir / "raw").glob("stats_player_week_*.parquet")):
        frames.append(pd.read_parquet(path, columns=["player_id", "season", "week", "season_type", "position"]))
    if not frames:
        raise SystemExit(f"no raw weekly files under {capture_dir / 'raw'}")
    return weekly_positions_by_player_season(pd.concat(frames, ignore_index=True))


def _headline(evaluation: dict) -> dict[str, float]:
    out = {}
    for block, key, quantity, metric in HEADLINE_QUANTITIES:
        entry = evaluation.get(block, {}).get(key, {}).get(quantity, {})
        out[f"{block}[{key}].{quantity}.{metric}"] = entry.get(metric, float("nan"))
    return out


def _coherence(frame: pd.DataFrame, horizons: tuple[int, ...]) -> dict:
    """Count the bound violations the round-2 review found; the runner refuses any."""
    tol = 1e-12
    counts = {"p_qual_year_gt_p_appear_year": 0, "p_qual_h_gt_p_appear_by_h": 0, "cumulative_decreasing": 0,
              "p_qual_year_gt_p_qual_h": 0, "e_qual_seasons_lt_p_qual_h": 0}
    for j in range(1, max(horizons) + 1):
        counts["p_qual_year_gt_p_appear_year"] += int((frame[f"p_qual_year{j}"] > frame[f"p_appear_year{j}"] + tol).sum())
        if j in horizons:
            counts["p_qual_h_gt_p_appear_by_h"] += int((frame[f"p_qual_h{j}"] > frame[f"p_appear_by_h{j}"] + tol).sum())
            counts["p_qual_year_gt_p_qual_h"] += int((frame[f"p_qual_year{j}"] > frame[f"p_qual_h{j}"] + tol).sum())
            counts["e_qual_seasons_lt_p_qual_h"] += int((frame[f"e_qual_seasons_h{j}"] + tol < frame[f"p_qual_h{j}"]).sum())
            if j > 1 and (j - 1) in horizons:
                counts["cumulative_decreasing"] += int((frame[f"p_qual_h{j}"] + tol < frame[f"p_qual_h{j - 1}"]).sum())
                counts["cumulative_decreasing"] += int((frame[f"p_appear_by_h{j}"] + tol < frame[f"p_appear_by_h{j - 1}"]).sum())
    return {"rows": int(len(frame)), "violations": counts, "status": "clean" if not any(counts.values()) else "VIOLATIONS"}


def main(argv=None) -> int:
    args = parse_args(argv)
    T = args.forecast_year
    last_completed = args.last_completed_season if args.last_completed_season is not None else T - 1
    horizons = tuple(sorted(set(args.horizons)))
    bar = dict(AVAILABILITY_BAR)
    policy = args.policy
    exploratory = tuple(a for a in args.exploratory if a != policy)
    started = datetime.now(timezone.utc)

    run_dir = create_run_dir(args.runs_root, name="dg165_rookie_capital")
    inputs = run_dir / "inputs"
    inputs.mkdir()
    (run_dir / ".gitignore").write_text("inputs/\n")
    print(f"run dir: {run_dir} | declared policy: {policy} | exploratory: {exploratory}")

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
    cohort, coverage = draft_cohort_from_picks(picks, seasons=range(args.first_class, T + 1), players=players, rosters=rosters)
    outcome_block = None
    if args.outcomes_csv is not None:
        # The COMMON outcome artifact (DG-179): both producers label from identical outcomes.
        if args.outcomes_manifest is None or args.weekly_capture is None:
            raise SystemExit("--outcomes-csv needs --outcomes-manifest and --weekly-capture")
        weekly_positions = _weekly_positions_from_capture(args.weekly_capture)
        oi = outcome_inputs(args.outcomes_csv, args.outcomes_manifest, cohort=cohort, weekly_positions=weekly_positions, bar=bar)
        if oi.labels_through < last_completed:
            raise SystemExit(f"outcome artifact labels through {oi.labels_through}; the run needs {last_completed}")
        last_completed = oi.labels_through
        qualifying, season_stats = oi.qualifying, oi.season_stats
        panel = oi.panel
        covered_seasons = oi.covered_seasons
        # EXPLICIT cohort restriction (Codex): classes whose rookie season the artifact does not
        # cover (1999, 2000) are excluded from fitting rather than labelled from an unmeasured absence.
        first_covered = min(covered_seasons)
        dropped_classes = sorted(int(c) for c in cohort.loc[cohort["draft_season"] < first_covered, "draft_season"].unique())
        cohort = cohort.loc[cohort["draft_season"] >= first_covered].reset_index(drop=True)
        print(f"cohort restricted to classes >= {first_covered} (dropped classes {dropped_classes}); labels outside {sorted(covered_seasons)[0]}-{sorted(covered_seasons)[-1]} stay unknown")
        panel_path = inputs / "common_outcomes.csv"
        shutil.copy2(args.outcomes_csv, panel_path)
        shutil.copy2(args.outcomes_manifest, inputs / "common_outcomes_manifest.json")
        panel_source = f"common outcome artifact {oi.binding['artifact']} (sha256 {oi.csv_sha256 if hasattr(oi, 'csv_sha256') else oi.binding['csv_sha256'][:12]})"
        outcome_block = {**oi.binding, "panel_report": oi.panel_report,
                         "cohort_restriction": {"first_class": first_covered, "dropped_classes": dropped_classes,
                                                "reason": "the artifact does not cover those rookie seasons; unknown, never zero"},
                         "weekly_capture": {"path": str(args.weekly_capture), "manifest_sha256": sha256_file(args.weekly_capture / "manifest.json")}}
        print(f"outcomes: {oi.binding['artifact']} rows {oi.binding['rows']} seasons {oi.binding['seasons']} labels_through {oi.labels_through} | panel {oi.panel_report}")
    else:
        covered_seasons = None
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
        qualifying = qualifying_season_keys(panel, bar)
        season_stats = season_stats_map(panel)
    print(f"panel: {len(panel)} player-seasons {panel['season'].min()}-{panel['season'].max()} ({panel_source})")

    # ---------------------------------------------------------------- events and cohort
    leaking = find_leaking_columns(cohort)
    if leaking:
        raise SystemExit(f"cohort frame carries market-derived columns: {leaking}")
    # The draft table's position is the model's position term; the players table carries the
    # player's CURRENT NFL position (a 2026 pick listed TE at the draft plays RB/FB). Both are
    # exported; the join key for a consumer is (draft_season, pick), unique within a draft.
    current = players.drop_duplicates("gsis_id").set_index("gsis_id")["position"].astype(str)
    cohort["position_current"] = cohort["gsis_id"].map(current).where(lambda s: s.notna(), None)
    position_changes = cohort.loc[cohort["position_current"].notna() & (cohort["position_current"] != cohort["position"]) & (cohort["draft_season"] == T)]
    print(f"cohort: {coverage} | {T} rookies whose current position differs from the draft table: {len(position_changes)}")
    cohort.to_csv(run_dir / "cohort.csv", index=False)

    # ---------------------------------------------------------------- the declared policy, evaluated; exploratory arms beside it
    forecast_years = range(args.eval_start, T)
    common = dict(qualifying=qualifying, season_stats=season_stats, horizons=horizons,
                  forecast_years=forecast_years, last_completed_season_today=last_completed, n_boot=args.eval_boot,
                  covered_seasons=covered_seasons)
    experiment = policy_experiment(cohort, policy=policy, exploratory=exploratory, **common)
    evaluation, predictions = experiment["arms"][policy], experiment["predictions"][policy]
    coherence = _coherence(predictions, horizons)
    evaluation["coherence"] = coherence
    if coherence["status"] != "clean":
        raise SystemExit(f"historical predictions violate the event bounds: {coherence}")
    evaluation_path = run_dir / "evaluation.json"
    evaluation_path.write_text(json.dumps(evaluation, indent=1, default=_json_default))
    evaluation_sha = sha256_file(evaluation_path)
    (run_dir / "EVALUATION.md").write_text(render_evaluation_markdown(evaluation))
    predictions.to_csv(run_dir / "out_of_time_predictions.csv", index=False)
    for name in exploratory:
        (run_dir / f"evaluation_exploratory_{name}.json").write_text(json.dumps(experiment["arms"][name], indent=1, default=_json_default))
        experiment["predictions"][name].to_csv(run_dir / f"out_of_time_predictions_{name}.csv", index=False)
    comparison = {k: v for k, v in experiment.items() if k not in ("arms", "predictions")}
    (run_dir / "policy_comparison.json").write_text(json.dumps(comparison, indent=1, default=_json_default))
    for name, value in _headline(evaluation).items():
        print(f"  {name} = {value:.4f}")
    chosen = [(y["forecast_year"], (y.get("policy_selection") or {}).get("chosen", y["variant"])) for y in evaluation["per_forecast_year"]]
    print(f"variants chosen inside training windows: {dict(chosen)}")
    print(f"coherence on {coherence['rows']} historical rows: {coherence['status']} {coherence['violations']}")

    # ---------------------------------------------------------------- the bounded calibration assessment (no correction applied)
    assessment = calibration_assessment(predictions, seasons=(1, 2), n_boot=args.eval_boot)
    (run_dir / "calibration_assessment.json").write_text(json.dumps(assessment, indent=1, default=_json_default))
    (run_dir / "CALIBRATION.md").write_text(render_assessment_markdown(assessment))

    # ---------------------------------------------------------------- sensitivity: unknown identities forced to zero, same policy
    sensitivity_eval, _ = evaluate_forecast_years(cohort, unresolved_as_zero=True, policy=policy, **{**common, "n_boot": 0})
    (run_dir / "evaluation_sensitivity_unresolved_as_zero.json").write_text(json.dumps(sensitivity_eval, indent=1, default=_json_default))
    deltas = [{"quantity": name, "default": value, "arm": _headline(sensitivity_eval)[name], "delta": _headline(sensitivity_eval)[name] - value}
              for name, value in _headline(evaluation).items()]

    # ---------------------------------------------------------------- final fit and scores (THE procedure, the declared policy)
    fit_kwargs = dict(qualifying=qualifying, season_stats=season_stats, horizons=horizons, forecast_year=T, covered_seasons=covered_seasons)
    model = fit_at_forecast_year(cohort, policy=policy, **fit_kwargs)
    train = training_frame_at(cohort, **fit_kwargs)
    rookies = cohort.loc[cohort["draft_season"] == T].reset_index(drop=True)
    if rookies.empty:
        raise SystemExit(f"no {T} draft class in the nflverse pick table; nothing to score")
    scores = score_class(model, rookies, model_policy=policy, evaluation_sha256=evaluation_sha)
    intervals = bootstrap_intervals(train, rookies, horizons=horizons, n_boot=args.bootstrap, variant=model.variant)
    scores = scores.merge(intervals, on="gsis_id", how="left")
    assert len(scores) == len(rookies), "rows lost in the interval merge"
    scores = scores.sort_values("pick").reset_index(drop=True)
    score_coherence = _coherence(scores, horizons)
    if score_coherence["status"] != "clean":
        raise SystemExit(f"scored rows violate the event bounds: {score_coherence}")
    scores_path = run_dir / f"rookie_scores_{T}.csv"
    scores.to_csv(scores_path, index=False)
    (run_dir / f"ROOKIES_{T}.md").write_text(render_scores_markdown(scores, horizons, T))
    print(f"scored {len(scores)} rookies of class {T} with variant {model.variant} (policy {policy}); identity: "
          f"{scores['identity_status'].value_counts().to_dict()}; coverage: {scores['coverage_status'].value_counts().to_dict()}")
    arm_model = fit_at_forecast_year(cohort, unresolved_as_zero=True, policy=policy, **fit_kwargs)
    arm_scores = score_class(arm_model, rookies, model_policy=policy, evaluation_sha256=evaluation_sha)
    base_scores = scores.set_index("gsis_id")
    score_deltas = []
    for col in [c for c in arm_scores.columns if c.startswith(("p_", "e_"))]:
        diff = np.abs(arm_scores[col].to_numpy(dtype=float) - base_scores.loc[arm_scores["gsis_id"], col].to_numpy(dtype=float))
        i = int(np.nanargmax(diff)) if np.isfinite(diff).any() else 0
        score_deltas.append({"column": col, "max_abs_delta": float(np.nanmax(diff)), "player": str(arm_scores["name"].iloc[i])})
    sensitivity = {"evaluation_deltas": deltas, "score_deltas": sorted(score_deltas, key=lambda r: -r["max_abs_delta"])[:12],
                   "sensitivity_arm_variant": arm_model.variant}
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
                     "source": str(args.prospects_csv), "sha256": sha256_file(args.prospects_csv)}

    # ---------------------------------------------------------------- manifest with affirmative identifiers and pairing
    manifest = {
        "ticket": "DG-165",
        "model_version": MODEL_VERSION,
        "model_policy": policy,
        "scoring_arm_id": model.arm_id,
        "scoring_variant": model.variant,
        "exploratory_arms": list(exploratory),
        "evidence_status": comparison["evidence_status"],
        "status": "RESEARCH CANDIDATE — not served, not promoted, not merged",
        "run_dir": str(run_dir.relative_to(REPO)),
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "forecast_date": {
            "forecast_year": T,
            "forecast_cutoff": f"{T}-09-01 (pre-season {T}, after the NFL draft)",
            "label_window": f"labels through NFL season {last_completed}; NFL season j = 1 is the rookie season = {T}",
            "labels_through": last_completed,
            "last_completed_season": last_completed,
        },
        "definitions": {
            "qualifying_season": (f"finished at or above the bar rank for the position by league-window points ({outcome_block['window_rule']}); "
                                  if outcome_block else "finished at or above the bar rank for the position by regular-season PPR total; ")
                                 + f"bar = {bar}; tie-robust N-th largest (canonical DG-164 cells); a qualifying season is by construction an appearance; "
                                   "cohort players are ranked at their DRAFT role every season, others at their weekly-stats position",
            "appearance": "at least one weekly stat row in nflverse regular-season player stats (not 'dressed', not 'took a snap'); "
                          "a player without a stat row scored zero fantasy points that season",
            "season_points": "regular-season PPR points (nflverse weekly fantasy_points_ppr), exactly 0 without an appearance",
            "games": "weeks with a weekly stat row, exactly 0 without an appearance",
            "identity_unresolved": "no gsis_id in nflverse draft picks and no match in the players table or 1999-%d rosters by draft key or name+year; "
                                   "labels NaN, never zero, except in the named sensitivity arm" % last_completed,
        },
        "units": ({
            "scoring_scope": f"championship window: {outcome_block['window_rule']}; scoring preset {outcome_block['scoring_preset']}; "
                             f"league_scoring_exact=False — {outcome_block['scoring_caveat']}",
            "scoring_preset": outcome_block["scoring_preset"], "league_scoring_exact": False,
            "target_identity": outcome_block["target_identity"], "coverage_status": outcome_block["coverage_status"],
            "qualification_note": outcome_block["qualification_note"],
            "exposure_definition": outcome_block["exposure_definition"],
            "ppg_denominator": "league-window points / league-window stat-row games — NOT the served all-games denominator (DG-024); reconcile, do not absorb",
            "seasons": "NFL season j = 1 is the rookie season = forecast_year; E[N_h] counts qualifying seasons in 1..h",
        } if outcome_block else {
            "scoring_scope": "regular season only; PPR as in nflverse weekly player stats",
            "exposure_definition": "stat-row games (weeks with a weekly stat row)",
            "ppg_denominator": "REG-season PPR points / stat-row games — NOT the served all-games denominator (DG-024); reconcile, do not absorb",
            "seasons": "NFL season j = 1 is the rookie season = forecast_year; E[N_h] counts qualifying seasons in 1..h",
        }),
        "outcomes": outcome_block,
        "construction": model.describe()["construction"],
        "no_composition_claims": "nothing here states how these quantities compose with Engine A, Engine B or the DG-164 cells; "
                                 "that comparability is the ranking lane's typed contract (DG-178)",
        "cohort": {"source": "nflreadpy.load_draft_picks(); identities resolved via load_players() and load_rosters(1999-%d)" % last_completed,
                   "classes": [args.first_class, T], "positions": ["QB", "RB", "WR", "TE"], "coverage": coverage,
                   "join_key": "(draft_season, pick) — unique within a draft year; `position` is the draft-table classification the model "
                               "uses, `position_current` is the nflverse players-table position at run time; treat position as an attribute",
                   "rookies_with_position_change": [{"name": r["name"], "pick": int(r["pick"]), "draft_position": r["position"], "current_position": r["position_current"]}
                                                    for _, r in position_changes.iterrows()],
                   "undrafted": "NOT in the cohort and NOT modelled — no undrafted-prospect population table exists in the product"},
        "model": model.describe(),
        "evaluation": {"forecast_years": [int(forecast_years.start), int(forecast_years.stop - 1)], "n_boot": args.eval_boot,
                       "policy_id": evaluation["policy_id"], "arm_ids": evaluation["arm_ids"],
                       "headline": _headline(evaluation), "coherence": coherence,
                       "sensitivity_unresolved_as_zero": deltas, "exploratory_comparison": "policy_comparison.json"},
        "calibration_assessment": "calibration_assessment.json / CALIBRATION.md — assessment only; no correction applied anywhere",
        "score_intervals": {"method": "refit on player-resampled training sets, 5th/95th percentile; fit uncertainty conditional on this variant",
                            "n_boot_requested": args.bootstrap, "n_boot_effective": intervals.attrs.get("n_boot_effective")},
        "dg176_names_present": dg176,
        "inputs": {
            "nflverse_draft_picks": {"path": str(picks_path.relative_to(run_dir)), "sha256": sha256_file(picks_path), "rows": int(len(picks))},
            "nflverse_players": {"path": str(players_path.relative_to(run_dir)), "sha256": sha256_file(players_path), "rows": int(len(players))},
            "nflverse_rosters": {"path": str(rosters_path.relative_to(run_dir)), "sha256": sha256_file(rosters_path), "rows": int(len(rosters))},
            "panel": {"path": str(panel_path.relative_to(run_dir)), "sha256": sha256_file(panel_path), "rows": int(len(panel)),
                      "seasons": [int(panel["season"].min()), int(panel["season"].max())], "source": panel_source},
            "age_cross_check": age_check,
        },
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                        "sklearn": __import__("sklearn").__version__, "nflreadpy": __import__("nflreadpy").__version__},
    }
    manifest["pairing"] = verify_pairing(manifest=manifest, evaluation=evaluation, scores=scores, evaluation_sha256=evaluation_sha)
    manifest["outputs_sha256"] = {p.name: sha256_file(p) for p in sorted(run_dir.iterdir()) if p.is_file() and p.name != "manifest.json"}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=_json_default))
    (run_dir / "REPORT.md").write_text(render_report_markdown(manifest, evaluation, sensitivity, scores, comparison, assessment))
    manifest["outputs_sha256"]["REPORT.md"] = sha256_file(run_dir / "REPORT.md")
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, default=_json_default))
    print(f"pairing: {manifest['pairing']['status']} | manifest written: {run_dir / 'manifest.json'}")
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
