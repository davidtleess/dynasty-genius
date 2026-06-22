"""Subsystem 1 canonical consensus math RED contract.

Falsification matrix seed:
- valid nominal multi-observation stats
- even-count raw float median
- S4-parity exclusive IQR
- raw IQR boundary values without any threshold flag in canonical math
- raw unscaled MAD
- distinct source and analyst counts
- staleness as max whole-day age versus ``as_of``
- len==1 IQR boundary
- empty collection fail-loud
- cross-component shape: no ``disagreement_flag`` in the pure math result
"""

from __future__ import annotations

from datetime import date

import pytest

from src.dynasty_genius.mock_consensus.consensus_math import (
    ConsensusObservation,
    compute_consensus_stats,
)


def _obs(
    pick_no: int | None,
    *,
    source_id: str,
    analyst: str,
    published_date: str = "2025-04-20",
    projected_round: int | None = None,
) -> ConsensusObservation:
    return ConsensusObservation(
        pick_no=pick_no,
        projected_round=projected_round,
        source_id=source_id,
        analyst=analyst,
        published_date=published_date,
    )


def _exact_pick_observations(
    pick_nos: list[int],
    *,
    published_dates: list[str] | None = None,
) -> list[ConsensusObservation]:
    dates = published_dates or ["2025-04-20"] * len(pick_nos)
    return [
        _obs(
            pick_no,
            source_id=f"source_{idx}",
            analyst=f"analyst_{idx}",
            published_date=dates[idx],
        )
        for idx, pick_no in enumerate(pick_nos)
    ]


def test_even_count_median_preserves_raw_float_pick() -> None:
    stats = compute_consensus_stats(
        _exact_pick_observations([20, 45]),
        as_of="2025-04-24",
    )

    assert stats.median == 32.5
    assert isinstance(stats.median, float)
    assert stats.min == 20
    assert stats.max == 45


def test_iqr_uses_statistics_quantiles_exclusive_method_for_s4_parity() -> None:
    stats = compute_consensus_stats(
        _exact_pick_observations([10, 20, 30, 40]),
        as_of="2025-04-24",
    )

    assert stats.iqr == pytest.approx(25.0)


@pytest.mark.parametrize(
    ("pick_nos", "expected_iqr"),
    [
        ([10, 12, 14, 16], 5.0),
        ([10, 12, 16, 18], 7.0),
    ],
)
def test_raw_iqr_boundary_values_do_not_emit_policy_flag(
    pick_nos: list[int],
    expected_iqr: float,
) -> None:
    stats = compute_consensus_stats(
        _exact_pick_observations(pick_nos),
        as_of="2025-04-24",
    )

    assert stats.iqr == pytest.approx(expected_iqr)
    assert not hasattr(stats, "disagreement_flag")


def test_mad_is_raw_unscaled_median_absolute_deviation() -> None:
    stats = compute_consensus_stats(
        _exact_pick_observations([10, 12, 14, 16]),
        as_of="2025-04-24",
    )

    assert stats.median == 13.0
    assert stats.mad == pytest.approx(2.0)


def test_counts_distinct_sources_and_distinct_analysts() -> None:
    observations = [
        _obs(10, source_id="source_a", analyst="same"),
        _obs(12, source_id="source_a", analyst="same"),
        _obs(14, source_id="source_b", analyst="same"),
        _obs(16, source_id="source_c", analyst="other"),
    ]

    stats = compute_consensus_stats(observations, as_of="2025-04-24")

    assert stats.n_sources == 3
    assert stats.n_unique_analysts == 2


def test_staleness_days_is_max_whole_day_age_vs_as_of() -> None:
    observations = _exact_pick_observations(
        [10, 12, 14],
        published_dates=["2025-04-20", "2025-04-10", "2025-04-23"],
    )

    stats = compute_consensus_stats(observations, as_of="2025-04-24")

    assert stats.staleness_days == (
        date.fromisoformat("2025-04-24") - date.fromisoformat("2025-04-10")
    ).days


def test_single_pick_has_zero_iqr_and_zero_mad() -> None:
    stats = compute_consensus_stats(
        _exact_pick_observations([31]),
        as_of="2025-04-24",
    )

    assert stats.median == 31.0
    assert stats.iqr == 0.0
    assert stats.mad == 0.0


def test_empty_observation_collection_fails_loud() -> None:
    with pytest.raises(ValueError, match="observations"):
        compute_consensus_stats([], as_of="2025-04-24")
