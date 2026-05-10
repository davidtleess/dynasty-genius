import pandas as pd
import pytest
import json
import os
from pathlib import Path
from scripts.enrich_training_data import check_leakage

ROOT = Path(__file__).resolve().parents[1]

def test_check_leakage_clean_df():
    df = pd.DataFrame({"gsis_id": ["1"], "pfr_player_name": ["Player A"], "dominator_rating": [0.3]})
    # Should not raise any error
    check_leakage(df)

def test_check_leakage_prohibited_columns():
    df = pd.DataFrame({"gsis_id": ["1"], "ktc_value": [1000], "pfr_player_name": ["Player A"]})
    report_path = ROOT / "leakage_violation_report.json"
    
    if report_path.exists():
        os.remove(report_path)
        
    with pytest.raises(ValueError, match="LEAKAGE DETECTED"):
        check_leakage(df)
    
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "ktc_value" in report["offending_columns"]

def test_check_leakage_regex_columns():
    df = pd.DataFrame({"gsis_id": ["1"], "adp_sleeper": [10.5], "pfr_player_name": ["Player A"]})
    report_path = ROOT / "leakage_violation_report.json"
    
    if report_path.exists():
        os.remove(report_path)

    with pytest.raises(ValueError, match="LEAKAGE DETECTED"):
        check_leakage(df)
        
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "adp_sleeper" in report["offending_columns"]
