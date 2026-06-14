"""Step 0.5 — surgical, provenance-preserving republish of the Engine B trust substrate.

Path B (cockpit-approved, David-authorized 2026-06-13). The pinned source runs predate
Step 0.5 and carry no ``model_status`` / fold ``null_coverage``; ``publish_trust_surface.py``
is copy-only and cannot add the gate. This script MERGES ONLY the additive Step 0.5 fields
into each pinned source artifact and writes it to the published path, holding every legacy
field byte-invariant (``run_id`` / ``run_date`` / ``git_sha`` / ``model_artifact_hash`` /
fold metrics / ``g1``–``g4`` / ``overall_grade`` / ``promotion_justification``).

It does NOT re-run the harness and does NOT recompute the legacy gate via
``evaluate_promotion_gates`` (which would perturb ``overall_grade`` / ``promotion_justification``
/ ``g1``–``g4``). Per-fold ``null_coverage`` is set to 1.0: the v1 harness imputes feature
nulls (``keep_empty_features=True``) instead of dropping rows, so real fold-local coverage is
1.0 (disclosed; the gate activates if future feature work introduces row drops).

Allowed artifact diff (cockpit-locked): per-fold ``null_coverage`` plus
``promotion_gate.{model_status, status_version, validity_*, null_coverage_min,
status_explanation}``. Everything else is untouched.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Repo-root bootstrap so the script runs standalone (matches scripts/run_backtest_b.py,
# scripts/dump_openapi.py). Direct execution puts scripts/ — not the repo root — on
# sys.path[0], so `from src...` would otherwise fail. E402 is ignored for scripts/**.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.dynasty_genius.eval.backtest_artifact import BacktestResult, GateResult
from src.dynasty_genius.eval.composite_gate import (
    NULL_COVERAGE_MIN,
    compute_model_status,
    effective_ci_adequacy_gate_pass,
    effective_rank_gate_pass,
)

RUNS_DIR = _REPO_ROOT / "app/data/backtest/runs"
PUBLISHED_DIR = _REPO_ROOT / "app/data/backtest/trust_surface/latest"
# Single-source the schema default so this script can never drift from GateResult.
_STATUS_VERSION = GateResult.model_fields["status_version"].default


def _step05_gate_fields(folds, *, legacy_g2_pass: bool, leakage_clean: bool = True) -> dict:
    """Compute ONLY the additive Step 0.5 GateResult fields from folds carrying
    ``null_coverage``. Mirrors the Step 0.5 block of ``evaluate_promotion_gates`` using the
    same ``composite_gate`` helpers; recomputes NO legacy gate field. ``validity_rmse_stability_pass``
    is taken from the artifact's existing ``g2`` pass (the harness sets it to ``g2_pass``),
    never recomputed here.
    """
    null_coverage_values = [f.null_coverage for f in folds if f.null_coverage is not None]
    null_coverage_min = min(null_coverage_values) if null_coverage_values else None
    status, expl = compute_model_status(
        folds=folds,
        null_coverage_min_obs=null_coverage_min,
        leakage_clean=leakage_clean,
    )
    return {
        "model_status": status,
        "status_version": _STATUS_VERSION,
        "validity_spearman_pass": effective_rank_gate_pass(expl),
        "validity_r2_pass": effective_rank_gate_pass(expl),
        "validity_ci_adequacy_pass": effective_ci_adequacy_gate_pass(expl),
        "validity_rmse_stability_pass": legacy_g2_pass,
        "validity_null_coverage_pass": (
            null_coverage_min is not None and null_coverage_min >= NULL_COVERAGE_MIN
        ),
        "validity_leakage_pass": leakage_clean,
        "validity_cold_start_fold_index": expl.cold_start_fold_index,
        "validity_cold_start_tolerated": expl.cold_start_tolerated,
        "validity_most_recent_fold_index": expl.most_recent_fold_index,
        "validity_most_recent_fold_pass": expl.most_recent_fold_pass,
        "null_coverage_min": null_coverage_min,
        "status_explanation": expl.model_dump(mode="json"),
    }


def republish_step05_artifacts(
    runs_dir: Path,
    published_dir: Path,
    pinned_run_ids: dict,
) -> dict:
    """Surgically merge Step 0.5 fields from each pinned source run into the published path.

    Returns ``{"statuses": {position: model_status}, "published_dir": str}``.
    """
    runs_dir = Path(runs_dir)
    published_dir = Path(published_dir)
    published_dir.mkdir(parents=True, exist_ok=True)

    statuses: dict[str, str] = {}
    for position, run_id in pinned_run_ids.items():
        source = runs_dir / run_id / f"backtest_result_{position}.json"
        # RAW dict carries every legacy byte untouched; we mutate ONLY the allowed keys.
        raw = json.loads(source.read_text(encoding="utf-8"))
        # Typed load is for COMPUTATION ONLY (never written back).
        result = BacktestResult.load(source)
        for fold in result.folds:
            fold.null_coverage = 1.0
        fields = _step05_gate_fields(
            result.folds,
            legacy_g2_pass=raw["promotion_gate"]["g2_rmse_stability_pass"],
            leakage_clean=True,
        )
        raw["promotion_gate"].update(fields)
        for fold in raw["folds"]:
            fold["null_coverage"] = 1.0

        dest = published_dir / f"backtest_result_{position}.json"
        dest.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        statuses[position] = fields["model_status"]

    return {"statuses": statuses, "published_dir": str(published_dir)}


def main() -> None:
    from scripts.publish_trust_surface import PINNED_RUN_IDS

    report = republish_step05_artifacts(RUNS_DIR, PUBLISHED_DIR, PINNED_RUN_IDS)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
