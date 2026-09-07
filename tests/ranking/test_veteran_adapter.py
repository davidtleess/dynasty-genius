"""DG-178 — the veteran adapter: served pieces + retention cells -> unconditional terms.

This is the ONE place a probability meets a conditional mean, and it happens inside one
declared event: P(qualifying season) recovered from the served row, E[ppg | plays] from the
same row, the replacement subtracted INSIDE the bracket, then the cells' unconditional
ratios carry it forward:

    ev_0 = P x (E - R)          ev_h = ev_0 x R(h)   for h = 1..5

Every test here names the production change that would make it fail.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "retention_cells_fixture.json"
FD = date(2026, 9, 6)


def _cells(path=FIXTURE):
    from src.dynasty_genius.ranking.survival_cells import RetentionCells

    return RetentionCells.load(path)


def _row(pid="p", pos="WR", age=24, dvs=None, proj=None, p90=20.1, clamped=False, engine="B",
         served_rate=None):
    from src.dynasty_genius.ranking.served_rows import ServedRow

    if served_rate is not None:
        dvs = served_rate / p90 * 100.0
    return ServedRow(player_id=pid, sleeper_id=pid, full_name=pid, position=pos, age=age,
                     dynasty_value_score=dvs, dvs_p90_ref=p90, dvs_clamped=clamped,
                     dvs_engine=engine, projection_2y=proj, captured_at="2026-09-06T13:00:53+00:00")


def _ref(pos="WR", rate=9.0, cond=10.0):
    from src.dynasty_genius.ranking.contract import ReplacementRef

    return ReplacementRef(position=pos, policy="best_available_served_rate", rate_ppg=rate,
                          conditional_rate_ppg=cond, snapshot_id="s",
                          horizon_assumption="held_constant_from_snapshot")


def _build(row, ref=None, cells=None):
    from src.dynasty_genius.ranking.adapters.veteran_served import build_term_set

    return build_term_set(row, ref or _ref(row.position), cells or _cells(), forecast_date=FD)


def test_availability_is_applied_once_inside_the_bracket() -> None:
    """P=0.5, E=18, R=9 -> ev_0 = 0.5 x (18 - 9) = 4.5. Applying P twice gives 2.25; applying
    it outside the bracket (P x E - R) gives 0.0. The WR 24-25 m2 fixture cell is flat-ish, so
    the later horizons are ev_0 x R(h) exactly."""
    # margin = E / cond = 18 / 11.6 -> 1.552, inside the fixture's m2 bin [1.5, 1.66)
    ts = _build(_row(age=24, served_rate=9.0, proj=18.0), _ref(rate=9.0, cond=11.6))
    assert ts.coverage == "full"
    evs = [t.ev_above_replacement for t in ts.terms]
    assert evs[0] == pytest.approx(4.5)
    assert evs[1:] == pytest.approx([4.5 * r for r in (0.9, 0.8, 0.7, 0.6, 0.5)])


def test_p_is_recovered_from_the_served_row_as_served_rate_over_projection() -> None:
    ts = _build(_row(age=24, dvs=45.0, p90=20.1, proj=12.06), _ref(rate=6.0, cond=7.8))
    # served rate 9.045, P = 0.75, ev_0 = 0.75 x (12.06 - 6.0)
    assert ts.terms[0].ev_above_replacement == pytest.approx(0.75 * (12.06 - 6.0))
    assert ts.producer.estimate_class == "candidate"
    assert ts.served.dynasty_value_score == 45.0


def test_a_clamped_served_row_yields_a_partial_because_p_is_only_a_bound() -> None:
    ts = _build(_row(age=24, dvs=100.0, clamped=True, proj=25.0))
    assert ts.coverage == "partial"
    assert ts.terms == []
    assert "bound" in ts.reason


def test_a_row_with_no_conditional_projection_has_no_veteran_terms() -> None:
    """An Engine A prospect: served score, no E[ppg | plays]. The veteran path cannot say
    anything about him; the rookie lane owes his terms."""
    ts = _build(_row(age=22, dvs=70.7, proj=None, engine="A"))
    assert ts.coverage == "none"
    assert "no conditional projection" in ts.reason
    assert ts.served.dvs_engine == "A"


def test_a_row_with_no_served_score_has_no_terms_and_keeps_identity() -> None:
    ts = _build(_row(pid="dell", age=26, dvs=None, proj=None, engine=None))
    assert ts.coverage == "none" and ts.player_id == "dell"
    assert "no served score" in ts.reason


def test_attrition_an_older_player_with_the_same_season_is_worth_less_over_the_horizon() -> None:
    """Fixture WR cells: 24-25 m2 decays slowly, 30-31 m2 decays fast. Same E, P, R. Served
    whole-year ages 24 and 30 look up 24.5 and 30.5 under the cells' right-inclusive cut."""
    young = _build(_row(pid="y", age=24, served_rate=9.0, proj=18.0), _ref(rate=9.0, cond=11.6))
    old = _build(_row(pid="o", age=30, served_rate=9.0, proj=18.0), _ref(rate=9.0, cond=11.6))
    assert young.terms[0].ev_above_replacement == old.terms[0].ev_above_replacement
    assert sum(t.ev_above_replacement for t in young.terms) > sum(t.ev_above_replacement for t in old.terms)


def test_a_suppressed_cell_gives_a_partial_with_the_files_reason_and_only_h0() -> None:
    """DG-176's shape on a veteran row: young quarterback, thin bin. h=0 is known; the future
    is a stated absence, never a neighbour's cell."""
    # QB <=23, margin 1.3 -> the fixture's suppressed m1 bin
    ts = _build(_row(pos="QB", age=22, served_rate=12.0, proj=15.6), _ref("QB", rate=10.0, cond=12.0))
    assert ts.coverage == "partial"
    assert [t.h for t in ts.terms] == [0]
    assert "n=10 < 12" in ts.reason


def test_an_unknown_age_cannot_reach_the_cells_and_says_so() -> None:
    ts = _build(_row(age=None, served_rate=9.0, proj=18.0), _ref(rate=9.0, cond=11.6))
    assert ts.coverage == "partial"
    assert "age" in ts.reason


def test_survival_keys_in_the_cell_file_cannot_enter_the_value(tmp_path) -> None:
    """R is unconditional; survival is already inside it. Halve any S(h) the file might carry
    and nothing may move. Fires the moment an adapter multiplies by S again."""
    raw = json.loads(FIXTURE.read_text())
    for c in raw["cells"]:
        for h in range(1, 6):
            c[f"S{h}"] = 0.5 * (0.9 ** h)
    perturbed = tmp_path / "cells_with_S.json"
    perturbed.write_text(json.dumps(raw))
    row = _row(age=24, served_rate=9.0, proj=18.0)
    a = _build(row, _ref(rate=9.0, cond=11.6), _cells())
    b = _build(row, _ref(rate=9.0, cond=11.6), _cells(perturbed))
    assert [t.ev_above_replacement for t in a.terms] == [t.ev_above_replacement for t in b.terms]


def test_a_served_rate_above_the_projection_is_a_broken_producer_not_a_probability() -> None:
    with pytest.raises(ValueError, match="probability"):
        _build(_row(age=24, served_rate=12.0, proj=10.0), _ref(rate=9.0, cond=11.6))


def test_the_h0_term_names_the_availability_event_it_was_integrated_over() -> None:
    from src.dynasty_genius.models.availability import EVENT_DEFINITION

    ts = _build(_row(age=24, served_rate=9.0, proj=18.0), _ref(rate=9.0, cond=11.6))
    assert EVENT_DEFINITION in ts.terms[0].conditioning_event
    assert "UNCONDITIONAL" in ts.terms[1].conditioning_event.upper()


def test_the_replacement_subtracted_is_recorded_with_the_bar_players_conditional_rate() -> None:
    ref = _ref(rate=9.0, cond=11.6)
    ts = _build(_row(age=25, served_rate=9.0, proj=18.0), ref)
    assert ts.replacement_ref == ref
    assert ts.producer.version.startswith("served:2026-09-06T13:00:53")


def test_below_the_bar_today_is_zero_now_and_an_unmodelled_future_not_six_zeros() -> None:
    """E <= R establishes nothing about seasons 1-5: the cells are keyed on a positive
    margin and say nothing about him. Before this fix seven of David's players carried six
    full zero years as if that were measured."""
    ts = _build(_row(age=24, served_rate=7.0, proj=8.5), _ref(rate=9.0, cond=10.0))
    assert ts.coverage == "partial"
    assert [t.h for t in ts.terms] == [0]
    assert ts.terms[0].ev_above_replacement == 0.0
    assert "below replacement" in ts.reason and "unmodelled" in ts.reason


def test_a_served_whole_year_age_is_binned_as_the_cells_would_bin_his_true_age() -> None:
    """The artifact serves Sleeper's whole-year age (floor). The cells were cut on exact age at
    September 1, right-inclusive: (23, 25] is '24-25'. A served 23 is a true age in [23, 24),
    which the cells put in '24-25' except at exactly 23.0. So the adapter looks up k + 0.5 and
    says so. Fixture: the QB '<=23' m1 cell is suppressed, the QB '24-25' m1 cell exists."""
    # margin = 15.6 / 12.0 = 1.3 -> the fixture's QB m1 bin [1.2, 1.5)
    ts = _build(_row(pos="QB", age=23, served_rate=12.0, proj=15.6), _ref("QB", rate=10.0, cond=12.0))
    assert ts.coverage == "full", ts.reason
    assert "24-25" in ts.terms[1].conditioning_event
    assert "whole-year" in ts.terms[1].conditioning_event


def test_a_served_age_of_twenty_two_stays_in_the_youngest_band() -> None:
    ts = _build(_row(pos="QB", age=22, served_rate=12.0, proj=15.6), _ref("QB", rate=10.0, cond=12.0))
    assert ts.coverage == "partial" and "n=10 < 12" in ts.reason
