"""BacktestResult — versioned artifact schema for the Engine B backtest harness.

Every backtest run writes one BacktestResult per position to:
    app/data/backtest/runs/{run_id}/backtest_result_{position}.json

The Trust Surface route reads this JSON; it never recomputes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TopKResult(BaseModel):
    k: int
    model_hit_rate: float
    market_hit_rate: float
    diff_wilson_ci95: Tuple[float, float]


class FoldResult(BaseModel):
    fold_index: int                                       # 1–4
    train_years: List[int]                               # e.g. [2018, 2019]
    test_year: int                                        # feature_season of test rows
    outcome_seasons: List[int]                           # e.g. [2021, 2022]
    n_train: int
    n_test: int
    n_excluded_injury: int = 0                           # v1: always 0 (no games data yet)

    # Rank correlation — primary = Kendall τ-b, secondary = Spearman ρ
    kendall_tau: float
    kendall_tau_bca_ci95: Tuple[float, float]            # BCa bootstrap
    spearman_rho: float
    spearman_rho_bca_ci95: Tuple[float, float]
    rank_ic: float                                        # alias for spearman_rho; IC convention

    # Error metrics
    rmse: float
    mae: float

    # Market comparison — None when market data unavailable for this fold
    ndcg_at_12_model: Optional[float] = None
    ndcg_at_12_market: Optional[float] = None
    ndcg_at_24_model: Optional[float] = None
    ndcg_at_24_market: Optional[float] = None
    precision_at_k: Optional[Dict[int, TopKResult]] = None  # {12: ..., 24: ..., 36: ...}

    calibration_by_decile: Optional[List[float]] = None  # mean residual per predicted-rank decile
    regime_notes: Optional[str] = None


class StabilityResult(BaseModel):
    rmse_per_fold: List[float]                           # length 4
    rmse_mean: float
    rmse_cv: float                                        # coefficient of variation
    rmse_max_deviation_pct: float
    dm_hln_statistic: Optional[float] = None
    dm_hln_pvalue: Optional[float] = None
    dm_method: str = "harvey_leybourne_newbold_1997"
    dm_passes: Optional[bool] = None                     # p <= 0.10


class DivergenceResult(BaseModel):
    """Gate 4. Populated only when sufficient FC snapshots and flagged player data exist."""
    n_flagged: int
    n_excluded_injury: int
    n_matched_controls_per_flag: int = 3                 # K=3
    forward_horizon_days: int                            # 180 or 365
    position_beta: float                                 # mean position-group % value change
    mean_alpha_flagged: float                            # Beta-adjusted
    mean_alpha_control: float
    diff_bca_ci95: Tuple[float, float]                   # BCa bootstrap
    mann_whitney_u: float
    mann_whitney_p: float
    mann_whitney_method: str                             # "exact" if n_flagged < 20
    hit_rate: float
    hit_rate_wilson_ci95: Tuple[float, float]


class GateResult(BaseModel):
    g1_rank_correlation_pass: bool
    g2_rmse_stability_pass: bool
    g3_market_superiority_pass: bool
    g4_divergence_validity_pass: Literal[True, False, "deferred", "insufficient_data"]
    overall_grade: Literal[
        "PRE_MODEL", "EXPERIMENTAL", "ACTIVE_B",
        "ACTIVE_B_VALIDATED", "DECISION_GRADE",
    ]
    gate_version: str = "1.0"
    promotion_justification: str


class BacktestResult(BaseModel):
    schema_version: str = "1.0.0"
    run_id: UUID = Field(default_factory=uuid4)
    run_date: datetime
    git_sha: Optional[str] = None
    model_version: str                                    # "engine_b_v2"
    model_artifact_hash: str                             # SHA-256 of the .pkl used
    position: Literal["QB", "RB", "WR", "TE"]
    ridge_alpha: float
    retrain_mode: Literal[
        "refit_per_fold_fixed_alpha",
        "frozen_retrospective",
    ]

    folds: List[FoldResult]                              # length 4
    rmse_stability: StabilityResult
    divergence_validity: Optional[DivergenceResult] = None

    market_source: Literal["fc_native", "dp_archive", "ktc_community_csv", "unavailable"]
    market_snapshot_dates: Optional[Dict[int, str]] = None  # {test_year: "YYYY-MM-DD"}

    promotion_gate: GateResult

    def save(self, directory: Path) -> Path:
        """Write artifact to directory/backtest_result_{position}.json. Returns path."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"backtest_result_{self.position}.json"
        path.write_text(
            self.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    @classmethod
    def load(cls, path: Path) -> BacktestResult:
        """Load artifact from JSON file."""
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def artifact_hash(pkl_path: Path) -> str:
        """Compute SHA-256 hex digest of a .pkl file."""
        h = hashlib.sha256()
        with open(pkl_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
