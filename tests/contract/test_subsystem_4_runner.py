"""Subsystem 4 Backtest-A runner + artifact contract tests (§5.8, §5.9)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.dynasty_genius.eval import backtest_mock_draft as bmd
from src.dynasty_genius.identity.prospect_nfl_bridge import CollegeProspectBridge

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_BACKTEST_A_CLI = REPO_ROOT / "scripts" / "run_backtest_a.py"

UUID_A = "cpr_12000000-0000-4000-8000-000000000001"
UUID_B = "cpr_12000000-0000-4000-8000-000000000002"
UUID_C = "cpr_12000000-0000-4000-8000-000000000003"

FALSIFICATION_MATRIX = {
    "valid_nominal": {
        "owner": "Task 12a",
        "coverage": "build_backtest_a_result clean path + artifact schema tests",
        "out_of_scope": None,
    },
    "boundary": {
        "owner": "Task 12a",
        "coverage": "empty per-(bucket, position) groups route through B-gate rollup",
        "out_of_scope": None,
    },
    "missing": {
        "owner": "Task 12b",
        "coverage": "missing snapshots dir and missing identity bridge fail loud",
        "out_of_scope": None,
    },
    "null_none": {
        "owner": "Task 12a",
        "coverage": "metrics is null whenever any hard block fires",
        "out_of_scope": None,
    },
    "wrong_type": {
        "owner": "Task 12b",
        "coverage": None,
        "out_of_scope": (
            "top-level Python argument type misuse fails loud; Task 12 caller owns "
            "typed Path/int arguments before entering runner internals"
        ),
    },
    "malformed_shape": {
        "owner": "Task 12b",
        "coverage": "malformed/partial snapshot JSON fails as ingestion/schema error",
        "out_of_scope": None,
    },
    "duplicate_conflict": {
        "owner": "Task 12b",
        "coverage": "duplicate run_id/pre-existing artifact is refused",
        "out_of_scope": None,
    },
    "empty_collection": {
        "owner": "Task 12b",
        "coverage": "empty snapshots dir fails loud; empty B-gate bucket excluded by design",
        "out_of_scope": None,
    },
    "cross_component_shape": {
        "owner": "Task 12a",
        "coverage": (
            "runner builds per-(round_bucket, position) MAE/coverage instead of "
            "feeding compute_metrics round-level count breakdown into evaluate_b_gate"
        ),
        "out_of_scope": None,
    },
    "numeric_edge_cases": {
        "owner": "Task 12a",
        "coverage": None,
        "out_of_scope": (
            "non-finite and out-of-range metric values are producer-semantic "
            "validation; compute_metrics/build_b_gate_per_bucket_position_breakdown "
            "own finite numeric production by construction"
        ),
    },
    "synthetic_override": {
        "owner": "Task 12a/12b",
        "coverage": "override date sets synthetic data_mode and paired CLI flags are enforced",
        "out_of_scope": None,
    },
}


def _round_for_pick(pick_no: int | None) -> int | None:
    if pick_no is None:
        return None
    if pick_no <= 32:
        return 1
    if pick_no <= 64:
        return 2
    if pick_no <= 105:
        return 3
    return min(7, ((pick_no - 1) // 32) + 1)


def _consensus(
    prospect_uuid: str,
    projected_pick_median: float | None,
    *,
    abstention_tier: str = "exact_pick",
) -> bmd.ProspectConsensus:
    return bmd.ProspectConsensus(
        prospect_uuid=prospect_uuid,
        projected_pick_median=projected_pick_median,
        projected_pick_iqr=4.0 if projected_pick_median is not None else None,
        projected_pick_min=(
            int(projected_pick_median) if projected_pick_median is not None else None
        ),
        projected_pick_max=(
            int(projected_pick_median) if projected_pick_median is not None else None
        ),
        n_sources=5 if abstention_tier != "abstain" else 2,
        n_unique_analysts=5 if abstention_tier != "abstain" else 2,
        snapshot_ids_used=[f"snapshot_{prospect_uuid[-4:]}"],
        staleness_days=2.0,
        abstention_tier=abstention_tier,
        abstention_reason=(
            None if abstention_tier != "abstain" else "abstain: insufficient sources"
        ),
    )


def _outcome(
    prospect_uuid: str,
    *,
    pick_no: int | None,
    position: str = "WR",
    udfa: bool = False,
) -> bmd.RealizedOutcome:
    return bmd.RealizedOutcome(
        prospect_uuid=prospect_uuid,
        gsis_id=None if udfa else f"00-{prospect_uuid[-4:]}",
        pfr_id=None,
        draft_year=2025,
        draft_pick_no=pick_no,
        draft_round=_round_for_pick(pick_no),
        nfl_team=None if udfa else "TEN",
        udfa=udfa,
        unbridged_prospect=False,
        bridge_stale_warning=False,
        warnings=[],
        evidence_full_name=f"Prospect {prospect_uuid[-4:]}",
        evidence_position=position,
        evidence_college="Test U",
    )


def _joined_rows() -> list[tuple[bmd.ProspectConsensus, bmd.RealizedOutcome]]:
    return [
        (_consensus(UUID_A, 5.0), _outcome(UUID_A, pick_no=1, position="QB")),
        (_consensus(UUID_B, 48.0), _outcome(UUID_B, pick_no=40, position="WR")),
        (
            _consensus(UUID_C, None, abstention_tier="abstain"),
            _outcome(UUID_C, pick_no=50, position="WR"),
        ),
    ]


def _bridge_for_joined(
    joined_rows: list[tuple[bmd.ProspectConsensus, bmd.RealizedOutcome]],
) -> CollegeProspectBridge:
    return CollegeProspectBridge(
        metadata={"draft_year": 2025, "schema_version": "prospect_nfl_bridge_v1.0.0"},
        entries=[],
    )


def _write_minimal_runner_inputs(
    tmp_path: Path,
    *,
    nested_snapshot: bool = False,
) -> tuple[Path, Path]:
    snapshots_dir = tmp_path / "snapshots"
    identity_dir = tmp_path / "identity"
    snapshot_parent = snapshots_dir / "nested" if nested_snapshot else snapshots_dir
    snapshot_parent.mkdir(parents=True)
    identity_dir.mkdir()
    (snapshot_parent / "snapshot.json").write_text("{}", encoding="utf-8")
    (identity_dir / "prospect_nfl_bridge.json").write_text(
        json.dumps({"metadata": {"draft_year": 2025}, "entries": []}),
        encoding="utf-8",
    )
    return snapshots_dir, identity_dir


def _join_diagnostics(*, reasons=None, review_queue=None) -> bmd.JoinDiagnostics:
    return bmd.JoinDiagnostics.model_validate(
        {
            "hard_block_reasons": list(reasons or []),
            "review_queue_payload": list(review_queue or []),
            "duplicate_gsis_ids_detected": [],
            "wrong_year_truth_collisions": [],
            "evidence_incomplete_uuids": [],
        }
    )


def _snapshots_coverage() -> dict:
    return {
        "snapshot_ids_used": ["snapshot_a"],
        "metadata_tuple_keys_used": ["source|analyst|2025-04-01|v1"],
        "total_snapshots_found": 1,
        "snapshots_used": 1,
        "total_picks": 3,
        "draft_date_used": "2025-04-24",
        "draft_date_source": "nflreadr.draft_picks",
        "warnings": [],
    }


def _bridge_coverage(**overrides) -> dict:
    coverage = {
        "consensus_unbridged_count": 0,
        "confirmed_class_unbridged_count": 0,
        "orphan_bridges_detected": [],
    }
    coverage.update(overrides)
    return coverage


def _build_result(**overrides):
    kwargs = {
        "run_id": "task12_contract_run",
        "draft_year": 2025,
        "data_mode": "real",
        "draft_date": "2025-04-24",
        "draft_date_source": "nflreadr.draft_picks",
        "snapshots_coverage": _snapshots_coverage(),
        "bridge_coverage": _bridge_coverage(),
        "joined_outcomes": _joined_rows(),
        "join_diagnostics": _join_diagnostics(),
        "bridge": _bridge_for_joined(_joined_rows()),
        "n_prospects_total_in_class": 3,
    }
    kwargs.update(overrides)
    return bmd.build_backtest_a_result(**kwargs)


def _payload(result) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return result


def test_task12_falsification_matrix_seeded_with_explicit_owners():
    expected_rows = {
        "valid_nominal",
        "boundary",
        "missing",
        "null_none",
        "wrong_type",
        "malformed_shape",
        "duplicate_conflict",
        "empty_collection",
        "cross_component_shape",
        "numeric_edge_cases",
        "synthetic_override",
    }

    assert set(FALSIFICATION_MATRIX) == expected_rows
    for row, entry in FALSIFICATION_MATRIX.items():
        assert entry["owner"], row
        assert entry["coverage"] or entry["out_of_scope"], row


def test_backtest_a_result_schema_contains_required_top_level_fields_and_forbids_extra():
    BacktestAResult = getattr(bmd, "BacktestAResult")
    payload = _payload(_build_result())

    assert set(payload) == {
        "metadata",
        "coverage",
        "metric_universe",
        "metrics",
        "abstention_summary",
        "backtest_b_gate_status",
        "warnings",
        "cohort_selection_bias_caveat",
        "acceptance_criteria_failed",
    }
    assert payload["metric_universe"] == "tracked_confirmed_prospect_universe"

    bad = dict(payload)
    bad["unexpected"] = "reject"
    with pytest.raises(ValidationError):
        BacktestAResult.model_validate(bad)


def test_artifact_metrics_null_on_unbridged_hard_block():
    result = _build_result(
        bridge_coverage=_bridge_coverage(consensus_unbridged_count=1),
    )
    payload = _payload(result)

    assert payload["metrics"] is None
    assert payload["acceptance_criteria_failed"] == ["consensus_unbridged"]


def test_artifact_metadata_includes_team_code_normalization_version():
    payload = _payload(_build_result())

    assert payload["metadata"]["team_code_normalization_version"] == (
        bmd.TEAM_CODE_NORMALIZATION_VERSION
    )


def test_artifact_metadata_includes_round_bucket_rounding_policy():
    payload = _payload(_build_result())

    assert payload["metadata"]["round_bucket_rounding_policy"] == "round_half_up"
    assert payload["metadata"]["round_bucket_rounding_policy"] == (
        bmd.ROUND_BUCKET_ROUNDING_POLICY
    )


def test_artifact_emits_selection_bias_caveat_with_constitution_citation():
    payload = _payload(_build_result())

    caveat = payload["cohort_selection_bias_caveat"]
    assert "Truth over convenience" in caveat
    assert "constitution" in caveat.lower()


def test_artifact_acceptance_criteria_failed_aggregated_from_canonical_tokens():
    result = _build_result(
        join_diagnostics=_join_diagnostics(
            reasons=["wrong_year_truth_collision", "evidence_snapshot_missing"]
        ),
        bridge_coverage=_bridge_coverage(
            consensus_unbridged_count=1,
            orphan_bridges_detected=[UUID_A],
        ),
    )
    payload = _payload(result)

    assert payload["acceptance_criteria_failed"] == [
        "wrong_year_truth_collision",
        "evidence_snapshot_missing",
        "consensus_unbridged",
        "orphan_bridges_detected",
    ]
    assert payload["metrics"] is None


def test_review_queue_written_from_join_diagnostics(tmp_path: Path):
    diagnostics = _join_diagnostics(
        review_queue=[
            {
                "prospect_uuid": UUID_A,
                "reason": "wrong_year_truth_collision",
                "gsis_id": "00-0001",
            }
        ]
    )
    queue_path = tmp_path / "review_queue.json"

    bmd.write_review_queue_from_join_diagnostics(diagnostics, queue_path)

    assert json.loads(queue_path.read_text(encoding="utf-8")) == (
        diagnostics.review_queue_payload
    )


def test_runner_builds_b_gate_breakdown_per_bucket_position_not_metric_round_counts():
    breakdown = bmd.build_b_gate_per_bucket_position_breakdown(_joined_rows())

    assert breakdown == {
        "R1-early": {"QB": {"mae": 4.0, "coverage": 1.0}},
        "R2": {"WR": {"mae": 8.0, "coverage": 0.5}},
    }
    assert all("n_realized" not in positions for positions in breakdown.values())
    assert all("n_scored" not in positions for positions in breakdown.values())


def test_runner_feeds_evaluate_b_gate_per_bucket_position_breakdown(monkeypatch):
    captured: dict = {}

    def fake_evaluate_b_gate(metrics, per_bucket_breakdown, *, data_mode, draft_date_source):
        captured["metrics"] = metrics
        captured["per_bucket_breakdown"] = per_bucket_breakdown
        captured["data_mode"] = data_mode
        captured["draft_date_source"] = draft_date_source
        return {
            "overall_status": "partial",
            "per_bucket_results": {},
            "gate_version": bmd.GATE_VERSION,
            "thresholds": {},
        }

    monkeypatch.setattr(bmd, "evaluate_b_gate", fake_evaluate_b_gate)

    _build_result()

    assert captured["data_mode"] == "real"
    assert captured["draft_date_source"] == "nflreadr.draft_picks"
    assert captured["per_bucket_breakdown"] == {
        "R1-early": {"QB": {"mae": 4.0, "coverage": 1.0}},
        "R2": {"WR": {"mae": 8.0, "coverage": 0.5}},
    }
    assert captured["metrics"]["metric_version"] == bmd.METRIC_VERSION


def test_runner_sets_data_mode_synthetic_when_override_date_used():
    payload = _payload(
        _build_result(
            data_mode="synthetic",
            draft_date="2025-04-24",
            draft_date_source="override:manual_fixture_date",
        )
    )

    assert payload["metadata"]["data_mode"] == "synthetic"
    assert payload["metadata"]["draft_date_source"] == "override:manual_fixture_date"
    assert (
        payload["backtest_b_gate_status"]["overall_status"]
        == "always_abstain_synthetic_data"
    )


def test_write_backtest_a_artifact_creates_run_dir_and_writes_atomic_json(
    tmp_path: Path,
):
    result = _build_result(run_id="atomic_run")
    artifact_path = bmd.write_backtest_a_artifact(result, output_root=tmp_path)

    assert artifact_path == tmp_path / "atomic_run" / "backtest_a_result.json"
    assert artifact_path.exists()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["run_id"] == "atomic_run"


def test_write_backtest_a_artifact_refuses_duplicate_run_id(tmp_path: Path):
    result = _build_result(run_id="duplicate_run")
    bmd.write_backtest_a_artifact(result, output_root=tmp_path)

    with pytest.raises(FileExistsError):
        bmd.write_backtest_a_artifact(result, output_root=tmp_path)


def test_runner_rejects_missing_or_empty_snapshots_dir(tmp_path: Path):
    BacktestAInputError = getattr(bmd, "BacktestAInputError")
    empty_snapshots = tmp_path / "empty_snapshots"
    empty_snapshots.mkdir()

    with pytest.raises(BacktestAInputError, match="snapshots"):
        bmd.run_backtest_a(
            snapshots_dir=empty_snapshots,
            identity_dir=tmp_path / "identity",
            draft_year=2025,
            run_id="empty_snapshots",
            output_root=tmp_path / "runs",
            override_draft_date="2025-04-24",
            override_reason="manual_fixture_date",
        )


def test_runner_rejects_missing_identity_bridge_artifact(tmp_path: Path):
    BacktestAInputError = getattr(bmd, "BacktestAInputError")
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()
    (snapshots_dir / "malformed.json").write_text("{}", encoding="utf-8")

    with pytest.raises(BacktestAInputError, match="bridge"):
        bmd.run_backtest_a(
            snapshots_dir=snapshots_dir,
            identity_dir=tmp_path / "missing_identity",
            draft_year=2025,
            run_id="missing_bridge",
            output_root=tmp_path / "runs",
            override_draft_date="2025-04-24",
            override_reason="manual_fixture_date",
        )


def test_runner_rejects_malformed_partial_snapshot_json(tmp_path: Path):
    BacktestAInputError = getattr(bmd, "BacktestAInputError")
    snapshots_dir = tmp_path / "snapshots"
    identity_dir = tmp_path / "identity"
    snapshots_dir.mkdir()
    identity_dir.mkdir()
    (snapshots_dir / "bad.json").write_text("{not-json", encoding="utf-8")
    (identity_dir / "prospect_nfl_bridge.json").write_text(
        json.dumps({"metadata": {"draft_year": 2025}, "entries": []}),
        encoding="utf-8",
    )

    with pytest.raises(BacktestAInputError, match="snapshot"):
        bmd.run_backtest_a(
            snapshots_dir=snapshots_dir,
            identity_dir=identity_dir,
            draft_year=2025,
            run_id="malformed_snapshot",
            output_root=tmp_path / "runs",
            override_draft_date="2025-04-24",
            override_reason="manual_fixture_date",
        )


def test_runner_real_mode_truth_unavailable_fails_closed_with_metrics_null(
    tmp_path: Path,
    monkeypatch,
):
    snapshots_dir, identity_dir = _write_minimal_runner_inputs(tmp_path)

    monkeypatch.setattr(
        bmd,
        "ingest_snapshots",
        lambda *args, **kwargs: (
            [],
            {
                "draft_date_used": "2025-04-24",
                "draft_date_source": "nflreadr.draft_picks",
                "warnings": [],
            },
        ),
    )
    monkeypatch.setattr(
        bmd,
        "aggregate_per_prospect",
        lambda *args, **kwargs: {UUID_A: _consensus(UUID_A, 5.0)},
    )
    monkeypatch.setattr(bmd, "_load_nflreadr_truth", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        bmd,
        "join_bridge_to_realized",
        lambda *args, **kwargs: (
            [(_consensus(UUID_A, 5.0), _outcome(UUID_A, pick_no=1, position="QB"))],
            _join_diagnostics(),
        ),
    )

    result = bmd.run_backtest_a(
        snapshots_dir=snapshots_dir,
        identity_dir=identity_dir,
        draft_year=2025,
        run_id="truth_unavailable",
        output_root=tmp_path / "runs",
    )

    assert "nflreadr_truth_unavailable" in result.acceptance_criteria_failed
    assert result.metrics is None


def test_runner_real_mode_uses_ingestion_resolved_draft_date_for_aggregation(
    tmp_path: Path,
    monkeypatch,
):
    snapshots_dir, identity_dir = _write_minimal_runner_inputs(tmp_path)
    captured: dict = {}

    def fake_ingest(*args, **kwargs):
        return (
            [],
            {
                "draft_date_used": "2025-04-24",
                "draft_date_source": "nflreadr.draft_picks",
                "warnings": [],
            },
        )

    def fake_aggregate(normalized_picks, draft_date, dispersion_threshold=6):
        captured["draft_date"] = draft_date
        return {}

    monkeypatch.setattr(bmd, "ingest_snapshots", fake_ingest)
    monkeypatch.setattr(bmd, "aggregate_per_prospect", fake_aggregate)
    monkeypatch.setattr(bmd, "_load_nflreadr_truth", lambda *args, **kwargs: [])

    result = bmd.run_backtest_a(
        snapshots_dir=snapshots_dir,
        identity_dir=identity_dir,
        draft_year=2025,
        run_id="real_date",
        output_root=tmp_path / "runs",
    )

    assert captured["draft_date"] == "2025-04-24"
    assert result.metadata["draft_date_used"] == "2025-04-24"


def test_runner_preflight_uses_recursive_snapshot_discovery(
    tmp_path: Path,
    monkeypatch,
):
    snapshots_dir, identity_dir = _write_minimal_runner_inputs(
        tmp_path, nested_snapshot=True
    )

    monkeypatch.setattr(
        bmd,
        "ingest_snapshots",
        lambda *args, **kwargs: (
            [],
            {
                "draft_date_used": "2025-04-24",
                "draft_date_source": "nflreadr.draft_picks",
                "warnings": [],
            },
        ),
    )
    monkeypatch.setattr(bmd, "aggregate_per_prospect", lambda *args, **kwargs: {})
    monkeypatch.setattr(bmd, "_load_nflreadr_truth", lambda *args, **kwargs: [])

    result = bmd.run_backtest_a(
        snapshots_dir=snapshots_dir,
        identity_dir=identity_dir,
        draft_year=2025,
        run_id="nested_snapshot",
        output_root=tmp_path / "runs",
    )

    assert result.metadata["run_id"] == "nested_snapshot"


def test_cli_requires_override_date_and_reason_together(tmp_path: Path):
    assert RUN_BACKTEST_A_CLI.exists(), "Task 12 CLI must exist at scripts/run_backtest_a.py"

    result = subprocess.run(
        [
            str(RUN_BACKTEST_A_CLI),
            "--snapshots-dir",
            str(tmp_path / "snapshots"),
            "--identity-dir",
            str(tmp_path / "identity"),
            "--draft-year",
            "2025",
            "--run-id",
            "bad_override",
            "--override-draft-date",
            "2025-04-24",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "override" in (result.stderr + result.stdout).lower()
    assert "reason" in (result.stderr + result.stdout).lower()


def test_cli_returns_nonzero_on_schema_ingestion_error(tmp_path: Path):
    assert RUN_BACKTEST_A_CLI.exists(), "Task 12 CLI must exist at scripts/run_backtest_a.py"
    snapshots_dir = tmp_path / "snapshots"
    identity_dir = tmp_path / "identity"
    snapshots_dir.mkdir()
    identity_dir.mkdir()
    (snapshots_dir / "bad.json").write_text("{not-json", encoding="utf-8")

    result = subprocess.run(
        [
            str(RUN_BACKTEST_A_CLI),
            "--snapshots-dir",
            str(snapshots_dir),
            "--identity-dir",
            str(identity_dir),
            "--draft-year",
            "2025",
            "--run-id",
            "schema_error",
            "--override-draft-date",
            "2025-04-24",
            "--override-reason",
            "manual_fixture_date",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "schema" in (result.stderr + result.stdout).lower()
