#!/usr/bin/env python3
"""DG-177 round 2, items 5 and 6 — years 1-5 on a longer BASIC cohort, and the inference cohort.

REPORT-ONLY. Pulls nflverse weekly stats and the players table over the network into
this run's directory (saved with shas), builds the basic cohort (``eval/basic_cohort``),
labels it on the agreed REG appearance event for horizons 1-5, evaluates the selection
policy per position and horizon with closed folds, and scores the 2025 cohort — which
includes players whose 2025 season was a whole absence after an active 2024 (Tank Dell)
as zero-games rows, never fabricated stat lines. Cells whose horizon cannot be
supported by closed history are reported unsupported and left empty.

Usage:  .venv/bin/python scripts/experiments/dg177_basic_horizons.py [--draws 1000]
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

from scripts.experiments.dg177_annual_forecasts import (  # noqa: E402
    RUNS_ROOT,
    _fmt,
    _fmt_delta,
    _git,
    build_manifest,
    pull_weekly_stats,
    validate_manifest,
)
from src.dynasty_genius.eval.annual_forecasts import (  # noqa: E402
    POLICY_SPACE,
    QUANTITIES,
    SELECTION_CRITERION,
    evaluate_horizon_policy,
    fit_policy,
    observed_mask,
)
from src.dynasty_genius.eval.annual_outcomes import (  # noqa: E402
    annual_targets,
    season_outcomes,
    split_unattributed_rows,
    validate_weekly_source,
)
from src.dynasty_genius.eval.basic_cohort import (  # noqa: E402
    BASIC_FEATURES,
    COHORT_RULE,
    PRODUCTION_SCOPE,
    build_basic_cohort,
    validate_players_table,
)
from src.dynasty_genius.eval.common_outcomes import load_common_outcomes  # noqa: E402
from src.dynasty_genius.eval.evaluation_status import (  # noqa: E402
    SUPPORTED_MEANING,
    evaluation_status,
)
from src.dynasty_genius.eval.universe_reconciliation import (
    reconcile_universe,  # noqa: E402
)
from src.dynasty_genius.eval.veteran_candidate import write_run_artifact  # noqa: E402
from src.dynasty_genius.models.label_closure import (
    admissible_train_seasons,  # noqa: E402
)

HORIZONS: tuple[int, ...] = (1, 2, 3, 4, 5)
FIRST_SEASON = 2005
INFERENCE_SEASON = 2025
LAST_COMPLETE_SEASON = 2025
SCOPE = "REG"
POSITIONS = ("QB", "RB", "WR", "TE")
MIN_TRAINING_SEASONS = 6
ARM = "basic_cohort_3col_plus_lags"
#: The outcome window a producer file was labelled on; the ranking lane's adapter refuses a
#: producer whose window differs from the board's, so the manifest names it explicitly.
WINDOW_IDS = {"this_lane_REG_aggregation": "all_reg_weeks", "common_outcome_artifact": "championship_week17"}


def window_id_for(label_source_kind: str) -> str:
    if label_source_kind not in WINDOW_IDS:
        raise ValueError(f"unknown label source {label_source_kind!r}; expected one of {sorted(WINDOW_IDS)}")
    return WINDOW_IDS[label_source_kind]
#: DG-165's immutable roster capture (read-only): one season-end roster row per player-season,
#: 1999-2025, dated by week inside the season. Same-season offensive-role evidence only.
DEFAULT_ROSTER_ROLES = Path("/Users/davidleess/dg-wt/DG-165/runs/20260906T154706Z/dg165_rookie_capital/inputs/nflverse_rosters.parquet")


def horizon_support(seasons: Iterable[int], *, last_complete_season: int, min_training_seasons: int) -> dict[int, dict[str, Any]]:
    """Which horizons the closed history can support, and why not otherwise."""
    seasons = sorted(int(s) for s in seasons)
    out: dict[int, dict[str, Any]] = {}
    for j in HORIZONS:
        closed = [s for s in seasons if s + j <= int(last_complete_season)]
        supported = len(closed) >= int(min_training_seasons)
        out[j] = {
            "closed_feature_seasons": closed,
            "supported": supported,
            "supported_means": SUPPORTED_MEANING,
            "reason": None if supported else (
                f"year-{j} labels close only for feature seasons {closed[0] if closed else '—'}..{closed[-1] if closed else '—'} "
                f"({len(closed)} seasons) with a cohort starting {seasons[0]}; fewer than the {min_training_seasons} "
                "closed seasons this evaluation needs — reported unsupported, not filled from year two"
            ),
        }
    return out


def evaluable_horizons(support: dict[int, dict[str, Any]]) -> list[int]:
    return [j for j, s in support.items() if s["supported"]]


def test_seasons_for(j: int, seasons: list[int], *, last_complete_season: int, min_training_seasons: int) -> list[int]:
    """Outer test seasons: every closed feature season that has at least the floor of
    closed seasons before it."""
    closed = [s for s in seasons if s + j <= last_complete_season]
    return [s for s in closed if len(admissible_train_seasons(closed, s, window=j)) >= min_training_seasons]


def _render(results: dict[str, Any]) -> str:
    m = results["manifest"]
    lines = ["# DG-177 — years 1-5 on the basic cohort (report-only)\n",
             f"Cohort rule: {results['cohort']['rule']} · production: {results['cohort']['production_scope']} · "
             f"features: {results['cohort']['features']} · git `{m['git_head']}`\n"]
    rf = results.get("role_fallback") or {}
    if rf.get("supplied"):
        lines.append(f"\nRole fallback: {rf['rule']} · roster capture rows {rf['rows']} ({rf['seasons'][0]}-{rf['seasons'][1]}) · "
                     f"by source {rf['counts']['by_source']} · resolved by roster {rf['counts']['resolved_by_roster_by_position']}\n")
    lines.append("\n## Horizon support\n")
    for j, s in results["horizon_support"].items():
        lines.append(f"- year {j}: {'supported' if s['supported'] else 'UNSUPPORTED — ' + s['reason']}; closed feature seasons "
                     f"{s['closed_feature_seasons'][0] if s['closed_feature_seasons'] else '—'}..{s['closed_feature_seasons'][-1] if s['closed_feature_seasons'] else '—'}")
    lines.append("\n## Policy evidence (pooled over evaluated folds; Δ = policy − training-only baseline, 90% player-resampled)\n")
    lines.append("| pos | year | folds | P Brier / base · AUC · base rate | points\\|appear Δr² | unconditional points Δr² | ΔRMSE | policies chosen (by fold) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for pos, per in results["historical"].items():
        for yk, ev in per.items():
            p = ev.get("pooled") or {}
            if not p:
                lines.append(f"| {pos} | {yk} | {len(ev.get('folds', []))} | no fold evaluable | | | | |")
                continue
            pol = p["policy"]
            pr = pol["probability"]
            lines.append(f"| {pos} | {yk} | {len(ev['evaluated_test_seasons'])} | {_fmt(pr['brier'])} / {_fmt(pr['baseline_brier'])} · "
                         f"{_fmt(pr['auc'], 2)} · {_fmt(pr['base_rate'], 2)} | {_fmt_delta(pol['points_given_appear']['delta_vs_baseline']['delta_r2'])} | "
                         f"{_fmt_delta(pol['points_unconditional']['delta_vs_baseline']['delta_r2'])} | "
                         f"{_fmt_delta(pol['points_unconditional']['delta_vs_baseline']['delta_rmse'])} | "
                         f"{json.dumps(p['policies_chosen_by_fold'])} |")
    u = results.get("universe_reconciliation") or {}
    if u.get("universe"):
        lines.append("\n## Eligible universe reconciliation\n")
        lines.append(f"{u['rows']} universe rows: {json.dumps(u['by_status'])}; rostered: {json.dumps(u['rostered_by_status'])}. "
                     "Every row is a forecast or one precise reason; nothing is written as zero.\n")
    c = results["inference_cohort"]
    lines.append(f"\n## Inference cohort (feature season {c['feature_season']})\n")
    lines.append(f"Rows {c['rows']} by position {c['by_position']}; zero-games rows (whole missed 2025 after an active 2024) "
                 f"{c['zero_games_rows']}; identity {c['identity_status']}.\n")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--tolerated-unattributed-points", type=float, default=0.0,
                        help="per-season points tolerance for unattributed stat lines; 0 (default) refuses them. Any "
                             "non-zero value is a disclosed cleaning exception recorded in the manifest.")
    parser.add_argument("--first-season", type=int, default=FIRST_SEASON)
    parser.add_argument("--min-train-rows", type=int, default=60)
    parser.add_argument("--out-root", type=Path, default=RUNS_ROOT)
    parser.add_argument("--universe", type=Path, default=None,
                        help="DG-178's eligible_universe.csv; every row gets a forecast or a precise reason")
    parser.add_argument("--outcomes-artifact", type=Path, default=None,
                        help="Codex's common player-season outcome CSV (labels); features stay ALL NFL games")
    parser.add_argument("--outcomes-manifest", type=Path, default=None, help="its manifest (scoring identifier, window, sha256)")
    parser.add_argument("--roster-roles", type=Path, default=DEFAULT_ROSTER_ROLES,
                        help="historical roster capture (parquet) for the same-season offensive-role fallback; "
                             "'none' disables it")
    args = parser.parse_args(argv)

    import nflreadpy as nfl

    from src.dynasty_genius.eval.backtest_harness import PRIMARY_NDCG_K

    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_root) / run_id / "dg177_basic_horizons"
    pull_seasons = list(range(args.first_season, LAST_COMPLETE_SEASON + 1))

    pulled_at = datetime.now(timezone.utc)
    raw_weekly = pull_weekly_stats(pull_seasons)
    # The cleaner returns the removed rows itself (original indices); an index difference
    # taken after its reset named trailing positions, not the rows that left.
    weekly, dropped_rows, dropped = split_unattributed_rows(raw_weekly, tolerated_points_per_season=args.tolerated_unattributed_points)
    source_validation = {**validate_weekly_source(weekly, seasons=pull_seasons), **dropped,
                         "cleaning": "the dropped placeholder rows and unattributed stat lines are a disclosed cleaning "
                                     "exception, not proof of source completeness; they are kept in dropped_rows.csv "
                                     "so the cleaning can be replayed"}
    weekly_bytes = gzip.compress(weekly.to_csv(index=False).encode("utf-8"))
    players = nfl.load_players()
    players = players.to_pandas() if hasattr(players, "to_pandas") else players
    players = players[["gsis_id", "display_name", "position", "birth_date", "last_season", "status"]].copy()
    players = players[players["gsis_id"].notna()].reset_index(drop=True)
    players_facts = validate_players_table(players)
    players_bytes = gzip.compress(players.to_csv(index=False).encode("utf-8"))
    print(f"weekly rows {len(weekly)} · players {len(players)} · source validated")

    roster_roles = None
    roster_facts: dict[str, Any] = {"supplied": False}
    if str(args.roster_roles).lower() != "none":
        roster_bytes = args.roster_roles.read_bytes()
        roster_roles = pd.read_parquet(args.roster_roles)
        roster_facts = {
            "supplied": True, "path": str(args.roster_roles), "sha256": hashlib.sha256(roster_bytes).hexdigest(),
            "rows": int(len(roster_roles)), "seasons": [int(roster_roles["season"].min()), int(roster_roles["season"].max())],
            "rows_per_player_season_max": int(roster_roles.groupby(["gsis_id", "season"]).size().max()),
            "rule": "non-offensive stat-line position -> exactly one offensive role among the SAME season's roster "
                    "position/depth rows, else abstain; today's listing never used; evidence kept on the row",
        }
    cohort_all = build_basic_cohort(weekly, players, seasons=pull_seasons, roster_roles=roster_roles)
    role_counts = {
        "by_source": cohort_all["position_source"].value_counts().to_dict(),
        "resolved_by_roster_by_position": cohort_all[cohort_all["position_source"] == "roster_same_season"]["position"].value_counts().to_dict(),
        "resolved_by_roster_by_season": {str(k): int(v) for k, v in cohort_all[cohort_all["position_source"] == "roster_same_season"].groupby("feature_season").size().items()},
        "abstained_conflicting": int((cohort_all["position_source"] == "conflicting_roster_roles").sum()),
        "unknown_no_offensive_role": int((cohort_all["position_source"] == "no_offensive_role").sum()),
    }
    cohort = cohort_all[cohort_all["position"].isin(POSITIONS)].reset_index(drop=True)
    print("role fallback:", role_counts["by_source"], "| resolved by roster:", role_counts["resolved_by_roster_by_position"])
    if args.outcomes_artifact is not None:
        # Labels from the COMMON artifact (REG league window, nflverse-default PPR, not exact league
        # scoring); features above stay ALL NFL games. Points, games and appearance come from one mask.
        common_manifest = json.loads(args.outcomes_manifest.read_text())
        outcomes = load_common_outcomes(args.outcomes_artifact, common_manifest)
        label_source = {"kind": "common_outcome_artifact", "path": str(args.outcomes_artifact),
                        "manifest": str(args.outcomes_manifest), "csv_sha256": outcomes.attrs["csv_sha256"],
                        "manifest_sha256": hashlib.sha256(args.outcomes_manifest.read_bytes()).hexdigest(),
                        "scoring": outcomes.attrs["scoring"], "exact_league_scoring": False,
                        "weeks": outcomes.attrs["weeks"], "seasons_covered": outcomes.attrs["seasons_covered"]}
        scope_label = outcomes.attrs["scope"]
    else:
        outcomes = season_outcomes(weekly, scope=SCOPE, validation=source_validation)
        label_source = {"kind": "this_lane_REG_aggregation", "scoring": "fantasy_points_ppr (nflverse weekly column)",
                        "exact_league_scoring": False, "weeks": "all REG weeks"}
        scope_label = SCOPE
    labelled = annual_targets(cohort, outcomes, horizons=HORIZONS, last_complete_season=LAST_COMPLETE_SEASON)
    df = pd.concat([cohort.reset_index(drop=True), labelled.drop(columns=["player_id", "position", "feature_season", "identity_status"])], axis=1)
    seasons = sorted(int(s) for s in df["feature_season"].unique())
    support = horizon_support(seasons, last_complete_season=LAST_COMPLETE_SEASON, min_training_seasons=MIN_TRAINING_SEASONS)
    print("cohort rows", len(df), "seasons", seasons[0], "..", seasons[-1], "| supported horizons", evaluable_horizons(support))

    historical: dict[str, Any] = {}
    prediction_frames: list[pd.DataFrame] = []
    for position in POSITIONS:
        k = int(PRIMARY_NDCG_K.get(position, 12))
        pos_df = df[df["position"] == position]
        historical[position] = {}
        for j in HORIZONS:
            if not support[j]["supported"]:
                historical[position][f"year{j}"] = {"unsupported": True, "reason": support[j]["reason"], "folds": []}
                continue
            tests = test_seasons_for(j, seasons, last_complete_season=LAST_COMPLETE_SEASON, min_training_seasons=MIN_TRAINING_SEASONS)
            ev, preds = evaluate_horizon_policy(
                pos_df, BASIC_FEATURES, horizon=j, test_seasons=tests, k=k,
                draws=args.draws, seed=args.seed, min_train_rows=args.min_train_rows,
            )
            historical[position][f"year{j}"] = ev
            preds.insert(0, "horizon", j)
            prediction_frames.append(preds)
            print(f"  {position} year{j}: evaluated {len(ev['evaluated_test_seasons'])} of {len(tests)} folds")

    # inference cohort: every 2025 basic-cohort row, zero-games rows included
    inference = df[df["feature_season"] == INFERENCE_SEASON].reset_index(drop=True)
    forecasts = inference[["player_id", "position", "statline_position", "position_source", "role_evidence", "listed_position",
                           "feature_season", "identity_status", "games_t", "seasons_since_last_observed"]].copy()
    forecasts.insert(4, "forecast_cutoff", f"post-{INFERENCE_SEASON}-season")
    forecasts.insert(5, "arm", ARM)
    fits: dict[str, Any] = {}
    for position in POSITIONS:
        rows = df[df["position"] == position]
        test = inference[inference["position"] == position]
        if test.empty:
            continue
        fits[position] = {}
        for j in HORIZONS:
            if not support[j]["supported"]:
                continue
            closed = rows[rows["feature_season"].astype(int) + j <= LAST_COMPLETE_SEASON]
            train = closed[observed_mask(closed, j)]
            pred, meta = fit_policy(train, test, BASIC_FEATURES, horizon=j, test_season=LAST_COMPLETE_SEASON)
            for name in QUANTITIES(j):
                forecasts.loc[test.index, name] = pred[name]
            forecasts.loc[test.index, f"forecast_season_year{j}"] = INFERENCE_SEASON + j
            fits[position][f"year{j}"] = meta
    for j in HORIZONS:
        if not support[j]["supported"]:
            for name in QUANTITIES(j):
                forecasts[name] = float("nan")
            forecasts[f"unsupported_year{j}_reason"] = support[j]["reason"]

    reconciliation: dict[str, Any] = {"universe": None}
    reconciled = pd.DataFrame()
    if args.universe is not None:
        universe = pd.read_csv(args.universe, dtype=str)
        idmap = nfl.load_ff_playerids()
        idmap = idmap.to_pandas() if hasattr(idmap, "to_pandas") else idmap
        idmap_bytes = gzip.compress(idmap.to_csv(index=False).encode("utf-8"))
        history = weekly.groupby("player_id")["season"].max().rename("last_season_seen").reset_index()
        reconciled = reconcile_universe(universe, idmap[["sleeper_id", "gsis_id"]], inference, history,
                                        inference_season=INFERENCE_SEASON,
                                        cohort_positions=cohort_all[["player_id", "feature_season", "position"]])
        reconciliation = {
            "universe": str(args.universe), "universe_sha256": hashlib.sha256(args.universe.read_bytes()).hexdigest(),
            "idmap": "nflreadpy.load_ff_playerids()", "idmap_sha256": hashlib.sha256(idmap_bytes).hexdigest(),
            "rows": int(len(reconciled)), "by_status": reconciled["status"].value_counts().to_dict(),
            "rostered_by_status": reconciled[reconciled["rostered"].astype(str).str.lower().isin(["true", "1"])]["status"].value_counts().to_dict(),
        }
        print("universe reconciliation:", reconciliation["by_status"])

    coverage = {
        "feature_season": INFERENCE_SEASON, "rows": int(len(forecasts)),
        "by_position": forecasts.groupby("position").size().to_dict(),
        "zero_games_rows": int((forecasts["games_t"] == 0).sum()),
        "identity_status": forecasts["identity_status"].value_counts().to_dict(),
    }
    source = {
        "weekly_stats": f"nflreadpy.load_player_stats(seasons={pull_seasons[0]}..{pull_seasons[-1]}, summary_level='week')",
        "weekly_stats_pulled_at_utc": pulled_at.isoformat(), "weekly_stats_rows": int(len(weekly)),
        "weekly_stats_sha256": hashlib.sha256(weekly_bytes).hexdigest(),
        "players_table": "nflreadpy.load_players()", "players_sha256": hashlib.sha256(players_bytes).hexdigest(),
        "players_facts": players_facts, "nflreadpy": nfl.__version__,
    }
    source["label_source"] = label_source
    manifest = build_manifest(
        horizons=evaluable_horizons(support), inference_season=INFERENCE_SEASON, last_complete_season=LAST_COMPLETE_SEASON,
        scope=SCOPE, source=source, git_head=_git("rev-parse", "HEAD"),
        features_by_arm={ARM: {p: list(BASIC_FEATURES) for p in POSITIONS}}, candidate_arm=ARM,
        candidate_rationale="the basic cohort's only arm: first-party production, games, age, one lag and last-seen "
                            "features; the selection policy (baseline / candidate / bounded blend) is chosen per "
                            "position, horizon and quantity on closed inner folds",
        comparator_export="none", inputs={"weekly_stats_sha256": source["weekly_stats_sha256"],
                                          "players_sha256": source["players_sha256"],
                                          **({"roster_roles_sha256": roster_facts["sha256"]} if roster_facts.get("supplied") else {})},
        source_validation=source_validation,
        selection_policy={"space": list(POLICY_SPACE), "criterion": dict(SELECTION_CRITERION),
                          "chosen": {p: {h: m["policy_by_quantity"] for h, m in per.items()} for p, per in fits.items()}},
        population=f"every {INFERENCE_SEASON} row of the basic cohort ({COHORT_RULE})",
    )
    manifest["inputs_note"] = "the basic cohort does not read the Engine B training file; its inputs are the two snapshots"
    manifest["horizon_support"] = {str(j): s for j, s in support.items()}
    manifest["unsupported_horizons"] = [j for j in HORIZONS if not support[j]["supported"]]
    results = {
        "run_id": run_id, "started_utc": started.isoformat(), "manifest": manifest,
        "role_fallback": {**roster_facts, "counts": role_counts, "cohort_attr": cohort_all.attrs.get("role_fallback")},
        "cohort": {"rule": COHORT_RULE, "production_scope": PRODUCTION_SCOPE, "features": list(BASIC_FEATURES),
                   "feature_notes": {"seasons_played": f"seasons OBSERVED since the cohort start ({args.first_season}); "
                                                       "left-censored, not full career length",
                                     "position_rule": "modal stat-line position must be QB/RB/WR/TE; a two-way "
                                                      "player whose stat lines say CB is excluded by this rule"},
                   "rows": int(len(df)), "seasons": [seasons[0], seasons[-1]],
                   "rows_by_position": df.groupby("position").size().to_dict()},
        "horizon_support": {str(j): s for j, s in support.items()},
        "historical": historical, "final_fits": fits, "inference_cohort": coverage,
        "universe_reconciliation": reconciliation,
        "config": {"draws": args.draws, "seed": args.seed, "min_train_rows": args.min_train_rows,
                   "min_training_seasons": MIN_TRAINING_SEASONS, "first_season": args.first_season},
    }
    provenance = {"git_head": _git("rev-parse", "HEAD"), "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
                  "source": source, "finished_utc": datetime.now(timezone.utc).isoformat()}
    report = _render(results)
    historical_predictions = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame()
    written = write_run_artifact(out_dir, results, historical_predictions, provenance=provenance, report_md=report)
    (out_dir / "basic_forecasts.csv").write_text(forecasts.to_csv(index=False))
    if len(reconciled):
        (out_dir / "universe_reconciliation.csv").write_text(reconciled.to_csv(index=False))
    (out_dir / "basic_cohort.csv.gz").write_bytes(gzip.compress(df.to_csv(index=False).encode("utf-8")))
    (out_dir / "weekly_stats_snapshot.csv.gz").write_bytes(weekly_bytes)
    (out_dir / "players_snapshot.csv.gz").write_bytes(players_bytes)
    (out_dir / "predictions.csv").rename(out_dir / "historical_predictions.csv")
    manifest["exports"] = {"candidate": "basic_forecasts.csv", "comparator": "none"}
    (out_dir / "dropped_rows.csv").write_text(dropped_rows.to_csv(index=False))
    manifest["outputs"] = {name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
                           for name in ["basic_forecasts.csv", "results.json", "historical_predictions.csv",
                                        "basic_cohort.csv.gz", "weekly_stats_snapshot.csv.gz", "players_snapshot.csv.gz",
                                        "dropped_rows.csv"]
                           + (["universe_reconciliation.csv"] if len(reconciled) else [])}
    manifest["outputs_sha256"] = dict(manifest["outputs"])
    manifest["evaluation_status"] = evaluation_status({"historical": historical}, historical_predictions, arm_key=None)
    manifest["role_fallback"] = results["role_fallback"]
    manifest["label_source"] = label_source
    manifest["window_id"] = window_id_for(label_source["kind"])
    manifest["scoring_scope"]["window_id"] = manifest["window_id"]
    if label_source["kind"] == "common_outcome_artifact":
        manifest["scoring_scope"] = {"scope": scope_label, "scoring": label_source["scoring"],
                                     "exact_league_scoring": False, "weeks": label_source["weeks"],
                                     "season_types": ["REG"], "window_id": manifest["window_id"]}
        manifest["inputs"]["common_outcomes_sha256"] = label_source["csv_sha256"]
    validate_manifest(manifest, known_arms={ARM},
                      required_inputs=("weekly_stats_sha256", "players_sha256") + (("roster_roles_sha256",) if roster_facts.get("supplied") else ()),
                      run_dir=out_dir)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {written} + basic_forecasts.csv, basic_cohort.csv.gz, snapshots, manifest.json to {out_dir}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
