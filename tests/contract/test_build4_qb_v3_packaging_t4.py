from __future__ import annotations

import importlib
import re
from typing import Any

import pandas as pd
import pytest

LABEL_BASIS_DISCLOSURE = (
    "startable_role_occupancy@H: positive iff games >= 8 and snap_share >= 0.50; "
    "games_only fallback disclosed; absent target rows and injury/availability "
    "conflation are label caveats."
)


def _packaging_module() -> Any:
    return importlib.import_module("src.dynasty_genius.features.qb_v3_research_output")


def _rookie_filter_module() -> Any:
    return importlib.import_module("src.dynasty_genius.features.qb_rookie_risk_filter")


def _value(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise AssertionError(f"unexpected object type: {type(value)}")


def _candidate_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "player_id": "eligible_qb",
                "feature_season": 2025,
                "age": 24.0,
                "draft_capital_prior": 1.0,
            },
            {
                "player_id": "day3_rookie",
                "feature_season": 2025,
                "age": 22.0,
                "draft_capital_prior": 0.15,
            },
        ]
    )


def _eligibility_mask() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "player_id": "eligible_qb",
                "feature_season": 2025,
                "eligible_for_qb_v3_candidate": True,
                "abstention_reason": None,
            },
            {
                "player_id": "day3_rookie",
                "feature_season": 2025,
                "eligible_for_qb_v3_candidate": False,
                "abstention_reason": "day3_rookie",
            },
        ]
    )


def _probabilities() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"player_id": "eligible_qb", "feature_season": 2025, "horizon": 1, "probability": 0.61},
            {"player_id": "eligible_qb", "feature_season": 2025, "horizon": 2, "probability": 0.54},
            {"player_id": "eligible_qb", "feature_season": 2025, "horizon": 3, "probability": 0.47},
            {"player_id": "day3_rookie", "feature_season": 2025, "horizon": 1, "probability": 0.12},
        ]
    )


def _cohort_priors() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "capital_band": "round_1",
                "horizon": 1,
                "base_rate_survival_prior": 0.63,
                "basis": "historical_role_occupancy_labels",
            },
            {
                "capital_band": "round_1",
                "horizon": 2,
                "base_rate_survival_prior": 0.58,
                "basis": "historical_role_occupancy_labels",
            },
            {
                "capital_band": "round_1",
                "horizon": 3,
                "base_rate_survival_prior": 0.51,
                "basis": "historical_role_occupancy_labels",
            },
            {
                "capital_band": "day3",
                "horizon": 1,
                "base_rate_survival_prior": 0.15,
                "basis": "historical_role_occupancy_labels",
            },
        ]
    )


def _validation_report() -> dict[str, Any]:
    return {
        "candidate_head": "qb_v3_candidate",
        "model_family": "regularized_logistic_regression",
        "horizon_summary": {
            1: {"promotion_eligible": False, "non_promotion_reason": "insufficient_evaluable_structural_folds"},
            2: {"promotion_eligible": False, "non_promotion_reason": "bca_ci_lower_not_above_zero"},
            3: {"promotion_eligible": False, "non_promotion_reason": "bca_ci_lower_not_above_zero"},
        },
        "decision_supported": False,
    }


def _build_research_output() -> dict[str, Any]:
    module = _packaging_module()
    return _as_dict(
        module.build_qb_v3_research_output(
            candidate_matrix=_candidate_matrix(),
            eligibility_mask=_eligibility_mask(),
            probabilities=_probabilities(),
            cohort_priors=_cohort_priors(),
            validation_report=_validation_report(),
            label_basis_disclosure=LABEL_BASIS_DISCLOSURE,
        )
    )


def _assert_decision_supported_false_recursive(value: Any) -> None:
    if isinstance(value, dict):
        if "decision_supported" in value:
            assert value["decision_supported"] is False
        for nested in value.values():
            _assert_decision_supported_false_recursive(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_decision_supported_false_recursive(nested)


def _assert_no_verdict_fields(value: Any) -> None:
    banned = {"promote", "recommend", "buy", "sell", "start", "sit", "tier", "verdict"}
    if isinstance(value, dict):
        assert not (set(value) & banned)
        for nested in value.values():
            _assert_no_verdict_fields(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_verdict_fields(nested)


def test_research_output_discloses_non_promoted_candidate_and_label_basis() -> None:
    output = _build_research_output()

    assert output["candidate_head"] == "qb_v3_candidate"
    assert output["artifact_status"] == "research_only_not_promoted"
    assert output["serving_integration"] is False
    assert output["pvo_integration"] is False
    assert output["decision_supported"] is False
    assert output["label_basis_disclosure"] == LABEL_BASIS_DISCLOSURE
    assert "games >= 8" in output["label_basis_disclosure"]
    assert "snap_share >= 0.50" in output["label_basis_disclosure"]


def test_eligible_qbs_get_probabilities_with_uncalibrated_caveat_and_cohort_prior() -> None:
    output = _build_research_output()
    row = next(row for row in output["rows"] if row["player_id"] == "eligible_qb")

    assert row["eligibility_status"] == "eligible_for_research_probability"
    assert set(row["survival_probabilities_by_horizon"]) == {1, 2, 3}
    assert row["survival_probabilities_by_horizon"][1]["model_probability"] == pytest.approx(0.61)
    assert row["survival_probabilities_by_horizon"][1]["cohort_prior_baseline"] == pytest.approx(0.63)
    assert row["survival_probabilities_by_horizon"][1]["value_type"] == "probability_value"
    assert "uncalibrated_probability" in row["caveats"]
    assert "not_promoted_candidate" in row["caveats"]
    assert "survival_tier" not in row
    assert "franchise_qb" not in str(row).lower()


def test_abstained_qbs_get_no_probability_only_reason_and_base_rate_prior() -> None:
    output = _build_research_output()
    row = next(row for row in output["rows"] if row["player_id"] == "day3_rookie")

    assert row["eligibility_status"] == "abstained"
    assert row["abstention_reason"] == "day3_rookie"
    assert row["base_rate_survival_prior"] == pytest.approx(0.15)
    assert "survival_probabilities_by_horizon" not in row
    assert "model_probability" not in str(row)


def test_research_output_is_descriptive_and_has_no_verdict_fields_or_labels() -> None:
    output = _build_research_output()

    _assert_decision_supported_false_recursive(output)
    _assert_no_verdict_fields(output)
    text = str(output).lower()
    for banned_pattern in (
        r"\bbuy\b",
        r"\bsell\b",
        r"\bhold\b",
        r"\bstart\b",
        r"\bsit\b",
        r"\brecommended\b",
        r"\bfranchise qb\b",
        r"\bbridge qb\b",
    ):
        assert re.search(banned_pattern, text) is None


def test_research_output_contract_fails_closed_on_bad_inputs() -> None:
    module = _packaging_module()
    with pytest.raises(ValueError, match="duplicate"):
        module.build_qb_v3_research_output(
            candidate_matrix=pd.concat([_candidate_matrix(), _candidate_matrix().iloc[[0]]]),
            eligibility_mask=_eligibility_mask(),
            probabilities=_probabilities(),
            cohort_priors=_cohort_priors(),
            validation_report=_validation_report(),
            label_basis_disclosure=LABEL_BASIS_DISCLOSURE,
        )
    with pytest.raises(ValueError, match="horizon"):
        module.build_qb_v3_research_output(
            candidate_matrix=_candidate_matrix(),
            eligibility_mask=_eligibility_mask(),
            probabilities=_probabilities().drop(columns=["horizon"]),
            cohort_priors=_cohort_priors(),
            validation_report=_validation_report(),
            label_basis_disclosure=LABEL_BASIS_DISCLOSURE,
        )
    with pytest.raises(ValueError, match="feature_season"):
        module.build_qb_v3_research_output(
            candidate_matrix=_candidate_matrix().assign(feature_season="2025"),
            eligibility_mask=_eligibility_mask(),
            probabilities=_probabilities(),
            cohort_priors=_cohort_priors(),
            validation_report=_validation_report(),
            label_basis_disclosure=LABEL_BASIS_DISCLOSURE,
        )


def test_research_output_is_deterministic() -> None:
    assert _build_research_output() == _build_research_output()


def _rookie_inputs() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"player_id": "round1_qb", "position": "QB", "draft_number": 12, "age_at_entry": 21.4},
            {"player_id": "day3_qb", "position": "QB", "draft_number": 100, "age_at_entry": 23.1},
            {"player_id": "udfa_qb", "position": "QB", "draft_number": pd.NA, "age_at_entry": 22.8},
        ]
    )


def _rookie_rows(result: Any) -> pd.DataFrame:
    rows = _value(result, "rows")
    assert isinstance(rows, pd.DataFrame)
    return rows


def test_rookie_qb_filter_uses_only_pre_nfl_capital_and_age() -> None:
    module = _rookie_filter_module()
    result = module.classify_rookie_qb_risk(_rookie_inputs())
    rows = _rookie_rows(result).set_index("player_id")

    assert rows.loc["round1_qb", "risk_filter_classification"] == "capital_qualified"
    assert rows.loc["day3_qb", "risk_filter_classification"] == "day3_insufficient_capital"
    assert rows.loc["udfa_qb", "risk_filter_classification"] == "undrafted_insufficient_capital"
    assert rows.loc["round1_qb", "base_rate_survival_prior"] > rows.loc["day3_qb", "base_rate_survival_prior"]
    assert "abstention_badge_text" in rows.columns
    assert "insufficient draft capital" in rows.loc["day3_qb", "abstention_badge_text"]
    assert bool(rows.loc["round1_qb", "decision_supported"]) is False


@pytest.mark.parametrize("leakage_column", ["ppg_t", "snap_share", "epa_per_dropback", "games_t"])
def test_rookie_qb_filter_rejects_nfl_usage_leakage(leakage_column: str) -> None:
    module = _rookie_filter_module()
    with pytest.raises(ValueError, match="NFL usage|leakage"):
        module.classify_rookie_qb_risk(_rookie_inputs().assign(**{leakage_column: 1.0}))


def test_rookie_qb_filter_output_never_contains_engine_b_training_columns() -> None:
    module = _rookie_filter_module()
    result = module.classify_rookie_qb_risk(_rookie_inputs())
    rows = _rookie_rows(result)

    forbidden = {"ppg_t", "snap_share", "epa_per_dropback", "games_t", "draft_capital_prior"}
    assert not forbidden & set(rows.columns)
    assert _value(result, "engine_b_training_integration") is False


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda df: df.drop(columns=["age_at_entry"]), "age_at_entry"),
        (lambda df: df.assign(draft_number="round1"), "draft_number"),
        (lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True), "duplicate"),
    ],
)
def test_rookie_qb_filter_fails_closed_on_bad_contract(
    mutate: Any,
    expected: str,
) -> None:
    module = _rookie_filter_module()
    with pytest.raises(ValueError, match=expected):
        module.classify_rookie_qb_risk(mutate(_rookie_inputs()))


def test_rookie_qb_filter_is_deterministic() -> None:
    module = _rookie_filter_module()

    first = _rookie_rows(module.classify_rookie_qb_risk(_rookie_inputs()))
    second = _rookie_rows(module.classify_rookie_qb_risk(_rookie_inputs()))

    pd.testing.assert_frame_equal(first, second)
