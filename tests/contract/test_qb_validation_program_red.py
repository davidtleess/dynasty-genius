"""QB-1 F1-F34 RED contract.

These tests deliberately target the not-yet-built validation package.  They are
hermetic: no network, no external artifacts, and no gitignored paths are read.
Each row names one falsification seed from the frozen v8 specification and
asserts the corresponding public seam exists before GREEN implementation.
"""

from __future__ import annotations

import copy
import importlib
import math

import pytest

from tests.contract.qb_validation_study_matrix_contract import exercise_s1_s34

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
    "F5": "D3 study machinery (Ridge lane)",
    "F6": "D3 study machinery (comparison scoring)",
    "F8": "D3 study machinery (primary comparison set)",
    "F10": "D5 report assembly (case panel)",
    "F13": "D5 report assembly (threshold-sensitivity panel)",
    "F16": "D4 static identity join (duplicate/conflict semantics)",
    "F18": "D4 static identity join (coverage gate)",
    "F25": "D5 report assembly (frozen-boundary assertion)",
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


def _failure_reason(exc_info: pytest.ExceptionInfo[BaseException]) -> str:
    """Read the machine reason without weakening a refusal to message matching."""
    reason = getattr(exc_info.value, "reason", None)
    assert isinstance(reason, str) and reason
    return reason


@pytest.mark.parametrize("seed,symbol", SEAM_PARAMS)
def test_falsification_seed_has_a_direct_hermetic_seam(seed: str, symbol: str) -> None:
    """Every registered RED row must have a callable implementation seam."""
    module = _study_module()
    assert callable(getattr(module, symbol)), f"{seed} seam missing: {symbol}"


def test_f1_source_failure_is_named_and_fail_closed() -> None:
    module = _study_module()
    with pytest.raises(Exception, match="source_unavailable|stale|fail_closed"):
        module.load_validation_sources({"weekly": {"status": "stale"}})


def test_f2_v9_d2a_behavioral_contract_s1_s34(tmp_path) -> None:
    """Ratified v9 D2a contract; one row preserves the 1F + 18XF ratchet."""
    module = _study_module()
    exercise_s1_s34(module, tmp_path)


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


def test_f4_expanding_fold_engine_is_exact_chronological_and_total() -> None:
    """D3-a F4: matrix-first fold engine, no estimator or scoring behavior."""
    module = _study_module()
    rows = [
        {
            "player_id": player_id,
            "target_season": season,
            "decision_supported": False,
        }
        for season in range(2016, 2026)
        for player_id in ("qb-a", "qb-b")
    ]
    study_matrix = {
        "matrix_version": "qb_validation_matrix.v1",
        "decision_supported": False,
        "matrix": rows,
    }
    before = copy.deepcopy(study_matrix)

    folds = module.run_expanding_folds(
        study_matrix,
        train_start_season=2016,
        test_seasons=tuple(range(2018, 2026)),
    )

    assert study_matrix == before, "fold construction must not mutate D2a output"
    assert [fold["test_season"] for fold in folds] == list(range(2018, 2026))
    for fold in folds:
        test_season = fold["test_season"]
        expected_train_seasons = list(range(2016, test_season))
        assert fold["train_seasons"] == expected_train_seasons
        assert {
            row["target_season"] for row in fold["train_rows"]
        } == set(expected_train_seasons)
        assert {
            row["target_season"] for row in fold["test_rows"]
        } == {test_season}
        assert not (
            {row["target_season"] for row in fold["train_rows"]}
            & {row["target_season"] for row in fold["test_rows"]}
        )
        assert len(fold["test_rows"]) == 2

    missing_2025 = copy.deepcopy(study_matrix)
    missing_2025["matrix"] = [
        row for row in missing_2025["matrix"] if row["target_season"] != 2025
    ]
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.run_expanding_folds(
            missing_2025,
            train_start_season=2016,
            test_seasons=tuple(range(2018, 2026)),
        )
    assert _failure_reason(exc_info) == "fold_test_empty"

    malformed = copy.deepcopy(study_matrix)
    malformed["matrix"][0]["target_season"] = "2016"
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.run_expanding_folds(
            malformed,
            train_start_season=2016,
            test_seasons=tuple(range(2018, 2026)),
        )
    assert _failure_reason(exc_info) == "fold_row_invalid"

    with pytest.raises(TypeError):
        module.run_expanding_folds(
            None,
            train_start_season=2016,
            test_seasons=tuple(range(2018, 2026)),
        )


def test_f12_age_feature_is_continuous_and_never_a_cohort_cliff() -> None:
    """D3-a F12: validate, but never bucket, clamp, or terminate, continuous age."""
    module = _study_module()
    rows = [
        {
            "player_id": f"qb-{index}",
            "target_season": 2025,
            "age_at_season_start": age,
        }
        for index, age in enumerate((29.0, 33.0, 36.0, 37.0, 40.0, 41.75, None))
    ]
    before = copy.deepcopy(rows)

    validated = module.validate_age_features(rows, cohort={"age_bound": None})

    assert validated == before
    assert rows == before, "age validation must not mutate, clamp, or terminal-zero rows"
    assert [
        row["age_at_season_start"] for row in validated
    ] == [29.0, 33.0, 36.0, 37.0, 40.0, 41.75, None]

    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.validate_age_features(rows, cohort={"age_bound": 40})
    assert _failure_reason(exc_info) == "age_cohort_cliff"

    for bad_age in (True, "40", -1.0, float("nan"), float("inf")):
        malformed = copy.deepcopy(rows)
        malformed[0]["age_at_season_start"] = bad_age
        with pytest.raises(module.QBValidationFailure) as exc_info:
            module.validate_age_features(malformed, cohort={"age_bound": None})
        assert _failure_reason(exc_info) == "age_feature_invalid"

    with pytest.raises(TypeError):
        module.validate_age_features(None, cohort={"age_bound": None})


def test_f20_degenerate_vectors_close_without_nan_or_partial_metric() -> None:
    """D3-a F20: empty/single/constant/all-null/ties are total named states."""
    module = _study_module()

    tied = module.validate_degenerate_inputs(
        predictions=[1.0, 1.0, 2.0, 3.0],
        labels=[4.0, 3.0, 3.0, 1.0],
    )
    assert tied == {
        "state": "degenerate_input",
        "reasons": ["mass_ties"],
        "metrics_allowed": True,
        "prediction_ranks": [1.5, 1.5, 3.0, 4.0],
        "label_ranks": [4.0, 2.5, 2.5, 1.0],
        "tie_counts": {"predictions": 1, "labels": 1},
    }

    forced_states = [
        ([], [], "empty_vectors"),
        ([1.0], [2.0], "single_observation"),
        ([1.0, 1.0], [1.0, 2.0], "constant_predictions"),
        ([1.0, 2.0], [3.0, 3.0], "constant_labels"),
        ([None, None], [1.0, 2.0], "all_null_predictions"),
        ([1.0, 2.0], [None, None], "all_null_labels"),
    ]
    for predictions, labels, reason in forced_states:
        result = module.validate_degenerate_inputs(predictions, labels)
        assert result["state"] == "degenerate_input"
        assert result["reasons"] == [reason]
        assert result["metrics_allowed"] is False
        assert "metric" not in result

    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.validate_degenerate_inputs([1.0, 2.0], [1.0])
    assert _failure_reason(exc_info) == "vector_length_mismatch"

    with pytest.raises(TypeError):
        module.validate_degenerate_inputs(None, [1.0])


def test_f22_imputer_learns_only_from_train_and_refuses_season_overlap() -> None:
    """D3-a F22: train median is auditable; test sentinels cannot move it."""
    module = _study_module()
    train_rows = [
        {
            "player_id": "train-a",
            "target_season": 2018,
            "x": 1.0,
            "y": None,
            "draft_round": None,
            "draft_overall": None,
            "is_udfa": None,
        },
        {
            "player_id": "train-b",
            "target_season": 2019,
            "x": None,
            "y": 10.0,
            "draft_round": 1.0,
            "draft_overall": 1.0,
            "is_udfa": 0.0,
        },
        {
            "player_id": "train-c",
            "target_season": 2019,
            "x": 3.0,
            "y": 20.0,
            "draft_round": 8.0,
            "draft_overall": 263.0,
            "is_udfa": 1.0,
        },
    ]
    test_rows = [
        {
            "player_id": "test-a",
            "target_season": 2020,
            "x": None,
            "y": None,
            "draft_round": None,
            "draft_overall": None,
            "is_udfa": None,
        },
        {
            "player_id": "test-sentinel",
            "target_season": 2020,
            "x": 10_000.0,
            "y": 20_000.0,
            "draft_round": 2.0,
            "draft_overall": 40.0,
            "is_udfa": 0.0,
        },
    ]
    train_before, test_before = copy.deepcopy(train_rows), copy.deepcopy(test_rows)
    features = ("x", "y", "draft_round", "draft_overall", "is_udfa")
    excluded = ("draft_round", "draft_overall", "is_udfa")

    result = module.fit_train_only_imputer(
        train_rows,
        test_rows,
        features=features,
        excluded_features=excluded,
    )

    assert train_rows == train_before and test_rows == test_before
    assert result["medians"] == {"x": 2.0, "y": 15.0}
    assert result["fit_target_seasons"] == [2018, 2019]
    assert result["train_rows"][1]["x"] == 2.0
    assert result["train_rows"][0]["y"] == 15.0
    assert result["test_rows"][0]["x"] == 2.0
    assert result["test_rows"][0]["y"] == 15.0
    assert result["test_rows"][1]["x"] == 10_000.0
    assert result["test_rows"][1]["y"] == 20_000.0
    assert result["test_rows"][0]["draft_round"] is None
    assert result["test_rows"][0]["draft_overall"] is None
    assert result["test_rows"][0]["is_udfa"] is None

    overlapping_test = copy.deepcopy(test_rows)
    overlapping_test[0]["target_season"] = 2019
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.fit_train_only_imputer(
            train_rows,
            overlapping_test,
            features=features,
            excluded_features=excluded,
        )
    assert _failure_reason(exc_info) == "target_season_overlap"

    with pytest.raises(TypeError):
        module.fit_train_only_imputer(
            None,
            test_rows,
            features=features,
            excluded_features=excluded,
        )


def test_f27_partition_consumes_d2a_manifests_and_refuses_any_drift() -> None:
    """D3-a F27: D2a owns declarations; D3 validates exact partition/composition."""
    module = _study_module()
    matrix_module = importlib.import_module(
        "src.dynasty_genius.eval.qb_validation.study_matrix"
    )
    manifests = {
        "h1": matrix_module.H1_MANIFEST,
        "h2": matrix_module.H2_MANIFEST,
        "h3": matrix_module.H3_MANIFEST,
        "h4": matrix_module.H4_MANIFEST,
    }

    assert module.validate_hypothesis_partition(manifests) == manifests

    overlap = copy.deepcopy(manifests)
    overlap["h2"] = (overlap["h1"][0],) + tuple(overlap["h2"][1:])
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.validate_hypothesis_partition(overlap)
    assert _failure_reason(exc_info) == "hypothesis_manifest_overlap"

    duplicate = copy.deepcopy(manifests)
    duplicate["h1"] = tuple(duplicate["h1"]) + (duplicate["h1"][0],)
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.validate_hypothesis_partition(duplicate)
    assert _failure_reason(exc_info) == "hypothesis_manifest_duplicate"

    for drifted_h4 in (
        tuple(manifests["h4"][:-1]),
        tuple(manifests["h4"]) + (("age_bucket_40", "static"),),
        tuple(manifests["h4"][:-1]) + (("is_udfa", "t-1"),),
    ):
        drift = copy.deepcopy(manifests)
        drift["h4"] = drifted_h4
        with pytest.raises(module.QBValidationFailure) as exc_info:
            module.validate_hypothesis_partition(drift)
        assert _failure_reason(exc_info) == "hypothesis_manifest_composition"

    with pytest.raises(TypeError):
        module.validate_hypothesis_partition(None)


def test_f4_each_fold_owns_independent_row_copies() -> None:
    """D3-a F4 (round-2 B2): folds must not share mutable row objects.

    A row that is test data in one fold is train data in a later fold; if folds
    share the same object, downstream in-place preparation contaminates other
    folds even though the source study matrix is untouched.
    """
    module = _study_module()
    rows = [
        {"player_id": player_id, "target_season": season, "decision_supported": False}
        for season in range(2016, 2026)
        for player_id in ("qb-a", "qb-b")
    ]
    study_matrix = {
        "matrix_version": "qb_validation_matrix.v1",
        "decision_supported": False,
        "matrix": rows,
    }
    folds = module.run_expanding_folds(
        study_matrix,
        train_start_season=2016,
        test_seasons=tuple(range(2018, 2026)),
    )

    # A 2016 row is train data in every fold; the objects must be distinct.
    assert folds[0]["train_rows"][0] is not folds[1]["train_rows"][0]

    folds[0]["train_rows"][0]["player_id"] = "MUTATED"
    assert all(
        row["player_id"] != "MUTATED"
        for fold in folds[1:]
        for row in fold["train_rows"]
    ), "mutating one fold's train row leaked into another fold"
    assert all(
        row["player_id"] != "MUTATED" for fold in folds for row in fold["test_rows"]
    ), "mutating one fold's train row leaked into a test fold"
    assert all(
        row["player_id"] != "MUTATED" for row in study_matrix["matrix"]
    ), "mutating a fold row leaked back into the source study matrix"


def test_f4_invalid_schedules_fail_closed() -> None:
    """D3-a F4 (round-2 B3): schedule semantics fail closed, no hardcoded tuple.

    Empty, duplicate/non-strictly-increasing, and any test season at or before
    train_start_season (an empty training window) must refuse — they cannot reach
    downstream machinery as ordinary evidence.
    """
    module = _study_module()
    rows = [
        {"player_id": player_id, "target_season": season, "decision_supported": False}
        for season in range(2016, 2026)
        for player_id in ("qb-a", "qb-b")
    ]
    study_matrix = {
        "matrix_version": "qb_validation_matrix.v1",
        "decision_supported": False,
        "matrix": rows,
    }

    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.run_expanding_folds(
            study_matrix, train_start_season=2016, test_seasons=()
        )
    assert _failure_reason(exc_info) == "fold_schedule_empty"

    for bad_seasons in ((2018, 2018), (2019, 2018, 2018), (2020, 2019)):
        with pytest.raises(module.QBValidationFailure) as exc_info:
            module.run_expanding_folds(
                study_matrix, train_start_season=2016, test_seasons=bad_seasons
            )
        assert _failure_reason(exc_info) == "fold_schedule_not_increasing"

    for train_start, test_seasons in ((2018, (2018,)), (2018, (2017,))):
        with pytest.raises(module.QBValidationFailure) as exc_info:
            module.run_expanding_folds(
                study_matrix,
                train_start_season=train_start,
                test_seasons=test_seasons,
            )
        assert _failure_reason(exc_info) == "fold_train_window_empty"


def test_f27_enforces_canonical_d2a_declarations_and_exact_keys() -> None:
    """D3-a F27 (round-2 B1): assert against D2a's module-owned declarations.

    Validating only the caller-internal relationship lets a coordinated H1+H4
    rewrite (relationship preserved) and undeclared manifest keys bypass the
    single-source-of-truth. F27 must equal the imported canonical manifests
    exactly and reject any key outside h1-h4.
    """
    module = _study_module()
    matrix_module = importlib.import_module(
        "src.dynasty_genius.eval.qb_validation.study_matrix"
    )
    manifests = {
        "h1": matrix_module.H1_MANIFEST,
        "h2": matrix_module.H2_MANIFEST,
        "h3": matrix_module.H3_MANIFEST,
        "h4": matrix_module.H4_MANIFEST,
    }

    new_first = ("market_signal", "t1")
    coordinated = copy.deepcopy(manifests)
    coordinated["h1"] = (new_first,) + tuple(manifests["h1"][1:])
    coordinated["h4"] = (new_first,) + tuple(manifests["h4"][1:])
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.validate_hypothesis_partition(coordinated)
    assert _failure_reason(exc_info) == "hypothesis_manifest_declaration_drift"

    extra = copy.deepcopy(manifests)
    extra["h5"] = (("market", "static"),)
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.validate_hypothesis_partition(extra)
    assert _failure_reason(exc_info) == "hypothesis_manifest_unexpected_key"


def test_f22_malformed_feature_declarations_raise_typeerror() -> None:
    """D3-a F22 (round-3 C1): feature/exclusion declarations are API inputs.

    A malformed declaration must fail loudly BEFORE any data processing. The
    load-bearing case: a string exclusion (``set('draft_round')`` = characters)
    leaves the draft-capital group imputable, which crosses F22's boundary that
    the draft-capital group is never median-imputed.
    """
    module = _study_module()
    train_rows = [
        {"player_id": "a", "target_season": 2018, "x": 1.0, "draft_round": 2.0},
        {"player_id": "b", "target_season": 2019, "x": 3.0, "draft_round": 4.0},
    ]
    test_rows = [
        {"player_id": "c", "target_season": 2020, "x": None, "draft_round": None},
    ]
    malformed = [
        ("x", ()),                              # features not a tuple
        (("x",), "x"),                          # excluded not a tuple
        (("x", "x"), ()),                       # duplicate features
        (("x",), ("typo",)),                    # excluded not a subset
        (("draft_round",), "draft_round"),      # string exclusion → draft-capital leak
    ]
    for features, excluded_features in malformed:
        with pytest.raises(TypeError):
            module.fit_train_only_imputer(
                train_rows,
                test_rows,
                features=features,
                excluded_features=excluded_features,
            )


def test_f4_empty_training_data_fails_closed() -> None:
    """D3-a F4 (round-3 C2): a schedule-valid fold with zero TRAIN rows refuses.

    No estimator can fit an empty training window; emitting it as ordinary fold
    evidence defers a known-corrupt state downstream.
    """
    module = _study_module()
    study_matrix = {
        "matrix_version": "qb_validation_matrix.v1",
        "decision_supported": False,
        "matrix": [
            {"player_id": "qb-a", "target_season": 2018, "decision_supported": False},
            {"player_id": "qb-b", "target_season": 2018, "decision_supported": False},
        ],
    }
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.run_expanding_folds(
            study_matrix, train_start_season=2016, test_seasons=(2018,)
        )
    assert _failure_reason(exc_info) == "fold_train_empty"


def test_f27_heterogeneous_unexpected_keys_are_named_not_typeerror() -> None:
    """D3-a F27 (round-3 C3): mixed-type extra keys get the named refusal.

    The mapping type is valid and its contents are corrupt, so a non-canonical key
    set must raise hypothesis_manifest_unexpected_key — never a bare TypeError from
    comparing unlike key types while formatting the detail.
    """
    module = _study_module()
    matrix_module = importlib.import_module(
        "src.dynasty_genius.eval.qb_validation.study_matrix"
    )
    manifests = {
        "h1": matrix_module.H1_MANIFEST,
        "h2": matrix_module.H2_MANIFEST,
        "h3": matrix_module.H3_MANIFEST,
        "h4": matrix_module.H4_MANIFEST,
        "h5": (("market", "static"),),
        1: (("mixed", "static"),),
    }
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.validate_hypothesis_partition(manifests)
    assert _failure_reason(exc_info) == "hypothesis_manifest_unexpected_key"


def test_f22_registered_draft_capital_must_be_excluded() -> None:
    """D3-a F22 (round-4 C4): the registered draft-capital group is never imputed.

    A well-typed but incomplete exclusion (empty, or missing one draft-capital
    field) must refuse before fitting — registration §8/§12 makes draft capital
    semantic, never median-imputable — rather than trust the caller's tuple to
    remember it. A feature set with no draft-capital field keeps ordinary empty
    exclusions.
    """
    module = _study_module()

    def _train_test(field: str):
        train = [
            {"player_id": "a", "target_season": 2018, field: 1.0},
            {"player_id": "b", "target_season": 2019, field: None},
        ]
        test = [{"player_id": "c", "target_season": 2020, field: None}]
        return train, test

    # Codex's exact failing input, plus each registered draft-capital field.
    for field in ("draft_round", "draft_overall", "is_udfa"):
        train, test = _train_test(field)
        with pytest.raises(module.QBValidationFailure) as exc_info:
            module.fit_train_only_imputer(
                train, test, features=(field,), excluded_features=()
            )
        assert _failure_reason(exc_info) == "draft_capital_not_excluded"

    # Partial exclusion: one draft-capital field excluded, another still exposed.
    train = [
        {"player_id": "a", "target_season": 2018, "draft_round": 1.0, "draft_overall": 5.0},
        {"player_id": "b", "target_season": 2019, "draft_round": None, "draft_overall": None},
    ]
    test = [{"player_id": "c", "target_season": 2020, "draft_round": None, "draft_overall": None}]
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.fit_train_only_imputer(
            train,
            test,
            features=("draft_round", "draft_overall"),
            excluded_features=("draft_round",),
        )
    assert _failure_reason(exc_info) == "draft_capital_not_excluded"

    # Preserve: a non-draft-capital feature with empty exclusion is fine.
    ok = module.fit_train_only_imputer(
        [
            {"player_id": "a", "target_season": 2018, "x": 1.0},
            {"player_id": "b", "target_season": 2019, "x": 3.0},
        ],
        [{"player_id": "c", "target_season": 2020, "x": None}],
        features=("x",),
        excluded_features=(),
    )
    assert ok["medians"] == {"x": 2.0}
    assert ok["test_rows"][0]["x"] == 2.0


def test_f22_numeric_edges_are_total_no_overflow_or_infinity() -> None:
    """D3-a F22 (round-4 C5): accepted numeric inputs never crash or fabricate inf.

    An int too large to convert to float is corrupt study data → named refusal, not
    a bare OverflowError. An even pair of finite values whose naive sum overflows
    must still yield a representable finite median, never inf.
    """
    module = _study_module()

    overflowing_int = 10**10000
    train = [
        {"player_id": "a", "target_season": 2018, "x": overflowing_int},
        {"player_id": "b", "target_season": 2019, "x": 1.0},
    ]
    test = [{"player_id": "c", "target_season": 2020, "x": None}]
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.fit_train_only_imputer(train, test, features=("x",), excluded_features=())
    assert _failure_reason(exc_info) == "imputer_value_invalid"

    train = [
        {"player_id": "a", "target_season": 2018, "x": 1e308},
        {"player_id": "b", "target_season": 2019, "x": 1e308},
    ]
    test = [{"player_id": "c", "target_season": 2020, "x": None}]
    result = module.fit_train_only_imputer(
        train, test, features=("x",), excluded_features=()
    )
    assert math.isfinite(result["medians"]["x"])
    assert result["medians"]["x"] == 1e308
    assert math.isfinite(result["test_rows"][0]["x"])
    assert result["test_rows"][0]["x"] == 1e308


def test_f22_only_draft_capital_may_be_excluded() -> None:
    """D3-a F22 (round-5 C6): only the registered draft-capital group is excludable.

    The inverse of C4: a caller must not silently exempt a registered H1/H2/H3/age
    feature (or any non-draft feature) from the pinned train-fitted median
    imputation by over-excluding it.
    """
    module = _study_module()
    for field in ("epa_per_dropback", "age_at_season_start", "x"):
        train = [
            {"player_id": "a", "target_season": 2018, field: 1.0},
            {"player_id": "b", "target_season": 2019, field: None},
        ]
        test = [{"player_id": "c", "target_season": 2020, field: None}]
        with pytest.raises(module.QBValidationFailure) as exc_info:
            module.fit_train_only_imputer(
                train, test, features=(field,), excluded_features=(field,)
            )
        assert _failure_reason(exc_info) == "non_draft_feature_excluded"

    # Preserve: exact draft exclusions for a mixed manifest still fit ordinary
    # features; an empty exclusion for a non-draft-only manifest already held (C4).
    ok = module.fit_train_only_imputer(
        [
            {"player_id": "a", "target_season": 2018, "x": 1.0,
             "draft_round": 2.0, "draft_overall": 5.0, "is_udfa": 0.0},
            {"player_id": "b", "target_season": 2019, "x": 3.0,
             "draft_round": None, "draft_overall": None, "is_udfa": None},
        ],
        [
            {"player_id": "c", "target_season": 2020, "x": None,
             "draft_round": None, "draft_overall": None, "is_udfa": None},
        ],
        features=("x", "draft_round", "draft_overall", "is_udfa"),
        excluded_features=("draft_round", "draft_overall", "is_udfa"),
    )
    assert ok["medians"] == {"x": 2.0}


def test_f22_subnormal_median_is_idempotent_and_endpoint_preserving() -> None:
    """D3-a F22 (round-5 C7): median(x, x) == x for min-subnormals, no underflow.

    The overflow-safe even median must not halve a minimum subnormal to zero.
    """
    module = _study_module()
    tiny = math.nextafter(0.0, math.inf)
    for value in (tiny, -tiny):
        train = [
            {"player_id": "a", "target_season": 2018, "x": value},
            {"player_id": "b", "target_season": 2019, "x": value},
        ]
        test = [{"player_id": "c", "target_season": 2020, "x": None}]
        result = module.fit_train_only_imputer(
            train, test, features=("x",), excluded_features=()
        )
        assert result["medians"]["x"] == value
        assert math.isfinite(result["medians"]["x"])
        assert result["test_rows"][0]["x"] == value

    # Preserve the C5 near-maximum pair fix.
    train = [
        {"player_id": "a", "target_season": 2018, "x": 1e308},
        {"player_id": "b", "target_season": 2019, "x": 1e308},
    ]
    test = [{"player_id": "c", "target_season": 2020, "x": None}]
    result = module.fit_train_only_imputer(
        train, test, features=("x",), excluded_features=()
    )
    assert result["medians"]["x"] == 1e308


def test_f4_extreme_season_spans_fail_closed() -> None:
    """D3-a F4 (round-5 C8): an unbounded season span never materializes a range.

    Type-correct but astronomical seasons pass the int/chronological checks; the
    eager range construction then crosses Python's sequence-length boundary
    (OverflowError / OOM). The span must be bounded before the range is built.
    """
    module = _study_module()
    huge = 10**100
    study_matrix = {
        "matrix_version": "qb_validation_matrix.v1",
        "decision_supported": False,
        "matrix": [
            {"player_id": "qb-a", "target_season": 2018, "decision_supported": False},
            {"player_id": "qb-b", "target_season": 2018, "decision_supported": False},
        ],
    }
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.run_expanding_folds(
            study_matrix, train_start_season=2016, test_seasons=(huge,)
        )
    assert _failure_reason(exc_info) == "fold_season_out_of_range"

    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.run_expanding_folds(
            study_matrix, train_start_season=-huge, test_seasons=(2018,)
        )
    assert _failure_reason(exc_info) == "fold_season_out_of_range"


class _RaisingRepr:
    """An object whose repr raises an ordinary exception — a hostile diagnostic value."""

    def __repr__(self) -> str:
        raise RuntimeError("repr exploded")


def _canonical_manifests(module_matrix):
    return {
        "h1": module_matrix.H1_MANIFEST,
        "h2": module_matrix.H2_MANIFEST,
        "h3": module_matrix.H3_MANIFEST,
        "h4": module_matrix.H4_MANIFEST,
    }


def test_all_seam_refusals_are_total_over_hostile_values() -> None:
    """D3-a (round-5 C9): no refusal/API diagnostic may crash rendering a value.

    Across all five seams, a huge int or an object whose __repr__ raises must still
    reach the intended named QBValidationFailure reason (or the intended API
    TypeError) with a bounded detail — never a bare rendering crash.
    """
    module = _study_module()
    matrix_module = importlib.import_module(
        "src.dynasty_genius.eval.qb_validation.study_matrix"
    )
    huge = 10**10000
    bad = _RaisingRepr()

    def _matrix(rows):
        return {
            "matrix_version": "qb_validation_matrix.v1",
            "decision_supported": False,
            "matrix": rows,
        }

    # (label, thunk, expected_exception, expected_reason_or_None)
    cases = [
        (
            "F4 huge test season",
            lambda: module.run_expanding_folds(
                _matrix([{"player_id": "a", "target_season": 2018}]),
                train_start_season=2016,
                test_seasons=(huge,),
            ),
            module.QBValidationFailure,
            "fold_season_out_of_range",
        ),
        (
            "F4 bad row season",
            lambda: module.run_expanding_folds(
                _matrix([{"player_id": "a", "target_season": bad}]),
                train_start_season=2016,
                test_seasons=(2018,),
            ),
            module.QBValidationFailure,
            "fold_row_invalid",
        ),
        (
            "F12 huge cohort bound",
            lambda: module.validate_age_features(
                [{"player_id": "a", "target_season": 2025, "age_at_season_start": 25.0}],
                cohort={"age_bound": huge},
            ),
            module.QBValidationFailure,
            "age_cohort_cliff",
        ),
        (
            "F12 bad age value",
            lambda: module.validate_age_features(
                [{"player_id": "a", "target_season": 2025, "age_at_season_start": bad}],
                cohort={"age_bound": None},
            ),
            module.QBValidationFailure,
            "age_feature_invalid",
        ),
        (
            "F20 huge element",
            lambda: module.validate_degenerate_inputs(
                [huge, 1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0]
            ),
            module.QBValidationFailure,
            "vector_element_invalid",
        ),
        (
            "F20 bad element",
            lambda: module.validate_degenerate_inputs(
                [bad, 1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0]
            ),
            module.QBValidationFailure,
            "vector_element_invalid",
        ),
        (
            "F22 huge feature entry",
            lambda: module.fit_train_only_imputer(
                [{"player_id": "a", "target_season": 2018}],
                [{"player_id": "b", "target_season": 2019}],
                features=(huge,),
                excluded_features=(),
            ),
            TypeError,
            None,
        ),
        (
            "F22 huge overlap season",
            lambda: module.fit_train_only_imputer(
                [{"player_id": "a", "target_season": huge, "x": 1.0}],
                [{"player_id": "b", "target_season": huge, "x": None}],
                features=("x",),
                excluded_features=(),
            ),
            module.QBValidationFailure,
            "target_season_overlap",
        ),
        (
            "F22 bad value",
            lambda: module.fit_train_only_imputer(
                [{"player_id": "a", "target_season": 2018, "x": bad}],
                [{"player_id": "b", "target_season": 2019, "x": None}],
                features=("x",),
                excluded_features=(),
            ),
            module.QBValidationFailure,
            "imputer_value_invalid",
        ),
        (
            "F27 huge extra key",
            lambda: module.validate_hypothesis_partition(
                {**_canonical_manifests(matrix_module), huge: (("m", "static"),)}
            ),
            module.QBValidationFailure,
            "hypothesis_manifest_unexpected_key",
        ),
        (
            "F27 bad extra key",
            lambda: module.validate_hypothesis_partition(
                {**_canonical_manifests(matrix_module), bad: (("m", "static"),)}
            ),
            module.QBValidationFailure,
            "hypothesis_manifest_unexpected_key",
        ),
        (
            "F27 malformed entry",
            lambda: module.validate_hypothesis_partition(
                {**_canonical_manifests(matrix_module), "h1": ((huge,),)}
            ),
            module.QBValidationFailure,
            "hypothesis_manifest_entry_invalid",
        ),
    ]
    for label, thunk, exception, reason in cases:
        with pytest.raises(exception) as exc_info:
            thunk()
        if reason is not None:
            assert exc_info.value.reason == reason, label
        # Bounded detail: a rendered full huge int would blow past this.
        assert len(str(exc_info.value)) < 500, label


class _RaisingReprStr(str):
    """A str subclass whose repr AND str raise — 'validated string' with teeth."""

    def __repr__(self) -> str:
        raise RuntimeError("repr exploded")

    def __str__(self) -> str:
        raise RuntimeError("str exploded")


def test_string_subclass_names_reach_a_bounded_boundary_refusal() -> None:
    """D3-a (round-6 C10): a str subclass cannot smuggle hostile rendering behavior
    past declaration/manifest validation into a raw refusal-detail site.

    Plain-string validation (``type(x) is str``) rejects the subclass at the
    API/entry boundary — whose detail already routes through ``_safe_repr`` — so no
    downstream ``feature``/``name`` rendering site can ever receive it.
    """
    module = _study_module()
    matrix_module = importlib.import_module(
        "src.dynasty_genius.eval.qb_validation.study_matrix"
    )
    bad = _RaisingReprStr("x")
    train = [{"player_id": "a", "target_season": 2018, "x": None}]
    test = [{"player_id": "b", "target_season": 2019, "x": None}]

    # F22 all-null median path — hostile feature name in `features`.
    with pytest.raises(TypeError) as exc_info:
        module.fit_train_only_imputer(
            train, test, features=(bad,), excluded_features=()
        )
    assert len(str(exc_info.value)) < 500

    # F22 non-draft over-exclusion — hostile name in both features and excluded.
    with pytest.raises(TypeError) as exc_info:
        module.fit_train_only_imputer(
            train, test, features=(bad,), excluded_features=(bad,)
        )
    assert len(str(exc_info.value)) < 500

    # F22 invalid value under a hostile feature name.
    with pytest.raises(TypeError) as exc_info:
        module.fit_train_only_imputer(
            [{"player_id": "a", "target_season": 2018, "x": "notanumber"}],
            test,
            features=(bad,),
            excluded_features=(),
        )
    assert len(str(exc_info.value)) < 500

    # F27 overlap path — hostile feature name in a manifest pair.
    h1 = ((bad, "t1"),)
    h2 = ((bad, "t1"),)
    h3 = ()
    h4 = h1 + h2 + h3 + matrix_module._IDENTITY_GROUPS
    with pytest.raises(module.QBValidationFailure) as exc_info:
        module.validate_hypothesis_partition(
            {"h1": h1, "h2": h2, "h3": h3, "h4": h4}
        )
    assert _failure_reason(exc_info) == "hypothesis_manifest_entry_invalid"
    assert len(str(exc_info.value)) < 500
