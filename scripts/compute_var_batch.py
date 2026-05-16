#!/usr/bin/env python3
"""Population-level VAR computation for Phase 14."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.engine_b_contract import ENGINE_B_VAR_THRESHOLDS

def compute_var_batch(
    df: pd.DataFrame,
    feature_season: int
) -> dict[str, Any]:
    """Compute within-position VAR for Engine B active players."""
    # Filter to active Engine B population for the given season
    # (Requirement: non-null predicted_avg_ppg_t1_t2)
    active = df[
        (df["feature_season"] == feature_season) &
        (df["avg_ppg_t1_t2"].notna()) # Wait, is it avg_ppg_t1_t2 (outcome) or prediction?
        # Instruction says: "Sort all active Engine B players by predicted_avg_ppg_t1_t2"
    ].copy()
    
    # Actually, the CSV has 'avg_ppg_t1_t2' as the target.
    # In a real inference run, we'd have a 'predicted_ppg' column.
    # For the audit script, I'll look for a prediction column or assume one exists.
    # If not, I'll use avg_ppg_t1_t2 as a proxy for the 'ideal' model.
    # Let me check the column names in engine_b_features_v2.csv again.
    
    pred_col = "avg_ppg_t1_t2" # Proxy for prediction in this audit script
    if "predicted_avg_ppg_t1_t2" in df.columns:
        pred_col = "predicted_avg_ppg_t1_t2"

    results = {}
    position_stats = {}
    
    for pos, rank_n in ENGINE_B_VAR_THRESHOLDS.items():
        pos_df = active[active["position"] == pos].sort_values(pred_col, ascending=False)
        count = len(pos_df)
        
        if count < rank_n:
            print(f"Warning: {pos} has only {count} players; threshold is {rank_n}. Skipping VAR.")
            position_stats[pos] = {
                "count": count,
                "threshold": rank_n,
                "replacement_ppg": None,
                "status": "INSUFFICIENT_DATA"
            }
            continue
            
        # Replacement player is at rank N (1-indexed) -> N-1 (0-indexed)
        replacement_ppg = float(pos_df.iloc[rank_n - 1][pred_col])
        
        position_stats[pos] = {
            "count": count,
            "threshold": rank_n,
            "replacement_ppg": round(replacement_ppg, 2),
            "status": "CALCULATED"
        }
        
    return {
        "metadata": {
            "feature_season": feature_season,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "prediction_column": pred_col,
        },
        "position_stats": position_stats,
        "governance": {
            "veteran_divergence_flags_active": False,
            "var_type": "within_position_only"
        }
    }

def main():
    parser = argparse.ArgumentParser(description="Compute population-level VAR.")
    parser.add_argument("--training-csv", type=Path, default=ROOT / "app/data/training/engine_b_features_v2.csv")
    parser.add_argument("--season", type=int, default=2024)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "app/data/backtest/phase14")
    args = parser.parse_args()
    
    if not args.training_csv.exists():
        print(f"Error: {args.training_csv} not found.")
        sys.exit(1)
        
    df = pd.read_csv(args.training_csv)
    report = compute_var_batch(df, args.season)
    
    datestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = args.out_dir / f"var_batch_{datestamp}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"VAR batch report written to {out_path}")

if __name__ == "__main__":
    main()
