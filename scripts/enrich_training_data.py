import re
import json
from pathlib import Path
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.models.engine_a_contract import PROHIBITED_COLUMNS, LEAKAGE_REGEX

def check_leakage(df: pd.DataFrame):
    prohibited_regex = re.compile(LEAKAGE_REGEX, re.IGNORECASE)
    
    offending = [
        c for c in df.columns 
        if c.lower() in [p.lower() for p in PROHIBITED_COLUMNS] 
        or prohibited_regex.match(c.lower())
    ]
    
    if offending:
        report = {
            "status": "FAILURE",
            "reason": "LEAKAGE DETECTED",
            "offending_columns": offending,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        report_path = ROOT / "leakage_violation_report.json"
        report_path.write_text(json.dumps(report, indent=2))
        raise ValueError(f"LEAKAGE DETECTED: {offending}. See {report_path.name} for details.")

def main():
    training_csv = ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
    output_csv = ROOT / "app" / "data" / "training" / "prospects_with_outcomes_v2.csv"
    
    print(f"Loading baseline: {training_csv.name}")
    baseline_df = pd.read_csv(training_csv)
    baseline_rows = len(baseline_df)
    
    # Verify baseline is clean
    check_leakage(baseline_df)
    
    # Placeholder for enrichment tasks
    enriched_df = baseline_df.copy()
    
    # Final contract checks
    print(f"Verifying final row count parity: {baseline_rows}")
    if len(enriched_df) != baseline_rows:
        raise ValueError(f"CRITICAL: Row count changed! Baseline: {baseline_rows}, Result: {len(enriched_df)}")
    
    # Fail-closed leakage guard on final result
    check_leakage(enriched_df)
    
    # Enriched CSV is NOT written until all tasks are complete
    # For Task 1, we just verify the skeleton works on baseline
    print("Pipeline skeleton verified on baseline data.")

if __name__ == "__main__":
    main()
