from src.dynasty_genius.eval.backtest_harness import evaluate_promotion_gates
from src.dynasty_genius.eval.backtest_metrics import compute_null_coverage
from tests.helpers.backtest_gate_builders import (
    build_mock_divergence,
    build_mock_fold,
    build_mock_stability,
)


def _step05_four_folds(spears, r2s, cis, null_coverage=0.97):
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
            null_coverage=null_coverage,
        )
        for i in range(4)
    ]


def test_model_status_is_emitted_and_g3_does_not_gate_it():
    # TE-like: cold-start weak, later strong; G3 fails/defers but validity status clears.
    folds = _step05_four_folds(
        [0.436, 0.792, 0.714, 0.706],
        [0.244, 0.457, 0.472, 0.558],
        [(0.24, 0.585), (0.69, 0.85), (0.61, 0.81), (0.57, 0.81)],
    )
    for fold in folds:
        fold.ndcg_at_12_model = 0.80
        fold.ndcg_at_12_market = 0.85
    result = evaluate_promotion_gates(
        position="TE",
        folds=folds,
        stability=build_mock_stability(),
        divergence=None,
        leakage_clean=True,
    )

    # G3 still computed + disclosed, but it does NOT gate model_status.
    assert result.g3_market_superiority_pass in (False, "deferred")
    assert result.model_status == "VALIDATED"
    assert result.status_explanation is not None
    assert result.status_explanation.cold_start_tolerated is True
    # overall_grade (deprecated) is still populated, unchanged contract.
    assert result.overall_grade in (
        "PRE_MODEL",
        "EXPERIMENTAL",
        "ACTIVE_B",
        "ACTIVE_B_VALIDATED",
        "DECISION_GRADE",
    )


def test_evaluate_promotion_gates_uses_fold_null_coverage_min_fail_closed():
    folds = _step05_four_folds(
        [0.80, 0.80, 0.80, 0.80],
        [0.60, 0.60, 0.60, 0.60],
        [(0.70, 0.80)] * 4,
        null_coverage=0.95,
    )
    folds[2].null_coverage = 0.89
    result = evaluate_promotion_gates(
        position="WR",
        folds=folds,
        stability=build_mock_stability(),
        leakage_clean=True,
    )

    assert result.null_coverage_min == 0.89
    assert result.validity_null_coverage_pass is False
    assert result.model_status == "EXPERIMENTAL"


def test_harness_fold_null_coverage_uses_test_mask_and_scored_frame_shape():
    # Cross-component shape test: eligible comes from the fold test_mask before feature handling;
    # scored comes from the X_test rows actually returned by _build_fold_data.
    # Current harness imputes feature nulls instead of dropping rows, so real v1 folds are expected
    # to report 1.0. This helper-level mismatch proves the wiring uses the two component shapes and
    # will fail if the harness later drops rows but forgets to propagate the scored shape.
    import pandas as pd

    from src.dynasty_genius.eval import backtest_harness as harness

    test_mask = pd.Series([True, True, True, False])
    scored_frame = pd.DataFrame({"feature": [1.0, 2.0]})

    assert harness._compute_fold_null_coverage(test_mask, scored_frame) == (
        compute_null_coverage(n_eligible=3, n_scored=2)
    )


def test_g1_pass_logic():
    # Pass WR: mean tau >= 0.40 and 3/4 CIs >= 0.20
    folds = [
        build_mock_fold(tau=0.45, tau_ci_low=0.25),
        build_mock_fold(tau=0.42, tau_ci_low=0.22),
        build_mock_fold(tau=0.40, tau_ci_low=0.21),
        build_mock_fold(tau=0.35, tau_ci_low=0.15),
    ]
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g1_rank_correlation_pass is True

    # Fail WR: mean tau < 0.40
    folds[0].kendall_tau = 0.35
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g1_rank_correlation_pass is False

    # Fail WR: only 2/4 CIs >= 0.20
    folds = [
        build_mock_fold(tau=0.50, tau_ci_low=0.25),
        build_mock_fold(tau=0.50, tau_ci_low=0.25),
        build_mock_fold(tau=0.50, tau_ci_low=0.15),
        build_mock_fold(tau=0.50, tau_ci_low=0.15),
    ]
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g1_rank_correlation_pass is False

    # Pass QB: mean tau >= 0.30
    folds = [build_mock_fold(tau=0.31, tau_ci_low=0.21)] * 4
    gate = evaluate_promotion_gates(folds, stability, "QB")
    assert gate.g1_rank_correlation_pass is True


def test_g2_stability_logic():
    folds = [build_mock_fold()] * 4
    
    # Pass: dev <= 25% and dm_p <= 0.10
    stability = build_mock_stability(max_dev=20.0, dm_p=0.08)
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g2_rmse_stability_pass is True

    # Fail: dev > 25%
    stability = build_mock_stability(max_dev=26.0, dm_p=0.05)
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g2_rmse_stability_pass is False

    # Fail: dm_p > 0.10
    stability = build_mock_stability(max_dev=10.0, dm_p=0.11)
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g2_rmse_stability_pass is False


def test_g3_market_superiority_logic():
    stability = build_mock_stability()
    
    # Pass: 3/4 wins
    folds = [
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=0.80, market_ndcg=0.85),
    ]
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g3_market_superiority_pass is True
    assert gate.g4_divergence_validity_pass == "deferred"
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"

    # Fail: 2/4 wins
    folds[2].ndcg_at_24_model = 0.80
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g3_market_superiority_pass is False
    assert gate.overall_grade == "ACTIVE_B"

    # Deferred: all market data None
    folds = [build_mock_fold(market_ndcg=None)] * 4
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g3_market_superiority_pass == "deferred"
    assert gate.g4_divergence_validity_pass == "deferred"
    assert gate.overall_grade == "ACTIVE_B"

    # Deferred: only 2 folds available, even if we win both (need 3 evaluable folds)
    folds = [
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=0.90, market_ndcg=0.85),
        build_mock_fold(model_ndcg=None, market_ndcg=None),
        build_mock_fold(model_ndcg=None, market_ndcg=None),
    ]
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.g3_market_superiority_pass == "deferred"
    assert gate.overall_grade == "ACTIVE_B"


def test_g4_divergence_logic():
    folds = [build_mock_fold()] * 4
    stability = build_mock_stability()
    
    # Pass all G1-G3
    # G4 Pass -> DECISION_GRADE
    div = build_mock_divergence(
        n_flagged=40,
        mw_p=0.05,
        diff_ci_low=0.01,
        hit_rate_ci_low=0.51,
    )
    gate = evaluate_promotion_gates(folds, stability, "WR", divergence=div)
    assert gate.g4_divergence_validity_pass is True
    assert gate.overall_grade == "DECISION_GRADE"

    # G4 Fail: p > 0.10
    div = build_mock_divergence(mw_p=0.11)
    gate = evaluate_promotion_gates(folds, stability, "WR", divergence=div)
    assert gate.g4_divergence_validity_pass is False
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"

    # G4 Insufficient Data: n < 30
    div = build_mock_divergence(n_flagged=25)
    gate = evaluate_promotion_gates(folds, stability, "WR", divergence=div)
    assert gate.g4_divergence_validity_pass == "insufficient_data"
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"


def test_grade_hierarchy():
    # G1 fail -> ACTIVE_B even if others pass
    folds = [build_mock_fold(tau=0.1)] * 4
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.overall_grade == "ACTIVE_B"

    # G2 fail -> ACTIVE_B
    folds = [build_mock_fold()] * 4
    stability = build_mock_stability(max_dev=50.0)
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.overall_grade == "ACTIVE_B"

    # TE position can now clear EXPERIMENTAL when G1/G2 pass.
    folds = [build_mock_fold()] * 4
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "TE")
    assert gate.overall_grade == "ACTIVE_B_VALIDATED"

    # TE remains EXPERIMENTAL when a core gate fails.
    folds = [build_mock_fold(tau=0.1)] * 4
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "TE")
    assert gate.overall_grade == "EXPERIMENTAL"


def test_gate_version_field_is_v1():
    folds = [build_mock_fold()] * 4
    stability = build_mock_stability()
    gate = evaluate_promotion_gates(folds, stability, "WR")
    assert gate.gate_version == "1.0"
