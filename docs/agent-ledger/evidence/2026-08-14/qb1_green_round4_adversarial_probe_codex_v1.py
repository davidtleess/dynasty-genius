"""Round-4 adversarial reproducers for the held QB-1 execution gate.

These tests assert defective accepted behavior.  They pass on the reviewed
round-4 boundary and should fail once the registered D5 publication schema is
enforced completely.  No real study input is read and no study is executed.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import src.dynasty_genius.eval.qb_validation as qb

contracts = importlib.import_module(
    "tests.contract.test_qb1_green_correction_contracts"
)


def _publish(tmp_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    registration = contracts._registration()
    return qb.run_qb1_study(
        execute=lambda: payload,
        output_path=tmp_path / "app/data/backtest/qb_validation/report.json",
        registration_hash=qb.REGISTRATION_PIN,
        generated_at="2026-08-14T23:00:00Z",
        repo_root=tmp_path,
        registration=registration,
    )


def test_runner_admits_partial_registered_study(tmp_path: Path) -> None:
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert len(report["folds"]) == 1
    assert len(registration["folds"]["test_seasons"]) == 8
    assert len(report["comparisons"]) == 1
    assert len(registration["contrasts"]) == 14
    assert "settings_hash" not in report["inputs"]
    assert "matrix_version" not in report["inputs"]


def test_runner_admits_negative_fold_census(tmp_path: Path) -> None:
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    fold = payload["folds"][0]
    fold["n_evaluable"] = -1
    fold["attrition"]["no_target_season"] = -4
    fold["attrition"]["manifest_missing"] = {"h1": -7}
    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["folds"][0]["n_evaluable"] == -1
    assert report["folds"][0]["attrition"]["no_target_season"] == -4
    assert report["folds"][0]["attrition"]["manifest_missing"]["h1"] == -7


def test_runner_admits_lane_invalid_comparisons(tmp_path: Path) -> None:
    registration = contracts._registration()

    model_payload = contracts._complete_ok_payload(registration)
    model_payload["comparisons"][0]["support_status"] = "market_superior"
    model_report = _publish(tmp_path, model_payload)
    assert model_report["run_status"] == "ok"
    assert model_report["comparisons"][0]["lane"] == "model"
    assert model_report["comparisons"][0]["support_status"] == "market_superior"

    h5_payload = contracts._complete_ok_payload(registration)
    h5_payload["comparisons"][0].update(
        {
            "id": "c11",
            "lane": "h5",
            "registered_direction": "market_noninferior_delta_gt_delta0",
            "support_status": "unsupported_power",
        }
    )
    h5_report = _publish(tmp_path, h5_payload)
    assert h5_report["run_status"] == "ok"
    assert "p_ni" not in h5_report["comparisons"][0]
    assert "ni_met" not in h5_report["comparisons"][0]


def test_runner_skips_case_and_sensitivity_schema_guards(tmp_path: Path) -> None:
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    payload["case_panel"] = [
        {"id": "not_a_registered_case", "decision_supported": False}
    ]
    payload["sensitivity_panels"] = [
        {"id": "not_a_registered_panel", "decision_supported": False}
    ]
    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["case_panel"][0]["id"] == "not_a_registered_case"
    assert report["sensitivity_panels"][0]["id"] == "not_a_registered_panel"
