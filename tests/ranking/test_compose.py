"""DG-178 — routing one served row to the producer that can speak for it.

An Engine A row is a prospect: no conditional projection, so the veteran adapter has
nothing to say and the rookie candidate (when supplied) does. Every other row goes through
the veteran adapter. With no rookie candidate supplied, a prospect is a stated blank —
never a fixture, never a filled-in number.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

FD = date(2026, 9, 6)
CELLS = Path(__file__).parent / "fixtures" / "retention_cells_fixture.json"
CSV = Path(__file__).parent / "fixtures" / "rookie_candidate_fixture.csv"
MANIFEST = Path(__file__).parent / "fixtures" / "rookie_candidate_manifest.json"


def test_the_served_row_carries_the_draft_pick_and_class_from_the_artifact() -> None:
    from src.dynasty_genius.ranking.served_rows import ServedRow

    r = ServedRow.from_artifact_row({
        "dg_player_id": "dg1", "sleeper_player_id": "13269", "nfl_draft_pick": 1, "nfl_draft_round": 1,
        "draft_class": 2026, "dvs_engine": "A", "projection_2y": None,
        "player": {"full_name": "Fernando Mendoza", "position": "QB", "age": 22},
        "valuation": {"dynasty_value_score": 70.73, "dvs_p90_ref": 20.1, "dvs_clamped": False},
    }, captured_at="2026-09-06T13:00:53+00:00")
    assert r.nfl_draft_pick == 1 and r.draft_class == 2026


def _rows():
    from src.dynasty_genius.ranking.served_rows import ServedRow

    cap = "2026-09-06T13:00:53+00:00"
    return [
        ServedRow(player_id="a", sleeper_id="13269", full_name="Fernando Mendoza", position="QB", age=22,
                  dynasty_value_score=70.73, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="A",
                  projection_2y=None, captured_at=cap, nfl_draft_pick=1, draft_class=2026),
        ServedRow(player_id="b", sleeper_id="1", full_name="Vet QB", position="QB", age=25,
                  dynasty_value_score=50.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                  projection_2y=12.0, captured_at=cap),
    ]


def _refs():
    from src.dynasty_genius.ranking.contract import ReplacementRef

    return {"QB": ReplacementRef(position="QB", policy="best_available_served_rate", rate_ppg=9.4,
                                 conditional_rate_ppg=10.7, snapshot_id="s",
                                 horizon_assumption="held_constant_from_snapshot")}


def test_engine_a_rows_go_to_the_rookie_candidate_and_the_rest_to_the_veteran_adapter() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_candidate import RookieCandidate
    from src.dynasty_genius.ranking.compose import compose_term_sets
    from src.dynasty_genius.ranking.survival_cells import RetentionCells

    sets = compose_term_sets(_rows(), _refs(), RetentionCells.load(CELLS),
                             rookie_candidate=RookieCandidate.load(CSV, MANIFEST), forecast_date=FD)
    by = {t.player_id: t for t in sets}
    assert by["a"].producer.name == "dg165_rookie_capital_v1"
    assert by["a"].coverage == "partial"  # probabilities present, level not supplied
    assert by["b"].producer.name == "veteran_served_plus_retention_cells"


def test_without_a_rookie_candidate_a_prospect_is_a_stated_blank() -> None:
    from src.dynasty_genius.ranking.compose import compose_term_sets
    from src.dynasty_genius.ranking.survival_cells import RetentionCells

    sets = compose_term_sets(_rows(), _refs(), RetentionCells.load(CELLS), rookie_candidate=None, forecast_date=FD)
    by = {t.player_id: t for t in sets}
    assert by["a"].coverage == "none" and "rookie lane owes" in by["a"].reason
    assert by["a"].producer.estimate_class == "candidate"


def test_rows_out_equal_rows_in_including_positions_with_no_replacement() -> None:
    """A position with no bar cannot be composed, but the row must still come back with a
    reason rather than vanish."""
    from src.dynasty_genius.ranking.compose import compose_term_sets
    from src.dynasty_genius.ranking.served_rows import ServedRow
    from src.dynasty_genius.ranking.survival_cells import RetentionCells

    rows = _rows() + [ServedRow(player_id="c", sleeper_id="2", full_name="Some TE", position="TE", age=25,
                                dynasty_value_score=30.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                                projection_2y=7.0, captured_at="x")]
    sets = compose_term_sets(rows, _refs(), RetentionCells.load(CELLS), rookie_candidate=None, forecast_date=FD)
    assert len(sets) == 3
    te = next(t for t in sets if t.player_id == "c")
    assert te.coverage == "none" and "no replacement" in te.reason


def test_with_an_annual_candidate_every_row_is_composed_on_the_annual_target() -> None:
    """When a producer's annual file is supplied, the comparable path uses it for every row
    it covers; rows it does not cover are stated absences. The legacy research adapters are
    not consulted on this path."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        AnnualCandidate,
        annual_replacement,
    )
    from src.dynasty_genius.ranking.assembler import assemble
    from src.dynasty_genius.ranking.compose import compose_annual_term_sets
    from src.dynasty_genius.ranking.contract import Posture, annual_target
    from src.dynasty_genius.ranking.served_rows import ServedRow

    fx = Path(__file__).parent / "fixtures"
    cand = AnnualCandidate.load(fx / "annual_candidate_fixture.csv", fx / "annual_candidate_manifest.json",
                                results_path=fx / "annual_candidate_grading.json")
    rostered = {"101", "102", "401"}
    refs = annual_replacement(cand, rostered_ids=rostered, snapshot_id="s")
    cap = "x"
    rows = [
        ServedRow(player_id="v1", sleeper_id="101", full_name="Vet One", position="WR", age=25,
                  dynasty_value_score=50.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                  projection_2y=12.0, captured_at=cap),
        ServedRow(player_id="q1", sleeper_id="401", full_name="Some QB", position="QB", age=25,
                  dynasty_value_score=60.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                  projection_2y=15.0, captured_at=cap),
        ServedRow(player_id="nobody", sleeper_id="999", full_name="Nobody", position="TE", age=25,
                  dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                  projection_2y=None, captured_at=cap),
    ]
    sets = compose_annual_term_sets(rows, refs, cand, forecast_date=FD)
    assert [t.player_id for t in sets] == ["v1", "q1", "nobody"]
    out = assemble(sets, Posture(label="rebuild", discount=1.0), horizons=cand.seasons - 1,
                   board=annual_target(FD), comparable_only=True)
    by = {v.player_id: v for v in out.values}
    # v1 against reference fa1: (180 - 98) + (144 - 72)
    assert by["v1"].readiness == "comparable" and by["v1"].value == pytest.approx(82.0 + 72.0)
    # q1 against reference fq: (285 - 136) + (261 - 105)
    assert by["q1"].readiness == "comparable" and by["q1"].value == pytest.approx(149.0 + 156.0)
    assert by["nobody"].readiness == "none" and "no replacement" in by["nobody"].reason
    assert out.readiness_counts["comparable"] == 2


def test_a_gsis_shaped_dg_player_id_is_recognised_as_the_gsis_id() -> None:
    """The artifact's dg_player_id is the gsis id ('00-0038564') while identity_ids.gsis_id
    is null on every row; a producer keyed by gsis must still join."""
    from src.dynasty_genius.ranking.served_rows import ServedRow

    r = ServedRow.from_artifact_row({
        "dg_player_id": "00-0038564", "sleeper_player_id": "10210", "dvs_engine": "B", "projection_2y": 7.0,
        "identity_ids": {"gsis_id": None, "sleeper_id": "10210"},
        "player": {"full_name": "Cameron Latu", "position": "TE", "age": 26},
        "valuation": {"dynasty_value_score": 30.0, "dvs_p90_ref": 20.1, "dvs_clamped": False},
    }, captured_at="x")
    assert r.gsis_id == "00-0038564"


def test_a_row_no_annual_producer_covers_says_so_not_no_replacement_bar() -> None:
    """Tank Dell has no 2025 feature row and is not a rookie: no producer forecasts him. The
    reason must say that, not 'no replacement bar', which is a different absence."""
    from src.dynasty_genius.ranking.compose import absent_annual_term_sets
    from src.dynasty_genius.ranking.served_rows import ServedRow

    row = ServedRow(player_id="dell", sleeper_id="9484", full_name="Tank Dell", position="WR", age=26,
                    dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                    projection_2y=None, captured_at="x")
    sets = absent_annual_term_sets([row], producers=["dg177:arm", "dg165_v3"], forecast_date=FD)
    assert sets[0].coverage == "none"
    assert "not forecast by any annual producer" in sets[0].reason and "dg177:arm" in sets[0].reason


def test_an_identity_bridge_fills_a_missing_gsis_so_a_producer_row_can_be_joined() -> None:
    """Tank Dell's artifact row carries no gsis (no 2025 feature row), while the five-year
    producer forecasts him under 00-0038977 and its reconciliation file maps his Sleeper id
    to that gsis. The bridge fills the gap; rows that already carry a gsis are untouched."""
    from src.dynasty_genius.ranking.served_rows import ServedRow, apply_identity_bridge

    rows = [ServedRow(player_id="9502", sleeper_id="9502", full_name="Tank Dell", position="WR", age=26,
                      dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                      projection_2y=None, captured_at="x"),
            ServedRow(player_id="00-0038996", sleeper_id="9484", full_name="Tucker Kraft", position="TE", age=25,
                      dynasty_value_score=46.9, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                      projection_2y=10.2, captured_at="x", gsis_id="00-0038996")]
    out = apply_identity_bridge(rows, {"9502": "00-0038977", "9484": "WRONG"})
    by = {r.sleeper_id: r for r in out}
    assert by["9502"].gsis_id == "00-0038977"
    assert by["9484"].gsis_id == "00-0038996"


def test_an_absent_row_carries_the_producers_stated_reason_never_an_invented_one() -> None:
    """Travis Hunter is WR-eligible in David's league and unforecast because the veteran
    producer excludes his two-position (DB-modal) history. The absence must say THAT, not
    'a veteran without a 2025 feature row or an undrafted rookie'."""
    from datetime import date

    from src.dynasty_genius.ranking.compose import absent_annual_term_sets
    from src.dynasty_genius.ranking.served_rows import ServedRow

    hunter = ServedRow(player_id="dg-hunter", sleeper_id="12530", full_name="Travis Hunter", position="WR", age=23,
                       dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine="A",
                       projection_2y=None, captured_at="x", fantasy_positions=("DB", "WR"),
                       placement_source="sleeper_fantasy_positions", nfl_status="Active")
    other = ServedRow(player_id="dg-x", sleeper_id="1", full_name="No Reason Guy", position="RB", age=30,
                      dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine="A",
                      projection_2y=None, captured_at="x")
    reasons = {"12530": "veteran_basic: position_outside_modelled_set (source position CB)"}
    sets = absent_annual_term_sets([hunter, other], ["vet", "rk"], forecast_date=date(2026, 9, 6), stated_reasons=reasons)
    assert sets[0].coverage == "none" and sets[0].reason == (
        "not forecast by any annual producer (vet, rk); the producer's stated reason: "
        "veteran_basic: position_outside_modelled_set (source position CB)")
    assert "2025 feature row" not in sets[0].reason
    # no stated reason: the generic sentence stays, marked as such
    assert sets[1].reason.startswith("not forecast by any annual producer (vet, rk); no producer stated a reason")
