"""Independent round-6 adversarial probes for the held QB-1 execution gate.

Each test starts from Claude's complete positive-control payload, changes one
semantic class, and asserts that the PUBLIC runner still publishes ``ok``.
The study itself is never executed; all inputs are hermetic report payloads.
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
        generated_at="2026-08-15T12:00:00Z",
        repo_root=tmp_path,
        registration=registration,
    )


def test_public_runner_accepts_empty_mandatory_h5_margin_readouts(
    tmp_path: Path,
) -> None:
    """Registration §9.2 requires all three margins regardless of outcome."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    margin_panel = payload["sensitivity_panels"][2]
    margin_panel["readout"] = {
        contrast_id: {} for contrast_id in ("c11", "c12", "c13", "c14")
    }

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert all(not row for row in report["sensitivity_panels"][2]["readout"].values())


def test_public_runner_accepts_positive_h5_result_without_fold_evidence(
    tmp_path: Path,
) -> None:
    """A substantive H5 result may claim four folds while all fold rows omit H5."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    for fold in payload["folds"]:
        for contrast_id in ("c11", "c12", "c13", "c14"):
            fold["metrics_with_CIs"].pop(contrast_id, None)
    h5 = next(row for row in payload["comparisons"] if row["id"] == "c11")
    h5.update(
        pooled_delta=0.10,
        ci95=[0.06, 0.14],
        p_ni=0.01,
        ni_met=True,
        support_status="market_noninferior",
        evaluable_folds=4,
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert all("c11" not in fold["metrics_with_CIs"] for fold in report["folds"])
    assert report["comparisons"][10]["support_status"] == "market_noninferior"


def test_public_runner_accepts_statuses_that_violate_the_fold_floor(
    tmp_path: Path,
) -> None:
    """Section 7 makes unsupported_power mandatory below each lane's floor."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    model = next(row for row in payload["comparisons"] if row["id"] == "c01")
    model.update(
        pooled_delta=0.10,
        ci95=[0.06, 0.14],
        p_perm=0.01,
        support_status="supported",
        evaluable_folds=0,
    )
    h5 = next(row for row in payload["comparisons"] if row["id"] == "c11")
    h5.update(
        pooled_delta=0.10,
        ci95=[0.06, 0.14],
        p_ni=0.01,
        ni_met=True,
        support_status="market_noninferior",
        evaluable_folds=0,
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["comparisons"][0]["support_status"] == "supported"
    assert report["comparisons"][0]["evaluable_folds"] == 0
    assert report["comparisons"][10]["support_status"] == "market_noninferior"
    assert report["comparisons"][10]["evaluable_folds"] == 0


def test_public_runner_accepts_fabricated_f13_computed_content(
    tmp_path: Path,
) -> None:
    """A typed mapping is accepted even when it cannot be the shipped computation."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    gate = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]
    gate["rule"] = "an unrelated nonempty rule"
    gate["threshold_yards"] = -123.0
    for fold in gate["per_fold"]:
        fold.update(
            n_evaluable=1,
            dual_threat_count=999,
            pocket_count=999,
            boundary_case_count=999,
            boundary_cases=[],
        )
    payload["sensitivity_panels"][0]["continuous_rushing_moderator"] = {
        "basis": "unrelated nonempty basis",
        "decision_supported": False,
    }

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = report["sensitivity_panels"][0]["binary_dual_threat_gate"]
    assert published["threshold_yards"] == -123.0
    assert published["per_fold"][0]["dual_threat_count"] == 999


def test_public_runner_accepts_unproduced_case_identity_and_lane(
    tmp_path: Path,
) -> None:
    """Blank identities and an unregistered lane still satisfy the case gate."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    case = next(row for row in payload["case_panel"] if row["id"] == "allen_2019_twin")
    case["player_name"] = ""
    case["gsis_id"] = ""
    case["lanes"] = {
        "fabricated_lane": {
            "state": "reported",
            "y_pred": 1.0,
            "y_true": 2.0,
            "decision_supported": False,
        }
    }

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = next(
        row for row in report["case_panel"] if row["id"] == "allen_2019_twin"
    )
    assert published["player_name"] == ""
    assert set(published["lanes"]) == {"fabricated_lane"}


def test_public_runner_accepts_empty_fold_ci_content(tmp_path: Path) -> None:
    """The required per-fold ci mapping may still be an empty shell."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    payload["folds"][0]["metrics_with_CIs"]["c01"]["ci"] = {}

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["folds"][0]["metrics_with_CIs"]["c01"]["ci"] == {}
