"""A machine-readable per-horizon evaluation status (Codex review of run 154635Z).

Three words this module refuses to let prose blur:
  * "supported" — the closed history was sufficient to EVALUATE a horizon. It never means
    validated, and an evaluated horizon with an inconclusive interval says "inconclusive".
  * the bootstrap — sampling uncertainty CONDITIONAL on the fitted models (players are
    resampled from fixed fits). Not model, selection or season uncertainty; not a forecast
    interval.
  * Brier — a better Brier score alone is not a calibration proof, so the status carries
    reliability diagnostics (expected calibration error, and the slope and intercept of a
    logistic recalibration of the outcome on the forecast's logit; 1 and 0 when calibrated)
    computed from the graded predictions themselves.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

BOOTSTRAP_MEANING = (
    "bootstrap intervals are sampling uncertainty conditional on the fitted models (players "
    "resampled from fixed fits); not model, selection or season uncertainty, and not a forecast interval"
)
SUPPORTED_MEANING = "closed history sufficient to evaluate; not validation"
BRIER_MEANING = (
    "a better Brier score alone is not a calibration proof; read the expected calibration error and "
    "the reliability slope/intercept (1 and 0 when calibrated) beside it"
)
STATUS_EVALUATED = "evaluated"
STATUS_NO_EVALUATED_FOLD = "no_evaluated_policy_fold"
STATUS_UNSUPPORTED = "unsupported"
CALIBRATION_BINS = 10


def calibration_diagnostics(truths, probs, *, bins: int = CALIBRATION_BINS) -> dict[str, Any]:
    y = np.asarray(truths, dtype=float)
    p = np.asarray(probs, dtype=float)
    keep = np.isfinite(y) & np.isfinite(p)
    y, p = y[keep], p[keep]
    out: dict[str, Any] = {
        "n": int(len(y)),
        "mean_predicted": float(p.mean()) if len(p) else float("nan"),
        "observed_rate": float(y.mean()) if len(y) else float("nan"),
        "ece": float("nan"), "reliability_slope": float("nan"), "reliability_intercept": float("nan"),
        "status": "ok",
    }
    if len(y) < 10 or len(np.unique(y)) < 2:
        out["status"] = "degenerate: one outcome class" if len(y) and len(np.unique(y)) < 2 else "too few rows"
        return out
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & ((p < hi) if hi < 1.0 else (p <= hi))
        if mask.any():
            ece += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    out["ece"] = float(ece)
    z = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).reshape(-1, 1)
    fit = LogisticRegression(C=1e6, max_iter=2000).fit(z, y.astype(int))
    out["reliability_slope"] = float(fit.coef_[0][0])
    out["reliability_intercept"] = float(fit.intercept_[0])
    return out


def _improvement_label(delta: dict[str, Any] | None) -> str:
    if not delta:
        return "not graded: zero evaluated policy folds"
    lo, hi = delta["ci90"]
    if lo > 0:
        return "within the reported 90% interval"
    if hi < 0:
        return "worse than the baseline within the 90% interval"
    return "inconclusive: the 90% interval includes zero"


def _predictions_for(predictions: pd.DataFrame | None, position: str, horizon: int, arm_key: str | None):
    if predictions is None or len(predictions) == 0:
        return None
    rows = predictions
    if "position" in rows.columns:
        rows = rows[rows["position"] == position]
    if "horizon" in rows.columns:
        rows = rows[rows["horizon"].astype(int) == int(horizon)]
    if arm_key is not None and "arm" in rows.columns:
        rows = rows[rows["arm"] == arm_key]
    p_col = f"policy_p_appear_year{horizon}" if f"policy_p_appear_year{horizon}" in rows.columns else f"p_appear_year{horizon}"
    y_col = f"appeared_year{horizon}"
    if p_col not in rows.columns or y_col not in rows.columns or rows.empty:
        return None
    return rows[y_col].astype(float).to_numpy(), rows[p_col].astype(float).to_numpy()


def evaluation_status(
    results: dict[str, Any], predictions: pd.DataFrame | None, *, arm_key: str | None
) -> dict[str, Any]:
    """One status per (position, horizon): counts, forecast seasons graded, the baseline
    comparison as an interval and a word, and calibration diagnostics from the predictions."""
    positions: dict[str, Any] = {}
    for position, per in results["historical"].items():
        positions[position] = {}
        for year_key, ev in per.items():
            horizon = int(str(year_key).replace("year", ""))
            if not isinstance(ev, dict):
                continue
            if ev.get("unsupported"):
                positions[position][year_key] = {"status": STATUS_UNSUPPORTED, "reason": ev.get("reason"),
                                                 "evaluated_folds": 0, "skipped_folds": 0}
                continue
            if arm_key is not None and arm_key in ev and "folds" not in ev:
                ev = ev[arm_key]
            folds = ev.get("folds", [])
            evaluated = [f for f in folds if f.get("skipped_reason") is None]
            skipped = [f for f in folds if f.get("skipped_reason") is not None]
            record: dict[str, Any] = {
                "status": STATUS_EVALUATED if evaluated else STATUS_NO_EVALUATED_FOLD,
                "evaluated_folds": len(evaluated), "skipped_folds": len(skipped),
                "forecast_seasons_graded": sorted(int(f["forecast_season"]) for f in evaluated),
                "skip_reasons": sorted({str(f["skipped_reason"])[:120] for f in skipped}),
            }
            pooled = ev.get("pooled") or {}
            block = pooled.get("policy", pooled) if pooled else {}
            delta = (block.get("points_unconditional", {}).get("delta_vs_baseline", {}).get("delta_r2")
                     if block else None)
            record["unconditional_points_delta_r2_vs_baseline"] = delta
            record["baseline_improvement"] = _improvement_label(delta if evaluated else None)
            if block.get("probability"):
                record["brier"] = block["probability"].get("brier")
                record["baseline_brier"] = block["probability"].get("baseline_brier")
            sample = _predictions_for(predictions, position, horizon, arm_key) if evaluated else None
            record["calibration"] = calibration_diagnostics(*sample) if sample is not None else {"n": 0, "status": "no graded predictions"}
            positions[position][year_key] = record
    return {
        "meaning": {"supported": SUPPORTED_MEANING, "bootstrap": BOOTSTRAP_MEANING, "brier": BRIER_MEANING,
                    "evaluated": "at least one outer policy fold graded; the interval decides the word",
                    STATUS_NO_EVALUATED_FOLD: "forecast exported, zero outer folds graded on this file"},
        "positions": positions,
    }
