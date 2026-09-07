"""DG-178 — the rookie FIXTURE adapter: a labelled stand-in, never a model.

The rookie lane (DG-165) owes per-season P(qualifies at h) and E[ppg | qualifies at h]. Until
that candidate exists, integration needs a term set with the right SHAPE so the assembler,
the audit and the tests can run end to end. This adapter builds one from explicit per-horizon
inputs and stamps it ``estimate_class="fixture"`` so it can never be read as a forecast.
"""
from __future__ import annotations

from datetime import date

import pytest

FD = date(2026, 9, 6)


def _row(pid="rk", pos="QB", age=22):
    from src.dynasty_genius.ranking.served_rows import ServedRow

    return ServedRow(player_id=pid, sleeper_id=pid, full_name="Fixture Rookie", position=pos, age=age,
                     dynasty_value_score=70.7, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="A",
                     projection_2y=None, captured_at="2026-09-06T13:00:53+00:00")


def _ref(pos="QB", rate=10.0):
    from src.dynasty_genius.ranking.contract import ReplacementRef

    return ReplacementRef(position=pos, policy="best_available_served_rate", rate_ppg=rate,
                          conditional_rate_ppg=12.0, snapshot_id="s",
                          horizon_assumption="held_constant_from_snapshot")


def test_each_horizon_multiplies_its_own_probability_by_its_own_conditional_margin() -> None:
    """ev_h = P(qualifies at h) x max(0, E[ppg | qualifies at h] - R). Same h, same event,
    both sides. Never P(ever) times a level-conditional path."""
    from src.dynasty_genius.ranking.adapters.rookie_fixture import (
        build_fixture_term_set,
    )

    per_h = [(0.0, 0.0), (0.3, 14.0), (0.5, 16.0), (0.5, 16.0), (0.45, 15.0), (0.4, 14.0)]
    ts = build_fixture_term_set(_row(), _ref(rate=10.0), per_h, forecast_date=FD, label="illustrative")
    evs = [t.ev_above_replacement for t in ts.terms]
    assert evs == pytest.approx([0.0, 0.3 * 4.0, 0.5 * 6.0, 0.5 * 6.0, 0.45 * 5.0, 0.4 * 4.0])
    assert ts.coverage == "full"


def test_the_fixture_is_stamped_as_a_fixture_and_says_so_in_every_event() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_fixture import (
        build_fixture_term_set,
    )

    ts = build_fixture_term_set(_row(), _ref(), [(0.0, 0.0)] * 6, forecast_date=FD, label="x")
    assert ts.producer.estimate_class == "fixture"
    assert all("FIXTURE" in t.conditioning_event for t in ts.terms)
    assert ts.served.dvs_engine == "A" and ts.served.dynasty_value_score == 70.7


def test_a_zero_game_rookie_with_no_fixture_probabilities_is_zero_not_blank() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_fixture import (
        build_fixture_term_set,
    )

    ts = build_fixture_term_set(_row(), _ref(), [(0.0, 0.0)] * 6, forecast_date=FD, label="x")
    assert [t.ev_above_replacement for t in ts.terms] == [0.0] * 6


def test_a_probability_outside_the_unit_interval_is_refused() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_fixture import (
        build_fixture_term_set,
    )

    with pytest.raises(ValueError, match="probability"):
        build_fixture_term_set(_row(), _ref(), [(1.2, 14.0)] + [(0.0, 0.0)] * 5, forecast_date=FD, label="x")


def test_a_conditional_rate_below_the_bar_contributes_zero_that_season() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_fixture import (
        build_fixture_term_set,
    )

    ts = build_fixture_term_set(_row(), _ref(rate=10.0), [(0.9, 8.0)] + [(0.0, 0.0)] * 5,
                                forecast_date=FD, label="x")
    assert ts.terms[0].ev_above_replacement == 0.0


def test_the_fixture_needs_every_horizon_or_says_it_is_partial() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_fixture import (
        build_fixture_term_set,
    )

    ts = build_fixture_term_set(_row(), _ref(), [(0.0, 0.0), (0.2, 13.0)], forecast_date=FD, label="x")
    assert ts.coverage == "partial"
    assert "horizons" in ts.reason
