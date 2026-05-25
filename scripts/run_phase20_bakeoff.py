"""Phase 20 — Head A v3 Full Board Activation Bake-Off.

Reruns the Phase 19 Head A bakeoff harness with Phase 20 feature contracts:

  W1 — WR: Trimmed 5-feature set (drops three collinear share metrics from W3).
  W2 — RB: Option B efficiency features (no games denominator).
  W3 — QB: 4-feature contract from cfbd_qb_adapter.py.

Gate thresholds (stricter than Phase 19):
  RMSE improvement ≥ 7% vs. row-aligned baseline (Phase 19 used 2%).
  2-of-3 required (RMSE + Spearman + NDCG@10).

Does NOT promote any model pkl or update any manifest.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Reuse all validated harness infrastructure from Phase 19
from scripts.run_head_a_bakeoff import (  # noqa: E402
    BASELINE_FEATURES,
    WALK_FORWARD_FOLDS,
    HeadAGateResult,
    _filter_available_features,
    _load_all_rows,
    _run_aligned_comparison,
    _run_standalone,
)

V3_CSV = ROOT / "app/data/training/prospects_with_outcomes_v3.csv"
OUTPUT_DIR = ROOT / "app/data/backtest/phase20"
OOF_LOG_DIR = OUTPUT_DIR / "oof_logs"

# Phase 20 gate — stricter than Phase 19 (2% → 7%)
RMSE_IMPROVEMENT_PCT_GATE_P20 = 7.0

# Phase 20 feature contracts (David-approved 2026-05-24)
HEAD_A_FEATURES_PHASE20: dict[str, list[str]] = {
    "WR": [
        "nfl_pick", "nfl_round", "final_college_age",
        "wr_breakout_age",
        "wr_yards_per_reception_career",
    ],
    "RB": [
        "nfl_pick", "nfl_round", "final_college_age",
        "rb_final_dominator",
        "rb_school_sp_plus",
        "rb_yards_per_carry_final",
        "rb_yards_per_reception_career",
    ],
    "QB": [
        "nfl_pick", "nfl_round", "final_college_age",
        "qb_completion_pct_final",
        "qb_yards_per_attempt_final",
        "qb_td_int_ratio_final",
        "qb_sack_rate_final",
    ],
}


def evaluate_phase20_gates(
    baseline_rmse: float,
    candidate_rmse: float,
    baseline_spearman: float,
    candidate_spearman: float,
    baseline_ndcg: float,
    candidate_ndcg: float,
) -> HeadAGateResult:
    """Phase 20 gates: 7% RMSE improvement required (no TE safety guard)."""
    rmse_improvement_pct = (baseline_rmse - candidate_rmse) / baseline_rmse * 100.0
    rmse_gate = rmse_improvement_pct >= RMSE_IMPROVEMENT_PCT_GATE_P20
    spearman_gate = candidate_spearman > baseline_spearman
    ndcg_gate = candidate_ndcg > baseline_ndcg

    metrics_passed = sum([rmse_gate, spearman_gate, ndcg_gate])
    fail_reasons: list[str] = []
    if not rmse_gate:
        fail_reasons.append("rmse_gate")
    if not spearman_gate:
        fail_reasons.append("spearman_gate")
    if not ndcg_gate:
        fail_reasons.append("ndcg_gate")

    passes = metrics_passed >= 2

    return HeadAGateResult(
        passes=passes,
        metrics_passed=metrics_passed,
        rmse_gate=rmse_gate,
        spearman_gate=spearman_gate,
        ndcg_gate=ndcg_gate,
        te_safety_blocked=False,
        fail_reasons=fail_reasons,
    )


def _run_position_p20(
    position: str,
    all_rows: list[dict],
    run_id: str,
    generated_at: str,
) -> dict:
    import dataclasses

    pos_rows = [r for r in all_rows if r.get("position", "").upper() == position.upper()]
    eligible = [r for r in pos_rows if r.get("censored_incomplete_arc", "0") != "1"]
    n_total = len(pos_rows)
    n_eligible = len(eligible)
    print(f"\n  {position}: {n_total} total rows, {n_eligible} non-censored")

    spec_features = HEAD_A_FEATURES_PHASE20.get(position)
    if spec_features is None:
        print(f"    [SKIP] No Phase 20 feature contract defined for {position}")
        return {"position": position, "skipped": True, "reason": "no_phase20_contract"}

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

            gate = evaluate_phase20_gates(
                baseline_rmse=abl.get("oof_rmse", float("inf")),
                candidate_rmse=cand.get("oof_rmse", float("inf")),
                baseline_spearman=abl.get("mean_fold_spearman", 0.0),
                candidate_spearman=cand.get("mean_fold_spearman", 0.0),
                baseline_ndcg=abl.get("mean_fold_ndcg_at_10", 0.0),
                candidate_ndcg=cand.get("mean_fold_ndcg_at_10", 0.0),
            )
            status = "PASS" if gate.passes else "FAIL"
            rmse_pct = (abl.get("oof_rmse", 0) - cand.get("oof_rmse", 0)) / abl.get("oof_rmse", 1) * 100
            print(f"    Gate [{cand_name}]: {status}  "
                  f"aligned_baseline RMSE={abl.get('oof_rmse')}  "
                  f"candidate RMSE={cand.get('oof_rmse')}  "
                  f"RMSE_delta={rmse_pct:.1f}%  "
                  f"metrics={gate.metrics_passed}/3  "
                  f"fail={gate.fail_reasons or ['none']}")
            candidate_gates[cand_name] = dataclasses.asdict(gate)

    oof_path = _write_oof_log_p20(position, ridge_result, gbt_result, run_id, generated_at)

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


def _to_float(value: object):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _write_oof_log_p20(position, ridge_result, gbt_result, run_id, generated_at):
    import csv as csv_mod
    OOF_LOG_DIR.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []
    for cand_name, result in [("ridge", ridge_result), ("gbt", gbt_result)]:
        if result.get("skipped"):
            continue
        for role in ("aligned_baseline", "candidate"):
            role_data = result.get(role, {})
            for pred in role_data.get("oof_predictions_all", []):
                rows_out.append({
                    "position": position, "candidate": cand_name, "role": role,
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
        writer = csv_mod.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)
    return out_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]
    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("Phase 20 — Head A v3 Full Board Activation Bake-Off")
    print(f"  Run ID      : {run_id}")
    print(f"  Generated   : {generated_at}")
    print(f"  CSV         : {V3_CSV}")
    print(f"  Folds       : {WALK_FORWARD_FOLDS}")
    print(f"  RMSE gate   : ≥{RMSE_IMPROVEMENT_PCT_GATE_P20}% (Phase 20, stricter than Phase 19 2%)")

    all_rows = _load_all_rows()
    print(f"  Total rows  : {len(all_rows)}")

    position_results: dict[str, dict] = {}
    for position in ["WR", "RB", "QB"]:
        position_results[position] = _run_position_p20(position, all_rows, run_id, generated_at)

    passing = [
        f"{pos}:{cand}"
        for pos, result in position_results.items()
        for cand, gate in result.get("gate_results", {}).items()
        if gate.get("passes")
    ]

    print(f"\n  Passing candidates: {passing or ['none']}")

    def _strip_raw(obj):
        if isinstance(obj, dict):
            return {k: _strip_raw(v) for k, v in obj.items() if k != "oof_predictions_all"}
        if isinstance(obj, list):
            return [_strip_raw(item) for item in obj]
        return obj

    artifact = {
        "run_id": run_id,
        "generated_at": generated_at,
        "scope": "Phase 20 — Head A v3 Full Board Activation (WR/RB/QB)",
        "csv_source": V3_CSV.name,
        "walk_forward_folds": [
            {"train_max_year": t, "test_year": v} for t, v in WALK_FORWARD_FOLDS
        ],
        "gate_thresholds": {
            "rmse_improvement_pct": RMSE_IMPROVEMENT_PCT_GATE_P20,
            "metrics_required": 2,
        },
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
        },
    }

    out_path = OUTPUT_DIR / f"phase20_bakeoff_{generated_at}_{run_id}.json"
    out_path.write_text(json.dumps(_strip_raw(artifact), indent=2))
    print(f"\n  Artifact: {out_path}")
    print("  promotion_decision: REQUIRES_DAVID_REVIEW")


if __name__ == "__main__":
    main()
