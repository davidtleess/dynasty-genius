"""DG-178 — reading the DG-165 rookie candidate (research output) into the contract.

The candidate file gives, per drafted 2026 rookie, P(qualifies in NFL season j) for
j = 1..5 on the same bar-rank event as the DG-164 cells. It does NOT give the conditional
production level E[ppg | qualifies in j]. So the adapter can build the probability half of
every term and must say, per player, that the level is missing — a partial with the
probabilities quoted, never a number and never a filled-in level.

Clock: the candidate's NFL season j (rookie season = 1 = 2026) is the contract's h = j - 1.
Join: the served artifact has no gsis_id for 2026 rookies, so the key is
(position, draft_season, pick).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

FD = date(2026, 9, 6)
FIXTURE_CSV = Path(__file__).parent / "fixtures" / "rookie_candidate_fixture.csv"
FIXTURE_MANIFEST = Path(__file__).parent / "fixtures" / "rookie_candidate_manifest.json"


def _row(pid="13269", pos="QB", pick=1, name="Fernando Mendoza"):
    from src.dynasty_genius.ranking.served_rows import ServedRow

    return ServedRow(player_id=pid, sleeper_id=pid, full_name=name, position=pos, age=22,
                     dynasty_value_score=70.73, dvs_p90_ref=20.1, dvs_clamped=False, dvs_engine="A",
                     projection_2y=None, captured_at="2026-09-06T13:00:53+00:00")


def _ref(pos="QB", rate=9.407):
    from src.dynasty_genius.ranking.contract import ReplacementRef

    return ReplacementRef(position=pos, policy="best_available_served_rate", rate_ppg=rate,
                          conditional_rate_ppg=10.7, snapshot_id="s",
                          horizon_assumption="held_constant_from_snapshot")


def _candidate():
    from src.dynasty_genius.ranking.adapters.rookie_candidate import RookieCandidate

    return RookieCandidate.load(FIXTURE_CSV, FIXTURE_MANIFEST)


def test_the_candidate_records_its_model_version_event_and_clock() -> None:
    c = _candidate()
    assert c.model_version == "dg165_rookie_capital_v1"
    assert c.rookie_season == 2026
    assert "QB37" in c.qualifying_event
    assert len(c.csv_sha256) == 64 and len(c.manifest_sha256) == 64
    assert c.seasons_covered == 5


def test_rows_are_keyed_by_position_draft_season_and_pick_not_gsis() -> None:
    c = _candidate()
    assert c.get("QB", 2026, 1).name == "Fernando Mendoza"
    assert c.get("TE", 2026, 16).name == "Kenyon Sadiq"
    assert c.get("WR", 2026, 999) is None


def test_without_a_level_the_term_set_is_partial_and_quotes_the_probabilities() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        build_rookie_term_set,
    )

    ts = build_rookie_term_set(_row(), _ref(), _candidate(), draft_pick=1, forecast_date=FD)
    assert ts.coverage == "partial"
    assert ts.terms == []
    assert "level" in ts.reason and "0.893" in ts.reason
    assert ts.producer.estimate_class == "candidate"
    assert ts.producer.name == "dg165_rookie_capital_v1"
    assert ts.served.dvs_engine == "A"


def test_with_a_level_each_season_multiplies_its_own_probability_by_its_own_margin() -> None:
    """ev_h = p_qual_year{h+1} x max(0, level_h - R). Season j=1 is h=0. Five seasons in the
    file, so a five-season board (horizons=4) is full."""
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        build_rookie_term_set,
    )

    level = [14.0, 15.0, 16.0, 16.0, 15.0]
    ts = build_rookie_term_set(_row(), _ref(rate=9.407), _candidate(), draft_pick=1, forecast_date=FD,
                               level_ppg_by_h=level, horizons=4)
    assert ts.coverage == "full"
    assert [t.h for t in ts.terms] == [0, 1, 2, 3, 4]
    assert ts.terms[0].ev_above_replacement == pytest.approx(0.893 * (14.0 - 9.407), abs=1e-3)
    assert ts.terms[1].season == 2027
    assert "qualifies in NFL season 2" in ts.terms[1].conditioning_event


def test_a_six_season_board_is_partial_because_the_file_covers_five() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        build_rookie_term_set,
    )

    ts = build_rookie_term_set(_row(), _ref(), _candidate(), draft_pick=1, forecast_date=FD,
                               level_ppg_by_h=[14.0] * 5, horizons=5)
    assert ts.coverage == "partial"
    assert len(ts.terms) == 5
    assert "covers 5" in ts.reason


def test_a_rookie_not_in_the_file_is_a_stated_absence() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        build_rookie_term_set,
    )

    ts = build_rookie_term_set(_row(pid="x", pos="WR", pick=250, name="Nobody"), _ref("WR"), _candidate(),
                               draft_pick=250, forecast_date=FD)
    assert ts.coverage == "none"
    assert "not in the rookie candidate file" in ts.reason


def test_a_level_below_the_bar_contributes_zero_that_season() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        build_rookie_term_set,
    )

    ts = build_rookie_term_set(_row(), _ref(rate=9.407), _candidate(), draft_pick=1, forecast_date=FD,
                               level_ppg_by_h=[5.0, 14.0, 14.0, 14.0, 14.0], horizons=4)
    assert ts.terms[0].ev_above_replacement == 0.0
    assert ts.terms[1].ev_above_replacement > 0.0


V2_CSV = Path(__file__).parent / "fixtures" / "rookie_candidate_v2_fixture.csv"
V2_MANIFEST = Path(__file__).parent / "fixtures" / "rookie_candidate_v2_manifest.json"


def test_the_real_manifest_shape_keeps_the_event_under_a_labels_string() -> None:
    """The DG-165 manifest stores its label definitions as a repr string under `labels`,
    not a `definitions` dict. The loader reads either, and refuses a manifest with neither."""
    from src.dynasty_genius.ranking.adapters.rookie_candidate import RookieCandidate

    c = RookieCandidate.load(V2_CSV, V2_MANIFEST)
    assert "bar rank" in c.qualifying_event and "37" in c.qualifying_event
    assert c.seasons_covered == 6
    assert c.ppg_denominator_note is not None and "REG" in c.ppg_denominator_note


def test_a_manifest_with_no_event_definition_is_refused(tmp_path) -> None:
    import json

    from src.dynasty_genius.ranking.adapters.rookie_candidate import RookieCandidate

    m = json.loads(V2_MANIFEST.read_text())
    del m["labels"]
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps(m))
    with pytest.raises(ValueError, match="qualifying"):
        RookieCandidate.load(V2_CSV, bad)


def test_a_level_carried_in_the_file_makes_a_six_season_board_full() -> None:
    """When the candidate supplies e_ppg_given_qual_year{j} itself, no caller level is needed
    and the term names the file as the level's source."""
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        RookieCandidate,
        build_rookie_term_set,
    )

    c = RookieCandidate.load(V2_CSV, V2_MANIFEST)
    ts = build_rookie_term_set(_row(), _ref(rate=9.407), c, draft_pick=1, forecast_date=FD, horizons=5)
    assert ts.coverage == "full"
    assert [t.h for t in ts.terms] == [0, 1, 2, 3, 4, 5]
    assert ts.terms[0].ev_above_replacement == pytest.approx(0.893 * (14.0 - 9.407), abs=1e-6)
    assert ts.terms[5].ev_above_replacement == pytest.approx(0.80 * (16.0 - 9.407), abs=1e-6)
    assert "level from dg165_rookie_capital_v2" in ts.terms[0].conditioning_event
    assert "REG" in ts.terms[0].conditioning_event  # the denominator mismatch rides on the term


def test_a_caller_level_overrides_the_file_level_and_says_so() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        RookieCandidate,
        build_rookie_term_set,
    )

    c = RookieCandidate.load(V2_CSV, V2_MANIFEST)
    ts = build_rookie_term_set(_row(), _ref(rate=9.407), c, draft_pick=1, forecast_date=FD, horizons=5,
                               level_ppg_by_h=[20.0] * 6, level_source="test override")
    assert ts.terms[0].ev_above_replacement == pytest.approx(0.893 * (20.0 - 9.407), abs=1e-6)
    assert "test override" in ts.terms[0].conditioning_event


V2_EVALUATION = Path(__file__).parent / "fixtures" / "rookie_candidate_v2_evaluation.json"


def test_the_levels_measured_bias_rides_on_every_rookie_term() -> None:
    """The lane measured its level under-predicting out of time by 0.6-1.1 ppg at every
    season. Against a 7-9 ppg bar that is a fifth of a rookie's margin, so it is quoted on
    the term itself — never left in a sibling file the reader of a number will not open."""
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        RookieCandidate,
        build_rookie_term_set,
    )

    c = RookieCandidate.load(V2_CSV, V2_MANIFEST, evaluation_path=V2_EVALUATION)
    assert c.level_caveat is not None
    assert "under-predicts" in c.level_caveat and "-1.13" in c.level_caveat
    assert c.level_bias_by_season["1"]["bias"] == -1.13
    ts = build_rookie_term_set(_row(), _ref(rate=9.407), c, draft_pick=1, forecast_date=FD, horizons=5)
    assert "under-predicts" in ts.terms[0].conditioning_event
    # A comparator that the level barely beats is part of the caveat, not a footnote.
    assert "position-mean" in c.level_caveat


def test_without_an_evaluation_file_the_caveat_is_absent_not_invented() -> None:
    from src.dynasty_genius.ranking.adapters.rookie_candidate import RookieCandidate

    c = RookieCandidate.load(V2_CSV, V2_MANIFEST)
    assert c.level_caveat is None and c.level_bias_by_season == {}


def test_a_rookie_file_for_another_season_is_refused_not_shifted_forward() -> None:
    """A 2026 rookie file read on a 2027 forecast date would relabel year 1 as 2027 and call
    it full. The same prior is not a forecast for a season later; refuse the vintage."""
    from src.dynasty_genius.ranking.adapters.rookie_candidate import (
        RookieCandidate,
        build_rookie_term_set,
    )

    c = RookieCandidate.load(V2_CSV, V2_MANIFEST)
    with pytest.raises(ValueError, match="vintage"):
        build_rookie_term_set(_row(), _ref(rate=9.407), c, draft_pick=1, forecast_date=date(2027, 9, 6), horizons=5)


def test_non_finite_probabilities_or_levels_in_the_file_are_refused(tmp_path) -> None:
    from src.dynasty_genius.ranking.adapters.rookie_candidate import RookieCandidate

    text = V2_CSV.read_text().replace(",0.893,", ",nan,")
    bad = tmp_path / "nan.csv"
    bad.write_text(text)
    with pytest.raises(ValueError, match="probability"):
        RookieCandidate.load(bad, V2_MANIFEST)
    text = V2_CSV.read_text().replace(",14.0,", ",inf,")
    bad2 = tmp_path / "inf.csv"
    bad2.write_text(text)
    with pytest.raises(ValueError, match="finite"):
        RookieCandidate.load(bad2, V2_MANIFEST)
