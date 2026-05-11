#!/usr/bin/env python3
"""QB CFBD college stats backtest.

Compares:
  Model A (baseline) : pick, round, age
  Model B (enriched) : pick, round, age + 10 QB college features from CFBD

Fetches live CFBD data for FULL/PARTIAL QBs using resources/cfbd_qb_id_map.json
(Gemini probe, 95.2% combined coverage, 2026-05-11).

NONE players (6 FCS/small-program QBs) receive all-None features and are
imputed to the training mean — they dilute signal slightly but are included
to avoid selection bias in the holdout evaluation.

Usage:
    python scripts/backtest_qb_cfbd.py

Output:
    docs/validation/qb_cfbd_backtest_report.md
    stdout summary

Promotion criterion (matches existing backtest methodology):
    Improvement on >=2 of 3 metrics vs. baseline on the held-out set:
      RMSE reduction >= 5%
      R² gain        >= 0.02
      Spearman gain  >= 0.03

Sample size caveat: QB holdout is 39 rows. Results are directionally
informative but confidence intervals are wide — interpret conservatively.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.dynasty_genius.adapters.cfbd_qb_adapter import (
    QB_CFBD_FEATURES,
    fetch_qb_college_stats,
)

BASELINE_CSV = ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
ID_MAP_PATH  = ROOT / "resources" / "cfbd_qb_id_map.json"
REPORT_PATH  = ROOT / "docs" / "validation" / "qb_cfbd_backtest_report.md"
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

MODEL_A_FEATURES = ["pick", "round", "age"]
MODEL_B_FEATURES = MODEL_A_FEATURES + QB_CFBD_FEATURES
OUTCOME = "y24_ppg"

RMSE_THRESHOLD     = 0.05
R2_THRESHOLD       = 0.02
SPEARMAN_THRESHOLD = 0.03
RATE_LIMIT_SLEEP   = 0.15   # seconds between player fetches


# ── Metric helpers ────────────────────────────────────────────────────────────

def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def spearman(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 4:
        return float("nan")
    return float(stats.spearmanr(y_true, y_pred).statistic)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "rmse":     rmse(y_true, y_pred),
        "r2":       float(r2_score(y_true, y_pred)),
        "spearman": spearman(y_true, y_pred),
    }


def fit_predict(X_train, y_train, X_test) -> np.ndarray:
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    return model.predict(X_test)


# ── CFBD data fetch ───────────────────────────────────────────────────────────

def fetch_all_qb_stats(df: pd.DataFrame, id_map: dict, api_key: str) -> pd.DataFrame:
    """Fetch CFBD college stats for every QB row; return enriched DataFrame."""
    records = []
    total = len(df)
    for i, (_, row) in enumerate(df.iterrows(), 1):
        name = row["pfr_player_name"]
        entry = id_map.get(name, {})
        coverage = entry.get("coverage", "NONE")

        if coverage in ("FULL", "PARTIAL"):
            cfbd_name = entry.get("cfbd_name", name)
            year      = entry.get("college_season_year")
            college   = entry.get("cfbd_college")
            print(f"  [{i:3d}/{total}] fetching {cfbd_name} ({year}) ...", end=" ", flush=True)
            stats_row = fetch_qb_college_stats(
                cfbd_name,
                year,
                api_key=api_key,
                college_team=college,
            )
            fetched = sum(1 for v in stats_row.values() if v is not None)
            print(f"{fetched}/{len(QB_CFBD_FEATURES)} features")
            time.sleep(RATE_LIMIT_SLEEP)
        else:
            print(f"  [{i:3d}/{total}] {name}: NONE — using nulls")
            stats_row = {f: None for f in QB_CFBD_FEATURES}

        records.append(stats_row)

    enriched = df.reset_index(drop=True).copy()
    for feat in QB_CFBD_FEATURES:
        enriched[feat] = [r[feat] for r in records]
    return enriched


# ── Model training + evaluation ───────────────────────────────────────────────

def run_comparison(df: pd.DataFrame) -> dict:
    train = df[df["is_training"] == 1]
    test  = df[df["is_training"] == 0]

    y_train = train[OUTCOME].values
    y_test  = test[OUTCOME].values

    # Model A — baseline only
    imp_a = SimpleImputer(strategy="mean")
    X_train_a = imp_a.fit_transform(train[MODEL_A_FEATURES].values.astype(float))
    X_test_a  = imp_a.transform(test[MODEL_A_FEATURES].values.astype(float))
    pred_a    = fit_predict(X_train_a, y_train, X_test_a)
    metrics_a = evaluate(y_test, pred_a)

    # Model B — baseline + QB CFBD features
    imp_b = SimpleImputer(strategy="mean")
    X_train_b = imp_b.fit_transform(train[MODEL_B_FEATURES].values.astype(float))
    X_test_b  = imp_b.transform(test[MODEL_B_FEATURES].values.astype(float))
    pred_b    = fit_predict(X_train_b, y_train, X_test_b)
    metrics_b = evaluate(y_test, pred_b)

    # Lift
    rmse_pct_reduction = (metrics_a["rmse"] - metrics_b["rmse"]) / metrics_a["rmse"]
    r2_gain            = metrics_b["r2"] - metrics_a["r2"]
    spearman_gain      = metrics_b["spearman"] - metrics_a["spearman"]

    # Promotion gate
    improvements = sum([
        rmse_pct_reduction >= RMSE_THRESHOLD,
        r2_gain            >= R2_THRESHOLD,
        spearman_gain      >= SPEARMAN_THRESHOLD,
    ])
    promotion_warranted = improvements >= 2

    null_counts = {f: df[f].isna().sum() for f in QB_CFBD_FEATURES}

    return {
        "n_train":            len(train),
        "n_test":             len(test),
        "metrics_a":          metrics_a,
        "metrics_b":          metrics_b,
        "rmse_pct_reduction": rmse_pct_reduction,
        "r2_gain":            r2_gain,
        "spearman_gain":      spearman_gain,
        "improvements":       improvements,
        "promotion_warranted": promotion_warranted,
        "null_counts":        null_counts,
    }


# ── Coverage stats ────────────────────────────────────────────────────────────

def coverage_summary(df: pd.DataFrame, id_map: dict) -> dict:
    counts = {"FULL": 0, "PARTIAL": 0, "NONE": 0}
    for name in df["pfr_player_name"]:
        counts[id_map.get(name, {}).get("coverage", "NONE")] += 1
    total = len(df)
    return {
        "total":   total,
        "full":    counts["FULL"],
        "partial": counts["PARTIAL"],
        "none":    counts["NONE"],
        "pct":     (counts["FULL"] + counts["PARTIAL"]) / total,
    }


# ── Report ────────────────────────────────────────────────────────────────────

def write_report(results: dict, coverage: dict) -> None:
    a = results["metrics_a"]
    b = results["metrics_b"]
    pw = results["promotion_warranted"]

    null_lines = "\n".join(
        f"  {f}: {n} null{'s' if n != 1 else ''}"
        for f, n in results["null_counts"].items()
    )

    rmse_pass     = "✓" if results["rmse_pct_reduction"] >= RMSE_THRESHOLD else "✗"
    r2_pass       = "✓" if results["r2_gain"] >= R2_THRESHOLD else "✗"
    spearman_pass = "✓" if results["spearman_gain"] >= SPEARMAN_THRESHOLD else "✗"
    gate_verdict  = "PASS — promotion warranted" if pw else "FAIL — promotion NOT warranted"
    if pw:
        interp = (
            "The enriched QB model meets the promotion gate. QB college features may be "
            "promoted from [] to model_input in POSITION_FEATURE_MATRIX[\"QB\"]. "
            "Recommend a secondary review before training the live model."
        )
    else:
        interp = (
            "The enriched QB model does not meet the promotion gate. QB college features "
            "remain context_signal only. POSITION_FEATURE_MATRIX[\"QB\"] stays as defined "
            "(empty or context-only). Do not promote without David's explicit override."
        )

    text = f"""---
baseline_model: pick_round_age
enriched_model: pick_round_age_cfbd_qb
held_out_n: {results['n_test']}
metric_delta_rmse_pct: {results['rmse_pct_reduction']:.4f}
metric_delta_r2: {results['r2_gain']:.4f}
metric_delta_spearman: {results['spearman_gain']:.4f}
improvements_meeting_threshold: {results['improvements']}/3
promotion_warranted: {str(pw).lower()}
cfbd_coverage_pct_qb: {coverage['pct']:.4f}
cfbd_coverage_none_players: {coverage['none']}
---

# QB CFBD Backtest Report

Generated: 2026-05-11
Methodology matches `backtest_engine_a_cfbd_only.py` (Task 4).

## Setup

- Training QBs : {results['n_train']}
- Holdout QBs  : {results['n_test']}  ⚠️ small — interpret conservatively
- CFBD coverage: {coverage['full']} FULL, {coverage['partial']} PARTIAL, {coverage['none']} NONE ({coverage['pct']:.1%} combined)
- Features for Model A: {', '.join(MODEL_A_FEATURES)}
- Features for Model B: {', '.join(MODEL_B_FEATURES)}

## Results

| Metric    | Model A (baseline) | Model B (+ QB CFBD) | Delta | Threshold | Pass? |
|-----------|-------------------|---------------------|-------|-----------|-------|
| RMSE      | {a['rmse']:.3f}           | {b['rmse']:.3f}               | {results['rmse_pct_reduction']:+.1%} reduction | ≥5%   | {rmse_pass} |
| R²        | {a['r2']:.3f}             | {b['r2']:.3f}                 | {results['r2_gain']:+.3f}            | ≥0.02 | {r2_pass} |
| Spearman  | {a['spearman']:.3f}       | {b['spearman']:.3f}           | {results['spearman_gain']:+.3f}      | ≥0.03 | {spearman_pass} |

**Metrics meeting threshold:** {results['improvements']}/3
**Promotion gate (≥2/3):** {gate_verdict}

## Null feature counts (imputed to training mean)

{null_lines}

## Interpretation

{interp}

## Caveats

- Holdout n={results['n_test']} QBs is below the 50-row threshold used for skill positions.
  Confidence intervals on all metrics are wide. A pass here is directional, not conclusive.
- NONE players ({coverage['none']} FCS/small-program QBs) are imputed to mean — they add
  noise, which slightly biases against the enriched model.
- QB outcome (y24_ppg) has high variance by position nature. Draft capital (pick/round)
  already captures most of the signal for QBs.
"""

    REPORT_PATH.write_text(text)
    print(f"\nReport written to {REPORT_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    api_key = os.getenv("CFBD_API_KEY", "").strip()
    if not api_key:
        print("ERROR: CFBD_API_KEY not set in .env — cannot fetch QB stats.")
        sys.exit(1)

    print("Loading training data ...")
    df_all = pd.read_csv(BASELINE_CSV)
    df = df_all[df_all["position"] == "QB"].copy()
    df["pick"]  = pd.to_numeric(df["pick"],  errors="coerce")
    df["round"] = pd.to_numeric(df["round"], errors="coerce")
    df["age"]   = pd.to_numeric(df["age"],   errors="coerce")
    df[OUTCOME] = pd.to_numeric(df[OUTCOME], errors="coerce")
    df = df.dropna(subset=["pick", "round", "age", OUTCOME])
    print(f"  {len(df)} QB rows ({df['is_training'].sum():.0f} train, "
          f"{(df['is_training']==0).sum()} holdout)")

    print("\nLoading CFBD player ID map ...")
    with open(ID_MAP_PATH) as f:
        id_map = json.load(f)

    cov = coverage_summary(df, id_map)
    print(f"  Coverage: {cov['full']} FULL, {cov['partial']} PARTIAL, "
          f"{cov['none']} NONE ({cov['pct']:.1%} combined)")

    print(f"\nFetching CFBD stats for {cov['full'] + cov['partial']} QBs ...")
    df_enriched = fetch_all_qb_stats(df, id_map, api_key)

    print("\nRunning Model A vs Model B comparison ...")
    results = run_comparison(df_enriched)

    a = results["metrics_a"]
    b = results["metrics_b"]
    print(f"\n{'─'*50}")
    print(f"  Model A (baseline) — RMSE {a['rmse']:.3f}  R² {a['r2']:.3f}  Spearman {a['spearman']:.3f}")
    print(f"  Model B (+ QB CFBD) — RMSE {b['rmse']:.3f}  R² {b['r2']:.3f}  Spearman {b['spearman']:.3f}")
    print(f"  Metrics meeting threshold: {results['improvements']}/3")
    verdict = "PASS — promotion warranted" if results["promotion_warranted"] else "FAIL — not promoted"
    print(f"  Promotion gate: {verdict}")
    print(f"{'─'*50}\n")

    write_report(results, cov)


if __name__ == "__main__":
    main()
