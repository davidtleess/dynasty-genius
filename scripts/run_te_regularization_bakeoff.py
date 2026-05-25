#!/usr/bin/env python3
"""Run the Phase 13.3.4 TE regularization bake-off."""
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

from src.dynasty_genius.eval.te_archetype_bakeoff import (
    BASELINE_TE_FEATURES,  # noqa: E402
    build_te_bakeoff_frame,  # noqa: E402
)
from src.dynasty_genius.eval.te_regularization_bakeoff import (  # noqa: E402
    ALPHA_GRID,
    evaluate_te_regularization_bakeoff,
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_eligible(path: Path) -> list[dict[str, Any]]:
    return list(_load_json(path)["eligible"])


def build_regularization_report(
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
    result = evaluate_te_regularization_bakeoff(frame, test_years=[2020, 2021, 2022, 2023])
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
            "ridge_alpha": 1.0,
            "alpha_grid": list(ALPHA_GRID),
            "eligible_count": int(archetype_artifact["metadata"]["eligible_count"]),
            "te_training_rows": int(len(te_training)),
            "test_years": [2020, 2021, 2022, 2023],
        },
        "result": result,
        "governance": result["governance"],
        "decision_policy": {
            "production_change_approved": False,
            "te_status": "EXPERIMENTAL",
            "next_step": "Review artifact to determine whether stronger alpha + role-risk justifies a spec.",
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run validation-only TE regularization bake-off.")
    parser.add_argument("--training", required=True, type=Path)
    parser.add_argument("--archetype", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_reg_bakeoff_20260516")
    args = parser.parse_args(argv)
    report = build_regularization_report(
        training_path=args.training,
        archetype_path=args.archetype,
        eligible_path=args.eligible_manifest,
        out_path=args.out,
        run_id=args.run_id,
    )
    print(f"TE regularization bake-off written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
