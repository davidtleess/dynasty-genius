"""Round-5 adversarial reproducers for the held QB-1 execution gate.

These tests assert defective accepted behavior at the pinned round-5 boundary.
They use only hermetic payloads plus the current autonomy audit record; no QB-1
study input is read and no study execution occurs.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import src.dynasty_genius.eval.qb_validation as qb

contracts = importlib.import_module(
    "tests.contract.test_qb1_green_correction_contracts"
)

AUTONOMY_ROOT = Path(
    "/Users/davidleess/dynasty-genius/.git/worktrees/"
    "dynasty-genius-product/dg-autonomy"
)


def _publish(tmp_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    registration = contracts._registration()
    return qb.run_qb1_study(
        execute=lambda: payload,
        output_path=tmp_path / "app/data/backtest/qb_validation/report.json",
        registration_hash=qb.REGISTRATION_PIN,
        generated_at="2026-08-15T00:20:00Z",
        repo_root=tmp_path,
        registration=registration,
    )


def test_public_runner_accepts_metric_free_registered_panels(tmp_path: Path) -> None:
    """F6/F10/F29: key shells are accepted as complete analytical panels."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert all(fold["metrics_with_CIs"] == {} for fold in report["folds"])
    assert all(set(case) == {"id", "scope_note", "decision_supported"} for case in report["case_panel"])
    assert "pooled_deltas" not in report["sensitivity_panels"][1]["unfiltered_primary"]
    assert "pooled_deltas" not in report["sensitivity_panels"][1]["min_four_games"]
    assert "readout" not in report["sensitivity_panels"][2]


def test_public_runner_accepts_invalid_retained_comparison_values(tmp_path: Path) -> None:
    """The H5 retention fields and comparison numerics are presence-only."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    model_row = payload["comparisons"][0]
    model_row["evaluable_folds"] = -9
    model_row["ci95"] = "not-an-interval"
    h5_row = next(row for row in payload["comparisons"] if row["lane"] == "h5")
    h5_row["p_ni"] = "not-a-probability"
    h5_row["ni_met"] = "not-a-boolean"

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["comparisons"][0]["evaluable_folds"] == -9
    assert report["comparisons"][0]["ci95"] == "not-an-interval"
    published_h5 = next(row for row in report["comparisons"] if row["lane"] == "h5")
    assert published_h5["p_ni"] == "not-a-probability"
    assert published_h5["ni_met"] == "not-a-boolean"


def test_public_runner_accepts_unknown_manifest_lanes_and_empty_panel_results(
    tmp_path: Path,
) -> None:
    """Per-lane attrition and the F13 analytical pair remain presence-only."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    payload["folds"][0]["attrition"]["manifest_missing"] = {"not_a_lane": 0}
    threshold = payload["sensitivity_panels"][0]
    threshold["binary_dual_threat_gate"] = True
    threshold["continuous_rushing_moderator"] = None
    threshold["boundary_cases_yards_per_game"] = [-1, 1, 999]

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["folds"][0]["attrition"]["manifest_missing"] == {"not_a_lane": 0}
    assert report["sensitivity_panels"][0]["continuous_rushing_moderator"] is None


def test_cap_repair_left_round4_without_its_open_snapshot() -> None:
    """Renumbering the run record did not renumber its script-owned snapshot."""
    run = json.loads((AUTONOMY_ROOT / "run.json").read_text())
    round4 = next(
        row
        for row in run["reviewRounds"]
        if row["phase"] == "green-review" and row["index"] == 4
    )
    snapshot = AUTONOMY_ROOT / "snapshots/green-review-4"

    assert round4["closedAt"] is not None
    assert round4["churn"]["filesChanged"] == 0
    assert round4["churn"]["linesChanged"] == 0
    assert not (snapshot / "open").exists()
    assert (snapshot / "close").exists()

