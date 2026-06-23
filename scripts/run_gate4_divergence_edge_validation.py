"""Gate-4 divergence-edge validation — T2 runner + §8 report emitter.

Wraps the T1 pure engine (`src/dynasty_genius/eval/gate4_divergence_edge.py`) with
report assembly, a test-backed §8 report-schema lock, aggregate-only +
decision_supported guards, and a fixture-injectable orchestration (`load_archive`
/ `analyze` are passed in so this is testable without the real archive). The real
FantasyCalc-archive run is T3-gated.

Pre-registered spec: docs/superpowers/specs/2026-06-23-gate4-divergence-edge-validation-design.md
(seal 84531dc). Validation study only — no model/PVO/Engine/UI/contract change;
market overlay-only; aggregate-only output; decision_supported=False.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dynasty_genius.eval.gate4_divergence_edge import (  # noqa: E402
    EFFECT_SIZE_FLOOR,
    HIGH_BAND,
    MIN_EFFECTIVE_BLOCKS,
    NEUTRAL_BAND,
    derive_claim_level,
)

REPORT_SCHEMA_VERSION = "gate4_divergence_edge_report.v1"
CLAIM_RETROSPECTIVE = "current_model_retrospective_diagnostic"
RETROSPECTIVE_DISCLAIMER = "retrospective association, not a tradeable edge"

_HORIZON_FIELDS = (
    "lift_HIGH",
    "lift_LOW",
    "bootstrap_ci",
    "effect_size",
    "n_by_bucket",
    "effective_month_block_count",
    "non_overlapping_sensitivity_sign",
)
_REQUIRED_REPORT_FIELDS = (
    "schema_version",
    "verdict",
    "claim_level",
    "training_cutoff",
    "source_family",
    "settings_hash",
    "archive_provenance",
    "horizons",
    "coverage",
    "stability",
    "falsification",
    "decision_supported",
    "pre_registration_lock",
    "summary",
)
# Nested §8 required fields — the report-schema lock must fail closed on these too
# (Codex T2 RED: a shallow top-level check is not the "test-backed schema lock"
# the spec requires).
_REQUIRED_NESTED: dict[str, tuple[str, ...]] = {
    "archive_provenance": ("files", "date_range", "snapshot_count", "cadence"),
    "coverage": (
        "usable_t_dates_by_horizon",
        "joined_observations",
        "identity_coverage",
        "per_position_missingness",
        "matched_surviving_counts",
    ),
    "stability": (
        "leave_one_month_out_signs",
        "top_position_contribution",
        "top_position_excluded",
    ),
    "falsification": (
        "label_shuffle_null",
        "lookahead_guard",
        "survivorship_on_off",
        "within_position_enforcement",
        "source_family_single_assert",
    ),
    "pre_registration_lock": ("param_snapshot",),
}
_REQUIRED_FILE_FIELDS = ("path", "sha256", "byte_size")


class Gate4ReportSchemaError(Exception):
    """Raised when a report violates the locked §8 schema / honesty guards."""


class Gate4RunnerError(Exception):
    """Raised when the operational run aborts (e.g. coverage gate not satisfied)."""


# ── Report assembly ──────────────────────────────────────────────────────────


def _summary(verdict: str, claim_level: str) -> dict:
    """Claim-level honesty block. A retrospective PASS statement MUST carry the
    'not a tradeable edge' disclaimer (spec §3.1/§8)."""
    if claim_level == CLAIM_RETROSPECTIVE:
        disclaimer = (
            "claim_level=current_model_retrospective_diagnostic: any PASS is a "
            f"{RETROSPECTIVE_DISCLAIMER}; it justifies a later vintage/walk-forward "
            "study, not product promotion."
        )
        pass_statements = (
            [f"Gate-4 verdict PASS — {RETROSPECTIVE_DISCLAIMER}."] if verdict == "PASS" else []
        )
    else:
        disclaimer = ""
        pass_statements = (
            ["Gate-4 verdict PASS (claim_level=tradeable_historical_edge)."]
            if verdict == "PASS"
            else []
        )
    return {"claim_level_disclaimer": disclaimer, "pass_statements": pass_statements}


def build_gate4_report(
    *,
    verdict: str,
    claim_level: str,
    training_cutoff: Any,
    source_family: str,
    settings_hash: str,
    archive_provenance: dict,
    horizon_results: dict[str, dict],
    coverage: dict,
    stability: dict,
    falsification: dict,
    pre_registration_lock: dict,
) -> dict:
    """Assemble the §8 machine-readable report. Aggregate-only by construction."""
    horizons = {
        h: {k: res[k] for k in _HORIZON_FIELDS} for h, res in horizon_results.items()
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "verdict": verdict,
        "claim_level": claim_level,
        "training_cutoff": training_cutoff,
        "source_family": source_family,
        "settings_hash": settings_hash,
        "archive_provenance": archive_provenance,
        "horizons": horizons,
        "coverage": coverage,
        "stability": stability,
        "falsification": falsification,
        "decision_supported": False,
        "pre_registration_lock": pre_registration_lock,
        "summary": _summary(verdict, claim_level),
    }


# ── Schema + honesty validators (test-backed lock, §8) ────────────────────────


def validate_gate4_report_schema(report: dict) -> None:
    """Fail closed on any missing required §8 field."""
    for field in _REQUIRED_REPORT_FIELDS:
        if field not in report:
            raise Gate4ReportSchemaError(f"missing required report field: {field}")
    if "spec_sha" not in report["pre_registration_lock"]:
        raise Gate4ReportSchemaError("pre_registration_lock missing spec_sha")

    # Nested required §8 fields (fail closed, naming the missing leaf).
    for section, keys in _REQUIRED_NESTED.items():
        node = report[section]
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                raise Gate4ReportSchemaError(f"{section} missing required field: {key}")
    date_range = report["archive_provenance"]["date_range"]
    for key in ("start", "end"):
        if not isinstance(date_range, dict) or key not in date_range:
            raise Gate4ReportSchemaError(f"archive_provenance.date_range missing required field: {key}")

    # archive_provenance.files: non-empty, each entry fully provenanced.
    files = report["archive_provenance"]["files"]
    if not isinstance(files, list) or not files:
        raise Gate4ReportSchemaError("archive_provenance.files must be a non-empty list")
    for entry in files:
        for key in _REQUIRED_FILE_FIELDS:
            if not isinstance(entry, dict) or key not in entry:
                raise Gate4ReportSchemaError(f"archive file entry missing required field: {key}")

    horizons = report["horizons"]
    if not isinstance(horizons, dict) or not horizons:
        raise Gate4ReportSchemaError("horizons must be a non-empty mapping")
    for h, res in horizons.items():
        missing = set(_HORIZON_FIELDS) - set(res)
        if missing:
            raise Gate4ReportSchemaError(f"horizon {h} missing fields: {sorted(missing)}")


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)


def assert_aggregate_only_report(report: dict) -> None:
    """No per-player rows may appear — the study reports buckets/horizons only
    (spec §7)."""
    for node in _walk(report):
        if isinstance(node, dict) and ("player_id" in node or "rows" in node):
            raise Gate4ReportSchemaError(
                "aggregate-only violation: per-player rows are not permitted in the report"
            )


def assert_recursive_decision_supported_false(report: dict) -> None:
    """`decision_supported=True` must never appear anywhere (spec §6/§7)."""
    for node in _walk(report):
        if isinstance(node, dict) and node.get("decision_supported") is True:
            raise Gate4ReportSchemaError("decision_supported=True is forbidden in the report")


# ── Orchestration (fixture-injectable; real archive is T3-gated) ──────────────


def _param_snapshot() -> dict:
    return {
        "divergence_high_threshold": HIGH_BAND,
        "neutral_band": NEUTRAL_BAND,
        "primary_horizons": [60, 90],
        "effect_size_floor": EFFECT_SIZE_FLOOR,
        "min_effective_month_blocks": MIN_EFFECTIVE_BLOCKS,
    }


def run_gate4_validation(
    *,
    load_archive: Callable[[], dict],
    analyze: Callable[..., dict],
    output_dir: Path,
    run_id: str,
    spec_sha: str,
) -> Path:
    """Orchestrate: load → coverage gate → claim_level → analyze → report → write.

    `load_archive` and `analyze` are injected so this is exercised on fixtures
    without a real DB/network (the real run wires the actual loader/analyzer)."""
    loaded = load_archive()

    if loaded.get("coverage_gate_status") != "ok":
        raise Gate4RunnerError(
            f"coverage gate not satisfied: {loaded.get('coverage_gate_status')!r} (abort, no run)"
        )

    claim_level = derive_claim_level(
        loaded["test_dates"], training_cutoff=loaded.get("training_cutoff")
    )
    analysis = analyze(loaded, claim_level=claim_level)

    training_cutoff = loaded.get("training_cutoff")
    report = build_gate4_report(
        verdict=analysis["verdict"],
        claim_level=claim_level,
        training_cutoff=training_cutoff.isoformat() if training_cutoff else None,
        source_family=loaded["source_family"],
        settings_hash=loaded["settings_hash"],
        archive_provenance=loaded["archive_provenance"],
        horizon_results=analysis["horizon_results"],
        coverage=analysis["coverage"],
        stability=analysis["stability"],
        falsification=analysis["falsification"],
        pre_registration_lock={"spec_sha": spec_sha, "param_snapshot": _param_snapshot()},
    )

    validate_gate4_report_schema(report)
    assert_aggregate_only_report(report)
    assert_recursive_decision_supported_false(report)

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2) + "\n"
    run_path = output_dir / f"gate4_divergence_edge_{run_id}.json"
    run_path.write_text(payload, encoding="utf-8")
    (output_dir / "gate4_divergence_edge_latest.json").write_text(payload, encoding="utf-8")
    return run_path
