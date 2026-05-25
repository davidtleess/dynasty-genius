"""Phase 19 W4 — Head B (Market Edge / Residuals) v3 Bake-Off Harness.

Runs 4-fold temporal walk-forward evaluation for Ridge and GBT candidates
against the Head B target (residual_ppg = actual PPG - expected PPG at pick).
No draft-capital features are permitted; leakage is enforced via head_b_contract.

Gates:
  Mandatory : Residual R² > 0 (model beats a mean-zero baseline)
  Secondary : ≥2 of 3 — within-tier pairwise accuracy, top-5 Day 3 sleeper
              precision, residual calibration monotonicity

Outlier sensitivity: LOOO coefficient drift report per position (Ridge only).
Feature with max drift >25% across folds → flagged "Candidate-Quarantined".

Does NOT promote any model pkl or update v3_manifest.json.
"""
from __future__ import annotations

import csv
import dataclasses
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.head_b_contract import check_head_b_feature_leakage

V3_CSV = ROOT / "app/data/training/prospects_with_outcomes_v3.csv"
OUTPUT_DIR = ROOT / "app/data/backtest/phase19"
OOF_LOG_DIR = OUTPUT_DIR / "oof_logs"

# ── Gate thresholds ───────────────────────────────────────────────────────────
LOOO_DRIFT_THRESHOLD_PCT: float = 25.0
DAY3_PICK_CUTOFF: int = 103
PAIRWISE_TIER_WINDOW: int = 10
PAIRWISE_ACCURACY_GATE_MIN: float = 0.5   # strictly greater than
DAY3_PRECISION_GATE_MIN: float = 0.5      # strictly greater than
SECONDARY_GATES_REQUIRED: int = 2

# ── Model hyperparameters ─────────────────────────────────────────────────────
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 50.0, 100.0, 250.0, 500.0, 1000.0]
GBT_PARAMS = {
    "max_depth": 3,
    "learning_rate": 0.05,
    "n_estimators": 50,
    "min_samples_leaf": 5,
    "random_state": 42,
}

# ── Walk-forward folds: (train_max_year, test_year) ───────────────────────────
WALK_FORWARD_FOLDS = [
    (2017, 2018),
    (2018, 2019),
    (2019, 2020),
    (2020, 2021),
]

# ── Head B feature matrices (no draft capital) ────────────────────────────────
HEAD_B_FEATURES: dict[str, list[str]] = {
    "QB": [],  # QB skipped — no residual features in W4 spec
    "RB": [
        "final_college_age",
        "rb_final_dominator",
        "rb_school_sp_plus",
    ],
    "WR": [
        "final_college_age",
        "wr_dominator_final",
        "wr_breakout_age",
        "wr_market_share_yds",
        "wr_yards_per_reception_career",
        "ryptpa",
    ],
    "TE": [
        "final_college_age",
        "te_ryptpa_final",
        "te_yards_per_reception_career",
    ],
}

TARGET_COL = "residual_ppg"


# ── Gate functions (public — imported by test suite) ─────────────────────────

def compute_residual_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Coefficient of determination for residual predictions."""
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 0.0


def evaluate_head_b_mandatory_gate(r2: float) -> bool:
    """Return True only when residual R² > 0."""
    return r2 > 0.0


def compute_within_tier_pairwise_accuracy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    nfl_picks: np.ndarray,
    tier_window: int = PAIRWISE_TIER_WINDOW,
) -> float:
    """Fraction of same-tier pairs (within tier_window picks) correctly ordered.

    Returns 0.0 when no qualifying pairs exist.
    """
    n = len(y_true)
    correct = 0.0
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            if abs(nfl_picks[i] - nfl_picks[j]) <= tier_window:
                total += 1
                diff_pred = y_pred[i] - y_pred[j]
                diff_true = y_true[i] - y_true[j]
                if diff_pred * diff_true > 0:
                    correct += 1.0
                elif diff_true == 0.0:
                    correct += 0.5  # tie: half credit
    return correct / total if total > 0 else 0.0


def compute_top5_day3_sleeper_precision(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    nfl_picks: np.ndarray,
) -> Optional[float]:
    """Precision@5 for Day 3 picks: top-5 predicted Head B plays from picks 103+.

    Returns None when fewer than 1 Day 3 pick is available.
    """
    day3_mask = nfl_picks >= DAY3_PICK_CUTOFF
    if day3_mask.sum() < 1:
        return None
    d3_pred = y_pred[day3_mask]
    d3_true = y_true[day3_mask]
    top_k = min(5, len(d3_pred))
    top_idx = np.argsort(d3_pred)[::-1][:top_k]
    return float(np.sum(d3_true[top_idx] > 0.0)) / top_k


def compute_residual_calibration_monotonicity(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bins: int = 4,
) -> bool:
    """True when mean actual residuals are monotonically non-decreasing across bins.

    Bins are formed by sorting rows by predicted residual, then splitting evenly.
    """
    n = len(y_pred)
    bin_size = n // n_bins
    if bin_size < 1:
        return False
    sorted_idx = np.argsort(y_pred)
    bin_true_means: list[float] = []
    for i in range(n_bins):
        start = i * bin_size
        end = start + bin_size if i < n_bins - 1 else n
        bin_rows = sorted_idx[start:end]
        bin_true_means.append(float(np.mean(y_true[bin_rows])))
    for i in range(1, len(bin_true_means)):
        if bin_true_means[i] < bin_true_means[i - 1]:
            return False
    return True


def compute_coefficient_drift(
    X_train: np.ndarray,
    y_train: np.ndarray,
    alpha: float,
    features: list[str],
) -> dict[str, float]:
    """LOOO coefficient drift: max % shift when the single largest-residual row is removed.

    Fits Ridge on full training set, identifies the outlier (argmax |residual|),
    refits without it, and returns per-feature drift percentages.
    """
    n = len(X_train)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    baseline = Ridge(alpha=alpha)
    baseline.fit(X_scaled, y_train)
    baseline_coef = baseline.coef_.copy()

    y_pred_train = baseline.predict(X_scaled)
    outlier_idx = int(np.argmax(np.abs(y_train - y_pred_train)))

    mask = np.ones(n, dtype=bool)
    mask[outlier_idx] = False
    if mask.sum() < 3:
        return {f: 0.0 for f in features}

    # Refit on outlier-removed set using same scaler (train stats)
    X_no_out = X_scaled[mask]
    y_no_out = y_train[mask]
    looo = Ridge(alpha=alpha)
    looo.fit(X_no_out, y_no_out)
    looo_coef = looo.coef_

    drift: dict[str, float] = {}
    for i, feat in enumerate(features):
        orig = float(baseline_coef[i])
        new = float(looo_coef[i])
        if abs(orig) < 1e-10:
            drift[feat] = 0.0 if abs(new) < 1e-10 else 100.0
        else:
            drift[feat] = abs(new - orig) / abs(orig) * 100.0
    return drift


def flag_unstable_features(
    drift_dict: dict[str, float],
    threshold: float = LOOO_DRIFT_THRESHOLD_PCT,
) -> list[str]:
    """Return feature names whose drift percentage exceeds threshold."""
    return [feat for feat, pct in drift_dict.items() if pct > threshold]


# ── Secondary gate evaluator ─────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class HeadBGateResult:
    mandatory_r2_passes: bool
    r2: float
    secondary_gates_passed: int
    pairwise_accuracy_gate: bool
    day3_precision_gate: bool
    calibration_monotonicity_gate: bool
    final_passes: bool
    fail_reasons: list[str]


def evaluate_head_b_gates(
    r2: float,
    pairwise_accuracy: Optional[float],
    day3_precision: Optional[float],
    calibration_monotone: bool,
) -> HeadBGateResult:
    """Evaluate mandatory R² gate and secondary 2-of-3 gates."""
    mandatory = evaluate_head_b_mandatory_gate(r2)

    pa_gate = (pairwise_accuracy is not None and
               pairwise_accuracy > PAIRWISE_ACCURACY_GATE_MIN)
    d3_gate = (day3_precision is not None and
               day3_precision > DAY3_PRECISION_GATE_MIN)
    mono_gate = calibration_monotone

    secondary_passed = sum([pa_gate, d3_gate, mono_gate])
    final = mandatory and secondary_passed >= SECONDARY_GATES_REQUIRED

    fail_reasons: list[str] = []
    if not mandatory:
        fail_reasons.append("mandatory_r2_gate")
    if not pa_gate:
        fail_reasons.append("pairwise_accuracy_gate")
    if not d3_gate:
        fail_reasons.append("day3_precision_gate")
    if not mono_gate:
        fail_reasons.append("calibration_monotonicity_gate")

    return HeadBGateResult(
        mandatory_r2_passes=mandatory,
        r2=round(r2, 4),
        secondary_gates_passed=secondary_passed,
        pairwise_accuracy_gate=pa_gate,
        day3_precision_gate=d3_gate,
        calibration_monotonicity_gate=mono_gate,
        final_passes=final,
        fail_reasons=fail_reasons,
    )


# ── Internal utilities ────────────────────────────────────────────────────────

def _to_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def scale_features(
    X_train: np.ndarray, X_test: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Fit StandardScaler on X_train; apply to both."""
    scaler = StandardScaler()
    return scaler.fit_transform(X_train), scaler.transform(X_test)


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


def _extract_matrix(
    rows: list[dict],
    features: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract (X, y, nfl_picks) from rows.

    nfl_pick is extracted as gate-calculation metadata, not a training feature.
    Rows with any missing feature, missing target, or missing nfl_pick are dropped.
    """
    X_rows: list[list[float]] = []
    y_rows: list[float] = []
    pick_rows: list[float] = []
    for row in rows:
        feat_vals = [_to_float(row.get(f)) for f in features]
        target_val = _to_float(row.get(TARGET_COL))
        pick_val = _to_float(row.get("nfl_pick"))
        if target_val is None or any(v is None for v in feat_vals) or pick_val is None:
            continue
        X_rows.append(feat_vals)  # type: ignore[arg-type]
        y_rows.append(target_val)
        pick_rows.append(pick_val)
    return (
        np.array(X_rows, dtype=float),
        np.array(y_rows, dtype=float),
        np.array(pick_rows, dtype=float),
    )


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
    return {"rmse": round(rmse, 4), "spearman": round(rho, 4)}


# ── LOOO per-fold drift accumulator ──────────────────────────────────────────

def _run_looo_drift_for_position(
    pos_rows: list[dict],
    features: list[str],
) -> dict[str, float]:
    """Compute max LOOO coefficient drift across all 4 folds for Ridge.

    Returns mapping from feature → max drift% across folds.
    """
    max_drift: dict[str, float] = {f: 0.0 for f in features}

    for train_max_year, _ in WALK_FORWARD_FOLDS:
        train_rows = _filter_training_rows(pos_rows, train_max_year)
        X_train, y_train, _ = _extract_matrix(train_rows, features)
        if len(X_train) < 5:
            continue
        # Use best alpha from RidgeCV for drift calculation
        scaler = StandardScaler()
        X_s = scaler.fit_transform(X_train)
        rcv = RidgeCV(alphas=RIDGE_ALPHA_GRID)
        rcv.fit(X_s, y_train)
        best_alpha = float(rcv.alpha_)

        fold_drift = compute_coefficient_drift(X_train, y_train, best_alpha, features)
        for feat, pct in fold_drift.items():
            if pct > max_drift.get(feat, 0.0):
                max_drift[feat] = pct

    return {f: round(max_drift[f], 2) for f in features}


# ── Position orchestrator ─────────────────────────────────────────────────────

def _run_position(
    position: str,
    all_rows: list[dict],
    run_id: str,
    generated_at: str,
) -> dict:
    pos_rows = [r for r in all_rows if r.get("position", "").upper() == position]
    eligible = [r for r in pos_rows if r.get("censored_incomplete_arc", "0") != "1"]
    n_total = len(pos_rows)
    n_eligible = len(eligible)
    spec_features = HEAD_B_FEATURES.get(position, [])

    print(f"\n  {position}: {n_total} total rows, {n_eligible} non-censored")

    if not spec_features:
        print(f"    [SKIP] No W4 features defined for {position}")
        return {
            "position": position,
            "n_total_rows": n_total,
            "n_eligible_rows": n_eligible,
            "skipped": True,
            "skip_reason": "no_w4_features",
        }

    # Leakage enforcement before any training
    check_head_b_feature_leakage(spec_features)

    available_features = _filter_available_features(eligible, spec_features)
    dropped_features = [f for f in spec_features if f not in available_features]

    if dropped_features:
        print(f"    [COVERAGE] Dropped low-coverage features: {dropped_features}")

    if not available_features:
        print("    [SKIP] All features dropped by coverage filter")
        return {
            "position": position,
            "n_total_rows": n_total,
            "n_eligible_rows": n_eligible,
            "skipped": True,
            "skip_reason": "all_features_dropped_by_coverage",
            "spec_features": spec_features,
            "dropped_features": dropped_features,
        }

    print(f"    Available features ({len(available_features)}): {available_features}")

    coverage_report = {
        feat: round(
            sum(1 for r in eligible if _to_float(r.get(feat)) is not None)
            / max(n_eligible, 1) * 100, 1
        )
        for feat in spec_features
    }

    # Accumulate OOF predictions across folds for all-fold gate evaluation
    ridge_oof: list[dict] = []
    ridge_fold_results: list[dict] = []
    gbt_oof: list[dict] = []
    gbt_fold_results: list[dict] = []

    for train_max_year, test_year in WALK_FORWARD_FOLDS:
        train_rows = _filter_training_rows(pos_rows, train_max_year)
        test_rows = [r for r in pos_rows if _to_float(r.get("season")) == float(test_year)]

        X_train, y_train, _ = _extract_matrix(train_rows, available_features)
        X_test, y_test, test_picks = _extract_matrix(test_rows, available_features)

        if len(X_train) < 5 or len(X_test) < 1:
            continue

        for model_type, oof_list, fold_list in [
            ("ridge", ridge_oof, ridge_fold_results),
            ("gbt", gbt_oof, gbt_fold_results),
        ]:
            y_pred, best_alpha = _fit_predict(X_train, y_train, X_test, model_type)
            fold = {
                "train_max_year": train_max_year,
                "test_year": test_year,
                "n_train": len(X_train),
                "n_test": len(X_test),
                **_fold_metrics(y_test, y_pred),
                "best_alpha": best_alpha,
            }
            fold_list.append(fold)
            for yt, yp, pk in zip(y_test, y_pred, test_picks):
                oof_list.append({
                    "y_true": float(yt),
                    "y_pred": float(yp),
                    "nfl_pick": float(pk),
                    "train_max_year": train_max_year,
                    "test_year": test_year,
                })

    # ── Evaluate gates on pooled OOF ─────────────────────────────────────────
    candidate_gates: dict[str, dict] = {}
    candidate_results: dict[str, dict] = {}

    for cand_name, oof_list, fold_list in [
        ("ridge", ridge_oof, ridge_fold_results),
        ("gbt", gbt_oof, gbt_fold_results),
    ]:
        if not oof_list:
            candidate_gates[cand_name] = {"error": "no_oof_predictions", "final_passes": False}
            candidate_results[cand_name] = {"skipped": True}
            continue

        all_y_true = np.array([p["y_true"] for p in oof_list])
        all_y_pred = np.array([p["y_pred"] for p in oof_list])
        all_picks = np.array([p["nfl_pick"] for p in oof_list])

        r2 = compute_residual_r2(all_y_true, all_y_pred)
        pairwise_acc = compute_within_tier_pairwise_accuracy(
            all_y_true, all_y_pred, all_picks
        )
        day3_prec = compute_top5_day3_sleeper_precision(all_y_true, all_y_pred, all_picks)
        monotone = compute_residual_calibration_monotonicity(all_y_true, all_y_pred)

        gate = evaluate_head_b_gates(r2, pairwise_acc, day3_prec, monotone)
        status = "PASS" if gate.final_passes else "FAIL"
        day3_display = f"{day3_prec:.3f}" if day3_prec is not None else "N/A"
        print(
            f"    Gate [{cand_name}]: {status}  "
            f"R²={r2:.4f}  pairwise={pairwise_acc:.3f}  "
            f"day3={day3_display}  "
            f"monotone={monotone}  "
            f"secondary={gate.secondary_gates_passed}/3  "
            f"fail={gate.fail_reasons or ['none']}"
        )

        oof_rmse = float(np.sqrt(np.mean((all_y_true - all_y_pred) ** 2)))
        mean_spearman = float(np.mean([f["spearman"] for f in fold_list])) if fold_list else 0.0

        candidate_gates[cand_name] = dataclasses.asdict(gate)
        candidate_results[cand_name] = {
            "n_folds": len(fold_list),
            "n_oof": len(oof_list),
            "oof_rmse": round(oof_rmse, 4),
            "oof_r2": round(r2, 4),
            "pairwise_accuracy": round(pairwise_acc, 4),
            "day3_precision": round(day3_prec, 4) if day3_prec is not None else None,
            "calibration_monotone": monotone,
            "mean_fold_spearman": round(mean_spearman, 4),
            "fold_results": fold_list,
        }

    # ── LOOO outlier sensitivity (Ridge only) ────────────────────────────────
    looo_drift = _run_looo_drift_for_position(eligible, available_features)
    unstable_features = flag_unstable_features(looo_drift)
    if unstable_features:
        print(f"    [LOOO] Unstable features (>{LOOO_DRIFT_THRESHOLD_PCT}% drift): "
              f"{unstable_features}")
        # Quarantine all candidates that were passing — they use the unstable features.
        for cand_name in list(candidate_gates.keys()):
            gates_dict = dict(candidate_gates[cand_name])
            if gates_dict.get("final_passes"):
                gates_dict["final_passes"] = False
                gates_dict["fail_reasons"] = list(gates_dict.get("fail_reasons", [])) + [
                    "looo_drift_quarantined"
                ]
                candidate_gates[cand_name] = gates_dict

    # Write OOF log
    oof_path = _write_oof_log(position, ridge_oof, gbt_oof, run_id, generated_at)

    return {
        "position": position,
        "n_total_rows": n_total,
        "n_eligible_rows": n_eligible,
        "spec_features": spec_features,
        "available_features": available_features,
        "dropped_features": dropped_features,
        "coverage_pct": coverage_report,
        "ridge": candidate_results.get("ridge", {}),
        "gbt": candidate_results.get("gbt", {}),
        "gate_results": candidate_gates,
        "looo_drift_pct": looo_drift,
        "unstable_features": unstable_features,
        "oof_log": str(oof_path.name) if oof_path else None,
    }


def _write_oof_log(
    position: str,
    ridge_oof: list[dict],
    gbt_oof: list[dict],
    run_id: str,
    generated_at: str,
) -> Optional[Path]:
    """Write pooled OOF predictions per position to a CSV for residual diagnostics."""
    OOF_LOG_DIR.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []
    for cand_name, oof_list in [("ridge", ridge_oof), ("gbt", gbt_oof)]:
        for pred in oof_list:
            rows_out.append({
                "position": position,
                "candidate": cand_name,
                "train_max_year": pred["train_max_year"],
                "test_year": pred["test_year"],
                "nfl_pick": pred["nfl_pick"],
                "y_true": pred["y_true"],
                "y_pred": round(pred["y_pred"], 4),
                "residual": round(pred["y_true"] - pred["y_pred"], 4),
            })
    if not rows_out:
        return None
    out_path = OOF_LOG_DIR / f"oof_head_b_{position}_{generated_at}_{run_id}.csv"
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("Phase 19 W4 — Head B v3 Bake-Off")
    print(f"  Run ID     : {run_id}")
    print(f"  Generated  : {generated_at}")
    print(f"  CSV        : {V3_CSV}")
    print(f"  Target     : {TARGET_COL}")
    print(f"  Folds      : {WALK_FORWARD_FOLDS}")

    all_rows = _load_all_rows()
    print(f"  Total rows : {len(all_rows)}")

    position_results: dict[str, dict] = {}
    outlier_report: dict[str, dict] = {}

    for position in ["QB", "RB", "WR", "TE"]:
        result = _run_position(position, all_rows, run_id, generated_at)
        position_results[position] = result
        if not result.get("skipped"):
            outlier_report[position] = {
                "looo_drift_pct": result.get("looo_drift_pct", {}),
                "unstable_features": result.get("unstable_features", []),
                "features_demoted_to_candidate_quarantined": result.get("unstable_features", []),
            }

    passing = [
        f"{pos}:{cand}"
        for pos, result in position_results.items()
        for cand, gate in result.get("gate_results", {}).items()
        if gate.get("final_passes")
    ]

    print(f"\n  Passing candidates: {passing or ['none']}")

    # Outlier sensitivity report (separate artifact per spec §4)
    sensitivity_path = OUTPUT_DIR / f"head_b_outlier_sensitivity_report_{generated_at}_{run_id}.json"
    sensitivity_path.write_text(json.dumps({
        "run_id": run_id,
        "generated_at": generated_at,
        "looo_drift_threshold_pct": LOOO_DRIFT_THRESHOLD_PCT,
        "positions": outlier_report,
    }, indent=2))
    print(f"  Sensitivity report: {sensitivity_path}")

    def _strip_raw(obj: object) -> object:
        if isinstance(obj, dict):
            return {k: _strip_raw(v) for k, v in obj.items() if k not in ("oof_predictions",)}
        if isinstance(obj, list):
            return [_strip_raw(i) for i in obj]
        return obj

    artifact = {
        "run_id": run_id,
        "generated_at": generated_at,
        "scope": "Phase 19 W4 — Head B v3 bake-off per position (residual_ppg target)",
        "csv_source": V3_CSV.name,
        "target_col": TARGET_COL,
        "walk_forward_folds": [
            {"train_max_year": t, "test_year": v} for t, v in WALK_FORWARD_FOLDS
        ],
        "gate_thresholds": {
            "mandatory_r2_gt_zero": True,
            "secondary_gates_required": SECONDARY_GATES_REQUIRED,
            "pairwise_accuracy_min": PAIRWISE_ACCURACY_GATE_MIN,
            "day3_precision_min": DAY3_PRECISION_GATE_MIN,
            "looo_drift_threshold_pct": LOOO_DRIFT_THRESHOLD_PCT,
        },
        "ridge_alpha_grid": RIDGE_ALPHA_GRID,
        "gbt_params": GBT_PARAMS,
        "positions": _strip_raw(position_results),
        "passing_candidates": passing,
        "promotion_decision": "REQUIRES_DAVID_REVIEW",
        "governance": {
            "market_data_used": False,
            "model_pkl_changed": False,
            "v3_manifest_changed": False,
            "head_b_draft_capital_leakage_checked": True,
            "target": TARGET_COL,
            "r2_gate": "pooled_oof",
            "pairwise_and_precision_gate": "pooled_oof_all_folds",
        },
        "outlier_sensitivity_report": str(sensitivity_path.name),
    }

    out_path = OUTPUT_DIR / f"head_b_bakeoff_{generated_at}_{run_id}.json"
    out_path.write_text(json.dumps(artifact, indent=2))
    print(f"\n  Artifact: {out_path}")
    print("  promotion_decision: REQUIRES_DAVID_REVIEW")


if __name__ == "__main__":
    main()
