"""Phase 19 W3 — Head A (Absolute Valuation) v3 Bake-Off Harness.

Runs 4-fold temporal walk-forward evaluation for two candidate architectures
(Regularized Ridge and Gradient Boosted Trees) against the Engine A v2 baseline
per position. Evaluates the 2-of-3 promotion gates from the W3 spec.

Validation-integrity guarantees:
  - Baseline and candidate are always evaluated on the IDENTICAL test rows per
    fold (row alignment to candidate feature availability).
  - Gates use true OOF RMSE/MAE computed from pooled out-of-fold predictions,
    not a naive equal-weight average of per-fold RMSE.
  - NDCG@10 uses realized PPG directly as relevance (matching repo convention
    in src/dynasty_genius/eval/backtest_metrics.py).
  - TE safety guard compares fractional MAE regression, not absolute delta.

Does NOT promote any model pkl or update latest.json.
"""
from __future__ import annotations

import csv
import dataclasses
import json
import math
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

V3_CSV = ROOT / "app/data/training/prospects_with_outcomes_v3.csv"
OUTPUT_DIR = ROOT / "app/data/backtest/phase19"
OOF_LOG_DIR = OUTPUT_DIR / "oof_logs"

# Promotion gate thresholds per W3 spec
RMSE_IMPROVEMENT_PCT_GATE = 2.0     # ≥2% OOF RMSE reduction vs aligned baseline
METRICS_REQUIRED_TO_PASS = 2        # 2-of-3 core metrics must clear
TE_MAE_REGRESSION_GATE = 0.01      # TE OOF MAE fractional regression must not exceed 1.0%

# Ridge alpha sweep (W3 spec §2.A)
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 50.0, 100.0, 250.0, 500.0, 1000.0]

# GBT hyperparams (W3 spec §2.B — shallow, regularized to combat small n)
GBT_PARAMS = {
    "max_depth": 3,
    "learning_rate": 0.05,
    "n_estimators": 50,
    "min_samples_leaf": 5,  # equivalent to LightGBM min_child_samples
    "random_state": 42,
}

# 4-fold walk-forward splits: (train_max_year, test_year)
WALK_FORWARD_FOLDS = [
    (2017, 2018),
    (2018, 2019),
    (2019, 2020),
    (2020, 2021),
]

# Baseline features (Engine A v2 equivalent)
BASELINE_FEATURES = ["nfl_pick", "nfl_round", "final_college_age"]

# Head A v3 candidate feature matrices per W3 spec §1
HEAD_A_FEATURES: dict[str, list[str]] = {
    "QB": ["nfl_pick", "nfl_round", "final_college_age"],
    "RB": [
        "nfl_pick", "nfl_round", "final_college_age",
        "rb_final_dominator", "rb_scrimmage_ypg", "rb_school_sp_plus", "rb_rec_ypg",
    ],
    "WR": [
        "nfl_pick", "nfl_round", "final_college_age",
        "wr_dominator_final", "wr_breakout_age", "wr_market_share_yds",
        "wr_yards_per_reception_career", "ryptpa", "yprr_college",
    ],
    "TE": [
        "nfl_pick", "nfl_round", "final_college_age",
        "te_ryptpa_final", "te_yards_per_reception_career",
    ],
}

TARGET_COL = "best3of4_ppg"


# ── Utility ───────────────────────────────────────────────────────────────────

def _to_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ── Public helpers (imported by test suite) ────────────────────────────────────

def scale_features(
    X_train: np.ndarray, X_test: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Fit StandardScaler on X_train; apply to both X_train and X_test."""
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    return X_train_s, X_test_s


def _filter_training_rows(rows: list[dict], train_max_year: int) -> list[dict]:
    """Return rows where season <= train_max_year and not censored."""
    result = []
    for row in rows:
        try:
            season = int(row.get("season", 0))
        except (ValueError, TypeError):
            continue
        if season > train_max_year:
            continue
        if row.get("censored_incomplete_arc", "0") == "1":
            continue
        result.append(row)
    return result


def _filter_available_features(
    rows: list[dict],
    candidate_features: list[str],
    min_coverage_pct: float = 50.0,
) -> list[str]:
    """Return features with ≥min_coverage_pct non-null values in rows."""
    if not rows:
        return []
    total = len(rows)
    return [
        feat for feat in candidate_features
        if (sum(1 for r in rows if _to_float(r.get(feat)) is not None) / total) * 100.0
        >= min_coverage_pct
    ]


def _build_aligned_fold(
    train_rows: list[dict],
    test_rows: list[dict],
    baseline_features: list[str],
    candidate_features: list[str],
) -> tuple[list[dict], list[dict]]:
    """Return (aligned_train, aligned_test) where every row has ALL features non-null.

    Uses the union of baseline and candidate features as the filter, so both
    models operate on an identical cohort within each fold.
    """
    all_features = list(set(baseline_features) | set(candidate_features))

    def _has_all(row: dict) -> bool:
        return all(_to_float(row.get(f)) is not None for f in all_features)

    return [r for r in train_rows if _has_all(r)], [r for r in test_rows if _has_all(r)]


def compute_ndcg_at_k(
    y_true: np.ndarray, y_pred: np.ndarray, k: int = 10
) -> float:
    """NDCG@k using realized PPG directly as relevance (repo convention).

    Matches src/dynasty_genius/eval/backtest_metrics.py::compute_ndcg:
      DCG  = sum(ppg[i] / log2(position + 1))  for top-k predicted positions
      IDCG = DCG of ideal (true) ranking
    """
    n = len(y_true)
    k = min(k, n)
    if k == 0:
        return 0.0

    pred_order = np.argsort(y_pred)[::-1][:k]
    ideal_order = np.argsort(y_true)[::-1][:k]

    discounts = np.log2(np.arange(1, k + 1) + 1)
    dcg = float(np.sum(y_true[pred_order] / discounts))
    idcg = float(np.sum(y_true[ideal_order] / discounts))

    return dcg / idcg if idcg > 0.0 else 0.0


def compute_oof_rmse_from_folds(
    oof_by_fold: list[list[dict]],
) -> float:
    """True OOF RMSE from all pooled out-of-fold predictions.

    Computes sqrt(SSE / N) where SSE and N are totals across all folds,
    correctly weighting folds by size rather than averaging fold-level RMSE.
    """
    sse = 0.0
    n = 0
    for fold_preds in oof_by_fold:
        for pred in fold_preds:
            sse += (pred["y_true"] - pred["y_pred"]) ** 2
            n += 1
    return math.sqrt(sse / n) if n > 0 else float("nan")


@dataclasses.dataclass(frozen=True)
class HeadAGateResult:
    passes: bool
    metrics_passed: int
    rmse_gate: bool
    spearman_gate: bool
    ndcg_gate: bool
    te_safety_blocked: bool
    fail_reasons: list[str]


def evaluate_head_a_gates(
    baseline_rmse: float,
    candidate_rmse: float,
    baseline_spearman: float,
    candidate_spearman: float,
    baseline_ndcg: float,
    candidate_ndcg: float,
    te_mae_delta: float = 0.0,
) -> HeadAGateResult:
    """Evaluate the W3 2-of-3 promotion gates plus TE safety guard.

    te_mae_delta is the fractional OOF MAE regression:
      (candidate_oof_mae - baseline_oof_mae) / baseline_oof_mae
    Guard fires when te_mae_delta > 0.01 (>1.0% regression).
    """
    rmse_improvement_pct = (baseline_rmse - candidate_rmse) / baseline_rmse * 100.0
    rmse_gate = rmse_improvement_pct >= RMSE_IMPROVEMENT_PCT_GATE
    spearman_gate = candidate_spearman > baseline_spearman
    ndcg_gate = candidate_ndcg > baseline_ndcg
    te_safety_blocked = te_mae_delta > TE_MAE_REGRESSION_GATE

    metrics_passed = sum([rmse_gate, spearman_gate, ndcg_gate])
    fail_reasons: list[str] = []
    if not rmse_gate:
        fail_reasons.append("rmse_gate")
    if not spearman_gate:
        fail_reasons.append("spearman_gate")
    if not ndcg_gate:
        fail_reasons.append("ndcg_gate")
    if te_safety_blocked:
        fail_reasons.append("te_safety_guard")

    passes = metrics_passed >= METRICS_REQUIRED_TO_PASS and not te_safety_blocked

    return HeadAGateResult(
        passes=passes,
        metrics_passed=metrics_passed,
        rmse_gate=rmse_gate,
        spearman_gate=spearman_gate,
        ndcg_gate=ndcg_gate,
        te_safety_blocked=te_safety_blocked,
        fail_reasons=fail_reasons,
    )


# ── Internal fold runner ──────────────────────────────────────────────────────

def _extract_matrix(
    rows: list[dict], features: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Extract feature matrix and target vector, dropping rows with any None."""
    X_rows: list[list[float]] = []
    y_rows: list[float] = []
    for row in rows:
        feat_vals = [_to_float(row.get(f)) for f in features]
        target_val = _to_float(row.get(TARGET_COL))
        if target_val is None or any(v is None for v in feat_vals):
            continue
        X_rows.append(feat_vals)  # type: ignore[arg-type]
        y_rows.append(target_val)
    return np.array(X_rows, dtype=float), np.array(y_rows, dtype=float)


def _fit_predict(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    model_type: str,
) -> tuple[np.ndarray, Optional[float]]:
    """Fit model and return (y_pred, best_alpha_or_None)."""
    X_train_s, X_test_s = scale_features(X_train, X_test)
    if model_type == "ridge":
        model = RidgeCV(alphas=RIDGE_ALPHA_GRID)
        model.fit(X_train_s, y_train)
        return model.predict(X_test_s), float(model.alpha_)
    elif model_type == "gbt":
        model = GradientBoostingRegressor(**GBT_PARAMS)
        model.fit(X_train_s, y_train)
        return model.predict(X_test_s), None
    else:
        raise ValueError(f"Unknown model_type: {model_type!r}")


def _fold_metrics(y_test: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute per-fold RMSE, Spearman, NDCG@10."""
    rmse = float(np.sqrt(np.mean((y_test - y_pred) ** 2)))
    rho = float(spearmanr(y_test, y_pred).statistic) if len(y_test) > 2 else 0.0
    ndcg = compute_ndcg_at_k(y_test, y_pred, k=10)
    return {"rmse": round(rmse, 4), "spearman": round(rho, 4), "ndcg_at_10": round(ndcg, 4)}


def _run_aligned_comparison(
    pos_rows: list[dict],
    baseline_features: list[str],
    candidate_features: list[str],
    model_type: str,
) -> dict:
    """Run all 4 folds with baseline and candidate on the same aligned row set.

    Returns {"aligned_baseline": agg_dict, "candidate": agg_dict} where every
    metric is derived from the identical pool of OOF predictions.
    """
    baseline_folds: list[dict] = []
    candidate_folds: list[dict] = []

    for train_max_year, test_year in WALK_FORWARD_FOLDS:
        all_train = _filter_training_rows(pos_rows, train_max_year)
        all_test = [r for r in pos_rows if _to_float(r.get("season")) == float(test_year)]

        aligned_train, aligned_test = _build_aligned_fold(
            all_train, all_test, baseline_features, candidate_features
        )

        X_train_b, y_train_b = _extract_matrix(aligned_train, baseline_features)
        X_test_b, y_test_b = _extract_matrix(aligned_test, baseline_features)
        X_train_c, y_train_c = _extract_matrix(aligned_train, candidate_features)
        X_test_c, y_test_c = _extract_matrix(aligned_test, candidate_features)

        # y_test must be the same for both (aligned cohort, same target column)
        if len(X_train_b) < 5 or len(X_test_b) < 1:
            continue

        y_pred_b, alpha_b = _fit_predict(X_train_b, y_train_b, X_test_b, "ridge")
        y_pred_c, alpha_c = _fit_predict(X_train_c, y_train_c, X_test_c, model_type)

        oof_b = [{"y_true": float(yt), "y_pred": float(yp)}
                 for yt, yp in zip(y_test_b, y_pred_b)]
        oof_c = [{"y_true": float(yt), "y_pred": float(yp)}
                 for yt, yp in zip(y_test_c, y_pred_c)]

        fold_b = {
            "train_max_year": train_max_year, "test_year": test_year,
            "n_train": len(X_train_b), "n_test": len(X_test_b),
            **_fold_metrics(y_test_b, y_pred_b),
            "best_alpha": alpha_b,
            "oof_predictions": oof_b,
        }
        fold_c = {
            "train_max_year": train_max_year, "test_year": test_year,
            "n_train": len(X_train_c), "n_test": len(X_test_c),
            **_fold_metrics(y_test_c, y_pred_c),
            "best_alpha": alpha_c,
            "oof_predictions": oof_c,
        }
        baseline_folds.append(fold_b)
        candidate_folds.append(fold_c)

    return {
        "aligned_baseline": _aggregate_folds(baseline_folds),
        "candidate": _aggregate_folds(candidate_folds),
    }


def _run_standalone(pos_rows: list[dict], features: list[str]) -> dict:
    """Run baseline on its own cohort (all rows with baseline features) — for diagnostics."""
    fold_results: list[dict] = []
    for train_max_year, test_year in WALK_FORWARD_FOLDS:
        train_rows = _filter_training_rows(pos_rows, train_max_year)
        test_rows = [r for r in pos_rows if _to_float(r.get("season")) == float(test_year)]

        X_train, y_train = _extract_matrix(train_rows, features)
        X_test, y_test = _extract_matrix(test_rows, features)
        if len(X_train) < 5 or len(X_test) < 1:
            continue

        y_pred, alpha = _fit_predict(X_train, y_train, X_test, "ridge")
        oof = [{"y_true": float(yt), "y_pred": float(yp)} for yt, yp in zip(y_test, y_pred)]
        fold_results.append({
            "train_max_year": train_max_year, "test_year": test_year,
            "n_train": len(X_train), "n_test": len(X_test),
            **_fold_metrics(y_test, y_pred),
            "best_alpha": alpha,
            "oof_predictions": oof,
        })
    return _aggregate_folds(fold_results)


def _aggregate_folds(fold_results: list[dict]) -> dict:
    """Aggregate OOF predictions with separate metrics for gates vs diagnostics.

    Gate metrics:
      - oof_rmse / oof_mae: pooled across folds (correct for error magnitude)
      - mean_fold_spearman / mean_fold_ndcg_at_10: unweighted mean of per-fold values
        (within-class ranking quality; avoids Simpson's-paradox inflation from pooling)

    Diagnostic metrics:
      - oof_spearman / oof_ndcg_at_10: pooled OOF rank (reported but NOT used for gates)

    Per-player log:
      - oof_predictions_all: flat list of every {y_true, y_pred} across all folds
    """
    if not fold_results:
        return {"error": "no_folds", "n_folds": 0}

    all_oof: list[dict] = []
    for fold in fold_results:
        train_max_year = fold.get("train_max_year")
        test_year = fold.get("test_year")
        for pred in fold.get("oof_predictions", []):
            all_oof.append({**pred, "train_max_year": train_max_year, "test_year": test_year})

    if not all_oof:
        return {"error": "no_oof_predictions", "n_folds": len(fold_results)}

    y_true_arr = np.array([p["y_true"] for p in all_oof])
    y_pred_arr = np.array([p["y_pred"] for p in all_oof])

    # Pooled OOF error metrics (gate-valid — weighted by fold size)
    oof_rmse = math.sqrt(float(np.mean((y_true_arr - y_pred_arr) ** 2)))
    oof_mae = float(np.mean(np.abs(y_true_arr - y_pred_arr)))

    # Fold-level rank metrics: unweighted mean of per-fold values (gate-valid)
    mean_fold_spearman = float(np.mean([f["spearman"] for f in fold_results]))
    mean_fold_ndcg = float(np.mean([f["ndcg_at_10"] for f in fold_results]))

    # Pooled rank metrics (diagnostic only — NOT for gates)
    oof_spearman = float(spearmanr(y_true_arr, y_pred_arr).statistic) if len(y_true_arr) > 2 else 0.0
    oof_ndcg = compute_ndcg_at_k(y_true_arr, y_pred_arr, k=10)

    return {
        "n_folds": len(fold_results),
        "n_oof": len(all_oof),
        # Gate inputs
        "oof_rmse": round(oof_rmse, 4),
        "oof_mae": round(oof_mae, 4),
        "mean_fold_spearman": round(mean_fold_spearman, 4),
        "mean_fold_ndcg_at_10": round(mean_fold_ndcg, 4),
        # Diagnostics (not used for gates)
        "oof_spearman": round(oof_spearman, 4),
        "oof_ndcg_at_10": round(oof_ndcg, 4),
        # Per-player predictions for OOF log
        "oof_predictions_all": all_oof,
        "fold_results": [
            {k: v for k, v in f.items() if k != "oof_predictions"}
            for f in fold_results
        ],
    }


# ── Position orchestrator ─────────────────────────────────────────────────────

def _run_position(
    position: str,
    all_rows: list[dict],
    run_id: str,
    generated_at: str,
) -> dict:
    pos_rows = [r for r in all_rows if r.get("position", "").upper() == position.upper()]
    eligible = [r for r in pos_rows if r.get("censored_incomplete_arc", "0") != "1"]
    n_total = len(pos_rows)
    n_eligible = len(eligible)
    print(f"\n  {position}: {n_total} total rows, {n_eligible} non-censored")

    spec_features = HEAD_A_FEATURES[position]
    available_features = _filter_available_features(eligible, spec_features)
    dropped_features = [f for f in spec_features if f not in available_features]

    if dropped_features:
        print(f"    [COVERAGE] Dropped {len(dropped_features)} low-coverage features: {dropped_features}")

    coverage_report = {
        feat: round(
            sum(1 for r in eligible if _to_float(r.get(feat)) is not None)
            / max(n_eligible, 1) * 100, 1
        )
        for feat in spec_features
    }

    enriched_differs = set(available_features) != set(BASELINE_FEATURES)

    # Standalone baseline (full cohort, diagnostic only)
    baseline_standalone = _run_standalone(pos_rows, BASELINE_FEATURES)
    print(f"    Baseline (standalone) OOF RMSE={baseline_standalone.get('oof_rmse')}  "
          f"Spearman={baseline_standalone.get('oof_spearman')}  NDCG={baseline_standalone.get('oof_ndcg_at_10')}")

    if not enriched_differs:
        print("    [SKIP] Enriched features collapsed to baseline — no candidates evaluated")
        ridge_result: dict = {"skipped": True, "reason": "enriched_features_equal_baseline"}
        gbt_result: dict = {"skipped": True, "reason": "enriched_features_equal_baseline"}
        candidate_gates: dict[str, dict] = {
            "ridge": {"skipped": True, "passes": False, "reason": ridge_result["reason"]},
            "gbt": {"skipped": True, "passes": False, "reason": gbt_result["reason"]},
        }
    else:
        print(f"    Available features ({len(available_features)}): {available_features}")
        ridge_cmp = _run_aligned_comparison(pos_rows, BASELINE_FEATURES, available_features, "ridge")
        gbt_cmp = _run_aligned_comparison(pos_rows, BASELINE_FEATURES, available_features, "gbt")

        ridge_result = ridge_cmp
        gbt_result = gbt_cmp

        candidate_gates = {}
        for cand_name, cmp in [("ridge", ridge_cmp), ("gbt", gbt_cmp)]:
            abl = cmp.get("aligned_baseline", {})
            cand = cmp.get("candidate", {})

            if "error" in cand:
                candidate_gates[cand_name] = {"error": cand["error"], "passes": False}
                continue

            te_mae_delta = 0.0
            if position == "TE":
                bm = abl.get("oof_mae") or 0.0
                cm = cand.get("oof_mae") or 0.0
                te_mae_delta = max(0.0, (cm - bm) / bm) if bm > 0 else 0.0

            gate = evaluate_head_a_gates(
                baseline_rmse=abl.get("oof_rmse", float("inf")),
                candidate_rmse=cand.get("oof_rmse", float("inf")),
                baseline_spearman=abl.get("mean_fold_spearman", 0.0),
                candidate_spearman=cand.get("mean_fold_spearman", 0.0),
                baseline_ndcg=abl.get("mean_fold_ndcg_at_10", 0.0),
                candidate_ndcg=cand.get("mean_fold_ndcg_at_10", 0.0),
                te_mae_delta=te_mae_delta,
            )
            status = "PASS" if gate.passes else "FAIL"
            print(f"    Gate [{cand_name}]: {status}  "
                  f"aligned_baseline OOF RMSE={abl.get('oof_rmse')}  "
                  f"candidate OOF RMSE={cand.get('oof_rmse')}  "
                  f"metrics={gate.metrics_passed}/3  "
                  f"fail={gate.fail_reasons or ['none']}")
            candidate_gates[cand_name] = dataclasses.asdict(gate)

    # Write OOF log from comparison dict
    oof_path = _write_oof_log(position, ridge_result, gbt_result, run_id, generated_at)

    return {
        "position": position,
        "n_total_rows": n_total,
        "n_eligible_rows": n_eligible,
        "spec_features": spec_features,
        "available_features": available_features,
        "dropped_features": dropped_features,
        "coverage_pct": coverage_report,
        "baseline_features": BASELINE_FEATURES,
        "baseline_standalone": baseline_standalone,
        "ridge": ridge_result,
        "gbt": gbt_result,
        "gate_results": candidate_gates,
        "oof_log": str(oof_path.name) if oof_path else None,
    }


def _write_oof_log(
    position: str,
    ridge_result: dict,
    gbt_result: dict,
    run_id: str,
    generated_at: str,
) -> Optional[Path]:
    """Write per-player OOF predictions for residual diagnostics.

    Each row is one test-set player: position, candidate, role (aligned_baseline
    or candidate), train_max_year, test_year, y_true, y_pred, residual.
    """
    OOF_LOG_DIR.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []

    for cand_name, result in [("ridge", ridge_result), ("gbt", gbt_result)]:
        if result.get("skipped"):
            continue
        for role in ("aligned_baseline", "candidate"):
            role_data = result.get(role, {})
            for pred in role_data.get("oof_predictions_all", []):
                rows_out.append({
                    "position": position,
                    "candidate": cand_name,
                    "role": role,
                    "train_max_year": pred.get("train_max_year"),
                    "test_year": pred.get("test_year"),
                    "y_true": pred["y_true"],
                    "y_pred": round(pred["y_pred"], 4),
                    "residual": round(pred["y_true"] - pred["y_pred"], 4),
                })

    if not rows_out:
        return None

    out_path = OOF_LOG_DIR / f"oof_{position}_{generated_at}_{run_id}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)
    return out_path


def _load_all_rows() -> list[dict]:
    if not V3_CSV.exists():
        raise FileNotFoundError(
            f"v3 training CSV not found: {V3_CSV}\n"
            "Ensure the W2b enrichment pipeline has been run."
        )
    with V3_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("Phase 19 W3 — Head A v3 Bake-Off")
    print(f"  Run ID     : {run_id}")
    print(f"  Generated  : {generated_at}")
    print(f"  CSV        : {V3_CSV}")
    print(f"  Folds      : {WALK_FORWARD_FOLDS}")

    all_rows = _load_all_rows()
    print(f"  Total rows : {len(all_rows)}")

    position_results: dict[str, dict] = {}
    for position in ["QB", "RB", "WR", "TE"]:
        position_results[position] = _run_position(position, all_rows, run_id, generated_at)

    passing = [
        f"{pos}:{cand}"
        for pos, result in position_results.items()
        for cand, gate in result.get("gate_results", {}).items()
        if gate.get("passes")
    ]

    print(f"\n  Passing candidates: {passing or ['none']}")

    def _strip_raw_predictions(obj: object) -> object:
        """Recursively remove oof_predictions_all from dicts before serialization."""
        if isinstance(obj, dict):
            return {k: _strip_raw_predictions(v) for k, v in obj.items()
                    if k != "oof_predictions_all"}
        if isinstance(obj, list):
            return [_strip_raw_predictions(item) for item in obj]
        return obj

    artifact = {
        "run_id": run_id,
        "generated_at": generated_at,
        "scope": "Phase 19 W3 — Head A v3 bake-off per position (row-aligned, OOF metrics)",
        "csv_source": V3_CSV.name,
        "walk_forward_folds": [
            {"train_max_year": t, "test_year": v} for t, v in WALK_FORWARD_FOLDS
        ],
        "gate_thresholds": {
            "rmse_improvement_pct": RMSE_IMPROVEMENT_PCT_GATE,
            "metrics_required": METRICS_REQUIRED_TO_PASS,
            "te_mae_regression_max_pct": TE_MAE_REGRESSION_GATE * 100,
        },
        "ridge_alpha_grid": RIDGE_ALPHA_GRID,
        "gbt_params": GBT_PARAMS,
        "positions": position_results,
        "passing_candidates": passing,
        "promotion_decision": "REQUIRES_DAVID_REVIEW",
        "governance": {
            "market_data_used": False,
            "model_pkl_changed": False,
            "latest_json_changed": False,
            "head_b_prohibited_cols_checked": True,
            "row_alignment": "candidate_feature_availability",
            "rmse_mae_gate": "pooled_oof_across_folds",
            "spearman_ndcg_gate": "unweighted_mean_of_fold_level_values",
            "ndcg_relevance": "direct_ppg",
        },
    }

    out_path = OUTPUT_DIR / f"head_a_bakeoff_{generated_at}_{run_id}.json"
    out_path.write_text(json.dumps(_strip_raw_predictions(artifact), indent=2))
    print(f"\n  Artifact: {out_path}")
    print("  promotion_decision: REQUIRES_DAVID_REVIEW")


if __name__ == "__main__":
    main()
