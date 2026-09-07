"""DG-178 — the assembler weights and sums. Nothing else.

Every term it receives is already unconditional and in one unit, so the only thing the
assembler is allowed to add is TIME PREFERENCE — the declared posture's discount. These
tests pin that it does exactly that, keeps every player on the board with a stated reason
when it cannot value him, and never lets a research number impersonate the served one.
"""
from __future__ import annotations

from datetime import date

import pytest

FD = date(2026, 9, 6)


def _terms(evs, event="fixture event"):
    from src.dynasty_genius.ranking.contract import (
        HorizonTerm,
        annual_target,
        season_for_horizon,
    )

    return [HorizonTerm(h=h, season=season_for_horizon(FD, h), ev_above_replacement=ev,
                        conditioning_event=event, spec=annual_target(FD)) for h, ev in enumerate(evs)]


def _ts(player_id, position, evs=None, coverage="full", reason=None, estimate_class="candidate",
        served=None, full_name=None):
    from src.dynasty_genius.ranking.contract import (
        ProducerRef,
        ReplacementRef,
        ServedReference,
        TermSet,
    )

    return TermSet(
        player_id=player_id, position=position, forecast_date=FD, full_name=full_name,
        producer=ProducerRef(name="fixture", version="0", estimate_class=estimate_class),
        replacement_ref=ReplacementRef(position=position, policy="fixture", rate_ppg=9.0,
                                       snapshot_id="s", horizon_assumption="held_constant_from_snapshot"),
        terms=_terms(evs) if evs is not None else [], coverage=coverage, reason=reason,
        served=ServedReference(**served) if served else None,
    )


def _posture(label, d):
    from src.dynasty_genius.ranking.contract import Posture

    return Posture(label=label, discount=d)


def test_value_is_the_discounted_sum_of_unconditional_terms() -> None:
    from src.dynasty_genius.ranking.assembler import compose_value

    rv = compose_value(_ts("p", "WR", [3.0, 2.0, 1.0, 0.0, 0.0, 0.0]), _posture("contend", 0.5), horizons=5)
    assert rv.value == pytest.approx(3.0 + 1.0 + 0.25)
    assert rv.horizons_used == 6
    assert rv.basis == "value_above_obtainable_replacement"
    assert rv.unit == "season_points_above_replacement"


def test_rebuild_posture_weights_every_season_equally() -> None:
    from src.dynasty_genius.ranking.assembler import compose_value

    rv = compose_value(_ts("p", "RB", [2.0, 2.0, 2.0, 2.0, 2.0, 2.0]), _posture("rebuild", 1.0), horizons=5)
    assert rv.value == pytest.approx(12.0)


def test_equal_terms_give_equal_value_at_every_position() -> None:
    """Common cross-position unit: position never enters the assembler."""
    from src.dynasty_genius.ranking.assembler import compose_value

    evs = [4.0, 3.5, 3.0, 2.0, 1.0, 0.5]
    values = {pos: compose_value(_ts("p", pos, evs), _posture("rebuild", 1.0), horizons=5).value
              for pos in ("QB", "RB", "WR", "TE")}
    assert len(set(values.values())) == 1


def test_a_delayed_rookie_breakout_is_worth_less_to_a_contender_than_to_a_rebuilder() -> None:
    """The rookie contributes nothing this season and next, then four seasons of 4.0; the
    veteran is front-loaded. Same undiscounted sum. Only the posture separates them, and it
    must separate them in the right direction."""
    from src.dynasty_genius.ranking.assembler import compose_value

    rookie = _ts("r", "WR", [0.0, 0.0, 4.0, 4.0, 4.0, 4.0])
    veteran = _ts("v", "WR", [5.0, 4.0, 3.0, 2.0, 1.0, 1.0])
    rebuild, contend = _posture("rebuild", 1.0), _posture("contend", 0.6)
    assert compose_value(rookie, rebuild, horizons=5).value == pytest.approx(16.0)
    assert compose_value(veteran, rebuild, horizons=5).value == pytest.approx(16.0)
    assert compose_value(rookie, contend, horizons=5).value < compose_value(veteran, contend, horizons=5).value
    assert compose_value(rookie, contend, horizons=5).value > 0.0


def test_a_player_with_no_estimate_keeps_his_identity_and_carries_a_reason() -> None:
    from src.dynasty_genius.ranking.assembler import assemble

    out = assemble([_ts("dell", "WR", coverage="none", reason="no 2025 feature row", full_name="Tank Dell"),
                    _ts("w", "WR", [1.0] * 6)], _posture("rebuild", 1.0), horizons=5)
    assert [v.player_id for v in out.values] == ["dell", "w"]
    blank = out.values[0]
    assert blank.value is None and blank.coverage == "none"
    assert blank.reason == "no 2025 feature row"
    assert blank.full_name == "Tank Dell"


def test_partial_coverage_yields_no_focal_value_but_stays_on_the_board() -> None:
    """A one-season number and a six-season number are not the same unit; a partial term set
    is shown with its reason rather than summed as if it were complete."""
    from src.dynasty_genius.ranking.assembler import compose_value

    rv = compose_value(_ts("p", "QB", [3.0], coverage="partial", reason="cell suppressed: n=10 < 12"),
                       _posture("rebuild", 1.0), horizons=5)
    assert rv.value is None
    assert rv.coverage == "partial"
    assert "suppressed" in rv.reason


def test_a_term_set_claiming_full_coverage_short_of_the_horizon_is_refused() -> None:
    from src.dynasty_genius.ranking.assembler import compose_value

    with pytest.raises(ValueError, match="p7.*h=0..5"):
        compose_value(_ts("p7", "TE", [1.0, 1.0, 1.0]), _posture("rebuild", 1.0), horizons=5)


def test_the_served_number_rides_alongside_untouched_and_is_never_the_value() -> None:
    from src.dynasty_genius.ranking.assembler import compose_value

    rv = compose_value(_ts("j", "RB", [2.0] * 6, served={"dynasty_value_score": 57.6, "dvs_engine": "B"}),
                       _posture("rebuild", 1.0), horizons=5)
    assert rv.served.dynasty_value_score == 57.6
    assert rv.value != 57.6
    assert rv.producer.estimate_class == "candidate"


def test_posture_is_required_never_defaulted() -> None:
    from src.dynasty_genius.ranking.assembler import assemble

    with pytest.raises(TypeError):
        assemble([_ts("p", "WR", [1.0] * 6)], horizons=5)  # type: ignore[call-arg]


def test_conditioning_events_used_are_recorded_on_the_result() -> None:
    from src.dynasty_genius.ranking.assembler import compose_value

    rv = compose_value(_ts("p", "WR", [1.0] * 6), _posture("rebuild", 1.0), horizons=5)
    assert rv.conditioning_events == ("fixture event",)


def test_ranked_order_puts_blanks_last_and_keeps_ties_stable() -> None:
    from src.dynasty_genius.ranking.assembler import assemble

    out = assemble([_ts("a", "WR", coverage="none", reason="x"),
                    _ts("b", "WR", [1.0] * 6), _ts("c", "WR", [2.0] * 6), _ts("d", "WR", [1.0] * 6)],
                   _posture("rebuild", 1.0), horizons=5)
    assert [v.player_id for v in out.ranked()] == ["c", "b", "d", "a"]
    assert out.counts == {"full": 3, "partial": 0, "none": 1}


def test_a_longer_term_set_is_summed_over_the_board_horizon_only() -> None:
    """Six seasons supplied, five-season board asked for: the sixth is not summed and the
    result says five horizons were used. Lets two producers with different reach be shown on
    one common horizon without either being refused."""
    from src.dynasty_genius.ranking.assembler import compose_value

    rv = compose_value(_ts("p", "WR", [1.0, 1.0, 1.0, 1.0, 1.0, 10.0]), _posture("rebuild", 1.0), horizons=4)
    assert rv.value == pytest.approx(5.0)
    assert rv.horizons_used == 5


def test_a_horizon_view_is_a_prefix_sum_of_the_same_terms_so_the_longer_view_never_falls_below_the_shorter() -> None:
    """Codex, round 3: the 2-year and 5-year numbers must come from ONE set of per-season
    terms (same reference, scoring, snapshot); the longer view sums more of the same
    non-negative terms, so value(H=4) >= value(H=1) and the first two terms are identical."""
    from datetime import date

    from src.dynasty_genius.ranking.assembler import compose_value
    from src.dynasty_genius.ranking.contract import (
        HorizonTerm,
        Posture,
        ProducerRef,
        ReplacementRef,
        TermSet,
        annual_target,
    )

    fd = date(2026, 9, 6)
    spec = annual_target(fd)
    terms = [HorizonTerm(h=h, season=2026 + h, ev_above_replacement=ev, spec=spec, expected_margin=ev if ev > 0 else -5.0,
                         action="retain" if ev > 0 else "replace", conditioning_event="season-long replace/retain counterfactual")
             for h, ev in enumerate((40.0, 30.0, 0.0, 20.0, 10.0))]
    ts = TermSet(player_id="p", sleeper_id="1", position="WR", coverage="full", forecast_date=fd,
                 producer=ProducerRef(name="basic", version="v", estimate_class="candidate", evidence_verified=True),
                 replacement_ref=ReplacementRef(position="WR", policy="best_forecast_available", rate_ppg=100.0, snapshot_id="s",
                                                horizon_assumption="same_player_from_snapshot_per_season"),
                 terms=terms, served=None)
    posture = Posture(label="rebuild", discount=1.0)
    two = compose_value(ts, posture, horizons=1, board=spec)
    five = compose_value(ts, posture, horizons=4, board=spec)
    assert two.value == 70.0 and five.value == 100.0 and five.value >= two.value
    assert [t.ev_above_replacement for t in ts.terms][:2] == [40.0, 30.0]
    # a value is never negative, so no prefix can exceed a longer prefix
    for h in range(5):
        assert compose_value(ts, posture, horizons=h, board=spec).value == sum(t.ev_above_replacement for t in terms[: h + 1])
