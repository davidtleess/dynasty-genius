"""Phase 16.4 WR College Bake-Off Harness.

Runs leave-one-draft-class-out Ridge regression for baseline and candidate
feature sets. Evaluates a three-part promotion gate. Writes a JSON artifact.
Does NOT touch model pkl files or latest.json.

Usage:
    .venv/bin/python3.14 scripts/run_wr_college_bakeoff.py
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
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ENRICHED_CSV = ROOT / "app/data/training/prospects_with_outcomes_phase16.csv"
OUTPUT_DIR = ROOT / "app/data/backtest/phase16"

# LOOCV cohort: draft classes with PFF coverage in the manifest
TRAINING_YEARS = set(range(2018, 2025))

# Promotion gate thresholds (Phase 16 spec)
MAE_IMPROVEMENT_PCT_GATE = 3.0  # ≥3% aggregate MAE improvement required
FOLDS_PASSING_GATE = 3          # ≥3 of N folds must show improvement
TE_MAE_DELTA_GATE = 0.01        # TE MAE must not regress by ≥1% absolute

BASELINE_FEATURES = ["pick", "round", "age"]
CANDIDATE_SETS = {
    "baseline": BASELINE_FEATURES,
    "baseline_ryptpa": BASELINE_FEATURES + ["ryptpa"],
    "baseline_yprr_college": BASELINE_FEATURES + ["yprr_college"],
    "baseline_ryptpa_yprr": BASELINE_FEATURES + ["ryptpa", "yprr_college"],
}


@dataclasses.dataclass
class BakeoffGateResult:
    passes: bool
    mae_improvement_pct: float
    folds_improved: int
    total_folds: int
    te_mae_delta: float
    fail_reasons: list[str]


def evaluate_promotion_gate(
    baseline_mae: float,
    candidate_mae: float,
    folds_improved: int,
    total_folds: int,
    te_mae_delta: float,
) -> BakeoffGateResult:
    """Three-part promotion gate per Phase 16 spec."""
    mae_improvement_pct = (baseline_mae - candidate_mae) / baseline_mae * 100
    fail_reasons: list[str] = []

    if mae_improvement_pct < MAE_IMPROVEMENT_PCT_GATE:
        fail_reasons.append("mae_improvement")
    if folds_improved < FOLDS_PASSING_GATE:
        fail_reasons.append("fold_consistency")
    if te_mae_delta >= TE_MAE_DELTA_GATE:
        fail_reasons.append("te_regression")

    return BakeoffGateResult(
        passes=len(fail_reasons) == 0,
        mae_improvement_pct=round(mae_improvement_pct, 4),
        folds_improved=folds_improved,
        total_folds=total_folds,
        te_mae_delta=round(te_mae_delta, 6),
        fail_reasons=fail_reasons,
    )


def compute_vif(X: np.ndarray, feature_idx: int) -> float:
    """Variance Inflation Factor for the feature at feature_idx."""
    from sklearn.linear_model import LinearRegression
    X_others = np.delete(X, feature_idx, axis=1)
    target = X[:, feature_idx]
    if X_others.shape[1] == 0:
        return 1.0
    r2 = LinearRegression().fit(X_others, target).score(X_others, target)
    return 1.0 / (1.0 - r2) if r2 < 1.0 else float("inf")


def _to_float(value: str | None) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _load_training_rows(position: str) -> list[dict]:
    if not ENRICHED_CSV.exists():
        raise FileNotFoundError(
            f"Enriched CSV not found: {ENRICHED_CSV}\n"
            "Run scripts/build_college_features.py first."
        )
    with ENRICHED_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r.get("position", "").upper() == position]


def _run_loocv(
    rows: list[dict],
    feature_names: list[str],
    target: str = "y24_ppg",
    alpha: float = 100.0,
) -> dict:
    """Leave-one-draft-class-out Ridge regression over TRAINING_YEARS."""
    eligible = []
    for row in rows:
        draft_year = int(row.get("season", 0))
        if draft_year not in TRAINING_YEARS:
            continue
        values = {f: _to_float(row.get(f)) for f in feature_names}
        y_val = _to_float(row.get(target))
        if y_val is None or any(v is None for v in values.values()):
            continue
        eligible.append({
            "draft_year": draft_year,
            "features": [values[f] for f in feature_names],
            "target": y_val,
        })

    years = sorted({r["draft_year"] for r in eligible})
    if len(years) < 2:
        return {"error": "insufficient_data", "n_rows": len(eligible), "n_folds": 0}

    fold_results = []
    for test_year in years:
        train = [r for r in eligible if r["draft_year"] != test_year]
        test = [r for r in eligible if r["draft_year"] == test_year]
        if not train or not test:
            continue

        X_train = np.array([r["features"] for r in train])
        y_train = np.array([r["target"] for r in train])
        X_test = np.array([r["features"] for r in test])
        y_test = np.array([r["target"] for r in test])

        model = Ridge(alpha=alpha).fit(X_train, y_train)
        y_pred = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        fold_results.append({
            "test_year": test_year,
            "n_train": len(train),
            "n_test": len(test),
            "mae": round(mae, 4),
        })

    mean_mae = float(np.mean([f["mae"] for f in fold_results]))
    return {
        "n_rows": len(eligible),
        "n_folds": len(fold_results),
        "fold_results": fold_results,
        "mean_mae": round(mean_mae, 4),
    }


def _count_folds_improved(baseline_folds: list[dict], candidate_folds: list[dict]) -> int:
    """Count folds where candidate MAE < baseline MAE, matched by test_year."""
    baseline_by_year = {f["test_year"]: f["mae"] for f in baseline_folds}
    count = 0
    for fold in candidate_folds:
        base_mae = baseline_by_year.get(fold["test_year"])
        if base_mae is not None and fold["mae"] < base_mae:
            count += 1
    return count


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("Phase 16.4 WR College Bake-Off")
    print(f"  Run ID: {run_id}")
    print(f"  Enriched CSV: {ENRICHED_CSV}")
    print(f"  Training years (LOOCV): {sorted(TRAINING_YEARS)}")

    wr_rows = _load_training_rows("WR")
    te_rows = _load_training_rows("TE")
    print(f"  WR rows loaded: {len(wr_rows)} | TE rows loaded: {len(te_rows)}")

    # Coverage check: only include yprr_college candidate if ≥50% WR rows have it
    yprr_covered = sum(1 for r in wr_rows if _to_float(r.get("yprr_college")) is not None
                       and int(r.get("season", 0)) in TRAINING_YEARS)
    yprr_eligible = sum(1 for r in wr_rows if int(r.get("season", 0)) in TRAINING_YEARS)
    yprr_coverage_pct = yprr_covered / yprr_eligible * 100 if yprr_eligible else 0
    print(f"  YPRR college coverage (in LOOCV years): {yprr_covered}/{yprr_eligible} = {yprr_coverage_pct:.1f}%")

    ryptpa_covered = sum(1 for r in wr_rows if _to_float(r.get("ryptpa")) is not None
                         and int(r.get("season", 0)) in TRAINING_YEARS)
    print(f"  RYPTPA coverage (in LOOCV years): {ryptpa_covered}/{yprr_eligible}")

    # Exclude combined candidate if yprr coverage too low
    active_candidates = {
        k: v for k, v in CANDIDATE_SETS.items()
        if "yprr_college" not in v or yprr_coverage_pct >= 50
    }
    if len(active_candidates) < len(CANDIDATE_SETS):
        excluded = set(CANDIDATE_SETS) - set(active_candidates)
        print(f"  [WARN] Excluded low-coverage candidates: {excluded}")

    # Run LOOCV for each candidate
    candidate_results: dict[str, dict] = {}
    for name, features in active_candidates.items():
        print(f"\n  Running: {name}  features={features}")
        result = _run_loocv(wr_rows, features)
        candidate_results[name] = result
        if "error" not in result:
            print(f"    n={result['n_rows']}, folds={result['n_folds']}, mean_mae={result['mean_mae']}")
        else:
            print(f"    {result['error']}")

    # VIF check for the combined candidate
    vif_report: dict = {}
    combined_eligible = [
        r for r in wr_rows
        if int(r.get("season", 0)) in TRAINING_YEARS
        and _to_float(r.get("ryptpa")) is not None
        and _to_float(r.get("yprr_college")) is not None
    ]
    if len(combined_eligible) >= 10:
        X_vif = np.array([
            [_to_float(r["ryptpa"]), _to_float(r["yprr_college"])]
            for r in combined_eligible
        ])
        vif_ryptpa = compute_vif(X_vif, 0)
        vif_yprr = compute_vif(X_vif, 1)
        vif_report = {
            "n_rows": len(combined_eligible),
            "vif_ryptpa": round(vif_ryptpa, 3),
            "vif_yprr_college": round(vif_yprr, 3),
            "collinear": vif_ryptpa > 5 or vif_yprr > 5,
            "recommendation": (
                "retain_ryptpa_only" if vif_yprr > vif_ryptpa and vif_ryptpa > 5
                else "retain_yprr_only" if vif_ryptpa > vif_yprr and vif_yprr > 5
                else "both_acceptable"
            ),
        }
        print(f"\n  VIF: RYPTPA={vif_ryptpa:.3f}, YPRR={vif_yprr:.3f} — {vif_report['recommendation']}")
    else:
        print(f"\n  VIF: skipped (only {len(combined_eligible)} rows with both features)")
        vif_report = {"n_rows": len(combined_eligible), "skipped": True}

    # TE baseline for regression guard
    te_baseline = _run_loocv(te_rows, BASELINE_FEATURES)
    te_baseline_mae = te_baseline.get("mean_mae") or 0.0
    print(f"\n  TE baseline MAE: {te_baseline_mae} ({te_baseline.get('n_rows')} rows, {te_baseline.get('n_folds')} folds)")

    # Gate evaluation for each non-baseline candidate
    gate_results: dict[str, dict] = {}
    baseline_result = candidate_results.get("baseline", {})
    baseline_mae = baseline_result.get("mean_mae")
    baseline_folds = baseline_result.get("fold_results", [])

    for name, result in candidate_results.items():
        if name == "baseline" or "error" in result:
            continue
        candidate_mae = result.get("mean_mae")
        if baseline_mae is None or candidate_mae is None:
            gate_results[name] = {"error": "missing_mae", "passes": False}
            continue

        folds_improved = _count_folds_improved(baseline_folds, result.get("fold_results", []))
        total_folds = len(result.get("fold_results", []))

        # TE MAE with candidate features that apply to TE (ryptpa only; yprr_college excluded)
        te_features = [f for f in CANDIDATE_SETS[name] if f != "yprr_college"]
        te_cand = _run_loocv(te_rows, te_features)
        te_cand_mae = te_cand.get("mean_mae") or 0.0
        te_delta = max(0.0, te_cand_mae - te_baseline_mae)

        gate = evaluate_promotion_gate(
            baseline_mae=baseline_mae,
            candidate_mae=candidate_mae,
            folds_improved=folds_improved,
            total_folds=total_folds,
            te_mae_delta=te_delta,
        )
        gate_results[name] = dataclasses.asdict(gate)
        status = "PASS" if gate.passes else "FAIL"
        reasons = gate.fail_reasons or ["all criteria met"]
        print(f"  Gate [{name}]: {status}  mae_pct={gate.mae_improvement_pct:.2f}%  "
              f"folds={folds_improved}/{total_folds}  te_delta={te_delta:.4f}  {reasons}")

    # Summary
    passing = [k for k, v in gate_results.items() if v.get("passes")]
    print(f"\n  Passing candidates: {passing or ['none']}")

    artifact = {
        "run_id": run_id,
        "generated_at": generated_at,
        "scope": "Phase 16.4 WR college efficiency signal bake-off",
        "training_years": sorted(TRAINING_YEARS),
        "gate_thresholds": {
            "mae_improvement_pct": MAE_IMPROVEMENT_PCT_GATE,
            "folds_passing": FOLDS_PASSING_GATE,
            "te_mae_delta_max": TE_MAE_DELTA_GATE,
        },
        "coverage": {
            "yprr_college_coverage_pct": round(yprr_coverage_pct, 1),
            "ryptpa_covered": ryptpa_covered,
            "loocv_eligible_wr": yprr_eligible,
        },
        "candidates": candidate_results,
        "vif_report": vif_report,
        "te_baseline": te_baseline,
        "gate_results": gate_results,
        "passing_candidates": passing,
        "promotion_decision": "PENDING_DAVID_REVIEW",
        "governance": {
            "market_data_used": False,
            "model_pkl_changed": False,
            "latest_json_changed": False,
            "raw_pff_rows_committed": False,
        },
    }

    out_path = OUTPUT_DIR / f"wr_college_bakeoff_{generated_at}_{run_id}.json"
    out_path.write_text(json.dumps(artifact, indent=2))
    print(f"\n  Artifact: {out_path.name}")
    print("  promotion_decision: PENDING_DAVID_REVIEW")


if __name__ == "__main__":
    main()
