"""D3-b — F5 ``fit_ridge_lane``: the single-fold, single-ridge-lane estimator.

Contract of record: frozen spec v9 §D3 + the sealed registration (keys 14/15/16;
`docs/validation/2026-07-21-qb-1-study-registration.md`), framing ENUMERATED
CLEAR 2026-07-23 (+ Codex round-1 G1-G6, round-2 V2-H1/H2/M1/M2). One lane on one
fold — the caller iterates the four lanes and eight folds; naive-carryforward and
comparison scoring are D3-c.

Pipeline per lane (registration key 15, EXACT): the train-fitted median imputer
(F22, which excludes the draft-capital group) → a train-fitted ``StandardScaler``
→ ``RidgeCV`` over the ordered grid (0.01, 0.1, 1, 10, 100) with ``cv=None`` (the
efficient LOO/GCV path). Every fit is TRAIN-only, and the finiteness gate is
STAGED — scaler state and transformed matrices are validated BEFORE RidgeCV,
ridge state BEFORE prediction, and predictions before return — so a finite input
that overflows the estimator refuses with ``estimator_nonfinite`` and never
reaches sklearn as a NaN/inf.

Validation runs in published precedence: API misuse → ``TypeError``; then, top
down, fold-root schedule → fold-row structure/classification → label-table
integrity → cross-table presence → manifest/value → missingness → draft-capital
→ fit degeneracy. Corrupt study data inside an otherwise-valid collection is a
named ``QBValidationFailure``; every external field is validated as an exact plain
primitive with a plausible domain BEFORE hash/equality/numeric conversion, and
every refusal detail renders through the bounded, total ``_safe_repr`` — so
neither a hostile subclass nor a huge plain value escapes as a bare exception or
an unbounded message. All outputs stay descriptive. H2 rushing production is a
hypothesis UNDER TEST — this lane fits H2 identically to every lane, no claim.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure
from src.dynasty_genius.eval.qb_validation.folds import (
    _DRAFT_CAPITAL_FEATURES,
    _MAX_SEASON,
    _MIN_SEASON,
    _is_finite_real,
    _safe_repr,
    fit_train_only_imputer,
)
from src.dynasty_genius.eval.qb_validation.study_matrix import (
    H1_MANIFEST,
    H2_MANIFEST,
    H3_MANIFEST,
    H4_MANIFEST,
)

_LANES = {"h1": H1_MANIFEST, "h2": H2_MANIFEST, "h3": H3_MANIFEST, "h4": H4_MANIFEST}
_ALPHA_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
_ROW_DROP_FRACTION = 0.5
_KNOWN_TARGETS = ("target_evaluable", "no_target_season")


def _refuse(reason: str, detail: str) -> None:
    raise QBValidationFailure(reason, detail)


def _exact_str(value: Any) -> bool:
    """An exact ``str`` with no surrounding/only whitespace (rejects subclasses)."""
    return type(value) is str and value != "" and value == value.strip()


def _exact_number(value: Any) -> bool:
    """An exact, finite ``int``/``float`` — rejects bool, subclasses, NaN/inf, and
    non-float-representable ints, BEFORE any numeric conversion."""
    return type(value) in (int, float) and _is_finite_real(value)


def _valid_season(value: Any) -> bool:
    """A plausible plain-int calendar-year season (bounded before any raw use)."""
    return type(value) is int and _MIN_SEASON <= value <= _MAX_SEASON


def _all_finite(*arrays: Any) -> bool:
    for array in arrays:
        if not np.all(np.isfinite(np.asarray(array, dtype=float))):
            return False
    return True


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _validate_label_table(labels: Any) -> dict[tuple[str, int], float]:
    """Phase 2: the consumed D2 label-row contract (integrity before presence)."""
    if not _is_sequence(labels):
        raise TypeError(f"labels must be a non-string sequence, got {type(labels).__name__}")
    lookup: dict[tuple[str, int], float] = {}
    for index, row in enumerate(labels):
        if not isinstance(row, Mapping):
            _refuse("label_row_invalid", f"label [{index}] is not a mapping")
        player_id = row.get("player_id")
        season = row.get("season")
        outcome = row.get("outcome_class")
        games = row.get("qualifying_games")
        if not _exact_str(player_id) or not _valid_season(season):
            _refuse(
                "label_row_invalid",
                f"label [{index}] identity player_id={_safe_repr(player_id)} "
                f"season={_safe_repr(season)}",
            )
        if type(outcome) is not str or outcome != "evaluable":
            _refuse("label_row_invalid", f"label [{index}] outcome_class={_safe_repr(outcome)}")
        if type(games) is not int or games < 1:
            _refuse("label_row_invalid", f"label [{index}] qualifying_games={_safe_repr(games)}")
        key = (player_id, season)
        if key in lookup:
            _refuse("duplicate_label", f"label table duplicates {_safe_repr(key)}")
        ppg = row.get("ppg")
        if not _exact_number(ppg):
            _refuse("label_value_invalid", f"label {_safe_repr(key)} ppg={_safe_repr(ppg)}")
        lookup[key] = float(ppg)
    return lookup


def _validate_fold_rows(
    rows: list[Any], *, where: str, test_season: int, train_seasons: set[int],
) -> list[tuple[Mapping[str, Any], str, int, str]]:
    """Phase 1: fold-row structure + classification, in published precedence."""
    validated: list[tuple[Mapping[str, Any], str, int, str]] = []
    seen: set[tuple[str, int]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            _refuse("fold_row_invalid", f"{where} row [{index}] is not a mapping")
        season = row.get("target_season")
        if not _valid_season(season):
            _refuse(
                "fold_row_invalid",
                f"{where} row [{index}] target_season={_safe_repr(season)} is not a plausible season",
            )
        if where == "test" and season != test_season:
            _refuse("fold_root_invalid", f"test row [{index}] season {_safe_repr(season)} != {test_season}")
        if where == "train" and (season >= test_season or season not in train_seasons):
            _refuse(
                "fold_root_invalid",
                f"train row [{index}] season {_safe_repr(season)} is not a scheduled pre-{test_season} season",
            )
        player_id = row.get("player_id")
        if not _exact_str(player_id):
            _refuse("player_identity_invalid", f"{where} row [{index}] player_id={_safe_repr(player_id)}")
        key = (player_id, season)
        if key in seen:
            _refuse("duplicate_player_season", f"{where} duplicates {_safe_repr(key)}")
        seen.add(key)
        target = row.get("target")
        if type(target) is not str or target not in _KNOWN_TARGETS:   # target BEFORE eligibility
            _refuse("target_class_invalid", f"{where} {_safe_repr(key)} target={_safe_repr(target)}")
        eligibility = row.get("eligibility")
        if type(eligibility) is not str:
            _refuse("eligibility_invalid", f"{where} {_safe_repr(key)} eligibility={_safe_repr(eligibility)}")
        if eligibility == "rookie_no_priors":
            _refuse("rookie_no_priors", f"{where} {_safe_repr(key)} is an injected rookie")
        if eligibility != "cohort_admitted":
            _refuse("eligibility_invalid", f"{where} {_safe_repr(key)} eligibility={_safe_repr(eligibility)}")
        validated.append((row, player_id, season, target))
    return validated


def _presence_and_missingness(
    validated: list[tuple[Mapping[str, Any], str, int, str]],
    *, lane: str, feature_names: tuple[str, ...],
    lookup: dict[tuple[str, int], float], where: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Phase 3: presence → manifest/value → missingness → draft-capital."""
    survivors: list[dict[str, Any]] = []
    dropped: list[list[Any]] = []
    for row, player_id, season, target in validated:
        key = (player_id, season)
        present = key in lookup
        if target == "target_evaluable" and not present:
            _refuse("classification_label_mismatch", f"{where} {_safe_repr(key)} evaluable but no label")
        if target == "no_target_season":
            if present:
                _refuse("classification_label_mismatch", f"{where} {_safe_repr(key)} no_target but a label")
            continue
        for name in feature_names:
            if name not in row:
                _refuse("manifest_feature_missing", f"{where} {_safe_repr(key)} missing lane key {name!r}")
            value = row.get(name)
            if value is not None and not _exact_number(value):
                _refuse("imputer_value_invalid", f"{where} {_safe_repr(key)} {name}={_safe_repr(value)}")
        missing = sum(1 for name in feature_names if row.get(name) is None)
        if missing / len(feature_names) > _ROW_DROP_FRACTION:
            dropped.append([player_id, season])
            continue
        if lane == "h4":
            for name in _DRAFT_CAPITAL_FEATURES:
                if row.get(name) is None:
                    _refuse(
                        "draft_capital_unresolved",
                        f"{_safe_repr(key)} carries a null draft-capital {name} after resolution",
                    )
        survivors.append({**row, "_key": key})
    dropped.sort()
    return survivors, {"count": len(dropped), "keys": dropped}


def _matrix(rows: list[dict[str, Any]], feature_names: tuple[str, ...]) -> np.ndarray:
    return np.array([[float(row[name]) for name in feature_names] for row in rows], dtype=float)


def fit_ridge_lane(
    fold: Mapping[str, Any],
    labels: Sequence[Mapping[str, Any]],
    *,
    lane: str,
) -> dict[str, Any]:
    """Fit ONE ridge lane on ONE fold, train-only, returning the single-lane result."""
    # 1. Wrong-call API → TypeError (exact-str lane check BEFORE any hash/membership).
    if not isinstance(fold, Mapping):
        raise TypeError(f"fold must be a mapping, got {type(fold).__name__}")
    if not _is_sequence(labels):
        raise TypeError(f"labels must be a non-string sequence, got {type(labels).__name__}")
    if type(lane) is not str or lane not in _LANES:
        raise TypeError(f"lane must be one of {tuple(_LANES)}, got {_safe_repr(lane)}")

    feature_names = tuple(name for name, _ in _LANES[lane])
    excluded = tuple(f for f in _DRAFT_CAPITAL_FEATURES if f in feature_names)

    # 2. Fold root: schedule + structural emptiness. A season is domain-bounded
    #    before any raw formatting so an astronomical value cannot crash rendering.
    test_season = fold.get("test_season")
    train_rows = fold.get("train_rows")
    test_rows = fold.get("test_rows")
    train_seasons = fold.get("train_seasons")
    if not _valid_season(test_season) or not isinstance(train_rows, list) or not isinstance(test_rows, list):
        _refuse("fold_root_invalid", "fold needs a plausible int test_season and train/test row lists")
    if not train_rows or not test_rows:
        _refuse("fold_root_invalid", "fold has an empty train or test partition")
    # A strictly-increasing, contiguous schedule ending at test_season-1 (start not hardcoded).
    if (
        not isinstance(train_seasons, list)
        or not train_seasons
        or any(not _valid_season(s) for s in train_seasons)
        or train_seasons[-1] != test_season - 1
        or any(train_seasons[i] != train_seasons[i - 1] + 1 for i in range(1, len(train_seasons)))
    ):
        _refuse("fold_root_invalid", f"train_seasons={_safe_repr(train_seasons)} is not a valid pre-test schedule")
    season_set = set(train_seasons)

    work = copy.deepcopy(fold)   # non-mutation of the caller's inputs

    v_train = _validate_fold_rows(work["train_rows"], where="train", test_season=test_season, train_seasons=season_set)
    v_test = _validate_fold_rows(work["test_rows"], where="test", test_season=test_season, train_seasons=season_set)
    lookup = _validate_label_table(labels)
    train_survivors, train_missing = _presence_and_missingness(
        v_train, lane=lane, feature_names=feature_names, lookup=lookup, where="train")
    test_survivors, test_missing = _presence_and_missingness(
        v_test, lane=lane, feature_names=feature_names, lookup=lookup, where="test")

    if len(train_survivors) < 2:
        _refuse("fold_train_insufficient", f"{len(train_survivors)} surviving train rows; LOO/GCV needs >= 2")
    if not test_survivors:
        _refuse("fold_test_unpredictable", "no surviving test rows to predict after filtering")

    imputed = fit_train_only_imputer(
        train_survivors, test_survivors, features=feature_names, excluded_features=excluded)
    x_train = _matrix(imputed["train_rows"], feature_names)
    x_test = _matrix(imputed["test_rows"], feature_names)
    y_train = np.array([lookup[row["_key"]] for row in train_survivors], dtype=float)

    # STAGED finiteness gate (V2-H1): validate each estimator stage's output BEFORE
    # the next stage consumes it, so sklearn never sees a NaN/inf and a numerical
    # overflow refuses by name. Only the shape-validated estimator stages catch a
    # numerical exception; API/programming errors are not caught here.
    try:
        scaler = StandardScaler().fit(x_train)
        scaled_train = scaler.transform(x_train)
        scaled_test = scaler.transform(x_test)
    except (np.linalg.LinAlgError, FloatingPointError, ValueError) as exc:
        _refuse("estimator_nonfinite", f"scaler numerical failure: {type(exc).__name__}")
    if not _all_finite(scaler.mean_, scaler.scale_, scaler.var_, scaled_train, scaled_test):
        _refuse("estimator_nonfinite", "non-finite scaler state or transformed matrix")

    try:
        ridge = RidgeCV(alphas=_ALPHA_GRID).fit(scaled_train, y_train)
    except (np.linalg.LinAlgError, FloatingPointError, ValueError) as exc:
        _refuse("estimator_nonfinite", f"ridge numerical failure: {type(exc).__name__}")
    if not _all_finite(ridge.coef_, [float(ridge.intercept_)], [float(ridge.alpha_)]):
        _refuse("estimator_nonfinite", "non-finite ridge state")

    try:
        y_pred_test = ridge.predict(scaled_test)
        y_pred_train = ridge.predict(scaled_train)
    except (np.linalg.LinAlgError, FloatingPointError, ValueError) as exc:
        _refuse("estimator_nonfinite", f"prediction numerical failure: {type(exc).__name__}")
    if not _all_finite(y_pred_train, y_pred_test):
        _refuse("estimator_nonfinite", "non-finite predictions")

    predictions = sorted(
        (
            {
                "player_id": row["_key"][0],
                "target_season": row["_key"][1],
                "y_pred": float(y_pred_test[i]),
                "y_true": lookup[row["_key"]],
                "decision_supported": False,
            }
            for i, row in enumerate(test_survivors)
        ),
        key=lambda p: (p["target_season"], p["player_id"]),
    )
    train_predictions = sorted(
        (
            {
                "player_id": row["_key"][0],
                "target_season": row["_key"][1],
                "y_pred": float(y_pred_train[i]),
                "decision_supported": False,
            }
            for i, row in enumerate(train_survivors)
        ),
        key=lambda p: (p["target_season"], p["player_id"]),
    )

    return {
        "test_season": test_season,
        "lane": lane,
        "feature_names": feature_names,
        "alpha": float(ridge.alpha_),
        "n_train": len(train_survivors),
        "n_predicted": len(test_survivors),
        "predictions": predictions,
        "missingness": {
            "train_manifest_missing": train_missing,
            "test_manifest_missing": test_missing,
        },
        "fit_diagnostics": {
            "imputer_medians": imputed["medians"],
            "scaler_mean": [float(v) for v in scaler.mean_],
            "scaler_scale": [float(v) for v in scaler.scale_],
            "scaler_var": [float(v) for v in scaler.var_],
            "ridge_coef": [float(v) for v in ridge.coef_],
            "ridge_intercept": float(ridge.intercept_),
            "train_predictions": train_predictions,
        },
        "decision_supported": False,
    }
