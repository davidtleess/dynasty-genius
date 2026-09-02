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
import os
import pickle
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.metrics import mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.engine_b_contract import (
    COMPOSITE_GATE_MIN_PASSING,
    ENGINE_B_ALLOWED_FEATURES,
    ENGINE_B_FEATURES_BY_POSITION,
    OUTCOME_COLUMN,
    optional_features_present,
    validate_no_prohibited_features,
    validate_no_temporal_leakage,
    validate_position_feature_contract,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATASET_PATH = ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
MODELS_DIR   = ROOT / "app" / "data" / "models" / "engine_b"
RUNS_DIR     = MODELS_DIR / "runs"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def model_publish(run_id: str) -> Iterator[None]:
    """Declare a model publish in flight for the WHOLE of it — first pickle to last write.

    The window being guarded opens at the FIRST bundle write, not the manifest. A scorer
    landing between pickle two and pickle three reads a half-swapped model set, which is
    the actual hazard; wrapping only the manifest would be present, green, and covering
    the wrong interval.

    A context manager rather than two calls, so the ordering cannot be got wrong by a
    later edit and the `finally` cannot be forgotten.
    """
    from src.dynasty_genius.model_publish_lock import clear_sentinel, write_sentinel

    write_sentinel(
        ROOT,
        run_id=run_id,
        # TZ-AWARE on purpose: blocking_publish() compares this to an aware now(), and a
        # naive stamp is treated as stale — which would silently disable the guard rather
        # than fail loudly.
        started_at=datetime.now(timezone.utc),
    )
    try:
        yield
    finally:
        # A stale sentinel that silently stops the daily chain is a worse defect than the
        # race it prevents. The module carries two independent staleness escapes for the
        # case where even this fails, but relying on them for the ordinary failure path
        # would be sloppy.
        clear_sentinel(ROOT)


def publish_model_set(
    manifest_path: Path, manifest: dict[str, Any], *, run_id: str
) -> None:
    """Declare the publish, write the manifest, and clear the declaration.

    A retrain replaces four pickles and a manifest as FIVE separate writes.
    ``com.davidleess.dynasty-model-pvo-refresh`` fires at 11:30 and 14:00 and takes no lock
    of any kind, so a run landing inside those writes scores the universe from a
    half-swapped model set and publishes it as live serving state, with a green receipt
    because from its side nothing failed.

    ``model_publish_lock`` (DG-126) is the consumer half and is already landed. It is INERT
    until a producer declares itself — it can only refuse when something wrote the
    sentinel. This is that producer. The lock module is IMPORTED rather than reimplemented
    so the two halves cannot drift.

    Advisory, not a lock: it stops the scheduled scorer, which is the observed hazard. It
    does not stop a human running the scorer by hand, and it does not make the five writes
    atomic. The atomic manifest write below closes a different window (a reader seeing a
    truncated manifest); both are needed and neither subsumes the other.

    ``clear_sentinel`` runs in a ``finally`` because a stale sentinel that silently stops
    the daily chain is a worse defect than the race it prevents. The module carries two
    independent staleness escapes for the case where even this fails, but relying on them
    for the ordinary failure path would be sloppy.
    """
    with model_publish(run_id):
        write_manifest(manifest_path, manifest)


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Publish the position→bundle manifest atomically.

    A plain ``open(path, "w")`` truncates on open, leaving a window in which the manifest
    is empty or half-written. That window matters because of who reads it:
    ``EngineBService`` resolves a bundle with ``self._v2_bundles.get(position) or
    self._v1_bundle`` (app/services/engine_b_service.py:136), a silent fail-open. A reader
    landing in the window finds no v2 bundles and serves the superseded v1 model for every
    position, with no error and no caveat — during a retrain, on the live product.

    Same temp-file + ``os.replace`` pattern the repo already uses in
    ``league_transactions._atomic_write_json`` and ``nflverse_usage._atomic_write_json``;
    ``os.replace`` is atomic on POSIX, so a reader sees either the old manifest or the new
    one and never a partial file. The temp file is created in the destination directory so
    the replace never crosses a filesystem boundary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, indent=2) + "\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

# ── Metadata columns excluded from all model feature sets ─────────────────────
_META_COLS = {
    "player_id", "position", "feature_season", "team",
    "depth_chart_position", "aging_curve_position",
}

# ── Unified feature list for v1.1 control (same logic as v1, minus 4 exclusions)
FEATURES_UNIFIED = sorted([
    f for f in ENGINE_B_ALLOWED_FEATURES
    if f not in _META_COLS
    and f != "te_role_is_risk_profile"
    # Position-exclusive optional features are PER-POSITION only and must never
    # enter the unified matrix, which fits every position together behind a
    # median imputer. There they are not sparse — they are a wrong constant.
    and not f.startswith("ngs_")
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
    if metrics_model["rmse"] < metrics_baseline["rmse"]:
        improvements += 1
    if metrics_model["r2"] > metrics_baseline["r2"]:
        improvements += 1
    if metrics_model["spearman"] > metrics_baseline["spearman"]:
        improvements += 1
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


def _make_imputer(strategy: str) -> SimpleImputer:
    """The one imputer constructor for every fit site in this file.

    `keep_empty_features=True` keeps a column that is all-NaN in the fit rows, imputed to
    0.0, instead of sklearn's default of silently dropping it. Without it the bundle's
    `"features"` list is one longer than the matrix the ridge was fit on: the artifact
    advertises an input the model has no coefficient for, a live value for that feature is
    discarded at inference, and anything zipping features with `coef_` misattributes every
    coefficient after the dropped slot. Mirrors `backtest_harness.py` (`_build_fold_data`),
    which has fit with this setting since 2026-05-14 — training and backtest must agree on
    the input set by construction. Shape honesty only: a constant-0.0 column takes a ~0
    coefficient, so predictions are unchanged. Pinned by tests/test_train_engine_b_bundle_width.py.
    """
    return SimpleImputer(strategy=strategy, keep_empty_features=True)


def _fit_position_ridge(
    pos_df: pd.DataFrame,
    features: list[str],
    alpha: float,
) -> tuple[Ridge, SimpleImputer, np.ndarray, np.ndarray]:
    X_raw = pos_df[features]
    y = pos_df[OUTCOME_COLUMN].values
    imputer = _make_imputer("median")
    X = imputer.fit_transform(X_raw)
    model = Ridge(alpha=alpha)
    model.fit(X, y)
    return model, imputer, X, y


def train_te_deployment_model(df: pd.DataFrame, run_dir: Path) -> dict[str, Any]:
    """Train only the deployable TE v3 artifact. Does not touch manifest or other positions."""
    train_df = df[(df["training_eligible"] == True) & (df["position"] == "TE")].copy()  # noqa: E712  pandas boolean mask
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
    # Hold out the same seasons every other position holds out. Scoring the fit on its own
    # X measured memorisation, not generalisation, and `promotion_warranted: None` below
    # meant the >=2/3 composite gate was never invoked for TE at all — so the one position
    # that ever failed a fair test (run 20260513T012309Z, 0 improvements of 3) shipped
    # afterwards with no test having been taken. Same split/fit/score/gate shape as
    # `_train_position`, so TE is judged by the standard the others are judged by.
    fit_df = train_df[~train_df["feature_season"].isin(HOLDOUT_SEASONS)]
    holdout_df = train_df[train_df["feature_season"].isin(HOLDOUT_SEASONS)]
    if holdout_df.empty:
        raise ValueError(
            f"TE deployment training has no holdout rows in seasons {HOLDOUT_SEASONS}; "
            "refusing to report in-sample metrics as validation"
        )

    model, imputer, X, y = _fit_position_ridge(
        fit_df,
        features,
        alpha=TE_MODEL_CHANGE_ALPHA,
    )
    X_test = imputer.transform(holdout_df[features])
    y_test = holdout_df[OUTCOME_COLUMN].values
    y_pred = model.predict(X_test)
    metrics_model = _score(y_test, y_pred)
    # Baseline on the SAME held-out rows — comparing against a baseline measured on the
    # training rows would compare two different populations.
    metrics_baseline = _score(y_test, holdout_df["ppg_t"].values)
    improvements, promotion_warranted = _gate(metrics_model, metrics_baseline)

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

    # te_role_is_risk_profile dropped from the TE contract 2026-06-26 (contamination
    # artifact); its coefficient is no longer reported. See the re-derivation spec.
    result = {
        "position": "TE",
        "skipped": False,
        "alpha_selected": TE_MODEL_CHANGE_ALPHA,
        "features": features,
        "n_features": len(features),
        "train_rows": len(X),
        "test_rows": len(holdout_df),
        "holdout_seasons": list(HOLDOUT_SEASONS),
        "metrics_model": metrics_model,
        "metrics_baseline": metrics_baseline,
        "improvements": improvements,
        "promotion_warranted": promotion_warranted,
        "artifact_path": str(artifact_path),
    }
    with open(report_path, "w") as f:
        json.dump(result, f, indent=2)
    return result


# ── Stage 6.1: v1.1 Unified Control ──────────────────────────────────────────

def train_v1_1_control(df: pd.DataFrame, run_dir: Path) -> dict[str, Any]:
    """Unified Ridge with Phase 6 exclusions applied. Validation artifact only."""
    train_df = df[df["training_eligible"] == True].copy()  # noqa: E712  pandas boolean mask

    available_features = [f for f in FEATURES_UNIFIED if f in train_df.columns]

    X_train_raw = train_df[~train_df["feature_season"].isin(HOLDOUT_SEASONS)][available_features]
    y_train     = train_df[~train_df["feature_season"].isin(HOLDOUT_SEASONS)][OUTCOME_COLUMN].values
    X_test_raw  = train_df[ train_df["feature_season"].isin(HOLDOUT_SEASONS)][available_features]
    y_test      = train_df[ train_df["feature_season"].isin(HOLDOUT_SEASONS)][OUTCOME_COLUMN].values
    baseline    = X_test_raw["ppg_t"].values

    print(f"  v1.1 unified — train {len(X_train_raw)} rows, holdout {len(X_test_raw)} rows")
    imputer = _make_imputer("mean")
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

    # OPTIONAL-IF-PRESENT (David's word, 2026-07-31): position-exclusive NGS
    # features join this position's matrix only when the dataset actually carries
    # them. A dataset built before the NGS streams landed trains exactly as it did
    # before — absence is normal, never an error. The required contract above is
    # untouched, which is what keeps the QB-1 walk-forward and the pinned
    # per-position contracts seeing the identical set they saw before.
    optional = optional_features_present(pos, pos_df.columns)
    if optional:
        print(f"  {pos}: +{len(optional)} optional NGS features present: {optional}")
    available = sorted(available + optional)

    validate_position_feature_contract(pos, available)

    X_train_raw = pos_df[~pos_df["feature_season"].isin(HOLDOUT_SEASONS)][available]
    y_train     = pos_df[~pos_df["feature_season"].isin(HOLDOUT_SEASONS)][OUTCOME_COLUMN].values
    X_test_raw  = pos_df[ pos_df["feature_season"].isin(HOLDOUT_SEASONS)][available]
    y_test      = pos_df[ pos_df["feature_season"].isin(HOLDOUT_SEASONS)][OUTCOME_COLUMN].values
    baseline    = X_test_raw["ppg_t"].values

    print(f"  {pos}: train {len(X_train_raw)} rows, holdout {len(X_test_raw)} rows, {len(available)} features")

    imputer = _make_imputer("median")
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
        train_df = df[df["training_eligible"] == True].copy()  # noqa: E712  pandas boolean mask
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
    train_df = df[df["training_eligible"] == True].copy()  # noqa: E712  pandas boolean mask

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

    # The declared window opens BEFORE the first pickle and closes after the manifest.
    # `_train_position` writes a bundle per position, so a scorer landing between pickle
    # two and pickle three would read a half-swapped model set — guarding only the manifest
    # would cover the wrong interval. run_dir's name is the run id by construction.
    with model_publish(run_dir.name):
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
        write_manifest(manifest_path, manifest)

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
