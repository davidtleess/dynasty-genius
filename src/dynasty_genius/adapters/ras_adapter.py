"""RAS adapter.

Provides risk-flag signals derived from Relative Athletic Scores.
Intentionally avoids exposing high RAS as a positive model signal.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = ROOT / "resources" / "fixtures" / "ras_mock.csv"

def fetch_ras_context(player_name: str, csv_path: Path = FIXTURE_PATH) -> dict[str, Any]:
    """Fetch RAS risk flags for a player name."""
    if not csv_path.exists():
        return {
            "low_ras_risk_flag": False,
            "missing_athletic_profile": True,
            "source_ras_score": "ras"
        }

    df = pd.read_csv(csv_path)
    # Search for player
    matches = df[df["player_name"].str.lower() == player_name.lower()]
    
    if matches.empty:
        return {
            "low_ras_risk_flag": False,
            "missing_athletic_profile": True,
            "source_ras_score": "ras"
        }

    score_val = matches.iloc[0]["ras_score"]
    
    # Handle empty/null score in CSV
    if pd.isna(score_val):
        return {
            "low_ras_risk_flag": False,
            "missing_athletic_profile": True,
            "source_ras_score": "ras"
        }

    try:
        score = float(score_val)
        return {
            "low_ras_risk_flag": score < 4.0,
            "missing_athletic_profile": False,
            "source_ras_score": "ras"
        }
    except (ValueError, TypeError):
        return {
            "low_ras_risk_flag": False,
            "missing_athletic_profile": True,
            "source_ras_score": "ras"
        }
