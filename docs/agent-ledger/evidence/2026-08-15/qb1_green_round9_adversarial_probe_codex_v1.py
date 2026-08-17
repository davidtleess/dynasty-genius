"""Fresh round-9 falsification probes for the held QB-1 publication gate.

Each test mutates the submitted positive-control report and asserts that a
payload impossible under the shipped producer still publishes ``run_status=ok``
through the public runner. The study and its inputs are never executed.
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
        generated_at="2026-08-15T22:15:00Z",
        repo_root=tmp_path,
        registration=registration,
    )


def _excluded(season: int) -> list[dict[str, Any]]:
    return [
        {
            "test_season": season,
            "reasons": ["join_coverage_low"],
            "decision_supported": False,
        }
    ]


def test_h5_null_delta_with_complete_support_publishes_as_excluded(
    tmp_path: Path,
) -> None:
    """The producer refuses a null delta when both Spearmans are computable.

    The round-9 gate uses delta presence as the evaluability predicate but only
    checks producer coherence in the other direction (delta present with
    missing support). A caller can therefore turn a producible/admitted fold
    into a claimed exclusion merely by deleting its delta.
    """
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    season = registration["h5"]["folds"][0]
    fold = next(row for row in payload["folds"] if row["test_season"] == season)
    metric = fold["metrics_with_CIs"]["c11"]
    assert metric["spearman_left"] is not None
    assert metric["spearman_right"] is not None
    assert metric["common_pool_n"] > 0
    metric["paired_delta"] = None
    comparison = next(row for row in payload["comparisons"] if row["id"] == "c11")
    comparison.update(evaluable_folds=3, excluded_folds=_excluded(season))

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["folds"][3]["metrics_with_CIs"]["c11"]["paired_delta"] is None


def test_h5_starved_fold_with_statistics_counts_as_evaluable(tmp_path: Path) -> None:
    """Registration §7 fixes fold_min_evaluable_n=20. The producer emits no
    point statistics below that floor, but the gate treats any positive pool
    with non-null statistics as admitted."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    season = registration["h5"]["folds"][0]
    fold = next(row for row in payload["folds"] if row["test_season"] == season)
    fold["metrics_with_CIs"]["c11"]["common_pool_n"] = 1

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    metric = report["folds"][3]["metrics_with_CIs"]["c11"]
    assert metric["common_pool_n"] == 1
    assert metric["paired_delta"] is not None


def test_h5_delta_disagrees_with_published_spearmans(tmp_path: Path) -> None:
    """The shipped admission function requires delta == left - right, but the
    report gate counts an arbitrary finite delta as mechanically evaluable."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    season = registration["h5"]["folds"][0]
    fold = next(row for row in payload["folds"] if row["test_season"] == season)
    metric = fold["metrics_with_CIs"]["c11"]
    metric["paired_delta"] = 1.75
    assert metric["paired_delta"] != metric["spearman_left"] - metric["spearman_right"]

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    assert report["folds"][3]["metrics_with_CIs"]["c11"]["paired_delta"] == 1.75


def _boundary_case(*, high_count: int = 0) -> dict[str, Any]:
    # 401 yards / 5 games: base True, minus True, plus False. With no other
    # season the genuine plus flip is True.
    return {
        "player_id": "qb-boundary",
        "binary_dual_threat": True,
        "flips_at_minus_1_ypg": False,
        "flips_at_plus_1_ypg": high_count == 0,
        "window_high_season_count": high_count,
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


def test_f13_impossible_high_season_count_masks_a_flip(tmp_path: Path) -> None:
    """A three-season window with one boundary season cannot contain 999 high
    seasons, but the trusted count masks the mechanically genuine plus flip."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    fold.update(
        n_evaluable=1,
        dual_threat_count=1,
        pocket_count=0,
        boundary_case_count=1,
        boundary_cases=[_boundary_case(high_count=999)],
        flips_at_minus_1_ypg=0,
        flips_at_plus_1_ypg=0,
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    case = report["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0][
        "boundary_cases"
    ][0]
    assert case["window_high_season_count"] == 999


def test_f13_duplicate_player_rows_inflate_aggregate_flips(tmp_path: Path) -> None:
    """The shipped producer emits one case per evaluable player, but duplicate
    player ids can be counted twice and made to reconcile to forged aggregates."""
    registration = contracts._registration()
    payload = contracts._complete_ok_payload(registration)
    case = _boundary_case()
    fold = payload["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0]
    fold.update(
        n_evaluable=2,
        dual_threat_count=2,
        pocket_count=0,
        boundary_case_count=2,
        boundary_cases=[case, dict(case)],
        flips_at_minus_1_ypg=0,
        flips_at_plus_1_ypg=2,
    )

    report = _publish(tmp_path, payload)

    assert report["run_status"] == "ok"
    cases = report["sensitivity_panels"][0]["binary_dual_threat_gate"]["per_fold"][0][
        "boundary_cases"
    ]
    assert [row["player_id"] for row in cases] == ["qb-boundary", "qb-boundary"]
