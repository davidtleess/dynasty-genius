"""DG-178 round 1 — comparability is TYPED, and it is not the same thing as coverage.

A string describing an event does not make two quantities comparable. Every term carries a
TargetSpec (scope, scoring, exposure, event, clock, quantity, cutoff); the board declares
the spec it requires; the assembler classifies each player's readiness from the typed
fields alone. Numerical coverage (are there numbers for h = 0..H) and scientific
comparability (are those numbers the same kind of thing) are reported separately.
"""
from __future__ import annotations

from datetime import date

import pytest

FD = date(2026, 9, 6)


def _annual():
    from src.dynasty_genius.ranking.contract import annual_target

    return annual_target(FD)


def _legacy():
    from src.dynasty_genius.ranking.contract import TargetSpec

    return TargetSpec(scope="ALL_GAMES", scoring="served_all_games_ppr", exposure="all_games",
                      event="two_season_window_qualifying", clock="two_season_window",
                      quantity="ppg_rate", labels_through=2025)


def _terms(evs, spec):
    from src.dynasty_genius.ranking.contract import HorizonTerm, season_for_horizon

    return [HorizonTerm(h=h, season=season_for_horizon(FD, h), ev_above_replacement=ev,
                        conditioning_event="x", spec=spec) for h, ev in enumerate(evs)]


def _ts(pid, evs, spec, coverage="full", reason=None):
    from src.dynasty_genius.ranking.contract import ProducerRef, ReplacementRef, TermSet

    return TermSet(player_id=pid, position="WR", forecast_date=FD, full_name=pid,
                   producer=ProducerRef(name="fx", version="0", estimate_class="candidate", evidence_verified=True),
                   replacement_ref=ReplacementRef(position="WR", policy="fx", rate_ppg=9.0, snapshot_id="s",
                                                  horizon_assumption="held_constant_from_snapshot"),
                   terms=_terms(evs, spec) if evs is not None else [], coverage=coverage, reason=reason)


def _posture():
    from src.dynasty_genius.ranking.contract import Posture

    return Posture(label="rebuild", discount=1.0)


def test_target_spec_fields_are_closed_sets_and_name_their_own_mismatches() -> None:
    from src.dynasty_genius.ranking.contract import TargetSpec

    a, b = _annual(), _legacy()
    assert a.mismatches(a) == ()
    assert set(a.mismatches(b)) == {"scope", "scoring", "exposure", "event", "clock", "quantity"}
    with pytest.raises(Exception):
        TargetSpec(scope="PRE", scoring="served_all_games_ppr", exposure="all_games",
                   event="appearance", clock="per_season", quantity="season_points", labels_through=2025)


def test_the_annual_target_is_the_agreed_contract() -> None:
    """Agreed with lanes 24974 and 23481 on 2026-09-06: REG scope, nflverse weekly PPR,
    stat-row exposure, appearance event, per-season clock, season points."""
    a = _annual()
    assert (a.scope, a.scoring, a.exposure, a.event, a.clock, a.quantity) == (
        "REG", "PPR_nflverse_weekly", "stat_row_games", "appearance", "per_season", "season_points")
    assert a.labels_through == 2025


def test_a_terms_unit_is_derived_from_its_typed_quantity_not_declared_in_prose() -> None:
    from src.dynasty_genius.ranking.contract import UNIT

    assert _terms([1.0], _annual())[0].unit == UNIT == "season_points_above_replacement"
    assert _terms([1.0], _legacy())[0].unit == "ppg_above_replacement"


def test_a_term_without_a_typed_spec_is_refused() -> None:
    from src.dynasty_genius.ranking.contract import HorizonTerm

    with pytest.raises(Exception):
        HorizonTerm(h=0, season=2026, ev_above_replacement=1.0, conditioning_event="prose only")


def test_readiness_is_classified_from_typed_fields_not_coverage() -> None:
    from src.dynasty_genius.ranking.assembler import assemble

    out = assemble([
        _ts("comp", [1.0] * 6, _annual()),
        _ts("legacy", [1.0] * 6, _legacy()),
        _ts("part", [1.0], _annual(), coverage="partial", reason="one season"),
        _ts("none", None, _annual(), coverage="none", reason="no forecast"),
    ], _posture(), horizons=5, board=_annual())
    by = {v.player_id: v for v in out.values}
    assert by["comp"].readiness == "comparable" and by["comp"].value == pytest.approx(6.0)
    assert by["legacy"].readiness == "research_only" and by["legacy"].value == pytest.approx(6.0)
    assert by["part"].readiness == "incomplete" and by["part"].value is None
    assert by["none"].readiness == "none" and by["none"].value is None
    assert out.readiness_counts == {"comparable": 1, "unverified": 0, "research_only": 1, "incomplete": 1, "none": 1}


def test_the_comparable_only_path_fails_incompatible_inputs_with_a_reason_and_identity() -> None:
    from src.dynasty_genius.ranking.assembler import assemble

    out = assemble([_ts("legacy", [1.0] * 6, _legacy(), ), _ts("comp", [2.0] * 6, _annual())],
                   _posture(), horizons=5, board=_annual(), comparable_only=True)
    legacy = next(v for v in out.values if v.player_id == "legacy")
    assert legacy.value is None
    assert legacy.readiness == "research_only"
    assert legacy.full_name == "legacy"
    assert "not comparable" in legacy.reason and "scope" in legacy.reason and "clock" in legacy.reason
    assert [v.player_id for v in out.ranked(comparable_only=True)] == ["comp"]


def test_a_board_on_another_label_window_makes_every_term_research_only() -> None:
    """Comparability is typed on which labels were available, not on the calendar day."""
    from src.dynasty_genius.ranking.assembler import assemble
    from src.dynasty_genius.ranking.contract import annual_target

    out = assemble([_ts("comp", [1.0] * 6, _annual())], _posture(), horizons=5,
                   board=annual_target(date(2027, 9, 6)))
    assert out.values[0].readiness == "research_only"
    assert "labels_through" in out.values[0].comparability_note


def test_without_a_board_readiness_is_unknown_and_nothing_is_called_comparable() -> None:
    from src.dynasty_genius.ranking.assembler import assemble

    out = assemble([_ts("comp", [1.0] * 6, _annual())], _posture(), horizons=5)
    assert out.values[0].readiness == "unclassified"


def test_legacy_adapters_type_their_terms_as_research_not_annual() -> None:
    """The served composition and the rookie level composition are research approximations
    and must never come out 'comparable' against the annual target."""
    from pathlib import Path

    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        RookieCandidate,
        build_rookie_term_set,
    )
    from src.dynasty_genius.ranking.adapters.veteran_served import build_term_set
    from src.dynasty_genius.ranking.assembler import assemble
    from src.dynasty_genius.ranking.contract import ReplacementRef
    from src.dynasty_genius.ranking.served_rows import ServedRow
    from src.dynasty_genius.ranking.survival_cells import RetentionCells

    fx = Path(__file__).parent / "fixtures"
    cells = RetentionCells.load(fx / "retention_cells_fixture.json")
    cap = "2026-09-06T13:00:53+00:00"
    vet = ServedRow(player_id="v", sleeper_id="v", full_name="Vet", position="WR", age=24,
                    dynasty_value_score=9.0 / 20.1 * 100, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                    projection_2y=18.0, captured_at=cap)
    rk = ServedRow(player_id="r", sleeper_id="r", full_name="Rk", position="QB", age=22,
                   dynasty_value_score=70.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="A",
                   projection_2y=None, captured_at=cap, nfl_draft_pick=1, draft_class=2026)
    ref_wr = ReplacementRef(position="WR", policy="p", rate_ppg=9.0, conditional_rate_ppg=11.6, snapshot_id="s",
                            horizon_assumption="held_constant_from_snapshot")
    ref_qb = ReplacementRef(position="QB", policy="p", rate_ppg=9.4, conditional_rate_ppg=10.7, snapshot_id="s",
                            horizon_assumption="held_constant_from_snapshot")
    cand = RookieCandidate.load(fx / "rookie_candidate_v2_fixture.csv", fx / "rookie_candidate_v2_manifest.json")
    sets = [build_term_set(vet, ref_wr, cells, forecast_date=FD),
            build_rookie_term_set(rk, ref_qb, cand, draft_pick=1, forecast_date=FD, horizons=5)]
    assert all(t.coverage == "full" for t in sets)
    out = assemble(sets, _posture(), horizons=5, board=_annual())
    assert {v.readiness for v in out.values} == {"research_only"}


def test_the_fixture_adapter_can_produce_a_comparable_term_set_for_end_to_end_tests() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_fixture import (
        build_fixture_term_set,
    )
    from src.dynasty_genius.ranking.assembler import assemble
    from src.dynasty_genius.ranking.contract import ReplacementRef
    from src.dynasty_genius.ranking.served_rows import ServedRow

    row = ServedRow(player_id="f", sleeper_id="f", full_name="Fixture", position="QB", age=22,
                    dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                    projection_2y=None, captured_at=None)
    ref = ReplacementRef(position="QB", policy="p", rate_ppg=9.4, snapshot_id="s",
                         horizon_assumption="held_constant_from_snapshot")
    ts = build_fixture_term_set(row, ref, [(0.5, 14.0)] * 6, forecast_date=FD, label="x", spec=_annual(),
                                evidence_verified=True)
    out = assemble([ts], _posture(), horizons=5, board=_annual())
    assert out.values[0].readiness == "comparable"
    assert out.values[0].producer.estimate_class == "fixture"
