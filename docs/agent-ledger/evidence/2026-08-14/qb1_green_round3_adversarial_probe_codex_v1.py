"""Round-3 adversarial reproducers for the held QB-1 execution gate.

The tests assert reviewed defective behavior, so they pass before correction
and should fail when the corresponding gaps are closed.  All analytical data
is synthetic; this file never executes the registered study on real inputs.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import src.dynasty_genius.eval.qb_validation as qb

runner = importlib.import_module("scripts.run_qb1_study")
contracts = importlib.import_module(
    "tests.contract.test_qb1_green_correction_contracts"
)


def test_runner_publishes_incomplete_registered_schema_as_ok(tmp_path: Path) -> None:
    """The public runner never invokes the separate registered-schema gate."""
    destination = tmp_path / "app/data/backtest/qb_validation/report.json"
    report = qb.run_qb1_study(
        execute=lambda: {
            "run_status": "ok",
            "decision_supported": False,
            "inputs": {},
            "folds": [],
            "comparisons": [],
            "case_panel": [],
            "sensitivity_panels": [],
        },
        output_path=destination,
        registration_hash=qb.REGISTRATION_PIN,
        generated_at="2026-08-14T20:00:00Z",
        repo_root=tmp_path,
    )

    assert report["run_status"] == "ok"
    assert "disclosures" not in report
    assert destination.exists()


def test_registered_schema_gate_admits_unregistered_fold_flag() -> None:
    """D5 closes the fold-flag vocabulary; the new validator does not."""
    registration = contracts._registration()
    qb.validate_registered_report_blocks(
        {
            "disclosures": [
                {**row, "decision_supported": False}
                for row in registration["disclosures"]
            ],
            "folds": [
                {
                    "test_season": 2025,
                    "attrition": {
                        "no_target_season": 0,
                        "rookie_no_priors": 0,
                        "cohort_ineligible_prior": 0,
                        "cohort_ineligible_unobserved": 0,
                        "manifest_missing": {"h1": 0},
                    },
                    "metrics_with_CIs": {},
                    "flags": ["not_a_registered_fold_flag"],
                    "decision_supported": False,
                }
            ],
            "comparisons": [
                {
                    "id": "c01",
                    "lane": "model",
                    "registered_direction": "h1_gt_naive",
                    "pooled_delta": 0.0,
                    "ci95": [None, None],
                    "p_perm": None,
                    "support_status": "unsupported_power",
                    "evaluable_folds": 0,
                    "decision_supported": False,
                }
            ],
        },
        registration=registration,
    )


@pytest.fixture(scope="module")
def composed_defect_evidence(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], list[set[str]], int]:
    """Drive the production composition once and expose two semantic defects."""
    tmp_path = tmp_path_factory.mktemp("qb1-round3-compose")
    real_fit = qb.fit_ridge_lane
    injected_count = 0
    frozen_calls: list[set[str]] = []

    def fit_with_known_missing(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal injected_count
        result = real_fit(*args, **kwargs)
        if kwargs.get("lane") == "h1":
            result["missingness"]["test_manifest_missing"] = {
                "count": 7,
                "keys": [["synthetic", result["test_season"]]],
            }
            injected_count += 1
        return result

    def capture_frozen(expected: Any) -> None:
        frozen_calls.append({Path(path).name for path in expected})

    h5_inputs = contracts._h5_inputs(tmp_path)
    with (
        patch.object(qb, "fit_ridge_lane", side_effect=fit_with_known_missing),
        patch.object(qb, "validate_frozen_hashes", side_effect=capture_frozen),
    ):
        report = runner.compose_study(
            registration=contracts._registration(),
            pool=contracts._hermetic_pool(tmp_path),
            repo_root=tmp_path,
            frozen_inputs={tmp_path / "crosswalk.json": "fixture"},
            **h5_inputs,
        )
    return report, frozen_calls, injected_count


def test_manifest_missing_mapping_is_reported_as_zero(
    composed_defect_evidence: tuple[dict[str, Any], list[set[str]], int],
) -> None:
    report, _frozen_calls, injected_count = composed_defect_evidence
    assert injected_count == len(report["folds"])
    assert all(
        fold["attrition"]["manifest_missing"]["h1"] == 0
        for fold in report["folds"]
    )


def test_f25_checks_study_inputs_instead_of_registered_frozen_set(
    composed_defect_evidence: tuple[dict[str, Any], list[set[str]], int],
) -> None:
    _report, frozen_calls, _injected_count = composed_defect_evidence
    observed = set().union(*frozen_calls)
    assert len(frozen_calls) == 2
    assert observed == {
        "crosswalk.json",
        "values_2021.csv",
        "values_2022.csv",
        "values_2023.csv",
        "values_2024.csv",
    }
    assert observed.isdisjoint(
        {
            "model_registry.json",
            "qb_v2.pkl",
            "v2_manifest.json",
            "qb_v3_walk_forward.py",
            "2026-07-04-build4-qb-v3-promotion-decision-record.md",
        }
    )


def test_f13_uses_nonqualifying_rows_as_games_in_boundary_arithmetic() -> None:
    weekly = [
        {
            "player_id": "boundary",
            "season": 2020,
            "attempts": 1,
            "sacks_suffered": 0,
            "carries": 0,
            "rushing_yards": 398.5,
        },
        {
            "player_id": "boundary",
            "season": 2020,
            "attempts": 0,
            "sacks_suffered": 0,
            "carries": 0,
            "rushing_yards": 0.0,
        },
    ]
    rushing = runner.build_season_rushing(weekly)
    panel = runner.build_archetype_threshold_panel(
        [
            {
                "test_season": 2021,
                "test_rows": [
                    {
                        "player_id": "boundary",
                        "target": "target_evaluable",
                        "rush_yds_per_game": 398.5,
                    }
                ],
            }
        ],
        rushing,
    )
    fold = panel["binary_dual_threat_gate"]["per_fold"][0]

    qualifying_games = sum(
        (row["attempts"] + row["sacks_suffered"] >= 1) or row["carries"] >= 1
        for row in weekly
    )
    assert qualifying_games == 1
    assert rushing[("boundary", 2020)]["weeks"] == 2
    assert fold["flips_at_minus_1_ypg"] == 1
    assert not (398.5 > 400.0 - qualifying_games)
