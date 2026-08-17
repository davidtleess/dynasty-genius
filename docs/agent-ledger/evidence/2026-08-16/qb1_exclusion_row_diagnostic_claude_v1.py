"""QB-1 revision-125 exclusion-row diagnostic (Claude v1) — Codex-staged
boundary `07d9ae3c…`, ACKed and released.

ONE composition replay against the unchanged frozen inputs, OUTSIDE the
registered runner. `compose_study`'s defense-in-depth
`validate_registered_report_blocks` call is intercepted; the projection below
is taken and the replay ABORTS before the validator returns. Persisted fields
are EXACTLY the sanctioned structural projection — no metric, status, label,
identity, panel, detail, or exception text.

Run:
    .venv/bin/python3.14 docs/agent-ledger/evidence/2026-08-16/qb1_exclusion_row_diagnostic_claude_v1.py
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

OUTPUT = Path(__file__).with_name("qb1_exclusion_row_diagnostic_output_claude_v1.json")

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
    """BaseException-derived so no composition-internal handler can swallow
    the abort; the composed payload never proceeds past the intercept."""


def project_exclusion_rows(blocks: Any) -> dict[str, Any]:
    """The sanctioned structural projection over comparisons' excluded_folds.
    Reads ONLY: id, lane, container types/lengths, entry keys, test_season
    (+type/predicate), reason words (+vocabulary membership), violated
    conjuncts of the execution.py:1288-1302 law, aggregate counts."""
    rows_out: list[dict[str, Any]] = []
    totals = {
        "comparison_rows": 0,
        "rows_with_none_excluded": 0,
        "rows_with_list_excluded": 0,
        "rows_with_other_excluded_type": 0,
        "exclusion_entries": 0,
        "violating_entries": 0,
        "violations_by_conjunct": {
            "entry_not_mapping": 0,
            "test_season_not_nonnegative_int": 0,
            "reasons_not_list_or_tuple": 0,
            "reasons_empty": 0,
            "reason_word_outside_vocabulary": 0,
        },
    }
    comparisons = blocks.get("comparisons") if isinstance(blocks, dict) else None
    if not isinstance(comparisons, list):
        return {
            "comparisons_container_type": type(comparisons).__name__,
            "rows": [],
            "totals": totals,
        }
    for row in comparisons:
        totals["comparison_rows"] += 1
        row_id = row.get("id") if isinstance(row, dict) else None
        lane = row.get("lane") if isinstance(row, dict) else None
        excluded = row.get("excluded_folds") if isinstance(row, dict) else None
        row_view: dict[str, Any] = {
            "id": row_id,
            "lane": lane,
            "excluded_container_type": type(excluded).__name__,
            "excluded_length": len(excluded)
            if isinstance(excluded, (list, tuple))
            else None,
            "entries": [],
        }
        if excluded is None:
            totals["rows_with_none_excluded"] += 1
        elif isinstance(excluded, list):
            totals["rows_with_list_excluded"] += 1
        else:
            totals["rows_with_other_excluded_type"] += 1
        entries = excluded if isinstance(excluded, (list, tuple)) else []
        for index, entry in enumerate(entries):
            totals["exclusion_entries"] += 1
            violated: list[str] = []
            is_mapping = isinstance(entry, dict)
            if not is_mapping:
                violated.append("entry_not_mapping")
            season = entry.get("test_season") if is_mapping else None
            season_ok = _nonnegative_int(season)
            if not season_ok:
                violated.append("test_season_not_nonnegative_int")
            reasons = entry.get("reasons") if is_mapping else None
            reasons_is_seq = isinstance(reasons, (list, tuple))
            if not reasons_is_seq:
                violated.append("reasons_not_list_or_tuple")
            elif not reasons:
                violated.append("reasons_empty")
            reason_views: list[dict[str, Any]] = []
            if reasons_is_seq:
                for reason in reasons:
                    member = reason in _FOLD_FLAG_VOCABULARY
                    reason_views.append(
                        {"word": reason if isinstance(reason, str) else
                         f"<non-str:{type(reason).__name__}>",
                         "in_vocabulary": member}
                    )
                    if not member:
                        violated.append("reason_word_outside_vocabulary")
            for name in violated:
                if name in totals["violations_by_conjunct"]:
                    totals["violations_by_conjunct"][name] += 1
            if violated:
                totals["violating_entries"] += 1
            row_view["entries"].append(
                {
                    "index": index,
                    "sorted_keys": sorted(map(str, entry)) if is_mapping else None,
                    "test_season": season
                    if isinstance(season, (int, float, str)) or season is None
                    else f"<{type(season).__name__}>",
                    "test_season_type": type(season).__name__,
                    "test_season_nonnegative_int": season_ok,
                    "reasons_container_type": type(reasons).__name__,
                    "reasons_length": len(reasons) if reasons_is_seq else None,
                    "reasons": reason_views,
                    "violated_conjuncts": sorted(set(violated)),
                }
            )
        rows_out.append(row_view)
    return {
        "comparisons_container_type": "list",
        "registered_vocabulary_from_pinned_code": sorted(_FOLD_FLAG_VOCABULARY),
        "rows": rows_out,
        "totals": totals,
    }


def main() -> int:
    before = hash_state()
    captured: dict[str, Any] = {}
    real_validator = qb.validate_registered_report_blocks

    def intercept(blocks: Any, *, registration: Any) -> None:
        captured["projection"] = project_exclusion_rows(blocks)
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
    result = {
        "diagnostic": "qb1-exclusion-row-projection/1",
        "boundary_script_sha256": (
            "07d9ae3c619e2d57bfb544903c7c012907087b74ef35685430cc0a2f4f186ae2"
        ),
        "aborted_before_validator_returned": aborted,
        "intercept_fired": "projection" in captured,
        "projection": captured.get("projection"),
        "hashes_before_equal_after": before == after,
        "hashes": before,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(
        json.dumps(
            {
                "aborted": aborted,
                "intercept_fired": "projection" in captured,
                "hashes_before_equal_after": before == after,
                "totals": (captured.get("projection") or {}).get("totals"),
                "output": str(OUTPUT.relative_to(REPO)),
            },
            indent=2,
        )
    )
    return 0 if aborted and "projection" in captured and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
