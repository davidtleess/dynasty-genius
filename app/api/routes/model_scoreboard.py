"""The Model Scoreboard route — the model's running record against real outcomes.

Reads the QB-1 validation report (real, day one) and the realized-outcome scorecard
(live weeks as they accrue) and answers the two questions a manager actually has, in
that order: does it beat the market, and does it beat last year's points.

Everything here is descriptive. `decision_supported` is False at every level.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.routes.model_scoreboard_models import (
    BaselineQuestion,
    Effect,
    LiveAccrual,
    MarketQuestion,
    ModelScoreboardErrorResponse,
    ModelScoreboardResponse,
    PositionScope,
)

router = APIRouter(tags=["system"])

_REPO_ROOT = Path(__file__).resolve().parents[3]
_QB1_REPORT = (
    _REPO_ROOT / "app" / "data" / "backtest" / "qb_validation" / "qb_validation_report.json"
)
_SCORECARD = _REPO_ROOT / "app" / "data" / "realized_outcome" / "scorecard_latest.json"

# Fixed by the pre-registration; not inferred from the report so a regenerated report
# can never silently move the bar it is judged against.
_MATERIALITY_FLOOR = 0.05
_STUDY_POSITION = "QB"
_UNSTUDIED = ["RB", "WR", "TE"]
# The registered contrasts this surface reads. The other nine exist so a
# pre-registration can stop the researcher steering the result; they are how you debug a
# model, not how a manager decides a waiver claim, and rendering all fourteen would be
# showing the experiment instead of the answer.
_BASELINE_CONTRAST = "c04"  # full model vs naive carry-forward
_COUNTERWEIGHT_CONTRAST = "c01"  # efficiency alone vs naive
_MARKET_LANE = "h5"


def _unavailable_503(message: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=ModelScoreboardErrorResponse(
            error="model_scoreboard_unavailable",
            message=message,
            decision_supported=False,
        ).model_dump(),
    )


def _effect(row: dict[str, Any]) -> Effect:
    ci = row.get("ci95") or []
    low = ci[0] if len(ci) == 2 and isinstance(ci[0], (int, float)) else None
    high = ci[1] if len(ci) == 2 and isinstance(ci[1], (int, float)) else None
    return Effect(
        value=float(row["pooled_delta"]),
        ci_low=low,
        ci_high=high,
        adjusted_p=row.get("adjusted_p"),
        evaluable_folds=row.get("evaluable_folds"),
        total_folds=(row.get("evaluable_folds") or 0) + len(row.get("excluded_folds") or []),
    )


def _load_live() -> LiveAccrual:
    """The live weekly record. No artifact yet is the honest pre-season state."""
    not_started = LiveAccrual(
        state="not_started",
        headline="No weeks graded yet — the first live week is Week 1.",
        weeks_graded=0,
        rank_metrics_available=False,
        rank_availability_note=(
            "Ranking accuracy needs four games per player before it can be computed, so "
            "those columns stay empty until roughly Week 5 even once grading starts."
        ),
    )
    try:
        payload = json.loads(_SCORECARD.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return not_started
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        return not_started

    coverage = payload.get("coverage") or {}
    rank_eligible = coverage.get("rank_eligible_count")
    return LiveAccrual(
        state="accruing",
        headline=f"Graded through Week {payload.get('as_of_week')}.",
        weeks_graded=int(payload.get("as_of_week") or 0),
        predictions_declared=coverage.get("declared_count"),
        predictions_graded=coverage.get("graded_count"),
        rank_eligible=rank_eligible,
        rank_metrics_available=bool(rank_eligible),
        rank_availability_note=(
            "Ranking accuracy counts only players with four or more games."
            if rank_eligible
            else "No player has four games yet, so ranking accuracy is not computed."
        ),
    )


@router.get(
    "/model-scoreboard",
    response_model=ModelScoreboardResponse,
    responses={503: {"model": ModelScoreboardErrorResponse}},
)
def get_model_scoreboard() -> ModelScoreboardResponse:
    try:
        report = json.loads(_QB1_REPORT.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise _unavailable_503("validation report not found") from exc
    except (OSError, ValueError) as exc:
        raise _unavailable_503(f"validation report unreadable: {exc}") from exc

    comparisons = {row.get("id"): row for row in (report.get("comparisons") or [])}
    try:
        baseline_row = comparisons[_BASELINE_CONTRAST]
        counterweight_row = comparisons[_COUNTERWEIGHT_CONTRAST]
    except KeyError as exc:
        raise _unavailable_503("validation report is missing a registered contrast") from exc

    market_rows = [
        row for row in (report.get("comparisons") or []) if row.get("lane") == _MARKET_LANE
    ]
    evaluable = max((row.get("evaluable_folds") or 0) for row in market_rows) if market_rows else 0
    excluded = market_rows[0].get("excluded_folds") if market_rows else []
    reasons = sorted({r for fold in (excluded or []) for r in (fold.get("reasons") or [])})
    total_folds = evaluable + len(excluded or [])

    market = MarketQuestion(
        position=_STUDY_POSITION,
        state="unanswered",
        headline="We cannot say yet whether the QB model beats the market.",
        why=(
            f"Only {evaluable} of {total_folds} test seasons produced a usable "
            f"model-versus-market comparison. The other {len(excluded or [])} were thrown "
            "out before any result was read, because the market data for those seasons was "
            "too thin to compare against."
        ),
        what_would_answer_it=(
            "Market prices captured forward, season by season. The comparison is scored per "
            "test season, so usable seasons — not weeks — are what accrue; the study can be "
            "re-run once enough of them exist. No date is promised here because the rate "
            "depends on capture coverage, not on the calendar."
        ),
        evaluable_folds=evaluable,
        total_folds=total_folds,
        excluded_fold_reasons=reasons,
        observed_effects=[_effect(row) for row in market_rows],
        effect_direction_note=(
            "On the single usable season the market ranked ahead of the model, but one "
            "season cannot settle it — these numbers are shown for completeness and support "
            "no conclusion in either direction."
        ),
    )

    effect = _effect(baseline_row)
    below_floor = effect.ci_low is not None and effect.ci_low < _MATERIALITY_FLOOR
    baseline = BaselineQuestion(
        position=_STUDY_POSITION,
        state="answered",
        headline=(
            "The full QB model ranks quarterbacks better than carrying last year's "
            "points forward."
        ),
        effect=effect,
        materiality_floor=_MATERIALITY_FLOOR,
        below_materiality_floor=below_floor,
        materiality_note=(
            "Both of these are true: the model does rank better, and the effect may be too "
            f"small to matter. The plausible range runs {effect.ci_low:.3f} to "
            f"{effect.ci_high:.3f}, and the study's own floor for a difference worth acting "
            f"on is {_MATERIALITY_FLOOR:.2f}."
            if below_floor and effect.ci_low is not None and effect.ci_high is not None
            else "The measured effect clears the study's materiality floor."
        ),
        counterweight_headline=(
            "Efficiency alone ranked worse than carrying last year's points forward."
        ),
        counterweight_effect=_effect(counterweight_row),
    )

    return ModelScoreboardResponse(
        generated_at=str(report.get("generated_at") or ""),
        market_question=market,
        baseline_question=baseline,
        position_scope=PositionScope(
            studied=[_STUDY_POSITION],
            unstudied=list(_UNSTUDIED),
            note=(
                "This study measured quarterbacks only. Running backs, receivers and tight "
                "ends have no equivalent study yet, so nothing here describes them."
            ),
        ),
        live=_load_live(),
        study_label="QB-1 validation study",
        decision_supported=False,
    )
