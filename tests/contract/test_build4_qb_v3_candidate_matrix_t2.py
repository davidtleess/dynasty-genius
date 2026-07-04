from __future__ import annotations

import importlib
from typing import Any

import pandas as pd
import pytest

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_B_FEATURES_QB,
    validate_position_feature_contract,
)


def _matrix_module() -> Any:
    return importlib.import_module("src.dynasty_genius.features.qb_v3_candidate_matrix")


def _value(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def _candidate_matrix(result: Any) -> pd.DataFrame:
    matrix = _value(result, "candidate_matrix")
    assert isinstance(matrix, pd.DataFrame)
    return matrix


def _eligibility_mask(result: Any) -> pd.DataFrame:
    mask = _value(result, "eligibility_mask")
    assert isinstance(mask, pd.DataFrame)
    return mask


def _feature_cols(result: Any) -> list[str]:
    feature_cols = _value(result, "feature_cols")
    assert isinstance(feature_cols, list)
    return feature_cols


def _diagnostics(result: Any) -> dict[str, Any]:
    diagnostics = _value(result, "diagnostics")
    assert isinstance(diagnostics, dict)
    return diagnostics


def _qb_feature_row(
    player_id: str,
    season: int,
    *,
    games_t: int = 8,
    age: float = 24.0,
    is_dual_threat: bool = False,
    position: str = "QB",
) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "position": position,
        "feature_season": season,
        "team": "MIN",
        "age": age,
        "ppg_t": 12.0,
        "games_t": games_t,
        "snap_share": 0.75,
        "aging_curve_value": 0.98,
        "ppg_t_minus_1": 11.0,
        "ppg_t_minus_2": 10.0,
        "snap_share_t_minus_1": 0.70,
        "ppg_t_minus_1_available": True,
        "ppg_t_minus_2_available": True,
        "snap_share_t_minus_1_available": True,
        "epa_per_dropback": 0.12,
        "cpoe": 2.4,
        "dakota": 0.08,
        "is_dual_threat": is_dual_threat,
        "training_eligible": season <= 2023,
    }


def _feature_rows(*rows: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _draft_rows(*rows: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=[
            "player_id",
            "draft_number",
            "entry_year",
            "round",
            "pick",
            "draft_year",
            "college",
        ],
    )


def _label_rows(*rows: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=[
            "player_id",
            "feature_season",
            "target_season",
            "horizon",
            "startable_role_occupancy",
            "label_basis",
        ],
    )


def _build_candidate(
    feature_rows: pd.DataFrame,
    draft_rows: pd.DataFrame,
    *,
    labels: pd.DataFrame | None = None,
) -> Any:
    module = _matrix_module()
    if labels is None:
        default_label_rows = [
            {
                "player_id": row.player_id,
                "feature_season": int(row.feature_season),
                "target_season": int(row.feature_season) + 1,
                "horizon": 1,
                "startable_role_occupancy": True,
                "label_basis": "games_and_snap",
            }
            for row in feature_rows.itertuples(index=False)
            if row.position == "QB"
        ]
        labels = _label_rows(*default_label_rows)
    return module.build_qb_v3_candidate_matrix(
        feature_rows=feature_rows,
        draft_prior_rows=draft_rows,
        labels=labels,
        candidate_head="qb_v3_candidate",
    )


def test_existing_qb_v2_contract_is_untouched_and_rejects_candidate_columns() -> None:
    module = _matrix_module()
    candidate_cols = sorted(module.ENGINE_B_FEATURES_QB_V3_CANDIDATE)

    assert "draft_capital_prior" not in ENGINE_B_FEATURES_QB
    assert "dual_threat_x_age" not in ENGINE_B_FEATURES_QB
    with pytest.raises(ValueError, match="not in allowed"):
        validate_position_feature_contract("QB", candidate_cols)

    module.validate_qb_v3_candidate_feature_contract(candidate_cols)


def test_candidate_validator_rejects_market_and_raw_draft_columns() -> None:
    module = _matrix_module()
    clean = sorted(module.ENGINE_B_FEATURES_QB_V3_CANDIDATE)

    for bad_col in ("ktc_value", "adp", "pick", "round", "draft_year", "college"):
        with pytest.raises(ValueError, match="[Pp]rohibited|raw draft"):
            module.validate_qb_v3_candidate_feature_contract([*clean, bad_col])


def test_builder_derives_fork_a_prior_without_raw_draft_columns_or_metadata() -> None:
    result = _build_candidate(
        _feature_rows(
            _qb_feature_row("rookie_round1", 2025, age=23.0),
            _qb_feature_row("year3_day2", 2027, age=25.0),
            _qb_feature_row("year4_round1", 2028, age=26.0),
        ),
        _draft_rows(
            {
                "player_id": "rookie_round1",
                "draft_number": 10,
                "entry_year": 2025,
                "round": 1,
                "pick": 10,
                "draft_year": 2025,
                "college": "Example State",
            },
            {
                "player_id": "year3_day2",
                "draft_number": 55,
                "entry_year": 2025,
                "round": 2,
                "pick": 55,
                "draft_year": 2025,
                "college": "Example Tech",
            },
            {
                "player_id": "year4_round1",
                "draft_number": 12,
                "entry_year": 2025,
                "round": 1,
                "pick": 12,
                "draft_year": 2025,
                "college": "Example A&M",
            },
        ),
    )

    matrix = _candidate_matrix(result).set_index("player_id")
    feature_cols = set(_feature_cols(result))
    raw_draft_cols = {"pick", "round", "draft_year", "college", "draft_number"}

    assert "draft_capital_prior" in feature_cols
    assert "nfl_year_at_feature" not in feature_cols
    assert not (raw_draft_cols & feature_cols)
    assert not (raw_draft_cols & set(matrix.columns))
    assert matrix.loc["rookie_round1", "draft_capital_prior"] > 0
    assert matrix.loc["year3_day2", "draft_capital_prior"] > 0
    assert matrix.loc["year4_round1", "draft_capital_prior"] == 0
    assert _diagnostics(result)["draft_capital_prior_basis"] in {
        "fixed_pre_registered_rule",
        "train_fold_only",
    }


def test_prior_is_qb_candidate_only_and_other_positions_are_excluded() -> None:
    result = _build_candidate(
        _feature_rows(
            _qb_feature_row("qb_ok", 2025),
            _qb_feature_row("rb_with_capital", 2025, position="RB"),
        ),
        _draft_rows(
            {
                "player_id": "qb_ok",
                "draft_number": 30,
                "entry_year": 2025,
                "round": 1,
                "pick": 30,
                "draft_year": 2025,
                "college": "QB U",
            },
            {
                "player_id": "rb_with_capital",
                "draft_number": 10,
                "entry_year": 2025,
                "round": 1,
                "pick": 10,
                "draft_year": 2025,
                "college": "RB U",
            },
        ),
    )

    assert set(_candidate_matrix(result)["player_id"]) == {"qb_ok"}
    assert _diagnostics(result)["excluded_non_qb_count"] == 1


def test_abstention_mask_precedes_scoring_and_discloses_day3_and_small_sample() -> None:
    result = _build_candidate(
        _feature_rows(
            _qb_feature_row("round4_rookie", 2025, games_t=8),
            _qb_feature_row("small_no_prior", 2025, games_t=7),
            _qb_feature_row("small_with_prior", 2024, games_t=8),
            _qb_feature_row("small_with_prior", 2025, games_t=7),
            _qb_feature_row("eligible_qb", 2025, games_t=8),
        ),
        _draft_rows(
            {
                "player_id": "round4_rookie",
                "draft_number": 100,
                "entry_year": 2025,
                "round": 4,
                "pick": 100,
                "draft_year": 2025,
                "college": "Day Three",
            },
            {
                "player_id": "small_no_prior",
                "draft_number": 20,
                "entry_year": 2025,
                "round": 1,
                "pick": 20,
                "draft_year": 2025,
                "college": "Small Sample",
            },
            {
                "player_id": "small_with_prior",
                "draft_number": 20,
                "entry_year": 2024,
                "round": 1,
                "pick": 20,
                "draft_year": 2024,
                "college": "Prior State",
            },
            {
                "player_id": "eligible_qb",
                "draft_number": 30,
                "entry_year": 2025,
                "round": 1,
                "pick": 30,
                "draft_year": 2025,
                "college": "Eligible U",
            },
        ),
    )

    mask = _eligibility_mask(result).set_index(["player_id", "feature_season"])
    diagnostics = _diagnostics(result)

    assert bool(mask.loc[("round4_rookie", 2025), "eligible_for_qb_v3_candidate"]) is False
    assert mask.loc[("round4_rookie", 2025), "abstention_reason"] == "day3_rookie"
    assert bool(mask.loc[("small_no_prior", 2025), "eligible_for_qb_v3_candidate"]) is False
    assert mask.loc[("small_no_prior", 2025), "abstention_reason"] == "small_sample_qb"
    assert bool(mask.loc[("small_with_prior", 2025), "eligible_for_qb_v3_candidate"]) is True
    assert bool(mask.loc[("eligible_qb", 2025), "eligible_for_qb_v3_candidate"]) is True
    assert diagnostics["abstention_counts"] == {
        "day3_rookie": 1,
        "small_sample_qb": 1,
    }
    assert "candidate_probability" not in set(_candidate_matrix(result).columns)


def test_dual_threat_age_interaction_exists_without_hardcoded_age_cliff() -> None:
    result = _build_candidate(
        _feature_rows(
            _qb_feature_row("dual_28", 2025, age=28.0, is_dual_threat=True),
            _qb_feature_row("pocket_28", 2025, age=28.0, is_dual_threat=False),
        ),
        _draft_rows(
            {
                "player_id": "dual_28",
                "draft_number": 20,
                "entry_year": 2025,
                "round": 1,
                "pick": 20,
                "draft_year": 2025,
                "college": "Run U",
            },
            {
                "player_id": "pocket_28",
                "draft_number": 20,
                "entry_year": 2025,
                "round": 1,
                "pick": 20,
                "draft_year": 2025,
                "college": "Pocket U",
            },
        ),
    )

    matrix = _candidate_matrix(result).set_index("player_id")
    feature_cols = set(_feature_cols(result))

    assert "dual_threat_x_age" in feature_cols
    assert matrix.loc["dual_28", "dual_threat_x_age"] == pytest.approx(28.0)
    assert matrix.loc["pocket_28", "dual_threat_x_age"] == pytest.approx(0.0)
    assert not any("cliff" in col.lower() for col in feature_cols)


def test_offseason_transfer_and_event_features_are_not_introduced() -> None:
    result = _build_candidate(
        _feature_rows(
            {
                **_qb_feature_row("stable_qb", 2025),
                "offseason_transfer": True,
                "coach_fired": True,
                "regime_change": True,
            }
        ),
        _draft_rows(
            {
                "player_id": "stable_qb",
                "draft_number": 20,
                "entry_year": 2025,
                "round": 1,
                "pick": 20,
                "draft_year": 2025,
                "college": "Stable U",
            }
        ),
    )

    feature_cols = set(_feature_cols(result))
    assert not {"offseason_transfer", "coach_fired", "regime_change"} & feature_cols


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda df: df.drop(columns=["games_t"]), "games_t"),
        (
            lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True),
            "duplicate",
        ),
        (lambda df: df.assign(feature_season="2025"), "feature_season"),
    ],
)
def test_matrix_builder_fails_closed_on_bad_feature_rows(
    mutate: Any,
    expected: str,
) -> None:
    features = _feature_rows(_qb_feature_row("bad_qb", 2025))
    draft = _draft_rows(
        {
            "player_id": "bad_qb",
            "draft_number": 20,
            "entry_year": 2025,
            "round": 1,
            "pick": 20,
            "draft_year": 2025,
            "college": "Bad U",
        }
    )

    with pytest.raises(ValueError, match=expected):
        _build_candidate(mutate(features), draft)


def test_matrix_builder_fails_when_draft_prior_source_has_duplicate_player() -> None:
    features = _feature_rows(_qb_feature_row("dup_prior_qb", 2025))
    draft = _draft_rows(
        {
            "player_id": "dup_prior_qb",
            "draft_number": 20,
            "entry_year": 2025,
            "round": 1,
            "pick": 20,
            "draft_year": 2025,
            "college": "One U",
        },
        {
            "player_id": "dup_prior_qb",
            "draft_number": 21,
            "entry_year": 2025,
            "round": 1,
            "pick": 21,
            "draft_year": 2025,
            "college": "Two U",
        },
    )

    with pytest.raises(ValueError, match="duplicate"):
        _build_candidate(features, draft)
