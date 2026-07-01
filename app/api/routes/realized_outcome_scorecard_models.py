"""Response models for the read-only Realized-Outcome scorecard API (scaffolding).

These mirror the exact dict shape emitted by
``src.dynasty_genius.outcome_loop.realized_outcome_scorer.score()`` (the producer
writes ``{**score(), "status": "ok"}`` to the gitignored scorecard artifact) plus a
small route envelope (``status`` / ``status_reason``, and a root ``maturity_pct``
convenience for the empty-state UI). Every level is ``extra="forbid"`` so a
verdict-shaped field (a ``recommendation`` on a cohort, a ``verdict`` on a tracking
row) fails closed rather than reaching the client.

Descriptive-only diagnostic surface: ``decision_supported`` is locked ``False`` at
every level; this is a fidelity/accuracy audit of a FROZEN model's predictions vs
realized NFL outcomes, never a player verdict.

SCAFFOLDING NOTE (real-shape verification deferred to ~Sept 2026): no scorecard
artifact exists yet (off-season no-op), so these models mirror ``score()``'s source
shape, not a produced artifact. The one known divergence: ``score()`` does NOT emit
``maturity_pct`` at the root (only per tracking row), so the route derives the root
value from the tracking rows when the artifact omits it (see the route module). The
BCa ``bca_ci`` shape is modeled as ``[low, high]`` pending the first real artifact.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Strict(BaseModel):
    """Forbid unknown keys at every level so verdict-shaped fields fail closed."""

    model_config = ConfigDict(extra="forbid")


class RankStat(_Strict):
    """A rank-correlation statistic with its BCa confidence interval (both nullable
    until a cohort clears the statistical power floor)."""

    value: Optional[float] = None
    bca_ci: Optional[list[float]] = None


class NdcgStat(_Strict):
    value: Optional[float] = None


class PrecisionAtK(_Strict):
    value: Optional[float] = None
    k: Optional[int] = None
    truth_def: Optional[str] = None
    hits: Optional[int] = None


class CohortMetric(_Strict):
    """Within-position rank-accuracy metrics for one position cohort. ``status`` is
    ``power_floor_not_met`` (correlations suppressed) or ``ok``."""

    spearman: RankStat
    kendall: RankStat
    ndcg: NdcgStat
    precision_at_k: PrecisionAtK
    status: str
    eligible_count: Optional[int] = None
    decision_supported: Literal[False]


class MifField(_Strict):
    """Model Input Fidelity for one utilization field — a diagnostic audit of a
    model INPUT (does realized usage match the model's assumption), NOT a player
    verdict. ``delta`` is only populated when ``status == "ok"``."""

    status: str
    delta: Optional[float] = None


class TrackingRow(_Strict):
    """One player's predicted vs realized PPG plus its input-fidelity audit."""

    gsis_id: str
    position: Optional[str] = None
    predicted_ppg: Optional[float] = None
    realized_ppg_to_date: Optional[float] = None
    realized_vs_expected_delta: Optional[float] = None
    realized_outcome_status: str
    maturity_pct: Optional[float] = None
    settlement_status: str
    model_input_fidelity: dict[str, MifField] = Field(default_factory=dict)
    decision_supported: Literal[False]


class RealizedOutcomeScorecardResponse(_Strict):
    """Read-only serve of the latest realized-outcome scorecard.

    ``status`` is ``inactive`` (no artifact yet — the healthy off-season state) or
    ``ok`` (a produced scorecard). ``settlement_status`` is ``unsettled`` until the
    2-year horizon. Leads with within-position rank accuracy + Model Input Fidelity;
    market data is excluded from scoring.
    """

    status: str
    status_reason: Optional[str] = None
    as_of_week: Optional[int] = None
    settlement_status: str
    maturity_pct: Optional[float] = None
    cohort_metrics: dict[str, CohortMetric] = Field(default_factory=dict)
    tracking_rows: list[TrackingRow] = Field(default_factory=list)
    excluded_counts: dict[str, int] = Field(default_factory=dict)
    decision_supported: Literal[False]

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, _v: object) -> bool:
        return False


class RealizedOutcomeScorecardErrorResponse(BaseModel):
    """Structured 503 body: the scorecard artifact is present but could not be
    served (malformed, wrong-root, wrong-schema, non-finite, or verdict-shaped).

    Absent artifact is NOT an error — it is the healthy off-season ``inactive`` 200.
    """

    error: str
    message: str
    decision_supported: Literal[False] = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, _v: object) -> bool:
        return False
