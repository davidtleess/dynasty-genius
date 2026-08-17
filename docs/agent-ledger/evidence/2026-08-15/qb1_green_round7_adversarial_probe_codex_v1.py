"""Round-7 adversarial probes for the held QB-1 public publication gate.

Each test starts from the submitted positive-control payload and asserts a
registered semantic contradiction that still publishes ``run_status=ok``.
No study inputs are read and the QB-1 study is never executed.
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
        generated_at="2026-08-15T10:30:00Z",
        repo_root=tmp_path,
        registration=registration,
    )


def test_public_runner_accepts_supported_in_wrong_direction(tmp_path: Path) -> None:
    """The registered total function requires contradicted, never supported."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    row = payload["comparisons"][0]
    row.update(
        evaluable_folds=8,
        pooled_delta=-0.10,
        ci95=[-0.14, -0.06],
        p_perm=0.01,
        support_status="supported",
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["comparisons"][0]["support_status"] == "supported"


def test_public_runner_accepts_unsupported_power_above_floor(tmp_path: Path) -> None:
    """The power status is also impossible when the registered floor is met."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    payload["comparisons"][0].update(
        evaluable_folds=8,
        pooled_delta=0.10,
        ci95=[0.06, 0.14],
        p_perm=0.01,
        support_status="unsupported_power",
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["comparisons"][0]["evaluable_folds"] == 8
    assert report["comparisons"][0]["support_status"] == "unsupported_power"


def test_public_runner_accepts_more_than_registered_model_folds(
    tmp_path: Path,
) -> None:
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    payload["comparisons"][0].update(
        evaluable_folds=9,
        pooled_delta=0.10,
        ci95=[0.06, 0.14],
        p_perm=0.01,
        support_status="supported",
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["comparisons"][0]["evaluable_folds"] == 9


def test_public_runner_accepts_market_noninferior_with_failed_ni(
    tmp_path: Path,
) -> None:
    """A present raw p value and caller-typed ni_met are not the NI contract."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(
        evaluable_folds=4,
        pooled_delta=0.0,
        ci95=[-0.10, 0.10],
        p_ni=0.99,
        ni_met=True,
        support_status="market_noninferior",
    )
    row.pop("adjusted_p_ni", None)
    row.pop("one_sided_lower_95", None)

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = report["comparisons"][10]
    assert published["p_ni"] == 0.99
    assert published["support_status"] == "market_noninferior"


def test_public_runner_accepts_all_twelve_margin_leaf_shells(
    tmp_path: Path,
) -> None:
    """Cell keys are exact, but every required result leaf may still be empty."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    readout = payload["sensitivity_panels"][2]["readout"]
    for margin_map in readout.values():
        for margin in list(margin_map):
            margin_map[margin] = {}

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert all(
        not leaf
        for margin_map in report["sensitivity_panels"][2]["readout"].values()
        for leaf in margin_map.values()
    )


def test_public_runner_accepts_partial_h5_omission_without_exclusion(
    tmp_path: Path,
) -> None:
    """One omitted H5 contrast bypasses the all-H5-absent flag check."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    target = next(
        fold
        for fold in payload["folds"]
        if fold["test_season"] in set(registration["h5"]["folds"])
    )
    target["metrics_with_CIs"].pop("c11")
    target["flags"] = []
    c11 = next(row for row in payload["comparisons"] if row["id"] == "c11")
    c11["evaluable_folds"] = 3

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published_fold = next(
        fold for fold in report["folds"] if fold["test_season"] == target["test_season"]
    )
    assert "c11" not in published_fold["metrics_with_CIs"]
    assert published_fold["flags"] == []


def test_public_runner_accepts_h5_fold_count_underclaim(tmp_path: Path) -> None:
    """Reconciliation is <=, not equality, even with four produced fold rows."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    c11 = next(row for row in payload["comparisons"] if row["id"] == "c11")
    c11.update(evaluable_folds=0, support_status="unsupported_power")

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert sum("c11" in fold["metrics_with_CIs"] for fold in report["folds"]) == 4
    assert report["comparisons"][10]["evaluable_folds"] == 0


def test_public_runner_accepts_impossible_f13_boundary_semantics(
    tmp_path: Path,
) -> None:
    """The row is shaped correctly but cannot be a ±1-yard boundary case."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    fold.update(
        n_evaluable=1,
        dual_threat_count=0,
        pocket_count=1,
        boundary_case_count=1,
        flips_at_minus_1_ypg=0,
        flips_at_plus_1_ypg=0,
        boundary_cases=[
            {
                "player_id": "fabricated",
                "binary_dual_threat": False,
                "flips_at_minus_1_ypg": False,
                "flips_at_plus_1_ypg": False,
                "boundary_seasons": [
                    {
                        "season": 1900,
                        "rushing_yards": 10000.0,
                        "qualifying_games": -10.5,
                        "decision_supported": False,
                    }
                ],
                "decision_supported": False,
            }
        ],
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = report["sensitivity_panels"][0]["binary_dual_threat_gate"]
    assert (
        published["per_fold"][0]["boundary_cases"][0]["boundary_seasons"][0]["season"]
        == 1900
    )


def test_public_runner_accepts_h5_case_lane_outside_h5_fold(tmp_path: Path) -> None:
    """The declared conditional H5 case-lane restriction is not enforced."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    case = payload["case_panel"][0]
    assert case["fold"] not in set(registration["h5"]["folds"])
    case["lanes"]["h5"] = {
        "state": "reported",
        "y_pred": 1.0,
        "y_true": 2.0,
        "decision_supported": False,
    }

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert "h5" in report["case_panel"][0]["lanes"]
