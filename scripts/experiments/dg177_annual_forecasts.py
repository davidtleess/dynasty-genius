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
feature list and the three-column recent-production set. Both are graded against
training-only baselines, and BOTH are exported as final forecasts (fitted on every row
whose year-j label was closed at the end of the last complete season, scoring the
inference partition). The file named ``annual_forecasts.csv`` carries the CANDIDATE
arm; which arm that is, and why, is written in the manifest. The choice was made on the
same historical folds the evaluation reports, and the manifest says so.

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
    POLICY_SPACE,
    QUANTITIES,
    SELECTION_CRITERION,
    evaluate_horizon,
    evaluate_horizon_policy,
    fit_horizon,
    fit_policy,
    observed_mask,
)
from src.dynasty_genius.eval.annual_outcomes import (  # noqa: E402
    EVENT,
    EXPOSURE,
    SCOPES,
    SCORING_COLUMN,
    annual_targets,
    drop_unattributed_zero_rows,
    season_outcomes,
    validate_weekly_source,
)
from src.dynasty_genius.eval.evaluation_status import (  # noqa: E402
    BOOTSTRAP_MEANING,
    BRIER_MEANING,
    SUPPORTED_MEANING,
    evaluation_status,
)
from src.dynasty_genius.eval.veteran_candidate import (
    validate_candidate_features,  # noqa: E402
    write_run_artifact,  # noqa: E402
)
from src.dynasty_genius.models.label_closure import assert_labels_known  # noqa: E402

SCOPE = "REG"
HORIZONS = (1, 2)
INFERENCE_SEASON = 2025
LAST_COMPLETE_SEASON = 2025
PULL_SEASONS = list(range(2018, 2026))
FORECAST_CUTOFF_RULE = "features observed through the feature season; a year-j label trains only when feature_season + j <= last complete season"
ARM_SERVED = "served_features"
ARM_RECENT = "recent_production_3col"
#: The exported candidate. Chosen after the historical evaluation on the same folds it
#: reports (a selection effect, stated): the three-column set matched or beat the served
#: list on unconditional points in six of eight position-horizon cells and never lost
#: detectably, while at QB year-2 the served list's appearance model scored below the
#: base rate. Fewer columns on a few hundred rows; nothing subtler than that.
ARM_CANDIDATE = ARM_RECENT
ARM_COMPARATOR = ARM_SERVED
CANDIDATE_RATIONALE = (
    "The exported candidate is the SELECTION POLICY over {baseline, recent_production_3col ridge, "
    "bounded blend}, chosen per position, horizon and quantity on closed inner folds inside the "
    "training window and applied by the same function final scoring calls; its outer-fold score is "
    "the evidence. recent_production_3col is the candidate arm because it matched or beat "
    "served_features on unconditional points in six of eight cells in round 1 and never lost "
    "detectably (that was a comparison on outer folds, so served_features stays an exploratory "
    "comparison, exported beside the candidate, not part of the policy space)."
)
EXPORTS = {ARM_CANDIDATE: "annual_forecasts.csv", ARM_COMPARATOR: "annual_forecasts_served_features.csv"}
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
    # NOT filled: a missing scoring value is unknown, and validate_weekly_source refuses it.
    out[SCORING_COLUMN] = pd.to_numeric(out[SCORING_COLUMN], errors="coerce")
    return out.reset_index(drop=True)


def final_forecasts(
    df: pd.DataFrame,
    features_by_position: dict[str, list[str]],
    *,
    horizons: Iterable[int],
    inference_season: int,
    last_complete_season: int,
    fitter=fit_horizon,
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
            pred, meta = fitter(train, test, features, horizon=j)
            out[f"forecast_season_year{j}"] = int(inference_season) + j
            for name in QUANTITIES(j):
                out[name] = pred[name]
            fits[position][f"year{j}"] = meta
        frames.append(out)
    forecasts = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return forecasts, fits


POSITIONS = ("QB", "RB", "WR", "TE")
KNOWN_ARMS = frozenset({ARM_SERVED, ARM_RECENT})


class ManifestShapeError(ValueError):
    """The handoff manifest does not have the shape the contract names."""


def validate_manifest(
    manifest: dict[str, Any], *, known_arms: frozenset[str] | set[str] = KNOWN_ARMS,
    required_inputs: tuple[str, ...] = ("training_csv_sha256",),
) -> None:
    """Assert the manifest's structure: arms and positions at their own levels, feature
    names that pass the feature gate, and input/output hashes present. Round-1's manifest
    nested arm names where positions belong and nobody could tell from prose.
    ``known_arms`` is the arm set the calling runner declares; an arm outside it is refused."""
    def _feature_list(where: str, value: Any) -> None:
        if not isinstance(value, list) or not value or not all(isinstance(f, str) for f in value):
            raise ManifestShapeError(f"{where}: expected a non-empty list of feature names, got {value!r}")
        if any(f in POSITIONS or f in known_arms for f in value):
            raise ManifestShapeError(f"{where}: a position or arm name sits where a feature name belongs: {value!r}")
        try:
            validate_candidate_features(value)
        except ValueError as err:
            raise ManifestShapeError(f"{where}: {err}") from err

    by_arm = manifest.get("features_by_arm")
    if not isinstance(by_arm, dict) or not by_arm:
        raise ManifestShapeError("features_by_arm is missing")
    for arm, per_position in by_arm.items():
        if arm not in known_arms:
            raise ManifestShapeError(f"unknown arm {arm!r} in features_by_arm (known: {sorted(known_arms)})")
        if not isinstance(per_position, dict) or not per_position:
            raise ManifestShapeError(f"features_by_arm[{arm!r}] must map position -> features")
        for position, features in per_position.items():
            if position not in POSITIONS:
                raise ManifestShapeError(f"features_by_arm[{arm!r}]: {position!r} is not a position")
            _feature_list(f"features_by_arm[{arm!r}][{position!r}]", features)
    by_position = manifest.get("features_by_position")
    if not isinstance(by_position, dict) or not by_position:
        raise ManifestShapeError("features_by_position is missing")
    for position, features in by_position.items():
        if position not in POSITIONS:
            raise ManifestShapeError(f"features_by_position: {position!r} is not a position (an arm name here is the round-1 defect)")
        _feature_list(f"features_by_position[{position!r}]", features)
    candidate = manifest.get("candidate_arm")
    if candidate not in by_arm or by_position != by_arm[candidate]:
        raise ManifestShapeError("features_by_position must equal features_by_arm[candidate_arm]")
    for block, required in (("inputs", tuple(required_inputs)), ("outputs", ("annual_forecasts.csv",))):
        values = manifest.get(block)
        if not isinstance(values, dict) or not values:
            raise ManifestShapeError(f"{block} hashes are missing")
        for key in required:
            if not isinstance(values.get(key), str) or len(values[key]) != 64:
                raise ManifestShapeError(f"{block}: {key} must carry a sha256")
    for key in ("event", "exposure_definition", "scoring_scope", "label_window", "quantities", "forecast_cutoff"):
        if key not in manifest:
            raise ManifestShapeError(f"target term {key!r} is missing")


def build_manifest(
    *, horizons: Iterable[int], inference_season: int, last_complete_season: int, scope: str,
    source: dict[str, Any], git_head: str, features_by_arm: dict[str, dict[str, list[str]]], population: str,
    candidate_arm: str = ARM_CANDIDATE, candidate_rationale: str = CANDIDATE_RATIONALE,
    comparator_export: str = EXPORTS[ARM_COMPARATOR],
    inputs: dict[str, str] | None = None, outputs: dict[str, str] | None = None,
    source_validation: dict[str, Any] | None = None,
    selection_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    horizons = [int(h) for h in horizons]
    if candidate_arm not in features_by_arm:
        raise ManifestShapeError(f"candidate arm {candidate_arm!r} is not among {sorted(features_by_arm)}")
    return {
        "producer": "DG-177 veteran annual forecast candidate (report-only)",
        "candidate_arm": candidate_arm,
        "scoring_arm": candidate_arm,
        "candidate_rationale": candidate_rationale,
        "selection_policy": dict(selection_policy or {
            "space": list(POLICY_SPACE), "criterion": dict(SELECTION_CRITERION),
            "where": "per position, horizon and quantity on closed inner folds inside the training window",
            "chosen": {},
        }),
        "exports": {"candidate": "annual_forecasts.csv", "comparator": comparator_export},
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
        "features_by_position": {p: list(f) for p, f in features_by_arm[candidate_arm].items()},
        "features_by_arm": {arm: {p: list(f) for p, f in per.items()} for arm, per in features_by_arm.items()},
        "inputs": dict(inputs or {}),
        "outputs": dict(outputs or {}),
        "outputs_sha256": dict(outputs or {}),
        "source_validation": dict(source_validation or {}),
        "intervals": "none exported; " + BOOTSTRAP_MEANING,
        "meaning": {"supported": SUPPORTED_MEANING, "bootstrap": BOOTSTRAP_MEANING, "brier": BRIER_MEANING},
        "evaluation_status": {},
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
                if ev.get("evidence") == "policy":
                    lines.append("\nEvidence = the SELECTION POLICY (chosen on closed inner folds): "
                                 + json.dumps(p.get("policies_chosen_by_fold", {})) + "\n")
                    p = {**p["policy"], "_exploratory": p["exploratory_candidate"]}
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
                if "_exploratory" in p:
                    x = p["_exploratory"]
                    lines.append(f"\nExploratory (plain candidate arm, not evidence for the policy): unconditional points "
                                 f"Δr² {_fmt_delta(x['points_unconditional']['delta_vs_baseline']['delta_r2'])}, "
                                 f"P Brier {_fmt(x['probability']['brier'])}\n")
                lines.append("\nPer fold, P(appear) Brier model / baseline and points|appear ΔRMSE vs baseline:\n")
                for f in ev["folds"]:
                    if f["skipped_reason"] is None:
                        blk = f.get("policy", f)
                        chosen = f" · policy {blk['policy_by_quantity']}" if "policy_by_quantity" in blk else ""
                        lines.append(f"- {f['test_season']}→{f['forecast_season']}: Brier {_fmt(blk['probability']['brier'])} / "
                                     f"{_fmt(blk['probability']['baseline_brier'])}; points|appear ΔRMSE "
                                     f"{_fmt_delta(blk['points_given_appear']['delta_vs_baseline']['delta_rmse'])}; "
                                     f"alpha points {f['fit']['points_model']['alpha']:g}, games {f['fit']['games_model']['alpha']:g}{chosen}")
    fc = results.get("final_forecast_coverage", {})
    if fc:
        lines.append("\n## Final forecasts exported (inference partition)\n")
        lines.append(f"Candidate arm `{m['candidate_arm']}` — {m['candidate_rationale']}\n")
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
    features_by_arm = {
        ARM_SERVED: {p: info["features"] for p, info in served.items()},
        ARM_RECENT: {p: list(RECENT_PRODUCTION_FEATURES) for p in served},
    }
    features_by_position = features_by_arm[ARM_CANDIDATE]

    pulled_at = datetime.now(timezone.utc)
    weekly = pull_weekly_stats(PULL_SEASONS)
    snapshot_bytes = gzip.compress(weekly.to_csv(index=False).encode("utf-8"))
    snapshot_sha = _sha256_bytes(snapshot_bytes)
    import nflreadpy

    # A missing player-season is an OBSERVED absence only if the source is complete,
    # unique and fully scored. Refuses otherwise; the facts go into the manifest.
    weekly, dropped = drop_unattributed_zero_rows(weekly)
    source_validation = {**validate_weekly_source(weekly, seasons=PULL_SEASONS), **dropped}
    outcomes = season_outcomes(weekly, scope=SCOPE, validation=source_validation)
    outcomes_all = season_outcomes(weekly, scope="ALL", validation=source_validation)
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
    for position in features_by_position:
        k = int(PRIMARY_NDCG_K.get(position, 12))
        pos_df = df[df["position"] == position]
        historical[position] = {}
        for j in HORIZONS:
            historical[position][f"year{j}"] = {}
            for arm in (ARM_SERVED, ARM_RECENT):
                feats = features_by_arm[arm][position]
                evaluator = evaluate_horizon_policy if arm == ARM_CANDIDATE else evaluate_horizon
                ev, preds = evaluator(
                    pos_df, feats, horizon=j, test_seasons=TEST_SEASONS_BY_HORIZON[j], k=k,
                    draws=args.draws, seed=args.seed, min_train_rows=args.min_train_rows,
                )
                historical[position][f"year{j}"][arm] = ev
                preds.insert(0, "arm", arm)
                preds.insert(0, "horizon", j)
                prediction_frames.append(preds)
                print(f"  {position} year{j} {arm}: evaluated {ev['evaluated_test_seasons']}")

    exported: dict[str, pd.DataFrame] = {}
    fits: dict[str, Any] = {}
    for arm, per_position in features_by_arm.items():
        frame, arm_fits = final_forecasts(
            df, per_position, horizons=HORIZONS, inference_season=INFERENCE_SEASON,
            last_complete_season=LAST_COMPLETE_SEASON,
            fitter=fit_policy if arm == ARM_CANDIDATE else fit_horizon,
        )
        frame.insert(3, "forecast_cutoff", f"post-{INFERENCE_SEASON}-season")
        frame.insert(4, "arm", arm)
        exported[arm] = frame
        fits[arm] = arm_fits
    forecasts = exported[ARM_CANDIDATE]
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
    provenance = collect_provenance(files, extra={
        "git_head": _git("rev-parse", "HEAD"), "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "worktree": json.loads((ROOT / ".dg-worktree.json").read_text()) if (ROOT / ".dg-worktree.json").exists() else None,
        "source": source, "finished_utc": datetime.now(timezone.utc).isoformat(),
    })
    inputs = {f"{label}_sha256": entry["sha256"] for label, entry in provenance["files"].items()}
    inputs["weekly_stats_sha256"] = snapshot_sha
    manifest_inputs = dict(inputs)
    selection_policy = {
        "space": list(POLICY_SPACE), "criterion": dict(SELECTION_CRITERION),
        "where": "per position, horizon and quantity on closed inner folds inside the training window; "
                 "applied by the same function final scoring calls",
        "chosen": {pos: {h: meta["policy_by_quantity"] for h, meta in per.items()}
                   for pos, per in fits[ARM_CANDIDATE].items()},
    }
    manifest = build_manifest(
        horizons=HORIZONS, inference_season=INFERENCE_SEASON, last_complete_season=LAST_COMPLETE_SEASON,
        scope=SCOPE, source=source, git_head=_git("rev-parse", "HEAD"),
        features_by_arm=features_by_arm, inputs=manifest_inputs, source_validation=source_validation,
        selection_policy=selection_policy,
        population=f"every row of the {INFERENCE_SEASON} feature partition of the training file "
                   f"(players with >= 4 stat-row games in {INFERENCE_SEASON}, rostered or not)",
    )
    results = {
        "run_id": run_id, "started_utc": started.isoformat(), "manifest": manifest,
        "alignment_check": alignment, "historical": historical, "final_fits": fits,
        "final_forecast_coverage": coverage,
        "config": {"draws": args.draws, "seed": args.seed, "min_train_rows": args.min_train_rows,
                   "test_seasons_by_horizon": TEST_SEASONS_BY_HORIZON, "arms": [ARM_SERVED, ARM_RECENT],
                   "candidate_arm": ARM_CANDIDATE, "features_by_arm": features_by_arm},
    }
    historical_predictions = pd.concat(prediction_frames, ignore_index=True)
    report = render_report(results)
    written = write_run_artifact(out_dir, results, historical_predictions, provenance=provenance, report_md=report)
    for arm, frame in exported.items():
        (out_dir / EXPORTS[arm]).write_text(frame.to_csv(index=False))
    (out_dir / "weekly_stats_snapshot.csv.gz").write_bytes(snapshot_bytes)
    (out_dir / "predictions.csv").rename(out_dir / "historical_predictions.csv")
    # Output hashes are known only now; the manifest is written LAST, validated first.
    manifest["outputs"] = {
        name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest()
        for name in [*EXPORTS.values(), "results.json", "historical_predictions.csv", "weekly_stats_snapshot.csv.gz"]
    }
    manifest["outputs_sha256"] = dict(manifest["outputs"])
    manifest["evaluation_status"] = evaluation_status(
        {"historical": {p: {h: arms[ARM_CANDIDATE] for h, arms in per.items()} for p, per in historical.items()}},
        historical_predictions, arm_key=ARM_CANDIDATE,
    )
    validate_manifest(manifest)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {written + list(EXPORTS.values()) + ['manifest.json', 'weekly_stats_snapshot.csv.gz']} to {out_dir}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
