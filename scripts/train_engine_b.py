#!/usr/bin/env python3
"""Engine B Training MVP (Task 5.4).

Trains the first active-player forecast model using the v2 remediated dataset.
Enforces the Engine B contract and validates against the naive baseline.
"""
from __future__ import annotations

import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_ALLOWED_FEATURES,
    OUTCOME_COLUMN,
    FEATURE_SEASON_COL,
    validate_no_temporal_leakage,
    validate_no_prohibited_features,
    COMPOSITE_GATE_MIN_PASSING
)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATASET_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
MODELS_DIR   = ROOT / "app" / "data" / "models" / "engine_b"
RUNS_DIR     = MODELS_DIR / "runs"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# ── Features ──────────────────────────────────────────────────────────────────
# Filter out metadata and outcome from the allowed set to get actual features
# Note: 'position' and 'aging_curve_position' are strings; Ridge needs numeric.
# In Engine B, we can use 'aging_curve_value' as the positional modifier.
FEATURES = sorted([
    f for f in ENGINE_B_ALLOWED_FEATURES 
    if f not in { "player_id", "feature_season", "team", "depth_chart_position", "aging_curve_position", "position" }
])

def _safe_spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return 0.0
    corr = scipy_stats.spearmanr(y_true, y_pred).statistic
    return float(corr) if not np.isnan(corr) else 0.0

def train_and_validate(df: pd.DataFrame, run_dir: Path) -> dict[str, Any]:
    # 1. Temporal Holdout (20% logic simplified to latest matured seasons)
    # feature_season 2023 is the latest with outcome (T+2 = 2025)
    # feature_season 2024 is inference-only (training_eligible=False)
    
    train_df = df[df["training_eligible"] == True].copy()
    
    # Stratified split by season
    # Let's use 2018-2021 as Train, 2022-2023 as Holdout (~30% holdout)
    holdout_seasons = [2022, 2023]
    
    X_train_raw = train_df[~train_df["feature_season"].isin(holdout_seasons)][FEATURES]
    y_train = train_df[~train_df["feature_season"].isin(holdout_seasons)][OUTCOME_COLUMN].values
    
    X_test_raw = train_df[train_df["feature_season"].isin(holdout_seasons)][FEATURES]
    y_test = train_df[train_df["feature_season"].isin(holdout_seasons)][OUTCOME_COLUMN].values
    
    # Naive Baseline: prior year PPG (ppg_t)
    baseline_pred = X_test_raw["ppg_t"].values
    
    # 2. Impute and Fit
    print(f"Training on {len(X_train_raw)} rows...")
    imputer = SimpleImputer(strategy="mean")
    X_train = imputer.fit_transform(X_train_raw)
    X_test = imputer.transform(X_test_raw)
    
    # alpha=100: features are collinear (snap_share/route_participation/ppg_t r≈0.7+);
    # stronger regularization stabilises predictions without harming gate metrics.
    model = Ridge(alpha=100.0)
    model.fit(X_train, y_train)
    
    # 3. Predict and Score
    y_pred = model.predict(X_test)
    
    # Metrics
    metrics_model = {
        "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
        "r2": r2_score(y_test, y_pred),
        "spearman": _safe_spearman(y_test, y_pred)
    }
    
    metrics_baseline = {
        "rmse": np.sqrt(mean_squared_error(y_test, baseline_pred)),
        "r2": r2_score(y_test, baseline_pred),
        "spearman": _safe_spearman(y_test, baseline_pred)
    }
    
    # 4. Success Gate
    improvements = 0
    if metrics_model["rmse"] < metrics_baseline["rmse"]: improvements += 1
    if metrics_model["r2"] > metrics_baseline["r2"]: improvements += 1
    if metrics_model["spearman"] > metrics_baseline["spearman"]: improvements += 1
    
    promotion_warranted = improvements >= COMPOSITE_GATE_MIN_PASSING
    
    # 5. Save Artifacts
    model_path = run_dir / "engine_b_v1.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "imputer": imputer, "features": FEATURES}, f)
        
    return {
        "metrics_model": metrics_model,
        "metrics_baseline": metrics_baseline,
        "improvements": improvements,
        "promotion_warranted": promotion_warranted,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "artifact_path": str(model_path.relative_to(ROOT))
    }

def main():
    if not DATASET_PATH.exists():
        print(f"Error: Dataset {DATASET_PATH} not found.")
        sys.exit(1)
        
    df = pd.read_csv(DATASET_PATH)
    
    # Final Governance Check
    validate_no_temporal_leakage(FEATURES)
    validate_no_prohibited_features(FEATURES)
    
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    
    print(f"Starting Engine B Training Run: {run_id}")
    results = train_and_validate(df, run_dir)
    
    # Report
    print(f"\n{'─'*50}")
    print(f"  Baseline (Prior PPG) — RMSE {results['metrics_baseline']['rmse']:.3f}  R² {results['metrics_baseline']['r2']:.3f}  Spearman {results['metrics_baseline']['spearman']:.3f}")
    print(f"  Engine B (Ridge)    — RMSE {results['metrics_model']['rmse']:.3f}  R² {results['metrics_model']['r2']:.3f}  Spearman {results['metrics_model']['spearman']:.3f}")
    print(f"  Gate Score: {results['improvements']}/3")
    print(f"  Verdict: {'PASS' if results['promotion_warranted'] else 'FAIL'}")
    print(f"{'─'*50}\n")
    
    # Save Report
    report_path = run_dir / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Model saved to {results['artifact_path']}")
    print(f"Report saved to {report_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
