from src.dynasty_genius.eval.backtest_artifact import GateResult, StatusExplanation
from src.dynasty_genius.eval.composite_gate import (
    CI_WIDTH_MAX,
    R2_FLOOR,
    SPEARMAN_THRESHOLD,
    ci_width,
    fold_ci_adequate,
    fold_rank_pass,
    identify_cold_start_fold,
)
from tests.helpers.backtest_gate_builders import build_mock_fold


def _base_gate_kwargs():
    return dict(
        g1_rank_correlation_pass=True,
        g2_rmse_stability_pass=True,
        g3_market_superiority_pass=False,
        g4_divergence_validity_pass="deferred",
        overall_grade="ACTIVE_B",
        promotion_justification="x",
    )


def test_gateresult_defaults_are_fail_closed_and_additive():
    g = GateResult(**_base_gate_kwargs())
    # New fields default fail-closed / non-breaking
    assert g.model_status == "EXPERIMENTAL"
    assert g.status_version == "0.5.0"
    assert g.status_explanation is None
    assert g.validity_spearman_pass is False
    assert g.validity_r2_pass is False
    assert g.validity_ci_adequacy_pass is False
    assert g.validity_rmse_stability_pass is False
    assert g.validity_null_coverage_pass is False
    assert g.validity_leakage_pass is False
    assert g.validity_cold_start_fold_index is None
    assert g.validity_cold_start_tolerated is False
    assert g.validity_most_recent_fold_index is None
    assert g.validity_most_recent_fold_pass is None
    assert g.null_coverage_min is None
    # Existing fields untouched
    assert g.overall_grade == "ACTIVE_B"
    assert g.gate_version == "1.0"


def test_status_explanation_round_trips():
    se = StatusExplanation(
        failed_rank_folds=[1],
        failed_ci_folds=[1],
        cold_start_fold_index=1,
        cold_start_tolerated=True,
        most_recent_fold_index=4,
        most_recent_fold_pass=True,
        null_coverage_min=0.97,
        leakage_clean=True,
        reason="cold-start fold excused; most-recent passes",
    )
    g = GateResult(
        **_base_gate_kwargs(),
        model_status="VALIDATED",
        status_explanation=se,
    )
    dumped = g.model_dump_json()
    reloaded = GateResult.model_validate_json(dumped)
    assert reloaded.model_status == "VALIDATED"
    assert reloaded.status_explanation.cold_start_tolerated is True
    assert reloaded.status_explanation.failed_rank_folds == [1]


def test_ci_width():
    assert ci_width((0.40, 0.70)) == 0.30
    assert CI_WIDTH_MAX == 0.30


def test_fold_predicates():
    good = build_mock_fold(
        idx=2,
        test_year=2021,
        train_years=[2018, 2019, 2020],
        spear=0.79,
        r2=0.46,
        ci=(0.69, 0.85),
    )
    assert SPEARMAN_THRESHOLD == 0.55
    assert R2_FLOOR == 0.0
    assert fold_rank_pass(good) is True
    assert fold_ci_adequate(good) is True

    weak_rank = build_mock_fold(
        idx=1,
        test_year=2020,
        train_years=[2018, 2019],
        spear=0.44,
        r2=0.24,
        ci=(0.24, 0.59),
    )
    assert fold_rank_pass(weak_rank) is False
    assert fold_ci_adequate(weak_rank) is False  # width 0.35 > 0.30


def test_cold_start_unique_min_year_and_thinnest_train():
    folds = [
        build_mock_fold(
            idx=1,
            test_year=2020,
            train_years=[2018, 2019],
            spear=0.44,
            r2=0.24,
            ci=(0.24, 0.59),
        ),
        build_mock_fold(
            idx=2,
            test_year=2021,
            train_years=[2018, 2019, 2020],
            spear=0.79,
            r2=0.46,
            ci=(0.69, 0.85),
        ),
    ]
    assert identify_cold_start_fold(folds) == 1


def test_cold_start_fail_loud_when_not_unique():
    # two folds share the min test_year -> no unique cold-start -> None (fail-loud)
    folds = [
        build_mock_fold(
            idx=1,
            test_year=2020,
            train_years=[2018, 2019],
            spear=0.44,
            r2=0.24,
            ci=(0.24, 0.59),
        ),
        build_mock_fold(
            idx=2,
            test_year=2020,
            train_years=[2017, 2018, 2019],
            spear=0.79,
            r2=0.46,
            ci=(0.69, 0.85),
        ),
    ]
    assert identify_cold_start_fold(folds) is None


def test_cold_start_fail_loud_when_min_year_not_thinnest_train():
    # min test_year fold is NOT the thinnest-train fold -> fail-loud None
    folds = [
        build_mock_fold(
            idx=1,
            test_year=2020,
            train_years=[2016, 2017, 2018, 2019],
            spear=0.44,
            r2=0.24,
            ci=(0.24, 0.59),
        ),
        build_mock_fold(
            idx=2,
            test_year=2021,
            train_years=[2018, 2019],
            spear=0.79,
            r2=0.46,
            ci=(0.69, 0.85),
        ),
    ]
    assert identify_cold_start_fold(folds) is None
