#!/usr/bin/env python3
"""Run the Phase 13.3.2 TE archetype feature bake-off report builder."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BuildFrameFn = Callable[..., pd.DataFrame]
EvaluateFn = Callable[..., dict[str, Any]]

DEFAULT_TEST_YEARS = [2020, 2021, 2022, 2023]
SCHEMA_VERSION = "0.1.0"

CANDIDATES: dict[str, list[str]] = {
    "snap_alignment_one_hot": [
        "te_align_detached",
        "te_align_balanced",
        "te_align_inline",
    ],
    "fantasy_role_one_hot": [
        "te_role_receiving_specialist",
        "te_role_complete_te",
        "te_role_blocking_specialist",
        "te_role_role_risk",
        "te_role_unclear_role",
    ],
    "complete_te_detector": ["te_role_complete_te"],
    "role_risk_detector": ["te_role_role_risk", "te_role_blocking_specialist"],
}


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_eligible(path: Path) -> list[dict[str, Any]]:
    data = _load_json(path)
    return list(data["eligible"])


def _load_evaluator_functions() -> tuple[BuildFrameFn, EvaluateFn]:
    try:
        from src.dynasty_genius.eval.te_archetype_bakeoff import (
            build_te_bakeoff_frame,
            evaluate_te_taxonomy_candidate,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Phase 13.3.2 evaluator functions are unavailable. "
            "Worker A/B must provide src.dynasty_genius.eval.te_archetype_bakeoff "
            "with build_te_bakeoff_frame and evaluate_te_taxonomy_candidate."
        ) from exc
    return build_te_bakeoff_frame, evaluate_te_taxonomy_candidate


def _governance_block() -> dict[str, bool]:
    return {
        "diagnostic_only": True,
        "model_features_changed": False,
        "te_promotion_changed": False,
        "market_data_used": False,
        "pff_grades_used": False,
        "player_level_rows_emitted": False,
    }


def build_bakeoff_report(
    *,
    training_path: Path,
    archetype_path: Path,
    eligible_path: Path,
    out_path: Path,
    run_id: str,
    generated_at: str | None = None,
    test_years: list[int] | None = None,
) -> dict[str, Any]:
    build_frame, evaluate_candidate = _load_evaluator_functions()

    training = pd.read_csv(training_path)
    te_training = training[training["position"] == "TE"].copy()
    archetype_artifact = _load_json(archetype_path)
    eligible_rows = _load_eligible(eligible_path)
    frame = build_frame(te_training, archetype_artifact, eligible_rows=eligible_rows)

    fold_years = test_years or DEFAULT_TEST_YEARS
    results = {
        name: evaluate_candidate(
            frame,
            candidate_name=name,
            candidate_columns=columns,
            test_years=fold_years,
        )
        for name, columns in CANDIDATES.items()
    }

    report = {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "generated_at": generated_at or _utc_timestamp(),
            "position": "TE",
            "source_training": training_path.as_posix(),
            "source_archetype_artifact": archetype_path.as_posix(),
            "eligible_count": int(
                archetype_artifact.get("metadata", {}).get("eligible_count", len(eligible_rows))
            ),
            "te_training_rows": int(len(te_training)),
            "test_years": fold_years,
        },
        "candidates": results,
        "governance": _governance_block(),
        "decision_policy": {
            "acceptance": (
                "Candidate must improve mean RMSE and MAE, improve RMSE in at least "
                "3 of 4 folds, and pass redaction/governance checks before a later "
                "David-approved model-change spec."
            ),
            "te_status": "TE remains EXPERIMENTAL regardless of this bake-off result.",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run validation-only TE archetype bake-off.")
    parser.add_argument("--training", required=True, type=Path)
    parser.add_argument("--archetype", required=True, type=Path)
    parser.add_argument("--eligible-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", default="te_archetype_bakeoff_20260516")
    parser.add_argument("--generated-at")
    args = parser.parse_args(argv)

    report = build_bakeoff_report(
        training_path=args.training,
        archetype_path=args.archetype,
        eligible_path=args.eligible_manifest,
        out_path=args.out,
        run_id=args.run_id,
        generated_at=args.generated_at,
    )
    print(f"TE archetype bake-off written: {args.out} candidates={len(report['candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
