"""Task 13.2.1 tests: draft-class LOOCV harness."""
from __future__ import annotations

import json

import pytest

from src.dynasty_genius.eval.draft_class_loocv import (
    DraftClassEvaluationRow,
    DraftClassLOOCVError,
    build_loocv_folds,
    evaluate_candidate_loocv,
)


def _rows() -> list[DraftClassEvaluationRow]:
    rows: list[DraftClassEvaluationRow] = []
    for year in (2021, 2022, 2023):
        for idx in range(5):
            rows.append(
                DraftClassEvaluationRow(
                    candidate_name="position_bucketed",
                    player_id=f"wr_{year}_{idx}",
                    position="WR",
                    draft_year=year,
                    predicted_score=float(5 - idx),
                    realized_value=float(5 - idx),
                )
            )
    return rows


def test_build_loocv_folds_holds_out_one_draft_class_at_a_time():
    folds = build_loocv_folds(_rows(), candidate_name="position_bucketed", position="WR")

    assert [fold.test_year for fold in folds] == [2021, 2022, 2023]
    assert folds[0].train_years == (2022, 2023)
    assert {row.draft_year for row in folds[0].test_rows} == {2021}
    assert {row.draft_year for row in folds[0].train_rows} == {2022, 2023}


def test_build_loocv_folds_filters_candidate_and_position():
    rows = _rows() + [
        DraftClassEvaluationRow(
            candidate_name="log_decay",
            player_id="rb_2021_0",
            position="RB",
            draft_year=2021,
            predicted_score=1.0,
            realized_value=1.0,
        )
    ]

    folds = build_loocv_folds(rows, candidate_name="position_bucketed", position="WR")

    assert len(folds) == 3
    assert all(row.candidate_name == "position_bucketed" for fold in folds for row in fold.test_rows)
    assert all(row.position == "WR" for fold in folds for row in fold.test_rows)


def test_build_loocv_folds_requires_at_least_two_draft_classes():
    rows = [row for row in _rows() if row.draft_year == 2021]

    with pytest.raises(DraftClassLOOCVError, match="at least two draft classes"):
        build_loocv_folds(rows, candidate_name="position_bucketed", position="WR")


def test_evaluate_candidate_loocv_computes_within_class_rank_metrics():
    result = evaluate_candidate_loocv(_rows(), candidate_name="position_bucketed", position="WR")

    assert result.candidate_name == "position_bucketed"
    assert result.position == "WR"
    assert len(result.folds) == 3
    assert all(fold.n_test == 5 for fold in result.folds)
    assert all(fold.within_class_kendall_tau == pytest.approx(1.0) for fold in result.folds)
    assert all(fold.within_class_spearman_rho == pytest.approx(1.0) for fold in result.folds)
    assert result.mean_kendall_tau == pytest.approx(1.0)
    assert result.mean_spearman_rho == pytest.approx(1.0)


def test_loocv_result_serializes_to_json():
    result = evaluate_candidate_loocv(_rows(), candidate_name="position_bucketed", position="WR")

    restored = json.loads(json.dumps(result.as_dict()))

    assert restored["candidate_name"] == "position_bucketed"
    assert restored["fold_strategy"] == "leave_one_draft_class_out"
    assert restored["folds"][0]["test_year"] == 2021
    assert restored["folds"][0]["train_years"] == [2022, 2023]


def test_loocv_harness_rejects_market_derived_source_fields():
    rows = _rows()
    rows[0] = DraftClassEvaluationRow(
        candidate_name="position_bucketed",
        player_id="wr_2021_0",
        position="WR",
        draft_year=2021,
        predicted_score=5.0,
        realized_value=5.0,
        source_fields=("pick", "ktc_value"),
    )

    with pytest.raises(DraftClassLOOCVError, match="market-derived"):
        evaluate_candidate_loocv(rows, candidate_name="position_bucketed", position="WR")


def test_fold_with_too_few_players_reports_null_rank_metrics():
    rows = [
        DraftClassEvaluationRow("position_bucketed", "wr_2021_1", "WR", 2021, 1.0, 1.0),
        DraftClassEvaluationRow("position_bucketed", "wr_2021_2", "WR", 2021, 2.0, 2.0),
        DraftClassEvaluationRow("position_bucketed", "wr_2022_1", "WR", 2022, 1.0, 1.0),
        DraftClassEvaluationRow("position_bucketed", "wr_2022_2", "WR", 2022, 2.0, 2.0),
    ]

    result = evaluate_candidate_loocv(rows, candidate_name="position_bucketed", position="WR")

    assert len(result.folds) == 2
    assert all(fold.n_test == 2 for fold in result.folds)
    assert all(fold.within_class_kendall_tau is None for fold in result.folds)
    assert result.mean_kendall_tau is None
