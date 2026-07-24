"""D3-c — the per-fold comparison-scoring layer: naive lane + F6 + F8.

Contract of record: framing v6 ENUMERATED CLEAR 2026-07-23 (route (b): per-fold
only), the sealed registration (`docs/validation/2026-07-21-qb-1-study-registration.md`,
contrasts c01-c14), and the D3-c behavioral RED. This layer turns per-lane
predictions into per-fold paired evidence across the 14 registered contrasts:

- ``build_naive_lane`` — the fourth prediction lane (most-recent evaluable PPG in
  {t-3..t-1}); no-prior-window rows are excluded and counted, never imputed.
- ``score_comparisons`` — one fold, one contrast: exact-key common-pool
  intersection, per-fold Spearman paired delta (``rho(left) - rho(right)`` from the
  literal registered left/right; ``registered_direction`` is metadata, never a
  second sign-flip), per-side F20 degeneracy, contrast-lane-aware secondaries
  (model: RMSE/MAE on H1-H4 sides + top-k; H5: Kendall + top-k, rank-only,
  higher-is-better ``value_2qb``), and player-keyed ``paired_evidence`` preserved
  for the D3-d inference family.
- ``build_primary_comparisons`` — F7 gate first, the two-level fold topology
  ({2018..2025} global, H5 consumed only on {2021..2024}), the six-lane admission
  rule (out-of-scope H5 is admitted-and-ignored without value access), consumed-only
  H5 provenance, the drivable ``validate_contrast_set`` guard, and the assembled 14
  contrasts.

Everything is per-fold and DESCRIPTIVE: ``decision_supported=False`` on every
emitted record, no ``support_status`` (F30/D5 own that), no pooling/bootstrap/
permutation/BH-FDR (D3-d), no H5 market materialization/join (D4). H2 rushing
production is a hypothesis UNDER TEST — every H2 contrast uses the identical code
path and this layer makes no rushing, incremental, or dynasty-value claim.

Validation follows the published precedence: wrong-call API inputs raise loudly as
``TypeError``; type-correct but corrupt study data raises a named
``QBValidationFailure``; every external field is an exact plain primitive validated
before hash/equality/numeric use, and every refusal detail renders through the
bounded ``_safe_repr`` so no hostile subclass or huge value escapes as a bare
exception or an unbounded message.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from scipy.stats import kendalltau, spearmanr

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure
from src.dynasty_genius.eval.qb_validation.folds import (
    _safe_repr,
    validate_degenerate_inputs,
)
from src.dynasty_genius.eval.qb_validation.registration import (
    require_registration_hash,
)
from src.dynasty_genius.eval.qb_validation.ridge_lane import (
    _exact_number,
    _exact_str,
    _is_sequence,
    _valid_season,
    _validate_fold_rows,
    _validate_label_table,
)

_MODEL_FOLDS = (2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025)
_H5_FOLDS = (2021, 2022, 2023, 2024)
_BASE_LANES = ("naive", "h1", "h2", "h3", "h4")
_KNOWN_LANES = ("naive", "h1", "h2", "h3", "h4", "h5")
_MODEL_LANE_SIDES = ("h1", "h2", "h3", "h4")
_TOP_KS = (6, 12, 24)
_CONTRAST_FIELDS = ("id", "lane", "left", "right", "direction")
_DP_PROVENANCE = "dynastyprocess_ecr_2qb"
_NAIVE_WINDOW = 3
_STARVED_N = 20

# The pinned registered contrast set (registration §8, ids c01-c14). A passed
# contrast must equal its registered literal by id — structural validity alone
# permits wrong-secondary routing / mislabeled evidence.
_REGISTERED_CONTRASTS = (
    {"id": "c01", "lane": "model", "left": "h1", "right": "naive", "direction": "h1_gt_naive"},
    {"id": "c02", "lane": "model", "left": "h2", "right": "naive", "direction": "h2_gt_naive"},
    {"id": "c03", "lane": "model", "left": "h3", "right": "naive", "direction": "h3_gt_naive"},
    {"id": "c04", "lane": "model", "left": "h4", "right": "naive", "direction": "h4_gt_naive"},
    {"id": "c05", "lane": "model", "left": "h2", "right": "h1", "direction": "h2_gt_h1"},
    {"id": "c06", "lane": "model", "left": "h2", "right": "h3", "direction": "h2_gt_h3"},
    {"id": "c07", "lane": "model", "left": "h3", "right": "h1", "direction": "h3_gt_h1"},
    {"id": "c08", "lane": "model", "left": "h4", "right": "h1", "direction": "h4_gt_h1"},
    {"id": "c09", "lane": "model", "left": "h4", "right": "h2", "direction": "h4_gt_h2"},
    {"id": "c10", "lane": "model", "left": "h4", "right": "h3", "direction": "h4_gt_h3"},
    {"id": "c11", "lane": "h5", "left": "h5", "right": "h1", "direction": "market_noninferior_delta_gt_delta0"},
    {"id": "c12", "lane": "h5", "left": "h5", "right": "h2", "direction": "market_noninferior_delta_gt_delta0"},
    {"id": "c13", "lane": "h5", "left": "h5", "right": "h3", "direction": "market_noninferior_delta_gt_delta0"},
    {"id": "c14", "lane": "h5", "left": "h5", "right": "h4", "direction": "market_noninferior_delta_gt_delta0"},
)
_REGISTERED_BY_ID = {row["id"]: row for row in _REGISTERED_CONTRASTS}


def _refuse(reason: str, detail: str) -> None:
    raise QBValidationFailure(reason, detail)


# --------------------------------------------------------------------------- #
# A — naive carryforward lane
# --------------------------------------------------------------------------- #
def _reconcile_label_presence(
    validated: list[tuple[Any, str, int, str]], lookup: dict[tuple[str, int], float]
) -> None:
    """F5's label-presence reconciliation (both directions), by (player_id, target_season).

    An ``target_evaluable`` row must have a label; a ``no_target_season`` row must
    not — applied to BOTH the train and test partitions, exactly as F5 does.
    """
    for _row, player_id, season, target in validated:
        present = (player_id, season) in lookup
        if target == "target_evaluable" and not present:
            _refuse("classification_label_mismatch", f"{_safe_repr((player_id, season))} evaluable but has no label")
        if target == "no_target_season" and present:
            _refuse("classification_label_mismatch", f"{_safe_repr((player_id, season))} no_target_season but a label exists")


def build_naive_lane(
    fold: Mapping[str, Any],
    label_table: Any,
) -> dict[str, Any]:
    """Build the per-fold naive-carryforward prediction lane.

    Prediction = the player's MOST RECENT evaluable PPG within target seasons
    ``{t-3..t-1}``; a test row with no prior evaluable PPG in that window is
    EXCLUDED and counted, never imputed. Season ``t`` supplies only ``y_true``;
    future/other-season rows in the one validated label table are validated but
    never used as carryforward candidates. Fold-row eligibility/target axes are
    consumed verbatim (D2a-owned) — D3 never re-derives classification.
    """
    if not isinstance(fold, Mapping):
        raise TypeError(f"fold must be a mapping, got {type(fold).__name__}")
    if not _is_sequence(label_table):
        raise TypeError(f"label_table must be a non-string sequence, got {type(label_table).__name__}")

    # F5 parity (ridge_lane.py:230-257) — same order and gates: fold root (incl.
    # non-empty train AND test) → train+test row classification → label-table
    # integrity → label-presence reconciliation for BOTH partitions. Reuses the F5
    # helpers, not a second authority; label content is validated AFTER the fold
    # root, so a corrupt schedule refuses before a corrupt label value.
    test_season = fold.get("test_season")
    train_rows = fold.get("train_rows")
    test_rows = fold.get("test_rows")
    train_seasons = fold.get("train_seasons")
    if (
        not _valid_season(test_season)
        or not isinstance(train_rows, list)
        or not isinstance(test_rows, list)
    ):
        _refuse("fold_root_invalid", "fold needs a plausible int test_season and train/test row lists")
    if not train_rows or not test_rows:
        _refuse("fold_root_invalid", "fold has an empty train or test partition")
    if (
        not isinstance(train_seasons, list)
        or not train_seasons
        or any(not _valid_season(s) for s in train_seasons)
        or train_seasons[-1] != test_season - 1
        or any(train_seasons[i] != train_seasons[i - 1] + 1 for i in range(1, len(train_seasons)))
    ):
        _refuse("fold_root_invalid", f"train_seasons={_safe_repr(train_seasons)} is not a valid pre-test schedule")
    season_set = set(train_seasons)

    v_train = _validate_fold_rows(train_rows, where="train", test_season=test_season, train_seasons=season_set)
    v_test = _validate_fold_rows(test_rows, where="test", test_season=test_season, train_seasons=season_set)
    lookup = _validate_label_table(label_table)  # integrity AFTER fold root/rows
    _reconcile_label_presence(v_train, lookup)  # train partition — both directions, no prediction
    window = {test_season - k for k in range(1, _NAIVE_WINDOW + 1)}

    predictions: list[dict[str, Any]] = []
    excluded_keys: list[list[Any]] = []
    for _row, player_id, season, target in v_test:
        true_key = (player_id, test_season)
        present = true_key in lookup
        if target == "no_target_season":
            # Both sides of classification-label presence, mirroring F5.
            if present:
                _refuse(
                    "classification_label_mismatch",
                    f"{_safe_repr(true_key)} no_target_season but a target-season label exists",
                )
            continue  # not an evaluable prediction subject; not counted
        if not present:
            _refuse(
                "classification_label_mismatch",
                f"{_safe_repr(true_key)} evaluable but has no target-season label",
            )
        candidates = [
            (s, ppg)
            for (pid, s), ppg in lookup.items()
            if pid == player_id and s in window
        ]
        if not candidates:
            excluded_keys.append([player_id, test_season])
            continue
        y_pred = max(candidates, key=lambda item: item[0])[1]
        predictions.append(
            {
                "player_id": player_id,
                "target_season": test_season,
                "y_pred": float(y_pred),
                "y_true": lookup[true_key],
                "decision_supported": False,
            }
        )

    predictions.sort(key=lambda row: (row["target_season"], row["player_id"]))
    excluded_keys.sort()
    return {
        "test_season": test_season,
        "lane": "naive",
        "n_predicted": len(predictions),
        "predictions": predictions,
        "excluded": {
            "count": len(excluded_keys),
            "keys": excluded_keys,
            "decision_supported": False,
        },
        "decision_supported": False,
    }


# --------------------------------------------------------------------------- #
# B — F6 score_comparisons
# --------------------------------------------------------------------------- #
def _validate_contrast(contrast: Any) -> None:
    """Closed contrast validation — runs BEFORE any lane access (F6's first gate).

    Beyond the closed shape, the contrast must equal its registered c01-c14
    literal by id: structural validity alone would permit a drifted direction/
    side to route to the wrong secondary family or mislabel the emitted evidence.
    Every field is an exact plain string BEFORE the registry hash/equality use, so
    a hostile subclass cannot reach the lookup.
    """
    if not isinstance(contrast, Mapping):
        raise TypeError(f"contrast must be a mapping, got {type(contrast).__name__}")
    # Every KEY must be an exact plain string BEFORE any set/hash/equality or
    # rendering — a str subclass key can equality-shadow a required field, and a
    # hostile ``__str__``/``__repr__`` key must render through the bounded safe repr.
    for key in list(contrast):
        if type(key) is not str:
            _refuse("contrast_malformed", f"contrast has a non-plain key {_safe_repr(key)}")
    if set(contrast) != set(_CONTRAST_FIELDS):
        _refuse("contrast_malformed", f"contrast keys={_safe_repr(sorted(contrast))}")
    for field in _CONTRAST_FIELDS:
        if not _exact_str(contrast.get(field)):
            _refuse("contrast_malformed", f"contrast {field}={_safe_repr(contrast.get(field))}")
    registered = _REGISTERED_BY_ID.get(contrast["id"])
    if registered is None or any(contrast[field] != registered[field] for field in _CONTRAST_FIELDS):
        _refuse(
            "contrast_malformed",
            f"contrast {_safe_repr(contrast['id'])} drifts from its registered literal",
        )


def _lane_test_season(lane: Mapping[str, Any]) -> int:
    season = lane.get("test_season")
    if not _valid_season(season):
        _refuse("lane_result_malformed", f"lane test_season={_safe_repr(season)}")
    return season


def _validate_lane(
    lane: Any, *, expected_lane: str, expected_season: int
) -> dict[tuple[str, int], tuple[float, float]]:
    """Full closed-LaneResultCore validation → {(player_id, target_season): (y_pred, y_true)}.

    Reused by F6 (``expected_season`` = the lane's own fold, after the cross-lane
    fold-match) and by F8's consumed-lane reconciliation (``expected_season`` = the
    outer ``lanes_by_fold`` key, so coherent-but-outer-wrong nested lanes are
    caught). Validates: mapping shape; recursive No-Verdict flag on root AND every
    consumed row; declared lane vs the contrast/map side; root and every row season
    reconciled to ``expected_season``; exact-plain key primitives; finite values;
    and unique keys — every external field before any hash/equality/numeric use.
    """
    if not isinstance(lane, Mapping):
        _refuse("lane_result_malformed", f"lane is not a mapping: {_safe_repr(lane)}")
    if lane.get("decision_supported") is not False:
        _refuse("lane_result_malformed", "lane root decision_supported must be False")
    if not _exact_str(lane.get("lane")) or lane.get("lane") != expected_lane:
        _refuse(
            "lane_identity_mismatch",
            f"declared lane={_safe_repr(lane.get('lane'))} != {expected_lane!r}",
        )
    root_season = lane.get("test_season")
    if not _valid_season(root_season):
        _refuse("lane_result_malformed", f"lane test_season={_safe_repr(root_season)}")
    if root_season != expected_season:
        _refuse("lane_fold_mismatch", f"lane test_season {root_season} != expected {expected_season}")
    predictions = lane.get("predictions")
    n_predicted = lane.get("n_predicted")
    if not isinstance(predictions, list):
        _refuse("lane_result_malformed", "predictions must be a list")
    if type(n_predicted) is not int or n_predicted != len(predictions):
        _refuse(
            "lane_result_malformed",
            f"n_predicted={_safe_repr(n_predicted)} != {len(predictions)} rows",
        )
    by_key: dict[tuple[str, int], tuple[float, float]] = {}
    for index, row in enumerate(predictions):
        if not isinstance(row, Mapping):
            _refuse("lane_result_malformed", f"prediction [{index}] is not a mapping")
        if row.get("decision_supported") is not False:
            _refuse("lane_result_malformed", f"prediction [{index}] decision_supported must be False")
        player_id = row.get("player_id")
        season = row.get("target_season")
        if not _exact_str(player_id) or not _valid_season(season):
            _refuse(
                "lane_result_malformed",
                f"prediction [{index}] key player_id={_safe_repr(player_id)} "
                f"target_season={_safe_repr(season)}",
            )
        if season != expected_season:
            _refuse(
                "lane_result_malformed",
                f"prediction [{index}] target_season {season} != lane fold {expected_season}",
            )
        y_pred = row.get("y_pred")
        y_true = row.get("y_true")
        if not _exact_number(y_pred) or not _exact_number(y_true):
            _refuse(
                "lane_result_malformed",
                f"prediction {_safe_repr((player_id, season))} "
                f"y_pred={_safe_repr(y_pred)} y_true={_safe_repr(y_true)}",
            )
        key = (player_id, season)
        if key in by_key:
            _refuse("lane_key_duplicate", f"lane duplicates {_safe_repr(key)}")
        by_key[key] = (float(y_pred), float(y_true))
    return by_key


def _topk_hit(
    common: list[tuple[str, int]], values: list[float], truths: list[float], k: int
) -> float:
    def topk(scores: list[float]) -> set[tuple[str, int]]:
        # Descending (higher-is-better), deterministic tie-break by player_id.
        order = sorted(
            range(len(common)), key=lambda i: (-scores[i], common[i][0])
        )
        return {common[i] for i in order[:k]}

    return len(topk(values) & topk(truths)) / k


def _rank_metric(
    func: Any, values: list[float], truths: list[float], *, allowed: bool
) -> float | None:
    if not allowed or len(values) < 2:
        return None
    return float(func(values, truths)[0])


def _hit_rate(
    common: list[tuple[str, int]],
    values: list[float],
    truths: list[float],
    *,
    fold_starved: bool,
    common_pool_n: int,
) -> dict[str, dict[str, Any]]:
    leaves: dict[str, dict[str, Any]] = {}
    for k in _TOP_KS:
        if fold_starved:
            leaves[f"k{k}"] = {"value": None, "state": "fold_starved"}
        elif common_pool_n < k:
            leaves[f"k{k}"] = {"value": None, "state": "undersized"}
        else:
            leaves[f"k{k}"] = {"value": _topk_hit(common, values, truths, k), "state": "ok"}
    return leaves


def _error_leaf(
    func: Any, values: list[float], truths: list[float], *, fold_starved: bool
) -> dict[str, Any]:
    if fold_starved:
        return {"value": None, "state": "fold_starved"}
    value = func(values, truths)
    # A final finiteness gate: contract-admitted finite extremes may still yield a
    # non-representable aggregate — named, never a silent inf or a clamp.
    if not math.isfinite(value):
        return {"value": None, "state": "non_finite"}
    return {"value": value, "state": "ok"}


def _rmse(values: list[float], truths: list[float]) -> float:
    # Max-scaled so contract-admitted finite extremes (e.g. ±1e308) do not overflow
    # the intermediate square/sum before the representable result is formed.
    diffs = [v - t for v, t in zip(values, truths)]
    scale = max((abs(d) for d in diffs), default=0.0)
    if scale == 0.0:
        return 0.0
    mean_scaled_sq = sum((d / scale) ** 2 for d in diffs) / len(diffs)
    return scale * math.sqrt(mean_scaled_sq)


def _mae(values: list[float], truths: list[float]) -> float:
    diffs = [abs(v - t) for v, t in zip(values, truths)]
    scale = max(diffs, default=0.0)
    if scale == 0.0:
        return 0.0
    return scale * (sum(d / scale for d in diffs) / len(diffs))


def score_comparisons(
    left_lane: Any,
    right_lane: Any,
    *,
    contrast: Any,
) -> dict[str, Any]:
    """Score ONE registered contrast on ONE fold — per-fold paired evidence only."""
    _validate_contrast(contrast)  # FIRST, before any lane value access
    if not isinstance(left_lane, Mapping):
        raise TypeError(f"left_lane must be a mapping, got {type(left_lane).__name__}")
    if not isinstance(right_lane, Mapping):
        raise TypeError(f"right_lane must be a mapping, got {type(right_lane).__name__}")

    left_ts = _lane_test_season(left_lane)
    right_ts = _lane_test_season(right_lane)
    if left_ts != right_ts:
        _refuse("lane_fold_mismatch", f"left test_season {left_ts} != right {right_ts}")

    left_by_key = _validate_lane(left_lane, expected_lane=contrast["left"], expected_season=left_ts)
    right_by_key = _validate_lane(right_lane, expected_lane=contrast["right"], expected_season=right_ts)

    common = sorted(
        set(left_by_key) & set(right_by_key), key=lambda key: (key[1], key[0])
    )
    for key in common:
        if left_by_key[key][1] != right_by_key[key][1]:
            _refuse("paired_label_mismatch", f"{_safe_repr(key)} y_true disagrees across lanes")

    common_pool_n = len(common)
    left_preds = [left_by_key[key][0] for key in common]
    right_preds = [right_by_key[key][0] for key in common]
    truths = [left_by_key[key][1] for key in common]
    fold_starved = common_pool_n < _STARVED_N

    degeneracy = {
        "left": validate_degenerate_inputs(left_preds, truths),
        "right": validate_degenerate_inputs(right_preds, truths),
        "decision_supported": False,
    }
    left_allowed = degeneracy["left"]["metrics_allowed"]
    right_allowed = degeneracy["right"]["metrics_allowed"]

    reasons: list[str] = []
    if common_pool_n == 0:
        reasons.append("empty_common_pool")
    if fold_starved:
        reasons.append("fold_starved")
    if not left_allowed or not right_allowed:
        reasons.append("degenerate_input")

    if fold_starved:
        spearman_left = spearman_right = paired_delta = None
    else:
        spearman_left = _rank_metric(spearmanr, left_preds, truths, allowed=left_allowed)
        spearman_right = _rank_metric(spearmanr, right_preds, truths, allowed=right_allowed)
        paired_delta = (
            spearman_left - spearman_right
            if spearman_left is not None and spearman_right is not None
            else None
        )

    per_lane_coverage = {
        "left": {
            "n_predicted": len(left_by_key),
            "n_in_common": common_pool_n,
            "n_left_only": len(left_by_key) - common_pool_n,
        },
        "right": {
            "n_predicted": len(right_by_key),
            "n_in_common": common_pool_n,
            "n_right_only": len(right_by_key) - common_pool_n,
        },
        "decision_supported": False,
    }

    hit_rate = {
        "left": _hit_rate(common, left_preds, truths, fold_starved=fold_starved, common_pool_n=common_pool_n),
        "right": _hit_rate(common, right_preds, truths, fold_starved=fold_starved, common_pool_n=common_pool_n),
    }
    secondaries: dict[str, Any] = {"hit_rate": hit_rate, "decision_supported": False}
    if contrast["lane"] == "model":
        rmse: dict[str, Any] = {}
        mae: dict[str, Any] = {}
        for side, side_lane, side_preds in (
            ("left", contrast["left"], left_preds),
            ("right", contrast["right"], right_preds),
        ):
            if side_lane in _MODEL_LANE_SIDES:
                rmse[side] = _error_leaf(_rmse, side_preds, truths, fold_starved=fold_starved)
                mae[side] = _error_leaf(_mae, side_preds, truths, fold_starved=fold_starved)
        secondaries["rmse"] = rmse
        secondaries["mae"] = mae
    else:  # h5 — rank-only, never RMSE/MAE on market values
        kendall: dict[str, Any] = {}
        for side, side_preds, allowed in (
            ("left", left_preds, left_allowed),
            ("right", right_preds, right_allowed),
        ):
            if fold_starved:
                kendall[side] = {"value": None, "state": "fold_starved"}
            else:
                value = _rank_metric(kendalltau, side_preds, truths, allowed=allowed)
                kendall[side] = {
                    "value": value,
                    "state": "ok" if value is not None else "degenerate_input",
                }
        secondaries["kendall"] = kendall

    paired_evidence = [
        {
            "player_id": key[0],
            "target_season": key[1],
            "left_pred": left_by_key[key][0],
            "right_pred": right_by_key[key][0],
            "y_true": left_by_key[key][1],
            "decision_supported": False,
        }
        for key in common
    ]

    return {
        "contrast_id": contrast["id"],
        "test_season": left_ts,
        "left_lane": contrast["left"],
        "right_lane": contrast["right"],
        "registered_direction": contrast["direction"],
        "common_pool_n": common_pool_n,
        "per_lane_coverage": per_lane_coverage,
        "spearman_left": spearman_left,
        "spearman_right": spearman_right,
        "paired_delta": paired_delta,
        "paired_evidence": paired_evidence,
        "secondaries": secondaries,
        "degeneracy": degeneracy,
        "fold_starved": fold_starved,
        "reasons": reasons,
        "decision_supported": False,
    }


# --------------------------------------------------------------------------- #
# C — F8 build_primary_comparisons
# --------------------------------------------------------------------------- #
def validate_contrast_set(assembled: Any, expected: Any) -> None:
    """Drivable defense-in-depth: the assembled contrast set must equal the pinned.

    A builder bug that drops/reorders/mutates a contrast during assembly is caught
    here; the RED drives it directly with a mismatched ``(assembled, expected)``
    pair. This is NOT a registration-tamper detector — that is F7's job.
    """
    if len(assembled) != len(expected):
        _refuse("assembled_contrasts_inconsistent", f"len {len(assembled)} != {len(expected)}")
    for got, want in zip(assembled, expected):
        for field in _CONTRAST_FIELDS:
            if got.get(field) != want.get(field):
                _refuse(
                    "assembled_contrasts_inconsistent",
                    f"contrast {_safe_repr(want.get('id'))} field {field} drifted",
                )


def _check_h5_provenance(h5_lane: Mapping[str, Any], fold: int) -> None:
    """Consumed in-scope H5 provenance — exact-plain BEFORE any equality, so a
    hostile ``__eq__`` cannot be invoked (runs AFTER core LaneResultCore validation)."""
    source = h5_lane.get("lane_source")
    if type(source) is not str or source != _DP_PROVENANCE:
        _refuse("market_provenance_missing", f"h5@{fold} lane_source={_safe_repr(source)}")
    for index, row in enumerate(h5_lane.get("predictions", [])):
        provenance = row.get("source_provenance") if isinstance(row, Mapping) else None
        if type(provenance) is not str or provenance != _DP_PROVENANCE:
            _refuse("market_provenance_missing", f"h5@{fold} row [{index}] provenance={_safe_repr(provenance)}")


def build_primary_comparisons(
    lanes_by_fold: Any,
    *,
    registration: Any,
    expected_registration_hash: Any,
) -> dict[str, Any]:
    """Assemble the 14 registered contrasts over the fold topology, per-fold only."""
    # 1. F7 gate FIRST — before ANY fold/lane access.
    verified_hash = require_registration_hash(registration, expected_registration_hash)
    if not isinstance(lanes_by_fold, Mapping):
        raise TypeError(f"lanes_by_fold must be a mapping, got {type(lanes_by_fold).__name__}")

    contrasts_spec = registration["contrasts"]
    assembled = [
        {field: spec[field] for field in _CONTRAST_FIELDS} for spec in contrasts_spec
    ]
    validate_contrast_set(assembled, contrasts_spec)

    # 2. Top-level fold-key admission: exactly {2018..2025}.
    for key in list(lanes_by_fold):
        if type(key) is not int or key not in _MODEL_FOLDS:
            _refuse("unexpected_fold", f"fold key {_safe_repr(key)} outside {_MODEL_FOLDS}")
    for fold in _MODEL_FOLDS:
        if fold not in lanes_by_fold:
            _refuse("fold_missing", f"required model fold {fold} absent")

    # 3. Per-fold lane admission + consumed-only H5 provenance (out-of-scope H5 is
    #    admitted by key but its value is NEVER accessed).
    for fold in _MODEL_FOLDS:
        fold_map = lanes_by_fold[fold]
        if not isinstance(fold_map, Mapping):
            _refuse("lane_result_malformed", f"fold {fold} is not a mapping of lanes")
        for lane_key in list(fold_map):
            if type(lane_key) is not str or lane_key not in _KNOWN_LANES:
                _refuse("unexpected_lane", f"lane key {_safe_repr(lane_key)}@{fold} outside {_KNOWN_LANES}")
        for base in _BASE_LANES:
            if base not in fold_map:
                _refuse("lane_missing", f"base lane {base!r}@{fold} absent")
        # Consumed-lane reconciliation to the OUTER key: a set of nested lanes that
        # are coherent with each other but wrong vs the map key passes F6's
        # lane-to-lane check, so F8 must reconcile each consumed lane to `fold`
        # here (this also core-validates, catching a None/malformed H5) — the
        # out-of-scope H5 value is never touched.
        for base in _BASE_LANES:
            _validate_lane(fold_map[base], expected_lane=base, expected_season=fold)
        if fold in _H5_FOLDS:
            if "h5" not in fold_map:
                _refuse("lane_missing", f"consumed h5 lane@{fold} absent")
            _validate_lane(fold_map["h5"], expected_lane="h5", expected_season=fold)
            _check_h5_provenance(fold_map["h5"], fold)

    # 4. Score — nested lane/fold reconciliation surfaces through score_comparisons.
    contrasts: list[dict[str, Any]] = []
    for spec in contrasts_spec:
        folds = _MODEL_FOLDS if spec["lane"] == "model" else _H5_FOLDS
        per_fold = [
            score_comparisons(
                lanes_by_fold[fold][spec["left"]],
                lanes_by_fold[fold][spec["right"]],
                contrast=spec,
            )
            for fold in folds
        ]
        contrasts.append(
            {
                "id": spec["id"],
                "lane": spec["lane"],
                "left": spec["left"],
                "right": spec["right"],
                "registered_direction": spec["direction"],
                "per_fold": per_fold,
                "folds_present": len(per_fold),
                "decision_supported": False,
            }
        )

    return {
        "registration_hash": verified_hash,
        "contrasts": contrasts,
        "decision_supported": False,
    }
