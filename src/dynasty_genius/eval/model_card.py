"""ModelCard + CalibrationReport — Mitchell et al. (2018) 9-section schema.

Artifacts are written once and never mutated. The Trust Surface reads them
via GET /trust-surface/{position}/model-card.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, List, Literal, Optional

from pydantic import BaseModel


class ModelCardMetrics(BaseModel):
    rmse_mean: float
    rmse_per_fold: List[float]
    kendall_tau_mean: float
    kendall_tau_per_fold: List[float]
    spearman_rho_mean: float
    spearman_rho_per_fold: List[float]
    ece: Optional[float] = None
    ndcg_at_24_model_mean: Optional[float] = None
    ndcg_at_24_market_mean: Optional[float] = None
    g1_pass: bool
    g2_pass: bool
    g3_pass: Any                    # bool | "deferred"
    g4_pass: Any                    # bool | "deferred" | "insufficient_data"
    overall_grade: str


class ModelCardSubgroup(BaseModel):
    label: str
    n: int
    rmse: float
    kendall_tau: float
    note: Optional[str] = None


class ModelCard(BaseModel):
    """Mitchell et al. (2018) model card schema — 9 sections."""
    schema_version: str = "1.0.0"
    generated_at: datetime
    position: Literal["QB", "RB", "WR", "TE"]
    backtest_run_id: str
    git_sha: Optional[str] = None

    # Section 1: Model Details
    model_version: str
    model_artifact_hash: str
    ridge_alpha: float
    training_window: str
    feature_list: List[str]
    retrain_mode: str

    # Section 2: Intended Use
    intended_use: str
    out_of_scope_uses: List[str]

    # Section 3: Factors
    relevant_factors: List[str]
    evaluation_factors: List[str]

    # Section 4: Metrics
    metrics: ModelCardMetrics

    # Section 5: Evaluation Data
    evaluation_data: str

    # Section 6: Training Data
    training_data: str

    # Section 7: Quantitative Analyses
    subgroup_results: List[ModelCardSubgroup]

    # Section 8: Ethical Considerations
    ethical_considerations: str

    # Section 9: Caveats and Recommendations
    caveats: List[str]
    known_failure_modes: List[str]
    is_experimental: bool

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ModelCard":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


class CalibrationDecile(BaseModel):
    decile: int                     # 1–10 (1 = lowest predicted PPG)
    predicted_mean: float
    observed_mean: float
    n: int
    residual_mean: float            # observed - predicted


class CalibrationReport(BaseModel):
    """Per-position calibration summary across all 4 folds (pooled)."""
    position: str
    backtest_run_id: str
    ece: float
    deciles: List[CalibrationDecile]    # length 10
    note: Optional[str] = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
