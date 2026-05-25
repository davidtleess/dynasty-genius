"""Manual Export adapter.

Handles ingestion of manual CSV exports from PFF, RotoViz, and Campus2Canton.
Enforces leakage prevention by dropping prohibited columns during ingestion.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.dynasty_genius.models.engine_a_contract import PROHIBITED_COLUMNS

ROOT = Path(__file__).resolve().parents[3]

def load_manual_export(source_name: str, csv_path: Path | None = None) -> tuple[pd.DataFrame, list[str]]:
    """
    Load a manual export CSV and filter prohibited columns.
    
    Returns:
        (DataFrame, list of dropped column names)
    """
    if csv_path is None:
        csv_path = ROOT / "resources" / "fixtures" / f"{source_name}_mock.csv"
        
    if not csv_path.exists():
        return pd.DataFrame(), []

    df = pd.read_csv(csv_path)
    
    dropped = [col for col in df.columns if col in PROHIBITED_COLUMNS]
    
    clean_df = df.drop(columns=dropped).copy()
    
    return clean_df, dropped
