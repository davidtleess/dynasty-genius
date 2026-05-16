"""Task 13.2.2 tests: draft-capital bake-off evaluator."""
from __future__ import annotations

import json

import pytest

from src.dynasty_genius.eval.draft_capital_bakeoff import (
    DraftCapitalBakeoffError,
    run_draft_capital_bakeoff,
)
from src.dynasty_genius.eval.draft_class_loocv import (
    DraftClassEvaluationRow,
    DraftClassLOOCVError,
)
from tests.fixtures.draft_capital_bakeoff import (
    _MARKET_CONTAMINATED_SOURCE_FIELDS,
    all_candidates_qb_rows,
    market_contaminated_cohort,
    qb_top15_cliff_rows,
    te_small_cohort_rows,
    wr_pick75_viability_rows,
)


def test_bakeoff_evaluates_all_required_candidates_for_position():
    result = run_draft_capital_bakeoff(all_candidates_qb_rows(), position="QB")

    assert result.position == "QB"
    assert result.fold_strategy == "leave_one_draft_class_out"
    assert {candidate.name for candidate in result.candidates} == {
        "current_engine_a_baseline",
        "log_decay",
        "position_bucketed",
        "position_isotonic_step",
    }
    assert all(candidate.fold_count == 3 for candidate in result.candidates)


def test_bakeoff_marks_controls_as_not_promotion_eligible():
    result = run_draft_capital_bakeoff(all_candidates_qb_rows(), position="QB")
    by_name = {candidate.name: candidate for candidate in result.candidates}

    assert by_name["current_engine_a_baseline"].role == "baseline"
    assert not by_name["current_engine_a_baseline"].promotion_eligible
    assert by_name["log_decay"].role == "control"
    assert not by_name["log_decay"].promotion_eligible
    assert by_name["position_bucketed"].promotion_eligible
    assert by_name["position_isotonic_step"].promotion_eligible
    assert result.promotion_decision == "requires_david_review"


def test_bakeoff_serializes_validation_artifact():
    result = run_draft_capital_bakeoff(all_candidates_qb_rows(), position="QB")

    restored = json.loads(json.dumps(result.as_dict()))

    assert restored["position"] == "QB"
    assert restored["promotion_decision"] == "requires_david_review"
    assert restored["candidates"][0]["name"] == "current_engine_a_baseline"
    assert "market_data" in restored["prohibited_inputs"]


def test_bakeoff_filters_mixed_position_rows():
    rows = wr_pick75_viability_rows("current_engine_a_baseline")
    rows += wr_pick75_viability_rows("log_decay")
    rows += wr_pick75_viability_rows("position_bucketed")
    rows += wr_pick75_viability_rows("position_isotonic_step")
    rows.append(
        DraftClassEvaluationRow(
            candidate_name="position_bucketed",
            player_id="qb_pick1_2020",
            position="QB",
            draft_year=2020,
            predicted_score=99.0,
            realized_value=22.0,
        )
    )

    result = run_draft_capital_bakeoff(rows, position="WR")

    assert result.position == "WR"
    assert all(candidate.position == "WR" for candidate in result.candidates)


@pytest.mark.parametrize("source_fields", _MARKET_CONTAMINATED_SOURCE_FIELDS)
def test_bakeoff_rejects_market_contaminated_candidate_rows(source_fields):
    rows = market_contaminated_cohort(source_fields=source_fields)
    rows += wr_pick75_viability_rows("current_engine_a_baseline")
    rows += wr_pick75_viability_rows("log_decay")
    rows += wr_pick75_viability_rows("position_isotonic_step")

    with pytest.raises(DraftClassLOOCVError, match="market-derived"):
        run_draft_capital_bakeoff(rows, position="WR")


def test_bakeoff_requires_all_manifest_candidates():
    rows = qb_top15_cliff_rows("current_engine_a_baseline")
    rows += qb_top15_cliff_rows("log_decay")
    rows += qb_top15_cliff_rows("position_bucketed")

    with pytest.raises(DraftCapitalBakeoffError, match="position_isotonic_step"):
        run_draft_capital_bakeoff(rows, position="QB")


def test_te_small_cohort_reports_null_metrics_without_crashing():
    rows = te_small_cohort_rows("current_engine_a_baseline")
    rows += te_small_cohort_rows("log_decay")
    rows += te_small_cohort_rows("position_bucketed")
    rows += te_small_cohort_rows("position_isotonic_step")

    result = run_draft_capital_bakeoff(rows, position="TE")

    assert result.position == "TE"
    assert all(candidate.mean_kendall_tau is None for candidate in result.candidates)
    assert result.leading_candidate is None


def test_bakeoff_reports_candidate_order_by_rank_metric():
    rows = all_candidates_qb_rows()
    result = run_draft_capital_bakeoff(rows, position="QB")

    ordered_names = [candidate.name for candidate in result.rank_order]

    assert set(ordered_names) == {
        "current_engine_a_baseline",
        "log_decay",
        "position_bucketed",
        "position_isotonic_step",
    }
