"""QB-1 F1-F34 RED contract.

These tests deliberately target the not-yet-built validation package.  They are
hermetic: no network, no external artifacts, and no gitignored paths are read.
Each row names one falsification seed from the frozen v8 specification and
asserts the corresponding public seam exists before GREEN implementation.
"""

from __future__ import annotations

import importlib

import pytest

ROWS = {
    "F1": "load_validation_sources",
    "F2": "build_registration",
    "F3": "build_study_matrix",
    "F4": "run_expanding_folds",
    "F5": "fit_ridge_lane",
    "F6": "score_comparisons",
    "F7": "require_registration_hash",
    "F8": "build_primary_comparisons",
    "F9": "scan_banned_language",
    "F10": "require_case_panel",
    "F11": "validate_label_table",
    "F12": "validate_age_features",
    "F13": "require_threshold_sensitivity",
    "F14": "validate_dataset_shape",
    "F15": "validate_manifest_columns",
    "F16": "validate_identity_duplicates",
    "F17": "validate_identity_overlap",
    "F18": "validate_join_coverage",
    "F19": "validate_as_of_dates",
    "F20": "validate_degenerate_inputs",
    "F21": "validate_scoring_edges",
    "F22": "fit_train_only_imputer",
    "F23": "reject_registration_drift",
    "F24": "validate_output_path",
    "F25": "validate_frozen_hashes",
    "F26": "validate_report_output",
    "F27": "validate_hypothesis_partition",
    "F28": "validate_attrition_classes",
    "F29": "validate_sensitivity_panel",
    "F30": "evaluate_power_and_status",
    "F31": "validate_artifact_tracking",
    "F32": "reconcile_identity_names",
    "F33": "enforce_consumer_boundary",
    "F34": "resolve_draft_join",
}

# Parked contract rows: seams whose implementing deliverable has not landed.
# Each is an expected failure with the SLICE DELIVERABLE that flips it named
# (CI-remedy Option 2, David-worded 2026-07-18). strict=True is the RED
# discipline: the moment a deliverable implements a seam, the row XPASSes and
# FAILS the suite until its marking is removed — parked can never rot into
# silently-green. Building a seam and un-marking its row happen in the SAME
# reviewed change.
PARKED_SEAMS = {
    "F3": "D2a study matrix",
    "F4": "D3 study machinery (expanding folds)",
    "F5": "D3 study machinery (Ridge lane)",
    "F6": "D3 study machinery (comparison scoring)",
    "F8": "D3 study machinery (primary comparison set)",
    "F10": "D5 report assembly (case panel)",
    "F12": "D3 study machinery (age/cohort features)",
    "F13": "D5 report assembly (threshold-sensitivity panel)",
    "F16": "D4 static identity join (duplicate/conflict semantics)",
    "F18": "D4 static identity join (coverage gate)",
    "F20": "D3 study machinery (degenerate-input closure)",
    "F22": "D3 study machinery (train-only imputer)",
    "F25": "D5 report assembly (frozen-boundary assertion)",
    "F27": "D3 study machinery (hypothesis manifest partition)",
    "F29": "D5 report assembly (sensitivity panel)",
    "F31": "D5 report assembly (artifact tracking)",
    "F32": "D4 static identity join (name reconciliation gate)",
    "F33": "the F33 consumer-boundary tripwire deliverable",
}

SEAM_PARAMS = [
    pytest.param(
        seed,
        symbol,
        id=f"{seed}-{symbol}",
        marks=pytest.mark.xfail(
            strict=True, reason=f"parked RED row: lands with {PARKED_SEAMS[seed]}"
        ),
    )
    if seed in PARKED_SEAMS
    else pytest.param(seed, symbol, id=f"{seed}-{symbol}")
    for seed, symbol in ROWS.items()
]


def _study_module():
    """Load the study package only; implementation is intentionally absent in RED."""
    return importlib.import_module("src.dynasty_genius.eval.qb_validation")


@pytest.mark.parametrize("seed,symbol", SEAM_PARAMS)
def test_falsification_seed_has_a_direct_hermetic_seam(seed: str, symbol: str) -> None:
    """Every registered RED row must have a callable implementation seam."""
    module = _study_module()
    assert callable(getattr(module, symbol)), f"{seed} seam missing: {symbol}"


def test_f1_source_failure_is_named_and_fail_closed() -> None:
    module = _study_module()
    with pytest.raises(Exception, match="source_unavailable|stale|fail_closed"):
        module.load_validation_sources({"weekly": {"status": "stale"}})


@pytest.mark.xfail(
    strict=True, reason="parked RED row: lands with D2a study matrix (build_study_matrix)"
)
def test_f2_fold_rejects_target_season_feature_leakage() -> None:
    module = _study_module()
    with pytest.raises(Exception, match="leak|as_of|target"):
        module.build_study_matrix(
            [{"target_season": 2025, "feature_season": 2025, "ppg": 10.0}]
        )


def test_f9_report_enforces_recursive_no_verdict_language() -> None:
    module = _study_module()
    with pytest.raises(Exception, match="banned|decision_supported|verdict"):
        module.scan_banned_language({"decision_supported": True, "support_status": "buy"})


@pytest.mark.parametrize("bad", [None, [], {"attempts": [1]}])
def test_f14_malformed_dataset_shape_fails_closed(bad) -> None:
    module = _study_module()
    with pytest.raises(Exception, match="shape|type|empty|column"):
        module.validate_dataset_shape(bad, dataset="weekly")


def test_f15_missing_manifest_column_has_named_reason() -> None:
    module = _study_module()
    with pytest.raises(Exception, match="manifest_column_missing"):
        module.validate_manifest_columns({"attempts": [1]}, required=["sacks_suffered"])


def test_f17_empty_identity_join_aborts_without_metrics() -> None:
    module = _study_module()
    with pytest.raises(Exception, match="identity_join_empty"):
        module.validate_identity_overlap([])


def test_f19_after_date_is_rejected() -> None:
    module = _study_module()
    with pytest.raises(Exception, match="as_of|after|date"):
        module.validate_as_of_dates(
            model_feature_date="2025-09-01", model_cutoff="2024-12-31",
            market_date="2025-09-01", market_cutoff="2025-09-01",
        )


def test_f24_output_override_is_refused() -> None:
    module = _study_module()
    with pytest.raises(Exception, match="output_path_violation|output path"):
        module.validate_output_path("/tmp/qb-validation-report.json")


def test_f26_negative_delta_is_not_clamped_and_report_is_no_verdict() -> None:
    # Fixture repaired 2026-07-17 (slice-2 review B6): D5 requires
    # decision_supported=False on the root AND every nested model, so the
    # comparison row carries it; a nested model MISSING the flag must refuse.
    module = _study_module()
    report = module.validate_report_output(
        {
            "decision_supported": False,
            "comparisons": [{"decision_supported": False, "pooled_delta": -0.25}],
        }
    )
    assert report["decision_supported"] is False
    assert report["comparisons"][0]["pooled_delta"] == -0.25
    with pytest.raises(Exception, match="decision_supported_missing_on_model"):
        module.validate_report_output(
            {"decision_supported": False, "comparisons": [{"pooled_delta": -0.25}]}
        )


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"folds": 2, "ci_excludes_zero": False}, "unsupported_power"),
        ({"folds": 8, "ci_excludes_zero": False}, "not_separable"),
        ({"folds": 8, "ci_excludes_zero": True, "direction": "wrong"}, "contradicted"),
    ],
)
def test_f30_forced_statuses_are_deterministic(payload, expected) -> None:
    module = _study_module()
    assert module.evaluate_power_and_status(payload)["support_status"] == expected


def test_f34_ambiguous_draft_fallback_is_triage_not_udfa() -> None:
    module = _study_module()
    result = module.resolve_draft_join(
        {"gsis_id": None, "name": "Example QB", "draft_season": 2022},
        [
            {"name": "Example QB", "season": 2022, "age": 21, "college": "A"},
            {"name": "Example QB", "season": 2022, "age": 21, "college": "B"},
        ],
    )
    assert result["resolution"] == "TRIAGE"


def test_f34_missing_identity_keys_triages_never_udfa() -> None:
    """Amendment A: an absent key cannot prove a drafted-list miss."""
    module = _study_module()
    result = module.resolve_draft_join(
        {"gsis_id": None, "display_name": None},
        [],
    )
    assert result["resolution"] == "TRIAGE"
    assert result["reason"] == "missing_identity_keys"
    assert "is_udfa" not in result
    assert "draft_round" not in result
    assert "draft_overall" not in result
