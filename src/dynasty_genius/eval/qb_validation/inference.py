"""QB-1 D3-d — the inference increment (pooling, cluster bootstrap BCa, shifted-null
NI, cluster permutation, BH-FDR).

Framing authority: ``claude_d3d_framing_v9.md`` (CLEAR 2026-07-24), layered over
v1-v8. This module turns D3-c's per-fold paired evidence into per-contrast
inference. It assigns **no** ``support_status`` (framing P9) and every emitted
record carries ``decision_supported=False`` recursively.

The study has NOT run and there is no result. H2 QB rushing production remains
UNDER TEST: contrasts c02/c05/c06/c09 traverse mechanically identical code with
no special-casing, and nothing here is a result, incrementality, or
dynasty-value claim.

Load-bearing pins (all from the frozen framing, not invented here):

* Fold inclusion is **fixed from the observed data** (P1); a fold contributes iff
  its ``paired_delta`` is not None, reconciled against the whole record rather
  than trusted as a field (v2 disposition 6).
* Replicate and jackknife **weights recompute** per replicate (P3).
* **Any** undefined replicate refuses the whole distribution by name (P8) — never
  a retry, a drop, a short distribution, or an invented tolerance.
* BCa ``z0`` uses a **midrank** proportion; the one-sided bound is the alpha=0.05
  BCa endpoint; endpoints are **never clamped** (00: surface the arithmetic
  honestly, unclamped).
* RNG is ``Generator(PCG64(SeedSequence([seed, procedure_ordinal, contrast_ordinal])))``
  with ``bootstrap=0``, ``permutation=1`` and contrast ordinals fixed by
  registered id — never by iteration order.
* BH-FDR runs over a **fixed 14-member** family mixing ``p_perm`` (model lanes)
  and ``p_ni`` (H5 lanes); a contrast without a p occupies its slot and is never
  rejected (P4/P5).
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any

import numpy as np
import scipy
from numpy.random import PCG64, Generator, SeedSequence
from scipy.stats import norm, rankdata

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure
from src.dynasty_genius.eval.qb_validation.folds import _safe_repr
from src.dynasty_genius.eval.qb_validation.registration import (
    require_registration_hash,
)
from src.dynasty_genius.eval.qb_validation.ridge_lane import (
    _exact_number,
    _exact_str,
    _is_sequence,
)

# ── Pinned contract constants ───────────────────────────────────────────────

EXPECTED_SCIPY_VERSION = "1.17.1"

_SEED_ROOT = 20260716
_PROCEDURE_ORDINALS = {"bootstrap": 0, "permutation": 1}
_STARVED_N = 20
_MODEL_FOLDS = tuple(range(2018, 2026))
_H5_FOLDS = (2021, 2022, 2023, 2024)
_LANES = ("model", "h5")
_FAMILY_SIZE = 14
_CONTRAST_IDS = tuple(f"c{i:02d}" for i in range(1, 15))

STATE_VOCABULARIES = {
    "pooling": ("ok", "no_contributing_folds"),
    "bootstrap": ("ok", "no_contributing_folds", "replicate_degenerate"),
    "bca": (
        "ok",
        "distribution_unavailable",
        "bca_bias_undefined",
        "jackknife_degenerate",
    ),
    "permutation": ("ok", "no_contributing_folds", "replicate_degenerate"),
    "ni": ("ok", "distribution_unavailable"),
    "bh": ("ok", "family_unavailable"),
}

REFUSAL_REASONS = frozenset(
    {
        "preregistration_missing",
        "dependency_version_drift",
        "registered_constant_drift",
        "contrast_set_drift",
        "fold_record_inconsistent",
        "unexpected_fold",
        "unexpected_lane",
        "non_plain_identity_key",
        "duplicate_evidence_key",
        "non_finite_evidence",
    }
)

# Registered constants asserted equal to the registration payload (P10): drift in
# the registered object is DETECTED, never silently overridden by a module literal.
_REGISTERED_INFERENCE = {
    "bootstrap_B": 10_000,
    "bootstrap_seed": _SEED_ROOT,
    "permutation_B": 10_000,
    "permutation_seed": _SEED_ROOT,
    "fdr_q": 0.10,
    "materiality_m": 0.05,
    "ci": "bca_cluster_by_player",
    "jackknife": "delete_one_player",
    "pooling": "evaluable_n_weighted_mean_of_per_fold_paired_deltas",
}
_REGISTERED_FLOORS = {
    "model_lane": 5,
    "model_lane_total": 8,
    "h5_lane": 3,
    "h5_lane_total": 4,
    "fold_min_evaluable_n": _STARVED_N,
}
_REGISTERED_H5 = {
    "delta_definition": "market_minus_model",
    "margin_m": 0.05,
    "boundary_delta0": -0.05,
}
_REGISTERED_MARGINS = (0.025, 0.05, 0.10)


def _refuse(reason: str, detail: str) -> None:
    raise QBValidationFailure(reason, detail)


def _contrast_ordinal(contrast_id: str) -> int:
    """Ordinal fixed by REGISTERED id (``c01``->1), never by iteration order."""
    return int(contrast_id[1:])


def _seed_material(procedure: str, contrast_id: str) -> list[int]:
    return [
        _SEED_ROOT,
        _PROCEDURE_ORDINALS[procedure],
        _contrast_ordinal(contrast_id),
    ]


def _generator(procedure: str, contrast_id: str) -> Generator:
    return Generator(PCG64(SeedSequence(_seed_material(procedure, contrast_id))))


# ── Golden RNG fixture (framing v4 §3: two canonical encodings) ─────────────


def _digest(values: list[int]) -> str:
    return hashlib.sha256(
        json.dumps(values, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _build_golden_fixture(*, n_clusters: int = 8, b: int = 16) -> dict[str, Any]:
    """Compute the golden draw digests from THIS module's pinned derivation.

    Deliberately computed, never transcribed: a silent RNG, ordering, seed, or
    library-stream change moves these digests and fails a contract row rather
    than quietly moving a study number.
    """
    bootstrap: dict[str, str] = {}
    permutation: dict[str, str] = {}
    for contrast_id in _CONTRAST_IDS:
        draws = _generator("bootstrap", contrast_id).integers(
            low=0, high=n_clusters, size=(b, n_clusters), dtype=np.int64
        )
        bootstrap[contrast_id] = _digest(
            [int(value) for value in draws.ravel(order="C")[:32].tolist()]
        )
        mask = (
            _generator("permutation", contrast_id).random(size=(b, n_clusters))
            < 0.5
        )
        permutation[contrast_id] = _digest(
            [int(value) for value in mask.ravel(order="C")[:32].tolist()]
        )
    return {
        "n_clusters": n_clusters,
        "B": b,
        "draw_digests": {"bootstrap": bootstrap, "permutation": permutation},
    }


GOLDEN_FIXTURE = _build_golden_fixture()


# ── Rank statistics ─────────────────────────────────────────────────────────


def _pearson(left: np.ndarray, right: np.ndarray) -> float | None:
    left_centered = left - left.mean()
    right_centered = right - right.mean()
    denominator = math.sqrt(
        float((left_centered * left_centered).sum())
        * float((right_centered * right_centered).sum())
    )
    if denominator == 0.0 or not math.isfinite(denominator):
        return None
    value = float((left_centered * right_centered).sum()) / denominator
    return value if math.isfinite(value) else None


def _pearson_rows(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Row-wise Pearson over rank matrices; NaN marks an UNDEFINED row.

    The replicate loops are the module's hot path (B=10,000 x folds), so the
    per-replicate statistic is computed as one batched array op rather than a
    Python loop. NaN is the internal 'undefined' marker only — it never reaches
    an emitted record, which carries a named state instead.
    """
    left_centered = left - left.mean(axis=-1, keepdims=True)
    right_centered = right - right.mean(axis=-1, keepdims=True)
    numerator = (left_centered * right_centered).sum(axis=-1)
    denominator = np.sqrt(
        (left_centered * left_centered).sum(axis=-1)
        * (right_centered * right_centered).sum(axis=-1)
    )
    result = np.full(np.shape(numerator), np.nan, dtype=np.float64)
    np.divide(numerator, denominator, out=result, where=denominator > 0.0)
    return result


def _spearman_rows(
    values: np.ndarray, truth_ranks: np.ndarray
) -> np.ndarray:
    return _pearson_rows(rankdata(values, axis=-1), truth_ranks)


def _spearman(values: np.ndarray, truths: np.ndarray) -> float | None:
    """Spearman rho as Pearson over midrank-averaged ranks; None when undefined.

    A constant vector has no rank ordering, so rho is UNDEFINED — returned as
    ``None`` and escalated by the caller into a named state. It is never
    silently coerced to 0.0, which would read as 'no association measured'
    rather than 'no association measurable'.
    """
    if values.size < 2:
        return None
    return _pearson(rankdata(values), rankdata(truths))


# ── Fold reconciliation (v2 disposition 6: reconcile the record, never trust a field)


def _validate_stored_statistic(
    value: Any, *, name: str, bound: float
) -> float | None:
    """A stored rank statistic must be finite AND inside its mathematical domain.

    Exact equality alone cannot police this: ``inf - finite == inf``, so an
    infinite rho satisfies its own delta reconciliation and reaches the pooled
    estimate as an honest-looking ``ok`` record. A Spearman lies in [-1, 1] and a
    difference of two Spearmans in [-2, 2] — those are properties of the
    statistic, not registered tunables, so the check is a record-shape clause and
    refuses under the existing ``fold_record_inconsistent`` reason.
    """
    if value is None:
        return None
    if type(value) is not float:
        _refuse(
            "fold_record_inconsistent",
            f"{name} must be an exact float or None, got {_safe_repr(type(value).__name__)}",
        )
    if not math.isfinite(value):
        _refuse("fold_record_inconsistent", f"{name} is not finite")
    if not -bound <= value <= bound:
        _refuse(
            "fold_record_inconsistent",
            f"{name} {_safe_repr(value)} is outside [-{bound}, {bound}]",
        )
    return value


def _fold_reasons(fold: Mapping[str, Any]) -> tuple[str, ...]:
    reasons = fold.get("reasons")
    if not _is_sequence(reasons):
        _refuse("fold_record_inconsistent", "fold reasons must be a sequence")
    return tuple(reasons)


def _reconcile_fold(
    fold: Any,
    *,
    lane_folds: tuple[int, ...],
) -> bool:
    """Return whether the fold is ADMITTED, refusing any self-inconsistent record.

    ``paired_delta is not None`` is the admission predicate (framing §4 Q3), but
    it is never a trust predicate: every clause below must independently agree
    before a non-null delta is allowed to carry weight.

    Fold/evidence season agreement is NOT checked here — it runs as a separate
    pass after cross-fold duplicate detection, so that a colliding key keeps its
    strictly more specific ``duplicate_evidence_key`` diagnosis while a
    non-colliding mismatch is still refused. Both paths reach every caller.
    """
    if not isinstance(fold, Mapping):
        _refuse("fold_record_inconsistent", f"fold must be a mapping, got {_safe_repr(type(fold).__name__)}")

    season = fold.get("test_season")
    if type(season) is not int or season not in lane_folds:
        _refuse("unexpected_fold", f"fold season {_safe_repr(season)} is outside the registered lane folds")

    pool_n = fold.get("common_pool_n")
    if type(pool_n) is not int or pool_n < 0:
        _refuse("fold_record_inconsistent", "common_pool_n must be a non-negative plain int")

    evidence = fold.get("paired_evidence")
    if not _is_sequence(evidence):
        _refuse("fold_record_inconsistent", "paired_evidence must be a sequence")
    if len(evidence) != pool_n:
        _refuse(
            "fold_record_inconsistent",
            f"paired_evidence length {len(evidence)} != common_pool_n {pool_n}",
        )

    seen: set[str] = set()
    for row in evidence:
        if not isinstance(row, Mapping):
            _refuse("fold_record_inconsistent", "paired_evidence row must be a mapping")
        player_id = row.get("player_id")
        if type(player_id) is not str:
            _refuse("non_plain_identity_key", "paired_evidence player_id must be a plain str")
        if player_id in seen:
            _refuse("fold_record_inconsistent", "duplicate player within a single fold")
        seen.add(player_id)

    starved = fold.get("fold_starved")
    if type(starved) is not bool or starved is not (pool_n < _STARVED_N):
        _refuse(
            "fold_record_inconsistent",
            f"fold_starved {_safe_repr(starved)} disagrees with common_pool_n {pool_n}",
        )

    degeneracy = fold.get("degeneracy")
    if not isinstance(degeneracy, Mapping):
        _refuse("fold_record_inconsistent", "degeneracy must be a mapping")
    allowed = []
    for side in ("left", "right"):
        side_record = degeneracy.get(side)
        if not isinstance(side_record, Mapping):
            _refuse("fold_record_inconsistent", f"degeneracy.{side} must be a mapping")
        side_allowed = side_record.get("metrics_allowed")
        if type(side_allowed) is not bool:
            _refuse("fold_record_inconsistent", f"degeneracy.{side}.metrics_allowed must be a bool")
        allowed.append(side_allowed)

    left_rho = _validate_stored_statistic(
        fold.get("spearman_left"), name="spearman_left", bound=1.0
    )
    right_rho = _validate_stored_statistic(
        fold.get("spearman_right"), name="spearman_right", bound=1.0
    )
    delta = _validate_stored_statistic(
        fold.get("paired_delta"), name="paired_delta", bound=2.0
    )

    computable = (
        not starved
        and all(allowed)
        and left_rho is not None
        and right_rho is not None
    )
    expected_delta = left_rho - right_rho if computable else None
    if expected_delta is None:
        if delta is not None:
            _refuse(
                "fold_record_inconsistent",
                "paired_delta present on a fold whose record cannot produce one",
            )
        return False
    if delta is None or delta != expected_delta:
        _refuse(
            "fold_record_inconsistent",
            "paired_delta disagrees with spearman_left - spearman_right",
        )
    return True


def _contrast_lane_folds(contrast: Any) -> tuple[str, tuple[int, ...]]:
    if not isinstance(contrast, Mapping):
        raise TypeError(
            f"contrast must be a mapping, got {type(contrast).__name__}"
        )
    lane = contrast.get("lane")
    if type(lane) is not str or lane not in _LANES:
        _refuse("unexpected_lane", f"lane {_safe_repr(lane)} is not a registered lane")
    return lane, (_H5_FOLDS if lane == "h5" else _MODEL_FOLDS)


def _check_cross_fold_duplicates(per_fold: Any) -> None:
    """A ``(player_id, target_season)`` may appear at most once across all folds."""
    seen: set[tuple[str, int]] = set()
    for fold in per_fold:
        for row in fold["paired_evidence"]:
            player_id = row.get("player_id")
            season = row.get("target_season")
            if type(player_id) is not str:
                _refuse(
                    "non_plain_identity_key",
                    "paired_evidence player_id must be an exact plain str",
                )
            if type(season) is not int:
                _refuse(
                    "fold_record_inconsistent",
                    "evidence target_season must be a plain int",
                )
            key = (player_id, season)
            if key in seen:
                _refuse(
                    "duplicate_evidence_key",
                    f"duplicate (player_id, target_season) for season {season}",
                )
            seen.add(key)


def _check_evidence_seasons(per_fold: Any) -> None:
    """Every row must sit in the fold whose header season it declares.

    Runs AFTER duplicate detection so a colliding key keeps the more specific
    diagnosis, but it is never skipped: a non-colliding mismatch would otherwise
    let the resampling substrate accept evidence in the wrong season while the
    pooling surface refuses the very same record.
    """
    for fold in per_fold:
        season = fold["test_season"]
        for row in fold["paired_evidence"]:
            if row.get("target_season") != season:
                _refuse(
                    "fold_record_inconsistent",
                    f"evidence target_season disagrees with fold season {season}",
                )


def _check_fold_topology(
    contrast: Mapping[str, Any], lane_folds: tuple[int, ...], per_fold: Any
) -> None:
    """The lane's REGISTERED season sequence, exactly once each, in order.

    Without this, a missing season silently shrinks the evidence base and — the
    defect that matters — duplicate seasons inflate ``evaluable_folds``, letting
    two unique H5 seasons masquerade as the registered four and satisfy a fold
    floor that gates the NI conjunction.
    """
    seasons = tuple(fold["test_season"] for fold in per_fold)
    if seasons != lane_folds:
        _refuse(
            "unexpected_fold",
            f"fold topology {_safe_repr(seasons)} != registered {_safe_repr(lane_folds)}",
        )
    folds_present = contrast.get("folds_present")
    # Exact plain int BEFORE equality: 8.0 and numpy.int64(8) both compare equal
    # to 8, and neither is the declared record shape the sole producer emits.
    if type(folds_present) is not int or folds_present != len(per_fold):
        _refuse(
            "fold_record_inconsistent",
            f"folds_present {_safe_repr(folds_present)} is not the plain int {len(per_fold)}",
        )


def _admission(contrast: Any) -> tuple[str, list[Any], list[bool]]:
    """The single ordered admission pipeline every public entry point runs.

    Order is load-bearing: per-fold reconciliation, then cross-fold duplicates,
    then fold/evidence season agreement, then registered topology. Each stage
    yields the most specific diagnosis available at that point.
    """
    lane, lane_folds = _contrast_lane_folds(contrast)
    per_fold = contrast.get("per_fold")
    if not _is_sequence(per_fold):
        _refuse("fold_record_inconsistent", "per_fold must be a sequence")
    flags = [_reconcile_fold(fold, lane_folds=lane_folds) for fold in per_fold]
    _check_cross_fold_duplicates(per_fold)
    _check_evidence_seasons(per_fold)
    _check_fold_topology(contrast, lane_folds, per_fold)
    return lane, list(per_fold), flags


def _admitted_folds(contrast: Any) -> tuple[str, list[Mapping[str, Any]]]:
    """The observed-data fold set (P1), fixed once and reused by every procedure."""
    lane, per_fold, flags = _admission(contrast)
    return lane, [fold for fold, admitted in zip(per_fold, flags) if admitted]


# ── 1. Pooling ──────────────────────────────────────────────────────────────


def pool_paired_deltas(contrast: Any, *, registration: Any) -> dict[str, Any]:
    """Evaluable-n weighted mean of per-fold paired deltas (registered pooling).

    Weight = the pair's exact ``common_pool_n`` (framing P2) — the n the delta was
    actually computed on. Excluded folds are recorded losslessly with their
    verbatim ordered reasons, so a reader can see WHY the estimate rests on the
    folds it rests on.
    """
    _require_mapping(registration, "registration")
    _lane, per_fold, flags = _admission(contrast)

    contributing: list[int] = []
    weights: dict[int, int] = {}
    excluded: list[dict[str, Any]] = []
    numerator = 0.0
    denominator = 0

    for fold, admitted in zip(per_fold, flags):
        if admitted:
            season = fold["test_season"]
            weight = fold["common_pool_n"]
            contributing.append(season)
            weights[season] = weight
            numerator += weight * fold["paired_delta"]
            denominator += weight
        else:
            excluded.append(
                {
                    "test_season": fold["test_season"],
                    "reasons": _fold_reasons(fold),
                    "decision_supported": False,
                }
            )

    if not contributing or denominator == 0:
        return {
            "pooled_delta": None,
            "state": "no_contributing_folds",
            "contributing_folds": [],
            "excluded_folds": excluded,
            "weights": {},
            "evaluable_folds": 0,
            "decision_supported": False,
        }

    return {
        "pooled_delta": numerator / denominator,
        "state": "ok",
        "contributing_folds": contributing,
        "excluded_folds": excluded,
        "weights": weights,
        "evaluable_folds": len(contributing),
        "decision_supported": False,
    }


# ── 2. Cluster universe ─────────────────────────────────────────────────────


def build_cluster_universe(contrast: Any) -> dict[str, Any]:
    """The player-keyed resampling substrate shared by bootstrap and permutation.

    The cluster is the PLAYER, not the row: a player appearing in several folds
    moves as one unit, which is what ``inference.ci = bca_cluster_by_player``
    registers. Row resampling on repeated-player data understates the interval.
    """
    _lane, admitted = _admitted_folds(contrast)

    rows_by_player: dict[str, list[dict[str, Any]]] = {}
    for fold in admitted:
        for row in fold["paired_evidence"]:
            # Identity type and duplicate keys are already settled by the shared
            # admission pipeline, which runs them in their contract order.
            player_id = row["player_id"]
            values = {}
            for field in ("left_pred", "right_pred", "y_true"):
                value = row.get(field)
                if not _exact_number(value):
                    _refuse(
                        "non_finite_evidence",
                        f"{field} must be an exact finite number",
                    )
                values[field] = float(value)
            rows_by_player.setdefault(player_id, []).append(
                {
                    "test_season": fold["test_season"],
                    "left_pred": values["left_pred"],
                    "right_pred": values["right_pred"],
                    "y_true": values["y_true"],
                    "decision_supported": False,
                }
            )

    player_ids = tuple(sorted(rows_by_player))
    return {
        "player_ids": player_ids,
        "n_clusters": len(player_ids),
        "rows_by_player": {
            player_id: rows_by_player[player_id] for player_id in player_ids
        },
        "decision_supported": False,
    }


class _FoldArrays:
    """Per-fold column arrays indexed by cluster ordinal (resampling hot path)."""

    __slots__ = ("cluster_index", "left", "right", "truth", "row_of_cluster")

    def __init__(self, cluster_index, left, right, truth, *, n_clusters) -> None:
        self.cluster_index = cluster_index
        self.left = left
        self.right = right
        self.truth = truth
        # A fold holding exactly one row for EVERY cluster admits a batched
        # resample (the draw indexes rows directly); a partial fold falls back
        # to the per-replicate path because its resampled size varies.
        self.row_of_cluster = None
        if cluster_index.size == n_clusters:
            row_of_cluster = np.full(n_clusters, -1, dtype=np.int64)
            row_of_cluster[cluster_index] = np.arange(
                cluster_index.size, dtype=np.int64
            )
            if not (row_of_cluster < 0).any():
                self.row_of_cluster = row_of_cluster


def _fold_arrays(universe: Mapping[str, Any]) -> list[_FoldArrays]:
    by_season: dict[int, list[tuple[int, float, float, float]]] = {}
    for ordinal, player_id in enumerate(universe["player_ids"]):
        for row in universe["rows_by_player"][player_id]:
            by_season.setdefault(row["test_season"], []).append(
                (ordinal, row["left_pred"], row["right_pred"], row["y_true"])
            )
    n_clusters = len(universe["player_ids"])
    folds = []
    for season in sorted(by_season):
        entries = by_season[season]
        folds.append(
            _FoldArrays(
                np.fromiter((e[0] for e in entries), dtype=np.int64, count=len(entries)),
                np.fromiter((e[1] for e in entries), dtype=np.float64, count=len(entries)),
                np.fromiter((e[2] for e in entries), dtype=np.float64, count=len(entries)),
                np.fromiter((e[3] for e in entries), dtype=np.float64, count=len(entries)),
                n_clusters=n_clusters,
            )
        )
    return folds


def _pooled_from_parts(
    parts: list[tuple[int, float | None]],
) -> float | None:
    numerator = 0.0
    denominator = 0
    for weight, delta in parts:
        if delta is None:
            return None
        numerator += weight * delta
        denominator += weight
    if denominator == 0:
        return None
    return numerator / denominator


# ── 3. Cluster bootstrap ────────────────────────────────────────────────────


def cluster_bootstrap_distribution(
    contrast: Any, *, registration: Any
) -> dict[str, Any]:
    """B cluster-resampled pooled deltas; weights recompute per replicate (P3).

    P8 is absolute: if ANY replicate is undefined the whole distribution is
    refused by name. No retry, no drop, no short distribution, no invented
    tolerance — a p-value or interval over a mutilated distribution is exactly
    the fabricated-confidence failure the No-Verdict line forbids.
    """
    _require_mapping(registration, "registration")
    b = _registered_int(registration, ("inference", "bootstrap_B"))
    contrast_id = _contrast_id(contrast)
    universe = build_cluster_universe(contrast)
    n_clusters = universe["n_clusters"]

    if n_clusters == 0:
        return {
            "deltas": None,
            "B": b,
            "seed_material": _seed_material("bootstrap", contrast_id),
            "n_clusters": 0,
            "state": "no_contributing_folds",
            "decision_supported": False,
        }

    folds = _fold_arrays(universe)
    draws = _generator("bootstrap", contrast_id).integers(
        low=0, high=n_clusters, size=(b, n_clusters), dtype=np.int64
    )

    numerators = np.zeros(b, dtype=np.float64)
    denominators = np.zeros(b, dtype=np.float64)
    batched = [fold for fold in folds if fold.row_of_cluster is not None]
    residual = [fold for fold in folds if fold.row_of_cluster is None]

    for fold in batched:
        rows = fold.row_of_cluster[draws]
        truth_ranks = rankdata(fold.truth[rows], axis=-1)
        left = _spearman_rows(fold.left[rows], truth_ranks)
        right = _spearman_rows(fold.right[rows], truth_ranks)
        numerators += n_clusters * (left - right)
        denominators += n_clusters

    if residual:
        for replicate in range(b):
            counts = np.bincount(draws[replicate], minlength=n_clusters)
            for fold in residual:
                multiplicity = counts[fold.cluster_index]
                if not multiplicity.any():
                    # P8: the observed fold set is FIXED. A replicate that gives
                    # an admitted fold zero rows cannot evaluate the registered
                    # estimator, so it is undefined — dropping the fold would
                    # silently change the statistic mid-replicate.
                    numerators[replicate] = np.nan
                    continue
                selector = np.repeat(
                    np.arange(fold.cluster_index.size), multiplicity
                )
                left_value = _spearman(
                    fold.left[selector], fold.truth[selector]
                )
                right_value = _spearman(
                    fold.right[selector], fold.truth[selector]
                )
                weight = int(selector.size)
                if left_value is None or right_value is None:
                    numerators[replicate] = np.nan
                else:
                    numerators[replicate] += weight * (
                        left_value - right_value
                    )
                denominators[replicate] += weight

    pooled_all = np.full(b, np.nan, dtype=np.float64)
    np.divide(
        numerators, denominators, out=pooled_all, where=denominators > 0.0
    )
    if np.isnan(pooled_all).any():
        return {
            "deltas": None,
            "B": b,
            "seed_material": _seed_material("bootstrap", contrast_id),
            "n_clusters": n_clusters,
            "state": "replicate_degenerate",
            "decision_supported": False,
        }

    return {
        "deltas": tuple(float(value) for value in pooled_all),
        "B": b,
        "seed_material": _seed_material("bootstrap", contrast_id),
        "n_clusters": n_clusters,
        "state": "ok",
        "decision_supported": False,
    }


def _jackknife_pooled(universe: Mapping[str, Any]) -> tuple[float, ...]:
    """Delete-one-PLAYER jackknife of the pooled statistic (registered unit)."""
    folds = _fold_arrays(universe)
    n_clusters = universe["n_clusters"]
    values: list[float] = []
    for deleted in range(n_clusters):
        parts: list[tuple[int, float | None]] = []
        for fold in folds:
            keep = fold.cluster_index != deleted
            if not keep.any():
                # Same fixed-fold semantics as the bootstrap: a deletion that
                # empties an admitted fold leaves the jackknife value undefined.
                return ()
            left = _spearman(fold.left[keep], fold.truth[keep])
            right = _spearman(fold.right[keep], fold.truth[keep])
            delta = None if left is None or right is None else left - right
            parts.append((int(keep.sum()), delta))
        pooled = _pooled_from_parts(parts)
        if pooled is None:
            # A degenerate deletion carries no jackknife value; the caller's
            # acceleration guard names the resulting state rather than guessing.
            return ()
        values.append(pooled)
    return tuple(values)


# ── 4. BCa interval ─────────────────────────────────────────────────────────


def _require_finite_members(values: Any, name: str) -> None:
    """Every member must be an exact finite float BEFORE any arithmetic.

    A single NaN silently poisons a percentile into a NaN interval that still
    reports ``state="ok"``, and makes ``>=`` comparisons return False so an NI
    p-value comes back finite and confident. Both are the fabricated-certainty
    failure the No-Verdict line exists to stop.
    """
    for value in values:
        if type(value) is not float:
            raise TypeError(
                f"{name} members must be exact floats, got {type(value).__name__}"
            )
        if not math.isfinite(value):
            _refuse("non_finite_evidence", f"{name} contains a non-finite member")


def _require_distribution(distribution: Any, name: str) -> tuple[float, ...] | None:
    if distribution is None:
        return None
    if type(distribution) is not tuple:
        raise TypeError(
            f"{name} must be tuple[float, ...] or None, got {type(distribution).__name__}"
        )
    _require_finite_members(distribution, name)
    return distribution


def bca_interval(
    distribution: Any, *, observed: Any, jackknife: Any
) -> dict[str, Any]:
    """Bias-corrected accelerated interval; degenerate paths are NAMED, not clamped.

    ``z0`` uses a MIDRANK proportion so deliberate ties do not push the bias
    correction to an endpoint. Endpoints are never clamped to a nominal range:
    the statistic is a difference of Spearmans on [-2, 2], and clamping would
    silently truncate a real extreme value into false tidiness.
    """
    values = _require_distribution(distribution, "distribution")
    unavailable = {
        "ci95_low": None,
        "ci95_high": None,
        "one_sided_lower_95": None,
        "z0": None,
        "acceleration": None,
        "state": "distribution_unavailable",
        "decision_supported": False,
    }
    if values is None or len(values) == 0:
        return unavailable
    if not _exact_number(observed):
        raise TypeError("observed must be an exact finite number")
    if not _is_sequence(jackknife):
        raise TypeError("jackknife must be a sequence")
    _require_finite_members(jackknife, "jackknife")

    array = np.asarray(values, dtype=np.float64)
    below = float(np.count_nonzero(array < observed))
    equal = float(np.count_nonzero(array == observed))
    proportion = (below + 0.5 * equal) / array.size
    if proportion <= 0.0 or proportion >= 1.0:
        return {
            **unavailable,
            "state": "bca_bias_undefined",
        }
    z0 = float(norm.ppf(proportion))

    jack = np.asarray(jackknife, dtype=np.float64)
    if jack.size == 0:
        return {**unavailable, "state": "jackknife_degenerate"}
    deviations = jack.mean() - jack
    sum_squares = float((deviations**2).sum())
    if sum_squares == 0.0:
        return {
            **unavailable,
            "z0": z0,
            "state": "jackknife_degenerate",
        }
    acceleration = float((deviations**3).sum()) / (6.0 * sum_squares**1.5)

    endpoints: dict[str, float | None] = {}
    for name, alpha in (
        ("ci95_low", 0.025),
        ("ci95_high", 0.975),
        ("one_sided_lower_95", 0.05),
    ):
        z_alpha = float(norm.ppf(alpha))
        shifted = z0 + z_alpha
        denominator = 1.0 - acceleration * shifted
        if denominator == 0.0 or not math.isfinite(denominator):
            return {
                **unavailable,
                "z0": z0,
                "acceleration": acceleration,
                "state": "bca_bias_undefined",
            }
        adjusted = norm.cdf(z0 + shifted / denominator)
        if not math.isfinite(float(adjusted)):
            return {
                **unavailable,
                "z0": z0,
                "acceleration": acceleration,
                "state": "bca_bias_undefined",
            }
        endpoints[name] = float(
            np.percentile(array, 100.0 * float(adjusted), method="linear")
        )

    return {
        "ci95_low": endpoints["ci95_low"],
        "ci95_high": endpoints["ci95_high"],
        "one_sided_lower_95": endpoints["one_sided_lower_95"],
        "z0": z0,
        "acceleration": acceleration,
        "state": "ok",
        "decision_supported": False,
    }


# ── 5. Cluster permutation ──────────────────────────────────────────────────


def cluster_permutation_p(contrast: Any, *, registration: Any) -> dict[str, Any]:
    """Paired cluster permutation: one swap decision per PLAYER, never per row.

    A row-wise swap would break the pairing the design rests on, so the swap is
    applied to every row of a player's cluster together. ``p_two`` carries the
    registered ``(1 + #extreme) / (B + 1)`` correction and is therefore never 0.
    """
    _require_mapping(registration, "registration")
    b = _registered_int(registration, ("inference", "permutation_B"))
    contrast_id = _contrast_id(contrast)

    pooled = pool_paired_deltas(contrast, registration=registration)
    universe = build_cluster_universe(contrast)
    n_clusters = universe["n_clusters"]

    if pooled["state"] != "ok" or n_clusters == 0:
        return {
            "p_two": None,
            "B": b,
            "n_extreme": None,
            "state": "no_contributing_folds",
            "decision_supported": False,
        }

    observed = abs(pooled["pooled_delta"])
    folds = _fold_arrays(universe)
    masks = _generator("permutation", contrast_id).random(size=(b, n_clusters)) < 0.5

    # The permuted sample keeps every original row, so each fold's truth ranks
    # and its weight are invariant across replicates and are computed once.
    numerators = np.zeros(b, dtype=np.float64)
    denominators = 0.0
    for fold in folds:
        truth_ranks = rankdata(fold.truth)
        swap = masks[:, fold.cluster_index]
        rho_left = _spearman_rows(
            np.where(swap, fold.right, fold.left), truth_ranks
        )
        rho_right = _spearman_rows(
            np.where(swap, fold.left, fold.right), truth_ranks
        )
        weight = int(fold.cluster_index.size)
        numerators += weight * (rho_left - rho_right)
        denominators += weight

    if denominators == 0.0 or np.isnan(numerators).any():
        return {
            "p_two": None,
            "B": b,
            "n_extreme": None,
            "state": "replicate_degenerate",
            "decision_supported": False,
        }
    n_extreme = int(
        np.count_nonzero(np.abs(numerators / denominators) >= observed)
    )

    return {
        "p_two": (1 + n_extreme) / (b + 1),
        "B": b,
        "n_extreme": n_extreme,
        "state": "ok",
        "decision_supported": False,
    }


# ── 6. Shifted-null non-inferiority ─────────────────────────────────────────


def shifted_null_ni_p(
    distribution: Any, *, observed: Any, delta0: Any
) -> dict[str, Any]:
    """Null-centered shifted cluster bootstrap NI p (registered H5 test).

    ``delta*_null := delta* - delta_obs + delta0`` with the registered boundary
    ``delta0 = -m``. The sign discipline here is the exact margin/boundary
    conflation the registration itself had to correct at review — it is asserted,
    not assumed.
    """
    values = _require_distribution(distribution, "distribution")
    if values is None:
        return {
            "p_ni": None,
            "delta0": delta0,
            "n_extreme": None,
            "state": "distribution_unavailable",
            "decision_supported": False,
        }
    if not _exact_number(observed) or not _exact_number(delta0):
        raise TypeError("observed and delta0 must be exact finite numbers")

    array = np.asarray(values, dtype=np.float64)
    shifted = array - float(observed) + float(delta0)
    n_extreme = int(np.count_nonzero(shifted >= float(observed)))
    return {
        "p_ni": (1 + n_extreme) / (array.size + 1),
        "delta0": delta0,
        "n_extreme": n_extreme,
        "state": "ok",
        "decision_supported": False,
    }


# ── 7. Benjamini-Hochberg ───────────────────────────────────────────────────


def benjamini_hochberg(
    p_by_contrast: Any, *, q: Any, family_size: int = _FAMILY_SIZE
) -> dict[str, Any]:
    """BH-FDR over a FIXED family size; a p-less contrast occupies its slot.

    Fixing ``m`` at the registered 14 is both the literal reading and the
    conservative one: shrinking the family to the p-bearing contrasts would
    quietly INCREASE the study's rejection rate.
    """
    if not isinstance(p_by_contrast, Mapping):
        raise TypeError(
            f"p_by_contrast must be a mapping, got {type(p_by_contrast).__name__}"
        )
    if type(family_size) is not int or family_size != _FAMILY_SIZE:
        _refuse(
            "registered_constant_drift",
            f"family_size {_safe_repr(family_size)} != registered {_FAMILY_SIZE}",
        )
    if not _exact_number(q) or not 0.0 < q <= 1.0:
        _refuse(
            "registered_constant_drift",
            f"fdr q {_safe_repr(q)} is outside (0, 1]",
        )
    for contrast_id, p_value in p_by_contrast.items():
        if type(contrast_id) is not str or contrast_id not in _CONTRAST_IDS:
            _refuse(
                "contrast_set_drift",
                f"unregistered contrast id {_safe_repr(contrast_id)}",
            )
        if p_value is None:
            continue
        if type(p_value) is not float:
            raise TypeError(
                f"p-value must be an exact float or None, got {type(p_value).__name__}"
            )
        if not math.isfinite(p_value) or not 0.0 <= p_value <= 1.0:
            _refuse(
                "non_finite_evidence",
                f"p-value {_safe_repr(p_value)} is not a finite probability in [0, 1]",
            )

    present = sorted(
        (
            (contrast_id, p_value)
            for contrast_id, p_value in p_by_contrast.items()
            if p_value is not None
        ),
        key=lambda item: (item[1], item[0]),
    )
    # All fourteen registered slots are materialized: a contrast absent from the
    # input holds its slot with adjusted=None / rejected=False rather than
    # vanishing from the family it is registered in.
    adjusted: dict[str, float | None] = {
        contrast_id: None for contrast_id in _CONTRAST_IDS
    }
    running = 1.0
    for rank in range(len(present), 0, -1):
        contrast_id, p_value = present[rank - 1]
        running = min(running, family_size * p_value / rank, 1.0)
        adjusted[contrast_id] = running

    rejected = {
        contrast_id: (value is not None and value <= q)
        for contrast_id, value in adjusted.items()
    }
    return {
        "adjusted": adjusted,
        "rejected": rejected,
        "family_size": family_size,
        "present_n": len(present),
        "state": "ok" if present else "family_unavailable",
        "decision_supported": False,
    }


# ── 8. Orchestrator ─────────────────────────────────────────────────────────


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping, got {type(value).__name__}")
    return value


def _contrast_id(contrast: Any) -> str:
    _require_mapping(contrast, "contrast")
    contrast_id = contrast.get("id")
    if not _exact_str(contrast_id) or contrast_id not in _CONTRAST_IDS:
        _refuse("contrast_set_drift", f"unregistered contrast id {_safe_repr(contrast_id)}")
    return contrast_id


def _registered_int(registration: Mapping[str, Any], path: tuple[str, ...]) -> int:
    node: Any = registration
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            _refuse("registered_constant_drift", f"missing registered key {'.'.join(path)}")
        node = node[key]
    if type(node) is not int:
        _refuse("registered_constant_drift", f"{'.'.join(path)} must be a plain int")
    return node


def _assert_registered_constants(registration: Mapping[str, Any]) -> None:
    inference = registration.get("inference")
    floors = registration.get("fold_floors")
    h5 = registration.get("h5")
    for block, expected, label in (
        (inference, _REGISTERED_INFERENCE, "inference"),
        (floors, _REGISTERED_FLOORS, "fold_floors"),
        (h5, _REGISTERED_H5, "h5"),
    ):
        if not isinstance(block, Mapping):
            _refuse("registered_constant_drift", f"registration.{label} must be a mapping")
        for key, value in expected.items():
            actual = block.get(key)
            if actual != value:
                _refuse(
                    "registered_constant_drift",
                    f"{label}.{key} drifted: registered {_safe_repr(actual)} != pinned {_safe_repr(value)}",
                )
    margins = h5.get("margin_sensitivity")
    if not _is_sequence(margins) or tuple(float(m) for m in margins) != _REGISTERED_MARGINS:
        _refuse(
            "registered_constant_drift",
            f"h5.margin_sensitivity drifted: {_safe_repr(margins)}",
        )


def _assert_contrast_set(comparisons: Mapping[str, Any], registration: Mapping[str, Any]) -> list[Any]:
    contrasts = comparisons.get("contrasts")
    if not _is_sequence(contrasts):
        _refuse("contrast_set_drift", "comparisons.contrasts must be a sequence")
    if len(contrasts) != _FAMILY_SIZE:
        _refuse(
            "contrast_set_drift",
            f"expected {_FAMILY_SIZE} registered contrasts, got {len(contrasts)}",
        )
    registered = {row["id"]: row for row in registration["contrasts"]}
    for contrast in contrasts:
        _require_mapping(contrast, "contrast")
        contrast_id = contrast.get("id")
        if contrast_id not in registered:
            _refuse("contrast_set_drift", f"unregistered contrast id {_safe_repr(contrast_id)}")
        spec = registered[contrast_id]
        for field, registered_field in (
            ("lane", "lane"),
            ("left", "left"),
            ("right", "right"),
            ("registered_direction", "direction"),
        ):
            if contrast.get(field) != spec[registered_field]:
                _refuse(
                    "contrast_set_drift",
                    f"{contrast_id}.{field} drifted from the registered contrast set",
                )
    if [contrast["id"] for contrast in contrasts] != list(_CONTRAST_IDS):
        _refuse("contrast_set_drift", "contrast order drifted from the registered set")
    return list(contrasts)


def run_primary_inference(
    comparisons: Any,
    *,
    registration: Any,
    expected_registration_hash: Any,
) -> dict[str, Any]:
    """Per-contrast inference plus the single registered BH family.

    Gate order is load-bearing and mirrors F8's precedence: the F7 registration
    gate fires BEFORE any input is touched, then the runtime dependency gate,
    then registered-constant drift, then contrast-set drift. Only then is the
    comparisons payload read.
    """
    verified_hash = require_registration_hash(
        registration, expected_registration_hash
    )
    if scipy.__version__ != EXPECTED_SCIPY_VERSION:
        _refuse(
            "dependency_version_drift",
            f"scipy {scipy.__version__} != pinned {EXPECTED_SCIPY_VERSION}",
        )
    _assert_registered_constants(registration)
    _require_mapping(comparisons, "comparisons")
    # The comparisons artifact's own declared provenance is part of the frozen
    # input contract: a stale artifact must be refused, never silently relabelled
    # with the currently verified hash on output.
    declared_hash = comparisons.get("registration_hash")
    if declared_hash != verified_hash:
        _refuse(
            "preregistration_missing",
            f"comparisons declares registration hash {_safe_repr(declared_hash)}, verified {verified_hash}",
        )
    contrasts = _assert_contrast_set(comparisons, registration)

    q = registration["inference"]["fdr_q"]
    h5_floor = registration["fold_floors"]["h5_lane"]
    delta0_registered = registration["h5"]["boundary_delta0"]

    results: list[dict[str, Any]] = []
    primary_p: dict[str, float | None] = {}
    margin_p: dict[float, dict[str, float | None]] = {
        margin: {} for margin in _REGISTERED_MARGINS
    }

    for contrast in contrasts:
        contrast_id = contrast["id"]
        lane = contrast["lane"]
        pooled = pool_paired_deltas(contrast, registration=registration)
        universe = build_cluster_universe(contrast)
        distribution = cluster_bootstrap_distribution(
            contrast, registration=registration
        )
        deltas = distribution["deltas"]
        observed = pooled["pooled_delta"]
        interval = bca_interval(
            deltas,
            observed=observed if observed is not None else 0.0,
            jackknife=_jackknife_pooled(universe),
        )
        permutation = cluster_permutation_p(contrast, registration=registration)

        if lane == "h5":
            ni = shifted_null_ni_p(
                deltas,
                observed=observed if observed is not None else 0.0,
                delta0=delta0_registered,
            )
            sensitivity: dict[float, dict[str, Any]] = {}
            for margin in _REGISTERED_MARGINS:
                leaf = shifted_null_ni_p(
                    deltas,
                    observed=observed if observed is not None else 0.0,
                    delta0=-margin,
                )
                sensitivity[margin] = leaf
                margin_p[margin][contrast_id] = leaf["p_ni"]
            primary_p[contrast_id] = sensitivity[_REGISTERED_H5["margin_m"]]["p_ni"]
        else:
            # NI is a registered H5-lane test; no NI distribution is constructed
            # for a model lane, so the record is honestly unavailable rather than
            # carrying a number that was never a registered quantity.
            ni = shifted_null_ni_p(
                None, observed=0.0, delta0=delta0_registered
            )
            sensitivity = {}
            for margin in _REGISTERED_MARGINS:
                margin_p[margin][contrast_id] = permutation["p_two"]
            primary_p[contrast_id] = permutation["p_two"]

        results.append(
            {
                "id": contrast_id,
                "lane": lane,
                "pooled": pooled,
                "interval": interval,
                "permutation": permutation,
                "ni": ni,
                "margin_sensitivity": sensitivity,
                "decision_supported": False,
            }
        )

    margin_adjusted = {
        margin: benjamini_hochberg(
            margin_p[margin], q=q, family_size=_FAMILY_SIZE
        )
        for margin in _REGISTERED_MARGINS
    }
    fdr = benjamini_hochberg(primary_p, q=q, family_size=_FAMILY_SIZE)

    for contrast in results:
        if contrast["lane"] != "h5":
            continue
        lower_bound = contrast["interval"]["one_sided_lower_95"]
        floor_met = contrast["pooled"]["evaluable_folds"] >= h5_floor
        rebuilt: dict[float, dict[str, Any]] = {}
        for margin, leaf in contrast["margin_sensitivity"].items():
            adjusted = margin_adjusted[margin]["adjusted"][contrast["id"]]
            # ni_met is a conjunction of three REGISTERED facts and is always a
            # bool. False means NOT ESTABLISHED — never "refuted".
            ni_met = bool(
                floor_met
                and lower_bound is not None
                and lower_bound > -margin
                and adjusted is not None
                and adjusted <= q
            )
            rebuilt[margin] = {
                "p_ni": leaf["p_ni"],
                "adjusted_p_ni": adjusted,
                "delta0": leaf["delta0"],
                "ni_met": ni_met,
                "state": leaf["state"],
                "decision_supported": False,
            }
        contrast["margin_sensitivity"] = rebuilt

    return {
        "registration_hash": verified_hash,
        "provenance": {
            "scipy_version": scipy.__version__,
            "numpy_version": np.__version__,
            "seed_material_root": _SEED_ROOT,
            "decision_supported": False,
        },
        "contrasts": results,
        "fdr": fdr,
        "decision_supported": False,
    }
