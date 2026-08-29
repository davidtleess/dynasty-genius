#!/usr/bin/env python3
"""DG-017 falsifier — refit Engine B per-position WITH feature scaling and an
honestly tuned alpha, then re-run the DG-001 what-drives-it decomposition.

REPORT-ONLY EXPERIMENT. Nothing here touches deployed artifacts, the model
store, or serving code. Deployed pkls are opened read-only from the trunk model
store; every output is written run-scoped inside this worktree.

The question (DG-017, "Falsifier, cheap and decisive"): the DG-001 headline —
ppg family 52–86% of standardized coefficient weight, usage/rate features at
numerical noise — was measured on UNSCALED Ridge fits whose alpha grid
saturated at its ceiling for QB. Refit with a train-fitted StandardScaler and
an alpha tuned on a grid that is widened until the optimum is interior, re-run
the same decomposition, and see whether the attribution moves.

Three arms per position:
  A  deployed   — the shipped pkl, exactly as trunk serves it (read-only).
  B  refit-unscaled — same protocol as the deployed trainer (median imputer,
     no scaler) but with the honest alpha grid, on the train split.
  C  refit-scaled   — identical to B plus StandardScaler between imputer and
     Ridge. Scaling is the ONLY difference between B and C.

Decomposition (DG-001's method): a feature's weight is the shift in prediction
per 1-SD move of the raw feature = |coef × SD(train)|. For arm C the scaler
makes that |coef| directly. Shares are weights over their sum; families group
by name (ppg*, age, volume, usage).
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
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

WORKTREE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKTREE))

from src.dynasty_genius.models.engine_b_contract import (  # noqa: E402
    ENGINE_B_FEATURES_BY_POSITION,
    OUTCOME_COLUMN,
    optional_features_present,
    validate_no_prohibited_features,
    validate_no_temporal_leakage,
    validate_position_feature_contract,
)

# ── Read-only trunk model store (DEPLOYED artifacts; never written) ──────────
TRUNK_RUNS = Path(
    "/Users/davidleess/dynasty-genius-product/app/data/models/engine_b/runs"
)
DEPLOYED_PKLS: dict[str, Path] = {
    "QB": TRUNK_RUNS / "20260513T012309Z" / "qb_v2.pkl",
    "RB": TRUNK_RUNS / "20260513T012309Z" / "rb_v2.pkl",
    "WR": TRUNK_RUNS / "20260513T012309Z" / "wr_v2.pkl",
    "TE": TRUNK_RUNS / "20260626T165649Z" / "te_v3.pkl",
}

DATASET_PATH = WORKTREE / "app" / "data" / "training" / "engine_b_features_v2.csv"
HOLDOUT_SEASONS = [2022, 2023]

# The deployed trainer's grid (train_engine_b.py:69) — kept only to reproduce
# the shipped fit as a replay check. The honest grid below replaces it.
DEPLOYED_ALPHA_CANDIDATES = [0.1, 1.0, 10.0, 50.0, 100.0, 200.0, 500.0, 1000.0]
DEPLOYED_TE_FIXED_ALPHA = 100.0

# Honest base grid: 15 points over 7 decades. tune_alpha_honestly widens it
# whenever the selection lands on a boundary, so no ceiling is ever binding.
HONEST_BASE_GRID = list(np.logspace(-3, 4, 15))
MAX_WIDENINGS = 6

USAGE_FEATURES = frozenset({
    "snap_share", "snap_share_t_minus_1", "snap_share_t_minus_1_available",
    "tprr", "yprr", "weighted_opportunity",
    "epa_per_dropback", "cpoe", "dakota", "is_dual_threat",
})


# ── Pure helpers (unit-tested) ───────────────────────────────────────────────

def standardized_weights(
    coefs: np.ndarray, feature_names: list[str], sds: np.ndarray
) -> dict[str, float]:
    """Per-feature 1-SD effect: |coef_j × SD_j|. DG-001's weight definition."""
    if not (len(coefs) == len(feature_names) == len(sds)):
        raise ValueError(
            f"length mismatch: {len(coefs)} coefs, {len(feature_names)} names, "
            f"{len(sds)} sds"
        )
    return {
        name: float(abs(c) * abs(s))
        for name, c, s in zip(feature_names, coefs, sds)
    }


def family_of(feature: str) -> str:
    """DG-001's family grouping, by feature name."""
    if feature.startswith("ppg"):
        return "ppg"
    if feature in ("age", "aging_curve_value"):
        return "age"
    if feature == "games_t":
        return "volume"
    if feature in USAGE_FEATURES:
        return "usage"
    return "other"


def family_shares(weights: dict[str, float]) -> dict[str, float]:
    """Share of total standardized weight per family. Zero-total gives zeros."""
    totals: dict[str, float] = {}
    for feature, weight in weights.items():
        fam = family_of(feature)
        totals[fam] = totals.get(fam, 0.0) + weight
    grand = sum(totals.values())
    if grand == 0.0:
        return {fam: 0.0 for fam in totals}
    return {fam: w / grand for fam, w in totals.items()}


def tune_alpha_honestly(
    X: np.ndarray,
    y: np.ndarray,
    base_grid: list[float],
    cv: int = 5,
    max_widenings: int = MAX_WIDENINGS,
) -> tuple[RidgeCV, list[float], int]:
    """RidgeCV whose grid is widened until the selected alpha is interior.

    A boundary selection means the search wanted to leave the grid — exactly the
    failure DG-017 measured in the deployed trainer (QB pinned at 1000.0, the
    ceiling). Each widening extends the pinned side by two decades at the same
    grid density. Gives up after max_widenings and returns the boundary fit,
    reporting the count so the caller can see the tuning was not honest.
    """
    grid = sorted(float(a) for a in base_grid)
    step = 2  # points per decade at logspace density comparable to the base grid
    widenings = 0
    while True:
        model = RidgeCV(alphas=grid, cv=cv)
        model.fit(X, y)
        alpha = float(model.alpha_)
        at_floor = alpha == min(grid)
        at_ceiling = alpha == max(grid)
        if not (at_floor or at_ceiling) or widenings >= max_widenings:
            return model, grid, widenings
        if at_ceiling:
            lo = np.log10(max(grid))
            extension = np.logspace(lo, lo + 2, 2 * step + 1)[1:]
        else:
            lo = np.log10(min(grid))
            extension = np.logspace(lo - 2, lo, 2 * step + 1)[:-1]
        grid = sorted(set(grid) | {float(a) for a in extension})
        widenings += 1


# ── Scoring (same definitions as train_engine_b.py) ──────────────────────────

def _safe_spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return 0.0
    corr = scipy_stats.spearmanr(y_true, y_pred).statistic
    return float(corr) if not np.isnan(corr) else 0.0


def _score(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
        "spearman": _safe_spearman(y_true, y_pred),
    }


# ── Experiment ───────────────────────────────────────────────────────────────

def _position_frame(df: pd.DataFrame, pos: str) -> tuple[pd.DataFrame, list[str]]:
    train_df = df[df["training_eligible"] == True].copy()  # noqa: E712
    pos_df = train_df[train_df["position"] == pos].copy()
    allowed = ENGINE_B_FEATURES_BY_POSITION[pos]
    available = sorted([f for f in allowed if f in pos_df.columns])
    available = sorted(available + optional_features_present(pos, pos_df.columns))
    validate_position_feature_contract(pos, available)
    validate_no_temporal_leakage(available)
    validate_no_prohibited_features(available)
    return pos_df, available


def run_position(df: pd.DataFrame, pos: str) -> dict[str, Any]:
    pos_df, features = _position_frame(df, pos)

    train = pos_df[~pos_df["feature_season"].isin(HOLDOUT_SEASONS)]
    hold = pos_df[pos_df["feature_season"].isin(HOLDOUT_SEASONS)]
    X_train_raw, y_train = train[features], train[OUTCOME_COLUMN].values
    X_hold_raw, y_hold = hold[features], hold[OUTCOME_COLUMN].values
    baseline_metrics = _score(y_hold, X_hold_raw["ppg_t"].values)

    result: dict[str, Any] = {
        "position": pos,
        "features": features,
        "train_rows": len(train),
        "holdout_rows": len(hold),
        "baseline_ppg_t": baseline_metrics,
    }

    # ── Arm A: deployed artifact, read-only ─────────────────────────────────
    with open(DEPLOYED_PKLS[pos], "rb") as f:
        bundle = pickle.load(f)
    dep_model, dep_imputer = bundle["model"], bundle["imputer"]
    dep_features = bundle["features"]
    dep_alpha = getattr(dep_model, "alpha_", None) or bundle.get("alpha")
    # SDs on the matrix the deployed model actually trained on: TE v3 fit on
    # ALL eligible rows (train_te_deployment_model), v2 fit on the train split.
    dep_train_raw = (pos_df if pos == "TE" else train)[dep_features]
    dep_train_X = dep_imputer.transform(dep_train_raw)
    dep_sds = dep_train_X.std(axis=0, ddof=0)
    dep_weights = standardized_weights(dep_model.coef_, dep_features, dep_sds)
    dep_pred = dep_model.predict(dep_imputer.transform(X_hold_raw[dep_features]))
    result["deployed"] = {
        "version": bundle.get("version"),
        "alpha": float(dep_alpha),
        "alpha_at_grid_ceiling": float(dep_alpha) == max(DEPLOYED_ALPHA_CANDIDATES),
        "coefs": {f: float(c) for f, c in zip(dep_features, dep_model.coef_)},
        "weights_1sd": dep_weights,
        "family_shares": family_shares(dep_weights),
        "holdout_metrics": _score(y_hold, dep_pred),
        "te_holdout_contaminated": pos == "TE",  # v3 trained on all rows incl. holdout
    }

    # ── Replay check: deployed recipe on today's data ───────────────────────
    imputer_r = SimpleImputer(strategy="median")
    X_train_r = imputer_r.fit_transform(X_train_raw[dep_features])
    if pos == "TE":
        X_all_r = SimpleImputer(strategy="median").fit_transform(pos_df[dep_features])
        replay = Ridge(alpha=DEPLOYED_TE_FIXED_ALPHA)
        replay.fit(X_all_r, pos_df[OUTCOME_COLUMN].values)
        replay_alpha = DEPLOYED_TE_FIXED_ALPHA
    else:
        replay = RidgeCV(alphas=DEPLOYED_ALPHA_CANDIDATES, cv=5)
        replay.fit(X_train_r, y_train)
        replay_alpha = float(replay.alpha_)
    result["replay_check"] = {
        "alpha": replay_alpha,
        "alpha_matches_deployed": replay_alpha == float(dep_alpha),
        "max_abs_coef_delta": float(
            np.max(np.abs(replay.coef_ - dep_model.coef_))
        ),
    }

    # ── Arm B: refit UNSCALED, honest alpha ─────────────────────────────────
    imputer_b = SimpleImputer(strategy="median")
    X_train_b = imputer_b.fit_transform(X_train_raw)
    X_hold_b = imputer_b.transform(X_hold_raw)
    model_b, grid_b, widen_b = tune_alpha_honestly(X_train_b, y_train, HONEST_BASE_GRID)
    sds_b = X_train_b.std(axis=0, ddof=0)
    weights_b = standardized_weights(model_b.coef_, features, sds_b)
    result["refit_unscaled"] = {
        "alpha": float(model_b.alpha_),
        "grid_widenings": widen_b,
        "grid_span": [min(grid_b), max(grid_b)],
        "coefs": {f: float(c) for f, c in zip(features, model_b.coef_)},
        "weights_1sd": weights_b,
        "family_shares": family_shares(weights_b),
        "holdout_metrics": _score(y_hold, model_b.predict(X_hold_b)),
    }

    # ── Arm C: refit SCALED, honest alpha — the falsifier ───────────────────
    scaler = StandardScaler()
    X_train_c = scaler.fit_transform(X_train_b)
    X_hold_c = scaler.transform(X_hold_b)
    model_c, grid_c, widen_c = tune_alpha_honestly(X_train_c, y_train, HONEST_BASE_GRID)
    # Scaled coefficients are already per-1-SD of the raw feature.
    weights_c = standardized_weights(
        model_c.coef_, features, np.ones(len(features))
    )
    result["refit_scaled"] = {
        "alpha": float(model_c.alpha_),
        "grid_widenings": widen_c,
        "grid_span": [min(grid_c), max(grid_c)],
        "coefs_per_1sd": {f: float(c) for f, c in zip(features, model_c.coef_)},
        "weights_1sd": weights_c,
        "family_shares": family_shares(weights_c),
        "holdout_metrics": _score(y_hold, model_c.predict(X_hold_c)),
    }
    return result


def main() -> None:
    df = pd.read_csv(DATASET_PATH)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = WORKTREE / "runs" / run_id / "dg017_scaled_refit"
    run_dir.mkdir(parents=True, exist_ok=False)

    results = {
        "experiment": "DG-017 scaled-refit falsifier (report-only)",
        "run_id": run_id,
        "dataset": str(DATASET_PATH.relative_to(WORKTREE)),
        "holdout_seasons": HOLDOUT_SEASONS,
        "positions": {},
    }
    for pos in ("QB", "RB", "WR", "TE"):
        print(f"── {pos} ──")
        r = run_position(df, pos)
        results["positions"][pos] = r
        for arm in ("deployed", "refit_unscaled", "refit_scaled"):
            fs = r[arm]["family_shares"]
            m = r[arm]["holdout_metrics"]
            alpha = r[arm]["alpha"]
            print(
                f"  {arm:15s} alpha={alpha:<10g} "
                f"ppg={fs.get('ppg', 0):.3f} age={fs.get('age', 0):.3f} "
                f"vol={fs.get('volume', 0):.3f} usage={fs.get('usage', 0):.3f}  "
                f"RMSE={m['rmse']:.3f} R2={m['r2']:.3f} rho={m['spearman']:.3f}"
            )
        rc = r["replay_check"]
        print(
            f"  replay: alpha={rc['alpha']} match={rc['alpha_matches_deployed']} "
            f"max|Δcoef|={rc['max_abs_coef_delta']:.2e}"
        )

    out = run_dir / "results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults: {out}")


if __name__ == "__main__":
    main()
