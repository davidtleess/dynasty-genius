"""QB-1 execution RED: D1 admission, D4/H5, D5, and the terminal runner.

These rows freeze mechanics only.  They do not compute or assert a QB-1 result;
QB rushing remains a registered hypothesis UNDER TEST until execution and
David's ruling.  Every dependency is local or injected, and no provider call is
allowed from this suite.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

PIN = "37065566a9b372e329454cc51edbcf3de724fd1e5cc57a2f15cc547b1ae54c9d"
DATASETS = (
    "weekly",
    "season_summary",
    "players",
    "rosters",
    "ff_playerids",
    "draft_picks",
    "pbp",
)


def _qb():
    return importlib.import_module("src.dynasty_genius.eval.qb_validation")


def _reason(exc_info: pytest.ExceptionInfo[BaseException]) -> str:
    reason = getattr(exc_info.value, "reason", None)
    assert isinstance(reason, str) and reason
    return reason


def _registration() -> dict[str, Any]:
    path = Path("docs/validation/2026-07-21-qb-1-study-registration.json")
    return json.loads(path.read_text())


def _h5(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "lane": "h5",
        "folds": 4,
        "pooled_delta": 0.01,
        "ci95": [-0.02, 0.04],
        "one_sided_lower_95": -0.04,
        "p_ni": 0.04,
        "adjusted_p_ni": 0.08,
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "payload,status,flag",
    [
        (
            _h5(folds=2, pooled_delta=0.30, ci95=[0.20, 0.40]),
            "unsupported_power",
            None,
        ),
        (_h5(pooled_delta=-0.08, ci95=[-0.12, -0.01]), "model_superior", None),
        (_h5(pooled_delta=0.08, ci95=[0.01, 0.12]), "market_superior", None),
        (_h5(), "market_noninferior", None),
        (
            _h5(one_sided_lower_95=-0.04, adjusted_p_ni=0.11),
            "inconclusive",
            "ci_p_disagreement",
        ),
        (
            _h5(one_sided_lower_95=-0.06, adjusted_p_ni=0.08),
            "inconclusive",
            "ci_p_disagreement",
        ),
        (
            _h5(one_sided_lower_95=-0.06, adjusted_p_ni=0.11),
            "inconclusive",
            None,
        ),
    ],
)
def test_h5_status_is_total_ordered_and_retains_ni(
    payload: dict[str, Any], status: str, flag: str | None
) -> None:
    result = _qb().evaluate_power_and_status(payload)
    assert result["support_status"] == status
    assert result["decision_supported"] is False
    assert result["p_ni"] == payload["p_ni"]
    assert result["ni_met"] is (
        payload["folds"] >= 3
        and payload["one_sided_lower_95"] > -0.05
        and payload["adjusted_p_ni"] <= 0.10
    )
    assert (flag in result.get("flags", [])) is (flag is not None)


def test_h5_registered_boundaries_are_strict_and_not_payload_knobs() -> None:
    qb = _qb()
    assert (
        qb.evaluate_power_and_status(_h5(one_sided_lower_95=-0.05, adjusted_p_ni=0.10))[
            "support_status"
        ]
        == "inconclusive"
    )
    assert (
        qb.evaluate_power_and_status(
            _h5(one_sided_lower_95=-0.049, adjusted_p_ni=0.10)
        )["support_status"]
        == "market_noninferior"
    )
    for knob in ("fold_floor", "margin", "fdr_q"):
        with pytest.raises(qb.QBValidationFailure) as exc_info:
            qb.evaluate_power_and_status(_h5(**{knob: 0}))
        assert _reason(exc_info) == "registration_override_refused"


def test_f16_duplicate_collapse_and_conflict_rejection_are_distinct() -> None:
    result = _qb().validate_identity_duplicates(
        [
            {"fantasypros_id": "10", "gsis_id": "g-1"},
            {"fantasypros_id": "10", "gsis_id": "g-1"},
            {"fantasypros_id": "20", "gsis_id": "g-2"},
            {"fantasypros_id": "20", "gsis_id": "g-3"},
        ],
        source_key="fantasypros_id",
        target_key="gsis_id",
    )
    assert result["mapping"] == {"10": "g-1"}
    assert result["duplicate_count"] == 1
    assert result["conflict_count"] == 1
    assert result["triage"] == [
        {"source_id": "20", "target_ids": ["g-2", "g-3"], "reason": "identity_conflict"}
    ]


def test_h5_bridge_joins_only_fp_id_never_a_name_fallback() -> None:
    result = _qb().build_h5_static_join(
        dp_rows=[
            {"fp_id": "10", "name": "Joined Name", "value": 100},
            {"fp_id": None, "name": "Same Name", "value": 90},
        ],
        crosswalk_rows=[
            {"fantasypros_id": "10", "gsis_id": "g-1", "name": "Joined Name"},
            {"fantasypros_id": "99", "gsis_id": "g-2", "name": "Same Name"},
        ],
        observed_at="2026-05-16T03:28:22Z",
        registration=_registration(),
    )
    assert [row["gsis_id"] for row in result["joined_rows"]] == ["g-1"]
    assert result["joined_rows"][0]["observed_at"] == "2026-05-16T03:28:22Z"
    assert result["joined_rows"][0]["assumed_effective"] is True
    assert result["unresolved_count"] == 1


@pytest.mark.parametrize("joined,evaluable,passes", [(69, 100, False), (70, 100, True)])
def test_f18_join_coverage_boundary_is_exact(
    joined: int, evaluable: int, passes: bool
) -> None:
    qb = _qb()
    if passes:
        result = qb.validate_join_coverage(
            joined, evaluable, registration=_registration()
        )
        assert result["coverage"] == pytest.approx(0.70)
        assert result["admitted"] is True
    else:
        with pytest.raises(qb.QBValidationFailure) as exc_info:
            qb.validate_join_coverage(joined, evaluable, registration=_registration())
        assert _reason(exc_info) == "join_coverage_low"


@pytest.mark.parametrize(
    "pairs,passes",
    [
        (
            [{"dp_name": "Match", "crosswalk_name": "Match"} for _ in range(49)]
            + [{"dp_name": "One", "crosswalk_name": "Mismatch"}],
            True,
        ),
        (
            [{"dp_name": "Match", "crosswalk_name": "Match"} for _ in range(48)]
            + [
                {"dp_name": "One", "crosswalk_name": "Mismatch"},
                {"dp_name": None, "crosswalk_name": "Missing counts"},
            ],
            False,
        ),
    ],
)
def test_f32_reconciliation_strictly_greater_than_two_percent_fails(
    pairs: list[dict[str, Any]], passes: bool
) -> None:
    qb = _qb()
    if passes:
        result = qb.reconcile_identity_names(pairs, registration=_registration())
        assert result["mismatch_count"] == 1
        assert result["mismatch_rate"] == pytest.approx(0.02)
        assert result["admitted"] is True
    else:
        with pytest.raises(qb.QBValidationFailure) as exc_info:
            qb.reconcile_identity_names(pairs, registration=_registration())
        assert _reason(exc_info) == "join_reconciliation_failed"


def test_real_newline_terminated_registration_hashes_as_canonical_object() -> None:
    path = Path("docs/validation/2026-07-21-qb-1-study-registration.json")
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    registration = json.loads(raw)
    assert _qb().build_registration(registration)["sha256"] == PIN
    assert hashlib.sha256(raw).hexdigest() != PIN
    assert _qb().require_registration_hash(registration, PIN) == PIN


def test_registration_missing_and_canonical_mutation_are_named() -> None:
    qb = _qb()
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.require_registration_hash(None, PIN)
    assert _reason(exc_info) == "preregistration_missing"

    changed = _registration()
    changed["inference"]["fdr_q"] = 0.11
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.reject_registration_drift(changed, PIN)
    assert _reason(exc_info) == "registration_drift"


def _raw_receipt(root: Path, *, repo_root: Path) -> dict[str, Any]:
    datasets: dict[str, Any] = {}
    for dataset in DATASETS:
        path = root / dataset / f"{dataset}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"{dataset}-immutable-snapshot".encode())
        datasets[dataset] = {
            "snapshots": [
                {
                    "file": str(path.relative_to(repo_root)),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "rows": 1,
                    "columns": 1,
                    "bytes": path.stat().st_size,
                }
            ]
        }
    receipt = {
        "operation": "qb1_d1_seven_dataset_fetch",
        "authorization": {"given_by": "David", "word_verbatim": "authorized"},
        "registration_pin": PIN,
        "nflreadpy_version": "fixture",
        "started_at": "2026-08-14T15:52:11+00:00",
        "finished_at": "2026-08-14T15:54:00+00:00",
        "datasets": datasets,
        "decision_supported": False,
    }
    (root / "fetch_manifest.json").write_text(json.dumps(receipt))
    return receipt


def test_d1_completion_receipt_admits_all_seven_with_verified_metadata(
    tmp_path,
) -> None:
    raw = tmp_path / "app/data/backtest/qb_validation/raw"
    _raw_receipt(raw, repo_root=tmp_path)
    loaded: list[Path] = []

    def frame_loader(path: Path) -> pd.DataFrame:
        loaded.append(path)
        return pd.DataFrame({"row": [1]})

    sources = _qb().admit_fetch_manifest(
        raw, repo_root=tmp_path, frame_loader=frame_loader
    )
    assert tuple(sources) == DATASETS
    assert len(loaded) == 7
    for dataset, state in sources.items():
        assert state["status"] == "ok"
        assert state["metadata"]["raw_snapshot_path"]
        assert state["metadata"]["source_timestamp"] == "2026-08-14T15:54:00+00:00"
        assert state["metadata"]["parser_version"]
        assert state["metadata"]["completeness"] == "complete"
        assert state["metadata"]["sha256"]


def test_d1_hash_drift_refuses_before_any_frame_is_loaded(tmp_path) -> None:
    raw = tmp_path / "app/data/backtest/qb_validation/raw"
    receipt = _raw_receipt(raw, repo_root=tmp_path)
    first = tmp_path / receipt["datasets"]["weekly"]["snapshots"][0]["file"]
    first.write_bytes(b"tampered")
    calls = 0

    def frame_loader(_path: Path) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        return pd.DataFrame({"row": [1]})

    with pytest.raises(_qb().QBValidationFailure) as exc_info:
        _qb().admit_fetch_manifest(raw, repo_root=tmp_path, frame_loader=frame_loader)
    assert _reason(exc_info) == "source_snapshot_drift"
    assert calls == 0


def test_fetch_rerun_invalidates_old_completion_receipt_first(tmp_path) -> None:
    runner = importlib.import_module("scripts.run_qb1_d1_fetch")
    manifest = tmp_path / "fetch_manifest.json"
    manifest.write_text("stale-success")
    runner.invalidate_completion_manifest(tmp_path)
    assert not manifest.exists()


def test_fetch_completion_write_uses_replace_as_atomic_commit(tmp_path) -> None:
    runner = importlib.import_module("scripts.run_qb1_d1_fetch")
    manifest = tmp_path / "fetch_manifest.json"
    seen: dict[str, Path] = {}

    def replace(source: Path, destination: Path) -> None:
        seen["source"] = source
        assert source.parent == destination.parent
        assert source != destination
        json.loads(source.read_text())
        source.replace(destination)

    runner.write_completion_manifest_atomic(
        manifest, {"decision_supported": False}, replace=replace
    )
    assert seen["source"] != manifest
    assert json.loads(manifest.read_text()) == {"decision_supported": False}


def test_d5_failure_report_has_no_metric_bearing_blocks() -> None:
    report = _qb().assemble_terminal_report(
        generated_at="2026-08-14T16:00:00Z",
        registration_hash=PIN,
        run_status="failed",
        failure_reason="source_unavailable",
    )
    assert report == {
        "schema_version": "qb_validation_report.v1",
        "generated_at": "2026-08-14T16:00:00Z",
        "registration_hash": PIN,
        "run_status": "failed",
        "failure_reason": "source_unavailable",
        "decision_supported": False,
    }
    assert not (
        {"inputs", "folds", "comparisons", "case_panel", "sensitivity_panels"}
        & report.keys()
    )


def test_d5_success_report_requires_complete_schema_and_recursive_honesty() -> None:
    qb = _qb()
    cases = [
        {
            "id": case_id,
            "scope_note": "second-season"
            if case_id in {"daniels_2025", "nix_2025"}
            else "registered case",
            "decision_supported": False,
        }
        for case_id in (
            "daniels_2025",
            "nix_2025",
            "mayfield_2025",
            "richardson_2025",
            "maye_2025",
            "allen_2019_twin",
            "richardson_2024_twin",
        )
    ]
    panels = [
        {
            "id": "archetype_threshold",
            "binary_dual_threat_gate": True,
            "continuous_rushing_moderator": True,
            "boundary_cases_yards_per_game": [-1, 1],
            "decision_supported": False,
        },
        {
            "id": "qualifying_games",
            "unfiltered_primary": {"min_qualifying_games": None},
            "min_four_games": {"min_qualifying_games": 4},
            "decision_supported": False,
        },
        {
            "id": "h5_margin",
            "margins": [0.025, 0.05, 0.10],
            "decision_supported": False,
        },
    ]
    # AMENDED under the Codex round-3 R3-G1 ruling (review `0b8dca62…`,
    # 2026-08-14): "Amend the frozen success fixtures to carry the complete
    # registered shape" — disclosures are REQUIRED on every ok report; the
    # prior fixture predated that requirement and under-specified the shape.
    report = qb.assemble_terminal_report(
        generated_at="2026-08-14T16:00:00Z",
        registration_hash=PIN,
        run_status="ok",
        disclosures=[
            {**row, "decision_supported": False}
            for row in _registration()["disclosures"]
        ],
        inputs={
            "snapshot_ids": ["s1"],
            "settings_hash": "a" * 64,
            "matrix_version": "qb_validation_matrix.v1",
        },
        folds=[
            {
                "test_season": 2025,
                "n_evaluable": 20,
                "attrition": {},
                "metrics_with_CIs": {},
                "flags": [],
                "decision_supported": False,
            }
        ],
        comparisons=[
            {
                "id": "c01",
                "registered_direction": "left_gt_right",
                "pooled_delta": -0.01,
                "ci95": [-0.1, 0.1],
                "p_perm": 0.5,
                "support_status": "not_separable",
                "decision_supported": False,
            }
        ],
        case_panel=cases,
        sensitivity_panels=panels,
    )
    assert report["run_status"] == "ok"
    assert "failure_reason" not in report
    assert report["comparisons"][0]["pooled_delta"] == -0.01
    qb.validate_report_output(report)


def test_terminal_writer_failure_leaves_no_partial_final_artifact(tmp_path) -> None:
    qb = _qb()
    destination = tmp_path / "app/data/backtest/qb_validation/qb_validation_report.json"

    def interrupt(_source: Path, _destination: Path) -> None:
        raise OSError("simulated interruption before atomic replace")

    with pytest.raises(OSError, match="simulated interruption"):
        qb.write_terminal_report_atomic(
            {"decision_supported": False},
            destination,
            repo_root=tmp_path,
            replace=interrupt,
        )
    assert not destination.exists()


def test_runner_converts_named_failure_to_atomic_terminal_artifact(tmp_path) -> None:
    qb = _qb()
    destination = tmp_path / "app/data/backtest/qb_validation/qb_validation_report.json"

    def execute() -> dict[str, Any]:
        raise qb.QBValidationFailure("source_unavailable", "fixture")

    result = qb.run_qb1_study(
        execute=execute,
        output_path=destination,
        registration_hash=PIN,
        generated_at="2026-08-14T16:00:00Z",
        repo_root=tmp_path,
    )
    assert result["run_status"] == "failed"
    assert result["failure_reason"] == "source_unavailable"
    assert json.loads(destination.read_text()) == result
    assert "comparisons" not in result


def test_f25_frozen_hashes_refuse_one_byte_drift(tmp_path) -> None:
    qb = _qb()
    artifact = tmp_path / "qb_v2.bin"
    artifact.write_bytes(b"frozen")
    expected = {artifact: hashlib.sha256(b"frozen").hexdigest()}
    qb.validate_frozen_hashes(expected)
    artifact.write_bytes(b"drifted")
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.validate_frozen_hashes(expected)
    assert _reason(exc_info) == "frozen_boundary_drift"


def test_f31_artifact_tracking_refuses_output_outside_frozen_root(tmp_path) -> None:
    qb = _qb()
    inside = tmp_path / "app/data/backtest/qb_validation/report.json"
    outside = tmp_path / "docs/validation/report.json"
    inside.parent.mkdir(parents=True)
    outside.parent.mkdir(parents=True)
    inside.write_text("{}")
    outside.write_text("{}")
    qb.validate_artifact_tracking([inside], repo_root=tmp_path)
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.validate_artifact_tracking([outside], repo_root=tmp_path)
    assert _reason(exc_info) == "output_path_violation"


def test_f31_real_output_root_is_gitignored() -> None:
    lines = {
        line.strip()
        for line in Path(".gitignore").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "app/data/backtest/qb_validation/" in lines


def test_f33_consumer_boundary_detects_import_and_raw_read(tmp_path) -> None:
    qb = _qb()
    leak = tmp_path / "src/dynasty_genius/api/leak.py"
    leak.parent.mkdir(parents=True)
    leak.write_text(
        "from src.dynasty_genius.eval.qb_validation import run_qb1_study\n"
        "P = 'app/data/backtest/qb_validation/report.json'\n"
    )
    with pytest.raises(qb.QBValidationFailure) as exc_info:
        qb.enforce_consumer_boundary(repo_root=tmp_path)
    assert _reason(exc_info) == "consumer_boundary_violation"


def test_d5_panel_seams_are_behavioral_not_presence_only() -> None:
    qb = _qb()
    case_ids = {
        "daniels_2025",
        "nix_2025",
        "mayfield_2025",
        "richardson_2025",
        "maye_2025",
        "allen_2019_twin",
        "richardson_2024_twin",
    }
    case_panel = [
        {
            "id": case_id,
            "scope_note": "second-season"
            if case_id in {"daniels_2025", "nix_2025"}
            else "registered case",
            "decision_supported": False,
        }
        for case_id in case_ids
    ]
    assert {row["id"] for row in qb.require_case_panel(case_panel)} == case_ids

    threshold_panel = {
        "binary_dual_threat_gate": True,
        "continuous_rushing_moderator": True,
        "boundary_cases_yards_per_game": [-1, 1],
        "decision_supported": False,
    }
    assert qb.require_threshold_sensitivity(threshold_panel) == threshold_panel
    with pytest.raises(qb.QBValidationFailure):
        qb.require_threshold_sensitivity({})

    sensitivity = {
        "unfiltered_primary": {"min_qualifying_games": None},
        "min_four_games": {"min_qualifying_games": 4},
        "h5_margin_sensitivity": {"margins": [0.025, 0.05, 0.10]},
        "decision_supported": False,
    }
    assert qb.validate_sensitivity_panel(sensitivity) == sensitivity
    with pytest.raises(qb.QBValidationFailure):
        qb.require_case_panel(case_panel[:-1])
    with pytest.raises(qb.QBValidationFailure):
        qb.validate_sensitivity_panel(
            {
                key: value
                for key, value in sensitivity.items()
                if key != "unfiltered_primary"
            }
        )


def test_h5_registered_snapshot_bridge_is_sha_pinned_and_fail_closed() -> None:
    root = Path("app/data/backtest/qb_validation/raw/dp_values")
    result = _qb().load_h5_snapshots(root, registration=_registration())
    assert [row["season"] for row in result] == [2021, 2022, 2023, 2024]
    assert [row["sha256"] for row in result] == [
        snapshot["sha256"] for snapshot in _registration()["h5"]["snapshots"]
    ]
    assert all(row["path"].parent == root for row in result)
