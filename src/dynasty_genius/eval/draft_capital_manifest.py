"""Draft-capital candidate manifest for Phase 13.2.

This module declares the bake-off candidates and validation contract only. It
does not transform Engine A features or promote a model candidate.
"""
from __future__ import annotations

import dataclasses
from typing import Any

REQUIRED_CANDIDATES = {
    "current_engine_a_baseline",
    "log_decay",
    "position_bucketed",
    "position_isotonic_step",
}

REQUIRED_PRIMARY_METRICS = {
    "within_class_kendall_tau",
    "within_class_spearman_rho",
}

PROHIBITED_INPUTS = {
    "market_data",
    "ktc",
    "fantasycalc",
    "adp",
    "dynastynerds",
    "fantasypros",
    "consensus",
}


@dataclasses.dataclass(frozen=True)
class DraftCapitalCandidate:
    name: str
    role: str
    transform_type: str
    fit_scope: str
    promotion_eligible: bool
    position_priors: dict[str, list[list[int]]] = dataclasses.field(default_factory=dict)
    learned_breakpoints: bool = False
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class DraftCapitalValidationProtocol:
    fold_strategy: str
    primary_metrics: tuple[str, ...]
    secondary_checks: tuple[str, ...]
    promotion_requirements: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class DraftCapitalCandidateManifest:
    phase: str
    version: str
    candidates: tuple[DraftCapitalCandidate, ...]
    validation_protocol: DraftCapitalValidationProtocol
    prohibited_inputs: tuple[str, ...]
    out_of_scope: tuple[str, ...]

    @property
    def allows_market_inputs(self) -> bool:
        return not bool(PROHIBITED_INPUTS & set(self.prohibited_inputs))

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "version": self.version,
            "candidates": [candidate.as_dict() for candidate in self.candidates],
            "validation_protocol": self.validation_protocol.as_dict(),
            "prohibited_inputs": list(self.prohibited_inputs),
            "out_of_scope": list(self.out_of_scope),
            "allows_market_inputs": self.allows_market_inputs,
        }


DRAFT_CAPITAL_CANDIDATE_MANIFEST = DraftCapitalCandidateManifest(
    phase="13.2",
    version="1.0.0",
    candidates=(
        DraftCapitalCandidate(
            name="current_engine_a_baseline",
            role="baseline",
            transform_type="current_pick_round_features",
            fit_scope="existing_engine_a",
            promotion_eligible=False,
            notes="Control arm representing current Engine A draft-capital handling.",
        ),
        DraftCapitalCandidate(
            name="log_decay",
            role="control",
            transform_type="smooth_log_decay",
            fit_scope="per_position",
            promotion_eligible=False,
            notes="Smooth control arm; expected to miss hard NFL draft cliffs.",
        ),
        DraftCapitalCandidate(
            name="position_bucketed",
            role="candidate",
            transform_type="ordinal_categorical_bucket",
            fit_scope="per_position",
            promotion_eligible=True,
            position_priors={
                "QB": [[1, 15], [16, 32], [33, 64], [65, 999]],
                "RB": [[1, 32], [33, 64], [65, 105], [106, 999]],
                "WR": [[1, 32], [33, 75], [76, 105], [106, 999]],
                "TE": [[1, 32], [33, 999]],
            },
            notes="Interpretable bins from Phase 13 research priors; must be validated.",
        ),
        DraftCapitalCandidate(
            name="position_isotonic_step",
            role="candidate",
            transform_type="monotonic_isotonic_step",
            fit_scope="per_position",
            promotion_eligible=True,
            learned_breakpoints=True,
            notes="Data-driven monotonic step transform. Breakpoints are learned artifacts.",
        ),
    ),
    validation_protocol=DraftCapitalValidationProtocol(
        fold_strategy="leave_one_draft_class_out",
        primary_metrics=(
            "within_class_kendall_tau",
            "within_class_spearman_rho",
        ),
        secondary_checks=(
            "bootstrap_ci",
            "pick_jitter_sensitivity",
            "bucket_calibration",
            "fold_stability",
        ),
        promotion_requirements=(
            "locked_identity_snapshot",
            "beats_current_baseline",
            "beats_log_decay_control",
            "positive_confidence_interval_lift",
            "stable_breakpoints_under_pick_jitter",
            "no_market_derived_inputs",
            "model_card_update",
        ),
    ),
    prohibited_inputs=tuple(sorted(PROHIBITED_INPUTS)),
    out_of_scope=(
        "dvs",
        "te_promotion",
        "market_feature_injection",
        "engine_b_retraining",
    ),
)


def candidate_names(manifest: DraftCapitalCandidateManifest) -> set[str]:
    return {candidate.name for candidate in manifest.candidates}


def manifest_as_dict(manifest: DraftCapitalCandidateManifest) -> dict[str, Any]:
    return manifest.as_dict()


def validate_draft_capital_manifest(manifest: dict[str, Any]) -> list[str]:
    """Return validation errors for a serialized draft-capital manifest."""
    errors: list[str] = []
    candidates = manifest.get("candidates", [])
    names = {candidate.get("name") for candidate in candidates if isinstance(candidate, dict)}
    missing = REQUIRED_CANDIDATES - names
    for name in sorted(missing):
        errors.append(f"missing required candidate: {name}")

    validation = manifest.get("validation_protocol", {})
    if validation.get("fold_strategy") != "leave_one_draft_class_out":
        errors.append("fold_strategy must be leave_one_draft_class_out")

    primary_metrics = set(validation.get("primary_metrics", []))
    for metric in sorted(REQUIRED_PRIMARY_METRICS - primary_metrics):
        errors.append(f"missing required primary metric: {metric}")

    prohibited_inputs = set(manifest.get("prohibited_inputs", []))
    for forbidden in sorted(PROHIBITED_INPUTS - prohibited_inputs):
        errors.append(f"missing prohibited input guard: {forbidden}")

    if manifest.get("allows_market_inputs") is not False:
        errors.append("allows_market_inputs must be false")

    return errors
