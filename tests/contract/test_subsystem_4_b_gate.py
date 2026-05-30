"""Subsystem 4 Backtest-B gate contract tests (§5.5-§5.7)."""
from __future__ import annotations

import builtins

import pytest

from src.dynasty_genius.eval import backtest_mock_draft as bmd


def _status(
    per_bucket_breakdown: dict,
    *,
    data_mode: str = "real",
    draft_date_source: str = "nflreadr.draft_picks",
):
    return bmd.evaluate_b_gate(
        {},
        per_bucket_breakdown,
        data_mode=data_mode,
        draft_date_source=draft_date_source,
    )


def test_evaluate_b_gate_passes_bucket_when_mae_and_coverage_meet_thresholds():
    result = _status({"R1-early": {"QB": {"mae": 8.0, "coverage": 0.80}}})

    assert result["overall_status"] == "all_pass"
    assert result["per_bucket_results"]["R1-early|QB"] == {
        "gate_result": "pass",
        "mae": 8.0,
        "coverage": 0.80,
    }


def test_evaluate_b_gate_fails_bucket_when_mae_exceeds_threshold():
    result = _status({"R1-mid": {"WR": {"mae": 12.1, "coverage": 0.70}}})

    assert result["overall_status"] == "all_fail"
    assert result["per_bucket_results"]["R1-mid|WR"]["gate_result"] == "fail"


def test_evaluate_b_gate_fails_bucket_when_coverage_below_threshold():
    result = _status({"R2": {"RB": {"mae": 18.0, "coverage": 0.59}}})

    assert result["overall_status"] == "all_fail"
    assert result["per_bucket_results"]["R2|RB"]["gate_result"] == "fail"


def test_evaluate_b_gate_reports_partial_when_some_buckets_pass_and_some_fail():
    result = _status(
        {
            "R1-late": {"TE": {"mae": 11.5, "coverage": 0.70}},
            "R2": {"WR": {"mae": 19.0, "coverage": 0.80}},
        }
    )

    assert result["overall_status"] == "partial"
    assert result["per_bucket_results"]["R1-late|TE"]["gate_result"] == "pass"
    assert result["per_bucket_results"]["R2|WR"]["gate_result"] == "fail"


def test_evaluate_b_gate_always_abstains_r3_and_day3_regardless_of_metrics():
    result = _status(
        {
            "R3": {"WR": {"mae": 0.0, "coverage": 1.0}},
            "Day3": {"RB": {"mae": 0.0, "coverage": 1.0}},
        }
    )

    assert result["overall_status"] == "always_abstain"
    assert result["per_bucket_results"]["R3|WR"] == {
        "gate_result": "always_abstain",
        "mae": 0.0,
        "coverage": 1.0,
    }
    assert result["per_bucket_results"]["Day3|RB"] == {
        "gate_result": "always_abstain",
        "mae": 0.0,
        "coverage": 1.0,
    }


def test_evaluate_b_gate_empty_breakdown_fails_closed():
    result = _status({})

    assert result["overall_status"] == "all_fail"
    assert result["per_bucket_results"] == {}


def test_evaluate_b_gate_pass_plus_always_abstain_rolls_up_to_all_pass():
    result = _status(
        {
            "R1-early": {"QB": {"mae": 8.0, "coverage": 0.80}},
            "R3": {"WR": {"mae": 0.0, "coverage": 1.0}},
        }
    )

    assert result["overall_status"] == "all_pass"
    assert result["per_bucket_results"]["R1-early|QB"]["gate_result"] == "pass"
    assert result["per_bucket_results"]["R3|WR"]["gate_result"] == "always_abstain"


def test_evaluate_b_gate_fail_plus_always_abstain_rolls_up_to_all_fail():
    result = _status(
        {
            "R2": {"RB": {"mae": 25.0, "coverage": 0.80}},
            "Day3": {"TE": {"mae": 0.0, "coverage": 1.0}},
        }
    )

    assert result["overall_status"] == "all_fail"
    assert result["per_bucket_results"]["R2|RB"]["gate_result"] == "fail"
    assert result["per_bucket_results"]["Day3|TE"]["gate_result"] == "always_abstain"


def test_evaluate_b_gate_pass_fail_and_always_abstain_rolls_up_to_partial():
    result = _status(
        {
            "R1-late": {"WR": {"mae": 12.0, "coverage": 0.70}},
            "R2": {"RB": {"mae": 25.0, "coverage": 0.80}},
            "R3": {"TE": {"mae": 0.0, "coverage": 1.0}},
        }
    )

    assert result["overall_status"] == "partial"
    assert result["per_bucket_results"]["R1-late|WR"]["gate_result"] == "pass"
    assert result["per_bucket_results"]["R2|RB"]["gate_result"] == "fail"
    assert result["per_bucket_results"]["R3|TE"]["gate_result"] == "always_abstain"


@pytest.mark.parametrize(
    ("data_mode", "draft_date_source"),
    [
        ("synthetic", "nflreadr.draft_picks"),
        ("real", "override:manual_fixture_date"),
    ],
)
def test_evaluate_b_gate_synthetic_inputs_force_always_abstain_with_schema_shape(
    data_mode: str,
    draft_date_source: str,
):
    result = _status(
        {"R1-early": {"QB": {"mae": 0.0, "coverage": 1.0}}},
        data_mode=data_mode,
        draft_date_source=draft_date_source,
    )

    assert result["overall_status"] == "always_abstain_synthetic_data"
    assert result["per_bucket_results"]["R1-early|QB"] == {
        "gate_result": "not_evaluable_synthetic",
        "mae": None,
        "coverage": None,
    }


def test_evaluate_b_gate_synthetic_hedge_ignores_malformed_stat_values():
    result = _status(
        {"R1-early": {"n_realized": 1, "n_scored": 1}},
        data_mode="synthetic",
        draft_date_source="x",
    )

    assert result["overall_status"] == "always_abstain_synthetic_data"
    assert result["per_bucket_results"]["R1-early|n_realized"] == {
        "gate_result": "not_evaluable_synthetic",
        "mae": None,
        "coverage": None,
    }
    assert result["per_bucket_results"]["R1-early|n_scored"] == {
        "gate_result": "not_evaluable_synthetic",
        "mae": None,
        "coverage": None,
    }


@pytest.mark.parametrize(
    ("per_bucket_breakdown", "expected_key"),
    [
        ({"R1-early": {"n_realized": 1}}, "R1-early|n_realized"),
        ({"R1-mid": {"QB": {"coverage": 0.80}}}, "R1-mid|QB"),
        ({"R2": {"RB": {"mae": None, "coverage": 0.80}}}, "R2|RB"),
        ({"R1-early": {"QB": {"mae": "garbage", "coverage": 0.80}}}, "R1-early|QB"),
        ({"R1-mid": {"WR": {"mae": 10.0, "coverage": "garbage"}}}, "R1-mid|WR"),
    ],
)
def test_evaluate_b_gate_real_mode_malformed_stats_fail_closed(
    per_bucket_breakdown: dict,
    expected_key: str,
):
    result = _status(per_bucket_breakdown, data_mode="real")

    assert result["overall_status"] == "all_fail"
    assert result["per_bucket_results"][expected_key] == {
        "gate_result": "fail",
        "mae": None,
        "coverage": None,
    }


def test_evaluate_b_gate_real_mode_malformed_bucket_structure_fails_closed():
    result = _status(
        {
            "R1-early": {"QB": {"mae": 8.0, "coverage": 0.80}},
            "R2": "garbage_string",
        },
        data_mode="real",
    )

    assert result["overall_status"] == "partial"
    assert result["per_bucket_results"]["R1-early|QB"]["gate_result"] == "pass"
    assert result["per_bucket_results"]["R2|__malformed__"] == {
        "gate_result": "fail",
        "mae": None,
        "coverage": None,
    }


def test_evaluate_b_gate_records_two_tier_thresholds_and_gate_version():
    result = _status({"R1-early": {"QB": {"mae": 8.0, "coverage": 0.80}}})

    assert result["gate_version"] == bmd.GATE_VERSION
    assert result["thresholds"] == {
        "evidence_to_evaluate_a_top_36_bridge_coverage": 0.90,
        "b_gate_required_truth_coverage": 1.00,
        "bucket_thresholds": {
            "R1-early": {"mae_max": 8.0, "coverage_min": 0.80},
            "R1-mid": {"mae_max": 12.0, "coverage_min": 0.70},
            "R1-late": {"mae_max": 12.0, "coverage_min": 0.70},
            "R2": {"mae_max": 18.0, "coverage_min": 0.60},
            "R3": {"gate_result": "always_abstain"},
            "Day3": {"gate_result": "always_abstain"},
        },
    }


def test_evaluate_b_gate_is_pure_function_with_no_filesystem_writes(monkeypatch):
    writes: list[str] = []
    real_open = builtins.open

    def fail_on_write(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            writes.append(str(file))
            raise AssertionError(f"unexpected write to {file}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fail_on_write)

    result = _status({"R1-early": {"QB": {"mae": 8.0, "coverage": 0.80}}})

    assert result["overall_status"] == "all_pass"
    assert writes == []
