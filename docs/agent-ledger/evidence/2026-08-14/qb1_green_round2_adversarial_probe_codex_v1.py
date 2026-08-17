"""Round-2 adversarial reproducers for the held QB-1 execution gate.

These tests assert the reviewed defective behavior, so they pass before the
correction and should fail once the named gaps are closed. They use only
synthetic data and never execute the registered study against real inputs.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[4]


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load("qb1_round2_runner_probe", ROOT / "scripts/run_qb1_study.py")
contracts = _load(
    "qb1_round2_contract_helpers",
    ROOT / "tests/contract/test_qb1_green_correction_contracts.py",
)


def test_cli_preflight_failure_escapes_without_terminal_artifact(tmp_path: Path) -> None:
    with (
        patch.object(runner, "_REPO_ROOT", tmp_path),
        patch.object(
            runner,
            "load_registration",
            side_effect=runner.qb.QBValidationFailure(
                "registration_pin_mismatch", "fixture"
            ),
        ),
        pytest.raises(runner.qb.QBValidationFailure),
    ):
        runner.main()

    assert not (tmp_path / runner.OUTPUT_PATH).exists()


def test_h5_coverage_uses_snapshot_rows_not_fold_evaluable_pool() -> None:
    fold = {
        "test_season": 2021,
        "test_rows": [
            {"player_id": f"g-{index}", "target": "target_evaluable"}
            for index in range(100)
        ],
    }
    lane, audit = runner.build_h5_lane(
        fold,
        dp_rows=[{"fp_id": "fp-0", "dp_name": "Name 0", "value_2qb": 1000.0}],
        crosswalk_entries=[
            {"fantasypros_id": "fp-0", "gsis_id": "g-0", "name": "Name 0"}
        ],
        observed_at="2026-05-16T03:28:22Z",
        registration=contracts._registration(),
        label_lookup={(f"g-{index}", 2021): 10.0 for index in range(100)},
    )

    assert audit["coverage"] == 1.0
    assert audit["excluded"] is False
    assert lane["n_predicted"] == 1
    assert lane["n_predicted"] / 100 < 0.70


def test_ok_composition_omits_registered_schema_and_skips_f25(tmp_path: Path) -> None:
    calls = 0

    def frozen_gate(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("F25 gate reached")

    with patch.object(runner.qb, "validate_frozen_hashes", side_effect=frozen_gate):
        report = runner.compose_study(
            registration=contracts._registration(),
            pool=contracts._hermetic_pool(tmp_path),
            repo_root=tmp_path,
            **contracts._h5_inputs(tmp_path),
        )

    fold = report["folds"][0]
    required_attrition = {
        "no_target_season",
        "rookie_no_priors",
        "cohort_ineligible_prior",
        "cohort_ineligible_unobserved",
        "manifest_missing",
    }
    assert report["run_status"] == "ok"
    assert calls == 0
    assert "disclosures" not in report
    assert "metrics_with_CIs" not in fold
    assert required_attrition - set(fold["attrition"])


def test_f13_panel_is_a_static_description_not_a_comparison() -> None:
    panel = runner.build_sensitivity_panels(
        [],
        {"contrasts": []},
        {
            "min_qualifying_games": 4,
            "pooled_deltas": {},
            "decision_supported": False,
        },
        contracts._registration(),
    )[0]

    assert panel["binary_dual_threat_gate"] is False
    assert panel["continuous_rushing_moderator"] is True
    assert not any("delta" in key or "metric" in key for key in panel)

