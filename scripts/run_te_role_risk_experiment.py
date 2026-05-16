#!/usr/bin/env python3
"""Run the Phase 13.3.3 TE role-risk controlled experiment."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval.te_archetype_bakeoff import build_te_bakeoff_frame  # noqa: E402
from src.dynasty_genius.eval.te_archetype_bakeoff import BASELINE_TE_FEATURES  # noqa: E402
from src.dynasty_genius.eval.te_role_risk_experiment import (  # noqa: E402
    PRIMARY_ALPHA,
    evaluate_te_role_risk_experiment,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_eligible(path: Path) -> list[dict[str, Any]]:
    return list(_load_json(path)["eligible"])


def build_role_risk_report(
    *,
    training_path: Path,
    archetype_path: Path,
    eligible_path: Path,
    out_path: Path,
    run_id: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    training = pd.read_csv(training_path)
    te_training = training[training["position"] == "TE"].copy()
    archetype_artifact = _load_json(archetype_path)
    eligible_rows = _load_eligible(eligible_path)
    frame = build_te_bakeoff_frame(te_training, archetype_artifact, eligible_rows=eligible_rows)
    result = evaluate_te_role_risk_experiment(frame, test_years=[2020, 2021, 2022, 2023])
    report = {
        "metadata": {
            "schema_version": "0.1.0",
            "run_id": run_id,
            "generated_at": generated_at or _utc_timestamp(),
            "position": "TE",
            "source_training": training_path.as_posix(),
            "source_archetype_artifact": archetype_path.as_posix(),
            "source_eligible_manifest": eligible_path.as_posix(),
            "baseline_features": list(BASELINE_TE_FEATURES),
            "ridge_alpha": PRIMARY_ALPHA,
            "eligible_count": int(archetype_artifact["metadata"]["eligible_count"]),
            "te_training_rows": int(len(te_training)),
            "test_years": [2020, 2021, 2022, 2023],
        },
        "result": result,
        "governance": result["governance"],
        "decision": {
            "production_change_approved": False,
            "te_status": "EXPERIMENTAL",
            "next_step": "If accepted, write a separate production model-change spec for David approval.",
        },
        "audit_caveats": [
            "Repo-relative source paths are provenance references and may become stale if files move.",
            "No production model artifact was written by this experiment.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run validation-only TE role-risk experiment.")
    parser.add_argument("--training", required=True, type=Path)
    parser.add_argument("--archetype", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_role_risk_experiment_20260516")
    args = parser.parse_args(argv)
    report = build_role_risk_report(
        training_path=args.training,
        archetype_path=args.archetype,
        eligible_path=args.eligible_manifest,
        out_path=args.out,
        run_id=args.run_id,
    )
    accepted = report["result"]["candidates"]["unified_penalty"]["summary"]["passes_acceptance"]
    print(f"TE role-risk experiment written: {args.out} accepted={accepted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
