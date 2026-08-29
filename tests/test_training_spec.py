"""DG-057 — TrainingSpec (§8.2): one hashed spec object.

TDD RED: fails until src/dynasty_genius/models/training_spec.py exists.

Covers:
1. The spec carries the nine §8.2 fields and hashes deterministically.
2. Changing any field changes the hash.
3. Hashing is insensitive to dict key insertion order (canonical JSON).
4. to_dict / from_dict round-trips to the same hash.
5. A missing required field is rejected at construction.
6. The hash is bare sha256 hex, matching the model_registry.json style.
"""

from __future__ import annotations

import re

import pytest


def _spec_kwargs(**overrides):
    """A complete, valid TrainingSpec field set (Engine A shaped)."""
    kwargs = dict(
        engine="engine_a",
        model_id="engine_a:WR",
        feature_set=("pick", "round", "age"),
        feature_set_version="v2",
        target="y24_ppg",
        label_horizon="second_nfl_season",
        cohort_filter="drafted_prospects_with_outcomes",
        preprocessing={"missing_data": "refuse_incomplete_rows", "scaling": "none"},
        estimator_family="ridge",
        tuning_policy={"alpha": "fixed", "search": "none"},
        time_split={"scheme": "draft_class_holdout", "grouping": "draft_class"},
        evaluation_baselines=("pick_only_linear", "positional_mean"),
        calibration_method="empirical_p90_ceiling",
    )
    kwargs.update(overrides)
    return kwargs


# ── 1. Deterministic hash ─────────────────────────────────────────────────────

def test_same_fields_same_hash():
    from src.dynasty_genius.models.training_spec import TrainingSpec

    a = TrainingSpec(**_spec_kwargs())
    b = TrainingSpec(**_spec_kwargs())
    assert a.spec_hash() == b.spec_hash()


def test_hash_is_bare_sha256_hex():
    from src.dynasty_genius.models.training_spec import TrainingSpec

    h = TrainingSpec(**_spec_kwargs()).spec_hash()
    assert re.fullmatch(r"[0-9a-f]{64}", h), h


# ── 2. Any field change changes the hash ─────────────────────────────────────

@pytest.mark.parametrize(
    "override",
    [
        {"feature_set": ("pick", "round", "age", "college_ppg")},
        {"feature_set_version": "v3"},
        {"target": "y25_ppg"},
        {"label_horizon": "third_nfl_season"},
        {"cohort_filter": "all_prospects"},
        {"preprocessing": {"missing_data": "impute_median", "scaling": "standard"}},
        {"estimator_family": "gradient_boosting"},
        {"tuning_policy": {"alpha": "grid", "search": "cv5"}},
        {"time_split": {"scheme": "walk_forward", "grouping": "season"}},
        {"evaluation_baselines": ("pick_only_linear",)},
        {"calibration_method": "isotonic"},
    ],
)
def test_any_field_change_changes_hash(override):
    from src.dynasty_genius.models.training_spec import TrainingSpec

    base = TrainingSpec(**_spec_kwargs())
    changed = TrainingSpec(**_spec_kwargs(**override))
    assert base.spec_hash() != changed.spec_hash(), override


# ── 3. Canonical JSON: dict key order is irrelevant ──────────────────────────

def test_dict_key_insertion_order_is_irrelevant():
    from src.dynasty_genius.models.training_spec import TrainingSpec

    a = TrainingSpec(
        **_spec_kwargs(
            preprocessing={"missing_data": "refuse_incomplete_rows", "scaling": "none"}
        )
    )
    b = TrainingSpec(
        **_spec_kwargs(
            preprocessing={"scaling": "none", "missing_data": "refuse_incomplete_rows"}
        )
    )
    assert a.spec_hash() == b.spec_hash()


# ── 4. Round-trip ────────────────────────────────────────────────────────────

def test_to_dict_from_dict_round_trip_preserves_hash():
    from src.dynasty_genius.models.training_spec import TrainingSpec

    original = TrainingSpec(**_spec_kwargs())
    rebuilt = TrainingSpec.from_dict(original.to_dict())
    assert rebuilt.spec_hash() == original.spec_hash()
    assert rebuilt.to_dict() == original.to_dict()


def test_from_dict_accepts_lists_for_tuple_fields():
    from src.dynasty_genius.models.training_spec import TrainingSpec

    d = TrainingSpec(**_spec_kwargs()).to_dict()
    assert isinstance(d["feature_set"], list)  # JSON has no tuples
    rebuilt = TrainingSpec.from_dict(d)
    assert rebuilt.feature_set == ("pick", "round", "age")


# ── 5. Missing required field refused ────────────────────────────────────────

def test_from_dict_missing_required_field_raises():
    from src.dynasty_genius.models.training_spec import TrainingSpec

    d = TrainingSpec(**_spec_kwargs()).to_dict()
    del d["target"]
    with pytest.raises(ValueError, match="target"):
        TrainingSpec.from_dict(d)


def test_from_dict_unknown_field_raises():
    from src.dynasty_genius.models.training_spec import TrainingSpec

    d = TrainingSpec(**_spec_kwargs()).to_dict()
    d["surprise"] = "field"
    with pytest.raises(ValueError, match="surprise"):
        TrainingSpec.from_dict(d)
