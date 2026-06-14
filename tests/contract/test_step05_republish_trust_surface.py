from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from src.dynasty_genius.eval.backtest_artifact import (
    BacktestResult,
    GateResult,
    StabilityResult,
)
from tests.helpers.backtest_gate_builders import build_mock_fold

POSITIONS = ("QB", "RB", "WR", "TE")
PINNED_RUN_IDS = {
    "QB": "00000000-0000-0000-0000-000000000001",
    "RB": "00000000-0000-0000-0000-000000000002",
    "WR": "00000000-0000-0000-0000-000000000003",
    "TE": "00000000-0000-0000-0000-000000000004",
}
EXPECTED_STATUS = {
    "QB": "PROVISIONAL",
    "RB": "VALIDATED",
    "WR": "VALIDATED",
    "TE": "VALIDATED",
}

ALLOWED_STEP05_PATHS = {
    ("promotion_gate", "model_status"),
    ("promotion_gate", "status_version"),
    ("promotion_gate", "validity_spearman_pass"),
    ("promotion_gate", "validity_r2_pass"),
    ("promotion_gate", "validity_ci_adequacy_pass"),
    ("promotion_gate", "validity_rmse_stability_pass"),
    ("promotion_gate", "validity_null_coverage_pass"),
    ("promotion_gate", "validity_leakage_pass"),
    ("promotion_gate", "validity_cold_start_fold_index"),
    ("promotion_gate", "validity_cold_start_tolerated"),
    ("promotion_gate", "validity_most_recent_fold_index"),
    ("promotion_gate", "validity_most_recent_fold_pass"),
    ("promotion_gate", "null_coverage_min"),
    ("promotion_gate", "status_explanation"),
}


def _four_folds(position: str):
    scenarios = {
        "WR": (
            [0.763, 0.785, 0.816, 0.794],
            [0.602, 0.680, 0.693, 0.666],
            [(0.69, 0.84), (0.71, 0.85), (0.74, 0.88), (0.73, 0.85)],
        ),
        "RB": (
            [0.70, 0.72, 0.74, 0.76],
            [0.30, 0.35, 0.40, 0.45],
            [(0.60, 0.80)] * 4,
        ),
        "TE": (
            [0.436, 0.792, 0.714, 0.706],
            [0.244, 0.457, 0.472, 0.558],
            [(0.24, 0.585), (0.69, 0.85), (0.61, 0.81), (0.57, 0.81)],
        ),
        "QB": (
            [0.678, 0.721, 0.693, 0.755],
            [0.141, 0.298, 0.287, 0.286],
            [(0.42, 0.82), (0.54, 0.83), (0.43, 0.84), (0.61, 0.86)],
        ),
    }
    spears, r2s, cis = scenarios[position]
    train = [
        [2018, 2019],
        [2018, 2019, 2020],
        [2018, 2019, 2020, 2021],
        [2018, 2019, 2020, 2021, 2022],
    ]
    return [
        build_mock_fold(
            idx=i + 1,
            test_year=2020 + i,
            train_years=train[i],
            spear=spears[i],
            r2=r2s[i],
            ci=cis[i],
        )
        for i in range(4)
    ]


def _artifact(position: str) -> BacktestResult:
    folds = _four_folds(position)
    return BacktestResult(
        run_id=UUID(PINNED_RUN_IDS[position]),
        run_date="2026-05-31T12:00:00Z",
        git_sha="abcdef1234567890abcdef1234567890abcdef12",
        model_version="engine_b_v2",
        model_artifact_hash=f"{position.lower()}-hash",
        position=position,  # type: ignore[arg-type]
        ridge_alpha=500.0,
        retrain_mode="refit_per_fold_fixed_alpha",
        folds=folds,
        rmse_stability=StabilityResult(
            rmse_per_fold=[f.rmse for f in folds],
            rmse_mean=3.5,
            rmse_cv=0.0,
            rmse_max_deviation_pct=0.0,
        ),
        market_source="fc_native",
        market_source_label="fantasycalc_native",
        market_snapshot_dates={2020: "2026-05-31"},
        promotion_gate=GateResult(
            g1_rank_correlation_pass=True,
            g2_rmse_stability_pass=True,
            g3_market_superiority_pass="deferred",
            g4_divergence_validity_pass="deferred",
            overall_grade="ACTIVE_B",
            promotion_justification=f"{position} legacy justification must stay fixed",
        ),
    )


def _write_pinned_sources(runs_dir: Path) -> dict[str, dict]:
    before_by_position = {}
    for position in POSITIONS:
        run_dir = runs_dir / PINNED_RUN_IDS[position]
        path = _artifact(position).save(run_dir)
        before_by_position[position] = json.loads(path.read_text(encoding="utf-8"))
    return before_by_position


def _diff_paths(before, after, prefix=()):
    if isinstance(before, dict) and isinstance(after, dict):
        paths = set()
        for key in set(before) | set(after):
            paths |= _diff_paths(before.get(key), after.get(key), (*prefix, key))
        return paths
    if isinstance(before, list) and isinstance(after, list):
        paths = set()
        for index in range(max(len(before), len(after))):
            b_val = before[index] if index < len(before) else None
            a_val = after[index] if index < len(after) else None
            paths |= _diff_paths(b_val, a_val, (*prefix, index))
        return paths
    return set() if before == after else {prefix}


def _is_allowed_step05_path(path: tuple) -> bool:
    if (
        len(path) == 3
        and path[0] == "folds"
        and isinstance(path[1], int)
        and path[2] == "null_coverage"
    ):
        return True
    return path in ALLOWED_STEP05_PATHS


def test_step05_republish_only_adds_provenance_preserving_status_fields(tmp_path):
    from scripts.republish_step05_trust_surface import republish_step05_artifacts

    runs_dir = tmp_path / "runs"
    published_dir = tmp_path / "trust_surface" / "latest"
    before_by_position = _write_pinned_sources(runs_dir)

    report = republish_step05_artifacts(
        runs_dir=runs_dir,
        published_dir=published_dir,
        pinned_run_ids=PINNED_RUN_IDS,
    )

    assert report["statuses"] == EXPECTED_STATUS

    for position in POSITIONS:
        published_path = published_dir / f"backtest_result_{position}.json"
        assert published_path.exists()
        after = json.loads(published_path.read_text(encoding="utf-8"))
        changed_paths = _diff_paths(before_by_position[position], after)
        unexpected = sorted(
            path for path in changed_paths if not _is_allowed_step05_path(path)
        )
        assert unexpected == []

        assert after["run_id"] == before_by_position[position]["run_id"]
        assert after["run_date"] == before_by_position[position]["run_date"]
        assert after["git_sha"] == before_by_position[position]["git_sha"]
        assert after["model_artifact_hash"] == before_by_position[position][
            "model_artifact_hash"
        ]
        assert after["promotion_gate"]["overall_grade"] == before_by_position[
            position
        ]["promotion_gate"]["overall_grade"]
        assert after["promotion_gate"]["promotion_justification"] == before_by_position[
            position
        ]["promotion_gate"]["promotion_justification"]
        assert after["promotion_gate"]["model_status"] == EXPECTED_STATUS[position]
        assert after["promotion_gate"]["null_coverage_min"] == 1.0
        assert all(fold["null_coverage"] == 1.0 for fold in after["folds"])
