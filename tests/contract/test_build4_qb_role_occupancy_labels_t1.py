from __future__ import annotations

import importlib
from typing import Any

import pandas as pd
import pytest


def _labels_module() -> Any:
    return importlib.import_module("src.dynasty_genius.features.qb_role_occupancy_labels")


def _script_module() -> Any:
    return importlib.import_module("scripts.generate_qb_role_occupancy_labels")


def _value(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def _labels(result: Any) -> pd.DataFrame:
    labels = _value(result, "labels")
    assert isinstance(labels, pd.DataFrame)
    return labels


def _diagnostics(result: Any) -> dict[str, Any]:
    diagnostics = _value(result, "diagnostics")
    assert isinstance(diagnostics, dict)
    return diagnostics


def _feature_rows(*, seasons: tuple[int, ...] = (2020,)) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    players = (
        ("snap_050", 8),
        ("snap_0499", 8),
        ("games_8", 8),
        ("games_7", 8),
        ("missing_snap", 8),
        ("absent_target", 8),
    )
    for season in seasons:
        for player_id, games_t in players:
            rows.append(
                {
                    "player_id": player_id,
                    "position": "QB",
                    "feature_season": season,
                    "games_t": games_t,
                    "training_eligible": season <= 2023,
                }
            )
    return pd.DataFrame(rows)


def _role_rows(*rows: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["player_id", "season", "position", "games", "snap_share"],
    )


def _build_labels(
    feature_rows: pd.DataFrame,
    role_rows: pd.DataFrame,
    *,
    horizons: tuple[int, ...] = (1,),
    available_label_seasons: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025),
    max_games_only_share: float = 0.05,
    inference_season: int | None = None,
) -> Any:
    module = _labels_module()
    return module.build_qb_role_occupancy_labels(
        feature_rows=feature_rows,
        role_rows=role_rows,
        horizons=horizons,
        available_label_seasons=available_label_seasons,
        max_games_only_share=max_games_only_share,
        inference_season=inference_season,
    )


def test_label_boundaries_use_fractional_snap_share_and_games_threshold() -> None:
    result = _build_labels(
        _feature_rows(),
        _role_rows(
            {
                "player_id": "snap_050",
                "season": 2021,
                "position": "QB",
                "games": 8,
                "snap_share": 0.50,
            },
            {
                "player_id": "snap_0499",
                "season": 2021,
                "position": "QB",
                "games": 8,
                "snap_share": 0.499,
            },
            {
                "player_id": "games_8",
                "season": 2021,
                "position": "QB",
                "games": 8,
                "snap_share": 0.99,
            },
            {
                "player_id": "games_7",
                "season": 2021,
                "position": "QB",
                "games": 7,
                "snap_share": 0.99,
            },
        ),
    )

    labels = _labels(result).set_index(["player_id", "horizon"])

    assert bool(labels.loc[("snap_050", 1), "startable_role_occupancy"]) is True
    assert bool(labels.loc[("snap_0499", 1), "startable_role_occupancy"]) is False
    assert bool(labels.loc[("games_8", 1), "startable_role_occupancy"]) is True
    assert bool(labels.loc[("games_7", 1), "startable_role_occupancy"]) is False
    assert labels["startable_role_occupancy"].any(), (
        "A percent-scale >= 50 snap-share misread yields zero positives and must fail."
    )


def test_games_construction_includes_postseason_weeks_before_labeling() -> None:
    module = _labels_module()
    player_stats = pd.DataFrame(
        [
            {
                "player_id": "postseason_qb",
                "season": 2021,
                "position": "QB",
                "week": week,
                "season_type": "REG" if week <= 7 else "POST",
            }
            for week in range(1, 9)
        ]
    )
    snap_counts = pd.DataFrame(
        [
            {
                "player_id": "postseason_qb",
                "season": 2021,
                "position": "QB",
                "week": week,
                "snap_share": 0.51,
            }
            for week in range(1, 9)
        ]
    )

    role_rows = module.aggregate_qb_role_source(
        player_stats=player_stats,
        snap_counts=snap_counts,
    )
    result = _build_labels(
        pd.DataFrame(
            [
                {
                    "player_id": "postseason_qb",
                    "position": "QB",
                    "feature_season": 2020,
                    "games_t": 8,
                    "training_eligible": True,
                }
            ]
        ),
        role_rows,
    )

    assert role_rows.loc[0, "games"] == 8
    assert bool(_labels(result).loc[0, "startable_role_occupancy"]) is True


def test_pit_labels_use_only_future_horizons_and_exclude_2025_inference_rows() -> None:
    feature_rows = pd.DataFrame(
        [
            {
                "player_id": "pit_qb",
                "position": "QB",
                "feature_season": season,
                "games_t": 8,
                "training_eligible": season <= 2023,
            }
            for season in (2022, 2023, 2024, 2025)
        ]
    )
    role_rows = _role_rows(
        {
            "player_id": "pit_qb",
            "season": 2023,
            "position": "QB",
            "games": 8,
            "snap_share": 0.75,
        },
        {
            "player_id": "pit_qb",
            "season": 2024,
            "position": "QB",
            "games": 8,
            "snap_share": 0.75,
        },
        {
            "player_id": "pit_qb",
            "season": 2025,
            "position": "QB",
            "games": 8,
            "snap_share": 0.75,
        },
    )

    result = _build_labels(
        feature_rows,
        role_rows,
        horizons=(1, 2, 3),
        available_label_seasons=(2023, 2024, 2025),
    )

    labels = _labels(result)
    assert (labels["target_season"] == labels["feature_season"] + labels["horizon"]).all()
    assert 2025 not in set(labels["feature_season"])
    assert labels.groupby("horizon")["feature_season"].max().to_dict() == {
        1: 2024,
        2: 2023,
        3: 2022,
    }


def test_inference_season_rows_never_label_even_when_future_window_exists() -> None:
    result = _build_labels(
        pd.DataFrame(
            [
                {
                    "player_id": "future_qb",
                    "position": "QB",
                    "feature_season": 2025,
                    "games_t": 8,
                    "training_eligible": False,
                }
            ]
        ),
        _role_rows(
            {
                "player_id": "future_qb",
                "season": 2026,
                "position": "QB",
                "games": 8,
                "snap_share": 0.99,
            }
        ),
        available_label_seasons=(2026,),
        inference_season=2025,
    )

    assert _labels(result).empty


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True),
            "duplicate",
        ),
        (
            lambda df: df.assign(startable_role_occupancy="true"),
            "bool",
        ),
        (
            lambda df: df.drop(columns=["horizon"]),
            "horizon",
        ),
        (
            lambda df: df.assign(feature_season="2020"),
            "season",
        ),
    ],
)
def test_label_table_contract_fails_closed(mutate: Any, expected: str) -> None:
    module = _labels_module()
    good = pd.DataFrame(
        [
            {
                "player_id": "contract_qb",
                "feature_season": 2020,
                "target_season": 2021,
                "horizon": 1,
                "startable_role_occupancy": True,
                "label_basis": "games_and_snap",
            }
        ]
    )

    with pytest.raises(ValueError, match=expected):
        module.validate_qb_role_occupancy_label_table(mutate(good))


def test_unknown_target_source_player_is_quarantined_and_never_scored() -> None:
    result = _build_labels(
        pd.DataFrame(
            [
                {
                    "player_id": "known_qb",
                    "position": "QB",
                    "feature_season": 2020,
                    "games_t": 8,
                    "training_eligible": True,
                }
            ]
        ),
        _role_rows(
            {
                "player_id": "known_qb",
                "season": 2021,
                "position": "QB",
                "games": 8,
                "snap_share": 0.75,
            },
            {
                "player_id": "unknown_qb",
                "season": 2021,
                "position": "QB",
                "games": 8,
                "snap_share": 0.75,
            },
        ),
    )

    labels = _labels(result)
    diagnostics = _diagnostics(result)

    assert set(labels["player_id"]) == {"known_qb"}
    assert "unknown_qb" in diagnostics["quarantined_player_ids"]
    assert diagnostics["quarantine_reasons"]["unknown_qb"] == "unknown_player_id"


def test_duplicate_source_rows_are_rejected_before_aggregation() -> None:
    module = _labels_module()
    player_stats = pd.DataFrame(
        [
            {
                "player_id": "dup_qb",
                "season": 2021,
                "position": "QB",
                "week": 1,
                "season_type": "REG",
            },
            {
                "player_id": "dup_qb",
                "season": 2021,
                "position": "QB",
                "week": 1,
                "season_type": "REG",
            },
        ]
    )
    snap_counts = pd.DataFrame(
        [
            {
                "player_id": "dup_qb",
                "season": 2021,
                "position": "QB",
                "week": 1,
                "snap_share": 0.75,
            }
        ]
    )

    with pytest.raises(ValueError, match="duplicate"):
        module.aggregate_qb_role_source(player_stats=player_stats, snap_counts=snap_counts)


def test_duplicate_role_rows_are_rejected_before_label_lookup() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        _build_labels(
            pd.DataFrame(
                [
                    {
                        "player_id": "dup_qb",
                        "position": "QB",
                        "feature_season": 2020,
                        "games_t": 8,
                        "training_eligible": True,
                    }
                ]
            ),
            _role_rows(
                {
                    "player_id": "dup_qb",
                    "season": 2021,
                    "position": "QB",
                    "games": 7,
                    "snap_share": 0.99,
                },
                {
                    "player_id": "dup_qb",
                    "season": 2021,
                    "position": "QB",
                    "games": 8,
                    "snap_share": 0.99,
                },
            ),
        )


def test_games_only_fallback_discloses_basis_and_fails_share_tolerance() -> None:
    result = _build_labels(
        pd.DataFrame(
            [
                {
                    "player_id": player_id,
                    "position": "QB",
                    "feature_season": 2020,
                    "games_t": 8,
                    "training_eligible": True,
                }
                for player_id in ("missing_snap", "snap_050")
            ]
        ),
        _role_rows(
            {
                "player_id": "missing_snap",
                "season": 2021,
                "position": "QB",
                "games": 8,
                "snap_share": pd.NA,
            },
            {
                "player_id": "snap_050",
                "season": 2021,
                "position": "QB",
                "games": 8,
                "snap_share": 0.50,
            },
        ),
        max_games_only_share=0.05,
    )

    labels = _labels(result).set_index("player_id")
    diagnostics = _diagnostics(result)

    assert bool(labels.loc["missing_snap", "startable_role_occupancy"]) is True
    assert labels.loc["missing_snap", "label_basis"] == "games_only"
    assert diagnostics["games_only_share_by_season"][2021]["share"] == 0.5
    assert diagnostics["games_only_share_by_season"][2021]["status"] == "fail"


def test_absent_target_row_labels_negative_with_disclosure_basis() -> None:
    result = _build_labels(
        pd.DataFrame(
            [
                {
                    "player_id": "absent_target",
                    "position": "QB",
                    "feature_season": 2020,
                    "games_t": 8,
                    "training_eligible": True,
                }
            ]
        ),
        _role_rows(),
    )

    labels = _labels(result)

    assert bool(labels.loc[0, "startable_role_occupancy"]) is False
    assert labels.loc[0, "label_basis"] == "absent_target_row"


def test_structural_coverage_matches_available_outcomes_by_horizon() -> None:
    module = _labels_module()

    coverage = module.compute_structural_label_coverage(
        feature_seasons=range(2018, 2026),
        available_label_seasons=range(2018, 2026),
        horizons=(1, 2, 3),
        inference_season=2025,
    )

    assert coverage == {
        1: {"max_feature_season": 2024, "structural_fold_count": 4},
        2: {"max_feature_season": 2023, "structural_fold_count": 4},
        3: {"max_feature_season": 2022, "structural_fold_count": 3},
    }


def test_class_balance_is_recomputed_from_role_occupancy_labels() -> None:
    module = _labels_module()
    labels = pd.DataFrame(
        [
            {
                "player_id": "h1_pos",
                "feature_season": 2020,
                "target_season": 2021,
                "horizon": 1,
                "startable_role_occupancy": True,
                "label_basis": "games_and_snap",
            },
            {
                "player_id": "h1_neg_a",
                "feature_season": 2020,
                "target_season": 2021,
                "horizon": 1,
                "startable_role_occupancy": False,
                "label_basis": "games_and_snap",
            },
            {
                "player_id": "h1_neg_b",
                "feature_season": 2020,
                "target_season": 2021,
                "horizon": 1,
                "startable_role_occupancy": False,
                "label_basis": "absent_target_row",
            },
        ]
    )

    balance = module.compute_qb_role_occupancy_class_balance(labels)

    assert balance.to_dict("records") == [
        {
            "horizon": 1,
            "positive": 1,
            "negative": 2,
            "total": 3,
            "positive_rate": pytest.approx(1 / 3),
        }
    ]
    assert "rank_lte_24_positive_rate" not in set(balance.columns)


def test_producer_script_exposes_frame_injectable_entrypoint() -> None:
    script = _script_module()

    assert callable(script.build_qb_role_occupancy_labels_from_frames)
