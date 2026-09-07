"""DG-178 round 1 — the reader for the AGREED annual target (both producers, one shape).

Per player and NFL season j: p_appear, conditional points and games, and the unconditional
pair. The adapter types the file from its manifest, refuses a file whose typed fields are
not the annual target's, checks the unconditional pair against p x conditional (a check
that can fail when a file is edited by hand), and builds C_ij = max(0, E[points] - R_j x
E[games]) with R_j from the same producer's unrostered rows.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

FD = date(2026, 9, 6)
CSV = Path(__file__).parent / "fixtures" / "annual_candidate_fixture.csv"
MANIFEST = Path(__file__).parent / "fixtures" / "annual_candidate_manifest.json"


def _load(csv=CSV, manifest=MANIFEST):
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    return AnnualCandidate.load(csv, manifest)


FIXTURE_GRADING = Path(__file__).parent / "fixtures" / "annual_candidate_grading.json"


def _load_verified():
    """The fixture producer with affirmative identity: scoring arm, declared hash, graded arm."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    return AnnualCandidate.load(CSV, MANIFEST, results_path=FIXTURE_GRADING)


def test_the_file_is_typed_from_its_manifest_as_the_annual_target() -> None:
    from src.dynasty_genius.ranking.contract import annual_target

    c = _load()
    assert c.spec == annual_target(FD)
    assert c.spec.labels_through == 2025
    assert c.seasons == 2 and c.model_version == "annual_fixture_v0"
    assert len(c.csv_sha256) == 64


def test_a_manifest_with_another_scope_or_exposure_is_refused(tmp_path) -> None:
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    m = json.loads(MANIFEST.read_text())
    m["scoring_scope"] = "ALL_GAMES"
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps(m))
    with pytest.raises(ValueError, match="annual target"):
        AnnualCandidate.load(CSV, bad)


def test_the_unconditional_pair_must_equal_p_times_the_conditional_pair(tmp_path) -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    text = CSV.read_text().replace("0.9,200.0,16.0,180.0,14.4", "0.9,200.0,16.0,150.0,14.4")
    bad = tmp_path / "bad.csv"
    bad.write_text(text)
    with pytest.raises(ValueError, match="p_appear x conditional"):
        AnnualCandidate.load(bad, MANIFEST)


def test_replacement_is_the_best_available_by_expected_points_and_his_season_points_are_the_reference() -> None:
    """David's rule on the annual quantities: the best player nobody owns, ranked by
    unconditional expected season points (availability inside); the reference quantity is HIS
    expected season points in the same window. fa1 (98.0) beats fa2 (60.0); rostered v1 ignored."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import annual_replacement

    refs = annual_replacement(_load(), rostered_ids={"101", "102", "401"}, snapshot_id="s")
    wr = refs["WR"]
    assert wr[0].player_id == "fa1"
    assert wr[0].rate_ppg == pytest.approx(98.0) and wr[1].rate_ppg == pytest.approx(72.0)
    assert wr[0].rate_quantity == "expected_season_points_same_window"
    assert refs["QB"][0].player_id == "fq"


def test_terms_are_comparable_and_follow_the_estimand() -> None:
    """v1: margin_1 = 180 - 98 = 82, margin_2 = 144 - 72 = 72; both retained; V = 154."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.assembler import compose_value
    from src.dynasty_genius.ranking.contract import Posture, annual_target
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load_verified()
    refs = annual_replacement(c, rostered_ids={"101", "102", "401"}, snapshot_id="s")
    row = ServedRow(player_id="v1", sleeper_id="101", full_name="Vet One", position="WR", age=25,
                    dynasty_value_score=50.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                    projection_2y=12.0, captured_at="x")
    ts = build_annual_term_set(row, refs["WR"], c, forecast_date=FD)
    assert ts.coverage == "full" and [t.h for t in ts.terms] == [0, 1]
    assert ts.terms[0].ev_above_replacement == pytest.approx(82.0)
    assert ts.terms[1].ev_above_replacement == pytest.approx(72.0)
    assert ts.terms[0].unit == "season_points_above_replacement"
    rv = compose_value(ts, Posture(label="rebuild", discount=1.0), horizons=1, board=annual_target(FD))
    assert rv.readiness == "comparable" and rv.value == pytest.approx(154.0)
    assert ts.served.dynasty_value_score == 50.0


def test_a_player_whose_expected_points_trail_the_reference_is_replaced_and_worth_zero() -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load()
    refs = annual_replacement(c, rostered_ids={"101", "102", "401"}, snapshot_id="s")
    row = ServedRow(player_id="v2", sleeper_id="102", full_name="Vet Two", position="WR", age=25,
                    dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                    projection_2y=None, captured_at="x")
    ts = build_annual_term_set(row, refs["WR"], c, forecast_date=FD)
    assert [t.ev_above_replacement for t in ts.terms] == [0.0, 0.0]
    assert [t.action for t in ts.terms] == ["replace", "replace"]
    assert ts.terms[0].expected_margin == pytest.approx(60.0 - 98.0)
    assert ts.coverage == "full"


def test_the_zero_test_is_expected_season_points_at_or_below_the_references() -> None:
    """CANONICAL.md's zero test, exactly: a player is worth 0 when his expected season points
    do not exceed the reference player's in the same window."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import annual_replacement

    refs = annual_replacement(_load(), rostered_ids={"101", "102", "401"}, snapshot_id="s")
    ref_points = refs["WR"][0].rate_ppg
    assert max(0.0, 98.0 - ref_points) == pytest.approx(0.0)
    assert max(0.0, 98.5 - ref_points) > 0.0


def test_an_unresolved_identity_or_a_missing_player_is_a_stated_absence() -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load()
    refs = annual_replacement(c, rostered_ids=set(), snapshot_id="s")
    unresolved = ServedRow(player_id="u1", sleeper_id="301", full_name="Unresolved Guy", position="WR", age=25,
                           dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                           projection_2y=None, captured_at="x")
    ts = build_annual_term_set(unresolved, refs["WR"], c, forecast_date=FD)
    assert ts.coverage == "none" and "unresolved" in ts.reason
    missing = ServedRow(player_id="zz", sleeper_id="999", full_name="Nobody", position="WR", age=25,
                        dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                        projection_2y=None, captured_at="x")
    ts2 = build_annual_term_set(missing, refs["WR"], c, forecast_date=FD)
    assert ts2.coverage == "none" and "no annual forecast" in ts2.reason


def test_a_file_for_another_forecast_year_is_refused() -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load()
    refs = annual_replacement(c, rostered_ids=set(), snapshot_id="s")
    row = ServedRow(player_id="v1", sleeper_id="101", full_name="Vet One", position="WR", age=25,
                    dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                    projection_2y=None, captured_at="x")
    with pytest.raises(ValueError, match="vintage"):
        build_annual_term_set(row, refs["WR"], c, forecast_date=date(2027, 9, 6))


def test_a_horizon_beyond_the_files_reach_is_partial_not_padded() -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.assembler import compose_value
    from src.dynasty_genius.ranking.contract import Posture, annual_target
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load()
    refs = annual_replacement(c, rostered_ids=set(), snapshot_id="s")
    row = ServedRow(player_id="v1", sleeper_id="101", full_name="Vet One", position="WR", age=25,
                    dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                    projection_2y=None, captured_at="x")
    ts = build_annual_term_set(row, refs["WR"], c, forecast_date=FD, horizons=5)
    assert ts.coverage == "partial" and "reach 2" in ts.reason
    rv = compose_value(ts, Posture(label="rebuild", discount=1.0), horizons=5, board=annual_target(FD))
    assert rv.readiness == "incomplete" and rv.value is None


V3_CSV = Path(__file__).parent / "fixtures" / "annual_rookie_v3_fixture.csv"
V3_MANIFEST = Path(__file__).parent / "fixtures" / "annual_rookie_v3_manifest.json"


def test_the_rookie_lanes_nested_manifest_shape_types_as_the_annual_target() -> None:
    """Lane 24974's v3 manifest nests cutoff under forecast_date, scope and exposure under
    units, and the event under definitions, in prose. The loader maps that prose onto the
    typed literals with a closed mapping and fails on anything it does not recognise."""
    from src.dynasty_genius.ranking.contract import annual_target

    c = _load(V3_CSV, V3_MANIFEST)
    assert c.spec == annual_target(FD)
    assert c.forecast_year == 2026 and c.seasons == 2
    assert c.model_version == "dg165_rookie_capital_v3"


def test_unrecognised_prose_for_a_typed_field_is_refused_not_guessed(tmp_path) -> None:
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    m = json.loads(V3_MANIFEST.read_text())
    m["units"]["exposure_definition"] = "snaps played"
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps(m))
    with pytest.raises(ValueError, match="exposure"):
        AnnualCandidate.load(V3_CSV, bad)


def test_rookie_rows_join_on_position_draft_season_and_pick_when_there_is_no_sleeper_id() -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load(V3_CSV, V3_MANIFEST)
    assert c.get(position="QB", draft_season=2026, pick=1).name == "Fernando Mendoza"
    refs = annual_replacement(c, rostered_ids=set(), snapshot_id="s", positions=["QB"])
    row = ServedRow(player_id="dg-mendoza", sleeper_id="13269", full_name="Fernando Mendoza", position="QB", age=22,
                    dynasty_value_score=70.73, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="A",
                    projection_2y=None, captured_at="x", nfl_draft_pick=1, draft_class=2026)
    ts = build_annual_term_set(row, refs["QB"], c, forecast_date=FD)
    assert ts.coverage == "full"
    # Mendoza is the only QB and unrostered here, so he is his own reference: worth exactly 0
    assert ts.terms[0].ev_above_replacement == 0.0 and ts.terms[0].expected_margin == pytest.approx(0.0)


def test_a_negated_phrase_in_a_denominator_note_cannot_type_the_scoring(tmp_path) -> None:
    """Lane 24974's ppg_denominator note reads '... NOT the served all-games denominator'.
    A substring match on that prose typed the file as served all-games scoring. Scoring is
    read only from fields that state scoring, with positive identifiers."""
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    m = json.loads(V3_MANIFEST.read_text())
    m["units"].pop("scoring")
    m["units"]["scoring_scope"] = "regular season only; PPR as in nflverse weekly player stats"
    m["units"]["ppg_denominator"] = "REG-season PPR points / stat-row games — NOT the served all-games denominator"
    ok = tmp_path / "m.json"
    ok.write_text(json.dumps(m))
    c = AnnualCandidate.load(V3_CSV, ok)
    assert c.spec.scoring == "PPR_nflverse_weekly"


def test_comparability_is_typed_on_the_label_window_not_the_calendar_day(tmp_path) -> None:
    """A producer whose cutoff day is 2026-09-01 with labels through 2025 has the same
    information as a 2026-09-06 board; a producer with labels through 2024 does not."""
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate
    from src.dynasty_genius.ranking.contract import annual_target

    m = json.loads(V3_MANIFEST.read_text())
    m["forecast_date"]["forecast_cutoff"] = "2026-09-01 (pre-season 2026, after the NFL draft)"
    m["forecast_date"]["label_window"] = "labels through NFL season 2025; NFL season j = 1 is the rookie season = 2026"
    same = tmp_path / "same.json"
    same.write_text(json.dumps(m))
    c = AnnualCandidate.load(V3_CSV, same)
    assert c.spec.labels_through == 2025
    assert c.spec == annual_target(FD)
    m["forecast_date"]["label_window"] = "labels through NFL season 2024"
    stale = tmp_path / "stale.json"
    stale.write_text(json.dumps(m))
    with pytest.raises(ValueError, match="labels_through"):
        AnnualCandidate.load(V3_CSV, stale)


def test_interval_columns_beside_the_season_columns_do_not_break_the_season_index() -> None:
    """The real v3 file carries p_appear_year1_lo90 / _hi90 beside p_appear_year1; only the
    exact season columns define the seasons."""
    c = _load(V3_CSV, V3_MANIFEST)
    assert c.seasons == 2
    assert c.get(position="QB", draft_season=2026, pick=1).p_appear == (0.975, 0.98)


def _served(pid, sid, pos, name, pick=None, cls=None, dvs=40.0, proj=8.0):
    from src.dynasty_genius.ranking.served_rows import ServedRow

    return ServedRow(player_id=pid, sleeper_id=sid, full_name=name, position=pos, age=23,
                     dynasty_value_score=dvs, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="A" if pick else "B",
                     projection_2y=None if pick else proj, captured_at="x", nfl_draft_pick=pick, draft_class=cls)


def test_the_bar_resolves_producer_rows_to_sleeper_ids_before_deciding_who_is_unrostered() -> None:
    """The rookie file has no Sleeper id. Without resolving through the artifact, every rookie
    read as unrostered and Mendoza (on David's roster) became his own bar. The pool must be
    decided on the artifact's Sleeper id, found by the pick join."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import annual_replacement

    c = _load(V3_CSV, V3_MANIFEST)
    served = [_served("dg-mendoza", "13269", "QB", "Fernando Mendoza", pick=1, cls=2026),
              _served("dg-sadiq", "13330", "TE", "Kenyon Sadiq", pick=16, cls=2026)]
    refs = annual_replacement([c], rostered_ids={"13269"}, snapshot_id="s", positions=["QB", "TE"], served_rows=served)
    assert refs["TE"][0].player_name == "Kenyon Sadiq"
    assert refs["TE"][0].pool_complete is True
    assert "QB" not in refs  # the only QB in the producers' files is rostered; no bar can be set


def test_a_bar_from_producers_that_do_not_cover_the_scored_unrostered_players_is_incomplete() -> None:
    """A rookie-only file cannot supply the league's next available QB: the artifact holds a
    scored, unrostered veteran QB the producers never forecast. The bar is flagged, and every
    term built on it is a stated partial rather than a comparable value."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )

    c = _load(V3_CSV, V3_MANIFEST)
    served = [_served("dg-mendoza", "13269", "QB", "Fernando Mendoza", pick=1, cls=2026),
              _served("dg-rattler", "9000", "QB", "Spencer Rattler", dvs=46.8, proj=10.7)]
    refs = annual_replacement([c], rostered_ids=set(), snapshot_id="s", positions=["QB"], served_rows=served)
    qb = refs["QB"][0]
    assert qb.pool_complete is False
    assert "Spencer Rattler" in qb.pool_note or "1 scored unrostered" in qb.pool_note
    ts = build_annual_term_set(served[0], refs["QB"], c, forecast_date=FD)
    assert ts.coverage == "partial"
    assert "replacement pool incomplete" in ts.reason


def test_the_bar_is_computed_over_the_union_of_producers() -> None:
    """Two producers (a veteran file and a rookie file) supply one pool per position."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import annual_replacement

    vet = _load(CSV, MANIFEST)          # WR fa1 (98.0 expected points), fa2; QB fq
    rk = _load(V3_CSV, V3_MANIFEST)     # QB Mendoza, TE Sadiq
    served = [_served("v1", "101", "WR", "Vet One"), _served("v2", "102", "WR", "Vet Two"),
              _served("fa1", "201", "WR", "Free Agent"), _served("fa2", "202", "WR", "Free Agent Two"),
              _served("q1", "401", "QB", "Some QB"), _served("fq", "402", "QB", "FA QB", dvs=30.0, proj=9.0),
              _served("dg-mendoza", "13269", "QB", "Fernando Mendoza", pick=1, cls=2026),
              _served("u1", "301", "WR", "Unresolved Guy", dvs=None, proj=None)]
    refs = annual_replacement([vet, rk], rostered_ids={"101", "102", "401"}, snapshot_id="s",
                              positions=["QB", "WR"], served_rows=served)
    # QB pool = FA QB (136 expected) and Mendoza (214.5 expected): Mendoza is the best available
    assert refs["QB"][0].player_name == "Fernando Mendoza" and refs["QB"][0].pool_complete is True
    assert refs["WR"][0].player_name == "Free Agent" and refs["WR"][0].pool_complete is True


DG177_CSV = Path(__file__).parent / "fixtures" / "annual_veteran_dg177_fixture.csv"
DG177_MANIFEST = Path(__file__).parent / "fixtures" / "annual_veteran_dg177_manifest.json"


def test_the_veteran_lanes_manifest_shape_types_as_the_annual_target() -> None:
    """Lane 23481 nests scope and scoring in one dict, writes the event as 'appeared:
    >= 1 stat-row game', gives the label window as {year1: 1, year2: 2} and the vintage as
    forecast_cutoff.feature_season / last_complete_season. No model_version key: the
    producer name and arm identify the file."""
    from src.dynasty_genius.ranking.contract import annual_target

    c = _load(DG177_CSV, DG177_MANIFEST)
    assert c.spec == annual_target(FD)
    assert c.spec.labels_through == 2025 and c.forecast_year == 2026 and c.seasons == 2
    assert c.model_version == "dg177_annual_forecasts:recent_production_3col"


def test_veteran_rows_join_on_gsis_id_carried_by_the_served_row() -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load(DG177_CSV, DG177_MANIFEST)
    v1 = ServedRow(player_id="dg-v1", sleeper_id="5001", full_name="Vet One", position="WR", age=26,
                   dynasty_value_score=50.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                   projection_2y=12.0, captured_at="x", gsis_id="00-0099001")
    fa = ServedRow(player_id="dg-fa", sleeper_id="5002", full_name="Free Agent", position="WR", age=26,
                   dynasty_value_score=40.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                   projection_2y=9.0, captured_at="x", gsis_id="00-0099002")
    refs = annual_replacement([c], rostered_ids={"5001"}, snapshot_id="s", positions=["WR"], served_rows=[v1, fa])
    assert refs["WR"][0].player_id == "00-0099002" and refs["WR"][0].pool_complete is True
    ts = build_annual_term_set(v1, refs["WR"], c, forecast_date=FD)
    assert ts.coverage == "full"
    assert ts.terms[0].ev_above_replacement == pytest.approx(180.0 - 98.0)


def test_the_served_row_carries_gsis_id_from_identity_ids() -> None:
    from src.dynasty_genius.ranking.served_rows import ServedRow

    r = ServedRow.from_artifact_row({
        "dg_player_id": "dg1", "sleeper_player_id": "5001", "dvs_engine": "B", "projection_2y": 12.0,
        "identity_ids": {"gsis_id": "00-0099001", "sleeper_id": "5001"},
        "player": {"full_name": "Vet One", "position": "WR", "age": 26},
        "valuation": {"dynasty_value_score": 50.0, "dvs_p90_ref": 20.1, "dvs_clamped": False},
    }, captured_at="x")
    assert r.gsis_id == "00-0099001"


def test_the_bar_player_is_named_from_the_artifact_when_the_producer_has_no_name_column() -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import annual_replacement
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load(DG177_CSV, DG177_MANIFEST)
    fa = ServedRow(player_id="00-0099002", sleeper_id="5002", full_name="Free Agent", position="WR", age=26,
                   dynasty_value_score=40.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                   projection_2y=9.0, captured_at="x", gsis_id="00-0099002")
    v1 = ServedRow(player_id="00-0099001", sleeper_id="5001", full_name="Vet One", position="WR", age=26,
                   dynasty_value_score=50.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                   projection_2y=12.0, captured_at="x", gsis_id="00-0099001")
    refs = annual_replacement([c], rostered_ids={"5001"}, snapshot_id="s", positions=["WR"], served_rows=[v1, fa])
    assert refs["WR"][0].player_name == "Free Agent"


DG177_RESULTS = Path(__file__).parent / "fixtures" / "annual_veteran_dg177_results.json"


def test_the_producers_own_grading_rides_on_each_term_as_an_evidence_note() -> None:
    """Lane 23481 graded unconditional points per position and season against a
    training-only persistence baseline and said QB year 2 does not beat it. The note is
    derived from results.json, not from prose, and lands on the term it describes."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        AnnualCandidate,
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = AnnualCandidate.load(DG177_CSV, DG177_MANIFEST, results_path=DG177_RESULTS)
    assert c.evidence_notes[("WR", 1)].startswith("beats")
    assert c.evidence_notes[("WR", 2)].startswith("does not beat")
    assert "95.0" in c.evidence_notes[("WR", 2)] and "92.0" in c.evidence_notes[("WR", 2)]
    fa = ServedRow(player_id="00-0099002", sleeper_id="5002", full_name="Free Agent", position="WR", age=26,
                   dynasty_value_score=40.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                   projection_2y=9.0, captured_at="x", gsis_id="00-0099002")
    v1 = ServedRow(player_id="00-0099001", sleeper_id="5001", full_name="Vet One", position="WR", age=26,
                   dynasty_value_score=50.0, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="B",
                   projection_2y=12.0, captured_at="x", gsis_id="00-0099001")
    refs = annual_replacement([c], rostered_ids={"5001"}, snapshot_id="s", positions=["WR"], served_rows=[v1, fa])
    ts = build_annual_term_set(v1, refs["WR"], c, forecast_date=FD)
    assert "does not beat" in ts.terms[1].conditioning_event
    assert "beats" in ts.terms[0].conditioning_event


def test_without_a_results_file_there_are_no_evidence_notes_and_nothing_is_invented() -> None:
    c = _load(DG177_CSV, DG177_MANIFEST)
    assert c.evidence_notes == {}


V3_EVALUATION = Path(__file__).parent / "fixtures" / "annual_rookie_v3_evaluation.json"


def test_the_rookie_lanes_grading_shape_yields_per_position_notes_with_bias() -> None:
    """evaluation.json["annual"]["j"]["e_points_year"] with rmse / rmse_training_baseline /
    bias, per position under by_position; a position the file does not grade falls back to
    the pooled cell. The bias rides on the note: their season-1 points run 12 under."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    c = AnnualCandidate.load(V3_CSV, V3_MANIFEST, results_path=V3_EVALUATION)
    assert c.evidence_notes[("QB", 1)].startswith("beats") and "65.3" in c.evidence_notes[("QB", 1)]
    assert "bias -18.7" in c.evidence_notes[("QB", 1)]
    assert c.evidence_notes[("QB", 2)].startswith("does not beat")
    assert c.evidence_notes[("TE", 1)].startswith("beats")
    # TE season 2 is not graded per position: pooled cell, labelled as pooled
    assert c.evidence_notes[("TE", 2)].startswith("beats") and "pooled" in c.evidence_notes[("TE", 2)]


def test_evidence_notes_from_an_evaluation_of_another_arm_say_so_on_every_term(tmp_path) -> None:
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    m = json.loads(V3_MANIFEST.read_text())
    m["trend_experiment"] = {"decision": "auto_trend"}
    man = tmp_path / "m.json"
    man.write_text(json.dumps(m))
    ev = json.loads(V3_EVALUATION.read_text())
    ev.pop("policy_id", None)
    ev["trend"] = False
    evp = tmp_path / "e.json"
    evp.write_text(json.dumps(ev))
    m.pop("scoring_arm_id", None)  # the trend_experiment decision is the affirmative identifier here
    man.write_text(json.dumps(m))
    c = AnnualCandidate.load(V3_CSV, man, results_path=evp)
    assert all(n.startswith("GRADING OF A DIFFERENT ARM") for n in c.evidence_notes.values())
    assert c.grading_arm_note is not None and "plain" in c.grading_arm_note


# ── Round 2, item 1: the season-long replace/retain counterfactual ──────────────────────
def _served_row(pid, sid, pos, name):
    from src.dynasty_genius.ranking.served_rows import ServedRow

    return ServedRow(player_id=pid, sleeper_id=sid, full_name=name, position=pos, age=25,
                     dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine=None,
                     projection_2y=None, captured_at="x", gsis_id=pid)


def test_the_replacement_player_is_worth_exactly_zero_against_himself() -> None:
    """Verified blocker (round 2): under E[points] - R x E[games] with R = E[points_bar]/17, the
    bar player himself came out +58.61 (Rattler) and +50.61 (Estime). The counterfactual is a
    season-long replace/retain comparison in one scoring window: signed margin = E[points_i]
    - E[points_ref]; the same player against himself is 0 at every season."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )

    c = _load(CSV, MANIFEST)  # WR fa1 (98.0 expected) is the best unrostered WR
    served = [_served_row("fa1", "201", "WR", "Free Agent"), _served_row("fa2", "202", "WR", "Free Agent Two"),
              _served_row("v1", "101", "WR", "Vet One"), _served_row("v2", "102", "WR", "Vet Two")]
    refs = annual_replacement([c], rostered_ids={"101", "102"}, snapshot_id="s", positions=["WR"], served_rows=served)
    assert refs["WR"][0].player_id == "fa1"
    ts = build_annual_term_set(served[0], refs["WR"], c, forecast_date=FD)
    assert [t.ev_above_replacement for t in ts.terms] == [0.0, 0.0]
    assert all(t.expected_margin == pytest.approx(0.0) for t in ts.terms)


def test_two_identical_forecast_distributions_yield_zero_and_the_margin_is_signed() -> None:
    """v2 expects 60.0 points in season 1 against fa1's 98.0: margin -38.0, so the ex-ante
    action is REPLACE and the expected policy advantage is 0; the signed margin is kept on the
    term so a reader can see how far below the reference he sits."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )

    c = _load(CSV, MANIFEST)
    served = [_served_row("fa1", "201", "WR", "Free Agent"), _served_row("v2", "102", "WR", "Vet Two"),
              _served_row("v1", "101", "WR", "Vet One")]
    refs = annual_replacement([c], rostered_ids={"101", "102"}, snapshot_id="s", positions=["WR"], served_rows=served)
    ts = build_annual_term_set(served[1], refs["WR"], c, forecast_date=FD)
    assert ts.terms[0].expected_margin == pytest.approx(60.0 - 98.0)
    assert ts.terms[0].ev_above_replacement == 0.0 and ts.terms[0].action == "replace"
    # v1: 180 - 98 = +82 in season 1, 144 - 72 = +72 in season 2: retain, positive part = margin
    ts1 = build_annual_term_set(served[2], refs["WR"], c, forecast_date=FD)
    assert ts1.terms[0].ev_above_replacement == pytest.approx(82.0) and ts1.terms[0].action == "retain"
    assert ts1.terms[1].ev_above_replacement == pytest.approx(72.0)
    assert refs["WR"][0].rate_quantity == "expected_season_points_same_window"
    assert refs["WR"][0].rate_ppg == pytest.approx(98.0)


def test_the_term_names_the_policy_as_season_long_replace_or_retain_not_weekly_optimal() -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )

    c = _load(CSV, MANIFEST)
    served = [_served_row("fa1", "201", "WR", "Free Agent"), _served_row("v1", "101", "WR", "Vet One")]
    refs = annual_replacement([c], rostered_ids={"101"}, snapshot_id="s", positions=["WR"], served_rows=served)
    ts = build_annual_term_set(served[1], refs["WR"], c, forecast_date=FD)
    ev = ts.terms[0].conditioning_event
    assert "season-long replace/retain" in ev and "not optimal weekly" in ev


# ── Round 2, item 3: evidence identity fails CLOSED ─────────────────────────────────────
def test_arm_consistency_with_no_affirmative_identifiers_is_unverified_not_consistent() -> None:
    """rookie_arm_consistency({}, {}) used to pass. Absence of an identifier is not agreement."""
    from src.dynasty_genius.ranking.grading import rookie_arm_consistency

    ok, why = rookie_arm_consistency({}, {})
    assert ok is False and "unverified" in why
    ok2, _ = rookie_arm_consistency({"scoring_arm_id": "auto_trend"}, {})
    assert ok2 is False
    ok3, _ = rookie_arm_consistency({"scoring_arm_id": "auto_trend", "outputs_sha256": {}}, {"policy_id": "auto_trend"})
    assert ok3 is True
    ok4, _ = rookie_arm_consistency({"scoring_arm_id": "auto_trend"}, {"policy_id": "plain"})
    assert ok4 is False


def test_a_producer_whose_evidence_identity_is_unverified_is_never_comparable(tmp_path) -> None:
    """Identifiers and hashes must be affirmative: the manifest names the scoring arm and the
    sha256 of the CSV it describes; the grading file names the arm it graded; they match. A
    file that cannot be verified is inspectable but not evidence-qualified: readiness
    'unverified', never 'comparable'."""

    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        AnnualCandidate,
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.assembler import compose_value
    from src.dynasty_genius.ranking.contract import Posture, annual_target
    from src.dynasty_genius.ranking.served_rows import ServedRow

    m = json.loads(V3_MANIFEST.read_text())
    m.pop("scoring_arm_id", None)
    m.pop("outputs_sha256", None)
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps(m))
    c = AnnualCandidate.load(V3_CSV, bare)  # no arm identifier, no declared hash, no grading file
    assert c.evidence.verified is False and "unverified" in c.evidence.reason
    v1 = ServedRow(player_id="dg-mendoza", sleeper_id="13269", full_name="Fernando Mendoza", position="QB", age=22,
                   dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine="A",
                   projection_2y=None, captured_at="x", nfl_draft_pick=1, draft_class=2026)
    other = ServedRow(player_id="dg-sadiq", sleeper_id="13330", full_name="Kenyon Sadiq", position="TE", age=21,
                      dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine="A",
                      projection_2y=None, captured_at="x", nfl_draft_pick=16, draft_class=2026)
    refs = annual_replacement([c], rostered_ids=set(), snapshot_id="s", positions=["QB"], served_rows=[v1, other])
    ts = build_annual_term_set(v1, refs["QB"], c, forecast_date=FD)
    assert ts.producer.evidence_verified is False
    rv = compose_value(ts, Posture(label="rebuild", discount=1.0), horizons=1, board=annual_target(FD))
    assert rv.readiness == "unverified" and rv.value is not None  # inspectable, not evidence-qualified
    rv2 = compose_value(ts, Posture(label="rebuild", discount=1.0), horizons=1, board=annual_target(FD), comparable_only=True)
    assert rv2.value is None and "unverified" in rv2.reason


def test_affirmative_identifiers_and_a_matching_declared_hash_verify_the_evidence(tmp_path) -> None:
    import hashlib
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    ev = json.loads(V3_EVALUATION.read_text())
    ev["policy_id"] = "auto_trend"
    evp = tmp_path / "e.json"
    evp.write_text(json.dumps(ev))
    hist = V3_CSV.parent / "historical_predictions.csv"  # the fixture history beside the scoring CSV
    m = json.loads(V3_MANIFEST.read_text())
    m["scoring_arm_id"] = "auto_trend"
    m["outputs_sha256"] = {V3_CSV.name: hashlib.sha256(V3_CSV.read_bytes()).hexdigest(),
                           hist.name: hashlib.sha256(hist.read_bytes()).hexdigest(),
                           evp.name: hashlib.sha256(evp.read_bytes()).hexdigest()}
    man = tmp_path / "m.json"
    man.write_text(json.dumps(m))
    c = AnnualCandidate.load(V3_CSV, man, results_path=evp)
    assert c.evidence.verified is True
    # a declared hash that does not match the bytes read is a failure, not a warning
    m["outputs_sha256"][V3_CSV.name] = "0" * 64
    man.write_text(json.dumps(m))
    c2 = AnnualCandidate.load(V3_CSV, man, results_path=evp)
    assert c2.evidence.verified is False and "sha256" in c2.evidence.reason


def test_rookie_rows_join_on_draft_season_and_pick_alone_position_is_an_attribute() -> None:
    """Max Bredeson: pick 159 is TE in the draft table and RB in Sleeper and nflverse's current
    players table. A pick number is unique within a draft year, so the join key is
    (draft_season, pick) and position rides along as an attribute."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        annual_replacement,
        build_annual_term_set,
    )
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = _load(V3_CSV, V3_MANIFEST)  # Sadiq is TE, pick 16 in the file
    row = ServedRow(player_id="dg-sadiq", sleeper_id="13330", full_name="Kenyon Sadiq", position="WR", age=21,
                    dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine="A",
                    projection_2y=None, captured_at="x", nfl_draft_pick=16, draft_class=2026)
    assert c.get(draft_season=2026, pick=16).name == "Kenyon Sadiq"
    refs = annual_replacement([c], rostered_ids=set(), snapshot_id="s", positions=["WR"], served_rows=[row])
    ts = build_annual_term_set(row, refs["WR"], c, forecast_date=FD)
    assert ts.coverage == "full" and ts.position == "WR"


def test_evidence_notes_read_the_policy_block_and_carry_fold_counts(tmp_path) -> None:
    """Lane 23481's basic-horizon results grade the selection POLICY under
    historical[pos][year{j}].pooled.policy.points_unconditional.{model,baseline}, with the
    folds listed in evaluated_test_seasons. A year graded on ONE fold must say so on the term."""
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    res = {"historical": {"WR": {
        "year1": {"evaluated_test_seasons": [2021, 2022, 2023], "pooled": {"policy": {"points_unconditional": {"model": {"rmse": 50.0}, "baseline": {"rmse": 60.0}}}}},
        "year5": {"evaluated_test_seasons": [2025], "pooled": {"policy": {"points_unconditional": {"model": {"rmse": 70.0}, "baseline": {"rmse": 72.0}}}}},
    }}}
    rp = tmp_path / "r.json"
    rp.write_text(json.dumps(res))
    hist = DG177_CSV.parent / "historical_predictions.csv"
    m = json.loads(DG177_MANIFEST.read_text())
    m["scoring_arm"] = "basic_cohort_3col_plus_lags"
    m.pop("candidate_arm", None)
    import hashlib
    m["outputs_sha256"][hist.name] = hashlib.sha256(hist.read_bytes()).hexdigest()
    m["outputs_sha256"][rp.name] = hashlib.sha256(rp.read_bytes()).hexdigest()
    man = tmp_path / "m.json"
    man.write_text(json.dumps(m))
    c = AnnualCandidate.load(DG177_CSV, man, results_path=rp)
    assert c.evidence_notes[("WR", 1)].startswith("beats") and "3 folds" in c.evidence_notes[("WR", 1)]
    assert "graded on ONE fold" in c.evidence_notes[("WR", 5)]
    assert c.evidence.verified is True  # the policy block IS the graded arm when the manifest names a scoring arm


# ── Round 3: evidence binds the scoring CSV, the history CSV and the evaluation file ─────
def _round3_producer(tmp_path, *, history_ok=True, evaluation_ok=True, declare_history=True):
    """A producer directory whose manifest declares sha256 for its scoring CSV, history CSV and
    evaluation file, with one of them optionally wrong or undeclared."""
    import hashlib
    import json
    import shutil

    d = tmp_path / "producer"
    d.mkdir()
    csv_p = d / V3_CSV.name
    shutil.copy(V3_CSV, csv_p)
    hist = d / "out_of_time_predictions.csv"
    hist.write_text("gsis_id,position,forecast_year,e_points_year1,points_1\n00-1,WR,2023,100,90\n")
    ev = json.loads(V3_EVALUATION.read_text())
    ev["policy_id"] = "auto_trend"
    evp = d / "evaluation.json"
    evp.write_text(json.dumps(ev))
    m = json.loads(V3_MANIFEST.read_text())
    m["scoring_arm_id"] = "auto_trend"
    m["outputs_sha256"] = {csv_p.name: hashlib.sha256(csv_p.read_bytes()).hexdigest(),
                           "evaluation.json": hashlib.sha256(evp.read_bytes()).hexdigest() if evaluation_ok else "1" * 64}
    if declare_history:
        m["outputs_sha256"]["out_of_time_predictions.csv"] = (hashlib.sha256(hist.read_bytes()).hexdigest()
                                                              if history_ok else "2" * 64)
    man = d / "manifest.json"
    man.write_text(json.dumps(m))
    return csv_p, man, evp


def test_evidence_is_verified_only_when_scoring_history_and_evaluation_bytes_all_match_their_declared_hashes(tmp_path) -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    csv_p, man, evp = _round3_producer(tmp_path)
    c = AnnualCandidate.load(csv_p, man, results_path=evp)
    assert c.evidence.verified is True
    assert c.evidence.bound_files == {"scoring": V3_CSV.name, "history": "out_of_time_predictions.csv",
                                      "evaluation": "evaluation.json"}
    assert "source check" in c.evidence.meaning and "not" in c.evidence.meaning  # identity, never validation


def test_a_history_file_whose_bytes_differ_from_the_declared_hash_leaves_the_evidence_unverified(tmp_path) -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    csv_p, man, evp = _round3_producer(tmp_path, history_ok=False)
    c = AnnualCandidate.load(csv_p, man, results_path=evp)
    assert c.evidence.verified is False and "history" in c.evidence.reason and "sha256" in c.evidence.reason


def test_an_evaluation_file_whose_bytes_differ_from_the_declared_hash_leaves_the_evidence_unverified(tmp_path) -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    csv_p, man, evp = _round3_producer(tmp_path, evaluation_ok=False)
    c = AnnualCandidate.load(csv_p, man, results_path=evp)
    assert c.evidence.verified is False and "evaluation" in c.evidence.reason and "sha256" in c.evidence.reason


def test_a_manifest_that_declares_no_history_file_is_unverified_not_silently_bound(tmp_path) -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    csv_p, man, evp = _round3_producer(tmp_path, declare_history=False)
    c = AnnualCandidate.load(csv_p, man, results_path=evp)
    assert c.evidence.verified is False and "history" in c.evidence.reason


def test_a_producers_evaluation_status_companion_is_read_per_season_and_bound_to_the_evaluation_bytes(tmp_path) -> None:
    """Lane 23481 writes <run>.evaluation_status.json beside the run directory naming the
    results sha it describes. Per (position, season): evaluated on n folds, or no evaluated
    policy fold. It is read only when its results sha matches the evaluation bytes read."""
    import hashlib
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    csv_p, man, evp = _round3_producer(tmp_path)
    status = {"results_sha256": hashlib.sha256(evp.read_bytes()).hexdigest(),
              "meaning": {"supported": "closed history sufficient to evaluate; not validation"},
              "positions": {"WR": {"year1": {"status": "evaluated", "evaluated_folds": 3,
                                             "baseline_improvement": "within the reported 90% interval"},
                                   "year2": {"status": "no_evaluated_policy_fold", "evaluated_folds": 0,
                                             "baseline_improvement": "not graded: zero evaluated policy folds"}}}}
    (tmp_path / "producer.evaluation_status.json").write_text(json.dumps(status))
    c = AnnualCandidate.load(csv_p, man, results_path=evp)
    assert c.evaluation_status is not None
    assert c.evaluation_status.per_season(1)["WR"]["folds"] == 3
    assert c.evaluation_status.per_season(2)["WR"]["status"] == "no_evaluated_policy_fold"
    assert c.evaluation_status.season_summary(2) == "not evaluated: zero historical folds at every position"
    assert c.evaluation_status.season_summary(1).startswith("evaluated on 3 folds")
    assert "within the 90% interval at 1 of 1 positions" in c.evaluation_status.season_summary(1)
    # a companion naming a different results sha is not read
    status["results_sha256"] = "9" * 64
    (tmp_path / "producer.evaluation_status.json").write_text(json.dumps(status))
    c2 = AnnualCandidate.load(csv_p, man, results_path=evp)
    assert c2.evaluation_status is None


# ── Round 3: the bar is the best among players WITH forecasts ────────────────────────────
def test_the_replacement_reference_states_it_is_the_best_among_forecast_players_and_counts_the_unforecast_eligible(tmp_path) -> None:
    """pool_complete=True meant 'every scored unrostered artifact player is forecast'. Eligible
    players nobody has forecast (no stat row, no draft pick) could still be the next actually
    available. The reference therefore carries its scope and the census count, and the
    completeness flag is False when eligible players are unforecast."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        AnnualCandidate,
        annual_replacement,
    )
    from src.dynasty_genius.ranking.served_rows import ServedRow

    c = AnnualCandidate.load(V3_CSV, V3_MANIFEST)
    v1 = ServedRow(player_id="dg-mendoza", sleeper_id="13269", full_name="Fernando Mendoza", position="QB", age=22,
                   dynasty_value_score=None, dvs_p90_ref=None, dvs_clamped=None, dvs_engine="A",
                   projection_2y=None, captured_at="x", nfl_draft_pick=1, draft_class=2026)
    refs = annual_replacement([c], rostered_ids=set(), snapshot_id="s", positions=["QB"], served_rows=[v1],
                              unforecast_eligible={"QB": 7})
    ref = refs["QB"][0]
    assert ref.reference_scope == "best among players with a forecast"
    # the forecast pool is complete (every scored unrostered artifact QB is forecast) while the
    # eligible census is not: both facts travel, and the copy must state the scope
    assert ref.unforecast_eligible == 7 and ref.pool_complete is True and ref.census_complete is False
    assert "7 eligible unrostered QB" in ref.pool_note and "may change the reference" in ref.pool_note
    # without a census the scope is still stated and the count is unknown, not zero
    refs2 = annual_replacement([c], rostered_ids=set(), snapshot_id="s", positions=["QB"], served_rows=[v1])
    assert refs2["QB"][0].unforecast_eligible is None and refs2["QB"][0].census_complete is None
    assert "eligible census not supplied" in (refs2["QB"][0].pool_note or "")
    # the future-season assumption is a scenario, said plainly
    assert "scenario" in ref.horizon_note.lower() and "not a claim about future waiver access" in ref.horizon_note


def test_a_rookie_evaluation_without_a_companion_yields_a_point_comparison_status_per_season() -> None:
    """Lane 24974's evaluation.json has no companion; its annual block gives one outer fold per
    forecast year and RMSE against the training baseline — a point comparison, never an
    interval, and the summary says so."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        _status_from_rookie_evaluation,
    )

    res = {"annual": {"1": {"p_qual_year": {"forecast_years": [2021, 2022, 2023]},
                            "e_points_year": {"rmse": 50.0, "rmse_training_baseline": 60.0, "forecast_years": [2021, 2022, 2023],
                                              "by_position": {"QB": {"rmse": 70.0, "rmse_training_baseline": 65.0},
                                                              "WR": {"rmse": 40.0, "rmse_training_baseline": 55.0}}}}}}
    st = _status_from_rookie_evaluation(res, "evaluation.json#annual")
    assert st is not None and st.per_season(1)["QB"]["folds"] == 3
    assert st.per_season(1)["QB"]["improvement"].startswith("rmse not below")
    assert st.season_summary(1) == ("evaluated on 3 folds; RMSE below its training-only baseline at 1 of 2 positions "
                                    "(a point comparison, no interval)")
    assert st.season_summary(1) and "90% interval" not in st.season_summary(1)


def test_a_file_on_the_full_season_window_is_refused_on_a_week17_board_never_mixed() -> None:
    """Codex, Week-17 queue: a changed window is a changed target. The first producer files
    (full regular season) cannot be composed on the championship-Week-17 board."""
    import pytest

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    with pytest.raises(ValueError, match="window"):
        AnnualCandidate.load(V3_CSV, V3_MANIFEST, window="championship_week17")
    assert AnnualCandidate.load(V3_CSV, V3_MANIFEST).spec.window == "all_reg_weeks"


# ── Week-17 queue: producers bind the SHARED outcome artifact's identity; mixed identities are refused ──
def _manifest_with_outcome(tmp_path, name, *, csv_sha="1" * 64, window="championship_week17", closure=2025, scoring="nflverse_default_ppr"):
    import json

    m = json.loads(V3_MANIFEST.read_text())
    m["scoring"] = scoring
    m["exposure_definition"] = "unique stat_record weeks within the outcome window"  # DG-179's exposure
    m["window"] = {"id": window, "regular_weeks_through_2020": [1, 16], "regular_weeks_since_2021": [1, 17]}
    # the binding a producer writes, in DG-179's own names (schema dg179_league_season_outcomes_v1)
    m["outcome"] = {"artifact": "outcomes.csv", "outcomes_csv_sha256": csv_sha, "manifest_sha256": "2" * 64,
                    "target_identity": "c" * 64, "scoring_identity": "a" * 64, "window_identity": "b" * 64,
                    "scoring_preset": "nflverse_default_ppr_championship_window_v1", "window": {"id": window},
                    "last_complete_season": closure, "coverage_status": "qualified_research_game_complete_identified_rows"}
    p = tmp_path / name
    p.write_text(json.dumps(m))
    return p


def test_a_producer_on_the_shared_outcome_binds_its_identity_from_the_manifest(tmp_path) -> None:
    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    c = AnnualCandidate.load(V3_CSV, _manifest_with_outcome(tmp_path, "m.json"), window="championship_week17")
    assert c.outcome_identity == {"artifact": "outcomes.csv", "outcomes_csv_sha256": "1" * 64, "manifest_sha256": "2" * 64,
                                  "target_identity": "c" * 64, "scoring_identity": "a" * 64, "window_identity": "b" * 64,
                                  "scoring_preset": "nflverse_default_ppr_championship_window_v1",
                                  "window": "championship_week17", "last_complete_season": 2025,
                                  "coverage_status": "qualified_research_game_complete_identified_rows"}
    assert c.spec.window == "championship_week17" and c.spec.scoring == "PPR_nflverse_default"
    assert c.spec.exposure == "stat_record_weeks_in_window"
    assert "coverage" not in c.evidence.reason  # the research qualification is affirmative
    # the first producer files bind no outcome artifact: stated as None, never invented
    assert AnnualCandidate.load(V3_CSV, V3_MANIFEST).outcome_identity is None


def test_producers_bound_to_different_outcome_artifacts_are_refused_together(tmp_path) -> None:
    import pytest

    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        AnnualCandidate,
        annual_replacement,
        assert_one_outcome_identity,
    )

    a = AnnualCandidate.load(V3_CSV, _manifest_with_outcome(tmp_path, "a.json"), window="championship_week17")
    b = AnnualCandidate.load(V3_CSV, _manifest_with_outcome(tmp_path, "b.json", csv_sha="9" * 64), window="championship_week17")
    assert a.outcome_identity["outcomes_csv_sha256"] != b.outcome_identity["outcomes_csv_sha256"]
    same = AnnualCandidate.load(V3_CSV, _manifest_with_outcome(tmp_path, "c.json"), window="championship_week17")
    assert_one_outcome_identity([a, same])  # identical binding: fine
    with pytest.raises(ValueError, match="outcome"):
        assert_one_outcome_identity([a, b])
    with pytest.raises(ValueError, match="outcome"):
        annual_replacement([a, b], rostered_ids=set(), snapshot_id="s")
    # a producer with no binding beside one with a binding is a mix too
    legacy = AnnualCandidate.load(V3_CSV, V3_MANIFEST)
    with pytest.raises(ValueError, match="outcome"):
        assert_one_outcome_identity([a, legacy])


def test_a_file_on_the_shared_outcome_is_unverified_until_the_artifacts_coverage_is_affirmatively_stated(tmp_path) -> None:
    """Codex, 2026-09-06 evening: a downloaded source is not complete outcome coverage. A
    producer bound to the shared artifact is verified only when its manifest carries the
    artifact's affirmative coverage status; absent or non-affirmative stays unverified."""
    import hashlib
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    def load(coverage):
        m = json.loads(V3_MANIFEST.read_text())
        m["scoring_arm_id"] = "auto_trend"
        m["scoring"] = "nflverse_default_ppr_championship_window_v1"
        m["exposure_definition"] = "unique stat_record weeks within the outcome window"
        m["window"] = "championship_week17"
        m["outcome"] = {"artifact": "outcomes.csv", "outcomes_csv_sha256": "1" * 64, "manifest_sha256": "2" * 64,
                        "target_identity": "c" * 64, "scoring_preset": "nflverse_default_ppr_championship_window_v1",
                        "window": {"id": "championship_week17"}, "last_complete_season": 2025}
        if coverage is not None:
            m["outcome"]["coverage_status"] = coverage["status"]
        ev = json.loads(V3_EVALUATION.read_text())
        ev["policy_id"] = "auto_trend"
        evp = tmp_path / "e.json"
        evp.write_text(json.dumps(ev))
        hist = V3_CSV.parent / "historical_predictions.csv"
        m["outputs_sha256"] = {V3_CSV.name: hashlib.sha256(V3_CSV.read_bytes()).hexdigest(),
                               hist.name: hashlib.sha256(hist.read_bytes()).hexdigest(),
                               evp.name: hashlib.sha256(evp.read_bytes()).hexdigest()}
        man = tmp_path / "m.json"
        man.write_text(json.dumps(m))
        return AnnualCandidate.load(V3_CSV, man, results_path=evp, window="championship_week17")

    assert load(None).evidence.verified is False and "coverage" in load(None).evidence.reason
    assert load({"status": "download_complete"}).evidence.verified is False
    assert load({"status": "calendar_checked_game_coverage_unverified"}).evidence.verified is False
    assert load({"status": "verified"}).evidence.verified is False  # a provisional word is not DG-179's qualification
    ok = load({"status": "qualified_research_game_complete_identified_rows"})
    assert ok.evidence.verified is True
    assert ok.outcome_identity["coverage_status"] == "qualified_research_game_complete_identified_rows"


def test_the_reference_records_its_runner_up_so_the_aging_reference_sensitivity_is_logged_not_hidden(tmp_path) -> None:
    """Codex (2026-09-06 evening): do NOT change the future-replacement policy this cycle;
    preserve the fixed same-available-player scenario explicitly and LOG the aging-reference
    sensitivity. The reference therefore names the runner-up, both per-season series and the
    season-1 gap that decided the identity."""
    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        AnnualCandidate,
        annual_replacement,
    )

    fx = Path(__file__).parent / "fixtures"
    c = AnnualCandidate.load(fx / "annual_candidate_fixture.csv", fx / "annual_candidate_manifest.json")
    refs = annual_replacement(c, rostered_ids={"101", "102", "401"}, snapshot_id="s")
    wr = refs["WR"][0]
    assert wr.runner_up is not None
    assert wr.runner_up["season1_gap"] > 0 and len(wr.runner_up["expected_points_by_season"]) == 2
    assert wr.runner_up["player_id"] != wr.player_id
    assert wr.reference_series == [r.rate_ppg for r in refs["WR"]]
    assert "same-available-player scenario" in wr.sensitivity_note and "runner-up" in wr.sensitivity_note


def test_a_manifest_that_binds_the_artifact_under_outcomes_types_the_window_from_the_preset(tmp_path) -> None:
    """Lane 24974's refit manifest (195904Z) binds the common artifact under `manifest.outcomes`
    (plural) with csv_sha256 / manifest_sha256 / declared_outputs and no top-level window key:
    the window is the artifact's, read from its scoring preset, and the identity comes from
    that block. Aliases follow the actual file, not the other way round."""
    import hashlib
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import (
        AnnualCandidate,
        _outcome_identity,
        _window,
    )

    m = json.loads(V3_MANIFEST.read_text())
    m["scoring_arm_id"] = "auto_trend"
    m["units"] = {"scoring_scope": "championship window: Equal-weight REG stat records ...; scoring preset "
                                   "nflverse_default_ppr_championship_window_v1; league_scoring_exact=False",
                  "exposure_definition": "unique stat_record weeks within the outcome window"}
    m["outcomes"] = {"schema_version": "dg179_league_season_outcomes_v1",
                     "csv_sha256": "1" * 64, "manifest_sha256": "2" * 64,
                     "declared_outputs": {"outcomes.csv": {"bytes": 10, "sha256": "1" * 64}},
                     "scoring_preset": "nflverse_default_ppr_championship_window_v1", "league_scoring_exact": False,
                     "target_identity": "c" * 64, "scoring_identity": "a" * 64, "window_identity": "b" * 64,
                     "coverage_status": "qualified_research_game_complete_identified_rows",
                     "exposure_definition": "unique stat_record weeks within the outcome window",
                     "labels_through": 2025, "covered_seasons": [2001, 2025]}
    for k in ("scoring_scope", "scoring", "exposure_definition", "window"):
        m.pop(k, None)
    ev = json.loads(V3_EVALUATION.read_text())
    ev["policy_id"] = "auto_trend"
    evp = tmp_path / "e.json"
    evp.write_text(json.dumps(ev))
    hist = V3_CSV.parent / "historical_predictions.csv"
    m["outputs_sha256"] = {V3_CSV.name: hashlib.sha256(V3_CSV.read_bytes()).hexdigest(),
                           hist.name: hashlib.sha256(hist.read_bytes()).hexdigest(),
                           evp.name: hashlib.sha256(evp.read_bytes()).hexdigest()}
    man = tmp_path / "m.json"
    man.write_text(json.dumps(m))
    assert _window(m) == "championship_week17"
    ident = _outcome_identity(m)
    assert ident["outcomes_csv_sha256"] == "1" * 64 and ident["manifest_sha256"] == "2" * 64
    assert ident["target_identity"] == "c" * 64 and ident["window"] == "championship_week17"
    assert ident["last_complete_season"] == 2025 and ident["coverage_status"].startswith("qualified_research")
    c = AnnualCandidate.load(V3_CSV, man, results_path=evp, window="championship_week17")
    assert c.spec.window == "championship_week17" and c.spec.exposure == "stat_record_weeks_in_window"
    assert c.spec.scoring == "PPR_nflverse_default" and c.evidence.verified is True


def test_the_evaluation_status_companion_is_recorded_with_the_sha256_of_the_bytes_read(tmp_path) -> None:
    """Lane 23481's cross-check of 202257Z: the evaluation-status companion was read but its
    sha256 appeared in no report. The status now carries the hash of the companion bytes so a
    report binds it like every other file read."""
    import hashlib
    import json

    from src.dynasty_genius.ranking.adapters.annual_candidate import AnnualCandidate

    csv_p, man, evp = _round3_producer(tmp_path)
    status = {"results_sha256": hashlib.sha256(evp.read_bytes()).hexdigest(),
              "positions": {"WR": {"year1": {"status": "evaluated", "evaluated_folds": 3,
                                             "baseline_improvement": "within the reported 90% interval"}}}}
    companion = tmp_path / "producer.evaluation_status.json"
    companion.write_text(json.dumps(status))
    c = AnnualCandidate.load(csv_p, man, results_path=evp)
    assert c.evaluation_status is not None
    assert c.evaluation_status.source_sha256 == hashlib.sha256(companion.read_bytes()).hexdigest()
    assert c.evaluation_status.to_json()["source_sha256"] == c.evaluation_status.source_sha256
