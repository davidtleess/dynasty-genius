"""Per-fold prediction log, market-comparison ledger, and divergence ledger schemas.

All artifacts are write-once. The harness emits prediction rows during run();
scripts consume those rows to produce CSV and JSON artifacts.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


# ── Prediction log ────────────────────────────────────────────────────────────

PREDICTION_LOG_COLUMNS = [
    "player_id",
    "position",
    "fold_index",
    "feature_season",
    "predicted_ppg",
    "realized_ppg",
    "model_rank",
    "residual",
    "age_at_feature_season",
    "draft_round",
]


def write_prediction_log_csv(rows: list[dict], path: Path) -> None:
    """Write prediction log rows to a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PREDICTION_LOG_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── Market-comparison ledger ──────────────────────────────────────────────────

class MarketComparisonEntry(BaseModel):
    player_id: str
    sleeper_id: Optional[str] = None
    position: str
    fold_index: int
    feature_season: int
    snapshot_date: str
    predicted_ppg: float
    model_rank: int
    fc_value: Optional[int] = None
    fc_rank: Optional[int] = None
    realized_ppg: Optional[float] = None
    realized_rank: Optional[int] = None
    rank_delta: Optional[int] = None   # fc_rank - model_rank; positive = model ranked higher


def write_market_comparison_json(
    entries: list[MarketComparisonEntry],
    path: Path,
) -> None:
    """Write market-comparison entries to a JSON array."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [json.loads(entry.json()) for entry in entries]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# ── Divergence ledger ─────────────────────────────────────────────────────────

class DivergenceLedgerEntry(BaseModel):
    player_id: str
    sleeper_id: Optional[str] = None
    position: str
    feature_season: int
    engine_b_pred_ppg: float
    engine_b_rank: int
    fc_value: Optional[int] = None
    fc_rank: Optional[int] = None
    snapshot_date: Optional[str] = None
    realized_avg_ppg_t1_t2: Optional[float] = None
    realized_rank: Optional[int] = None
    rank_delta: Optional[int] = None          # fc_rank - engine_b_rank; positive = model ranked higher
    flagged_direction: Optional[str] = None   # "model_higher" | "model_lower" | None
