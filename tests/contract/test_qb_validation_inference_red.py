"""QB-1 D3-d inference behavioral RED.

Framing authority: ``claude_d3d_framing_v9.md`` (CLEAR 2026-07-24).
The study has not run. H2 QB rushing production remains UNDER TEST and is
exercised with mechanically identical inference behavior.

This slice intentionally adds no parked seam. The existing PARKED_SEAMS ratchet
stays at nine; D3-d is anchored by the closed public contract in
``src/dynasty_genius/eval/qb_validation/inference.py``.
"""

from __future__ import annotations

import copy
import importlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import scipy
from numpy.random import PCG64, Generator, SeedSequence

_INFERENCE_MODULE = "src.dynasty_genius.eval.qb_validation.inference"
_REGISTRATION_PATH = (
    Path(__file__).parents[2]
    / "docs"
    / "validation"
    / "2026-07-21-qb-1-study-registration.json"
)
_MODEL_FOLDS = tuple(range(2018, 2026))
_H5_FOLDS = (2021, 2022, 2023, 2024)
_PUBLIC_FUNCTIONS = (
    "pool_paired_deltas",
    "build_cluster_universe",
    "cluster_bootstrap_distribution",
    "bca_interval",
    "cluster_permutation_p",
    "shifted_null_ni_p",
    "benjamini_hochberg",
)
_CONTRAST_IDS = tuple(f"c{i:02d}" for i in range(1, 15))
_GOLDEN_DRAW_DIGESTS = {
    "bootstrap": {
        "c01": "f8a76e08fa759833e073895c53cbe955d7ed909219f27aeba6387e994d0a22bb",
        "c02": "560897c76f55a71a2a522ac83ae84e698ae75bbe29244e1c4dd01a11a836169e",
        "c03": "3ab05db0e5248f5dcbfbbda854f64c1fbfebf7501593b0778062144459e5f326",
        "c04": "31187f28ccfd9df356458068f07e071adb1c57b2a04cebdcbc29b0c36088fd56",
        "c05": "d4df648431f180a19d06f1d281a0ff9bf428a84129d5ae7a669501567b077fa9",
        "c06": "cc63467d0a48c9c6d13b05c24fa66c85bf9759794fbff4587a755efd5d963c6f",
        "c07": "24f29829dc83c714c8c19b5f72974852d300a8d06a5006468e4d2189247c9a33",
        "c08": "996430d0417eb83f92fe99fe0be2ac84f06cb012e4b7735b6548bfd4da2e55d3",
        "c09": "1ec00ce0ee56e85a4efc64ec043f51353ad4c3538e5c97d2070db72a077363b1",
        "c10": "be48a52731e5129e197f493ffa93772a1239a5841c8c98e78cfda3fc5e5a099c",
        "c11": "821cb685c5ada1fea4d49b2b78d5e996d80f7d07650b6a8ea66cd353e3511b14",
        "c12": "b1c37f5a334c6f56c08ae1c525784ae32567d9fe4ad3a5e521a97b4bb53944dd",
        "c13": "b4d7aa4b91de9628225e201da13391c2497b6bc2e93d562001b200c200f08a62",
        "c14": "9b53cd7c3f0b61e43fb0eeaa5bde62c0c7307f74a38f89829d248670b6109cc0",
    },
    "permutation": {
        "c01": "2f25f809fd3d2876ebac4fd7bbd38855895ae7b714428f3f78d393d5ba74a0e2",
        "c02": "2a902bcfa79d0bd1bccd112125032e767e485ccc4f3d41f022b703f03590629b",
        "c03": "49f0c6f1b8a11f762be491bd6a46f518e7907c029863cd11e5ddba0b8b886724",
        "c04": "33d8988d386448325c92d840c70d7f48c97fe93b2974ab57d16111972637d26a",
        "c05": "f3ce1e526e81b2563464b360074f25b0ce0c86ee91dbea85ddfa68bb5bd1e0c0",
        "c06": "efa88edfcdf8158f8356f61c647908bbb5812fd6f48a79abf6ef4358535f7f53",
        "c07": "cf76d77c3c6e93380e25f59b72841501546f759f2eb43abe545bb5383e9a3792",
        "c08": "71fa97d385cb655e2ea176d2832f5b5248a1b0bb090b1f0420482c313cb1900b",
        "c09": "c6f9d4017227c766041b2a70925df9e74cfcb1cad487289ce4e4767971146c1a",
        "c10": "98a30c4cca4b81e94d26927c21c193288805ace5c672ccb647634e58ee8bb462",
        "c11": "41bc8e7cfd726a60e660b1c0ad01a0c31307cba364da95d1be32edfe00aa0803",
        "c12": "899eecfd35fdcf1d0838cd7abeb117d5ebad15fd4be27830da503a608d6b7291",
        "c13": "166294559a5a72bcfa441b0066aabaeeb9ee0c07cc62a79bbc764c6408a1b330",
        "c14": "bd1a9128f46cc8006708cb461be3197ef7035e61fae85cc933063732a32a6c8e",
    },
}


def _inference():
    try:
        return importlib.import_module(_INFERENCE_MODULE)
    except ModuleNotFoundError as exc:
        pytest.fail(f"D3-d public module missing: {_INFERENCE_MODULE}: {exc}")


def _study_module():
    return importlib.import_module("src.dynasty_genius.eval.qb_validation")


def _registration() -> dict[str, Any]:
    return json.loads(_REGISTRATION_PATH.read_text(encoding="utf-8"))


def _registration_hash(registration: dict[str, Any]) -> str:
    return _study_module().build_registration(registration)["sha256"]


def _contrast_spec(contrast_id: str) -> dict[str, Any]:
    return copy.deepcopy(
        next(
            row
            for row in _registration()["contrasts"]
            if row["id"] == contrast_id
        )
    )


def _player_ids(n: int, *, start: int = 0) -> list[str]:
    return [f"p{i:03d}" for i in range(start, start + n)]


def _lane(
    lane: str,
    season: int,
    *,
    player_ids: list[str],
    order: str,
) -> dict[str, Any]:
    rows = []
    for index, player_id in enumerate(player_ids):
        y_true = float(index + 1)
        if order == "perfect":
            y_pred = y_true
        elif order == "reverse":
            y_pred = -y_true
        elif order == "flat":
            y_pred = 1.0
        else:  # pragma: no cover - fixture misuse
            raise AssertionError(f"unknown fixture order {order!r}")
        row = {
            "player_id": player_id,
            "target_season": season,
            "y_pred": y_pred,
            "y_true": y_true,
            "decision_supported": False,
        }
        if lane == "h5":
            row["source_provenance"] = "dynastyprocess_ecr_2qb"
        rows.append(row)
    result = {
        "test_season": season,
        "lane": lane,
        "n_predicted": len(rows),
        "predictions": rows,
        "decision_supported": False,
    }
    if lane == "h5":
        result["lane_source"] = "dynastyprocess_ecr_2qb"
    return result


def _fold_record(
    contrast_id: str,
    season: int,
    *,
    n: int = 20,
    start: int = 0,
    left_order: str = "perfect",
    right_order: str = "perfect",
) -> dict[str, Any]:
    spec = _contrast_spec(contrast_id)
    ids = _player_ids(n, start=start)
    return _study_module().score_comparisons(
        _lane(spec["left"], season, player_ids=ids, order=left_order),
        _lane(spec["right"], season, player_ids=ids, order=right_order),
        contrast=spec,
    )


def _fold_record_with_predictions(
    contrast_id: str,
    season: int,
    *,
    left_predictions: list[float],
    right_predictions: list[float],
) -> dict[str, Any]:
    assert len(left_predictions) == len(right_predictions)
    spec = _contrast_spec(contrast_id)
    ids = _player_ids(len(left_predictions))
    left = _lane(spec["left"], season, player_ids=ids, order="perfect")
    right = _lane(spec["right"], season, player_ids=ids, order="perfect")
    for row, prediction in zip(
        left["predictions"], left_predictions, strict=True
    ):
        row["y_pred"] = prediction
    for row, prediction in zip(
        right["predictions"], right_predictions, strict=True
    ):
        row["y_pred"] = prediction
    return _study_module().score_comparisons(
        left,
        right,
        contrast=spec,
    )


def _contrast_record(
    contrast_id: str,
    *,
    per_fold: list[dict[str, Any]] | None = None,
    empty: bool = False,
) -> dict[str, Any]:
    spec = _contrast_spec(contrast_id)
    folds = _H5_FOLDS if spec["lane"] == "h5" else _MODEL_FOLDS
    if per_fold is None:
        count = 0 if empty else 20
        per_fold = [
            _fold_record(contrast_id, season, n=count)
            for season in folds
        ]
    return {
        "id": spec["id"],
        "lane": spec["lane"],
        "left": spec["left"],
        "right": spec["right"],
        "registered_direction": spec["direction"],
        "per_fold": per_fold,
        "folds_present": len(per_fold),
        "decision_supported": False,
    }


def _all_comparisons(*, empty: bool) -> dict[str, Any]:
    registration = _registration()
    return {
        "registration_hash": _registration_hash(registration),
        "contrasts": [
            _contrast_record(contrast_id, empty=empty)
            for contrast_id in _CONTRAST_IDS
        ],
        "decision_supported": False,
    }


def _two_fold_signal_contrast() -> dict[str, Any]:
    """Two admitted folds plus six legitimate evidence-poverty exclusions."""
    per_fold = [
        _fold_record(
            "c01",
            2018,
            n=20,
            left_order="perfect",
            right_order="reverse",
        ),
        _fold_record(
            "c01",
            2019,
            n=40,
            left_order="perfect",
            right_order="perfect",
        ),
    ]
    per_fold.extend(
        _fold_record("c01", season, n=0)
        for season in _MODEL_FOLDS[2:]
    )
    return _contrast_record("c01", per_fold=per_fold)


def _failure_reason(exc_info: pytest.ExceptionInfo[BaseException]) -> str:
    reason = getattr(exc_info.value, "reason", None)
    assert isinstance(reason, str) and reason
    return reason


def _mapping_paths(value: Any, path: tuple[Any, ...] = ()):
    if isinstance(value, Mapping):
        yield path, value
        for key, nested in value.items():
            yield from _mapping_paths(nested, (*path, key))
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            yield from _mapping_paths(nested, (*path, index))


def _assert_total_classification(
    value: Mapping[str, Any],
    *,
    record_paths: set[tuple[Any, ...]],
    container_paths: set[tuple[Any, ...]],
) -> None:
    """V6: every mapping is exactly one declared record or pure container."""
    seen = {path for path, _ in _mapping_paths(value)}
    assert record_paths.isdisjoint(container_paths)
    assert seen == record_paths | container_paths
    for path, mapping in _mapping_paths(value):
        if path in record_paths:
            assert mapping.get("decision_supported") is False
        else:
            assert path in container_paths
            assert "decision_supported" not in mapping


def _assert_no_support_status(value: Any) -> None:
    if isinstance(value, Mapping):
        assert "support_status" not in value
        for nested in value.values():
            _assert_no_support_status(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _assert_no_support_status(nested)


def _drives_states(surface: str, *states: str):
    """Attach row-local v9 coverage bookkeeping to a behavioral test."""

    def decorate(function):
        driven = {
            key: set(values)
            for key, values in getattr(
                function, "_d3d_driven_states", {}
            ).items()
        }
        driven.setdefault(surface, set()).update(states)
        function._d3d_driven_states = driven
        return function

    return decorate


def _drives_refusals(*reasons: str):
    """Attach row-local v9 refusal bookkeeping to a behavioral test."""

    def decorate(function):
        driven = set(
            getattr(function, "_d3d_driven_refusals", set())
        )
        driven.update(reasons)
        function._d3d_driven_refusals = driven
        return function

    return decorate


def _expected_fixed_m_bh(
    p_by_contrast: dict[str, float | None],
    *,
    family_size: int = 14,
) -> dict[str, float | None]:
    present = sorted(
        (
            (contrast_id, p_value)
            for contrast_id, p_value in p_by_contrast.items()
            if p_value is not None
        ),
        key=lambda item: (item[1], item[0]),
    )
    adjusted: dict[str, float | None] = {
        contrast_id: None for contrast_id in _CONTRAST_IDS
    }
    running = 1.0
    for rank in range(len(present), 0, -1):
        contrast_id, p_value = present[rank - 1]
        running = min(running, family_size * p_value / rank, 1.0)
        adjusted[contrast_id] = running
    return adjusted


class _ExplodingComparisons(dict):
    def _explode(self, *args, **kwargs):
        raise AssertionError("comparisons accessed before the required gate")

    __getitem__ = _explode
    __iter__ = _explode
    __len__ = _explode
    get = _explode
    items = _explode
    keys = _explode
    values = _explode


class _HostileStr(str):
    def _explode(self, *args, **kwargs):
        raise AssertionError("hostile identity method invoked")

    __hash__ = _explode
    __eq__ = _explode
    __repr__ = _explode
    __str__ = _explode


def _install_fast_orchestrator_primitives(monkeypatch, inference):
    """Stub separately tested numerics while retaining public global lookups."""
    calls: dict[str, list[Any]] = {
        "pool": [],
        "universe": [],
        "bootstrap": [],
        "interval": [],
        "permutation": [],
        "ni": [],
        "bh": [],
    }
    real_pool = inference.pool_paired_deltas
    real_universe = inference.build_cluster_universe
    real_bh = inference.benjamini_hochberg

    def spy_pool(contrast, *, registration):
        calls["pool"].append(contrast["id"])
        return real_pool(contrast, registration=registration)

    def spy_universe(contrast):
        calls["universe"].append(contrast["id"])
        return real_universe(contrast)

    def fake_bootstrap(contrast, *, registration):
        calls["bootstrap"].append(contrast["id"])
        return {
            "deltas": (-0.10, 0.00, 0.10, 0.20) * 2_500,
            "B": 10_000,
            "seed_material": [20260716, 0, int(contrast["id"][1:])],
            "n_clusters": 20,
            "state": "ok",
            "decision_supported": False,
        }

    def fake_interval(distribution, *, observed, jackknife):
        calls["interval"].append(len(jackknife))
        return {
            "ci95_low": -0.04,
            "ci95_high": 0.20,
            "one_sided_lower_95": -0.03,
            "z0": 0.0,
            "acceleration": 0.0,
            "state": "ok",
            "decision_supported": False,
        }

    def fake_permutation(contrast, *, registration):
        calls["permutation"].append(contrast["id"])
        return {
            "p_two": 500 / 10_001,
            "B": 10_000,
            "n_extreme": 499,
            "state": "ok",
            "decision_supported": False,
        }

    def fake_ni(distribution, *, observed, delta0):
        calls["ni"].append(delta0)
        numerators = {
            -0.025: 2_000,
            -0.05: 500,
            -0.10: 100,
        }
        numerator = numerators[delta0]
        return {
            "p_ni": numerator / 10_001,
            "delta0": delta0,
            "n_extreme": numerator - 1,
            "state": "ok",
            "decision_supported": False,
        }

    def spy_bh(p_by_contrast, *, q, family_size):
        calls["bh"].append(
            (family_size, frozenset(p_by_contrast))
        )
        return real_bh(
            p_by_contrast,
            q=q,
            family_size=family_size,
        )

    monkeypatch.setattr(inference, "pool_paired_deltas", spy_pool)
    monkeypatch.setattr(inference, "build_cluster_universe", spy_universe)
    monkeypatch.setattr(
        inference, "cluster_bootstrap_distribution", fake_bootstrap
    )
    monkeypatch.setattr(inference, "bca_interval", fake_interval)
    monkeypatch.setattr(
        inference, "cluster_permutation_p", fake_permutation
    )
    monkeypatch.setattr(inference, "shifted_null_ni_p", fake_ni)
    monkeypatch.setattr(inference, "benjamini_hochberg", spy_bh)
    return calls


def test_d3d_public_surface_and_pinned_constants_exist() -> None:
    inference = _inference()
    for name in (*_PUBLIC_FUNCTIONS, "run_primary_inference"):
        assert callable(getattr(inference, name)), name
    assert inference.EXPECTED_SCIPY_VERSION == "1.17.1"
    assert isinstance(inference.GOLDEN_FIXTURE, Mapping)
    assert inference.STATE_VOCABULARIES == {
        "pooling": ("ok", "no_contributing_folds"),
        "bootstrap": (
            "ok",
            "no_contributing_folds",
            "replicate_degenerate",
        ),
        "bca": (
            "ok",
            "distribution_unavailable",
            "bca_bias_undefined",
            "jackknife_degenerate",
        ),
        "permutation": (
            "ok",
            "no_contributing_folds",
            "replicate_degenerate",
        ),
        "ni": ("ok", "distribution_unavailable"),
        "bh": ("ok", "family_unavailable"),
    }
    assert inference.REFUSAL_REASONS == frozenset(
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


def test_d3d_wrong_object_kinds_fail_loud_with_type_error() -> None:
    inference = _inference()
    registration = _registration()
    with pytest.raises(TypeError):
        inference.pool_paired_deltas(None, registration=registration)
    with pytest.raises(TypeError):
        inference.build_cluster_universe(None)
    with pytest.raises(TypeError):
        inference.cluster_bootstrap_distribution(
            None, registration=registration
        )
    with pytest.raises(TypeError):
        inference.bca_interval(
            "not-a-distribution", observed=0.0, jackknife=(0.0, 1.0)
        )
    with pytest.raises(TypeError):
        inference.cluster_permutation_p(None, registration=registration)
    with pytest.raises(TypeError):
        inference.shifted_null_ni_p(
            "not-a-distribution", observed=0.0, delta0=-0.05
        )
    with pytest.raises(TypeError):
        inference.benjamini_hochberg(None, q=0.10, family_size=14)


@_drives_states("pooling", "ok")
def test_d3d_pooling_uses_common_pool_weights_and_lossless_exclusions() -> None:
    inference = _inference()
    result = inference.pool_paired_deltas(
        _two_fold_signal_contrast(), registration=_registration()
    )
    assert set(result) == {
        "pooled_delta",
        "state",
        "contributing_folds",
        "excluded_folds",
        "weights",
        "evaluable_folds",
        "decision_supported",
    }
    assert result["state"] == "ok"
    assert result["contributing_folds"] == [2018, 2019]
    assert result["weights"] == {2018: 20, 2019: 40}
    assert result["evaluable_folds"] == 2
    assert result["pooled_delta"] == pytest.approx(2.0 / 3.0)
    assert result["excluded_folds"] == [
        {
            "test_season": season,
            "reasons": (
                "empty_common_pool",
                "fold_starved",
                "degenerate_input",
            ),
            "decision_supported": False,
        }
        for season in _MODEL_FOLDS[2:]
    ]
    record_paths = {()}
    record_paths.update(
        {("excluded_folds", index) for index in range(6)}
    )
    _assert_total_classification(
        result,
        record_paths=record_paths,
        container_paths={("weights",)},
    )


@_drives_states("pooling", "no_contributing_folds")
def test_d3d_zero_contributing_folds_are_named_and_never_fabricated() -> None:
    inference = _inference()
    result = inference.pool_paired_deltas(
        _contrast_record("c01", empty=True),
        registration=_registration(),
    )
    assert result["state"] == "no_contributing_folds"
    assert result["pooled_delta"] is None
    assert result["contributing_folds"] == []
    assert result["weights"] == {}
    assert result["evaluable_folds"] == 0
    assert all(
        row["reasons"]
        == ("empty_common_pool", "fold_starved", "degenerate_input")
        for row in result["excluded_folds"]
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda fold: fold.update(common_pool_n=19),
        lambda fold: fold.update(fold_starved=True),
        lambda fold: fold["degeneracy"]["left"].update(
            metrics_allowed=False
        ),
        lambda fold: fold.update(spearman_left=True),
        lambda fold: fold.update(paired_delta=0.25),
        lambda fold: fold["paired_evidence"].pop(),
        lambda fold: fold.update(test_season=2025),
        lambda fold: fold["paired_evidence"].append(
            copy.deepcopy(fold["paired_evidence"][0])
        ),
    ],
    ids=(
        "common-pool-n",
        "starvation-identity",
        "degeneracy-side",
        "exact-finite-numeric",
        "delta-equality",
        "evidence-length",
        "fold-key",
        "evidence-uniqueness",
    ),
)
@_drives_refusals("fold_record_inconsistent")
def test_d3d_non_null_delta_never_bypasses_fold_reconciliation(mutate) -> None:
    inference = _inference()
    contrast = _two_fold_signal_contrast()
    mutate(contrast["per_fold"][0])
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.pool_paired_deltas(
            contrast, registration=_registration()
        )
    assert _failure_reason(exc_info) == "fold_record_inconsistent"


def test_d3d_cluster_universe_is_sorted_player_keyed_and_record_total() -> None:
    inference = _inference()
    contrast = _two_fold_signal_contrast()
    result = inference.build_cluster_universe(contrast)
    assert set(result) == {
        "player_ids",
        "n_clusters",
        "rows_by_player",
        "decision_supported",
    }
    assert result["player_ids"] == tuple(sorted(_player_ids(40)))
    assert result["n_clusters"] == 40
    assert set(result["rows_by_player"]) == set(result["player_ids"])
    assert len(result["rows_by_player"]["p000"]) == 2
    assert len(result["rows_by_player"]["p039"]) == 1
    for player_id, rows in result["rows_by_player"].items():
        assert all(
            set(row)
            == {
                "test_season",
                "left_pred",
                "right_pred",
                "y_true",
                "decision_supported",
            }
            for row in rows
        )
        assert all(row["decision_supported"] is False for row in rows)
        assert all(type(player_id) is str for _ in rows)

    record_paths = {()}
    for player_id, rows in result["rows_by_player"].items():
        record_paths.update(
            {
                ("rows_by_player", player_id, index)
                for index in range(len(rows))
            }
        )
    _assert_total_classification(
        result,
        record_paths=record_paths,
        container_paths={("rows_by_player",)},
    )


@_drives_refusals("non_plain_identity_key", "non_finite_evidence")
def test_d3d_cluster_universe_refuses_hostile_and_nonfinite_evidence() -> None:
    inference = _inference()
    contrast = _two_fold_signal_contrast()
    contrast["per_fold"][0]["paired_evidence"][0]["player_id"] = _HostileStr(
        "p000"
    )
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.build_cluster_universe(contrast)
    assert _failure_reason(exc_info) == "non_plain_identity_key"
    assert len(str(exc_info.value)) < 500

    contrast = _two_fold_signal_contrast()
    contrast["per_fold"][0]["paired_evidence"][0]["left_pred"] = math.inf
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.build_cluster_universe(contrast)
    assert _failure_reason(exc_info) == "non_finite_evidence"


@_drives_refusals(
    "unexpected_fold",
    "unexpected_lane",
    "duplicate_evidence_key",
)
def test_d3d_fold_lane_and_cross_fold_duplicate_refusals_are_named() -> None:
    inference = _inference()

    contrast = _two_fold_signal_contrast()
    contrast["per_fold"].append(
        _fold_record("c01", 2026, n=20)
    )
    contrast["folds_present"] = 9
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.pool_paired_deltas(
            contrast, registration=_registration()
        )
    assert _failure_reason(exc_info) == "unexpected_fold"

    contrast = _two_fold_signal_contrast()
    contrast["lane"] = "not-a-lane"
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.pool_paired_deltas(
            contrast, registration=_registration()
        )
    assert _failure_reason(exc_info) == "unexpected_lane"

    contrast = _two_fold_signal_contrast()
    contrast["per_fold"][1]["paired_evidence"][0][
        "target_season"
    ] = 2018
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.build_cluster_universe(contrast)
    assert _failure_reason(exc_info) == "duplicate_evidence_key"


@_drives_states("bootstrap", "ok")
def test_d3d_bootstrap_is_clustered_deterministic_and_reweights_draws() -> None:
    inference = _inference()
    contrast = _two_fold_signal_contrast()
    result = inference.cluster_bootstrap_distribution(
        contrast, registration=_registration()
    )
    assert set(result) == {
        "deltas",
        "B",
        "seed_material",
        "n_clusters",
        "state",
        "decision_supported",
    }
    assert result["state"] == "ok"
    assert result["B"] == 10_000
    assert result["seed_material"] == [20260716, 0, 1]
    assert result["n_clusters"] == 40
    assert isinstance(result["deltas"], tuple)
    assert len(result["deltas"]) == result["B"]

    draws = Generator(
        PCG64(SeedSequence([20260716, 0, 1]))
    ).integers(
        low=0,
        high=40,
        size=(10_000, 40),
        dtype=np.int64,
    )
    for index, draw in enumerate(draws):
        fold_2018_weight = int(np.count_nonzero(draw < 20))
        if (
            1 < fold_2018_weight < 20
            and len(set(draw[draw < 20].tolist())) > 1
            and len(set(draw.tolist())) > 1
        ):
            expected = (2.0 * fold_2018_weight) / (
                fold_2018_weight + 40
            )
            assert result["deltas"][index] == pytest.approx(expected)
            break
    else:  # pragma: no cover - pinned stream guarantees a witness
        raise AssertionError("pinned stream lacked a below-20 admitted-fold draw")

    repeated = inference.cluster_bootstrap_distribution(
        copy.deepcopy(contrast), registration=_registration()
    )
    assert repeated == result
    _assert_total_classification(
        result,
        record_paths={()},
        container_paths=set(),
    )


@_drives_states("bootstrap", "no_contributing_folds")
def test_d3d_bootstrap_nullability_biconditional_is_closed() -> None:
    inference = _inference()
    unavailable = inference.cluster_bootstrap_distribution(
        _contrast_record("c01", empty=True),
        registration=_registration(),
    )
    assert unavailable["state"] == "no_contributing_folds"
    assert unavailable["deltas"] is None
    assert (unavailable["deltas"] is None) is (
        unavailable["state"] != "ok"
    )


@_drives_states("bootstrap", "replicate_degenerate")
def test_d3d_bootstrap_refuses_any_undefined_replicate() -> None:
    """P8 permits no retry, drop, short distribution, or tolerance."""
    first_draw = Generator(
        PCG64(SeedSequence([20260716, 0, 1]))
    ).integers(
        low=0,
        high=20,
        size=(10_000, 20),
        dtype=np.int64,
    )[0]
    missing = sorted(set(range(20)) - set(first_draw.tolist()))
    assert missing

    left_predictions = [0.0] * 20
    left_predictions[missing[0]] = 1.0
    right_predictions = [float(index + 1) for index in range(20)]
    admitted = _fold_record_with_predictions(
        "c01",
        2018,
        left_predictions=left_predictions,
        right_predictions=right_predictions,
    )
    assert admitted["paired_delta"] is not None
    assert admitted["degeneracy"]["left"]["metrics_allowed"] is True
    assert len({left_predictions[index] for index in first_draw}) == 1

    per_fold = [admitted]
    per_fold.extend(
        _fold_record("c01", season, n=0)
        for season in _MODEL_FOLDS[1:]
    )
    inference = _inference()
    result = inference.cluster_bootstrap_distribution(
        _contrast_record("c01", per_fold=per_fold),
        registration=_registration(),
    )
    assert result["B"] == 10_000
    assert result["n_clusters"] == 20
    assert result["state"] == "replicate_degenerate"
    assert result["deltas"] is None
    assert (result["deltas"] is None) is (result["state"] != "ok")
    assert result["decision_supported"] is False


@_drives_states(
    "bca",
    "ok",
    "bca_bias_undefined",
    "jackknife_degenerate",
)
def test_d3d_bca_uses_midrank_and_refuses_degenerate_endpoints() -> None:
    inference = _inference()
    tied = inference.bca_interval(
        (0.0, 1.0, 1.0, 2.0),
        observed=1.0,
        jackknife=(0.0, 1.0, 2.0),
    )
    assert set(tied) == {
        "ci95_low",
        "ci95_high",
        "one_sided_lower_95",
        "z0",
        "acceleration",
        "state",
        "decision_supported",
    }
    assert tied["state"] == "ok"
    assert tied["z0"] == pytest.approx(0.0, abs=1e-15)
    assert tied["acceleration"] == pytest.approx(0.0, abs=1e-15)

    unclamped = inference.bca_interval(
        (1.1, 1.2, 1.3, 1.4, 1.5),
        observed=1.3,
        jackknife=(1.1, 1.3, 1.5),
    )
    assert unclamped["state"] == "ok"
    assert unclamped["ci95_high"] > 1.0

    bias_undefined = inference.bca_interval(
        (0.0, 0.1, 0.2),
        observed=1.0,
        jackknife=(0.0, 0.5, 1.0),
    )
    assert bias_undefined["state"] == "bca_bias_undefined"
    assert bias_undefined["ci95_low"] is None
    assert bias_undefined["ci95_high"] is None
    assert bias_undefined["one_sided_lower_95"] is None

    jackknife_degenerate = inference.bca_interval(
        (0.0, 1.0, 2.0),
        observed=1.0,
        jackknife=(1.0, 1.0, 1.0),
    )
    assert jackknife_degenerate["state"] == "jackknife_degenerate"
    assert jackknife_degenerate["ci95_low"] is None
    _assert_total_classification(
        tied,
        record_paths={()},
        container_paths=set(),
    )


@_drives_states("bca", "distribution_unavailable")
def test_d3d_bca_unavailable_distribution_has_null_endpoints() -> None:
    inference = _inference()
    result = inference.bca_interval(
        None,
        observed=0.25,
        jackknife=(0.10, 0.20, 0.30),
    )
    assert result["state"] == "distribution_unavailable"
    assert result["ci95_low"] is None
    assert result["ci95_high"] is None
    assert result["one_sided_lower_95"] is None
    assert result["decision_supported"] is False


@_drives_states("permutation", "ok")
def test_d3d_permutation_uses_one_swap_per_union_cluster_and_exact_p() -> None:
    inference = _inference()
    contrast = _two_fold_signal_contrast()
    result = inference.cluster_permutation_p(
        contrast, registration=_registration()
    )
    assert set(result) == {
        "p_two",
        "B",
        "n_extreme",
        "state",
        "decision_supported",
    }
    assert result["state"] == "ok"
    assert result["B"] == 10_000

    masks = (
        Generator(PCG64(SeedSequence([20260716, 1, 1])))
        .random(size=(10_000, 40))
        < 0.5
    )
    first_fold_masks = masks[:, :20]
    expected_extreme = int(
        np.count_nonzero(
            np.all(first_fold_masks, axis=1)
            | np.all(~first_fold_masks, axis=1)
        )
    )
    assert result["n_extreme"] == expected_extreme
    assert result["p_two"] == (1 + expected_extreme) / 10_001
    _assert_total_classification(
        result,
        record_paths={()},
        container_paths=set(),
    )


@_drives_states("permutation", "no_contributing_folds")
def test_d3d_permutation_names_zero_contributing_folds() -> None:
    contrast = _contrast_record("c01", empty=True)
    assert all(
        fold["paired_delta"] is None for fold in contrast["per_fold"]
    )
    inference = _inference()
    result = inference.cluster_permutation_p(
        contrast,
        registration=_registration(),
    )
    assert set(result) == {
        "p_two",
        "B",
        "n_extreme",
        "state",
        "decision_supported",
    }
    assert result["B"] == 10_000
    assert result["state"] == "no_contributing_folds"
    assert result["p_two"] is None
    assert result["n_extreme"] is None
    assert result["decision_supported"] is False
    _assert_total_classification(
        result,
        record_paths={()},
        container_paths=set(),
    )


@_drives_states("permutation", "replicate_degenerate")
def test_d3d_permutation_refuses_any_undefined_replicate() -> None:
    """P8 forbids a p-value over fewer than the registered B replicates."""
    first_mask = (
        Generator(PCG64(SeedSequence([20260716, 1, 1])))
        .random(size=(10_000, 20))[0]
        < 0.5
    )
    assert first_mask.any()
    assert (~first_mask).any()

    left_predictions = [
        float(index + 1) if swap else 0.0
        for index, swap in enumerate(first_mask)
    ]
    right_predictions = [
        0.0 if swap else float(index + 1)
        for index, swap in enumerate(first_mask)
    ]
    admitted = _fold_record_with_predictions(
        "c01",
        2018,
        left_predictions=left_predictions,
        right_predictions=right_predictions,
    )
    assert admitted["paired_delta"] is not None
    assert admitted["degeneracy"]["left"]["metrics_allowed"] is True
    assert admitted["degeneracy"]["right"]["metrics_allowed"] is True
    swapped_left = [
        right_predictions[index] if swap else left_predictions[index]
        for index, swap in enumerate(first_mask)
    ]
    assert len(set(swapped_left)) == 1

    per_fold = [admitted]
    per_fold.extend(
        _fold_record("c01", season, n=0)
        for season in _MODEL_FOLDS[1:]
    )
    inference = _inference()
    result = inference.cluster_permutation_p(
        _contrast_record("c01", per_fold=per_fold),
        registration=_registration(),
    )
    assert result["B"] == 10_000
    assert result["state"] == "replicate_degenerate"
    assert result["p_two"] is None
    assert result["n_extreme"] is None
    assert result["decision_supported"] is False


@_drives_states("ni", "ok", "distribution_unavailable")
def test_d3d_shifted_null_ni_has_registered_sign_and_denominator() -> None:
    inference = _inference()
    distribution = (-0.10, 0.00, 0.10, 0.20)
    result = inference.shifted_null_ni_p(
        distribution,
        observed=0.10,
        delta0=-0.05,
    )
    shifted = [
        value - 0.10 - 0.05
        for value in distribution
    ]
    expected_extreme = sum(value >= 0.10 for value in shifted)
    assert set(result) == {
        "p_ni",
        "delta0",
        "n_extreme",
        "state",
        "decision_supported",
    }
    assert result["state"] == "ok"
    assert result["delta0"] == -0.05
    assert result["n_extreme"] == expected_extreme
    assert result["p_ni"] == (1 + expected_extreme) / 5

    unavailable = inference.shifted_null_ni_p(
        None,
        observed=0.10,
        delta0=-0.05,
    )
    assert unavailable["state"] == "distribution_unavailable"
    assert unavailable["p_ni"] is None
    _assert_total_classification(
        result,
        record_paths={()},
        container_paths=set(),
    )


@_drives_states("bh", "ok", "family_unavailable")
def test_d3d_bh_keeps_family_size_14_without_serialized_sentinels() -> None:
    inference = _inference()
    p_values = {
        contrast_id: (index + 1) / 100
        for index, contrast_id in enumerate(_CONTRAST_IDS)
    }
    p_values["c14"] = None
    result = inference.benjamini_hochberg(
        p_values,
        q=0.10,
        family_size=14,
    )
    assert set(result) == {
        "adjusted",
        "rejected",
        "family_size",
        "present_n",
        "state",
        "decision_supported",
    }
    assert result["state"] == "ok"
    assert result["family_size"] == 14
    assert result["present_n"] == 13
    assert result["adjusted"] == _expected_fixed_m_bh(p_values)
    assert result["adjusted"]["c14"] is None
    assert result["rejected"]["c14"] is False

    unavailable = inference.benjamini_hochberg(
        {contrast_id: None for contrast_id in _CONTRAST_IDS},
        q=0.10,
        family_size=14,
    )
    assert unavailable["state"] == "family_unavailable"
    assert unavailable["present_n"] == 0
    assert all(
        value is None for value in unavailable["adjusted"].values()
    )
    assert not any(unavailable["rejected"].values())
    _assert_total_classification(
        result,
        record_paths={()},
        container_paths={("adjusted",), ("rejected",)},
    )


@_drives_refusals("preregistration_missing")
def test_d3d_orchestrator_preserves_f7_reason_before_input_access() -> None:
    inference = _inference()
    registration = _registration()
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.run_primary_inference(
            _ExplodingComparisons(),
            registration=registration,
            expected_registration_hash="0" * 64,
        )
    assert _failure_reason(exc_info) == "preregistration_missing"


@_drives_refusals("dependency_version_drift")
def test_d3d_orchestrator_dependency_gate_is_second_and_exact(
    monkeypatch,
) -> None:
    inference = _inference()
    registration = _registration()
    monkeypatch.setattr(scipy, "__version__", "1.17.2")
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.run_primary_inference(
            _ExplodingComparisons(),
            registration=registration,
            expected_registration_hash=_registration_hash(registration),
        )
    assert _failure_reason(exc_info) == "dependency_version_drift"


@_drives_refusals("registered_constant_drift", "contrast_set_drift")
def test_d3d_orchestrator_refuses_constant_and_contrast_drift_in_order() -> None:
    inference = _inference()
    drifted = _registration()
    drifted["inference"]["bootstrap_B"] = 9_999
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.run_primary_inference(
            _ExplodingComparisons(),
            registration=drifted,
            expected_registration_hash=_registration_hash(drifted),
        )
    assert _failure_reason(exc_info) == "registered_constant_drift"

    registration = _registration()
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.run_primary_inference(
            {
                "registration_hash": _registration_hash(registration),
                "contrasts": [],
                "decision_supported": False,
            },
            registration=registration,
            expected_registration_hash=_registration_hash(registration),
        )
    assert _failure_reason(exc_info) == "contrast_set_drift"


def test_d3d_orchestrator_all_unavailable_is_total_and_no_verdict() -> None:
    inference = _inference()
    registration = _registration()
    result = inference.run_primary_inference(
        _all_comparisons(empty=True),
        registration=registration,
        expected_registration_hash=_registration_hash(registration),
    )
    assert set(result) == {
        "registration_hash",
        "provenance",
        "contrasts",
        "fdr",
        "decision_supported",
    }
    assert result["registration_hash"] == _registration_hash(registration)
    assert result["provenance"] == {
        "scipy_version": "1.17.1",
        "numpy_version": np.__version__,
        "seed_material_root": 20260716,
        "decision_supported": False,
    }
    assert len(result["contrasts"]) == 14
    assert [row["id"] for row in result["contrasts"]] == list(
        _CONTRAST_IDS
    )
    assert result["fdr"]["state"] == "family_unavailable"
    _assert_no_support_status(result)

    record_paths: set[tuple[Any, ...]] = {
        (),
        ("provenance",),
        ("fdr",),
    }
    container_paths: set[tuple[Any, ...]] = {
        ("fdr", "adjusted"),
        ("fdr", "rejected"),
    }
    for index, contrast in enumerate(result["contrasts"]):
        prefix = ("contrasts", index)
        expected_excluded = 4 if contrast["lane"] == "h5" else 8
        expected_margins = (
            {0.025, 0.05, 0.10}
            if contrast["lane"] == "h5"
            else set()
        )
        assert len(contrast["pooled"]["excluded_folds"]) == expected_excluded
        assert set(contrast["margin_sensitivity"]) == expected_margins
        for margin in expected_margins:
            leaf = contrast["margin_sensitivity"][margin]
            assert leaf["p_ni"] is None
            assert leaf["adjusted_p_ni"] is None
            assert type(leaf["ni_met"]) is bool
            assert leaf["ni_met"] is False
        record_paths.add(prefix)
        for field in ("pooled", "interval", "permutation", "ni"):
            record_paths.add((*prefix, field))
        container_paths.add((*prefix, "pooled", "weights"))
        for excluded_index in range(expected_excluded):
            record_paths.add(
                (*prefix, "pooled", "excluded_folds", excluded_index)
            )
        container_paths.add((*prefix, "margin_sensitivity"))
        for margin in expected_margins:
            record_paths.add(
                (*prefix, "margin_sensitivity", margin)
            )
    _assert_total_classification(
        result,
        record_paths=record_paths,
        container_paths=container_paths,
    )


def test_d3d_h2_contrasts_use_identical_inference_mechanics() -> None:
    inference = _inference()
    registration = _registration()
    result = inference.run_primary_inference(
        _all_comparisons(empty=True),
        registration=registration,
        expected_registration_hash=_registration_hash(registration),
    )
    by_id = {row["id"]: row for row in result["contrasts"]}
    for h2_id, control_id in (
        ("c02", "c01"),
        ("c05", "c07"),
        ("c06", "c07"),
        ("c09", "c08"),
    ):
        h2 = copy.deepcopy(by_id[h2_id])
        control = copy.deepcopy(by_id[control_id])
        for row in (h2, control):
            row.pop("id")
        assert h2 == control


def test_d3d_populated_h2_and_control_data_have_identical_inference() -> None:
    """H2 cannot be special-cased behind an all-unavailable coincidence."""
    registration = _registration()
    control = _contrast_record("c01", empty=False)
    h2 = _contrast_record("c02", empty=False)
    assert all(
        fold["paired_delta"] is not None
        for contrast in (control, h2)
        for fold in contrast["per_fold"]
    )
    inference = _inference()

    pooled_control = inference.pool_paired_deltas(
        control, registration=registration
    )
    pooled_h2 = inference.pool_paired_deltas(h2, registration=registration)
    assert pooled_h2 == pooled_control
    assert pooled_h2["state"] == "ok"
    assert pooled_h2["evaluable_folds"] == 8

    bootstrap_control = inference.cluster_bootstrap_distribution(
        control, registration=registration
    )
    bootstrap_h2 = inference.cluster_bootstrap_distribution(
        h2, registration=registration
    )
    for field in (
        "deltas",
        "B",
        "n_clusters",
        "state",
        "decision_supported",
    ):
        assert bootstrap_h2[field] == bootstrap_control[field]
    assert bootstrap_h2["state"] == "ok"
    assert set(bootstrap_h2["deltas"]) == {0.0}

    interval_control = inference.bca_interval(
        bootstrap_control["deltas"],
        observed=pooled_control["pooled_delta"],
        jackknife=(0.0,) * 20,
    )
    interval_h2 = inference.bca_interval(
        bootstrap_h2["deltas"],
        observed=pooled_h2["pooled_delta"],
        jackknife=(0.0,) * 20,
    )
    assert interval_h2 == interval_control
    assert interval_h2["state"] == "jackknife_degenerate"

    permutation_control = inference.cluster_permutation_p(
        control, registration=registration
    )
    permutation_h2 = inference.cluster_permutation_p(
        h2, registration=registration
    )
    assert permutation_h2 == permutation_control
    assert permutation_h2["n_extreme"] == 10_000
    assert permutation_h2["p_two"] == 1.0


def test_d3d_margin_sensitivity_reuses_distribution_and_runs_full_bh(
    monkeypatch,
) -> None:
    inference = _inference()
    registration = _registration()
    comparisons = _all_comparisons(empty=False)
    calls = _install_fast_orchestrator_primitives(
        monkeypatch, inference
    )

    result = inference.run_primary_inference(
        comparisons,
        registration=registration,
        expected_registration_hash=_registration_hash(registration),
    )
    assert calls["pool"] == list(_CONTRAST_IDS)
    assert calls["universe"] == list(_CONTRAST_IDS)
    assert calls["bootstrap"] == list(_CONTRAST_IDS)
    assert len(calls["interval"]) == 14
    assert calls["permutation"] == list(_CONTRAST_IDS)
    assert len(calls["bootstrap"]) == len(set(calls["bootstrap"])) == 14
    assert len(calls["bh"]) == 4
    assert all(
        family_size == 14 and ids == frozenset(_CONTRAST_IDS)
        for family_size, ids in calls["bh"]
    )
    assert set(calls["ni"]) == {-0.025, -0.05, -0.10}

    for contrast in result["contrasts"]:
        if contrast["lane"] == "model":
            assert contrast["margin_sensitivity"] == {}
            continue
        assert set(contrast["margin_sensitivity"]) == {0.025, 0.05, 0.10}
        for margin, leaf in contrast["margin_sensitivity"].items():
            assert leaf["decision_supported"] is False
            assert leaf["p_ni"] is not None
            assert leaf["adjusted_p_ni"] is not None
            assert leaf["ni_met"] is (
                contrast["pooled"]["evaluable_folds"]
                >= registration["fold_floors"]["h5_lane"]
                and -0.03 > -margin
                and leaf["adjusted_p_ni"]
                <= registration["inference"]["fdr_q"]
            )
    _assert_no_support_status(result)


def test_d3d_ni_met_is_false_when_h5_fold_floor_is_unmet(
    monkeypatch,
) -> None:
    """Spec v9:66 binds ni_met to floor AND lower bound AND adjusted p."""
    registration = _registration()
    comparisons = _all_comparisons(empty=False)
    c11 = next(
        row for row in comparisons["contrasts"] if row["id"] == "c11"
    )
    c11["per_fold"][2] = _fold_record("c11", 2023, n=0)
    c11["per_fold"][3] = _fold_record("c11", 2024, n=0)
    assert sum(
        fold["paired_delta"] is not None for fold in c11["per_fold"]
    ) == 2

    inference = _inference()
    _install_fast_orchestrator_primitives(monkeypatch, inference)
    result = inference.run_primary_inference(
        comparisons,
        registration=registration,
        expected_registration_hash=_registration_hash(registration),
    )
    c11_result = next(
        row for row in result["contrasts"] if row["id"] == "c11"
    )
    assert c11_result["pooled"]["evaluable_folds"] == 2
    assert (
        c11_result["pooled"]["evaluable_folds"]
        < registration["fold_floors"]["h5_lane"]
    )
    assert c11_result["interval"]["one_sided_lower_95"] == -0.03

    leaf = c11_result["margin_sensitivity"][0.05]
    assert -0.03 > -0.05
    assert leaf["adjusted_p_ni"] <= registration["inference"]["fdr_q"]
    assert type(leaf["ni_met"]) is bool
    assert leaf["ni_met"] is False


def test_d3d_rng_streams_and_canonical_digest_encodings_are_pinned() -> None:
    inference = _inference()
    assert inference.GOLDEN_FIXTURE["n_clusters"] == 8
    assert inference.GOLDEN_FIXTURE["B"] == 16
    assert inference.GOLDEN_FIXTURE["draw_digests"] == _GOLDEN_DRAW_DIGESTS


def test_d3d_behavioral_drive_coverage_matches_declared_vocabularies() -> None:
    driven_states: dict[str, set[str]] = {}
    driven_refusals: set[str] = set()
    for candidate in tuple(globals().values()):
        if not callable(candidate):
            continue
        if not getattr(candidate, "__name__", "").startswith("test_d3d_"):
            continue
        for surface, states in getattr(
            candidate, "_d3d_driven_states", {}
        ).items():
            driven_states.setdefault(surface, set()).update(states)
        driven_refusals.update(
            getattr(candidate, "_d3d_driven_refusals", set())
        )

    inference = _inference()
    declared_states = {
        surface: set(states)
        for surface, states in inference.STATE_VOCABULARIES.items()
    }
    assert driven_states == declared_states
    assert driven_refusals == set(inference.REFUSAL_REASONS)


def test_d3d_red_does_not_move_the_nine_seam_ratchet() -> None:
    red = importlib.import_module(
        "tests.contract.test_qb_validation_program_red"
    )
    assert set(red.PARKED_SEAMS) == {
        "F10",
        "F13",
        "F16",
        "F18",
        "F25",
        "F29",
        "F31",
        "F32",
        "F33",
    }
    assert len(red.PARKED_SEAMS) == 9


# ── D3-d GREEN review r1 disposition rows ───────────────────────────────────
# Codex binding review 2026-07-25: six reproduced residual families. Each row
# below was proven red against the r1 implementation for the stated reason
# before the repair. Permanent contract, not throwaway probes.


def _disjoint_two_fold_contrast() -> dict[str, Any]:
    """Two admitted folds over DISJOINT player sets: 40 clusters, 20 per fold."""
    per_fold = [
        _fold_record(
            "c01", 2018, n=20, start=0, left_order="perfect", right_order="reverse"
        ),
        _fold_record(
            "c01", 2019, n=20, start=20, left_order="perfect", right_order="reverse"
        ),
    ]
    per_fold.extend(
        _fold_record("c01", season, n=0) for season in _MODEL_FOLDS[2:]
    )
    return _contrast_record("c01", per_fold=per_fold)


@_drives_states("bootstrap", "replicate_degenerate")
def test_d3d_zero_row_admitted_fold_refuses_the_whole_distribution(
    monkeypatch,
) -> None:
    """P8: an observed fold that receives ZERO resampled rows is undefined.

    Dropping it silently changes the estimator mid-replicate — the observed fold
    set is fixed, so a replicate that cannot evaluate every admitted fold has no
    delta at all.
    """
    inference = _inference()
    registration = _registration()
    registration["inference"]["bootstrap_B"] = 1

    class _FixedGenerator:
        def integers(self, *, low, high, size, dtype):
            assert size == (1, 40)
            # Draw only the second fold's twenty clusters, twice each.
            return np.asarray([list(range(20, 40)) * 2], dtype=np.int64)

    monkeypatch.setattr(
        inference, "_generator", lambda procedure, contrast_id: _FixedGenerator()
    )
    result = inference.cluster_bootstrap_distribution(
        _disjoint_two_fold_contrast(), registration=registration
    )
    assert result["state"] == "replicate_degenerate"
    assert result["deltas"] is None
    assert result["decision_supported"] is False


@_drives_refusals("unexpected_fold")
def test_d3d_missing_registered_fold_seasons_are_refused() -> None:
    inference = _inference()
    contrast = _contrast_record(
        "c01",
        per_fold=[
            _fold_record("c01", season, n=20) for season in range(2018, 2023)
        ],
    )
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.pool_paired_deltas(contrast, registration=_registration())
    assert _failure_reason(exc_info) == "unexpected_fold"


@_drives_refusals("unexpected_fold")
def test_d3d_duplicate_fold_seasons_cannot_inflate_the_evaluable_floor() -> None:
    """Two unique H5 seasons must never masquerade as the registered four."""
    inference = _inference()
    contrast = _contrast_record(
        "c11",
        per_fold=[
            _fold_record("c11", 2021, n=20, start=0),
            _fold_record("c11", 2021, n=20, start=20),
            _fold_record("c11", 2022, n=20, start=40),
            _fold_record("c11", 2022, n=20, start=60),
        ],
    )
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.pool_paired_deltas(contrast, registration=_registration())
    assert _failure_reason(exc_info) == "unexpected_fold"


@_drives_refusals("fold_record_inconsistent")
def test_d3d_universe_refuses_non_colliding_fold_evidence_season_mismatch() -> None:
    """The duplicate-key row does not license disabling the season clause."""
    inference = _inference()
    contrast = _two_fold_signal_contrast()
    for row in contrast["per_fold"][0]["paired_evidence"]:
        row["target_season"] = 2020  # the 2020 fold is empty: no collision
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.build_cluster_universe(contrast)
    assert _failure_reason(exc_info) == "fold_record_inconsistent"


@_drives_refusals("preregistration_missing")
def test_d3d_orchestrator_refuses_stale_comparisons_registration_hash() -> None:
    inference = _inference()
    registration = _registration()
    comparisons = _all_comparisons(empty=True)
    comparisons["registration_hash"] = "f" * 64
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.run_primary_inference(
            comparisons,
            registration=registration,
            expected_registration_hash=_registration_hash(registration),
        )
    assert _failure_reason(exc_info) == "preregistration_missing"


@_drives_refusals("non_finite_evidence")
def test_d3d_non_finite_distribution_and_jackknife_members_are_refused() -> None:
    inference = _inference()
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(_study_module().QBValidationFailure) as exc_info:
            inference.bca_interval(
                (bad, -0.1, 0.0, 0.1), observed=0.0, jackknife=(0.0, 1.0, 2.0)
            )
        assert _failure_reason(exc_info) == "non_finite_evidence"
        with pytest.raises(_study_module().QBValidationFailure) as exc_info:
            inference.shifted_null_ni_p(
                (bad, -0.1, 0.0, 0.1), observed=0.0, delta0=-0.05
            )
        assert _failure_reason(exc_info) == "non_finite_evidence"
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.bca_interval(
            (0.0, 1.0, 2.0), observed=1.0, jackknife=(0.0, math.inf)
        )
    assert _failure_reason(exc_info) == "non_finite_evidence"
    with pytest.raises(TypeError):
        inference.bca_interval(
            (0.0, "not-a-float"), observed=0.0, jackknife=(0.0, 1.0)
        )


@_drives_refusals("contrast_set_drift", "registered_constant_drift")
def test_d3d_bh_materializes_fourteen_slots_and_validates_inputs() -> None:
    inference = _inference()

    partial = inference.benjamini_hochberg(
        {"c01": 0.01}, q=0.10, family_size=14
    )
    assert set(partial["adjusted"]) == set(_CONTRAST_IDS)
    assert set(partial["rejected"]) == set(_CONTRAST_IDS)
    assert partial["present_n"] == 1
    assert partial["adjusted"]["c14"] is None
    assert partial["rejected"]["c14"] is False

    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.benjamini_hochberg(
            {"not-a-contrast": 0.01}, q=0.10, family_size=14
        )
    assert _failure_reason(exc_info) == "contrast_set_drift"

    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.benjamini_hochberg({"c01": 0.01}, q=0.10, family_size=0)
    assert _failure_reason(exc_info) == "registered_constant_drift"

    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.benjamini_hochberg({"c01": 0.01}, q=2.0, family_size=14)
    assert _failure_reason(exc_info) == "registered_constant_drift"

    for bad in (math.nan, math.inf, 1.5, -0.5):
        with pytest.raises(_study_module().QBValidationFailure) as exc_info:
            inference.benjamini_hochberg(
                {"c01": bad}, q=0.10, family_size=14
            )
        assert _failure_reason(exc_info) == "non_finite_evidence"


# ── D3-d GREEN review r2 disposition rows ───────────────────────────────────
# Codex binding review r2 2026-07-25: stored statistics and folds_present must
# match the frozen record shape, not merely satisfy equality. Both close through
# the existing fold_record_inconsistent reason; no vocabulary change.


@pytest.mark.parametrize(
    "mutate",
    [
        lambda fold: fold.update(
            spearman_left=math.inf, paired_delta=math.inf
        ),
        lambda fold: fold.update(
            spearman_left=-math.inf, paired_delta=-math.inf
        ),
        lambda fold: fold.update(spearman_right=math.inf, paired_delta=-math.inf),
        lambda fold: fold.update(spearman_left=math.nan, paired_delta=math.nan),
        lambda fold: fold.update(
            spearman_left=1.0, spearman_right=-2.0, paired_delta=3.0
        ),
        lambda fold: fold.update(
            spearman_left=1.5, spearman_right=1.0, paired_delta=0.5
        ),
    ],
    ids=(
        "left-positive-inf",
        "left-negative-inf",
        "right-positive-inf",
        "left-nan",
        "right-below-domain",
        "left-above-domain",
    ),
)
@_drives_refusals("fold_record_inconsistent")
def test_d3d_stored_statistics_must_be_finite_and_in_domain(mutate) -> None:
    """A stored rho outside [-1, 1] or a non-finite delta is impossible evidence.

    Infinity satisfies its own difference (``inf - finite == inf``), so exact
    equality alone cannot catch it; the domain and finiteness clauses must run
    before the equality reconciliation.
    """
    inference = _inference()
    contrast = _two_fold_signal_contrast()
    mutate(contrast["per_fold"][0])
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.pool_paired_deltas(contrast, registration=_registration())
    assert _failure_reason(exc_info) == "fold_record_inconsistent"

    contrast = _two_fold_signal_contrast()
    mutate(contrast["per_fold"][0])
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.build_cluster_universe(contrast)
    assert _failure_reason(exc_info) == "fold_record_inconsistent"


@pytest.mark.parametrize(
    "impostor",
    [8.0, np.int64(8), True],
    ids=("float", "numpy-int64", "bool"),
)
@_drives_refusals("fold_record_inconsistent")
def test_d3d_folds_present_must_be_an_exact_plain_int(impostor) -> None:
    """Equality coercion must not admit a numeric impostor as the record shape."""
    inference = _inference()
    contrast = _two_fold_signal_contrast()
    contrast["folds_present"] = impostor
    with pytest.raises(_study_module().QBValidationFailure) as exc_info:
        inference.pool_paired_deltas(contrast, registration=_registration())
    assert _failure_reason(exc_info) == "fold_record_inconsistent"
