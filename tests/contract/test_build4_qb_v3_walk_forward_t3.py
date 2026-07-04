from __future__ import annotations

import importlib
from typing import Any

import pandas as pd
import pytest

from src.dynasty_genius.features.qb_v3_candidate_matrix import (
    ENGINE_B_FEATURES_QB_V3_CANDIDATE,
)


def _wf_module() -> Any:
    return importlib.import_module("src.dynasty_genius.eval.qb_v3_walk_forward")


def _value(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def _candidate_frame(
    *,
    seasons: tuple[int, ...] = (2018, 2019, 2020, 2021, 2022, 2023),
    rows_per_season: int = 36,
    ineligible_training_row: bool = False,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for season in seasons:
        for idx in range(rows_per_season):
            player_id = f"qb_{season}_{idx:02d}"
            ppg_t = float(idx)
            rows.append(
                {
                    "player_id": player_id,
                    "feature_season": season,
                    "age": 23.0 + (idx % 8) * 0.5,
                    "ppg_t": ppg_t,
                    "games_t": 8 + (idx % 9),
                    "snap_share": 0.35 + (idx % 20) / 40,
                    "aging_curve_value": 0.9 + (idx % 6) / 100,
                    "ppg_t_minus_1": ppg_t - 1,
                    "ppg_t_minus_2": ppg_t - 2,
                    "snap_share_t_minus_1": 0.30 + (idx % 18) / 45,
                    "ppg_t_minus_1_available": idx % 5 != 0,
                    "ppg_t_minus_2_available": idx % 7 != 0,
                    "snap_share_t_minus_1_available": idx % 4 != 0,
                    "epa_per_dropback": -0.2 + idx / 100,
                    "cpoe": -4.0 + idx / 4,
                    "dakota": -0.1 + idx / 150,
                    "is_dual_threat": idx % 3 == 0,
                    "draft_capital_prior": 1.0 if idx < 12 else 0.7 if idx < 24 else 0.15,
                    "dual_threat_x_age": (23.0 + (idx % 8) * 0.5) if idx % 3 == 0 else 0.0,
                }
            )
    if ineligible_training_row:
        row = rows[0].copy()
        row.update({"player_id": "mask_ineligible_training_qb", "feature_season": 2019})
        rows.append(row)
    return pd.DataFrame(rows)


def _eligibility_mask(candidate_frame: pd.DataFrame, *, all_eligible: bool = True) -> pd.DataFrame:
    records = []
    for row in candidate_frame.itertuples(index=False):
        eligible = all_eligible and row.player_id != "mask_ineligible_training_qb"
        records.append(
            {
                "player_id": row.player_id,
                "feature_season": int(row.feature_season),
                "eligible_for_qb_v3_candidate": eligible,
                "abstention_reason": None if eligible else "small_sample_qb",
            }
        )
    return pd.DataFrame(records)


def _labels_for(candidate_frame: pd.DataFrame, *, horizons: tuple[int, ...] = (1, 2, 3)) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in candidate_frame.itertuples(index=False):
        season = int(row.feature_season)
        player_id = str(row.player_id)
        if player_id == "mask_ineligible_training_qb":
            positive = True
        else:
            idx = int(player_id.rsplit("_", 1)[1])
            positive = idx % 2 == 0
        for horizon in horizons:
            target_season = season + horizon
            if target_season <= 2025:
                rows.append(
                    {
                        "player_id": player_id,
                        "feature_season": season,
                        "target_season": target_season,
                        "horizon": horizon,
                        "startable_role_occupancy": positive,
                        "label_basis": "games_and_snap",
                    }
                )
    return pd.DataFrame(rows)


def _report_dict(report: Any) -> dict[str, Any]:
    if isinstance(report, dict):
        return report
    if hasattr(report, "to_dict"):
        return report.to_dict()
    raise AssertionError(f"unexpected report type: {type(report)}")


def _assert_recursive_decision_supported_false(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for child in value.values():
            _assert_recursive_decision_supported_false(child)
    elif isinstance(value, list):
        for child in value:
            _assert_recursive_decision_supported_false(child)


def _assert_no_verdict_fields(value: Any) -> None:
    banned = {"promote", "promote_model", "promotion_recommendation", "recommend", "verdict"}
    if isinstance(value, dict):
        assert not (set(value) & banned)
        for child in value.values():
            _assert_no_verdict_fields(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_verdict_fields(child)


def test_t3_uses_new_logistic_classification_driver_not_ridge_walkforward() -> None:
    module = _wf_module()

    assert module.QB_V3_MODEL_FAMILY == "regularized_logistic_regression"
    assert module.QB_V3_TOP_K == 12
    assert module.QB_V3_STRUCTURAL_FOLD_COUNTS == {1: 4, 2: 4, 3: 3}
    assert not hasattr(module, "WalkForwardDriver")


def test_fold_data_reuses_expanding_window_pattern_and_fit_preprocessors_on_train_only() -> None:
    module = _wf_module()
    candidates = _candidate_frame(seasons=(2018, 2019, 2020), ineligible_training_row=True)
    labels = _labels_for(candidates, horizons=(1,))
    mask = _eligibility_mask(candidates)

    fold = module.build_qb_v3_classification_fold_data(
        candidate_matrix=candidates,
        labels=labels,
        eligibility_mask=mask,
        feature_cols=list(ENGINE_B_FEATURES_QB_V3_CANDIDATE),
        test_year=2020,
        horizon=1,
    )

    train_seasons = set(_value(fold, "train_metadata")["feature_season"])
    test_seasons = set(_value(fold, "test_metadata")["feature_season"])
    train_player_ids = set(_value(fold, "train_metadata")["player_id"])
    train_features = _value(fold, "train_features")
    test_features = _value(fold, "test_features")

    assert train_seasons == {2018, 2019}
    assert test_seasons == {2020}
    assert "mask_ineligible_training_qb" not in train_player_ids
    assert abs(train_features["ppg_t"].mean()) < 1e-10
    assert abs(test_features["ppg_t"].mean()) > 0.1


def test_train_fold_prevalence_baseline_is_used_and_test_fold_prevalence_is_rejected() -> None:
    module = _wf_module()

    baseline = module.compute_train_fold_prevalence_baseline(
        y_train=pd.Series([True, True, True, False]),
        y_test=pd.Series([False, False, False, False]),
    )

    assert baseline == pytest.approx(0.75)
    with pytest.raises(ValueError, match="train-fold"):
        module.compute_train_fold_prevalence_baseline(
            y_train=pd.Series([True, True, True, False]),
            y_test=pd.Series([False, False, False, False]),
            strategy="test_fold_prevalence",
        )


def test_fold_metrics_include_brier_auc_top_k_and_bca_ci_gate_inputs() -> None:
    module = _wf_module()

    metrics = module.compute_qb_v3_fold_metrics(
        fold_index=1,
        test_year=2020,
        horizon=1,
        y_true=pd.Series([True, True, True, False, False, False]),
        probabilities=pd.Series([0.91, 0.82, 0.74, 0.31, 0.22, 0.11]),
        baseline_probability=0.5,
        top_k=12,
        rng_seed=123,
        n_bootstrap=50,
    )

    assert _value(metrics, "model_family") == "regularized_logistic_regression"
    assert _value(metrics, "brier_score") < _value(metrics, "baseline_brier_score")
    assert 0.0 <= _value(metrics, "roc_auc") <= 1.0
    assert _value(metrics, "top_k_precision") == pytest.approx(0.5)
    assert _value(metrics, "top_k") == 12
    ci = _value(metrics, "brier_delta_bca_ci")
    assert set(ci) == {"lower", "upper", "method"}
    assert ci["method"] == "BCa"
    auc_ci = _value(metrics, "auc_delta_bca_ci")
    assert set(auc_ci) == {"lower", "upper", "method"}
    assert auc_ci["method"] == "BCa"


def test_small_n_holdouts_are_excluded_from_averages_but_count_against_eligibility() -> None:
    module = _wf_module()
    fold_metrics = [
        {"horizon": 1, "fold_index": 1, "brier_delta": 0.04, "auc_delta": 0.03},
    ]
    exclusions = [
        {"horizon": 1, "fold_index": 2, "reason": "low_sample_qb_holdout"},
        {"horizon": 1, "fold_index": 3, "reason": "low_sample_qb_holdout"},
        {"horizon": 1, "fold_index": 4, "reason": "low_sample_qb_holdout"},
        {"horizon": 3, "fold_index": 1, "reason": "low_sample_qb_holdout"},
    ]

    summary = module.summarize_qb_v3_horizon_gates(
        fold_metrics=fold_metrics,
        exclusions=exclusions,
        horizons=(1, 3),
    )

    h1 = summary[1]
    h3 = summary[3]
    assert h1["structural_fold_count"] == 4
    assert h1["evaluable_fold_count"] == 1
    assert h1["metric_average_fold_count"] == 1
    assert h1["promotion_eligible"] is False
    assert h1["non_promotion_reason"] == "insufficient_evaluable_structural_folds"
    assert h3["structural_fold_count"] == 3
    assert h3["minimum_evaluable_folds"] == 2


def test_brier_ci_passing_without_auc_ci_does_not_make_promotion_case() -> None:
    module = _wf_module()
    fold_metrics = [
        {
            "horizon": 1,
            "fold_index": fold_index,
            "brier_delta": 0.10,
            "auc_delta": -0.20,
            "brier_delta_bca_ci": {"lower": 0.01, "upper": 0.20, "method": "BCa"},
            "auc_delta_bca_ci": {"lower": -0.02, "upper": 0.05, "method": "BCa"},
        }
        for fold_index in (1, 2, 3)
    ]

    summary = module.summarize_qb_v3_horizon_gates(
        fold_metrics=fold_metrics,
        exclusions=[],
        horizons=(1,),
    )

    assert summary[1]["promotion_eligible"] is False
    assert summary[1]["non_promotion_reason"] == "bca_ci_lower_not_above_zero"


def test_empty_eligible_fold_is_reported_as_exclusion_not_crash() -> None:
    module = _wf_module()
    candidates = _candidate_frame(seasons=(2018, 2019, 2020), rows_per_season=4)
    labels = _labels_for(candidates, horizons=(1,))
    mask = _eligibility_mask(candidates, all_eligible=False)

    report = _report_dict(
        module.run_qb_v3_walk_forward_validation(
            candidate_matrix=candidates,
            labels=labels,
            eligibility_mask=mask,
            feature_cols=list(ENGINE_B_FEATURES_QB_V3_CANDIDATE),
            horizons=(1,),
            test_years=(2020,),
            n_bootstrap=10,
            random_state=123,
        )
    )

    assert report["fold_horizon_metrics"] == []
    assert report["exclusions"] == [
        {"fold_index": 1, "test_year": 2020, "horizon": 1, "reason": "empty_eligible_cohort"}
    ]
    assert report["horizon_summary"][1]["promotion_eligible"] is False


def test_validation_report_is_descriptive_and_contains_no_verdict_fields() -> None:
    module = _wf_module()
    candidates = _candidate_frame()
    labels = _labels_for(candidates)
    mask = _eligibility_mask(candidates)

    report = _report_dict(
        module.run_qb_v3_walk_forward_validation(
            candidate_matrix=candidates,
            labels=labels,
            eligibility_mask=mask,
            feature_cols=list(ENGINE_B_FEATURES_QB_V3_CANDIDATE),
            n_bootstrap=10,
            random_state=123,
        )
    )

    assert report["candidate_head"] == "qb_v3_candidate"
    assert report["decision_supported"] is False
    assert report["model_family"] == "regularized_logistic_regression"
    assert isinstance(report["fold_horizon_metrics"], list)
    assert isinstance(report["exclusions"], list)
    assert set(report["horizon_summary"]) == {1, 2, 3}
    _assert_recursive_decision_supported_false(report)
    _assert_no_verdict_fields(report)


def test_validation_report_is_deterministic_for_fixed_random_state() -> None:
    module = _wf_module()
    candidates = _candidate_frame()
    labels = _labels_for(candidates)
    mask = _eligibility_mask(candidates)

    first = _report_dict(
        module.run_qb_v3_walk_forward_validation(
            candidate_matrix=candidates,
            labels=labels,
            eligibility_mask=mask,
            feature_cols=list(ENGINE_B_FEATURES_QB_V3_CANDIDATE),
            n_bootstrap=10,
            random_state=314,
        )
    )
    second = _report_dict(
        module.run_qb_v3_walk_forward_validation(
            candidate_matrix=candidates,
            labels=labels,
            eligibility_mask=mask,
            feature_cols=list(ENGINE_B_FEATURES_QB_V3_CANDIDATE),
            n_bootstrap=10,
            random_state=314,
        )
    )

    assert second == first


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda df: df.assign(startable_role_occupancy="true"),
            "bool",
        ),
        (
            lambda df: df.drop(columns=["startable_role_occupancy"]),
            "startable_role_occupancy",
        ),
        (
            lambda df: df.assign(feature_season="2020"),
            "season",
        ),
    ],
)
def test_training_labels_fail_closed_on_wrong_type_or_missing_columns(
    mutate: Any,
    expected: str,
) -> None:
    module = _wf_module()
    candidates = _candidate_frame(seasons=(2018, 2019, 2020))
    labels = _labels_for(candidates, horizons=(1,))

    with pytest.raises(ValueError, match=expected):
        module.validate_qb_v3_training_labels(mutate(labels))


def test_leakage_gates_reject_market_and_raw_draft_columns_per_fold() -> None:
    module = _wf_module()
    candidates = _candidate_frame(seasons=(2018, 2019, 2020))
    labels = _labels_for(candidates, horizons=(1,))
    mask = _eligibility_mask(candidates)

    with pytest.raises(ValueError, match="[Pp]rohibited|raw draft"):
        module.build_qb_v3_classification_fold_data(
            candidate_matrix=candidates.assign(ktc_value=1000),
            labels=labels,
            eligibility_mask=mask,
            feature_cols=[*ENGINE_B_FEATURES_QB_V3_CANDIDATE, "ktc_value"],
            test_year=2020,
            horizon=1,
        )


def test_script_exposes_frame_injectable_validation_report_entrypoint() -> None:
    script = importlib.import_module("scripts.generate_qb_v3_validation_report")

    assert callable(script.build_qb_v3_validation_report_from_frames)
