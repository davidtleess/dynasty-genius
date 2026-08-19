"""Response models for the Model Scoreboard — the model's record against real outcomes.

The scoreboard answers two questions in the order they matter to a manager, not in the
order the experiment produced them:

1. **Does the model beat the market?** If it does there is an edge; if it does not, the
   market is free. QB-1 CANNOT answer this yet, and the surface says so with the reason
   and the condition for answering it — never buried.
2. **Does it beat carrying last year's points forward?** The naive baseline. QB-1 answers
   this, with a caveat that must travel with the number.

Two units disciplines are load-bearing here:

* **The contrast metric is per-fold Spearman, paired delta** (registration §"Primary
  metric"), with a **materiality floor of 0.05 Spearman units**. `points_per_qualifying
  _game` is the study's PREDICTION TARGET, not the unit of the contrast. A delta of 0.098
  is a ranking-quality difference, NOT a tenth of a fantasy point. Every field carrying a
  delta names its unit, and the API never emits a bare number a client could label "PPG".
* **δ = (market − model)**, fixed once in the registration. A POSITIVE market delta favours
  the MARKET. Rendering a positive δ as a model win would invert the finding.

Scope discipline: QB-1's cohort is `position_filter: QB_at_matrix_build`. Nothing in it
measured RB, WR or TE. Every result carries its position, and the unstudied positions are
reported as unstudied rather than omitted — an unqualified headline would read as "my
model" when it is "my QB model".
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# The unit string is a constant, not free text: the surface must be unable to render a
# delta without it, and no code path may substitute "points".
SPEARMAN_UNITS = "spearman_rank_correlation"


class Effect(_Strict):
    """One measured difference, with its unit and its uncertainty attached.

    `value`, `ci_low` and `ci_high` are meaningless without `unit`; they are modelled
    together so a client cannot render the point estimate alone.
    """

    value: float
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    unit: Literal["spearman_rank_correlation"] = SPEARMAN_UNITS
    adjusted_p: Optional[float] = None
    evaluable_folds: Optional[int] = None
    total_folds: Optional[int] = None


class MarketQuestion(_Strict):
    """Question 1 — the one that decides whether this product has an edge at all."""

    position: str
    # `unanswered` is a first-class answer, not an error. It carries WHY and WHAT WOULD
    # ANSWER IT so the surface never reads as a silent gap.
    state: Literal["unanswered", "answered"]
    headline: str
    why: str
    what_would_answer_it: str
    evaluable_folds: int
    total_folds: int
    excluded_fold_reasons: list[str] = Field(default_factory=list)
    # Present but explicitly non-conclusive while `state == "unanswered"`.
    observed_effects: list[Effect] = Field(default_factory=list)
    effect_direction_note: str


class BaselineQuestion(_Strict):
    """Question 2 — does the model beat carrying last year's points forward?"""

    position: str
    state: Literal["answered", "unanswered"]
    headline: str
    effect: Effect
    materiality_floor: float
    # True when the confidence interval reaches below the study's own materiality floor:
    # the direction is established while the magnitude may not matter. Both are true and
    # the surface shows both — a scoreboard that shows only the win is a verdict wearing
    # statistics.
    below_materiality_floor: bool
    materiality_note: str
    counterweight_headline: str
    counterweight_effect: Effect


class PositionScope(_Strict):
    """Which positions have a study at all. Unstudied positions are stated, not omitted."""

    studied: list[str] = Field(default_factory=list)
    unstudied: list[str] = Field(default_factory=list)
    note: str


class LiveAccrual(_Strict):
    """The weekly record accruing against real outcomes."""

    state: Literal["not_started", "accruing"]
    headline: str
    weeks_graded: int
    # Honest denominators, inline on the surface — a rank statistic over 318 of 501
    # predictions is a different claim than one over 501.
    predictions_declared: Optional[int] = None
    predictions_graded: Optional[int] = None
    rank_eligible: Optional[int] = None
    rank_metrics_available: bool
    rank_availability_note: str


class ModelScoreboardResponse(_Strict):
    generated_at: str
    market_question: MarketQuestion
    baseline_question: BaselineQuestion
    position_scope: PositionScope
    live: LiveAccrual
    study_label: str
    decision_supported: Literal[False]


class ModelScoreboardErrorResponse(BaseModel):
    error: str
    message: str
    decision_supported: Literal[False]
