"""QB-1 Round-20 post-GREEN real-surface projection (Claude v2) — the ONE
authorized read-only composition replay after the adapter GREEN (registration
read 0453ca80… §verification). Same projection law as revision 125
(`qb1_exclusion_row_diagnostic_claude_v1.py`): intercept compose_study's
defense-in-depth validate_registered_report_blocks call, project ONLY
structural exclusion-row facts, abort BEFORE the validator returns.

PASS criteria: 14 terminal comparison rows; every exclusion entry satisfies
the exclusion-row clause (zero violations); every reason word is in the
UNCHANGED publication vocabulary; before/after digests identical.

Run:
    .venv/bin/python3.14 docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_postgreen_projection_claude_v2.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import pandas as pd  # noqa: E402

import src.dynasty_genius.eval.qb_validation as qb  # noqa: E402
from src.dynasty_genius.eval.qb_validation.execution import (  # noqa: E402
    _FOLD_FLAG_VOCABULARY,
    _nonnegative_int,
)

sys.path.insert(0, str(REPO / "scripts"))
import run_qb1_study as runner  # noqa: E402

OUTPUT = Path(__file__).with_name(
    "qb1_exclusion_row_postgreen_projection_output_claude_v2.json"
)

PINNED_FILES = [
    "src/dynasty_genius/eval/qb_validation/execution.py",
    "scripts/run_qb1_study.py",
    "tests/contract/test_qb1_green_correction_contracts.py",
    "src/dynasty_genius/eval/qb_validation/identity.py",
    "src/dynasty_genius/eval/qb_validation/study_matrix.py",
    "src/dynasty_genius/eval/qb_validation/qb_ppg_labels.py",
    "src/dynasty_genius/eval/qb_validation/status.py",
    "src/dynasty_genius/adapters/nflreadpy_qb_adapter.py",
    "src/dynasty_genius/eval/qb_validation/errors.py",
    "src/dynasty_genius/eval/qb_validation/comparisons.py",
    "app/data/backtest/qb_validation/qb_validation_report.json",
    "docs/agent-ledger/evidence/2026-08-16/qb1_registered_rerun_r19_stdout_claude_v1.txt",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_state() -> dict[str, str]:
    state: dict[str, str] = {}
    for rel in PINNED_FILES:
        state[rel] = sha256(REPO / rel)
    for file in sorted((REPO / runner.RAW_ROOT).rglob("*")):
        if file.is_file():
            state[str(file.relative_to(REPO))] = sha256(file)
    return state


class _AbortDiagnostic(BaseException):
    pass


def project(blocks: Any) -> dict[str, Any]:
    rows_out: list[dict[str, Any]] = []
    totals = {
        "comparison_rows": 0,
        "exclusion_entries": 0,
        "entries_satisfying_clause": 0,
        "entries_violating_clause": 0,
        "reason_words_outside_vocabulary": 0,
    }
    for row in blocks.get("comparisons", []):
        totals["comparison_rows"] += 1
        excluded = row.get("excluded_folds") if isinstance(row, dict) else None
        view = {
            "id": row.get("id"),
            "lane": row.get("lane"),
            "excluded_container_type": type(excluded).__name__,
            "entries": [],
        }
        for index, entry in enumerate(
            excluded if isinstance(excluded, (list, tuple)) else []
        ):
            totals["exclusion_entries"] += 1
            is_mapping = isinstance(entry, dict)
            reasons = entry.get("reasons") if is_mapping else None
            reasons_seq = isinstance(reasons, (list, tuple))
            words = [
                {"word": reason, "in_vocabulary": reason in _FOLD_FLAG_VOCABULARY}
                for reason in (reasons if reasons_seq else [])
            ]
            outside = sum(1 for w in words if not w["in_vocabulary"])
            totals["reason_words_outside_vocabulary"] += outside
            satisfies = (
                is_mapping
                and _nonnegative_int(entry.get("test_season"))
                and reasons_seq
                and bool(reasons)
                and outside == 0
            )
            totals[
                "entries_satisfying_clause"
                if satisfies
                else "entries_violating_clause"
            ] += 1
            view["entries"].append(
                {
                    "index": index,
                    "test_season": entry.get("test_season") if is_mapping else None,
                    "reasons": words,
                    "satisfies_exclusion_clause": satisfies,
                }
            )
        rows_out.append(view)
    return {
        "registered_vocabulary_from_pinned_code": sorted(_FOLD_FLAG_VOCABULARY),
        "rows": rows_out,
        "totals": totals,
    }


def main() -> int:
    before = hash_state()
    captured: dict[str, Any] = {}
    real_validator = qb.validate_registered_report_blocks

    def intercept(blocks: Any, *, registration: Any) -> None:
        captured["projection"] = project(blocks)
        raise _AbortDiagnostic

    registration = runner.load_registration(REPO)
    qb.enforce_consumer_boundary(repo_root=REPO)
    crosswalk_entries, observed_at = runner.load_crosswalk(REPO)
    pool = qb.admit_and_load_validation_pool(
        REPO / runner.RAW_ROOT, repo_root=REPO, frame_loader=pd.read_parquet
    )
    dp_snapshots = qb.load_h5_snapshots(
        REPO / runner.DP_VALUES_ROOT, registration=registration
    )
    dp_rows_by_season = {
        snapshot["season"]: runner.load_dp_snapshot_rows(snapshot)
        for snapshot in dp_snapshots
    }
    qb.validate_registered_report_blocks = intercept
    aborted = False
    try:
        runner.compose_study(
            registration=registration,
            pool=pool,
            crosswalk_entries=crosswalk_entries,
            crosswalk_observed_at=observed_at,
            dp_snapshots=dp_snapshots,
            dp_rows_by_season=dp_rows_by_season,
            repo_root=REPO,
            frozen_inputs={REPO / runner.CROSSWALK_PATH: runner.CROSSWALK_SHA256},
        )
    except _AbortDiagnostic:
        aborted = True
    finally:
        qb.validate_registered_report_blocks = real_validator

    after = hash_state()
    projection = captured.get("projection") or {}
    totals = projection.get("totals") or {}
    passed = (
        aborted
        and before == after
        and totals.get("comparison_rows") == 14
        and totals.get("entries_violating_clause") == 0
        and totals.get("reason_words_outside_vocabulary") == 0
    )
    result = {
        "diagnostic": "qb1-exclusion-row-postgreen-projection/2",
        "aborted_before_validator_returned": aborted,
        "intercept_fired": "projection" in captured,
        "projection": projection,
        "hashes_before_equal_after": before == after,
        "passed": passed,
        "hashes": before,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "aborted": aborted,
                "hashes_before_equal_after": before == after,
                "totals": totals,
                "passed": passed,
                "output": str(OUTPUT.relative_to(REPO)),
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
