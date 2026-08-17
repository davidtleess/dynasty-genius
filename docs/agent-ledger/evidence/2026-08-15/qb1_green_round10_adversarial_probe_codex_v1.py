"""Fresh round-10 falsification probes for the held QB-1 publication gate.

These tests mutate the submitted positive-control report and assert that an
F13 fold impossible under the shipped producer still publishes ``ok`` through
the public runner. The registered study and its inputs are never executed.
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
        generated_at="2026-08-15T23:15:00Z",
        repo_root=tmp_path,
        registration=registration,
    )


def _case(first_season: int, *, yards: float) -> dict[str, Any]:
    games = 5
    base = yards > 400.0
    minus = yards > 400.0 - games
    plus = yards > 400.0 + games
    row = {
        "season": first_season - 1,
        "rushing_yards": yards,
        "qualifying_games": games,
        "decision_supported": False,
    }
    return {
        "player_id": "qb-boundary",
        "binary_dual_threat": base,
        "flips_at_minus_1_ypg": minus != base,
        "flips_at_plus_1_ypg": plus != base,
        "window_seasons": [dict(row)],
        "boundary_seasons": [dict(row)],
        "decision_supported": False,
    }


def _replace_first_fold(
    payload: dict[str, Any],
    *,
    case: dict[str, Any],
    dual_count: int,
    pocket_count: int,
) -> None:
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"][
        "per_fold"
    ][0]
    fold.update(
        n_evaluable=1,
        dual_threat_count=dual_count,
        pocket_count=pocket_count,
        boundary_case_count=1,
        boundary_cases=[case],
        flips_at_minus_1_ypg=int(case["flips_at_minus_1_ypg"]),
        flips_at_plus_1_ypg=int(case["flips_at_plus_1_ypg"]),
    )


def test_true_boundary_player_can_be_counted_as_pocket(tmp_path: Path) -> None:
    """With n=1, the sole disclosed player is classified True by the gate.

    The producer must therefore emit dual=1/pocket=0. The submitted gate
    recomputes the row boolean but accepts the opposite caller totals.
    """
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    case = _case(registration["folds"]["test_seasons"][0], yards=401.0)
    assert case["binary_dual_threat"] is True
    _replace_first_fold(payload, case=case, dual_count=0, pocket_count=1)

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = report["sensitivity_panels"][0]["binary_dual_threat_gate"][
        "per_fold"
    ][0]
    assert published["dual_threat_count"] == 0
    assert published["boundary_cases"][0]["binary_dual_threat"] is True


def test_false_boundary_player_can_be_counted_as_dual(tmp_path: Path) -> None:
    """The inverse contradiction also publishes.

    At 399/5 the sole player is base-False and minus-shift-True. The producer
    must emit dual=0/pocket=1, but the gate accepts dual=1/pocket=0 while the
    row and flip aggregate remain internally reconciled.
    """
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    case = _case(registration["folds"]["test_seasons"][0], yards=399.0)
    assert case["binary_dual_threat"] is False
    assert case["flips_at_minus_1_ypg"] is True
    _replace_first_fold(payload, case=case, dual_count=1, pocket_count=0)

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    published = report["sensitivity_panels"][0]["binary_dual_threat_gate"][
        "per_fold"
    ][0]
    assert published["pocket_count"] == 0
    assert published["boundary_cases"][0]["binary_dual_threat"] is False

