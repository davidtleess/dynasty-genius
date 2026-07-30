"""TW30-WORD-K RED: the SQL governance workflow reports truth without gating."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

WORKFLOW_PATH = Path(".github/workflows/codex_audit.yml")


def _workflow() -> tuple[str, dict[str, Any]]:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)
    return text, parsed


def _step(
    job: dict[str, Any], *, step_id: str | None = None, name: str | None = None
) -> dict:
    matches = [
        step
        for step in job["steps"]
        if (step_id is None or step.get("id") == step_id)
        and (name is None or step.get("name") == name)
    ]
    assert len(matches) == 1
    return matches[0]


def test_sql_governance_report_only_workflow_preserves_auditor_truth(
    tmp_path: Path,
) -> None:
    """A real auditor failure must be visible numerically without becoming a job gate."""
    workflow_text, workflow = _workflow()
    job = workflow["jobs"]["sql-governance"]
    audit = _step(job, step_id="sql_audit")
    summary = _step(job, name="Publish audit findings to the run summary")

    assert job["name"] == "SQL governance audit (REPORT-ONLY)"
    assert audit["continue-on-error"] is True
    assert audit["shell"] == "bash"
    assert (
        "python scripts/codex_audit_sql.py infrastructure/src/sql resources"
        in audit["run"]
    )
    assert 'echo "$code" > sql_audit_exit.txt' in audit["run"]
    assert 'exit "$code"' in audit["run"]

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        'echo "simulated SQL governance finding"\n'
        'exit "${FAKE_AUDIT_EXIT:-7}"\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "FAKE_AUDIT_EXIT": "7",
    }

    audit_result = subprocess.run(
        ["bash", "-c", audit["run"]],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert audit_result.returncode == 7
    assert (tmp_path / "sql_audit_exit.txt").read_text(encoding="utf-8").strip() == "7"
    assert "simulated SQL governance finding" in (
        tmp_path / "sql_audit_output.txt"
    ).read_text(encoding="utf-8")

    assert summary["if"] == "always()"
    assert summary["shell"] == "bash"
    summary_path = tmp_path / "github-step-summary.md"
    summary_script = summary["run"].replace(
        "${{ steps.sql_audit.outcome }}",
        "failure",
    )
    summary_result = subprocess.run(
        ["bash", "-c", summary_script],
        cwd=tmp_path,
        env={**env, "GITHUB_STEP_SUMMARY": str(summary_path)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert summary_result.returncode == 0
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "Auditor exit code (the auditor's own): `7`" in summary_text
    assert "Step outcome (tolerated by continue-on-error): `failure`" in summary_text
    assert "simulated SQL governance finding" in summary_text
    assert "they route to TOWER" in summary["run"]
    assert "straight to David" in summary["run"]

    # The audit step is tolerated; the workflow must not promise that unrelated
    # setup or summary failures are impossible.
    assert "because the job cannot fail" not in workflow_text.lower()
