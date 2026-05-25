#!/usr/bin/env python3.14
"""Generate ModelCard and CalibrationReport artifacts from BacktestResult runs.

Reads the latest BacktestResult per position, optionally joins the per-fold
prediction log CSV for calibration deciles and subgroup slices, then writes:
  app/data/backtest/model_cards/{POS}_model_card.json
  app/data/backtest/model_cards/{POS}_calibration_report.json

Usage:
    .venv/bin/python3.14 scripts/generate_model_cards.py --position WR
    .venv/bin/python3.14 scripts/generate_model_cards.py --all
"""
from __future__ import annotations

import argparse
import math
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd

from src.dynasty_genius.eval.backtest_artifact import BacktestResult
from src.dynasty_genius.eval.backtest_metrics import (
    compute_ece,
    compute_subgroup_metrics,
)
from src.dynasty_genius.eval.model_card import (
    CalibrationDecile,
    CalibrationReport,
    ModelCard,
    ModelCardMetrics,
    ModelCardSubgroup,
)

RUNS_DIR = Path("app/data/backtest/runs")
OUTPUT_DIR = Path("app/data/backtest/model_cards")
VALID_POSITIONS = ("QB", "RB", "WR", "TE")


# ── Position-specific authored sections ───────────────────────────────────────

_TEMPLATES: dict[str, dict] = {
    "QB": {
        "intended_use": (
            "Forecast 2-year average PPG for active NFL quarterbacks. "
            "Dynasty trade decision support in Superflex PPR (12-team, 2QB) leagues."
        ),
        "out_of_scope_uses": [
            "Single-season redraft start/sit decisions",
            "Keeper cap valuations without manager review",
        ],
        "ethical_considerations": (
            "Decision aid only. Market overlay (FantasyCalc) is a post-scoring reference — "
            "it is not a training input and must not be treated as ground truth. "
            "Model outputs carry uncertainty bands that must be exposed to end users."
        ),
        "caveats": [
            "Sample size: ~43–49 QB rows per fold. Folds involving roster turnover years carry elevated noise.",
            "Mobile QB rushing floors depreciate sharply after age 33. Model does not encode a hard cliff — "
            "age is a continuous feature — but predictions near this threshold carry higher uncertainty.",
            "Superflex format premiums are not modeled directly. Value-above-replacement comparisons across "
            "positions require a separate normalization layer (deferred to DVS spec).",
        ],
        "known_failure_modes": [
            "Injury-year outliers distort PPG labels for players who missed significant games. "
            "The model has no games-played filter in v2.",
            "Historical regime shifts (2020 COVID, rules changes) can widen fold-to-fold RMSE.",
        ],
    },
    "RB": {
        "intended_use": (
            "Forecast 2-year average PPG for active NFL running backs. "
            "Dynasty trade decision support in Superflex PPR (12-team, 2QB) leagues."
        ),
        "out_of_scope_uses": [
            "Single-season redraft start/sit decisions",
            "Keeper cap valuations without manager review",
        ],
        "ethical_considerations": (
            "Decision aid only. Market overlay (FantasyCalc) is a post-scoring reference — "
            "it is not a training input and must not be treated as ground truth. "
            "Model outputs carry uncertainty bands that must be exposed to end users."
        ),
        "caveats": [
            "RB age cliff begins ~26. The model encodes age as a continuous feature; users should "
            "interpret high-confidence predictions for players ≥26 with increased skepticism.",
            "Role volatility (committee backfields, mid-season usage shifts) creates floor risk "
            "not captured in PPG-based training labels.",
            "Weighted Opportunity and High-Value Touches are not yet in the feature set. "
            "See Phase 13 research brief.",
        ],
        "known_failure_modes": [
            "Low-snap, high-efficiency backs on poor offenses may be undervalued by a PPG-trained label.",
            "Committee backs show high variance that PPG smooths over.",
        ],
    },
    "WR": {
        "intended_use": (
            "Forecast 2-year average PPG for active NFL wide receivers. "
            "Dynasty trade decision support in Superflex PPR (12-team, 2QB) leagues."
        ),
        "out_of_scope_uses": [
            "Single-season redraft start/sit decisions",
            "Keeper cap valuations without manager review",
        ],
        "ethical_considerations": (
            "Decision aid only. Market overlay (FantasyCalc) is a post-scoring reference — "
            "it is not a training input and must not be treated as ground truth. "
            "Model outputs carry uncertainty bands that must be exposed to end users."
        ),
        "caveats": [
            "Age cliff begins ~29. WR prime window is broad (25–29), making mid-career predictions most reliable.",
            "Quarterback volatility (team changes, QB injuries) creates landing-spot risk that "
            "YPRR-adjacent features cannot capture in a pure efficiency model.",
        ],
        "known_failure_modes": [
            "Slot vs. outside receiver distinctions are not explicitly modeled. A slot receiver "
            "moving to a vertical role will be mispredicted until the new role PPG accumulates.",
        ],
    },
    "TE": {
        "intended_use": "EXPERIMENTAL — not for trade decisions. Diagnostic only.",
        "out_of_scope_uses": [
            "Any trade decision",
            "Dynasty value ranking",
            "Trust Surface display without explicit EXPERIMENTAL label",
        ],
        "ethical_considerations": (
            "TE model failed Phase 10/11 promotion gates (0/3). This card documents failure modes. "
            "Do not use outputs for decisions."
        ),
        "caveats": [
            "TE model failed Phase 10/11 promotion gates (0/3). Alpha=1.0 indicates severe overfitting; "
            "model cannot beat a naive prior-PPG baseline.",
            "Role heterogeneity (inline blocker vs. receiving specialist) is not segmented. "
            "A single model trained on mixed archetypes cannot capture either reliably.",
            "Sample size is the tightest of any position: ~30–35 TE starters per fold.",
        ],
        "known_failure_modes": [
            "TD variance dominates short-window PPG, making calibration unstable. "
            "The model's calibration_by_decile will show large residuals.",
            "Draft capital selects for inline blockers who have zero fantasy utility. "
            "Model trained on overall_rank overweights pick number for non-fantasy TEs.",
        ],
    },
}


# ── Core generator ────────────────────────────────────────────────────────────

def find_latest_backtest_result(position: str, runs_dir: Path) -> Optional[Path]:
    """Return the most recently written backtest_result_{position}.json, or None."""
    candidates = list(runs_dir.glob(f"*/backtest_result_{position}.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _calibration_from_predictions(
    pred_df: pd.DataFrame,
    backtest_run_id: str,
    position: str,
) -> tuple[list[CalibrationDecile], float]:
    """Compute 10 calibration deciles and ECE from pooled prediction log."""
    pred_df = pred_df.dropna(subset=["predicted_ppg", "realized_ppg"]).copy()
    if len(pred_df) < 10:
        return [], float("nan")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pred_df["_decile"] = pd.qcut(pred_df["predicted_ppg"], q=10, labels=False, duplicates="drop")

    deciles: list[CalibrationDecile] = []
    for d_idx in sorted(pred_df["_decile"].dropna().unique()):
        group = pred_df[pred_df["_decile"] == d_idx]
        pred_mean = float(group["predicted_ppg"].mean())
        obs_mean = float(group["realized_ppg"].mean())
        n = len(group)
        deciles.append(CalibrationDecile(
            decile=int(d_idx) + 1,
            predicted_mean=pred_mean,
            observed_mean=obs_mean,
            n=n,
            residual_mean=obs_mean - pred_mean,
        ))

    ece = compute_ece([(d.predicted_mean, d.observed_mean, d.n) for d in deciles])
    return deciles, ece


def _age_subgroups(pred_df: pd.DataFrame) -> list[ModelCardSubgroup]:
    """Compute subgroup metrics per age bucket from prediction log."""
    col = "age_at_feature_season"
    if col not in pred_df.columns or pred_df[col].isna().all():
        return []

    buckets = [
        ("age_under_26", pred_df[col] < 26),
        ("age_26_to_28", (pred_df[col] >= 26) & (pred_df[col] <= 28)),
        ("age_29_plus", pred_df[col] > 28),
    ]
    subgroups: list[ModelCardSubgroup] = []
    for label, mask in buckets:
        group = pred_df[mask].dropna(subset=["predicted_ppg", "realized_ppg"])
        if len(group) == 0:
            continue
        m = compute_subgroup_metrics(
            group["predicted_ppg"].tolist(),
            group["realized_ppg"].tolist(),
        )
        tau = m["kendall_tau"]
        rmse = m["rmse"]
        subgroups.append(ModelCardSubgroup(
            label=label,
            n=int(m["n"]),
            rmse=float(rmse) if rmse is not None else float("nan"),
            kendall_tau=float(tau) if tau is not None else float("nan"),
        ))
    return subgroups


def generate_card_for_position(
    position: str,
    runs_dir: Path = RUNS_DIR,
    output_dir: Path = OUTPUT_DIR,
) -> tuple[ModelCard, CalibrationReport]:
    """Generate ModelCard + CalibrationReport for position.

    Reads the latest BacktestResult artifact. If a predictions CSV exists in
    the same run directory, uses it for calibration deciles and subgroups.
    Writes both JSON artifacts to output_dir.
    """
    result_path = find_latest_backtest_result(position, runs_dir)
    if result_path is None:
        raise FileNotFoundError(
            f"No backtest_result_{position}.json found under {runs_dir}. "
            "Run scripts/run_backtest.py first."
        )

    result = BacktestResult.load(result_path)
    run_dir = result_path.parent

    # Load predictions CSV if available
    pred_csv = run_dir / f"predictions_{position}.csv"
    pred_df: Optional[pd.DataFrame] = None
    if pred_csv.exists():
        try:
            pred_df = pd.read_csv(pred_csv)
        except Exception as e:
            warnings.warn(f"Could not load predictions CSV for {position}: {e}")

    # Calibration deciles and ECE
    calibration_deciles: list[CalibrationDecile] = []
    ece_value: Optional[float] = None
    if pred_df is not None:
        deciles, ece = _calibration_from_predictions(
            pred_df, str(result.run_id), position
        )
        calibration_deciles = deciles
        ece_value = None if (math.isnan(ece) if isinstance(ece, float) else False) else ece

    # Subgroup slices
    subgroups: list[ModelCardSubgroup] = []
    if pred_df is not None:
        subgroups = _age_subgroups(pred_df)

    # Fold-level metrics
    folds = result.folds
    tau_per_fold = [f.kendall_tau for f in folds]
    rho_per_fold = [f.spearman_rho for f in folds]
    rmse_per_fold = [f.rmse for f in folds]
    tau_mean = sum(tau_per_fold) / len(tau_per_fold) if tau_per_fold else float("nan")
    rho_mean = sum(rho_per_fold) / len(rho_per_fold) if rho_per_fold else float("nan")
    rmse_mean = result.rmse_stability.rmse_mean

    gate = result.promotion_gate
    ndcg_model_vals = [f.ndcg_at_24_model for f in folds if f.ndcg_at_24_model is not None]
    ndcg_market_vals = [f.ndcg_at_24_market for f in folds if f.ndcg_at_24_market is not None]

    metrics = ModelCardMetrics(
        rmse_mean=rmse_mean,
        rmse_per_fold=rmse_per_fold,
        kendall_tau_mean=tau_mean,
        kendall_tau_per_fold=tau_per_fold,
        spearman_rho_mean=rho_mean,
        spearman_rho_per_fold=rho_per_fold,
        ece=ece_value,
        ndcg_at_24_model_mean=(sum(ndcg_model_vals) / len(ndcg_model_vals)) if ndcg_model_vals else None,
        ndcg_at_24_market_mean=(sum(ndcg_market_vals) / len(ndcg_market_vals)) if ndcg_market_vals else None,
        g1_pass=gate.g1_rank_correlation_pass,
        g2_pass=gate.g2_rmse_stability_pass,
        g3_pass=gate.g3_market_superiority_pass,
        g4_pass=gate.g4_divergence_validity_pass,
        overall_grade=gate.overall_grade,
    )

    tmpl = _TEMPLATES[position]
    fold_table = "\n".join(
        f"  Fold {f.fold_index}: test_year={f.test_year}, "
        f"n_train={f.n_train}, n_test={f.n_test}, tau={f.kendall_tau:.3f}"
        for f in folds
    )
    training_years_all = sorted({y for f in folds for y in f.train_years})

    card = ModelCard(
        generated_at=datetime.now(timezone.utc),
        position=position,  # type: ignore[arg-type]
        backtest_run_id=str(result.run_id),
        git_sha=result.git_sha,
        model_version=result.model_version,
        model_artifact_hash=result.model_artifact_hash,
        ridge_alpha=result.ridge_alpha,
        training_window=f"{min(training_years_all)}–{max(training_years_all)} (expanding; {len(folds)} folds)",
        feature_list=sorted(folds[0].train_years.__class__.__name__ and
                           list({col for col in (pred_df.columns if pred_df is not None else [])
                                 if col not in {"player_id", "position", "fold_index",
                                                "feature_season", "predicted_ppg",
                                                "realized_ppg", "model_rank", "residual",
                                                "age_at_feature_season", "draft_round"}})
                            or ["see_engine_b_features_v2.csv"]),
        retrain_mode=result.retrain_mode,
        intended_use=tmpl["intended_use"],
        out_of_scope_uses=tmpl["out_of_scope_uses"],
        relevant_factors=["position", "age", "sample_size", "draft_capital"],
        evaluation_factors=["age_bucket", "draft_round_bucket"],
        metrics=metrics,
        evaluation_data=fold_table,
        training_data="app/data/training/engine_b_features_v2.csv",
        subgroup_results=subgroups,
        ethical_considerations=tmpl["ethical_considerations"],
        caveats=tmpl["caveats"],
        known_failure_modes=tmpl["known_failure_modes"],
        is_experimental=(position == "TE"),
    )

    calibration = CalibrationReport(
        position=position,
        backtest_run_id=str(result.run_id),
        ece=ece_value if ece_value is not None else float("nan"),
        deciles=calibration_deciles,
        note=None if calibration_deciles else "predictions CSV unavailable; deciles not computed",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    card.save(output_dir / f"{position}_model_card.json")
    calibration.save(output_dir / f"{position}_calibration_report.json")

    return card, calibration


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate ModelCard artifacts.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--position", choices=list(VALID_POSITIONS))
    target.add_argument("--all", action="store_true")
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    positions = VALID_POSITIONS if args.all else (args.position,)
    for pos in positions:
        print(f"Generating model card for {pos}...", flush=True)
        try:
            card, report = generate_card_for_position(
                pos,
                runs_dir=args.runs_dir,
                output_dir=args.output_dir,
            )
            ece_str = f"{report.ece:.4f}" if not math.isnan(report.ece) else "n/a"
            print(
                f"  {pos}: grade={card.metrics.overall_grade}, "
                f"tau={card.metrics.kendall_tau_mean:.3f}, "
                f"ece={ece_str}, "
                f"subgroups={len(card.subgroup_results)}"
            )
        except FileNotFoundError as e:
            print(f"  {pos}: SKIPPED — {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
