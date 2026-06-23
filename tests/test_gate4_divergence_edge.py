"""Gate-4 pure divergence-edge validation engine contracts.

T1 is intentionally fixture-only: no archive DB, no file I/O, no model calls.
The locked contract is spec commit 84531dc.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.dynasty_genius.eval import gate4_divergence_edge as gate4


def _month_fixture(month: int, high_delta: float, neutral_delta: float) -> list[dict]:
    snap = date(2025, month, 1)
    rows: list[dict] = []
    for i in range(5):
        rows.append(
            {
                "player_id": f"h{month}_{i}",
                "position": "WR",
                "snapshot_date": snap,
                "initial_market_pct": 25.0 + i,
                "bucket": "MODEL_HIGH_MARKET_LOW",
                "fwd_delta": high_delta,
            }
        )
        rows.append(
            {
                "player_id": f"n{month}_{i}",
                "position": "WR",
                "snapshot_date": snap,
                "initial_market_pct": 25.0 + i,
                "bucket": "NEUTRAL",
                "fwd_delta": neutral_delta,
            }
        )
    return rows


def test_within_position_percentiles_are_not_cross_position() -> None:
    rows = [
        {"player_id": "qb_low", "position": "QB", "model_value": 10, "market_value": 90},
        {"player_id": "qb_mid", "position": "QB", "model_value": 20, "market_value": 80},
        {"player_id": "qb_high", "position": "QB", "model_value": 30, "market_value": 70},
        {"player_id": "wr_low", "position": "WR", "model_value": 1000, "market_value": 1},
        {"player_id": "wr_high", "position": "WR", "model_value": 2000, "market_value": 2},
    ]

    scored = gate4.compute_within_position_percentiles(
        rows,
        model_value_key="model_value",
        market_value_key="market_value",
    )
    by_id = {row["player_id"]: row for row in scored}

    assert by_id["qb_low"]["model_pct"] == 0.0
    assert by_id["qb_mid"]["model_pct"] == 50.0
    assert by_id["qb_high"]["model_pct"] == 100.0
    assert by_id["wr_low"]["model_pct"] == 0.0
    assert by_id["wr_high"]["model_pct"] == 100.0
    assert by_id["qb_low"]["market_pct"] == 100.0


@pytest.mark.parametrize(
    ("model_pct", "market_pct", "expected"),
    [
        (70.0, 50.0, "MODEL_HIGH_MARKET_LOW"),
        (30.0, 50.0, "MODEL_LOW_MARKET_HIGH"),
        (55.0, 50.0, "NEUTRAL"),
        (45.0, 50.0, "NEUTRAL"),
        (69.99, 50.0, None),
        (30.01, 50.0, None),
    ],
)
def test_divergence_bucket_edges_are_locked(
    model_pct: float,
    market_pct: float,
    expected: str | None,
) -> None:
    assert gate4.classify_divergence(model_pct, market_pct) == expected


def test_forward_date_resolver_is_forward_only_with_seven_day_tolerance() -> None:
    available = [
        date(2026, 2, 28),  # before Jan 1 + 60; forbidden even if nearest
        date(2026, 3, 2),
        date(2026, 3, 5),
    ]

    assert gate4.resolve_forward_date(date(2026, 1, 1), 60, available) == date(
        2026,
        3,
        2,
    )
    assert gate4.resolve_forward_date(date(2026, 1, 1), 60, [date(2026, 3, 10)]) is None


def test_forward_outcome_uses_future_market_pct_delta() -> None:
    start = [
        {
            "player_id": "p1",
            "position": "RB",
            "snapshot_date": date(2025, 1, 1),
            "market_pct": 40.0,
        }
    ]
    future = [{"player_id": "p1", "position": "RB", "market_pct": 62.5}]

    out = gate4.compute_forward_outcomes(start, future, horizon_days=60)

    assert out[0]["fwd_delta"] == 22.5
    assert out[0]["outcome_status"] == "observed"


def test_disappeared_player_gets_fifth_percentile_cohort_outcome() -> None:
    start = [
        {
            "player_id": f"p{i}",
            "position": "RB",
            "snapshot_date": date(2025, 1, 1),
            "market_pct": 50.0,
        }
        for i in range(6)
    ]
    future = [
        {"player_id": "p0", "position": "RB", "market_pct": 30.0},
        {"player_id": "p1", "position": "RB", "market_pct": 40.0},
        {"player_id": "p2", "position": "RB", "market_pct": 50.0},
        {"player_id": "p3", "position": "RB", "market_pct": 60.0},
        {"player_id": "p4", "position": "RB", "market_pct": 70.0},
    ]

    out = gate4.compute_forward_outcomes(start, future, horizon_days=60)
    by_id = {row["player_id"]: row for row in out}

    assert by_id["p5"]["outcome_status"] == "survivorship_penalty"
    assert by_id["p5"]["fwd_delta"] == pytest.approx(-18.0)


def test_survivorship_penalty_is_position_horizon_date_specific() -> None:
    jan = date(2025, 1, 1)
    mar = date(2025, 3, 1)
    start = []
    future = []
    for prefix, snap, future_pcts in [
        ("jan", jan, [30.0, 50.0, 70.0, 90.0, 110.0]),
        ("mar", mar, [-10.0, 10.0, 30.0, 50.0, 70.0]),
    ]:
        for i in range(6):
            start.append(
                {
                    "player_id": f"{prefix}_{i}",
                    "position": "RB",
                    "snapshot_date": snap,
                    "market_pct": 50.0,
                }
            )
        for i, pct in enumerate(future_pcts):
            future.append({"player_id": f"{prefix}_{i}", "position": "RB", "market_pct": pct})

    out = gate4.compute_forward_outcomes(start, future, horizon_days=60)
    by_id = {row["player_id"]: row for row in out}

    assert by_id["jan_5"]["fwd_delta"] == pytest.approx(-16.0)
    assert by_id["mar_5"]["fwd_delta"] == pytest.approx(-56.0)


def test_matched_lift_drops_stratum_with_too_few_signal_or_control() -> None:
    rows = []
    rows += _month_fixture(1, high_delta=20.0, neutral_delta=5.0)
    rows += _month_fixture(2, high_delta=8.0, neutral_delta=2.0)
    rows += [
        {
            "player_id": f"thin_h{i}",
            "position": "WR",
            "snapshot_date": date(2025, 3, 1),
            "initial_market_pct": 35.0,
            "bucket": "MODEL_HIGH_MARKET_LOW",
            "fwd_delta": 100.0,
        }
        for i in range(4)
    ]
    rows += [
        {
            "player_id": f"thin_n{i}",
            "position": "WR",
            "snapshot_date": date(2025, 3, 1),
            "initial_market_pct": 35.0,
            "bucket": "NEUTRAL",
            "fwd_delta": -100.0,
        }
        for i in range(20)
    ]

    result = gate4.compute_matched_lift(
        rows,
        signal_bucket="MODEL_HIGH_MARKET_LOW",
        control_bucket="NEUTRAL",
    )

    assert result["lift"] == pytest.approx(10.5)
    assert result["kept_strata"] == 2
    assert result["dropped_strata"] == 1
    assert result["n_signal"] == 10
    assert result["n_control"] == 10


def test_month_block_bootstrap_recomputes_matched_lift_and_drops_thin_strata() -> None:
    rows = []
    rows += _month_fixture(1, high_delta=10.0, neutral_delta=0.0)
    rows += [
        {
            "player_id": f"thin_h{i}",
            "position": "WR",
            "snapshot_date": date(2025, 1, 1),
            "initial_market_pct": 35.0,
            "bucket": "MODEL_HIGH_MARKET_LOW",
            "fwd_delta": 1000.0,
        }
        for i in range(4)
    ]
    rows += [
        {
            "player_id": f"thin_n{i}",
            "position": "WR",
            "snapshot_date": date(2025, 1, 1),
            "initial_market_pct": 35.0,
            "bucket": "NEUTRAL",
            "fwd_delta": -1000.0,
        }
        for i in range(20)
    ]

    result = gate4.month_block_bootstrap_ci(
        rows,
        signal_bucket="MODEL_HIGH_MARKET_LOW",
        control_bucket="NEUTRAL",
        n_resamples=20,
        rng_seed=7,
    )

    assert result["lift"] == pytest.approx(10.0)
    assert result["ci95"] == pytest.approx((10.0, 10.0))


def test_month_block_bootstrap_point_estimate_matches_weighted_matched_lift() -> None:
    rows = []
    rows += _month_fixture(1, high_delta=20.0, neutral_delta=0.0)
    for i in range(20):
        rows.append(
            {
                "player_id": f"h2_{i}",
                "position": "WR",
                "snapshot_date": date(2025, 2, 1),
                "initial_market_pct": 25.0 + (i % 5),
                "bucket": "MODEL_HIGH_MARKET_LOW",
                "fwd_delta": 0.0,
            }
        )
        rows.append(
            {
                "player_id": f"n2_{i}",
                "position": "WR",
                "snapshot_date": date(2025, 2, 1),
                "initial_market_pct": 25.0 + (i % 5),
                "bucket": "NEUTRAL",
                "fwd_delta": 0.0,
            }
        )

    expected = gate4.compute_matched_lift(
        rows,
        signal_bucket="MODEL_HIGH_MARKET_LOW",
        control_bucket="NEUTRAL",
    )["lift"]
    result = gate4.month_block_bootstrap_ci(
        rows,
        signal_bucket="MODEL_HIGH_MARKET_LOW",
        control_bucket="NEUTRAL",
        n_resamples=100,
        rng_seed=7,
    )

    assert expected == pytest.approx(4.0)
    assert result["lift"] == pytest.approx(expected)


def test_month_block_bootstrap_reports_ci_and_effective_blocks() -> None:
    rows = []
    for month in range(1, 7):
        rows += _month_fixture(month, high_delta=20.0, neutral_delta=5.0)

    result = gate4.month_block_bootstrap_ci(
        rows,
        signal_bucket="MODEL_HIGH_MARKET_LOW",
        control_bucket="NEUTRAL",
        n_resamples=300,
        rng_seed=7,
    )

    assert result["effective_month_block_count"] == 6
    assert result["lift"] == pytest.approx(15.0)
    assert result["ci95"][0] > 0.0
    assert result["ci95"][1] > 0.0


def test_non_overlapping_sensitivity_keeps_dates_spaced_by_horizon() -> None:
    rows = []
    for month in [1, 2, 3, 4, 5, 6]:
        rows += _month_fixture(month, high_delta=12.0, neutral_delta=2.0)

    result = gate4.non_overlapping_sensitivity(
        rows,
        horizon_days=60,
        signal_bucket="MODEL_HIGH_MARKET_LOW",
        control_bucket="NEUTRAL",
    )

    assert result["selected_dates"] == [date(2025, 1, 1), date(2025, 4, 1), date(2025, 6, 1)]
    assert result["sign"] == "positive"


def test_non_overlapping_sensitivity_enforces_exact_day_spacing() -> None:
    rows = []
    for snap, high_delta, neutral_delta in [
        (date(2025, 1, 1), 12.0, 2.0),
        (date(2025, 3, 1), -12.0, -2.0),  # 59 days after Jan 1; must be skipped.
        (date(2025, 3, 2), 14.0, 1.0),
    ]:
        for i in range(5):
            rows.append(
                {
                    "player_id": f"h{snap}_{i}",
                    "position": "WR",
                    "snapshot_date": snap,
                    "initial_market_pct": 25.0 + i,
                    "bucket": "MODEL_HIGH_MARKET_LOW",
                    "fwd_delta": high_delta,
                }
            )
            rows.append(
                {
                    "player_id": f"n{snap}_{i}",
                    "position": "WR",
                    "snapshot_date": snap,
                    "initial_market_pct": 25.0 + i,
                    "bucket": "NEUTRAL",
                    "fwd_delta": neutral_delta,
                }
            )

    result = gate4.non_overlapping_sensitivity(
        rows,
        horizon_days=60,
        signal_bucket="MODEL_HIGH_MARKET_LOW",
        control_bucket="NEUTRAL",
    )

    assert result["selected_dates"] == [date(2025, 1, 1), date(2025, 3, 2)]
    assert result["sign"] == "positive"


def test_claim_level_requires_training_cutoff_before_every_test_date() -> None:
    test_dates = [date(2025, 6, 1), date(2025, 9, 1)]

    assert gate4.derive_claim_level(test_dates, training_cutoff=date(2025, 5, 31)) == (
        "tradeable_historical_edge"
    )
    assert gate4.derive_claim_level(test_dates, training_cutoff=date(2025, 6, 2)) == (
        "current_model_retrospective_diagnostic"
    )
    assert gate4.derive_claim_level(test_dates, training_cutoff=None) == (
        "current_model_retrospective_diagnostic"
    )


def _passing_horizon() -> dict:
    return {
        "lift_HIGH": 12.0,
        "lift_LOW": 9.0,
        "ci_HIGH": (1.0, 20.0),
        "ci_LOW": (0.5, 18.0),
        "effect_size_HIGH": 12.0,
        "effective_month_block_count": 6,
        "non_overlapping_sensitivity_sign": "positive",
        "n_by_bucket": {
            "MODEL_HIGH_MARKET_LOW": 40,
            "MODEL_LOW_MARKET_HIGH": 35,
            "NEUTRAL": 80,
        },
    }


def test_verdict_pass_requires_both_60_and_90_horizons_all_criteria() -> None:
    verdict = gate4.evaluate_verdict(
        horizon_results={60: _passing_horizon(), 90: _passing_horizon()},
        coverage={
            "usable_t_dates_by_horizon": {60: 8, 90: 8},
            "joined_observations": 240,
            "identity_coverage": 0.94,
        },
        stability={
            "leave_one_month_out_high_signs": ["positive"] * 8,
            "top_position_contribution": 0.45,
            "top_position_excluded_high_sign": "positive",
        },
        source_family_status="single_source",
        pit_model_status="ok",
    )

    assert verdict["verdict"] == "PASS"
    assert verdict["decision_supported"] is False


@pytest.mark.parametrize(
    ("source_status", "pit_status", "identity_coverage", "expected"),
    [
        ("mixed_source", "ok", 0.95, "SOURCE_INADEQUATE"),
        ("single_source", "inadequate", 0.95, "MODEL_PIT_INADEQUATE"),
        ("single_source", "ok", 0.89, "IDENTITY_COVERAGE_INADEQUATE"),
    ],
)
def test_verdict_fail_closed_precedes_statistical_pass_fail(
    source_status: str,
    pit_status: str,
    identity_coverage: float,
    expected: str,
) -> None:
    verdict = gate4.evaluate_verdict(
        horizon_results={60: _passing_horizon(), 90: _passing_horizon()},
        coverage={
            "usable_t_dates_by_horizon": {60: 8, 90: 8},
            "joined_observations": 240,
            "identity_coverage": identity_coverage,
        },
        stability={
            "leave_one_month_out_high_signs": ["positive"] * 8,
            "top_position_contribution": 0.45,
            "top_position_excluded_high_sign": "positive",
        },
        source_family_status=source_status,
        pit_model_status=pit_status,
    )

    assert verdict["verdict"] == expected


def test_verdict_underpowered_for_effective_month_blocks_below_floor() -> None:
    weak = _passing_horizon()
    weak["effective_month_block_count"] = 5

    verdict = gate4.evaluate_verdict(
        horizon_results={60: weak, 90: _passing_horizon()},
        coverage={
            "usable_t_dates_by_horizon": {60: 8, 90: 8},
            "joined_observations": 240,
            "identity_coverage": 0.94,
        },
        stability={
            "leave_one_month_out_high_signs": ["positive"] * 8,
            "top_position_contribution": 0.45,
            "top_position_excluded_high_sign": "positive",
        },
        source_family_status="single_source",
        pit_model_status="ok",
    )

    assert verdict["verdict"] == "UNDERPOWERED"


def test_verdict_fail_when_powered_effect_size_or_direction_fails() -> None:
    failing = _passing_horizon()
    failing["effect_size_HIGH"] = 7.99

    verdict = gate4.evaluate_verdict(
        horizon_results={60: failing, 90: _passing_horizon()},
        coverage={
            "usable_t_dates_by_horizon": {60: 8, 90: 8},
            "joined_observations": 240,
            "identity_coverage": 0.94,
        },
        stability={
            "leave_one_month_out_high_signs": ["positive"] * 8,
            "top_position_contribution": 0.45,
            "top_position_excluded_high_sign": "positive",
        },
        source_family_status="single_source",
        pit_model_status="ok",
    )

    assert verdict["verdict"] == "FAIL"


def test_label_shuffle_preserves_date_position_counts_but_breaks_assignments() -> None:
    rows = _month_fixture(1, high_delta=20.0, neutral_delta=5.0)

    shuffled = gate4.shuffle_labels_within_date_position(rows, rng_seed=3)

    original_counts = gate4.bucket_counts(rows, group_by=["snapshot_date", "position"])
    shuffled_counts = gate4.bucket_counts(shuffled, group_by=["snapshot_date", "position"])
    assert shuffled_counts == original_counts
    assert [row["bucket"] for row in shuffled] != [row["bucket"] for row in rows]


def test_date_leakage_guard_rejects_future_data_in_bucket_assignment() -> None:
    with pytest.raises(ValueError, match="look-ahead"):
        gate4.assert_no_bucket_lookahead(
            bucket_snapshot_date=date(2025, 1, 1),
            feature_as_of=date(2025, 4, 1),
        )


def test_single_source_family_assertion_rejects_mixed_sources() -> None:
    rows = [
        {"source": "fc_native", "settings_hash": "sf_ppr"},
        {"source": "ktc_community_csv", "settings_hash": "sf_ppr"},
    ]

    with pytest.raises(ValueError, match="single source"):
        gate4.assert_single_source_family(rows)
