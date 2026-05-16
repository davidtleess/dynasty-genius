"""Task 13.2.0 tests: draft-capital candidate manifest."""
from __future__ import annotations

import json

from src.dynasty_genius.eval.draft_capital_manifest import (
    DRAFT_CAPITAL_CANDIDATE_MANIFEST,
    REQUIRED_CANDIDATES,
    REQUIRED_PRIMARY_METRICS,
    candidate_names,
    manifest_as_dict,
    validate_draft_capital_manifest,
)


def test_manifest_contains_all_required_candidates():
    names = candidate_names(DRAFT_CAPITAL_CANDIDATE_MANIFEST)

    assert REQUIRED_CANDIDATES <= names


def test_manifest_marks_baseline_and_log_decay_as_non_promoted_controls():
    by_name = {candidate.name: candidate for candidate in DRAFT_CAPITAL_CANDIDATE_MANIFEST.candidates}

    assert by_name["current_engine_a_baseline"].role == "baseline"
    assert not by_name["current_engine_a_baseline"].promotion_eligible
    assert by_name["log_decay"].role == "control"
    assert not by_name["log_decay"].promotion_eligible


def test_manifest_includes_position_specific_candidate_priors():
    by_name = {candidate.name: candidate for candidate in DRAFT_CAPITAL_CANDIDATE_MANIFEST.candidates}
    bucketed = by_name["position_bucketed"]
    isotonic = by_name["position_isotonic_step"]

    assert bucketed.position_priors["QB"][0] == [1, 15]
    assert [33, 75] in bucketed.position_priors["WR"]
    assert [1, 32] in bucketed.position_priors["TE"]
    assert isotonic.fit_scope == "per_position"
    assert isotonic.learned_breakpoints


def test_manifest_requires_leave_one_class_out_and_rank_metrics():
    validation = DRAFT_CAPITAL_CANDIDATE_MANIFEST.validation_protocol

    assert validation.fold_strategy == "leave_one_draft_class_out"
    assert REQUIRED_PRIMARY_METRICS <= set(validation.primary_metrics)
    assert "bootstrap_ci" in validation.secondary_checks
    assert "pick_jitter_sensitivity" in validation.secondary_checks


def test_manifest_excludes_market_features_and_dvs():
    manifest = DRAFT_CAPITAL_CANDIDATE_MANIFEST

    assert "market_data" in manifest.prohibited_inputs
    assert "ktc" in manifest.prohibited_inputs
    assert "fantasycalc" in manifest.prohibited_inputs
    assert "dvs" in manifest.out_of_scope
    assert not manifest.allows_market_inputs


def test_manifest_serializes_to_json():
    payload = manifest_as_dict(DRAFT_CAPITAL_CANDIDATE_MANIFEST)
    restored = json.loads(json.dumps(payload))

    assert restored["phase"] == "13.2"
    assert restored["validation_protocol"]["fold_strategy"] == "leave_one_draft_class_out"
    assert restored["candidates"][0]["name"] == "current_engine_a_baseline"


def test_manifest_validation_rejects_missing_required_candidate():
    payload = manifest_as_dict(DRAFT_CAPITAL_CANDIDATE_MANIFEST)
    payload["candidates"] = [
        candidate for candidate in payload["candidates"]
        if candidate["name"] != "position_isotonic_step"
    ]

    errors = validate_draft_capital_manifest(payload)

    assert any("position_isotonic_step" in error for error in errors)
