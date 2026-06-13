from src.dynasty_genius.eval.backtest_artifact import GateResult, StatusExplanation
from src.dynasty_genius.eval.composite_gate import (
    CI_WIDTH_MAX,
    NULL_COVERAGE_MIN,
    R2_FLOOR,
    SPEARMAN_THRESHOLD,
    ci_width,
    compute_model_status,
    effective_ci_adequacy_gate_pass,
    effective_rank_gate_pass,
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


def _four_folds(spears, r2s, cis):
    train = [
        [2018, 2019],
        [2018, 2019, 2020],
        [2018, 2019, 2020, 2021],
        [2018, 2019, 2020, 2021, 2022],
    ]
    return [
        build_mock_fold(
            idx=i + 1,
            test_year=2020 + i,
            train_years=train[i],
            spear=spears[i],
            r2=r2s[i],
            ci=cis[i],
        )
        for i in range(4)
    ]


def test_status_wr_validated():
    folds = _four_folds(
        [0.763, 0.785, 0.816, 0.794],
        [0.602, 0.680, 0.693, 0.666],
        [(0.69, 0.84), (0.71, 0.85), (0.74, 0.88), (0.73, 0.85)],
    )
    status, expl = compute_model_status(
        folds,
        null_coverage_min_obs=0.97,
        leakage_clean=True,
    )
    assert status == "VALIDATED"
    assert expl.most_recent_fold_pass is True


def test_status_te_validated_cold_start_excused():
    # fold-1 (cold-start) fails both rank (0.436) and CI-width (0.345); later folds strong
    folds = _four_folds(
        [0.436, 0.792, 0.714, 0.706],
        [0.244, 0.457, 0.472, 0.558],
        [(0.24, 0.585), (0.69, 0.85), (0.61, 0.81), (0.57, 0.81)],
    )
    status, expl = compute_model_status(
        folds,
        null_coverage_min_obs=0.97,
        leakage_clean=True,
    )
    assert status == "VALIDATED"
    assert expl.cold_start_tolerated is True
    assert expl.failed_rank_folds == [1] and expl.failed_ci_folds == [1]
    assert effective_rank_gate_pass(expl) is True
    assert effective_ci_adequacy_gate_pass(expl) is True


def test_status_qb_provisional_middle_ci_breach():
    # all rank-pass, but CI-width breaches at fold-1(cold-start) AND fold-3(middle)
    folds = _four_folds(
        [0.678, 0.721, 0.693, 0.755],
        [0.141, 0.298, 0.287, 0.286],
        [(0.42, 0.82), (0.54, 0.83), (0.43, 0.84), (0.61, 0.86)],
    )
    status, expl = compute_model_status(
        folds,
        null_coverage_min_obs=0.97,
        leakage_clean=True,
    )
    assert status == "PROVISIONAL"
    assert 3 in expl.failed_ci_folds


def test_status_experimental_when_leakage_dirty():
    folds = _four_folds(
        [0.80, 0.80, 0.80, 0.80],
        [0.6, 0.6, 0.6, 0.6],
        [(0.7, 0.8)] * 4,
    )
    status, _ = compute_model_status(
        folds,
        null_coverage_min_obs=0.99,
        leakage_clean=False,
    )
    assert status == "EXPERIMENTAL"


def test_status_experimental_when_null_coverage_below_floor():
    assert NULL_COVERAGE_MIN == 0.90
    folds = _four_folds(
        [0.80, 0.80, 0.80, 0.80],
        [0.6, 0.6, 0.6, 0.6],
        [(0.7, 0.8)] * 4,
    )
    status, _ = compute_model_status(
        folds,
        null_coverage_min_obs=0.80,
        leakage_clean=True,
    )
    assert status == "EXPERIMENTAL"


def test_status_provisional_when_most_recent_fold_fails():
    # most-recent (fold-4) fails rank -> never VALIDATED even though 3/4 pass
    folds = _four_folds(
        [0.80, 0.80, 0.80, 0.40],
        [0.6, 0.6, 0.6, 0.6],
        [(0.7, 0.8)] * 4,
    )
    status, expl = compute_model_status(
        folds,
        null_coverage_min_obs=0.97,
        leakage_clean=True,
    )
    assert status == "PROVISIONAL"
    assert expl.most_recent_fold_pass is False


def test_status_provisional_when_middle_fold_fails_not_cold_start():
    # only fold-2 (middle) fails rank; cold-start tolerance does NOT cover it
    folds = _four_folds(
        [0.80, 0.40, 0.80, 0.80],
        [0.6, 0.6, 0.6, 0.6],
        [(0.7, 0.8)] * 4,
    )
    status, _ = compute_model_status(
        folds,
        null_coverage_min_obs=0.97,
        leakage_clean=True,
    )
    assert status == "PROVISIONAL"


def test_status_provisional_when_cold_start_not_unique():
    # fail-loud cold-start (None) -> a failing oldest fold is NOT excused
    folds = _four_folds(
        [0.40, 0.80, 0.80, 0.80],
        [0.6, 0.6, 0.6, 0.6],
        [(0.7, 0.8)] * 4,
    )
    folds[1].test_year = 2020  # duplicate min year -> identify returns None
    status, expl = compute_model_status(
        folds,
        null_coverage_min_obs=0.97,
        leakage_clean=True,
    )
    assert status == "PROVISIONAL"
    assert expl.cold_start_fold_index is None
