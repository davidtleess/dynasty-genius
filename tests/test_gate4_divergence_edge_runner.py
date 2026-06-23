"""Gate-4 T2 runner/report contract tests.

The real FantasyCalc archive is T3-gated. These tests use injected fixtures only
and require the runner to wrap the T1 pure engine instead of touching a real DB.
"""
from __future__ import annotations

import json
from datetime import date
from importlib import import_module
from pathlib import Path

import pytest

SPEC_SHA = "84531dc"
RETROSPECTIVE_DISCLAIMER = "retrospective association, not a tradeable edge"


def _runner():
    return import_module("scripts.run_gate4_divergence_edge_validation")


def _archive_provenance() -> dict:
    return {
        "files": [
            {
                "path": "fixture/fc_archive.csv",
                "sha256": "a" * 64,
                "byte_size": 1234,
            }
        ],
        "date_range": {"start": "2025-01-01", "end": "2026-01-01"},
        "snapshot_count": 54,
        "cadence": "weekly",
    }


def _horizon_result(lift_high: float = 12.0) -> dict:
    return {
        "lift_HIGH": lift_high,
        "lift_LOW": 9.0,
        "bootstrap_ci": {
            "HIGH": [1.0, 20.0],
            "LOW": [0.5, 18.0],
        },
        "effect_size": {"HIGH": lift_high, "LOW": 9.0},
        "n_by_bucket": {
            "MODEL_HIGH_MARKET_LOW": 42,
            "MODEL_LOW_MARKET_HIGH": 35,
            "NEUTRAL": 90,
        },
        "effective_month_block_count": 8,
        "non_overlapping_sensitivity_sign": "positive",
    }


def _coverage() -> dict:
    return {
        "usable_t_dates_by_horizon": {"60": 9, "90": 9},
        "joined_observations": 260,
        "identity_coverage": 0.94,
        "per_position_missingness": {"QB": 0.04, "RB": 0.06, "WR": 0.05, "TE": 0.08},
        "matched_surviving_counts": {
            "60": {"MODEL_HIGH_MARKET_LOW": 42, "MODEL_LOW_MARKET_HIGH": 35, "NEUTRAL": 90},
            "90": {"MODEL_HIGH_MARKET_LOW": 40, "MODEL_LOW_MARKET_HIGH": 34, "NEUTRAL": 88},
        },
    }


def _stability() -> dict:
    return {
        "leave_one_month_out_signs": {"60": ["positive"] * 8, "90": ["positive"] * 8},
        "top_position_contribution": 0.44,
        "top_position_excluded": {"position": "WR", "sign": "positive"},
    }


def _falsification() -> dict:
    return {
        "label_shuffle_null": "pass",
        "lookahead_guard": "pass",
        "survivorship_on_off": "pass",
        "within_position_enforcement": "pass",
        "source_family_single_assert": "pass",
    }


def _report_kwargs(**overrides) -> dict:
    base = {
        "verdict": "PASS",
        "claim_level": "current_model_retrospective_diagnostic",
        "training_cutoff": "2026-05-13",
        "source_family": "fc_native",
        "settings_hash": "sf_ppr_12team",
        "archive_provenance": _archive_provenance(),
        "horizon_results": {"60": _horizon_result(), "90": _horizon_result()},
        "coverage": _coverage(),
        "stability": _stability(),
        "falsification": _falsification(),
        "pre_registration_lock": {
            "spec_sha": SPEC_SHA,
            "param_snapshot": {
                "divergence_high_threshold": 20,
                "neutral_band": 5,
                "primary_horizons": [60, 90],
                "effect_size_floor": 8,
                "min_effective_month_blocks": 6,
            },
        },
    }
    base.update(overrides)
    return base


def test_build_report_emits_all_section_8_required_fields() -> None:
    runner = _runner()

    report = runner.build_gate4_report(**_report_kwargs())

    assert report["schema_version"] == "gate4_divergence_edge_report.v1"
    assert report["verdict"] == "PASS"
    assert report["claim_level"] == "current_model_retrospective_diagnostic"
    assert report["training_cutoff"] == "2026-05-13"
    assert report["source_family"] == "fc_native"
    assert report["settings_hash"] == "sf_ppr_12team"
    assert report["archive_provenance"] == _archive_provenance()
    assert set(report["horizons"]) == {"60", "90"}
    for horizon in ["60", "90"]:
        assert set(report["horizons"][horizon]) == {
            "lift_HIGH",
            "lift_LOW",
            "bootstrap_ci",
            "effect_size",
            "n_by_bucket",
            "effective_month_block_count",
            "non_overlapping_sensitivity_sign",
        }
    assert report["coverage"] == _coverage()
    assert report["stability"] == _stability()
    assert report["falsification"] == _falsification()
    assert report["decision_supported"] is False
    assert report["pre_registration_lock"]["spec_sha"] == SPEC_SHA
    runner.validate_gate4_report_schema(report)


def test_report_schema_validator_fails_closed_on_missing_required_field() -> None:
    runner = _runner()
    report = runner.build_gate4_report(**_report_kwargs())
    report.pop("archive_provenance")

    with pytest.raises(runner.Gate4ReportSchemaError, match="archive_provenance"):
        runner.validate_gate4_report_schema(report)


@pytest.mark.parametrize(
    "path",
    [
        ("archive_provenance", "files"),
        ("archive_provenance", "date_range"),
        ("archive_provenance", "snapshot_count"),
        ("archive_provenance", "cadence"),
        ("archive_provenance", "date_range", "start"),
        ("archive_provenance", "date_range", "end"),
        ("coverage", "usable_t_dates_by_horizon"),
        ("coverage", "joined_observations"),
        ("coverage", "identity_coverage"),
        ("coverage", "per_position_missingness"),
        ("coverage", "matched_surviving_counts"),
        ("stability", "leave_one_month_out_signs"),
        ("stability", "top_position_contribution"),
        ("stability", "top_position_excluded"),
        ("falsification", "label_shuffle_null"),
        ("falsification", "lookahead_guard"),
        ("falsification", "survivorship_on_off"),
        ("falsification", "within_position_enforcement"),
        ("falsification", "source_family_single_assert"),
        ("pre_registration_lock", "param_snapshot"),
    ],
)
def test_report_schema_validator_fails_closed_on_missing_nested_required_field(
    path: tuple[str, ...],
) -> None:
    runner = _runner()
    report = runner.build_gate4_report(**_report_kwargs())
    node = report
    for key in path[:-1]:
        node = node[key]
    node.pop(path[-1])

    with pytest.raises(runner.Gate4ReportSchemaError, match=path[-1]):
        runner.validate_gate4_report_schema(report)


@pytest.mark.parametrize(
    ("bad_files", "expected"),
    [
        ([], "files"),
        ([{"sha256": "a" * 64, "byte_size": 1234}], "path"),
        ([{"path": "fixture.csv", "byte_size": 1234}], "sha256"),
        ([{"path": "fixture.csv", "sha256": "a" * 64}], "byte_size"),
    ],
)
def test_report_schema_validator_fails_closed_on_bad_archive_file_entries(
    bad_files: list[dict],
    expected: str,
) -> None:
    runner = _runner()
    report = runner.build_gate4_report(**_report_kwargs())
    report["archive_provenance"]["files"] = bad_files

    with pytest.raises(runner.Gate4ReportSchemaError, match=expected):
        runner.validate_gate4_report_schema(report)


def test_retrospective_pass_statements_carry_required_disclaimer() -> None:
    runner = _runner()

    report = runner.build_gate4_report(**_report_kwargs())

    assert RETROSPECTIVE_DISCLAIMER in report["summary"]["claim_level_disclaimer"]
    pass_statements = report["summary"]["pass_statements"]
    assert pass_statements
    assert all(RETROSPECTIVE_DISCLAIMER in statement for statement in pass_statements)


def test_tradeable_pass_does_not_need_retrospective_disclaimer() -> None:
    runner = _runner()

    report = runner.build_gate4_report(
        **_report_kwargs(
            claim_level="tradeable_historical_edge",
            training_cutoff="2024-12-31",
        )
    )

    assert RETROSPECTIVE_DISCLAIMER not in report["summary"].get(
        "claim_level_disclaimer", ""
    )


def test_report_is_aggregate_only_and_recursive_decision_supported_false() -> None:
    runner = _runner()

    report = runner.build_gate4_report(**_report_kwargs())
    runner.assert_aggregate_only_report(report)
    runner.assert_recursive_decision_supported_false(report)

    with_player = json.loads(json.dumps(report))
    with_player["horizons"]["60"]["rows"] = [{"player_id": "00-003", "lift": 12.0}]
    with pytest.raises(runner.Gate4ReportSchemaError, match="aggregate-only"):
        runner.assert_aggregate_only_report(with_player)

    with_true_decision = json.loads(json.dumps(report))
    with_true_decision["coverage"]["decision_supported"] = True
    with pytest.raises(runner.Gate4ReportSchemaError, match="decision_supported"):
        runner.assert_recursive_decision_supported_false(with_true_decision)


def test_runner_uses_injected_loader_and_analyzer_and_writes_tmp_report(tmp_path: Path) -> None:
    runner = _runner()
    calls: list[str] = []

    def load_fixture() -> dict:
        calls.append("load")
        return {
            "source_family": "fc_native",
            "settings_hash": "sf_ppr_12team",
            "archive_provenance": _archive_provenance(),
            "test_dates": [date(2025, 1, 1), date(2025, 2, 1)],
            "training_cutoff": date(2026, 5, 13),
            "coverage_gate_status": "ok",
        }

    def analyze_fixture(loaded: dict, *, claim_level: str) -> dict:
        calls.append(f"analyze:{claim_level}")
        assert loaded["settings_hash"] == "sf_ppr_12team"
        return {
            "verdict": "PASS",
            "horizon_results": {"60": _horizon_result(), "90": _horizon_result()},
            "coverage": _coverage(),
            "stability": _stability(),
            "falsification": _falsification(),
        }

    path = runner.run_gate4_validation(
        load_archive=load_fixture,
        analyze=analyze_fixture,
        output_dir=tmp_path,
        run_id="fixture-run",
        spec_sha=SPEC_SHA,
    )

    assert calls == ["load", "analyze:current_model_retrospective_diagnostic"]
    assert path == tmp_path / "gate4_divergence_edge_fixture-run.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["pre_registration_lock"]["spec_sha"] == SPEC_SHA
    assert report["decision_supported"] is False
    assert (tmp_path / "gate4_divergence_edge_latest.json").exists()
    runner.assert_aggregate_only_report(report)


def test_runner_coverage_gate_failure_stops_before_analyzer_and_write(tmp_path: Path) -> None:
    runner = _runner()

    def load_fixture() -> dict:
        return {
            "source_family": "fc_native",
            "settings_hash": "sf_ppr_12team",
            "archive_provenance": _archive_provenance(),
            "test_dates": [date(2025, 1, 1)],
            "training_cutoff": date(2024, 12, 31),
            "coverage_gate_status": "missing_archive",
        }

    def analyze_fixture(_loaded: dict, *, claim_level: str) -> dict:
        raise AssertionError("coverage gate failure must stop before analysis")

    with pytest.raises(runner.Gate4RunnerError, match="coverage gate"):
        runner.run_gate4_validation(
            load_archive=load_fixture,
            analyze=analyze_fixture,
            output_dir=tmp_path,
            run_id="bad",
            spec_sha=SPEC_SHA,
        )

    assert not list(tmp_path.glob("gate4_divergence_edge_*.json"))
