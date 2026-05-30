"""Subsystem 4 Backtest-B v1 always-abstain stub contract tests (§6.1)."""
from __future__ import annotations

import builtins
import json
import subprocess
from pathlib import Path

from src.dynasty_genius.eval import backtest_mock_draft as bmd

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_BACKTEST_B_CLI = REPO_ROOT / "scripts" / "run_backtest_b.py"

EXPECTED_B_STUB_REASON = (
    "Backtest B v1 deliberately excluded per spec §39; "
    "gated on Backtest A clearance"
)

FALSIFICATION_MATRIX = {
    "valid_nominal": {
        "owner": "Task 13",
        "coverage": "exact 6-field dict with decision_supported False and exit_code 0",
        "out_of_scope": None,
    },
    "upstream_run_id_present": {
        "owner": "Task 13",
        "coverage": "passed upstream_run_id is echoed into library and CLI report",
        "out_of_scope": None,
    },
    "upstream_run_id_none": {
        "owner": "Task 13",
        "coverage": "omitted upstream_run_id remains None",
        "out_of_scope": None,
    },
    "wrong_type": {
        "owner": "Task 13 caller",
        "coverage": None,
        "out_of_scope": (
            "top-level Python argument type misuse is caller contract; CLI parses "
            "strings and library preserves the provided value without validation"
        ),
    },
    "write_isolation": {
        "owner": "Task 13",
        "coverage": "only backtest_b_abstain.json may be written; no other B artifacts",
        "out_of_scope": None,
    },
    "abstain_locked": {
        "owner": "Task 13",
        "coverage": "stub status/reason/required_gate cannot silently become non-abstain",
        "out_of_scope": None,
    },
    "cli_symmetry": {
        "owner": "Task 13",
        "coverage": "CLI accepts Backtest-A flags plus --upstream-run without ingestion",
        "out_of_scope": None,
    },
}


def _expected_payload(upstream_run_id=None) -> dict:
    return {
        "status": "gated_on_backtest_a_per_bucket_position",
        "reason": EXPECTED_B_STUB_REASON,
        "required_gate": "backtest_a_per_bucket_position",
        "upstream_run_id": upstream_run_id,
        "decision_supported": False,
        "exit_code": 0,
    }


def test_task13_falsification_matrix_seeded_with_explicit_owners():
    expected_rows = {
        "valid_nominal",
        "upstream_run_id_present",
        "upstream_run_id_none",
        "wrong_type",
        "write_isolation",
        "abstain_locked",
        "cli_symmetry",
    }

    assert set(FALSIFICATION_MATRIX) == expected_rows
    for row, entry in FALSIFICATION_MATRIX.items():
        assert entry["owner"], row
        assert entry["coverage"] or entry["out_of_scope"], row


def test_run_backtest_b_returns_exact_abstain_contract_without_upstream_run():
    result = bmd.run_backtest_b()

    assert result == _expected_payload()


def test_run_backtest_b_echoes_upstream_run_id():
    result = bmd.run_backtest_b(upstream_run_id="backtest_a_20260530T103000Z")

    assert result == _expected_payload("backtest_a_20260530T103000Z")


def test_backtest_b_remains_abstained_in_v1(tmp_path: Path, monkeypatch):
    writes: list[Path] = []
    real_open = builtins.open

    def spy_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            writes.append(Path(file))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)

    result = bmd.write_backtest_b_abstain_report(
        run_id="b_stub_lock",
        output_root=tmp_path,
        upstream_run_id="backtest_a_upstream",
    )

    assert result == _expected_payload("backtest_a_upstream")
    assert writes == [tmp_path / "b_stub_lock" / "backtest_b_abstain.json"]
    assert writes[0].exists()
    assert json.loads(writes[0].read_text(encoding="utf-8")) == result


def test_cli_accepts_backtest_a_flags_plus_upstream_run_and_writes_abstain_report(
    tmp_path: Path,
):
    assert RUN_BACKTEST_B_CLI.exists(), "Task 13 CLI must exist at scripts/run_backtest_b.py"
    run_id = "b_cli_stub"
    upstream_run_id = "backtest_a_20260530T103000Z"

    result = subprocess.run(
        [
            str(RUN_BACKTEST_B_CLI),
            "--snapshots-dir",
            str(tmp_path / "snapshots"),
            "--identity-dir",
            str(tmp_path / "identity"),
            "--draft-year",
            "2025",
            "--run-id",
            run_id,
            "--output-root",
            str(tmp_path / "runs"),
            "--override-draft-date",
            "2025-04-24",
            "--override-reason",
            "manual_fixture_date",
            "--include-untrusted",
            "--dispersion-threshold",
            "6",
            "--upstream-run",
            upstream_run_id,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    report_path = tmp_path / "runs" / run_id / "backtest_b_abstain.json"
    assert result.returncode == 0
    assert report_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8")) == _expected_payload(
        upstream_run_id
    )


def test_cli_allows_missing_upstream_run_and_records_null(tmp_path: Path):
    assert RUN_BACKTEST_B_CLI.exists(), "Task 13 CLI must exist at scripts/run_backtest_b.py"
    run_id = "b_cli_no_upstream"

    result = subprocess.run(
        [
            str(RUN_BACKTEST_B_CLI),
            "--snapshots-dir",
            str(tmp_path / "snapshots"),
            "--identity-dir",
            str(tmp_path / "identity"),
            "--draft-year",
            "2025",
            "--run-id",
            run_id,
            "--output-root",
            str(tmp_path / "runs"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    report_path = tmp_path / "runs" / run_id / "backtest_b_abstain.json"
    assert result.returncode == 0
    assert json.loads(report_path.read_text(encoding="utf-8")) == _expected_payload()
