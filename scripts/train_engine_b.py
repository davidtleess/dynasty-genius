#!/usr/bin/env python3
"""Engine B Training Script — Phase 6 (v1.1 control + v2.0 stratified).

Modes:
  v1_1_control   Stage 6.1 — unified Ridge, route_participation removed,
                 validation artifact only, never promoted to production.
  v2_stratified  Stage 6.2 — 4 independent RidgeCV models, one per position,
                 per-position promotion gate, writes v2_manifest.json.
"""
from __future__ import annotations

import argparse
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
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.metrics import mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_ALLOWED_FEATURES,
    ENGINE_B_FEATURES_BY_POSITION,
    OUTCOME_COLUMN,
    validate_no_temporal_leakage,
    validate_no_prohibited_features,
    validate_position_feature_contract,
    COMPOSITE_GATE_MIN_PASSING,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATASET_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
MODELS_DIR   = ROOT / "app" / "data" / "models" / "engine_b"
RUNS_DIR     = MODELS_DIR / "runs"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)

# ── Metadata columns excluded from all model feature sets ─────────────────────
_META_COLS = {
    "player_id", "position", "feature_season", "team",
    "depth_chart_position", "aging_curve_position",
}

# ── Unified feature list for v1.1 control (same logic as v1, minus 4 exclusions)
FEATURES_UNIFIED = sorted([
    f for f in ENGINE_B_ALLOWED_FEATURES
    if f not in _META_COLS and f != "te_role_is_risk_profile"
])

HOLDOUT_SEASONS = [2022, 2023]

# Alpha candidates for RidgeCV search
ALPHA_CANDIDATES = [0.1, 1.0, 10.0, 50.0, 100.0, 200.0, 500.0, 1000.0]
TE_MODEL_CHANGE_ALPHA = 100.0


def _safe_spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return 0.0
    corr = scipy_stats.spearmanr(y_true, y_pred).statistic
    return float(corr) if not np.isnan(corr) else 0.0


def _gate(metrics_model: dict, metrics_baseline: dict) -> tuple[int, bool]:
    improvements = 0
    if metrics_model["rmse"] < metrics_baseline["rmse"]: improvements += 1
    if metrics_model["r2"] > metrics_baseline["r2"]:     improvements += 1
    if metrics_model["spearman"] > metrics_baseline["spearman"]: improvements += 1
    return improvements, improvements >= COMPOSITE_GATE_MIN_PASSING


def _score(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
        "spearman": _safe_spearman(y_true, y_pred),
    }


def _ensure_availability_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Derive snap_share_t_minus_1_available if not already in dataset."""
    if "snap_share_t_minus_1_available" not in df.columns:
        df = df.copy()
        df["snap_share_t_minus_1_available"] = df["snap_share_t_minus_1"].notna()
    return df


def _fit_position_ridge(
    pos_df: pd.DataFrame,
    features: list[str],
    alpha: float,
) -> tuple[Ridge, SimpleImputer, np.ndarray, np.ndarray]:
    X_raw = pos_df[features]
    y = pos_df[OUTCOME_COLUMN].values
    imputer = SimpleImputer(strategy="median")
    X = imputer.fit_transform(X_raw)
    model = Ridge(alpha=alpha)
    model.fit(X, y)
    return model, imputer, X, y


def train_te_deployment_model(df: pd.DataFrame, run_dir: Path) -> dict[str, Any]:
    """Train only the deployable TE v3 artifact. Does not touch manifest or other positions."""
    train_df = df[(df["training_eligible"] == True) & (df["position"] == "TE")].copy()
    if len(train_df) < 10:
        return {"position": "TE", "skipped": True, "reason": "insufficient_rows"}

    features = sorted(ENGINE_B_FEATURES_BY_POSITION["TE"])
    validate_position_feature_contract("TE", features)
    validate_no_temporal_leakage(features)
    validate_no_prohibited_features(features)
    missing = [feature for feature in features if feature not in train_df.columns]
    if missing:
        raise ValueError(f"TE deployment training missing required columns: {missing}")

    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = run_dir / "te_v3.pkl"
    report_path = run_dir / "validation_report_te.json"
    if artifact_path.exists() or report_path.exists():
        raise FileExistsError(f"TE deployment artifact already exists in {run_dir}")
    model, imputer, X, y = _fit_position_ridge(
        train_df,
        features,
        alpha=TE_MODEL_CHANGE_ALPHA,
    )
    y_pred = model.predict(X)
    metrics_model = _score(y, y_pred)
    metrics_baseline = _score(y, train_df["ppg_t"].values)

    with open(artifact_path, "wb") as f:
        pickle.dump({
            "model": model,
            "imputer": imputer,
            "features": features,
            "version": "engine_b_v3_te",
            "position": "TE",
            "is_validation_only": False,
            "alpha": TE_MODEL_CHANGE_ALPHA,
        }, f)

    feature_index = features.index("te_role_is_risk_profile")
    result = {
        "position": "TE",
        "skipped": False,
        "alpha_selected": TE_MODEL_CHANGE_ALPHA,
        "features": features,
        "n_features": len(features),
        "train_rows": len(X),
        "metrics_model": metrics_model,
        "metrics_baseline": metrics_baseline,
        "promotion_warranted": None,
        "te_role_is_risk_profile_coefficient": float(model.coef_[feature_index]),
        "artifact_path": str(artifact_path),
    }
    with open(report_path, "w") as f:
        json.dump(result, f, indent=2)
    return result


# ── Stage 6.1: v1.1 Unified Control ──────────────────────────────────────────

def train_v1_1_control(df: pd.DataFrame, run_dir: Path) -> dict[str, Any]:
    """Unified Ridge with Phase 6 exclusions applied. Validation artifact only."""
    train_df = df[df["training_eligible"] == True].copy()

    available_features = [f for f in FEATURES_UNIFIED if f in train_df.columns]

    X_train_raw = train_df[~train_df["feature_season"].isin(HOLDOUT_SEASONS)][available_features]
    y_train     = train_df[~train_df["feature_season"].isin(HOLDOUT_SEASONS)][OUTCOME_COLUMN].values
    X_test_raw  = train_df[ train_df["feature_season"].isin(HOLDOUT_SEASONS)][available_features]
    y_test      = train_df[ train_df["feature_season"].isin(HOLDOUT_SEASONS)][OUTCOME_COLUMN].values
    baseline    = X_test_raw["ppg_t"].values

    print(f"  v1.1 unified — train {len(X_train_raw)} rows, holdout {len(X_test_raw)} rows")
    imputer = SimpleImputer(strategy="mean")
    X_train = imputer.fit_transform(X_train_raw)
    X_test  = imputer.transform(X_test_raw)

    model = Ridge(alpha=100.0)
    model.fit(X_train, y_train)

    y_pred          = model.predict(X_test)
    metrics_model   = _score(y_test, y_pred)
    metrics_baseline = _score(y_test, baseline)
    improvements, promotion_warranted = _gate(metrics_model, metrics_baseline)

    artifact_path = run_dir / "engine_b_v1_1.pkl"
    with open(artifact_path, "wb") as f:
        pickle.dump({
            "model": model,
            "imputer": imputer,
            "features": available_features,
            "version": "engine_b_v1_1",
            "is_validation_only": True,
        }, f)

    return {
        "mode": "v1_1_control",
        "is_validation_only": True,
        "alpha_fixed": 100.0,
        "features": available_features,
        "metrics_model": metrics_model,
        "metrics_baseline": metrics_baseline,
        "improvements": improvements,
        "promotion_warranted": promotion_warranted,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "artifact_path": str(artifact_path.relative_to(ROOT)),
    }


# ── Stage 6.2: v2.0 Position-Stratified ──────────────────────────────────────

def _train_position(
    pos: str,
    train_df: pd.DataFrame,
    run_dir: Path,
    v1_0_metrics: dict[str, dict],
    v1_1_metrics: dict[str, dict],
) -> dict[str, Any]:
    """Train one position model, validate, and save artifact."""
    allowed = ENGINE_B_FEATURES_BY_POSITION[pos]
    pos_df = train_df[train_df["position"] == pos].copy()

    if len(pos_df) < 10:
        print(f"  {pos}: insufficient rows ({len(pos_df)}), skipping")
        return {"position": pos, "skipped": True, "reason": "insufficient_rows"}

    # Only include columns that exist in the dataset and are in this position's contract
    available = sorted([f for f in allowed if f in pos_df.columns])

    validate_position_feature_contract(pos, available)

    X_train_raw = pos_df[~pos_df["feature_season"].isin(HOLDOUT_SEASONS)][available]
    y_train     = pos_df[~pos_df["feature_season"].isin(HOLDOUT_SEASONS)][OUTCOME_COLUMN].values
    X_test_raw  = pos_df[ pos_df["feature_season"].isin(HOLDOUT_SEASONS)][available]
    y_test      = pos_df[ pos_df["feature_season"].isin(HOLDOUT_SEASONS)][OUTCOME_COLUMN].values
    baseline    = X_test_raw["ppg_t"].values

    print(f"  {pos}: train {len(X_train_raw)} rows, holdout {len(X_test_raw)} rows, {len(available)} features")

    imputer = SimpleImputer(strategy="median")
    X_train = imputer.fit_transform(X_train_raw)
    X_test  = imputer.transform(X_test_raw)

    model = RidgeCV(alphas=ALPHA_CANDIDATES, cv=5)
    model.fit(X_train, y_train)

    y_pred           = model.predict(X_test)
    metrics_v2       = _score(y_test, y_pred)
    metrics_baseline = _score(y_test, baseline)
    improvements, promotion_warranted = _gate(metrics_v2, metrics_baseline)

    artifact_name = f"{pos.lower()}_v2.pkl"
    artifact_path = run_dir / artifact_name
    with open(artifact_path, "wb") as f:
        pickle.dump({
            "model": model,
            "imputer": imputer,
            "features": available,
            "version": f"engine_b_v2_{pos.lower()}",
            "position": pos,
            "is_validation_only": False,
        }, f)

    return {
        "position": pos,
        "skipped": False,
        "alpha_selected": float(model.alpha_),
        "features": available,
        "n_features": len(available),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "metrics_v2": metrics_v2,
        "metrics_v1_1": v1_1_metrics.get(pos),
        "metrics_v1_0": v1_0_metrics.get(pos),
        "metrics_baseline": metrics_baseline,
        "improvements": improvements,
        "promotion_warranted": promotion_warranted,
        "artifact_path": str(artifact_path.relative_to(ROOT)),
    }


def _load_v1_0_metrics_by_position(df: pd.DataFrame) -> dict[str, dict]:
    """Compute naive-comparison metrics from v1.0 unified model if pkl exists."""
    v1_pkl = RUNS_DIR / "20260512T032635Z" / "engine_b_v1.pkl"
    if not v1_pkl.exists():
        return {}
    try:
        with open(v1_pkl, "rb") as f:
            bundle = pickle.load(f)
        train_df = df[df["training_eligible"] == True].copy()
        test_df = train_df[train_df["feature_season"].isin(HOLDOUT_SEASONS)]
        v1_features = [c for c in bundle["features"] if c in test_df.columns]
        imputer: SimpleImputer = bundle["imputer"]
        model_v1 = bundle["model"]
        result = {}
        for pos in ENGINE_B_FEATURES_BY_POSITION:
            pos_test = test_df[test_df["position"] == pos]
            if len(pos_test) == 0:
                continue
            X = imputer.transform(pos_test[v1_features])
            y_pred = model_v1.predict(X)
            result[pos] = _score(pos_test[OUTCOME_COLUMN].values, y_pred)
        return result
    except Exception:
        return {}


def train_v2_stratified(df: pd.DataFrame, run_dir: Path) -> dict[str, Any]:
    """Train 4 independent RidgeCV models. Write per-position validation reports."""
    train_df = df[df["training_eligible"] == True].copy()

    # Load v1.0 per-position metrics for 3-way comparison
    v1_0_metrics = _load_v1_0_metrics_by_position(df)

    # Load v1.1 control metrics from its report if available
    v1_1_report = RUNS_DIR / "v1_1_control" / "training_report.json"
    v1_1_metrics: dict[str, dict] = {}
    if v1_1_report.exists():
        try:
            with open(v1_1_report) as f:
                v1_1_data = json.load(f)
            # v1.1 is unified — use its overall metrics for all positions as reference
            for pos in ENGINE_B_FEATURES_BY_POSITION:
                v1_1_metrics[pos] = v1_1_data.get("metrics_model", {})
        except Exception:
            pass

    position_results: dict[str, Any] = {}
    manifest: dict[str, str | None] = {}

    for pos in ("QB", "RB", "WR", "TE"):
        result = _train_position(pos, train_df, run_dir, v1_0_metrics, v1_1_metrics)
        position_results[pos] = result
        if not result.get("skipped") and result.get("promotion_warranted"):
            manifest[pos] = result["artifact_path"]
        else:
            manifest[pos] = None

    # Write per-position validation reports
    for pos, result in position_results.items():
        report_path = run_dir / f"validation_report_{pos.lower()}.json"
        with open(report_path, "w") as f:
            json.dump(result, f, indent=2)

    # Write manifest only for promoted positions
    manifest_path = MODELS_DIR / "v2_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    promoted = [p for p, path in manifest.items() if path is not None]
    not_promoted = [p for p, path in manifest.items() if path is None]

    return {
        "mode": "v2_stratified",
        "positions": position_results,
        "manifest": manifest,
        "promoted": promoted,
        "not_promoted": not_promoted,
        "manifest_path": str(manifest_path.relative_to(ROOT)),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Engine B training — Phase 6")
    parser.add_argument(
        "--mode",
        choices=["v1_1_control", "v2_stratified"],
        default="v1_1_control",
        help="v1_1_control: Stage 6.1 hygiene control (validation only). "
             "v2_stratified: Stage 6.2 position-stratified production candidate.",
    )
    parser.add_argument(
        "--position",
        choices=["TE"],
        default=None,
        help="Train one guarded deployment artifact. Currently supported only for TE.",
    )
    args = parser.parse_args()

    if not DATASET_PATH.exists():
        print(f"Error: Dataset {DATASET_PATH} not found.")
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH)
    df = _ensure_availability_flags(df)

    if args.mode == "v1_1_control":
        validate_no_temporal_leakage(FEATURES_UNIFIED)
        validate_no_prohibited_features(FEATURES_UNIFIED)

        run_dir = RUNS_DIR / "v1_1_control"
        run_dir.mkdir(parents=True, exist_ok=True)

        print("Starting Engine B v1.1 Control Run (validation artifact only)")
        results = train_v1_1_control(df, run_dir)

        print(f"\n{'─'*54}")
        print("  Mode: v1.1 unified control  [VALIDATION ONLY — not promoted]")
        print(f"  Alpha: {results['alpha_fixed']} (fixed — same as v1.0)")
        print(f"  Features: {len(results['features'])}")
        print(f"  Baseline  — RMSE {results['metrics_baseline']['rmse']:.3f}  R² {results['metrics_baseline']['r2']:.3f}  Spearman {results['metrics_baseline']['spearman']:.3f}")
        print(f"  v1.1      — RMSE {results['metrics_model']['rmse']:.3f}  R² {results['metrics_model']['r2']:.3f}  Spearman {results['metrics_model']['spearman']:.3f}")
        print(f"  Gate: {results['improvements']}/3  ({'PASS' if results['promotion_warranted'] else 'FAIL'} — informational only)")
        print(f"{'─'*54}\n")

        report_path = run_dir / "training_report.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Artifact: {results['artifact_path']}")
        print(f"Report:   {report_path.relative_to(ROOT)}")

    else:  # v2_stratified
        print("Starting Engine B v2.0 Stratified Training Run")
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=False)

        if args.position == "TE":
            results = {
                "mode": "v2_stratified_te_only",
                "positions": {"TE": train_te_deployment_model(df, run_dir)},
                "manifest": None,
                "promoted": [],
                "not_promoted": [],
                "manifest_path": None,
            }
        else:
            results = train_v2_stratified(df, run_dir)

        print(f"\n{'─'*54}")
        print(f"  Mode: v2.0 stratified  [run: {run_id}]")
        for pos, r in results["positions"].items():
            if r.get("skipped"):
                print(f"  {pos}: SKIPPED — {r.get('reason')}")
                continue
            if args.position == "TE":
                print(
                    f"  {pos}: deployment artifact written  "
                    f"RMSE {r['metrics_model']['rmse']:.3f}  "
                    f"R² {r['metrics_model']['r2']:.3f}  "
                    f"Spearman {r['metrics_model']['spearman']:.3f}  "
                    f"alpha={r['alpha_selected']}"
                )
            else:
                verdict = "PASS ✓ promoted" if r["promotion_warranted"] else "FAIL — not promoted"
                print(f"  {pos}: {verdict}  RMSE {r['metrics_v2']['rmse']:.3f}  R² {r['metrics_v2']['r2']:.3f}  Spearman {r['metrics_v2']['spearman']:.3f}  alpha={r['alpha_selected']}")
        print(f"\n  Promoted: {results['promoted']}")
        print(f"  Not promoted: {results['not_promoted']}")
        print(f"  Manifest: {results['manifest_path']}")
        print(f"{'─'*54}\n")

        report_path = run_dir / "training_report.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Report: {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
