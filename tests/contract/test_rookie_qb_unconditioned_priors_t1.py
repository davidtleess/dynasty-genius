"""Rookie-QB unconditioned prior table contract (T1 RED).

This pins the producer/table mechanics from
docs/superpowers/specs/2026-07-04-rookie-filter-prior-recalibration-design.md
without touching the T3 runtime filter wiring.
"""

from __future__ import annotations

import importlib
import math
from typing import Any

import pandas as pd
import pytest

GENERATED_AT = "2026-07-04T13:30:00+00:00"
GENERATION_COMMAND = ".venv/bin/python3.14 scripts/compute_rookie_qb_unconditioned_priors.py"
MACHINERY_SHA = "abc123fixture"
SOURCE_CAVEAT = "fixture source; no network"


def _module() -> Any:
    return importlib.import_module("scripts.compute_rookie_qb_unconditioned_priors")


def _roster(
    player_id: str | None,
    *,
    entry_year: int,
    draft_number: int | float | None,
    season: int | None = None,
    position: str = "QB",
) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "season": season if season is not None else entry_year,
        "position": position,
        "entry_year": entry_year,
        "draft_number": draft_number,
    }


def _role(
    player_id: str,
    *,
    season: int,
    games: int,
    snap_share: float | None,
    position: str = "QB",
) -> dict[str, Any]:
    return {
        "player_id": player_id,
        "season": season,
        "position": position,
        "games": games,
        "snap_share": snap_share,
    }


def _compute(rosters: list[dict[str, Any]], roles: list[dict[str, Any]]) -> dict[str, Any]:
    module = _module()
    return module.compute_rookie_qb_unconditioned_priors(
        rosters=pd.DataFrame(rosters),
        role_rows=pd.DataFrame(roles),
        generated_at=GENERATED_AT,
        generation_command=GENERATION_COMMAND,
        machinery_repo_sha=MACHINERY_SHA,
        source_caveat=SOURCE_CAVEAT,
        cohort_entry_years=tuple(range(2018, 2024)),
        horizons=(1, 2, 3),
        prediction_ranges={
            ("round_1_picks_1_32", 1): (0.80, 0.88),
            ("round_2_picks_33_64", 1): (0.45, 0.50),
            ("day3_picks_65_plus", 2): (0.05, 0.08),
            ("undrafted", 1): (0.01, 0.02),
        },
    )


def _row(artifact: dict[str, Any], band: str, horizon: int) -> dict[str, Any]:
    matches = [
        row
        for row in artifact["rows"]
        if row["capital_band"] == band and row["horizon"] == horizon
    ]
    assert len(matches) == 1
    return matches[0]


def test_role_row_direct_priors_pin_band_boundaries_and_table_math() -> None:
    artifact = _compute(
        rosters=[
            _roster("pick32", entry_year=2020, draft_number=32),
            _roster("pick33", entry_year=2020, draft_number=33),
            _roster("pick64", entry_year=2020, draft_number=64),
            _roster("pick65", entry_year=2020, draft_number=65),
            _roster("udfa", entry_year=2020, draft_number=None),
        ],
        roles=[
            _role("pick32", season=2021, games=8, snap_share=0.50),
            _role("pick33", season=2021, games=9, snap_share=0.60),
            _role("pick65", season=2021, games=10, snap_share=0.55),
            _role("udfa", season=2021, games=7, snap_share=0.99),
        ],
    )

    assert _row(artifact, "round_1_picks_1_32", 1) == {
        "capital_band": "round_1_picks_1_32",
        "horizon": 1,
        "n": 1,
        "positives": 1,
        "rate": 1.0,
        "basis": {"games_and_snap": 1, "games_only": 0, "absent_role_row": 0},
    }
    round2 = _row(artifact, "round_2_picks_33_64", 1)
    assert round2["n"] == 2
    assert round2["positives"] == 1
    assert round2["rate"] == pytest.approx(0.5)
    day3 = _row(artifact, "day3_picks_65_plus", 1)
    assert day3["n"] == 1
    assert day3["positives"] == 1
    udfa = _row(artifact, "undrafted", 1)
    assert udfa["n"] == 1
    assert udfa["positives"] == 0
    for row in artifact["rows"]:
        if row["rate"] is not None:
            assert row["positives"] <= row["n"]
            assert math.isclose(row["rate"], row["positives"] / row["n"])


def test_sit_then_start_is_h1_negative_and_h3_positive_without_label_conditioning() -> None:
    artifact = _compute(
        rosters=[_roster("sit_then_start", entry_year=2018, draft_number=26)],
        roles=[_role("sit_then_start", season=2021, games=16, snap_share=0.98)],
    )

    assert _row(artifact, "round_1_picks_1_32", 1)["positives"] == 0
    assert _row(artifact, "round_1_picks_1_32", 2)["positives"] == 0
    assert _row(artifact, "round_1_picks_1_32", 3)["positives"] == 1


def test_observability_window_excludes_unobservable_horizons_not_denominator_rows() -> None:
    artifact = _compute(
        rosters=[
            _roster("recent_qb", entry_year=2023, draft_number=40),
            _roster("old_qb", entry_year=2022, draft_number=41),
        ],
        roles=[
            _role("recent_qb", season=2024, games=8, snap_share=0.50),
            _role("recent_qb", season=2025, games=8, snap_share=0.50),
            _role("old_qb", season=2025, games=8, snap_share=0.50),
        ],
    )

    metadata = artifact["metadata"]
    assert metadata["max_available_role_season"] == 2025
    assert _row(artifact, "round_2_picks_33_64", 1)["n"] == 2
    assert _row(artifact, "round_2_picks_33_64", 2)["n"] == 2
    assert _row(artifact, "round_2_picks_33_64", 3)["n"] == 1
    assert artifact["diagnostics"]["structural_exclusions"] == [
        {
            "player_id": "recent_qb",
            "entry_year": 2023,
            "horizon": 3,
            "target_season": 2026,
            "reason": "target_season_unavailable",
        }
    ]


def test_empty_role_source_fails_closed_instead_of_fabricating_observability() -> None:
    with pytest.raises(ValueError, match="role.*source.*empty"):
        _compute(
            rosters=[_roster("old_qb", entry_year=2018, draft_number=1)],
            roles=[],
        )


def test_games_only_fallback_counts_basis_and_absent_role_row_is_negative() -> None:
    artifact = _compute(
        rosters=[
            _roster("games_only_positive", entry_year=2020, draft_number=10),
            _roster("never_played", entry_year=2020, draft_number=11),
        ],
        roles=[_role("games_only_positive", season=2021, games=9, snap_share=None)],
    )

    row = _row(artifact, "round_1_picks_1_32", 1)
    assert row["n"] == 2
    assert row["positives"] == 1
    assert row["basis"] == {"games_and_snap": 0, "games_only": 1, "absent_role_row": 1}


def test_roster_repeats_collapse_but_conflicting_draft_metadata_fails_closed() -> None:
    artifact = _compute(
        rosters=[
            _roster("repeat_qb", entry_year=2020, draft_number=12, season=2020),
            _roster("repeat_qb", entry_year=2020, draft_number=12, season=2021),
        ],
        roles=[_role("repeat_qb", season=2021, games=8, snap_share=0.5)],
    )
    assert _row(artifact, "round_1_picks_1_32", 1)["n"] == 1

    with pytest.raises(ValueError, match="conflicting.*draft metadata"):
        _compute(
            rosters=[
                _roster("bad_repeat", entry_year=2020, draft_number=12, season=2020),
                _roster("bad_repeat", entry_year=2020, draft_number=13, season=2021),
            ],
            roles=[],
        )


def test_roster_sparse_na_draft_numbers_coalesce_to_known_slot_without_order_dependence() -> None:
    artifact_na_first = _compute(
        rosters=[
            _roster("sparse_qb", entry_year=2020, draft_number=None, season=2020),
            _roster("sparse_qb", entry_year=2020, draft_number=12, season=2021),
        ],
        roles=[_role("sparse_qb", season=2021, games=8, snap_share=0.5)],
    )
    artifact_slot_first = _compute(
        rosters=[
            _roster("sparse_qb", entry_year=2020, draft_number=12, season=2021),
            _roster("sparse_qb", entry_year=2020, draft_number=None, season=2020),
        ],
        roles=[_role("sparse_qb", season=2021, games=8, snap_share=0.5)],
    )

    assert _row(artifact_na_first, "round_1_picks_1_32", 1)["n"] == 1
    assert _row(artifact_na_first, "undrafted", 1)["n"] == 0
    assert _row(artifact_slot_first, "round_1_picks_1_32", 1)["n"] == 1
    assert _row(artifact_slot_first, "undrafted", 1)["n"] == 0
    assert artifact_na_first["rows"] == artifact_slot_first["rows"]


def test_identity_failures_are_quarantined_not_counted_as_negative() -> None:
    artifact = _compute(
        rosters=[
            _roster(None, entry_year=2020, draft_number=20),
            _roster("known_qb", entry_year=2020, draft_number=21),
        ],
        roles=[_role("known_qb", season=2021, games=8, snap_share=0.5)],
    )

    row = _row(artifact, "round_1_picks_1_32", 1)
    assert row["n"] == 1
    assert row["positives"] == 1
    assert artifact["diagnostics"]["quarantined_entries"] == [
        {"player_id": None, "reason": "identity_unresolved"}
    ]


def test_artifact_schema_and_prediction_check_are_report_only() -> None:
    artifact = _compute(
        rosters=[_roster("day3_qb", entry_year=2020, draft_number=100)],
        roles=[_role("day3_qb", season=2022, games=8, snap_share=0.5)],
    )

    assert artifact["metadata"] == {
        "config_version": 2,
        "generated_at": GENERATED_AT,
        "generation_command": GENERATION_COMMAND,
        "machinery_repo_sha": MACHINERY_SHA,
        "source_caveat": SOURCE_CAVEAT,
        "cohort_entry_years": [2018, 2019, 2020, 2021, 2022, 2023],
        "max_available_role_season": 2022,
        "decision_supported": False,
    }
    assert artifact["decision_supported"] is False
    assert artifact["prediction_check"]["status"] == "report_only"
    assert artifact["prediction_check"]["gating"] is False
    expected_checks = {
        ("round_1_picks_1_32", 1),
        ("round_2_picks_33_64", 1),
        ("day3_picks_65_plus", 2),
        ("undrafted", 1),
    }
    observed_checks = {
        (check["capital_band"], check["horizon"])
        for check in artifact["prediction_check"]["checks"]
    }
    assert observed_checks == expected_checks
    assert any(
        check["status"] == "outside_pre_registered_range"
        for check in artifact["prediction_check"]["checks"]
    )


def test_pre_registered_prediction_ranges_are_defaulted_for_real_run() -> None:
    module = _module()
    artifact = module.compute_rookie_qb_unconditioned_priors(
        rosters=pd.DataFrame([_roster("round1_qb", entry_year=2020, draft_number=1)]),
        role_rows=pd.DataFrame([_role("round1_qb", season=2021, games=8, snap_share=0.5)]),
        generated_at=GENERATED_AT,
        generation_command=GENERATION_COMMAND,
        machinery_repo_sha=MACHINERY_SHA,
        source_caveat=SOURCE_CAVEAT,
        cohort_entry_years=tuple(range(2018, 2024)),
        horizons=(1, 2, 3),
    )

    observed_checks = {
        (check["capital_band"], check["horizon"])
        for check in artifact["prediction_check"]["checks"]
    }
    assert observed_checks == {
        ("round_1_picks_1_32", 1),
        ("round_2_picks_33_64", 1),
        ("day3_picks_65_plus", 2),
        ("undrafted", 1),
    }
    assert artifact["prediction_check"]["status"] == "report_only"
    assert artifact["prediction_check"]["gating"] is False


def test_validate_prior_table_fails_duplicate_cells_and_requires_all_h1_bands() -> None:
    module = _module()
    artifact = _compute(
        rosters=[
            _roster("round1_qb", entry_year=2020, draft_number=1),
            _roster("round2_qb", entry_year=2020, draft_number=40),
            _roster("day3_qb", entry_year=2020, draft_number=100),
            _roster("udfa_qb", entry_year=2020, draft_number=None),
        ],
        roles=[_role("round1_qb", season=2021, games=8, snap_share=0.5)],
    )
    module.validate_rookie_qb_prior_table(artifact)

    duplicate = {**artifact, "rows": [*artifact["rows"], artifact["rows"][0].copy()]}
    with pytest.raises(ValueError, match="duplicate.*capital_band.*horizon"):
        module.validate_rookie_qb_prior_table(duplicate)

    null_h1 = {
        **artifact,
        "rows": [
            {**row, "n": 0, "positives": 0, "rate": None}
            if row["capital_band"] == "round_1_picks_1_32" and row["horizon"] == 1
            else row
            for row in artifact["rows"]
        ],
    }
    with pytest.raises(ValueError, match="runtime-consumed H1.*all capital bands"):
        module.validate_rookie_qb_prior_table(null_h1)


def test_observable_empty_non_h1_cell_is_null_never_zero() -> None:
    artifact = _compute(
        rosters=[_roster("round1_qb", entry_year=2020, draft_number=1)],
        roles=[_role("round1_qb", season=2021, games=8, snap_share=0.5)],
    )

    empty_h2 = _row(artifact, "day3_picks_65_plus", 2)
    assert empty_h2["n"] == 0
    assert empty_h2["positives"] == 0
    assert empty_h2["rate"] is None


def test_compute_is_deterministic_and_does_not_write_the_config_artifact(tmp_path) -> None:
    module = _module()
    output_path = tmp_path / "rookie_qb_prior_table_v2.json"
    rosters = [_roster("round1_qb", entry_year=2020, draft_number=1)]
    roles = [_role("round1_qb", season=2021, games=8, snap_share=0.5)]

    first = _compute(rosters, roles)
    second = _compute(rosters, roles)

    assert first == second
    assert not output_path.exists()
    assert callable(module.write_rookie_qb_prior_table)


def test_producer_source_does_not_import_market_or_nfl_usage_inputs() -> None:
    module = _module()
    source = module.__loader__.get_source(module.__name__)
    assert source is not None
    forbidden = ["ktc", "fantasycalc", "dynasty_nerds", "ppg_t", "snap_share_t", "games_t"]
    for token in forbidden:
        assert token not in source
