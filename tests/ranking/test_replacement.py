"""DG-178 — the replacement policy David ruled: 'the next who is actually available'.

The bar at each position is the best player NOBODY in his league owns, measured on the
served rate. It is held constant across horizons as a declared scenario. Band-averaging
(his own suggestion) is a parameter that defaults to 1, so the ruling ships unchanged.
"""
from __future__ import annotations

import pytest


def _row(pid, pos, dvs, proj, p90=20.1, clamped=False, name=None):
    from src.dynasty_genius.ranking.served_rows import ServedRow

    return ServedRow(player_id=pid, sleeper_id=pid, full_name=name or pid, position=pos, age=25,
                     dynasty_value_score=dvs, dvs_p90_ref=p90, dvs_clamped=clamped,
                     dvs_engine="B", projection_2y=proj, captured_at="2026-09-06T13:00:53+00:00")


def test_the_bar_is_the_best_unrostered_served_rate_not_the_best_player() -> None:
    from src.dynasty_genius.ranking.replacement import available_replacement

    rows = [_row("star", "WR", 80.0, 18.0), _row("fa1", "WR", 45.0, 10.0), _row("fa2", "WR", 40.0, 9.5)]
    ref = available_replacement(rows, rostered_ids={"star"}, snapshot_id="league-x")["WR"]
    assert ref.player_id == "fa1"
    assert ref.rate_ppg == pytest.approx(45.0 / 100 * 20.1)
    assert ref.conditional_rate_ppg == pytest.approx(10.0)
    assert ref.policy == "best_available_served_rate"
    assert ref.horizon_assumption == "held_constant_from_snapshot"
    assert ref.snapshot_id == "league-x"
    assert ref.band == 1


def test_band_averaging_is_opt_in_and_averages_the_top_band() -> None:
    from src.dynasty_genius.ranking.replacement import available_replacement

    rows = [_row("fa1", "RB", 40.0, 9.0), _row("fa2", "RB", 30.0, 7.0), _row("fa3", "RB", 10.0, 3.0)]
    ref = available_replacement(rows, rostered_ids=set(), snapshot_id="s", band=2)["RB"]
    assert ref.band == 2
    assert ref.rate_ppg == pytest.approx(((40.0 + 30.0) / 2) / 100 * 20.1)
    assert ref.conditional_rate_ppg == pytest.approx(8.0)
    assert ref.player_id is None  # an average is not one man


def test_rows_without_a_conditional_projection_cannot_set_the_bar() -> None:
    """An Engine A prospect has a served score but no E[ppg | plays]; the margin key needs
    the conditional rate, so he cannot be the bar even when unrostered."""
    from src.dynasty_genius.ranking.replacement import available_replacement

    rows = [_row("rookie", "TE", 50.0, None), _row("fa", "TE", 30.0, 6.0)]
    ref = available_replacement(rows, rostered_ids=set(), snapshot_id="s")["TE"]
    assert ref.player_id == "fa"


def test_a_position_with_nobody_available_is_an_error_not_a_zero() -> None:
    from src.dynasty_genius.ranking.replacement import available_replacement

    rows = [_row("q", "QB", 50.0, 12.0)]
    with pytest.raises(ValueError, match="QB"):
        available_replacement(rows, rostered_ids={"q"}, snapshot_id="s")


def test_a_clamped_row_cannot_set_the_bar_because_its_rate_is_a_bound() -> None:
    from src.dynasty_genius.ranking.replacement import available_replacement

    rows = [_row("cl", "QB", 100.0, 25.0, clamped=True), _row("fa", "QB", 50.0, 12.0)]
    ref = available_replacement(rows, rostered_ids=set(), snapshot_id="s")["QB"]
    assert ref.player_id == "fa"
