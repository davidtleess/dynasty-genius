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

    assert result["overall_status"] == "all_fail"
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
