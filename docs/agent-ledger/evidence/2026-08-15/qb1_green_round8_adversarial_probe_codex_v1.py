"""Fresh round-8 falsification probes for the held QB-1 publication gate.

Each test mutates the submitted positive-control report and asserts that a
semantically impossible payload still publishes ``run_status=ok`` through the
public runner. The study and its inputs are never executed.
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
        generated_at="2026-08-15T12:15:00Z",
        repo_root=tmp_path,
        registration=registration,
    )


def test_h5_key_presence_counts_a_non_evaluable_fold(tmp_path: Path) -> None:
    """A present metric shell is not a mechanically evaluable fold."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    target = next(
        fold
        for fold in payload["folds"]
        if fold["test_season"] in set(registration["h5"]["folds"])
    )
    target["metrics_with_CIs"]["c11"].update(
        paired_delta=None,
        spearman_left=None,
        spearman_right=None,
        common_pool_n=0,
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["comparisons"][10]["evaluable_folds"] == 4
    assert report["folds"][3]["metrics_with_CIs"]["c11"]["paired_delta"] is None


def test_h5_below_floor_partial_evidence_can_claim_ni_met(tmp_path: Path) -> None:
    """The unavailable-evidence exception admits a partial, self-conflicting row."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    h5_seasons = list(registration["h5"]["folds"])
    row = next(row for row in payload["comparisons"] if row["id"] == "c11")
    row.update(
        evaluable_folds=2,
        pooled_delta=0.01,
        ci95=[-0.02, 0.04],
        p_ni=0.01,
        adjusted_p_ni=None,
        one_sided_lower_95=None,
        ni_met=True,
        support_status="unsupported_power",
        flags=["registered_below_floor_rule"],
        excluded_folds=[
            {
                "test_season": season,
                "reasons": ["join_coverage_low"],
                "decision_supported": False,
            }
            for season in h5_seasons[:2]
        ],
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = report["comparisons"][10]
    assert published["evaluable_folds"] == 2
    assert published["ni_met"] is True
    assert published["p_ni"] == 0.01
    assert published["adjusted_p_ni"] is None


def _f13_case(*, flips_plus: bool) -> dict[str, Any]:
    # 401 yards / 5 games: base threshold 400 is True; the +1-yard-per-game
    # threshold is 405 and therefore False. The shipped computation's plus
    # flip is unambiguously True.
    return {
        "player_id": "qb-boundary",
        "binary_dual_threat": True,
        "flips_at_minus_1_ypg": False,
        "flips_at_plus_1_ypg": flips_plus,
        "boundary_seasons": [
            {
                "season": 2017,
                "rushing_yards": 401.0,
                "qualifying_games": 5,
                "decision_supported": False,
            }
        ],
        "decision_supported": False,
    }


def test_f13_false_negative_flip_publishes(tmp_path: Path) -> None:
    """The gate checks claimed True flips, but trusts an impossible False."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    fold.update(
        n_evaluable=1,
        dual_threat_count=1,
        pocket_count=0,
        boundary_case_count=1,
        boundary_cases=[_f13_case(flips_plus=False)],
        flips_at_minus_1_ypg=0,
        flips_at_plus_1_ypg=0,
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = report["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    assert published["boundary_cases"][0]["flips_at_plus_1_ypg"] is False


def test_f13_aggregate_flip_count_disagrees_with_cases(tmp_path: Path) -> None:
    """A genuine case flip need not reconcile to the per-fold aggregate."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    fold.update(
        n_evaluable=1,
        dual_threat_count=1,
        pocket_count=0,
        boundary_case_count=1,
        boundary_cases=[_f13_case(flips_plus=True)],
        flips_at_minus_1_ypg=0,
        flips_at_plus_1_ypg=0,
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = report["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    assert published["boundary_cases"][0]["flips_at_plus_1_ypg"] is True
    assert published["flips_at_plus_1_ypg"] == 0
