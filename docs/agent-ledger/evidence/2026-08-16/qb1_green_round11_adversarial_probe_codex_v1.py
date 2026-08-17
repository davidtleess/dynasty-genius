"""Fresh Round-11 falsification probes for F13 source-evidence totality.

The tests first obtain a truthful F13 fold from the shipped producer, then
replace its disclosed evidence with a different, internally consistent story
before passing the report through the public terminal runner. Passing tests are
the defect: the publication gate accepted evidence that is not the evidence the
producer read. The registered study and provider inputs are never executed.
"""

from __future__ import annotations

import importlib
from copy import deepcopy
from pathlib import Path
from typing import Any

import src.dynasty_genius.eval.qb_validation as qb

contracts = importlib.import_module(
    "tests.contract.test_qb1_green_correction_contracts"
)
runner = importlib.import_module("scripts.run_qb1_study")


def _publish(tmp_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    registration = contracts._registration()
    return qb.run_qb1_study(
        execute=lambda: payload,
        output_path=tmp_path / "app/data/backtest/qb_validation/report.json",
        registration_hash=qb.REGISTRATION_PIN,
        generated_at="2026-08-16T07:45:00-04:00",
        repo_root=tmp_path,
        registration=registration,
    )


def _truthful_boundary_fold(first_season: int) -> dict[str, Any]:
    folds = [
        {
            "test_season": first_season,
            "test_rows": [
                {
                    "player_id": "qb-real",
                    "target": "target_evaluable",
                    "rush_yds_per_game": 80.2,
                    "rush_att_per_game": 8.0,
                }
            ],
        }
    ]
    rushing = {
        ("qb-real", first_season - 1): {
            "rushing_yards": 401.0,
            "weeks": 5,
        }
    }
    return runner.build_archetype_threshold_panel(folds, rushing)[
        "binary_dual_threat_gate"
    ]["per_fold"][0]


def test_complete_observed_window_can_be_concealed_as_absence(tmp_path: Path) -> None:
    """The producer read 401/5, so the player is dual, boundary, and +1-flips.

    Replacing that complete observed window with [] and changing every derived
    field to the new self-consistent pocket/no-boundary story still publishes.
    """
    registration = contracts._registration()
    first_season = registration["folds"]["test_seasons"][0]
    truthful = _truthful_boundary_fold(first_season)
    assert truthful["dual_threat_count"] == 1
    assert truthful["boundary_case_count"] == 1
    assert truthful["flips_at_plus_1_ypg"] == 1
    assert truthful["evaluable_players"][0]["window_seasons"]

    concealed = deepcopy(truthful)
    concealed.update(
        dual_threat_count=0,
        pocket_count=1,
        evaluable_players=[
            {
                "player_id": "qb-real",
                "window_seasons": [],
                "decision_supported": False,
            }
        ],
        boundary_case_count=0,
        boundary_cases=[],
        flips_at_minus_1_ypg=0,
        flips_at_plus_1_ypg=0,
    )
    payload = contracts._complete_ok_payload(registration)
    payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][
        0
    ] = concealed

    report = _publish(tmp_path, payload)
    assert report["run_status"] == "ok"
    published = report["sensitivity_panels"][0]["binary_dual_threat_gate"][
        "per_fold"
    ][0]
    assert published["evaluable_players"][0]["window_seasons"] == []
    assert published["pocket_count"] == 1


def test_evaluable_player_identity_can_be_substituted(tmp_path: Path) -> None:
    """The evidence values stay exact, but the producer's player disappears.

    An arbitrary replacement id carrying the real player's evidence still
    satisfies every submitted aggregate and membership check.
    """
    registration = contracts._registration()
    first_season = registration["folds"]["test_seasons"][0]
    truthful = _truthful_boundary_fold(first_season)
    assert truthful["evaluable_players"][0]["player_id"] == "qb-real"

    substituted = deepcopy(truthful)
    substituted["evaluable_players"][0]["player_id"] = "qb-substitute"
    substituted["boundary_cases"][0]["player_id"] = "qb-substitute"

    payload = contracts._complete_ok_payload(registration)
    payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][
        0
    ] = substituted

    report = _publish(tmp_path, payload)
    assert report["run_status"] == "ok"
    published = report["sensitivity_panels"][0]["binary_dual_threat_gate"][
        "per_fold"
    ][0]
    assert published["evaluable_players"][0]["player_id"] == "qb-substitute"
    assert published["dual_threat_count"] == 1
