"""D3-a — expanding-fold construction and the train-safe preparation guards.

Contract of record: frozen spec v9 (SHA-256 347c2d6e30d2…) + the ratified
computability amendment (SHA-256 b7221a7a8b69…). This module is the layer that
runs BEFORE any estimator (F5, D3-b) or comparison scoring (F6, D3-c): it splits
the D2a study matrix into an exact chronological expanding-window cross-validation
schedule, validates the study-design partition and the continuity of the age
feature, and prepares each fold's inputs so no test-fold signal can leak into a
fit.

Five seams live here, all pinned by ``tests/contract/test_qb_validation_program_red.py``:

- F4  ``run_expanding_folds``      — deterministic expanding-window fold schedule.
- F12 ``validate_age_features``    — age stays a continuous feature; never a cliff.
- F20 ``validate_degenerate_inputs`` — total named states for un-scorable vectors.
- F22 ``fit_train_only_imputer``   — medians learned from train seasons only.
- F27 ``validate_hypothesis_partition`` — H1/H2/H3 disjoint, H4 = their composition.

Fail-closed law (§D5): every refusal on malformed/corrupt study data raises
``QBValidationFailure`` with a NAMED machine reason; a wrong-call API misuse
(non-collection where a collection is required) raises ``TypeError`` loudly. No
function fabricates a metric or a NaN in place of a refusal, and none mutates its
inputs — the D2a output and the caller's rows are always left untouched.

H2 note: rushing production is a hypothesis UNDER TEST. Nothing here asserts it,
weights it, or treats it as established; H2 features are validated for partition
membership only, exactly as H1 and H3 are.
"""
from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure
from src.dynasty_genius.eval.qb_validation.study_matrix import (
    _IDENTITY_GROUPS,
    H1_MANIFEST,
    H2_MANIFEST,
    H3_MANIFEST,
    H4_MANIFEST,
)

# Registration §8/§12: the draft-capital group is SEMANTIC and is never
# median-imputed; missingness is resolved upstream. These are three of the D2a
# module-owned identity groups (the fourth, age_at_season_start, is not draft
# capital). F22 enforces the invariant structurally — it does not trust a
# caller-supplied exclusion tuple to remember it.
_DRAFT_CAPITAL_FEATURES = ("draft_round", "draft_overall", "is_udfa")

# A season is a calendar year; values outside a generous plausible-year window are
# invalid AND, left unchecked, would make range() materialize an astronomically
# large list (OverflowError / OOM). This is a resource-safety domain bound, not the
# sealed study season tuple — it constrains the fold-schedule span before the range
# is built without pinning which seasons the study uses.
_MIN_SEASON = 1900
_MAX_SEASON = 2200


def _refuse(reason: str, detail: str) -> None:
    raise QBValidationFailure(reason, detail)


def _safe_repr(value: Any) -> str:
    """A bounded, exception-safe repr for any external value in a diagnostic.

    A corrupt study value must never crash the very refusal that reports it: a huge
    int hits CPython's int→str digit limit, and a user-defined ``__repr__`` can
    raise an arbitrary ``Exception``. Both are caught and rendered as a bounded
    placeholder. Only ordinary ``Exception`` is caught — ``BaseException``
    control-flow signals (KeyboardInterrupt, SystemExit) still propagate.
    """
    try:
        text = repr(value)
    except Exception:
        return f"<unrepr-able {type(value).__name__}>"
    return text if len(text) <= 80 else f"{text[:77]}..."


def _is_finite_real(value: Any) -> bool:
    """True for a non-bool real that is finite AND representable as a float.

    False for bool, str, NaN, inf, None, and an int so large it cannot convert to
    a finite float (e.g. ``10**10000``) — such a value is corrupt study data, not a
    usable numeric, and must not reach ``_median``'s ``float()`` as a bare crash.
    """
    if type(value) is bool:
        return False
    if isinstance(value, int):
        try:
            return math.isfinite(float(value))
        except OverflowError:
            return False
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _is_int_season(value: Any) -> bool:
    """A season is a plain int; bool is not a season even though it subclasses int."""
    return type(value) is int


def _median(values: list[float]) -> float:
    """Median of a non-empty numeric list, total over finite float-representable input.

    The even case prefers the exact ``(a + b)/2`` — which preserves idempotence for
    minimum subnormals, where ``a/2`` would underflow to zero — and only falls back
    to the overflow-safe ``a/2 + b/2`` when the sum is non-finite (near-maximum
    pairs). Either way the result stays within ``[min, max]`` and finite. Inputs are
    already gated to finite float-representable reals by ``_is_finite_real``
    upstream, so ``float()`` cannot raise here.
    """
    ordered = sorted(float(v) for v in values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    low, high = ordered[mid - 1], ordered[mid]
    total = low + high
    if math.isfinite(total):
        return total / 2.0
    return low / 2.0 + high / 2.0


def _average_ranks(values: list[float]) -> tuple[list[float], int]:
    """Ascending fractional (average) ranks, plus the count of tied value-groups.

    Smallest value earns rank 1. Tied values share the average of the ranks their
    positions would occupy. The tie-group count is the number of distinct values
    that appear more than once.
    """
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    tie_groups = 0
    i = 0
    n = len(order)
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = average
        if j > i:
            tie_groups += 1
        i = j + 1
    return ranks, tie_groups


def _validate_feature_declaration(value: Any, name: str) -> None:
    """A feature/exclusion declaration is a tuple of unique, non-empty strings.

    These are API inputs, not study data, so a malformed shape or content is a
    loud ``TypeError`` (§8 robustness boundary) — never a silent character-iterable
    that could, e.g., leave the draft-capital group imputable.
    """
    if not isinstance(value, tuple):
        raise TypeError(
            f"{name} must be a tuple of feature-name strings, got {type(value).__name__}"
        )
    for entry in value:
        # Plain strings only: a str subclass is an external object that may override
        # __repr__/__str__/__hash__/__eq__, so it is rejected here (its bounded
        # refusal detail routes through _safe_repr) rather than reaching a raw
        # downstream rendering site.
        if type(entry) is not str or not entry:
            raise TypeError(
                f"{name} entries must be non-empty strings; got {_safe_repr(entry)}"
            )
    if len(value) != len(set(value)):
        raise TypeError(f"{name} must not contain duplicate feature names")


# --------------------------------------------------------------------------- #
# F4 — expanding-window fold schedule
# --------------------------------------------------------------------------- #
def run_expanding_folds(
    study_matrix: Mapping[str, Any],
    *,
    train_start_season: int,
    test_seasons: tuple[int, ...],
) -> list[dict[str, Any]]:
    """Build an exact chronological expanding-window fold schedule from D2a output.

    For each ``test_season`` (in the given order) the training window is the full
    contiguous span ``[train_start_season, test_season)`` and the test window is
    exactly that one season. The schedule must be non-empty, strictly increasing,
    and start strictly after ``train_start_season`` (no empty training window) — an
    invalid schedule is a fail-closed refusal, so it can never reach downstream
    machinery as ordinary evidence. Schedule semantics are enforced structurally,
    not by hardcoding the sealed season tuple. The D2a study matrix is never
    mutated, and every fold owns independent deep copies of its rows so in-place
    preparation in one fold cannot contaminate another. A scheduled season with no
    rows, or a row whose ``target_season`` is not a plain int, is refused.
    """
    if not isinstance(study_matrix, Mapping):
        raise TypeError(
            "run_expanding_folds requires the D2a study-matrix mapping, "
            f"got {type(study_matrix).__name__}"
        )
    if not _is_int_season(train_start_season):
        raise TypeError("train_start_season must be an int season")
    try:
        requested_seasons = list(test_seasons)
    except TypeError as exc:
        raise TypeError("test_seasons must be an iterable of int seasons") from exc
    for season in requested_seasons:
        if not _is_int_season(season):
            raise TypeError("test_seasons must contain only int seasons")

    if not requested_seasons:
        _refuse(
            "fold_schedule_empty",
            "test_seasons is empty; an expanding schedule needs at least one season",
        )
    # Bound the season domain BEFORE any range() is materialized: a type-correct but
    # astronomical season would otherwise crash on eager range construction / OOM.
    for season in (train_start_season, *requested_seasons):
        if not _MIN_SEASON <= season <= _MAX_SEASON:
            _refuse(
                "fold_season_out_of_range",
                f"season {_safe_repr(season)} is outside the plausible window "
                f"[{_MIN_SEASON}, {_MAX_SEASON}]; the fold-schedule span must be bounded",
            )
    for earlier, later in zip(requested_seasons, requested_seasons[1:]):
        if later <= earlier:
            _refuse(
                "fold_schedule_not_increasing",
                f"test_seasons must strictly increase; {later} does not follow {earlier}",
            )
    for season in requested_seasons:
        if season <= train_start_season:
            _refuse(
                "fold_train_window_empty",
                f"test season {season} is not after train_start_season "
                f"{train_start_season}; the training window would be empty",
            )

    matrix = study_matrix.get("matrix")
    if not isinstance(matrix, list):
        _refuse(
            "fold_matrix_invalid",
            f"study_matrix['matrix'] must be a list, got {type(matrix).__name__}",
        )

    # Read-only validation against the source rows; never mutated here.
    for index, row in enumerate(matrix):
        if not isinstance(row, Mapping):
            _refuse("fold_row_invalid", f"matrix row [{index}] is not a mapping")
        if not _is_int_season(row.get("target_season")):
            _refuse(
                "fold_row_invalid",
                f"matrix row [{index}] target_season="
                f"{_safe_repr(row.get('target_season'))} is not an int season",
            )

    folds: list[dict[str, Any]] = []
    for test_season in requested_seasons:
        train_seasons = list(range(train_start_season, test_season))
        train_set = set(train_seasons)
        # Deep-copy per fold: a row that is test data in one fold is train data in
        # a later fold, so folds must not share row objects.
        train_rows = copy.deepcopy(
            [row for row in matrix if row["target_season"] in train_set]
        )
        test_rows = copy.deepcopy(
            [row for row in matrix if row["target_season"] == test_season]
        )
        if not test_rows:
            _refuse(
                "fold_test_empty",
                f"test season {test_season} has no rows in the study matrix",
            )
        if not train_rows:
            _refuse(
                "fold_train_empty",
                f"test season {test_season} has no training rows in "
                f"seasons {train_seasons}; no estimator can fit this fold",
            )
        folds.append(
            {
                "test_season": test_season,
                "train_seasons": train_seasons,
                "train_rows": train_rows,
                "test_rows": test_rows,
            }
        )
    return folds


# --------------------------------------------------------------------------- #
# F12 — continuous age feature (never a cohort cliff)
# --------------------------------------------------------------------------- #
def validate_age_features(
    rows: list[Mapping[str, Any]],
    *,
    cohort: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Validate ``age_at_season_start`` as a continuous feature and return it unchanged.

    A non-null age must be a finite, positive real; ``None`` is a permitted missing
    value carried through untouched. A cohort that declares a hard ``age_bound`` is
    a binary age cliff — forbidden by the constitution's continuous-aging rule — and
    is refused. Ages are never bucketed, clamped, or terminal-zeroed; the input rows
    are not mutated.
    """
    if not isinstance(rows, list):
        raise TypeError(
            f"validate_age_features requires a list of rows, got {type(rows).__name__}"
        )
    if not isinstance(cohort, Mapping):
        raise TypeError("cohort must be a mapping")

    if cohort.get("age_bound") is not None:
        _refuse(
            "age_cohort_cliff",
            f"cohort age_bound={_safe_repr(cohort.get('age_bound'))} "
            "imposes a hard age cliff; "
            "age is a continuous feature and must not be bounded",
        )

    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            _refuse("age_feature_invalid", f"row [{index}] is not a mapping")
        age = row.get("age_at_season_start")
        if age is None:
            continue
        if type(age) is bool or not _is_finite_real(age) or age <= 0:
            _refuse(
                "age_feature_invalid",
                f"row [{index}] age_at_season_start={_safe_repr(age)} "
                "is not a positive finite age",
            )
    return copy.deepcopy(rows)


# --------------------------------------------------------------------------- #
# F20 — degenerate-input closure (total named states, no fabricated metric)
# --------------------------------------------------------------------------- #
def _degenerate(reason: str) -> dict[str, Any]:
    return {"state": "degenerate_input", "reasons": [reason], "metrics_allowed": False}


def validate_degenerate_inputs(
    predictions: list[Any],
    labels: list[Any],
) -> dict[str, Any]:
    """Classify a (predictions, labels) pair into a total, named degeneracy state.

    Empty, single-observation, all-null, partial-null, and constant vectors are
    un-scorable: each returns ``metrics_allowed=False`` with exactly one named
    reason and no fabricated metric. Mass ties are scorable — rank correlation is
    still defined — so they return ``metrics_allowed=True`` with the ascending
    average ranks and the per-vector tie-group counts. A length mismatch is a
    fail-closed refusal; a non-list argument is a loud ``TypeError``.
    """
    if not isinstance(predictions, list) or not isinstance(labels, list):
        raise TypeError("predictions and labels must be lists")
    if len(predictions) != len(labels):
        _refuse(
            "vector_length_mismatch",
            f"predictions has {len(predictions)} entries, labels has {len(labels)}",
        )
    for name, vector in (("predictions", predictions), ("labels", labels)):
        for index, value in enumerate(vector):
            if value is not None and not _is_finite_real(value):
                _refuse(
                    "vector_element_invalid",
                    f"{name}[{index}]={_safe_repr(value)} is not a finite real or null",
                )

    n = len(predictions)
    if n == 0:
        return _degenerate("empty_vectors")
    if n == 1:
        return _degenerate("single_observation")

    pred_present = [value for value in predictions if value is not None]
    label_present = [value for value in labels if value is not None]
    if not pred_present:
        return _degenerate("all_null_predictions")
    if not label_present:
        return _degenerate("all_null_labels")
    if len(pred_present) != n:
        return _degenerate("partial_null_predictions")
    if len(label_present) != n:
        return _degenerate("partial_null_labels")
    if len(set(predictions)) == 1:
        return _degenerate("constant_predictions")
    if len(set(labels)) == 1:
        return _degenerate("constant_labels")

    prediction_ranks, prediction_ties = _average_ranks(predictions)
    label_ranks, label_ties = _average_ranks(labels)
    has_ties = bool(prediction_ties or label_ties)
    return {
        "state": "degenerate_input" if has_ties else "ok",
        "reasons": ["mass_ties"] if has_ties else [],
        "metrics_allowed": True,
        "prediction_ranks": prediction_ranks,
        "label_ranks": label_ranks,
        "tie_counts": {"predictions": prediction_ties, "labels": label_ties},
    }


# --------------------------------------------------------------------------- #
# F22 — train-only median imputer (no test-fold leakage)
# --------------------------------------------------------------------------- #
def fit_train_only_imputer(
    train_rows: list[Mapping[str, Any]],
    test_rows: list[Mapping[str, Any]],
    *,
    features: tuple[str, ...],
    excluded_features: tuple[str, ...],
) -> dict[str, Any]:
    """Impute missing feature values using medians learned from the TRAIN rows only.

    Medians are computed over non-null train values for every feature that is not
    excluded; excluded features (identity/draft-capital columns) are never imputed
    and are carried through as-is. Test-row values — including out-of-range
    sentinels — never enter the median fit, proving the train/test wall. The train
    and test seasons must be disjoint or the fit is refused. Inputs are not mutated;
    the returned rows are independent, imputed copies.
    """
    if not isinstance(train_rows, list) or not isinstance(test_rows, list):
        raise TypeError("train_rows and test_rows must be lists")

    _validate_feature_declaration(features, "features")
    _validate_feature_declaration(excluded_features, "excluded_features")
    if not set(excluded_features) <= set(features):
        raise TypeError("excluded_features must be a subset of features")

    unexcluded_capital = [
        feature
        for feature in _DRAFT_CAPITAL_FEATURES
        if feature in features and feature not in set(excluded_features)
    ]
    if unexcluded_capital:
        _refuse(
            "draft_capital_not_excluded",
            f"registered draft-capital features {unexcluded_capital} are in "
            "`features` but not `excluded_features`; the draft-capital group is "
            "semantic and is never median-imputed (registration §8/§12)",
        )
    non_draft_excluded = [
        feature for feature in excluded_features
        if feature not in _DRAFT_CAPITAL_FEATURES
    ]
    if non_draft_excluded:
        _refuse(
            "non_draft_feature_excluded",
            f"features {non_draft_excluded} are excluded but are not the registered "
            "draft-capital group; every non-draft feature is train-fitted "
            "median-imputed and cannot be exempted (registration §8/§12)",
        )

    excluded = set(excluded_features)
    imputable = [feature for feature in features if feature not in excluded]

    train = copy.deepcopy(train_rows)
    test = copy.deepcopy(test_rows)

    def _seasons(rows: list[dict[str, Any]], where: str) -> list[int]:
        seasons: list[int] = []
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                _refuse("imputer_row_invalid", f"{where} row [{index}] is not a mapping")
            season = row.get("target_season")
            if not _is_int_season(season):
                _refuse(
                    "imputer_row_invalid",
                    f"{where} row [{index}] target_season={_safe_repr(season)} "
                    "is not an int season",
                )
            seasons.append(season)
        return seasons

    train_seasons = _seasons(train, "train")
    test_seasons = _seasons(test, "test")
    overlap = set(train_seasons) & set(test_seasons)
    if overlap:
        _refuse(
            "target_season_overlap",
            "train and test share target seasons "
            f"{sorted(_safe_repr(season) for season in overlap)}",
        )

    for where, rows in (("train", train), ("test", test)):
        for index, row in enumerate(rows):
            for feature in features:
                value = row.get(feature)
                if value is not None and not _is_finite_real(value):
                    _refuse(
                        "imputer_value_invalid",
                        f"{where} row [{index}] {feature}={_safe_repr(value)} "
                        "is not a finite real or null",
                    )

    medians: dict[str, float] = {}
    for feature in imputable:
        present = [row[feature] for row in train if row.get(feature) is not None]
        if not present:
            _refuse(
                "imputer_train_all_null",
                f"feature {feature!r} has no non-null train value to fit a median",
            )
        medians[feature] = _median(present)

    for row in (*train, *test):
        for feature in imputable:
            if row.get(feature) is None:
                row[feature] = medians[feature]

    return {
        "medians": medians,
        "fit_target_seasons": sorted(set(train_seasons)),
        "train_rows": train,
        "test_rows": test,
    }


# --------------------------------------------------------------------------- #
# F27 — hypothesis-manifest partition (D2a declares, D3 validates)
# --------------------------------------------------------------------------- #
def _validated_manifest(value: Any, key: str) -> tuple[tuple[str, str], ...]:
    """Normalize one manifest to a tuple of (name, timeframe) string pairs."""
    if not isinstance(value, (tuple, list)):
        _refuse("hypothesis_manifest_entry_invalid", f"{key} is not a sequence")
    normalized: list[tuple[str, str]] = []
    for index, entry in enumerate(value):
        # Plain strings only for the (name, timeframe) pair — a str subclass is an
        # external object with overridable rendering/hashing and is rejected here.
        if (
            not isinstance(entry, (tuple, list))
            or len(entry) != 2
            or type(entry[0]) is not str
            or type(entry[1]) is not str
        ):
            _refuse(
                "hypothesis_manifest_entry_invalid",
                f"{key}[{index}]={_safe_repr(entry)} is not a (name, timeframe) pair",
            )
        normalized.append((entry[0], entry[1]))
    return tuple(normalized)


def validate_hypothesis_partition(manifests: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate the H1/H2/H3/H4 partition D2a declares, refusing any drift.

    H1, H2, and H3 must each be duplicate-free and pairwise disjoint by feature
    name. H4 must be exactly ``H1 + H2 + H3`` followed by the module-owned identity
    block (age/draft-capital groups), so any dropped, added, or timeframe-shifted
    feature is caught. Because the declarations are owned by ``study_matrix``
    (§B7 single source of truth), this seam consumes them by import and asserts the
    passed manifests carry EXACTLY the keys ``h1``-``h4`` and equal the canonical
    D2a objects — the relationship checks alone would accept a coordinated caller
    rewrite or an extra lane. Returns the input unchanged when valid.
    """
    if not isinstance(manifests, Mapping):
        raise TypeError(
            f"validate_hypothesis_partition requires a mapping, "
            f"got {type(manifests).__name__}"
        )
    for key in ("h1", "h2", "h3", "h4"):
        if key not in manifests:
            _refuse("hypothesis_manifest_incomplete", f"missing manifest {key!r}")
    extra_keys = set(manifests) - {"h1", "h2", "h3", "h4"}
    if extra_keys:
        # Sort safe reprs, never the raw keys — a mapping may carry mixed-type
        # keys, and comparing unlike types would crash the refusal itself.
        _refuse(
            "hypothesis_manifest_unexpected_key",
            f"undeclared manifest keys {sorted(_safe_repr(key) for key in extra_keys)}; "
            "only h1-h4 are declared",
        )

    groups = {key: _validated_manifest(manifests[key], key) for key in ("h1", "h2", "h3", "h4")}

    for key in ("h1", "h2", "h3"):
        names = [name for name, _ in groups[key]]
        if len(names) != len(set(names)):
            _refuse("hypothesis_manifest_duplicate", f"{key} contains a duplicate feature")

    seen: dict[str, str] = {}
    for key in ("h1", "h2", "h3"):
        for name, _ in groups[key]:
            if name in seen:
                _refuse(
                    "hypothesis_manifest_overlap",
                    f"feature {name!r} appears in both {seen[name]} and {key}",
                )
            seen[name] = key

    expected_h4 = groups["h1"] + groups["h2"] + groups["h3"] + _IDENTITY_GROUPS
    if groups["h4"] != expected_h4:
        _refuse(
            "hypothesis_manifest_composition",
            "h4 is not exactly h1 + h2 + h3 + the identity block",
        )

    canonical = {
        "h1": tuple(H1_MANIFEST),
        "h2": tuple(H2_MANIFEST),
        "h3": tuple(H3_MANIFEST),
        "h4": tuple(H4_MANIFEST),
    }
    for key in ("h1", "h2", "h3", "h4"):
        if groups[key] != canonical[key]:
            _refuse(
                "hypothesis_manifest_declaration_drift",
                f"{key} does not equal the D2a module-owned declaration",
            )
    return manifests
