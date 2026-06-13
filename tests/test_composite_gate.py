from src.dynasty_genius.eval.backtest_artifact import GateResult, StatusExplanation


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
