"""TE regularization bake-off evaluator for Phase 13.3.4."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.dynasty_genius.eval.te_role_risk_experiment import (
    ROLE_RISK_CANDIDATES,
    _evaluate_candidate,
    _with_unified_penalty,
)

ALPHA_GRID = (1.0, 10.0, 50.0, 100.0, 250.0, 500.0)

BAKEOFF_CANDIDATES = {
    "baseline_only": [],
    **ROLE_RISK_CANDIDATES,
}


def evaluate_te_regularization_bakeoff(
    frame: pd.DataFrame,
    *,
    test_years: list[int],
) -> dict[str, Any]:
    experiment_frame = _with_unified_penalty(frame)
    
    # First, compute the anchor baseline: alpha=1.0, baseline_only
    anchor_baseline = _evaluate_candidate(
        experiment_frame,
        candidate_name="baseline_only",
        candidate_columns=[],
        test_years=test_years,
        alpha=1.0,
    )
    # Compute absolute means from fold data (avoids KeyError on nonexistent summary keys)
    anchor_rmse = float(np.mean([fold["baseline_rmse"] for fold in anchor_baseline["folds"]]))
    anchor_mae = float(np.mean([fold["baseline_mae"] for fold in anchor_baseline["folds"]]))

    results_by_alpha: dict[str, dict[str, Any]] = {}
    for alpha in ALPHA_GRID:
        alpha_str = str(float(alpha))
        results_by_alpha[alpha_str] = {}
        for name, columns in BAKEOFF_CANDIDATES.items():
            res = _evaluate_candidate(
                experiment_frame,
                candidate_name=name,
                candidate_columns=list(columns),
                test_years=test_years,
                alpha=alpha,
            )
            # Compute absolute means for this cell to calculate deltas vs anchor baseline
            cell_rmse = float(np.mean([fold["candidate_rmse"] for fold in res["folds"]]))
            cell_mae = float(np.mean([fold["candidate_mae"] for fold in res["folds"]]))
            res["summary"]["rmse_delta_vs_baseline_a1"] = round(cell_rmse - anchor_rmse, 4)
            res["summary"]["mae_delta_vs_baseline_a1"] = round(cell_mae - anchor_mae, 4)
            results_by_alpha[alpha_str][name] = res

    return {
        "experiment_name": "te_regularization_bakeoff",
        "alpha_grid": list(ALPHA_GRID),
        "anchor_baseline_alpha": 1.0,
        "results_by_alpha": results_by_alpha,
        "governance": {
            "diagnostic_only": True,
            "model_features_changed": False,
            "te_promotion_changed": False,
            "market_data_used": False,
            "pff_grades_used": False,
            "player_level_rows_emitted": False,
        },
    }
